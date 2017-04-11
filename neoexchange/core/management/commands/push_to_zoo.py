from core.models import Block
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from core.zoo import download_images_block, create_manifest_file, reorder_candidates, push_set_to_panoptes
from core.archive_subs import archive_lookup_images
from core.frames import find_images_for_block
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
            default=False,
            help='Where to download the images',
        )

    def handle(self, *args, **options):
        blocks = Block.objects.all() #filter(active=True, block_start__lte=datetime.now(), block_end__gte=datetime.now())
        download_dir = options['download_dir']
        if options['blockid']:
            blocks = blocks.filter(pk=options['blockid'])
        logger.debug("==== %s x Zoo blocks %s ====" % (blocks.count(), datetime.now().strftime('%Y-%m-%d %H:%M')))
        for block in blocks:
            files = None
            cand_per_image = None
            logger.debug("Finding thumbnails for Block {}".format(block.id))
            try:
                image_list, candidates, xmax, ymax = find_images_for_block(block.id)
            except TypeError:
                logger.debug("Problem encountered")
                continue
            images = archive_lookup_images(image_list)
            if images and candidates:
                scale = xmax/1920.
                cand_per_image = reorder_candidates(candidates)
            if not candidates:
                logger.debug('Block {} had no candidates'.format(block))
                continue
            if not images:
                logger.debug('Block {} had no images'.format(block))
                continue
            if files:
                if not download_dir:
                    download_dir = tempfile.mkdtemp()
                files = download_images_block(block.id, images, cand_per_image, scale, download_dir)
                manifest = push_set_to_panoptes(files, num_segments=12, blockid=block.id, download_dir=download_dir)
                if not options['download_dir']:
                    shutil.rmtree(download_dir)
            else:
                logger.debug('Failed to download images')
