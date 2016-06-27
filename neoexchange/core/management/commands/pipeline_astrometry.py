import os
from datetime import datetime
from glob import glob
from sys import exit
import tempfile

from django.core.management.base import BaseCommand, CommandError

from core.views import check_catalog_and_refit, store_detections
from photometrics.catalog_subs import store_catalog_sources, make_sext_file
from photometrics.external_codes import make_pa_rate_dict, run_mtdlink
#from core.models import CatalogSources

class Command(BaseCommand):

    help = 'Do All The Things'

    def add_arguments(self, parser):
        parser.add_argument('datadir', help='Path to the data to ingest')
        parser.add_argument('--keep-temp-dir', action="store_true", help='Whether to remove the temporary dir')
        parser.add_argument('--temp-dir', dest='temp_dir', action="store", help='Name of the temporary directory to use')
        parser.add_argument('--pa', action="store", help='Target angle of motion')
        parser.add_argument('--deltapa', action="store", help='Target angle of motion range')
        parser.add_argument('--minrate', action="store", help='Target minimum rate of motion (arcsec/min)')
        parser.add_argument('--maxrate', action="store", help='Target maximum rate of motion (arcsec/min)')

    def determine_images_and_catalogs(self, datadir, output=True):

        fits_files, fits_catalogs = None, None

        if os.path.exists(datadir) and os.path.isdir(datadir):
            fits_files = sorted(glob(datadir + '*e??.fits'))
            fits_catalogs = sorted(glob(datadir + '*e??_cat.fits'))
            if len(fits_files) == 0 and len(fits_catalogs) == 0:
                self.stdout.write("No FITS files and catalogs found in directory %s" % datadir)
                fits_files, fits_catalogs = None, None
            else:
                self.stdout.write("Found %d FITS files and %d catalogs" % ( len(fits_files), len(fits_catalogs)))
        else:
            self.stdout.write("Could not open directory $s" % datadir)
            fits_files, fits_catalogs = None, None

        return fits_files, fits_catalogs

    def handle(self, *args, **options):
        self.stdout.write("==== Pipeline processing astrometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        datadir = os.path.join(os.path.abspath(options['datadir']), '')
        self.stdout.write("datapath=%s" % (datadir))

        # Get lists of images and catalogs
        fits_files, fits_catalogs = self.determine_images_and_catalogs(datadir)
        if fits_files == None or fits_catalogs == None:
            exit(-2)

        # If a --temp_dir option was given on the command line use that as our
        # directory, otherwise create a random directory in /tmp
        if options['temp_dir']:
            temp_dir = options['temp_dir']
            if os.path.exists(temp_dir) == False:
                os.makedirs(temp_dir)
        else:
            temp_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')

        keep_temp = ''
        if options['keep_temp_dir']: keep_temp = ' (will keep)'
        self.stdout.write("Using %s as temp dir%s" % (temp_dir, keep_temp ))

        #create a new list of fits files to run mtdlink on
        fits_file_list = []

        configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))
        for catalog in fits_catalogs:
            # Step 1: Determine if astrometric fit in catalog is good and
            # if not, refit using SExtractor and SCAMP.
            self.stdout.write("Processing %s" % catalog)
            new_catalog_or_status, num_new_frames_created = check_catalog_and_refit(configs_dir, temp_dir, catalog)

            try:
                int(new_catalog_or_status)
                if new_catalog_or_status != 0:
                    self.stdout.write("Error reprocessing %s (Error code= %s)" % (catalog, new_catalog_or_status))
                    exit(-3)
                new_catalog = catalog
                catalog_type = 'LCOGT'
            except ValueError:
                new_catalog = new_catalog_or_status
                catalog_type = 'FITS_LDAC'

            # Step 2: Check for good zeropoint and redetermine if needed. Ingest
            # results into CatalogSources
            self.stdout.write("Creating CatalogSources from %s (Cat. type=%s)" % (new_catalog, catalog_type))
            num_sources_created, num_in_catalog = store_catalog_sources(new_catalog, catalog_type)

            # Step 3: Synthesize MTDLINK-compatible SExtractor .sext ASCII catalogs
            # from CatalogSources
            self.stdout.write("Creating .sext file(s) from %s" % (new_catalog))
            fits_filename = make_sext_file(temp_dir, new_catalog)

            fits_file_list.append(fits_filename)

        # Step 4: Run MTDLINK to find moving objects
        self.stdout.write("Running mtdlink on file(s) %s" % (fits_file_list))
        param_file = os.path.abspath(os.path.join('photometrics', 'configs', 'mtdi.lcogt.param'))
        #May change this to get pa and rate from compute_ephem later
        pa_rate_dict = make_pa_rate_dict(float(options['pa']), float(options['deltapa']), float(options['minrate']), float(options['maxrate']))

        retcode_or_cmdline = run_mtdlink(configs_dir, temp_dir, fits_file_list, len(fits_file_list), param_file, pa_rate_dict)

        # Step 5: Read MTDLINK output file and create candidates in NEOexchange
        if len(fits_file_list) > 0:
            mtds_file = os.path.join(temp_dir, fits_file_list[0].replace('.fits', '.mtds'))
            if os.path.exists(mtds_file):
                store_detections(mtds_file,dbg=False)
            else:
                self.stdout.write("Cannot find the MTDS output file  %s" % mtds_file)

        # Tidy up
        if options['keep_temp_dir'] != True:
            try:
                files_to_remove = glob(os.path.join(temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                self.stdout.write("Error removing files in temporary test directory %s" % temp_dir)
            try:
                os.rmdir(temp_dir)
            except OSError:
                 self.stdout.write("Error removing temporary test directory %s" % temp_dir)
