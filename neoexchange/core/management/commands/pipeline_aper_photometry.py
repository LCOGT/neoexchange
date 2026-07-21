
####management command wrapper for aperture photometry code: core/management/commands/pipeline_psf_photometry.py


from django.core.management.base import BaseCommand, CommandParser, CommandError


from core.views import perform_aper_photometry
from core.models.blocks import Block
from astropy.table import Table

from datetime import datetime
from astropy.time import Time
import os

class Command(BaseCommand):

    help = """Perform aperture photometry on a set of processed FITS frames."""

    def add_arguments(self, parser: CommandParser) -> None:
        default_path = os.path.join(os.path.sep, 'apophis', 'eng', 'rocks')

        parser.add_argument('datadir', action="store", default=default_path, help='Path for processed data (e.g. %(default)s)')
        parser.add_argument('block',type = int, action = "store", help = "Block number of Observation")
        parser.add_argument("aperture_radius",type = float, action = "store", help ="Define aperture radius for photometry")
        parser.add_argument("--account_zps", action = "store_true",default = False, help ="Account for zero point corrections")
        parser.add_argument("--output_dir", default = os.getcwd(), help = "Output directory for Astropy table")
        parser.add_argument("--output",default=None,help="Output ECSV filename")

    def handle(self, *args, **options):
        try:
            block = Block.objects.get(id = options['block'])
        except Block.DoesNotExist:
            raise CommandError( f"Block {options['block']} does not exist.")

        self.stdout.write("==== Pipeline processing Aperture photometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        
        results = perform_aper_photometry(block, options['datadir'], options['account_zps'], options['aperture_radius'])
        self.stdout.write(f"returned object: {type(results)}") 
        self.stdout.write(f"Returned value: {results}")

        if isinstance(results, Table):
            
            if options['output'] is None:
                filename = f"aper_photometry_{options['block']}.ecsv"
            else:
                filename = options['output']
            output = os.path.join(options['output_dir'], filename)
            
            if "times" in results.colnames:
                results["times"] = Time(results["times"])  #change datetime.datetime ---> Astropy.Time objects

            for name in results.colnames:
                print(name, type(results[name][0]))
            
            results.write(output, format = "ascii.ecsv")

            self.stdout.write(self.style.SUCCESS(f"Wrtote Astropy Table object to {output}"))
        
            if len(results.columns) >0:
                self.stdout.write("Table contains data.")
            else:
                self.stdout.write("Table has no columns.")

#END goal: BASH
#  python manage.py pipeline_aper_photometry [block requestnumber] [default_path / Hera / [date]/] 
