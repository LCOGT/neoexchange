from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from astrometrics.sources_subs import fetch_yarkovsky_targets, random_delay
from core.views import update_MPC_orbit


class Command(BaseCommand):
    help = 'Fetch Yarkovsky target list for the current month'

    def add_arguments(self, parser):
        parser.add_argument('yark_targets', nargs='+', help='List of Yarkovsky targets to ingest')

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching Yarkovsky targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        yark_targets = fetch_yarkovsky_targets(options['yark_targets'])
        for obj_id in yark_targets:
            self.stdout.write("Reading Yarkovsky target %s" % obj_id)
            update_MPC_orbit(obj_id, origin='Y')
            # Wait between 10 and 20 seconds
            delay = random_delay(10, 20)
            self.stdout.write("Slept for %d seconds" % delay)
