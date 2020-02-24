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
from core.views import determine_active_proposals
from photometrics.gf_movie import make_movie
from core.utils import save_to_default
from core.models.pipelines import PipelineProcess, PipelineOutput

logger = logging.getLogger(__name__)

class DownloadProcessPipeline(PipelineProcess):
    """
    Pipeline process to make a timelapse from a sequence of FITS images
    """
    short_name = 'dl'
    allowed_suffixes = ['.gz', '.fz']
    flags = {
        'skip_download': {
            'default': False,
            'long_name': 'Skip data download'
        },
    }
    OBSTYPES = ['EXPOSE', 'ARC', 'LAMPFLAT', 'SPECTRUM']

    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **flags):
        self.out_path = tmpdir()
        tl_settings = self.get_settings()

        try:
            self.download()
            # unpack tarballs and make movie.
            self.get_frames()
            self.process()
            self.cleanup()
        except ValueError as ex:
            logger.error('ValueError: {}'.format(ex))
            raise AsyncError('Invalid parameters. Are all images the same size?')
        except TimeLimitExceeded:
            raise AsyncError("Timelapse took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Timelapse record has been deleted")

        return [PipelineOutput(outfile, DataProduct, settings.DATA_PRODUCT_TYPES['timelapse'][0])]

    def download(self, obs_date, proposals):
        self.frames = {}
        auth_headers = archive_login()
        start_date, end_date = determine_archive_start_end(obs_date)
        for proposal in proposals:
            logger.info("Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal ))
            obstypes = OBSTYPES
            if (proposal == 'LCOEngineering' and options['dlengimaging'] is False) or options['spectraonly'] is True:
                # Not interested in imaging frames
                obstypes = ['ARC', 'LAMPFLAT', 'SPECTRUM']

            for obstype in obstypes:
                if obstype == 'EXPOSE':
                    redlevel = ['91', ]
                else:
                    # '' seems to be needed to get the tarball of FLOYDS products
                    redlevel = ['0', '']
                frames = get_frame_data(start_date, end_date, auth_headers, obstype, proposal, red_lvls=redlevel)
                for red_lvl in frames.keys():
                    if red_lvl in all_frames:
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
                for red_lvl in all_frames.keys():
                    logger.info("Found %d frames for reduction level: %s" % ( len(all_frames[red_lvl]), red_lvl ))
                dl_frames = download_files(self.frames, self.out_path)
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
                    if filenames:
                        for filename in filenames:
                            save_to_default(filename, self.out_path)
        return

    def process(self):
        return

    def cleanup():
        # Check if we're using a temp dir and then delete it
        if gettempdir() in self.out_path:
            shutil.rmtree(self.out_path)
