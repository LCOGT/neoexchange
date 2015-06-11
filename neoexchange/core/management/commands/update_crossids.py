from astrometrics.sources_subs import fetch_previous_NEOCP_desigs
from core.views import update_crossids
from core.models import *

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = ''
    help = 'Update objects for new cross-identifications from the Previous NEO Confirmation Page Objects page'

    def handle(self, *args, **options):
        logger.info("==== %s ====" % datetime.now())
        objects = fetch_previous_NEOCP_desigs()
        for obj_id in objects:
            update_crossids(obj_id, dbg=False)
