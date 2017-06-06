from core.models import Block
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from core.zoo import download_images_block, create_manifest_file, reorder_candidates, push_set_to_panoptes
from core.archive_subs import archive_lookup_images
from core.frames import find_images_for_block
from django.conf import settings
import logging
import tempfile
import shutil

logger = logging.getLogger('neox')

class Command(BaseCommand):
    help = 'Retrieve Zooniverse classifications and parse them'

    def handle(self, *args, **options):
