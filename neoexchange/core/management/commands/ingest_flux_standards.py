from core.models import CalibSource
from django.core.management.base import BaseCommand, CommandError
from astrometrics.sources_subs import fetch_flux_standards
from datetime import datetime

class Command(BaseCommand):
    help = "Ingest the list of ESO Spectrophotometric standards"

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching ESO spectrophotometric standards %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        flux_standards = fetch_flux_standards()
        num_created = 0
        for standard in flux_standards:
            
            params = {
                        'name' : standard,
                        'ra'  : flux_standards[standard]['ra_rad'],
                        'dec' : flux_standards[standard]['dec_rad'],
                        'vmag' : flux_standards[standard]['mag'],
                        'spectral_type' : flux_standards[standard]['spec_type'],
                        'source_type' : CalibSource.FLUX_STANDARD,
                        'notes' : flux_standards[standard]['notes']
                     }
            calib_source, created = CalibSource.objects.get_or_create(**params)
            if created:
                num_created += 1
        self.stdout.write("=== Created {} new flux standards".format(num_created))
