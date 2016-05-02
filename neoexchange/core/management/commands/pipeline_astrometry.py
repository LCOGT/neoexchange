import os
from datetime import datetime
from glob import glob
from sys import exit
import tempfile

from django.core.management.base import BaseCommand, CommandError

from core.views import check_catalog_and_refit
from photometrics.catalog_subs import store_catalog_sources
#from core.models import CatalogSources

class Command(BaseCommand):

    help = 'Do All The Things'

    def add_arguments(self, parser):
        parser.add_argument('datadir', help='Path to the data to ingest')
        parser.add_argument('--keep-temp-dir', action="store_true", help='Whether to remove the temporary dir')

    def determine_images_and_catalogs(self, datadir, output=True):

        fits_files, fits_catalogs = None, None

        if os.path.exists(datadir) and os.path.isdir(datadir):
            fits_files = glob(datadir + '*e??.fits')
            fits_catalogs = glob(datadir + '*e??_cat.fits')
            if len(fits_files) == 0 and len(fits_catalogs) == 0:
                self.stdout.write("No FITS files and catalogs found in directory %s" % datadir)
                fits_files, fits_catalogs = None, None
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

        temp_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')
        keep_temp = ''
        if options['keep_temp_dir']: keep_temp = ' (will keep)'
        self.stdout.write("Using %s as temp dir%s" % (temp_dir, keep_temp ))

        configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))
        for catalog in fits_catalogs:
            # Step 1: Determine if astrometric fit in catalog is good and
            # if not, refit using SExtractor and SCAMP.
            self.stdout.write("Processing %s" % catalog)
            new_catalog_or_status = check_catalog_and_refit(configs_dir, temp_dir, catalog)
            new_catalog = new_catalog_or_status
            if str(new_catalog_or_status).isdigit():
                if new_catalog_or_status != 0:
                    self.stdout.write("Error reprocessing %s (Error code= %s" % (catalog, new_catalog_or_status))
                    exit(-3)
                new_catalog = catalog

            # Step 2: Check for good zeropoint and redetermine if needed. Ingest
            # results into CatalogSources
            self.stdout.write("Creating CatalogSources from %s" % new_catalog)
            num_sources_created, num_in_catalog = store_catalog_sources(new_catalog)

            # Step 3: Synthesize MTDLINK-compatible SExtractor .sext ASCII catalogs
            # from CatalogSources

            # Step 4: Run MTDLINK to find moving objects

            # Step 5: Read MTDLINK output file and create candidates in NEOexchange

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
