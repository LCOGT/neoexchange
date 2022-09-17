import logging
import time
import os
from sys import argv
from datetime import datetime, timedelta
import warnings

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from dramatiq.middleware.time_limit import TimeLimitExceeded
import calviacat as cvc
import astropy.coordinates as coord

from core.models import Frame
from core.models.pipelines import PipelineProcess, PipelineOutput
from core.utils import save_to_default, NeoException
from core.views import find_matching_image_file, run_sextractor_make_catalog, \
    run_scamp, find_block_for_frame, make_new_catalog_entry
from core.tasks import send_task, run_pipeline
from photometrics.catalog_subs import FITSHdrException, open_fits_catalog, \
    get_catalog_header, increment_red_level, get_reference_catalog, extract_catalog, \
    existing_catalog_coverage, reset_database_connection, \
    update_zeropoint, update_frame_zeropoint, get_or_create_CatalogSources
from photometrics.photometry_subs import map_filter_to_calfilter
from photometrics.external_codes import updateFITSWCS, updateFITScalib

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
            filepath_or_status = self.setup(fits_file, desired_catalog, out_path)
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

    def setup(self, fits_file, desired_catalog, dest_dir):

        # Open catalog, get header and check fit status
        fits_header, junk_table, cattype = open_fits_catalog(fits_file, header_only=True)
        try:
            header = get_catalog_header(fits_header, cattype)
        except FITSHdrException as e:
            logger.error("Bad header for %s (%s)" % (fits_file, e))
            return -1

        # Check for matching catalog (solved with desired astrometric reference catalog)
        catfilename = os.path.basename(fits_file).replace('.fits', '_ldac.fits')
        catalog_frames = Frame.objects.filter(filename=catfilename,
                                              frametype__in=(Frame.BANZAI_LDAC_CATALOG, Frame.FITS_LDAC_CATALOG),
                                              astrometric_catalog=desired_catalog)
        if len(catalog_frames) != 0:
            logger.info(f"Found reprocessed frame ({catalog_frames[0].filename:}) in DB")
            self.log(f"Found reprocessed frame ({catalog_frames[0].filename:}) in DB")
            ldac_filepath =  os.path.abspath(os.path.join(dest_dir, catalog_frames[0].filename))
            if os.path.exists(ldac_filepath) is True:
                return 0
            else:
                logger.info("but not on disk. continuing")
                self.log("but not on disk. continuing")

        # Find image file for this catalog
        fits_filepath = find_matching_image_file(fits_file)
        if fits_filepath is None:
            logger.error("Could not open matching image %s for catalog %s" % ( fits_filepath, fits_file))
            return -1

        return fits_filepath

    def process(self, fits_file, configs_dir, dest_dir):

        # Make a new FITS_LDAC catalog from the frame
        self.log(f"Processing {fits_file:} with SExtractor")
        checkimage_types = ['BACKGROUND_RMS', "-BACKGROUND"]
        if '-e91' in fits_file:
            # No need to make rms or background images until we have a new
            # astrometric fit and -e92 files
            checkimage_types = []
        status, new_ldac_catalog = run_sextractor_make_catalog(configs_dir, dest_dir, fits_file, checkimage_type=checkimage_types)
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
        'ldac_catalog': {
            'default': None,
            'long_name': 'Filepath to source catalog to process'
        },
        'configs_dir':{
            'default': os.path.abspath(os.path.join('photometrics', 'configs')),
            'long_name' : 'Full path to Scamp configuration files'
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
        ldac_catalog = inputs.get('ldac_catalog')
        configs_dir = inputs.get('configs_dir')
        desired_catalog = inputs.get('desired_catalog')

        try:
            refcat_or_status = self.setup(ldac_catalog, out_path, desired_catalog)
            if type(refcat_or_status) != int:
                # Run SCAMP on the FITS-LDAC catalog to derive new astrometric fit
                status = self.process(ldac_catalog, configs_dir, out_path, refcat_or_status)
                if status == 0:
                    # Update WCS in FITS file with the results from the SCAMP fit
                    status, fits_file_output = self.update_wcs(fits_file, ldac_catalog, out_path)
                    # Re-extract a new FITS-LDAC catalog from the updated frame
                    pipeline_cls = PipelineProcess.get_subclass('proc-extract')
                    extract_inputs = { 'fits_file' : fits_file_output,
                                       'configs_dir' : configs_dir,
                                       'datadir' : out_path,
                                       'desired_catalog' : desired_catalog
                                     }
                    self.log(f"Creating new FITS-LDAC catalog for {fits_file_output:}")
                    extract_pipe = pipeline_cls.create_timestamped(extract_inputs)
                    send_task(run_pipeline, extract_pipe, 'proc-extract')
                    # XXX How do we wait until the above finishes ?
                    new_ldac_catalog = fits_file_output.replace('e92', 'e92_ldac')
                    logger.debug(f"Filename after 2nd SExtractor= {new_ldac_catalog:}")
                    # if status != 0:
                        # logger.error("Execution of second SExtractor failed")
                        # return -4, 0

                    # # Reset DB connection after potentially long-running process.
                    # XXX Can we do this here ? Will it break the Dramatiq process?
                    # reset_database_connection()
                    fits_header, junk_table, cattype = open_fits_catalog(fits_file, header_only=True)
                    try:
                        header = get_catalog_header(fits_header, cattype)
                    except FITSHdrException as e:
                        logger.error(f"Bad header for {fits_file:} ({e:})")
                        self.log(f"Bad header for {fits_file:} ({e:})")
                        return -1

                    # # Find Block for original frame
                    block = find_block_for_frame(fits_file)
                    if block is None:
                        logger.error(f"Could not find block for fits frame {fits_file:}")
                        self.log(f"Could not find block for fits frame {fits_file:}")
                        return -3

                    # # Check if we have a sitecode (none if this is a new instrument/telescope)
                    if header.get('site_code', None) is None:
                        logger.error(f"No sitecode found for fits frame {fits_file:}")
                        self.log(f"No sitecode found for fits frame {fits_file:}")
                        return -5

                    # # Create a new Frame entry for the new_ldac_catalog (e92_ldac.fits)
                    num_new_frames_created = make_new_catalog_entry(new_ldac_catalog, header, block)

        except NeoException as ex:
            logger.error('Error with astrometric fit: {}'.format(ex))
            self.log('Error with astrometric fit: {}'.format(ex))
            raise AsyncError('Error performing astrometric fit')
        except TimeLimitExceeded:
            raise AsyncError("Astrometric fit took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return

    def setup(self, catfile, dest_dir, desired_catalog):

        # Open catalog, get header and check fit status
        fits_header, junk_table, cattype = open_fits_catalog(catfile, header_only=True)
        try:
            header = get_catalog_header(fits_header, cattype)
        except FITSHdrException as e:
            logger.error("Bad header for %s (%s)" % (catfile, e))
            return -1

        refcat, num_ref_srcs = get_reference_catalog(dest_dir, header['field_center_ra'],
            header['field_center_dec'], header['field_width'], header['field_height'],
            cat_name=desired_catalog)
        if refcat is None or num_ref_srcs is None:
            logger.error(f"Could not obtain reference catalog for fits frame {catfile:}")
            return -6

        return refcat

    def process(self, new_ldac_catalog, configs_dir, dest_dir, refcat):

        scamp_status = run_scamp(configs_dir, dest_dir, new_ldac_catalog, refcatalog=refcat)
        self.log(f"Return status for scamp: {scamp_status:}")
        logger.info("Return status for scamp: {}".format(scamp_status))
        if scamp_status != 0:
            logger.error("Execution of Scamp failed")
            self.log("Execution of Scamp failed")
        return scamp_status

    def update_wcs(self, fits_file, new_ldac_catalog, dest_dir):
        """Update the WCS information in <fits_file> using the information
        from the SCAMP output in the <new_ldac_catalog>.head and 'scamp.xml'
        files inside <dest_dir>"""

        scamp_file = os.path.basename(new_ldac_catalog).replace('.fits', '.head' )
        scamp_file = os.path.join(dest_dir, scamp_file)
        scamp_xml_file = os.path.basename(new_ldac_catalog).replace('.fits', '.xml' )
        scamp_xml_file = os.path.join(dest_dir, scamp_xml_file)
        # Update WCS in image file
        # Strip off now unneeded FITS extension
        fits_file = fits_file.replace('[SCI]', '')
        # Get new output filename
        fits_file_output = increment_red_level(fits_file)
        fits_file_output = os.path.join(dest_dir, fits_file_output.replace('[SCI]', ''))
        logger.info(f"Updating refitted WCS in image file: {fits_file:}. Output to: {fits_file_output:}")
        self.log(f"Updating refitted WCS in image file: {fits_file:}. Output to: {fits_file_output:}")
        status, new_header = updateFITSWCS(fits_file, scamp_file, scamp_xml_file, fits_file_output)
        logger.info(f"Return status for updateFITSWCS: {status:}")
        self.log(f"Return status for updateFITSWCS: {status:}")
        return status, fits_file_output

class ZeropointProcessPipeline(PipelineProcess):
    """
    Determine zeropoint for a frame
    """
    short_name = 'zp'
    long_name = 'Determine zeropoint for a frame'
    inputs = {
        'ldac_catalog': {
            'default': None,
            'long_name': 'Filepath to source catalog to process'
        },
        'catalog_type': {
            'default': 'BANZAI_LDAC',
            'long_name': 'Type of source catalog'
        },
        'zeropoint_tolerance':{
            'default': 0.1,
            'long_name' : 'Standard deviation of zeropoint acceptable for good fit'
        },
        'desired_catalog' : {
            'default' : 'PS1',
            'long_name' : 'Type of photometric catalog desired'
        },
        'new_method' : {
            'default' : True,
            'long_name' : 'Whether to use the new ZP method via calviacat'
        }
    }

    class Meta:
        proxy = True

    def do_pipeline(self, tmpdir, **inputs):

        catfile = inputs.get('ldac_catalog')
        catalog_type = inputs.get('catalog_type')
        phot_cat_name = inputs.get('desired_catalog')
        std_zeropoint_tolerance = inputs.get('zeropoint_tolerance')

        try:

            num_in_table = 0
            num_sources_created = 0
            avg_zeropoint = None
            C = None
            std_zeropoint = None
            color_const = False

            header, table, refcat = self.setup(catfile, catalog_type, phot_cat_name)

            if header and table and refcat:
                cal_filter = map_filter_to_calfilter(header['filter'])
                if cal_filter is None:
                    logger.error(f"This filter ({header['filter']}) is not calibrateable")
                    return
                # Cross match with reference catalog and compute zeropoint
                logger.info(f"Calibrating {header['filter']} instrumental mags. with {cal_filter} using {phot_cat_name}")
                avg_zeropoint, std_zeropoint, C, cal_color = self.cross_match_and_zp(table, refcat, std_zeropoint_tolerance, cal_filter, header['filter'], color_const)
                logger.info(f"New zp={avg_zeropoint:} +/- {std_zeropoint:} {C:}")
                self.log(f"New zp={avg_zeropoint:} +/- {std_zeropoint:} {C:}")

                # if crossmatch is good, update new zeropoint
                if std_zeropoint < std_zeropoint_tolerance:
                    logger.debug("Got good zeropoint - updating header")
                    header['color_used'] = cal_color
                    header['color'] = -99
                    header['color_err'] = 0.00
                    if color_const is False:
                        header['color'] = C
                        header['color_err'] = -99
                    logger.debug("Calling update_zeropoint")
                    header, table = update_zeropoint(header, table, avg_zeropoint, std_zeropoint, include_zperr=False)

                    # get the fits filename from the catfile in order to get the Block from the Frame
                    if 'e91_ldac.fits' in os.path.basename(catfile):
                        fits_file = os.path.basename(catfile.replace('e91_ldac.fits', 'e91.fits'))
                    elif 'e92_ldac.fits' in os.path.basename(catfile):
                        fits_file = os.path.basename(catfile.replace('e92_ldac.fits', 'e92.fits'))
                    else:
                        fits_file = os.path.basename(catfile)

                    fits_filepath = os.path.join(os.path.dirname(catfile), fits_file)

                    # update the zeropoint computed above in a new Frame entry for the e92 frame
                    ast_cat_name = 'GAIA-DR2'
                    logger.debug("Calling update_frame_zeropoint")
                    frame = update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filename=fits_file, frame_type=Frame.NEOX_RED_FRAMETYPE)

                    # Write updated photometric calibration keywords to FITS header of e92.fits file
                    logger.debug("Calling updateFITScalib")
                    status, new_fits_header = updateFITScalib(header, fits_filepath, "BANZAI")

                    # update the zeropoint computed above in the CATALOG file Frame
                    logger.debug("Calling update_frame_zeropoint (2)")
                    frame_cat = update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filename=os.path.basename(catfile), frame_type=Frame.BANZAI_LDAC_CATALOG)

                    # store the CatalogSources
                    logger.debug("Calling get_or_create_CatalogSources")
                    num_sources_created, num_in_table = get_or_create_CatalogSources(table, frame, header)
                else:
                    logger.warning("Didn't get good zeropoint - not updating header")
                    self.log("Didn't get good zeropoint - not updating header")
            else:
                logger.warning(f"Could not open {catfile:}")
                self.log(f"Could not open {catfile:}")


        except NeoException as ex:
            logger.error('Error with zeropoint determination: {}'.format(ex))
            self.log('Error with zeropoint determination: {}'.format(ex))
            raise AsyncError('Error performing zeropoint determination')
        except TimeLimitExceeded:
            raise AsyncError("Zeropoint determination took longer than 10 mins to create")
        except PipelineProcess.DoesNotExist:
            raise AsyncError("Record has been deleted")
        self.log('Pipeline Completed')
        return

    def setup(self, catfile, catalog_type, phot_cat_name, max_records=None, match_limit=None, min_matches=None):
        """Open the catalog file <catfile> of type <catalog_type> and search
        for a calibration catalog that covers the pointing.
        Optionally [max_records], [match_limit] and [min_matches] can be passed
        in and will be passed onto the calviacat.Catalog constructor.
        The header, source table and calibration DB object are returned.
        """

        refcat = None

        filename = os.path.basename(catfile)
        datadir = os.path.join(os.path.dirname(catfile), '')

        header, table = extract_catalog(catfile, catalog_type)
        if header and table:
            db_filename = self.create_caldb_filename(datadir, header, phot_cat_name)

            kwargs = {}
            if max_records is not None:
                kwargs['max_records'] = max_records
            if match_limit is not None:
                kwargs['match_limit'] = match_limit
            if min_matches is not None:
                kwargs['min_matches'] = min_matches
            # Create or load calviacat catalog
            if phot_cat_name == 'PS1':
                refcat = cvc.PanSTARRS1(db_filename, **kwargs)
            elif phot_cat_name == 'REFCAT2':
                refcat = cvc.RefCat2(db_filename, **kwargs)
            elif phot_cat_name == 'GAIA-DR2':
                refcat = cvc.Gaia(db_filename, **kwargs)
            else:
                logger.error(f"Unknown reference catalog {phot_cat_name:}. Must be one of PS1, REFCAT2, GAIA-DR2")
        return header, table, refcat

    def create_caldb_filename(self, datadir, header, phot_cat_name, dbg=False):
        db_filename = existing_catalog_coverage(datadir, header['field_center_ra'], header['field_center_dec'], header['field_width'], header['field_height'], phot_cat_name, '*.db', dbg)
        created = False
        if db_filename is None:
            # Add 25% to passed width and height in lieu of actual calculation of extent
            # of a series of frames
            set_width = header['field_width']
            set_height = header['field_height']
            units = set_width[-1]
            try:
                ref_width = float(set_width[:-1]) * 1.25
                ref_width = "{:.1f}{}".format(ref_width, units)
            except ValueError:
                ref_width = set_width
            units = set_height[-1]
            try:
                ref_height = float(set_height[:-1]) * 1.25
                ref_height = "{:.1f}{}".format(ref_height, units)
            except ValueError:
                ref_height = set_height

            # Rewrite name of catalog to include position and size
            refcat_filename = "{}_{ra:.2f}{dec:+.2f}_{width}x{height}.db".format(phot_cat_name, ra=header['field_center_ra'], dec=header['field_center_dec'], width=ref_width, height=ref_height)
            db_filename = os.path.join(datadir, refcat_filename)
            created = True

        prefix = "Created" if created else "Retrieved"
        self.log("{prefix:} DB file {refcat_filename:}")
        return db_filename

    def cross_match_and_zp(self, table, refcat, std_zeropoint_tolerance, cal_filter, obs_filter, color_const=True):

        phot = table[table['flags'] == 0]  # clean LCO catalog
        lco = coord.SkyCoord(phot['obs_ra'], phot['obs_dec'], unit='deg')

        if len(refcat.search(lco)[0]) < 500:
            start = time.time()
            refcat.fetch_field(lco)
            end = time.time()
            logger.debug(f"TIME: refcat.fetch_field took {end-start:.1f} seconds")

        start = time.time()
        retstatus = refcat.xmatch(lco)
        if retstatus is not None:
            objids, distances = retstatus
        else:
            logger.warning("Crossmatching failed")
            return None, None, None, None
        end = time.time()
        logger.debug(f"TIME: cvc cross_match took {end-start:.1f} seconds")

        # cross_match can be a very slow process which can cause
        # the DB connection to time out. If we reset and explicitly close the
        # connection, Django will auto-reconnect.
        reset_database_connection()

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message='divide by zero encountered')
            start = time.time()
            if color_const is True:
                avg_zeropoint, C, std_zeropoint, r, gmi = refcat.cal_constant(objids, phot['obs_mag'], cal_filter)
                cal_color = 'g-i' # Fixed/held constant
            else:
                cal_color = 'g-' + cal_filter
                gmi_limits = [0.2, 3.0]
                if obs_filter == 'w':
                    gmi_limits = [0.5, 1.5]
                avg_zeropoint, C, std_zeropoint, r, gmr, gmi = refcat.cal_color(objids, phot['obs_mag'], cal_filter, cal_color, gmi_lim=gmi_limits)
            end = time.time()
        logger.debug(f"TIME: compute_zeropoint took {end-start:.1f} seconds")
        logger.debug(f"New zp={avg_zeropoint:} +/- {std_zeropoint:} {r.count():} {C:}")

        return avg_zeropoint, std_zeropoint, C, cal_color
