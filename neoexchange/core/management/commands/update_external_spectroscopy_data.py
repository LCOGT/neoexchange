from astrometrics.sources_subs import fetch_manos_targets, fetch_smass_targets
from core.views import update_previous_spectra

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime

class Command(BaseCommand):
    help = 'Pull in external spectroscopy for Characterization Targets'

    def handle(self, *args, **options):
        self.stdout.write("==== Searching MANOS Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        new_manos_data = fetch_manos_targets()
        for m_datum in new_manos_data:
            resp = update_previous_spectra(m_datum,'M',dbg=False)
            if resp:
                msg = "New MANOS data found for %s" % m_datum[0]
                self.stdout.write(msg)
        self.stdout.write("==== Searching SMASS Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        new_smass_data = fetch_smass_targets()
        for s_datum in new_smass_data:
            resp = update_previous_spectra(s_datum,'S',dbg=False)
            if resp:
                msg = "New SMASS data found for %s" % datum[0]
                self.stdout.write(msg)
