from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from core.models import StaticSource
from astrometrics.sources_subs import fetch_flux_standards
from core.views import create_calib_sources

class Command(BaseCommand):
    help = "Ingest the list of ESO Spectrophotometric standards"

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching ESO spectrophotometric standards %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        flux_standards = fetch_flux_standards()
        num_created = create_calib_sources(flux_standards)
        self.stdout.write("=== Created {} new flux standards".format(num_created))
