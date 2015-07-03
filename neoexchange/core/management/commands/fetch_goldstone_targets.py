from astrometrics.sources_subs import fetch_goldstone_targets
from core.views import update_MPC_orbit

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime

class Command(BaseCommand):
    help = 'Fetch Goldstone target list for the current year'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching Goldstone targets ====")
        radar_targets = fetch_goldstone_targets()
        for obj_id in radar_targets:
            self.stdout.write("Reading Goldstone target %s" % obj_id)
            update_MPC_orbit(obj_id, origin='G')
