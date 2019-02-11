"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

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
        pass
