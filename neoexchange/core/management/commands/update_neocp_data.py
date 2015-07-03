from astrometrics.sources_subs import fetch_NEOCP
from core.views import update_NEOCP_orbit

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime

class Command(BaseCommand):
    help = 'Check NEOCP for objects in need of follow up'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching NEOCP targets ====")
        objects = fetch_NEOCP()
        self.stdout.write("==== Found %s NEOCP targets ====" % len(objects))
        for obj_id in objects:
            self.stdout.write("Reading NEOCP target %s" % obj_id)
            resp = update_NEOCP_orbit(str(obj_id))
            
