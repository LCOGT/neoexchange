from astrometrics.sources_subs import fetch_NEOCP, parse_NEOCP
from core.views import update_NEOCP_orbit

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime

class Command(BaseCommand):
    help = 'Check NEOCP for objects in need of follow up'

    def handle(self, *args, **options):
        self.stdout.write("==== Fetching NEOCP targets %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        neocp_page = fetch_NEOCP()
        obj_ids = parse_NEOCP(neocp_page)
        self.stdout.write("==== Found %s NEOCP targets ====" % len(obj_ids))
        for obj_id in obj_ids:
            self.stdout.write("Reading NEOCP target %s" % obj_id)
            resp = update_NEOCP_orbit(str(obj_id))
            if resp:
                self.stdout.write(resp)
            
