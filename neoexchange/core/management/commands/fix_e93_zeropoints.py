import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from core.models import Block
from core.views import sync_e93_calibration


class Command(BaseCommand):

    help = """Repair the photometric calibration of a Block's e93 difference images, made before the
    e92 calibration was copied into them (Hera zeropoint analysis, Fix 8): for each e93 Frame the
    zeropoint, its error and source, the colour terms and the photometric catalog are copied from the
    e92 Frame into the e93 Frame, the e93 FITS and its .rms.fits, and the zeropoint aperture radius
    (L1ZPAPER) is written into the e93 files, the e92 FITS and the e92 LDAC catalog if they lack it.
    e92 frames without a NEOx zeropoint are reported and left alone."""

    def add_arguments(self, parser):
        parser.add_argument('datadir', action="store", help='Directory holding the Block\'s e92/e93 FITS files and LDAC catalogs')
        parser.add_argument('--block', type=int, required=True, help='Block ID to repair')
        parser.add_argument('--dry-run', action="store_true", default=False, help='Report what would change without writing to the files or the database')

    def handle(self, *args, **options):
        try:
            block = Block.objects.get(id=options['block'])
        except Block.DoesNotExist:
            raise CommandError(f"Block ID {options['block']} does not exist.")
        datadir = options['datadir']
        if not os.path.isdir(datadir):
            raise CommandError(f"{datadir} is not a directory")

        prefix = '(dry-run) ' if options['dry_run'] else ''
        now_string = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
        self.stdout.write(f"==== {prefix}Repairing e93 calibration for Block {block.id} (ReqNum {block.request_number}) from {datadir} {now_string} ====")

        results = sync_e93_calibration(block, datadir, dry_run=options['dry_run'])
        if len(results) == 0:
            self.stdout.write(f"No e93 Frames found for Block {block.id}")
            return

        for result in results:
            if result['status'] == 'ok':
                line = (f"{result['e93']}: L1ZP {result['old_zeropoint']} -> {result['new_zeropoint']} ({result['zeropoint_src']}), "
                        f"L1ZPAPER {result['zp_aperture_pix']} px; files: {', '.join(result['files_updated']) or 'none'}")
            else:
                line = f"{result['e93']}: NOT REPAIRED ({result['status']})"
            for message in result['messages']:
                line += f"\n    {message}"
            self.stdout.write(line)

        num_ok = sum(1 for result in results if result['status'] == 'ok')
        summary = f"{prefix}{num_ok} of {len(results)} e93 Frames repaired"
        if num_ok == len(results):
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            problems = sorted({result['status'] for result in results if result['status'] != 'ok'})
            self.stdout.write(self.style.WARNING(f"{summary}; problems: {', '.join(problems)}"))
