import glob
import os
import requests
import logging
import csv
import subprocess
from PIL import Image, ImageDraw

logger = logging.getLogger('neox')

def create_manifest_file(blockid, frame_list, num_segments, download_dir):
    # The manifest file for Zooniverse will have one row per segment of
    # 3 x 3 grid from original image.
    file_name = 'manifest_{}.csv'.format(blockid)
    full_filename = os.path.join(download_dir, file_name)
    frameids = [fr['img'] for fr in frame_list]
    with open(full_filename, "wb") as f:
        wr = csv.writer(f, delimiter=',', escapechar='\\', quotechar='"', quoting=csv.QUOTE_NONE)
        for i in range(0, num_segments):
            filenames = ['frame-{}-{}.jpg'.format(frameid,i) for frameid in frameids]
            row = [i]
            row += filenames
            wr.writerow(row)
    f.close()

    return full_filename


def download_images_block(blockid, frames, download_dir):
    current_files = glob.glob(download_dir+"*.jpg")
    for frame in frames:
        filename = download_image(frame, current_files, download_dir, blockid)
        if not filename:
            logger.debug('Download problem with {}'.format(frame))
        else:
            files = create_mosaic(filename, frame['id'], download_dir)
    return

def create_mosaic(filename, frameid, download_dir):
    # Create a 3 x 3 mosaic of the image so we get better detail of where the moving object is
    full_filename =os.path.join(download_dir, filename)
    mosaic_options = "convert {} -crop 400x400 {}frame-{}-%d.jpg".format(full_filename,download_dir,frameid)
    logger.debug(mosaic_options)
    subprocess.call(mosaic_options, shell=True)
    files = ['frame-{}-%d.jpg'.format(frameid,i) for i in range(0,9)]
    return files

def download_image(frame, current_files, download_dir, blockid):
    # frame_date = frame['date_obs'].strftime("%Y%m%d%H%M%S")
    file_name = 'block_%s_%s.jpg' % (blockid, frame['id'])
    full_filename = os.path.join(download_dir, file_name)
    if full_filename in current_files:
        logger.debug("Frame {} already present".format(file_name))
        return False
    with open(full_filename, "wb") as f:
        logger.debug("Downloading %s" % file_name)
        response = requests.get(frame['url'], stream=True)
        logger.debug(frame['url'])
        if response.status_code != 200:
            logger.debug('Failed to download: %s' % response.status_code)
            return False
        total_length = response.headers.get('content-length')

        if total_length is None:
            f.write(response.content)
        else:
            for data in response.iter_content():
                f.write(data)
    f.close()

    return file_name

def add_markers_to_image(coords, filename, radius=10):
    image = Image.open(filename)
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.ellipse((coords[0]-r, coords[1]-r, coords[0]+r, coords[1]+r), fill=(0,255,0,128))
    image.save(filename, 'jpeg')
    return 
