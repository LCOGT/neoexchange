import logging
import os
from sys import argv
from datetime import datetime, timedelta
from tempfile import mkdtemp, gettempdir
import shutil
from glob import glob

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

from core.archive_subs import archive_login, get_frame_data, get_catalog_data, \
    determine_archive_start_end, download_files, make_data_dir
from core.models.pipelines import PipelineProcess, PipelineOutput
from core.utils import save_to_default, NeoException
from core.views import determine_active_proposals
from photometrics.gf_movie import make_movie

logger = logging.getLogger(__name__)

class DownloadProcessPipeline(PipelineProcess):
    """
    Download and process FITS image and spectra data
    """
    short_name = 'dlp'
    allowed_suffixes = ['.gz', '.fz']
    inputs = {
        'date': {
            'default': None,
            'long_name': 'Date of the data to download (YYYYMMDD)'
        },
        'proposal':{
            'default': None,
            'long_name' : 'Proposal code to query for data (e.g. LCO2019B-023; default is for all active proposals)'
        },
        'datadir' : {
            'default' : None,
            'long_name' : 'Place to save data'
        },
        'spectraonly': {
            'default' : False,
            'long_name' : 'Whether to only download spectra'
        },
        'dlengimaging' : {
            'default' : False,
            'long_name' : 'Whether to download imaging for LCOEngineering'
        },
        'numdays' : {
            'default' : 0.0,
            'long_name' : 'How many extra days to look for'
        }
    }
    OBSTYPES = ['EXPOSE', 'ARC', 'LAMPFLAT', 'SPECTRUM']

    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **inputs):
        if not inputs.get('datadir')
            self.out_path = tmpdir()
        else:
            self.out_path = inputs.get('datadir')
        obs_date = inputs.get('obs_date')
        proposals = inputs.get('proposals')
        dlengimaging = inputs.get('dlengimaging')
        spectraonly = inputs.get('spectraonly')
        numdays = inputs.get('numdays')

        try:
            self.download(obs_date, proposals, out_path, dlengimaging, spectraonly)
            # unpack tarballs and make movie.
            self.create_movies()
            self.cleanup()
        except NeoException as ex:
            logger.error('Error with Movie: {}'.format(ex))
            raise AsyncError('Error creating movie')
        except TimeLimitExceeded:
            raise AsyncError("Download and create took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")

        return [PipelineOutput(outfile, DataProduct, settings.DATA_PRODUCT_TYPES['timelapse'][0])]

    def download(self, obs_date, proposals, out_path, dlengimaging=False, spectraonly=False):
        self.frames = {}
        if not hasattr(self, out_path):
            self.out_path = out_path
        auth_headers = archive_login()
        start_date, end_date = determine_archive_start_end(obs_date)
        for proposal in proposals:
            logger.info("Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal ))
            obstypes = self.OBSTYPES
            if (proposal == 'LCOEngineering' and not dlengimaging) or spectraonly:
                # Not interested in imaging frames
                obstypes = ['ARC', 'LAMPFLAT', 'SPECTRUM']

            for obstype in obstypes:
                if obstype == 'EXPOSE':
                    redlevel = ['91', ]
                else:
                    # '' seems to be needed to get the tarball of FLOYDS products
                    redlevel = ['0', '']
                logger.info(f"Looking for {obstype} data")
                frames = get_frame_data(start_date, end_date, auth_headers, obstype, proposal, red_lvls=redlevel)
                for red_lvl in frames.keys():
                    if red_lvl in self.frames:
                        self.frames[red_lvl] = self.frames[red_lvl] + frames[red_lvl]
                    else:
                        self.frames[red_lvl] = frames[red_lvl]
                if 'CATALOG' in obstype or obstype == '':
                    catalogs = get_catalog_data(frames, auth_headers)
                    for red_lvl in frames.keys():
                        if red_lvl in self.frames:
                            self.frames[red_lvl] = self.frames[red_lvl] + catalogs[red_lvl]
                        else:
                            self.frames[red_lvl] = catalogs[red_lvl]
                for red_lvl in self.frames.keys():
                    logger.info("Found %d frames for reduction level: %s" % ( len(self.frames[red_lvl]), red_lvl ))
                dl_frames = download_files(self.frames, out_path)
                logger.info("Downloaded %d frames" % ( len(dl_frames) ))
        return

    def create_movies(self):
        for frame in self.frames.get('', []):
            if "tar.gz" in frame['filename']:
                tar_path = make_data_dir(self.out_path, frame)
                obj = frame['OBJECT'].replace(" ", "_")
                req_num = str(frame['REQNUM'])
                movie_file = make_movie(frame['DATE_OBS'], obj, req_num, tar_path, self.out_path, frame['PROPID'])
                if settings.USE_S3:
                    filenames = glob(os.path.join(tar_path, obj + '_' + req_num, '*_2df_ex.fits'))
                    for filename in filenames:
                        save_to_default(filename, self.out_path)
        return

    def cleanup():
        # Check if we're using a temp dir and then delete it
        if gettempdir() in self.out_path:
            shutil.rmtree(self.out_path)
