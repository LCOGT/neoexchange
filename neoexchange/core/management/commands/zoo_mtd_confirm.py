from datetime import datetime, timedelta
import logging
import tempfile
import shutil
import os
import subprocess
import glob

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from fits2image.conversions import fits_to_jpg

from core.models import Block, PanoptesReport
from core.zoo import download_images_block
from core.archive_subs import archive_lookup_images, download_files
from core.frames import find_images_for_block, fetch_observations

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
        blocks = Block.objects.all()#filter(active=True, block_start__lte=datetime.now(), block_end__gte=datetime.now())
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
            logger.debug("Finding images for Block {}".format(block.id))
            try:
                image_list, candidates, xmax, ymax = find_images_for_block(block.id)
                frameids = [_['img'] for _ in image_list]
            except TypeError:
                logger.debug("Problem encountered")
                continue
            images = fetch_observations(block.tracking_number)
            if images:
                frames = {'91':images}
            else:
                logger.debug('Block {} had no images'.format(block))
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
                logger.debug("Making JPG {}".format(jpg_name))
                result = fits_to_jpg(path_to_fits=filename, path_to_jpg=jpg_name, width=xmax, height=ymax, quality=75, median=85)
                if result:
                    jpg_files.append(jpg_name)
            else:
                logger.debug('Failed to download images')

            # Make the image cut-outs for the candidates
            for candidate in candidates:
                cutouts = []
                for frameid, filename, coords in zip(frameids, jpg_files,candidate['coords']):
                    outfile = os.path.join(download_dir, "frame-{}-{}-{}.jpg".format(block.id, candidate['id'], frameid))
                    options = "convert {infile} -crop 300x300+{x}+{y} +repage {outfile}".format(infile=filename, x=coords['x'], y=coords['y'], outfile=outfile)
                    logger.debug("Creating mosaic for {}".format(frameid))
                    subprocess.call(options, shell=True)
                    cutouts.append(outfile)
                candidate['cutouts'] = cutouts
            # if jpg_files:
            #     subject_ids = panoptes_add_set(jpg_files, num_segments=9, blockid=block.id, download_dir=download_dir, workflow=workflow)
            #     if subject_ids:
            #         create_panoptes_report(block, subject_ids)
            #     if not options['download_dir']:
            #         shutil.rmtree(download_dir)
            # else:
            #     logger.debug('Failed to download images')
