"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime, timedelta
import logging
import tempfile
import shutil
import os
import glob

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from fits2image.conversions import fits_to_jpg

from core.models import Block, PanoptesReport
from core.zoo import download_images_block, make_cutouts, panoptes_add_set_mtd, create_panoptes_report
from core.archive_subs import archive_lookup_images, download_files
from core.frames import find_images_for_block, fetch_observations

logger = logging.getLogger('neox')

class Command(BaseCommand):
    help = 'Parse Zooniverse classificiation report'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            dest='filename',
            default=False,
            help='Local path and filename of Panoptes classification report',
        )


    def handle(self, *args, **options):
        filename = options['filename']
        read_classification_report(filename)
