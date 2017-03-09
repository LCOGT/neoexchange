from core.models import Block
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from core.archive_subs import find_images_block, download_images_block
from django.conf import settings
import logging

logger = logging.getLogger('neox')

class Command(BaseCommand):
    help = 'Update pending blocks if observation requests have been made'

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
            default=settings.MEDIA_ROOT,
            help='Where to download the images',
        )

    def handle(self, *args, **options):
        updated_reqs = []
        blocks = Block.objects.all() #filter(active=True, block_start__lte=datetime.now(), block_end__gte=datetime.now())
        if options['blockid']:
            blocks = blocks.filter(pk=options['blockid'])
        logger.debug("==== %s x Zoo blocks %s ====" % (blocks.count(), datetime.now().strftime('%Y-%m-%d %H:%M')))
        for block in blocks:
            logger.debug("Finding thumbnails for {}".format(block))
            images, candidates = find_images_block(block.id)
            if images and candidates:
                resp = download_images_block(block.id, images, options['download_dir'])
            if not candidates:
                logger.debug('Block {} had no candidates'.format(block))
            if not images:
                logger.debug('Block {} had no images'.format(block))
