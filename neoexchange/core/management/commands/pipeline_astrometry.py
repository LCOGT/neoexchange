import os
from datetime import datetime
from glob import glob
from sys import exit
import tempfile

from django.core.management.base import BaseCommand, CommandError

from core.views import check_catalog_and_refit
#from core.models import CatalogSources

class Command(BaseCommand):

    help = 'Do All The Things'

    def add_arguments(self, parser):
        parser.add_argument('datadir', help='Path to the data to ingest')
        parser.add_argument('--keep-temp-dir', action="store_true", help='Whether to remove the temporary dir')

    def handle(self, *args, **options):
        self.stdout.write("==== Pipeline processing astrometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        datadir = os.path.join(os.path.abspath(options['datadir']), '')
        self.stdout.write("datapath=%s" % (datadir))
        if os.path.exists(datadir) and os.path.isdir(datadir):
            fits_files = glob(datadir + '*e??.fits')
            fits_catalogs = glob(datadir + '*e??_cat.fits')
            if len(fits_files) == 0 and len(fits_catalogs) == 0:
                self.stdout.write("No FITS files and catalogs found in directory %s" % datadir)
                exit(-2)
            self.stdout.write("Found %d FITS files and %d catalogs" % ( len(fits_files), len(fits_catalogs)))

            temp_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')
            keep_temp = ''
            if options['keep_temp_dir']: keep_temp = ' (will keep)'
            self.stdout.write("Using %s as temp dir%s" % (temp_dir, keep_temp ))
            configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))
            for catalog in fits_catalogs:
                # Do stuff
                self.stdout.write("Processing %s" % catalog)
                check_catalog_and_refit(configs_dir, temp_dir, catalog)
  
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
        else:
            self.stdout.write("Could not open directory $s" % datadir)
            exit(-1)
