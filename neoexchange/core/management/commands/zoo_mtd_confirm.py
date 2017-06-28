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
from core.archive_subs import archive_lookup_images, download_files, fetch_observations
from core.frames import find_images_for_block

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
            blocks = Block.objects.filter(pk=options['blockid'])
        logger.debug("==== %s x Zoo blocks %s ====" % (blocks.count(), datetime.now().strftime('%Y-%m-%d %H:%M')))
        for block in blocks:
            if PanoptesReport.objects.filter(block=block):
                logger.debug("Block {} already pushed to Zooniverse".format(block))
                continue
            files = None
            cand_per_image = None
            logger.debug("Finding images for Block {}".format(block.id))
            try:
                image_list, candidates, xmax, ymax = find_images_for_block(block.id)
                if len(candidates) < 1:
                    logger.debug("No candidates!")
                    continue
                frameids = [_['img'] for _ in image_list]
                logger.debug("Found {} candidates".format(len(candidates)))
            except TypeError:
                logger.debug("Problem encountered")
                continue
            images = fetch_observations(block.tracking_number)
            if images:
                frames = {'91':images}
            else:
                logger.debug('Block {} had no images'.format(block.id))
                continue

            # Download files and make JPG versions at full resolution
            jpg_files = []
            if not download_dir:
                download_dir = tempfile.mkdtemp()
            files = download_files(frames, download_dir)
            if not files:
                # Double check in case we already have the files
                files = glob.glob(os.path.join(download_dir, "*.fz"))
            for frameid, filename in zip(frameids,files):
                jpg_name = os.path.join(download_dir, frameid+ ".jpg")
                if os.path.isfile(jpg_name):
                    jpg_files.append(jpg_name)
                    logger.debug('File exists: {}'.format(jpg_name))
                    continue
                logger.debug("Making JPG {}".format(jpg_name))
                result = fits_to_jpg(path_to_fits=filename, path_to_jpg=jpg_name, width=xmax, height=ymax, quality=75, median=85)
                if result:
                    jpg_files.append(jpg_name)
            else:
                logger.debug('Failed to download images')

            # Make the image cut-outs for the candidates
            candidates = make_cutouts(candidates, frameids, jpg_files, block.id, download_dir, ymax)
            subject_ids = panoptes_add_set_mtd(candidates=candidates, blockid=block.id)
            if subject_ids:
                create_panoptes_report(block, subject_ids)
            if not options['download_dir']:
                shutil.rmtree(download_dir)
