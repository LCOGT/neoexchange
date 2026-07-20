


####management command wrapper for aperture photometry code: core/management/commands/pipeline_psf_photometry.py

###WILL be placed as: core/management/commands/pipeline_aper_photometry.py 
from django.core.management.base import BaseCommand, CommandParser, CommandError


from core.views import perform_aper_photometry
from core.models.blocks import Block

from datetime import datetime
import os

class Command(BaseCommand):

    help = """Perform aperture photometry on a set of processed FITS frames."""

    def add_arguments(self, parser: CommandParser) -> None:
        default_path = os.path.join(os.path.sep, 'apophis', 'eng', 'rocks')

        parser.add_argument('datadir', action="store", default=default_path, help='Path for processed data (e.g. %(default)s)')
        parser.add_argument('block',type = int, action = "store", help = "Block number of Observation")
        parser.add_argument("aperture_radius",type = float, action = "store", help ="Define aperture radius for photometry")
        parser.add_argument("--account_zps", action = "store_true",default = False, help ="Account for zero point corrections")


    def handle(self, *args, **options):
        try:
            block = Block.objects.get(id = options['block'])
        except Block.DoesNotExist:
            raise CommandError( f"Block {options['block']} does not exist.")

        self.stdout.write("==== Pipeline processing Aperture photometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        
        results = perform_aper_photometry(block, options['datadir'], options['account_zps'], options['aperture_radius'])
        






#Input from USER
# ---block request number
#THEN: use Block.objects.get() to get the block to perform aper_photmetry
#--look at make_subtractions.py to get an idea of how to do this

#---look at other maganement command codes to see how to handle boolean inputs/options: ex: account_zps flag
#--look at other commands to see how to set value for aperture radius




#END goal: BASH
#    python manage.py pipeline_aper_photometry [block requestnumber] [default_path / Hera / [date]/] 
#command will pass info to perform_aper_photometry for the results | DONT put any code after results then!!