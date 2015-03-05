from ingest.sources_subs import fetch_NEOCP
from ingest.views import update_NEOCP_orbit
from ingest.models import *

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = ''
    help = 'Check NEOCP for objects in need of follow up'

    def handle(self, *args, **options):
        logger.info("==== %s ====" % datetime.now())
        objects = fetch_NEOCP()
        for obj_id in objects:
            update_NEOCP_orbit(obj_id)