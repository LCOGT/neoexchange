from astrometrics.sources_subs import fetch_taxonomy_page
from core.views import update_taxonomy

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime

class Command(BaseCommand):
    help = 'Check Database for objects in need of Taxonomy update'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching Taxonomy Tables %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        new_tax_data = fetch_taxonomy_page()
        for tax_id in new_tax_data:
            resp = update_taxonomy(tax_id,dbg=False)
            if resp:
                msg = "Updated Taxonomy for %s" % tax_id[0]
                self.stdout.write(msg)
