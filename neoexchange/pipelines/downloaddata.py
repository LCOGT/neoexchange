import logging
import os
from sys import argv
from datetime import datetime, timedelta
from tempfile import mkdtemp, gettempdir
import shutil
from glob import glob
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.forms import model_to_dict
from dramatiq.middleware.time_limit import TimeLimitExceeded

from astrometrics.ephem_subs import determine_rates_pa
from core.archive_subs import archive_login, get_frame_data, get_catalog_data, \
    determine_archive_start_end, download_files, make_data_dir
from core.models import Frame
from core.models.pipelines import PipelineProcess, PipelineOutput
from core.utils import save_to_default, NeoException
from core.views import determine_active_proposals
from photometrics.catalog_subs import get_fits_files, sort_rocks, find_first_last_frames
from photometrics.gf_movie import make_movie

logger = logging.getLogger(__name__)

class DownloadProcessPipeline(PipelineProcess):
    """
    Download and process FITS image and spectra data
    """
    short_name = 'dlp'
    long_name = 'Download and Process observation data'
    inputs = {
        'obs_date': {
            'default': None,
            'long_name': 'Date of the data to download (YYYYMMDD)'
        },
        'proposals':{
            'default': None,
            'long_name' : 'Proposal code to query for data (e.g. LCO2019B-023; default is for all active proposals)'
        },
        'spectraonly': {
            'default' : False,
            'long_name' : 'Whether to only download spectra'
        },
        'dlengimaging' : {
            'default' : False,
            'long_name' : 'Whether to download imaging for LCOEngineering'
        },
        'downloadonly': {
            'default' : False,
            'long_name' : 'Whether to only download data'
        },
        'numdays' : {
            'default' : 0.0,
            'long_name' : 'How many extra days to look for'
        },
        'object' : {
            'default' : '',
            'long_name' : 'Download data for specific object'
        }
    }
    OBSTYPES = ['EXPOSE', ] # 'ARC', 'LAMPFLAT', 'SPECTRUM']

    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **inputs):
        if not inputs.get('datadir'):
            out_path = tmpdir
        else:
            out_path = inputs.get('datadir')
        obs_date = inputs.get('obs_date')
        proposals = inputs.get('proposals')
        dlengimaging = inputs.get('dlengimaging')
        spectraonly = inputs.get('spectraonly')
        downloadonly = inputs.get('downloadonly')
        numdays = inputs.get('numdays')
        object = inputs.get('object')

        try:
            self.download(obs_date, proposals, out_path, numdays, dlengimaging, spectraonly)
            # unpack tarballs and make movie.
            self.create_movies()
            self.sort_objects()
            if downloadonly is False:
                self.process(objectid=object)
        except NeoException as ex:
            logger.error('Error with Movie: {}'.format(ex))
            self.log('Error with Movie: {}'.format(ex))
            raise AsyncError('Error creating movie')
        except TimeLimitExceeded:
            raise AsyncError("Download and create took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return

    def download(self, obs_date, proposals, out_path, maxfiles_mtd, numdays=0.0, dlengimaging=False, spectraonly=False):
        self.frames = {}
        self.maxfiles_mtd = maxfiles_mtd
        if not hasattr(self, 'out_path'):
            self.out_path = Path(out_path) / obs_date.strftime('%Y%m%d')
        if not hasattr(self, 'obs_date'):
            self.obs_date = obs_date
        auth_headers = archive_login()
        start_date, end_date = determine_archive_start_end(obs_date)
        end_date = end_date + timedelta(days=numdays)
        for proposal in proposals:
            logger.info("Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal ))
            self.log("Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal ))
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
                self.log(f"Looking for {obstype} data")
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
                    self.log("Found %d frames for reduction level: %s" % ( len(self.frames[red_lvl]), red_lvl ))
                dl_frames = download_files(self.frames, out_path)
                logger.info("Downloaded %d frames" % ( len(dl_frames) ))
                self.log("Downloaded %d frames" % ( len(dl_frames) ))
        return

    def sort_objects(self):
        self.log('Sorting rocks')
        fits_files = get_fits_files(self.out_path)
        self.log("Found %d FITS files in %s" % (len(fits_files), self.out_path))
        objects = sort_rocks(fits_files)
        logger.info(objects)
        self.objects = objects
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

    def process(self, objectid=None):
# Step 3: For each object:
        for rock in self.objects:
            # Skip if a specific object was specified on the commandline and this isn't it
            if objectid and objectid not in rock:
                    continue
            datadir = os.path.join(self.out_path, rock)
            self.log('Processing target %s in %s' % (rock, datadir))

# Step 3a: Check data is in DB
            fits_files = get_fits_files(datadir)
            self.log("Found %d FITS files in %s" % (len(fits_files), datadir))
            first_frame, last_frame = find_first_last_frames(fits_files)
            if not first_frame or not last_frame:
                self.log("Couldn't determine first and last frames, skipping target")
                continue
            self.log("Timespan %s->%s" % (first_frame.midpoint, last_frame.midpoint))
# Step 3b: Calculate mean PA and speed
            if first_frame.block:
                astrometry_lightcurve(first_frame, last_frame, body=first_frame.block.body, datadir=datadir, fits_files=fits_files, date=self.obs_date, maxfiles_mtd=self.maxfiles_mtd)
            else:
                self.log(f"No Block found for object {rock}")
        return

    def cleanup(self):
        # Check if we're using a temp dir and then delete it
        # This is only needed when running as management command version
        # Async pipeline uses autoclosing syntax
        if gettempdir() in self.out_path:
            shutil.rmtree(self.out_path)

def astrometry_lightcurve(first_frame, last_frame, body, datadir, fits_files, date, maxfiles_mtd):
    if body.epochofel:
        elements = model_to_dict(body)
        min_rate, max_rate, pa, deltapa = determine_rates_pa(first_frame.midpoint, last_frame.midpoint, elements, first_frame.sitecode)

# Step 3c: Run pipeline_astrometry
        mtdlink_args = "datadir=%s pa=%03d deltapa=%03d minrate=%.3f maxrate=%.3f" % (datadir, pa, deltapa, min_rate, max_rate)
        skip_mtdlink = False
        keep_temp_dir = False
        if len(fits_files) > maxfiles_mtd:
            logger.info("Too many frames to run mtd_link")
            skip_mtdlink = True
# Compulsory arguments need to go here as a list
        mtdlink_args = [datadir, pa, deltapa, min_rate, max_rate]

# Optional arguments go here, minus the leading double minus signs and with
# hyphens replaced by underscores for...reasons.
# e.g. '--keep-temp-dir' becomes 'temp_dir'
        mtdlink_kwargs = {'temp_dir': os.path.join(datadir, 'Temp'),
                          'skip_mtdlink': skip_mtdlink,
                          'keep_temp_dir': False
                          }
        logger.info("Calling pipeline_astrometry with: %s %s" % (mtdlink_args, mtdlink_kwargs))
        try:
            status = call_command('pipeline_astrometry', *mtdlink_args, **mtdlink_kwargs)
        except NeoException as e:
            logger.error(f"ERROR: {e}")
    else:
        logger.error("Object %s does not have updated elements" % body.current_name())
    shortdate = date.strftime('%Y%m%d')
# Step 4: Run Lightcurve Extraction
    if first_frame.block.superblock.tracking_number == last_frame.block.superblock.tracking_number:
        status = call_command('lightcurve_extraction', int(first_frame.block.superblock.tracking_number),
                              '--single', '--date', shortdate)
    else:
        tn_list = []
        for fits in fits_files:
            if fits.block.superblock.tracking_number not in tn_list:
                status = call_command('lightcurve_extraction', int(fits.block.superblock.tracking_number),
                                      '--single', '--date', shortdate)
                tn_list.append(fits.block.superblock.tracking_number)
    return
