from astrometrics.sources_subs import fetch_manos_targets, fetch_smass_targets
from core.views import update_previous_spectra

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime


class Command(BaseCommand):
    help = 'Pull in external spectroscopy for Characterization Targets'

    def add_arguments(self, parser):
        parser.add_argument('-a', '--all', action="store_true", help='Download ALL SMASS data. Default: Grab data from the current year.')

    def handle(self, *args, **options):
        # # MANOS page moved, and is a mess... Much more work to get this working again...
        # self.stdout.write("==== Searching MANOS Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        # new_manos_data = fetch_manos_targets()
        # for m_datum in new_manos_data:
        #     resp = update_previous_spectra(m_datum, 'M', dbg=False)
        #     if resp:
        #         msg = "New MANOS data found for %s" % m_datum[0]
        #         self.stdout.write(msg)
        self.stdout.write("==== Searching SMASS Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        new_smass_data = fetch_smass_targets(None, options['all'])
        for s_datum in new_smass_data:
            resp = update_previous_spectra(s_datum, 'S', dbg=False)
            if resp:
                msg = "New SMASS data found for %s" % s_datum[0]
                self.stdout.write(msg)
