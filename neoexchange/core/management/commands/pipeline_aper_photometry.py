
####management command wrapper for aperture photometry code: core/management/commands/pipeline_psf_photometry.py


import os
from datetime import datetime

import numpy as np
from astropy.table import Table
from astropy.time import Time
from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.models.blocks import Block
from core.models.dataproducts import DataProduct
from core.plots import plot_combined_lightcurve
from core.utils import NeoException, save_dataproduct
from core.views import perform_aper_photometry
from photometrics.external_codes import aperture_radius_label
from photometrics.lightcurve_subs import aper_table_to_dart_table, combine_simultaneous_bands, write_dartformat_file


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
        parser.add_argument("--from-table", dest='from_table', default=None, metavar='ECSV', help="Skip the photometry and read a previously written aperture photometry ECSV table instead (for re-running the multi-band combination)")
        parser.add_argument("--combine", dest='combine', action="store_true", default=None, help="Combine simultaneous bands into one lightcurve (default: when the table has more than one filter and zeropoints are applied)")
        parser.add_argument("--no-combine", dest='combine', action="store_false", help="Do not combine simultaneous bands")
        parser.add_argument("--ref-filter", dest='ref_filter', default='rp', help="Filter whose magnitude scale the combined lightcurve is on (default: %(default)s)")
        parser.add_argument("--taxonomy", default='S', help="Taxonomic class for the colour-offset priors: SOLAR, MEAN, S, C, Q, X, D, NEO (default: %(default)s)")
        parser.add_argument("--min-bands", dest='min_bands', type=int, default=1, help="Drop combined epochs with fewer than this many bands (default: %(default)s)")
        parser.add_argument("--overwrite", action="store_true", default=False, help="Replace existing DataProducts for the DART and plot files")

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

        os.makedirs(options['output_dir'], exist_ok=True)
        radius_pix = options['radius_pix']
        account_zps = options['account_zps']
        if options['from_table'] is not None:
            results = Table.read(options['from_table'], format="ascii.ecsv")
            self.stdout.write(f"Read {len(results)} rows from {options['from_table']}")
            if 'aperture radius pix' in results.colnames and len(results) > 0:
                # Recover the measurement settings the table was made with
                radii = [float(r) for r in results['aperture radius pix'] if r != ""]
                zp_radii = [float(r) for r in results['ZP aperture radius pix'] if r != ""]
                if radii and zp_radii and radii != zp_radii:
                    radius_pix = radii[0]
            account_zps = True
            output = options['from_table']
        else:
            if radius_pix is None:
                self.stdout.write("Aperture radius: each frame's zeropoint aperture (L1ZPAPER)")
            else:
                self.stdout.write(f"Aperture radius: {radius_pix} pixels")
            try:
                results = perform_aper_photometry(block, options['datadir'], account_zps, aperture_radius_pix=radius_pix)
            except NeoException as e:
                raise CommandError(str(e))
            self.stdout.write(f"returned object: {type(results)}")
            self.stdout.write(f"Returned value: {results}")

            if not isinstance(results, Table):
                return

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

            results.write(output, format = "ascii.ecsv", overwrite = True)

            self.stdout.write(self.style.SUCCESS(f"Wrote Astropy Table object to {output}"))

            if len(results.columns) > 0:
                self.stdout.write("Table contains data.")
            else:
                self.stdout.write("Table has no columns.")

        if len(results) == 0:
            return

        filters = [f for f in dict.fromkeys(str(f) for f in results['filters']) if f]
        base_name = os.path.join(options['output_dir'], f"aper_photometry_{block.id}_r{aperture_radius_label(radius_pix)}")

        # Per-filter "DART format" lightcurve files
        for obs_filter in filters:
            dart_table = aper_table_to_dart_table(results, obs_filter)
            if len(dart_table) == 0:
                continue
            dart_path = f"{base_name}_{obs_filter}_dart.txt"
            write_dartformat_file(dart_table, dart_path, aprad=float(dart_table['aprad'][0]), overwrite=True)
            save_dataproduct(block.superblock, dart_path, DataProduct.DART_TXT, force=options['overwrite'])
            self.stdout.write(f"Wrote {len(dart_table)} {obs_filter} points to {dart_path}")

        combine = options['combine']
        if combine is None:
            combine = len(filters) > 1 and account_zps
        if not combine:
            return
        if not account_zps:
            raise CommandError("Combining bands needs calibrated magnitudes; rerun with --account_zps")
        if options['ref_filter'] not in filters:
            raise CommandError(f"Reference filter {options['ref_filter']} not in table (filters: {', '.join(filters)})")

        combined, per_band, info = combine_simultaneous_bands(results, ref_filter=options['ref_filter'], taxonomy=options['taxonomy'],
                                                              min_bands=options['min_bands'])
        self.stdout.write(f"\nCombining {', '.join(filters)} onto the {options['ref_filter']} scale "
                          f"(matching window +/-{info['match_tolerance_s']:.0f} s, {info['num_rows_removed']} unusable rows dropped)")
        for obs_filter in filters:
            counts = info['counts'][obs_filter]
            prior = info['priors'].get(obs_filter)
            prior_str = f"prior {prior:+.3f}" if prior is not None else "no prior"
            flag = "  <-- differs from prior" if info['prior_mismatch'].get(obs_filter) else ""
            self.stdout.write(f"  {obs_filter:<3s} offset {info['offsets'][obs_filter]:+.3f} ({options['taxonomy']}-type {prior_str}); "
                              f"{counts['used']} used, {counts['flagged']} outliers, {counts['unmatched']} unmatched{flag}")
        for warning in info['warnings']:
            self.stdout.write(self.style.WARNING(f"  {warning}"))
        if len(combined) == 0:
            self.stdout.write(self.style.WARNING("No combined epochs produced"))
            return
        nbands_counts = np.bincount(combined['nbands'])
        nbands_str = ', '.join(f"{n} with {i} band{'s' if i != 1 else ''}" for i, n in enumerate(nbands_counts) if n)
        self.stdout.write(f"  {len(combined)} epochs ({nbands_str}); point-to-point scatter {info['p2p_scatter']:.4f} mag, "
                          f"median error {float(np.median(combined['sig'])):.4f} mag")

        combined_base = f"{base_name}_combined_{options['ref_filter']}"
        combined.write(f"{combined_base}.ecsv", format="ascii.ecsv", overwrite=True)
        dart_path = f"{combined_base}_dart.txt"
        write_dartformat_file(combined, dart_path, aprad=float(combined['aprad'][0]), overwrite=True)
        save_dataproduct(block.superblock, dart_path, DataProduct.DART_TXT, force=options['overwrite'])
        title = f"{block.body.current_name()}, Block {block.id}, {block.site} {str(block.block_start)[:10]}: {'+'.join(filters)} combined"
        plot_path = plot_combined_lightcurve(combined, per_band, title, f"{combined_base}.png", ref_filter=options['ref_filter'])
        save_dataproduct(block, plot_path, DataProduct.PNG_LIGHTCURVE_COMBINED_UNPHASED, force=options['overwrite'])
        self.stdout.write(self.style.SUCCESS(f"Wrote {combined_base}.ecsv, {dart_path} and {plot_path}"))

#END goal: BASH
#  python manage.py pipeline_aper_photometry [block requestnumber] [default_path / Hera / [date]/] 
