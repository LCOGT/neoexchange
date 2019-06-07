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

from core.models import Block, PanoptesReport
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from core.zoo import download_images_block, create_panoptes_report, reorder_candidates
from core.archive_subs import archive_lookup_images
from core.frames import find_images_for_block
from django.conf import settings
import logging
import tempfile
import shutil

logger = logging.getLogger('neox')

class Command(BaseCommand):
    help = 'Send Blocks which recently got data to Zooniverse'

    def add_arguments(self, parser):
        parser.add_argument(
            '-b',
            dest='blockid',
            default=False,
            help='Block ID to update',
        )
        parser.add_argument(
            '-d',
            dest='download_dir',
            default=False,
            help='Where to download the images',
        )

    def handle(self, *args, **options):
        blocks = Block.objects.filter(active=True, block_start__lte=datetime.now(), block_end__gte=datetime.now())
        download_dir = options['download_dir']
        if options['blockid']:
            blocks = blocks.filter(pk=options['blockid'])
        logger.debug("==== %s x Zoo blocks %s ====" % (blocks.count(), datetime.now().strftime('%Y-%m-%d %H:%M')))
        for block in blocks:
            if PanoptesReport.objects.filter(block=block):
                logger.debug("Block {} already pushed to Zooniverse".format(block))
                continue
            files = None
            cand_per_image = None
            logger.debug("Finding thumbnails for Block {}".format(block.id))
            try:
                image_list, candidates, xmax, ymax = find_images_for_block(block.id)
            except TypeError:
                logger.debug("Problem encountered")
                continue
            images = archive_lookup_images(image_list)
            if images:
                scale = xmax/1920.
            else:
                logger.debug('Block {} had no images'.format(block))
                continue
            if not download_dir:
                download_dir = tempfile.mkdtemp()
            files = download_images_block(block.id, images,  scale, download_dir)
            if files:
                subject_ids = panoptes_add_set(files, num_segments=9, blockid=block.id, download_dir=download_dir, workflow=workflow)
                if subject_ids:
                    create_panoptes_report(block, subject_ids)
                if not options['download_dir']:
                    shutil.rmtree(download_dir)
            else:
                logger.debug('Failed to download images')
