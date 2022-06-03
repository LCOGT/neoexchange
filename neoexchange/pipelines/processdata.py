import logging
import os
from sys import argv
from datetime import datetime, timedelta

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from dramatiq.middleware.time_limit import TimeLimitExceeded

from core.models import Frame
from core.models.pipelines import PipelineProcess, PipelineOutput
from core.utils import save_to_default, NeoException
from core.views import find_matching_image_file, run_sextractor_make_catalog, run_scamp
from photometrics.catalog_subs import FITSHdrException, open_fits_catalog, get_catalog_header, increment_red_level

logger = logging.getLogger(__name__)

class SExtractorProcessPipeline(PipelineProcess):
    """
    Detect objects in a FITS image using SExtractor
    """
    short_name = 'detect'
    long_name = 'Detect objects in an image using SExtractor'
    inputs = {
        'fits_file': {
            'default': None,
            'long_name': 'Filepath to image file to process'
        },
        'configs_dir':{
            'default': os.path.abspath(os.path.join('photometrics', 'configs')),
            'long_name' : 'Full path to SExtractor configuration files'
        },
        'datadir': {
            'default' : None,
            'long_name' : 'Directory for output data'
        },
        'desired_catalog' : {
            'default' : 'GAIA-DR2',
            'long_name' : 'Type of astrometric catalog desired'
        }
    }

    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **inputs):
        if not inputs.get('datadir'):
            out_path = tmpdir
        else:
            out_path = inputs.get('datadir')
        fits_file = inputs.get('fits_file')
        configs_dir = inputs.get('configs_dir')
        desired_catalog = inputs.get('desired_catalog')

        try:
            filepath_or_status = self.setup(fits_file, desired_catalog)
            print('filepath_or_status=', filepath_or_status)
            if type(filepath_or_status) != int:
                status = self.process(filepath_or_status, configs_dir, out_path)
        except NeoException as ex:
            logger.error('Error with source extraction: {}'.format(ex))
            self.log('Error with source extraction: {}'.format(ex))
            raise AsyncError('Error performing source extraction')
        except TimeLimitExceeded:
            raise AsyncError("Source extraction took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return

    def setup(self, fits_file, desired_catalog):

        # Open catalog, get header and check fit status
        fits_header, junk_table, cattype = open_fits_catalog(fits_file, header_only=True)
        try:
            header = get_catalog_header(fits_header, cattype)
        except FITSHdrException as e:
            logger.error("Bad header for %s (%s)" % (fits_file, e))
            return -1

        # Check for matching catalog (solved with desired astrometric reference catalog)
        catfilename = os.path.basename(fits_file).replace('.fits', '_ldac.fits')
        reproc_catfilename = increment_red_level(catfilename)
        catalog_frames = Frame.objects.filter(filename__in=(catfilename, reproc_catfilename),
                                              frametype__in=(Frame.BANZAI_LDAC_CATALOG, Frame.FITS_LDAC_CATALOG),
                                              astrometric_catalog=desired_catalog)
        if len(catalog_frames) != 0:
            logger.info("Found reprocessed frame in DB")
            self.log(f"Found reprocessed frame ({catalog_frames[0]:}) in DB")
            return 0

        # Find image file for this catalog
        fits_filepath = find_matching_image_file(fits_file)
        if fits_filepath is None:
            logger.error("Could not open matching image %s for catalog %s" % ( fits_filepath, fits_file))
            return -1

        return fits_filepath

    def process(self, fits_file, configs_dir, dest_dir):

        # Make a new FITS_LDAC catalog from the frame
        self.log(f"Processing {fits_file:} with SExtractor")
        status, new_ldac_catalog = run_sextractor_make_catalog(configs_dir, dest_dir, fits_file)
        if status != 0:
            logger.error("Execution of SExtractor failed")
            self.log("Execution of SExtractor failed")
            return -4
        self.log(f"Produced {new_ldac_catalog:}")

class ScampProcessPipeline(PipelineProcess):
    """
    Refit astrometry for an object catalog using Scamp
    """
    short_name = 'scamp'
    long_name = 'Refit astrometry for an object catalog using Scamp'
    inputs = {
        'fits_file': {
            'default': None,
            'long_name': 'Filepath to image file to process'
        },
        'configs_dir':{
            'default': os.path.abspath(os.path.join('photometrics', 'configs')),
            'long_name' : 'Full path to Scamp configuration files'
        },
        'datadir': {
            'default' : None,
            'long_name' : 'Directory for output data'
        }
    }

    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **inputs):
        if not inputs.get('datadir'):
            out_path = tmpdir
        else:
            out_path = inputs.get('datadir')
        fits_file = inputs.get('fits_file')
        configs_dir = inputs.get('configs_dir')

        try:
            filepath_or_status = self.setup(fits_file)
            if type(filepath_or_status) != int:
                status = self.process(filepath_or_status, configs_dir, dest_dir)
        except NeoException as ex:
            logger.error('Error with source extraction: {}'.format(ex))
            self.log('Error with source extraction: {}'.format(ex))
            raise AsyncError('Error performing source extraction')
        except TimeLimitExceeded:
            raise AsyncError("Source extraction took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return

    def setup(self, fits_file):

        # Open catalog, get header and check fit status
        fits_header, junk_table, cattype = open_fits_catalog(fits_file, header_only=True)
        try:
            header = get_catalog_header(fits_header, cattype)
        except FITSHdrException as e:
            logger.error("Bad header for %s (%s)" % (catfile, e))
            return -1

        # Check for matching catalog (solved with desired astrometric reference catalog)
        catfilename = os.path.basename(catfile).replace('.fits', '_ldac.fits')
        reproc_catfilename = increment_red_level(catfilename)
        catalog_frames = Frame.objects.filter(filename__in=(catfilename, reproc_catfilename),
                                              frametype__in=(Frame.BANZAI_LDAC_CATALOG, Frame.FITS_LDAC_CATALOG),
                                              astrometric_catalog=desired_catalog)
        if len(catalog_frames) != 0:
            logger.info("Found reprocessed frame in DB")
            return 0

        # Find image file for this catalog
        fits_filepath = find_matching_image_file(fits_file)
        if fits_filepath is None:
            logger.error("Could not open matching image %s for catalog %s" % ( fits_filepath, fits_file))
            return -1

        return fits_filepath

    def process(self, fits_file, configs_dir, dest_dir):

        # Make a new FITS_LDAC catalog from the frame
        status, new_ldac_catalog = run_scamp(configs_dir, dest_dir, fits_file)
        if status != 0:
            logger.error("Execution of Scamp failed")
            return -4

class ZeropointProcessPipeline(PipelineProcess):
    """
    Determine zeropoint for a frame
    """
    short_name = 'zp'
    long_name = 'Determine zeropoint for a frame'
    inputs = {
        'fits_file': {
            'default': None,
            'long_name': 'Filepath to image file to process'
        },
        'configs_dir':{
            'default': os.path.abspath(os.path.join('photometrics', 'configs')),
            'long_name' : 'Full path to SExtractor configuration files'
        },
        'datadir': {
            'default' : None,
            'long_name' : 'Directory for output data'
        }
    }

    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **inputs):
        if not inputs.get('datadir'):
            out_path = tmpdir
        else:
            out_path = inputs.get('datadir')
        fits_file = inputs.get('fits_file')
        configs_dir = inputs.get('configs_dir')

        try:
            filepath_or_status = self.setup(fits_file)
            if type(filepath_or_status) != int:
                status = self.process(filepath_or_status, configs_dir, dest_dir)
        except NeoException as ex:
            logger.error('Error with source extraction: {}'.format(ex))
            self.log('Error with source extraction: {}'.format(ex))
            raise AsyncError('Error performing source extraction')
        except TimeLimitExceeded:
            raise AsyncError("Source extraction took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return

    def setup(self, fits_file):

        # Open catalog, get header and check fit status
        fits_header, junk_table, cattype = open_fits_catalog(fits_file, header_only=True)
        try:
            header = get_catalog_header(fits_header, cattype)
        except FITSHdrException as e:
            logger.error("Bad header for %s (%s)" % (catfile, e))
            return -1

        # Check for matching catalog (solved with desired astrometric reference catalog)
        catfilename = os.path.basename(catfile).replace('.fits', '_ldac.fits')
        reproc_catfilename = increment_red_level(catfilename)
        catalog_frames = Frame.objects.filter(filename__in=(catfilename, reproc_catfilename),
                                              frametype__in=(Frame.BANZAI_LDAC_CATALOG, Frame.FITS_LDAC_CATALOG),
                                              astrometric_catalog=desired_catalog)
        if len(catalog_frames) != 0:
            logger.info("Found reprocessed frame in DB")
            return 0

        # Find image file for this catalog
        fits_filepath = find_matching_image_file(fits_file)
        if fits_filepath is None:
            logger.error("Could not open matching image %s for catalog %s" % ( fits_filepath, fits_file))
            return -1

        return fits_filepath

    def process(self, fits_file, configs_dir, dest_dir):

        # Make a new FITS_LDAC catalog from the frame
        status, new_ldac_catalog = run_sextractor_make_catalog(configs_dir, dest_dir, fits_file)
        if status != 0:
            logger.error("Execution of SExtractor failed")
            return -4
