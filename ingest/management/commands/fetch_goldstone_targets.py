from ingest.sources_subs import fetch_goldstone_targets
from ingest.views import update_MPC_orbit
from ingest.models import *

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = ''
    help = 'Fetch Goldstone target list for the current year'

    def handle(self, *args, **options):
        logger.info("==== %s ====" % 'Fetching Goldstone targets')
        logger.info("==== %s ====" % datetime.now())
        radar_targets = fetch_goldstone_targets()
        for obj_id in radar_targets:
            logger.info("Adding %s to DB" % obj_id)
            update_MPC_orbit(obj_id)
