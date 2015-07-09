from astrometrics.sources_subs import fetch_previous_NEOCP_desigs
from core.views import update_crossids

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime

class Command(BaseCommand):
    help = 'Update objects for new cross-identifications from the Previous NEO Confirmation Page Objects page'

    def handle(self, *args, **options):
        self.stdout.write("==== %s ====" % datetime.now())
        objects = fetch_previous_NEOCP_desigs()
        for obj_id in objects:
            resp = update_crossids(obj_id, dbg=False)
            if resp:
                msg = "Updated crossid for %s" % obj_id
                self.stdout.write(msg)
