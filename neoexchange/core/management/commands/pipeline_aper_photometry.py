
####management command wrapper for aperture photometry code: core/management/commands/pipeline_psf_photometry.py


import os
from datetime import datetime

from astropy.table import Table
from astropy.time import Time
from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.models.blocks import Block
from core.utils import NeoException
from core.views import perform_aper_photometry
from photometrics.external_codes import aperture_radius_label


class Command(BaseCommand):

    help = """Perform aperture photometry on a set of processed FITS frames."""

    def add_arguments(self, parser: CommandParser) -> None:
        default_path = os.path.join(os.path.sep, 'apophis', 'eng', 'rocks')

        parser.add_argument('datadir', action="store", default=default_path, help='Path for processed data (e.g. %(default)s)')
        parser.add_argument("radius_pix", type=float, nargs='?', default=None, help="Aperture radius in PIXELS. If omitted, each frame is measured with the aperture its zeropoint was fitted with (L1ZPAPER header keyword, written by proc-zeropoint). The equivalent in arcsec, from each frame's WCS pixel scale, is recorded alongside it in the output")
        parser.add_argument('--block',type = int, action = "store", help = "Block number of Observation")
        parser.add_argument("--groupid", type = int, default = None, help ="LCO group ID associated with the block")
        parser.add_argument("--request_number",type=int,default=None,help="LCO request number associated with the block")
        parser.add_argument("--account_zps", action = "store_true",default = False, help ="Account for zero point corrections")
        parser.add_argument("--output_dir", default = os.getcwd(), help = "Output directory for Astropy table")
        parser.add_argument("--output",default=None,help="Output ECSV filename")

    def handle(self, *args, **options):

        block = None

        if options['block'] is not None:
            try:
                block = Block.objects.get(id = options['block'])
            except Block.DoesNotExist:
                raise CommandError(f"Block ID {options['block']} does not exist.")

            #block and group id match sanity check
            if options['groupid'] is not None and block.groupid != options['groupid']:
                raise CommandError( f" Block {block.id} has groupid {block.groupid},"
                                    f" not {options['groupid']}")

        elif options['groupid'] is not None:
            try:
                block = Block.objects.get(superblock__groupid = options['groupid'])
            except Block.DoesNotExist:
                raise CommandError( f"Block id {options['groupid']} does not exist.")

        elif options['request_number'] is not None:
            try:
                block = Block.objects.get(request_number=options['request_number'])
            except Block.DoesNotExist:
                raise CommandError(
                    f"Request number {options['request_number']} does not exist.")

            #Sanity check on requst number database
            if options['request_number'] is not None and int(block.request_number) != options['request_number']:
                raise CommandError(
                    f"Block {block.id} has request number {block.request_number}, "
                    f"not {options['request_number']}")

        else:
            raise CommandError(" Must provide either --block or --groupid.")

        time_now = datetime.now().strftime('%Y-%m-%d %H:%M')
        self.stdout.write(f"==== Pipeline processing Aperture photometry {time_now} ====")


        radius_pix = options['radius_pix']
        if radius_pix is None:
            self.stdout.write("Aperture radius: each frame's zeropoint aperture (L1ZPAPER)")
        else:
            self.stdout.write(f"Aperture radius: {radius_pix} pixels")
        try:
            results = perform_aper_photometry(block, options['datadir'], options['account_zps'], aperture_radius_pix=radius_pix)
        except NeoException as e:
            raise CommandError(str(e))
        self.stdout.write(f"returned object: {type(results)}") 
        self.stdout.write(f"Returned value: {results}")

        if isinstance(results, Table):
            radii_pix = [r for r in results['aperture radius pix'] if r != ""]
            radii_arcsec = [r for r in results['aperture radius arcsec'] if r != ""]
            if radii_arcsec:
                self.stdout.write(f"Aperture radius {min(radii_pix):.3f}-{max(radii_pix):.3f} px = {min(radii_arcsec):.3f}-{max(radii_arcsec):.3f} arcsec on these frames")

            if options['output'] is None:
                filename = f"aper_photometry_{block.id}_r{aperture_radius_label(radius_pix)}.ecsv"
            else:
                filename = options['output']
            output = os.path.join(options['output_dir'], filename)

            if "times" in results.colnames:
                results["times"] = Time(results["times"])  #change datetime.datetime ---> Astropy.Time objects

            for name in results.colnames:
                print(name, type(results[name][0]))

            results.write(output, format = "ascii.ecsv", overwrite = True)

            self.stdout.write(self.style.SUCCESS(f"Wrote Astropy Table object to {output}"))

            if len(results.columns) >0:
                self.stdout.write("Table contains data.")
            else:
                self.stdout.write("Table has no columns.")

#END goal: BASH
#  python manage.py pipeline_aper_photometry [block requestnumber] [default_path / Hera / [date]/] 
