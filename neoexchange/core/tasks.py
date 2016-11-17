# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from celery.schedules import crontab
from celery.decorators import periodic_task

import os
from datetime import datetime
from glob import glob
from sys import exit
import tempfile

from photometrics.catalog_subs import store_catalog_sources, make_sext_file, extract_sci_image
from photometrics.external_codes import make_pa_rate_dict, run_mtdlink
from astrometrics.sources_subs import fetch_NEOCP, parse_NEOCP_extra_params
from core.views import update_NEOCP_orbit, update_NEOCP_observations, check_catalog_and_refit, store_detections

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


import logging

logger = logging.getLogger(__name__)


@periodic_task(run_every=(crontab(minute='*/10')))
def update_neocp_data():
    #Check NEOCP for objects in need of follow up
    logger.debug("==== Fetching NEOCP targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
    neocp_page = fetch_NEOCP()
    obj_ids = parse_NEOCP_extra_params(neocp_page)
    logger.debug("==== Found %s NEOCP targets ====" % len(obj_ids))
    for obj_id in obj_ids:
        obj_name = obj_id[0]
        obj_extra_params = obj_id[1]
        logger.debug("Reading NEOCP target %s" % obj_name)
        resp = update_NEOCP_orbit(str(obj_name), obj_extra_params)
        if resp:
            logger.debug(resp)
        resp = update_NEOCP_observations(str(obj_name), obj_extra_params)
        if resp:
            logger.debug(resp)

@shared_task
def pipeline_astrometry(datadir, temp_dir, keep_temp_dir, skip_mtdlink, pa, deltapa):

    # set tolerance for determining the zeropoint and catalog to use (should be cmdline options)
    std_zeropoint_tolerance = 0.10

    logger.debug("==== Pipeline processing astrometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

    datadir = os.path.join(datadir, '')
    logger.debug("datapath=%s" % (datadir))

    # Get lists of images and catalogs
    fits_files, fits_catalogs = determine_images_and_catalogs(datadir)
    if fits_files == None or fits_catalogs == None:
        exit(-2)

    # If a --temp_dir option was given on the command line use that as our
    # directory, otherwise create a random directory in /tmp
    if temp_dir:
        temp_dir = os.path.expanduser(temp_dir)
        if os.path.exists(temp_dir) == False:
            os.makedirs(temp_dir)
    else:
        temp_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')

    keep_temp = ''
    if keep_temp_dir: keep_temp = ' (will keep)'
    logger.debug("Using %s as temp dir%s" % (temp_dir, keep_temp ))

    #create a new list of fits files to run mtdlink on
    fits_file_list = []

    configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))
    for catalog in fits_catalogs:
        # Step 1: Determine if astrometric fit in catalog is good and
        # if not, refit using SExtractor and SCAMP.
        logger.debug("Processing %s" % catalog)
        new_catalog_or_status, num_new_frames_created = check_catalog_and_refit(configs_dir, temp_dir, catalog)

        try:
            int(new_catalog_or_status)
            if new_catalog_or_status != 0:
                logger.debug("Error reprocessing %s (Error code= %s)" % (catalog, new_catalog_or_status))
                exit(-3)
            new_catalog = catalog
            catalog_type = 'LCOGT'
            if 'e91' in catalog or 'e11' in catalog:
                catalog_type = 'BANZAI'
        except ValueError:
            new_catalog = new_catalog_or_status
            catalog_type = 'FITS_LDAC'
            if 'e91' in catalog or 'e11' in catalog:
                catalog_type = 'BANZAI_LDAC'

        # Step 2: Check for good zeropoint and redetermine if needed. Ingest
        # results into CatalogSources
        logger.debug("Creating CatalogSources from %s (Cat. type=%s)" % (new_catalog, catalog_type))

        num_sources_created, num_in_catalog = store_catalog_sources(new_catalog, std_zeropoint_tolerance, catalog_type)
        if num_sources_created >= 0 and num_in_catalog > 0:
            logger.debug("Created/updated %d sources from %d in catalog" % (num_sources_created, num_in_catalog) )
        else:
            logger.debug("Error occured storing catalog sources (Error code= %d, %d)" % (num_sources_created, num_in_catalog))
        # Step 3: Synthesize MTDLINK-compatible SExtractor .sext ASCII catalogs
        # from CatalogSources
        logger.debug("Creating .sext file(s) from %s" % (new_catalog))
        fits_filename = make_sext_file(temp_dir, new_catalog, catalog_type)

        if 'BANZAI' in catalog_type:
            fits_filename = extract_sci_image(catalog, new_catalog)
        fits_file_list.append(fits_filename)

    if skip_mtdlink == False:
        # Step 4: Run MTDLINK to find moving objects
        logger.debug("Running mtdlink on file(s) %s" % (fits_file_list))
        param_file = os.path.abspath(os.path.join('photometrics', 'configs', 'mtdi.lcogt.param'))
        #May change this to get pa and rate from compute_ephem later
        pa_rate_dict = make_pa_rate_dict(float(pa), float(deltapa), float(minrate), float(maxrate))

        retcode_or_cmdline = run_mtdlink(configs_dir, temp_dir, fits_file_list, len(fits_file_list), param_file, pa_rate_dict, catalog_type)

        # Step 5: Read MTDLINK output file and create candidates in NEOexchange
        if len(fits_file_list) > 0:
            mtds_file = os.path.join(temp_dir, fits_file_list[0].replace('.fits', '.mtds'))
            if os.path.exists(mtds_file):
                store_detections(mtds_file,dbg=False)
            else:
                logger.debug("Cannot find the MTDS output file  %s" % mtds_file)
    else:
        logger.debug("Skipping running of mtdlink")

    # Tidy up
    if keep_temp_dir != True:
        try:
            files_to_remove = glob(os.path.join(temp_dir, '*'))
            for file_to_rm in files_to_remove:
                os.remove(file_to_rm)
        except OSError:
            logger.debug("Error removing files in temporary test directory %s" % temp_dir)
        try:
            os.rmdir(temp_dir)
        except OSError:
             logger.debug("Error removing temporary test directory %s" % temp_dir)

def determine_images_and_catalogs(datadir, output=True):

    fits_files, fits_catalogs = None, None

    if os.path.exists(datadir) and os.path.isdir(datadir):
        fits_files = sorted(glob(datadir + '*e??.fits'))
        fits_catalogs = sorted(glob(datadir + '*e??_cat.fits'))
        banzai_files = sorted(glob(datadir + '*e91.fits*'))
        banzai_ql_files = sorted(glob(datadir + '*e11.fits*'))
        if len(banzai_files) > 0:
            fits_files = fits_catalogs = banzai_files
        elif len(banzai_ql_files) > 0:
            fits_files = fits_catalogs = banzai_ql_files
        if len(fits_files) == 0 and len(fits_catalogs) == 0:
            logger.debug("No FITS files and catalogs found in directory %s" % datadir)
            fits_files, fits_catalogs = None, None
        else:
            logger.debug("Found %d FITS files and %d catalogs" % ( len(fits_files), len(fits_catalogs)))
    else:
        logger.debug("Could not open directory $s" % datadir)
        fits_files, fits_catalogs = None, None

    return fits_files, fits_catalogs
