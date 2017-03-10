import glob
import os
import requests
import logging

logger = logging.getLogger('neox')

def sort_candidates(frames, candidates):
    image_dict = dict(im['img'] : [] for im in frames)
    for c in candidates:
        for i, coord in enumerate(coords):
            frameid = frames[i]['img']
            image_dict[framid].append(coord)
    return image_dict

def download_images_block(blockid, frames, download_dir, candidates):
    current_files = glob.glob(download_dir+"*.jpg")
    img_dict = sort_candidates(frames, candidates)
    for frame in frames:
        filename = download_image(frame, current_files, download_dir, blockid)
        if filename:
            candidates = img_dict[frame['img']]
            manifest = create_manifest(filename,frame, candidates)
            print(manifest)


def download_image(frame, current_files, download_dir, blockid):
    frame_date = frame['date_obs'].strftime("%Y%m%d%H%M%S")
    file_name = 'block_%s_%s_%s.jpg' % (blockid, frame['img'], frame_date)
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

    return filename
