import glob
import os
import requests
import logging
import csv
import json
import subprocess
from PIL import Image, ImageDraw
from datetime import datetime
from astropy.coordinates import SkyCoord
from numpy import mean, sqrt
from django.conf import settings

from panoptes_client import SubjectSet, Subject, Panoptes, Project, Workflow
from panoptes_client.panoptes import PanoptesAPIException

from core.models import Frame, Block, SITE_CHOICES, TELESCOPE_CHOICES, PanoptesReport, \
    CatalogSources

logger = logging.getLogger('neox')

def panoptes_add_set(files, num_segments, blockid, download_dir):
    Panoptes.connect(username=settings.ZOONIVERSE_USER, password=settings.ZOONIVERSE_PASSWD)
    bk = Block.objects.get(pk=blockid)

    project = Project.find(slug='zemogle/agent-neo')

    subject_set = SubjectSet()
    subject_set.links.project = project
    subject_set.display_name = 'block_{}'.format(blockid)
    try:
        subject_set.save()
    except PanoptesAPIException:
        return False

    subject_list = []
    subject_ids = []
    telescope = dict(TELESCOPE_CHOICES)
    site = dict(SITE_CHOICES)
    for index in range(0, num_segments):
        subject_files = [fn for fn in files if "-{}.jpg".format(index) in fn]
        if not subject_files:
            logger.debug('No files found matching -{}.jpg'.format(index))
            continue

        subject = Subject()
        subject.links.project = project
        for i, filename in enumerate(subject_files):
            subject.add_location(download_dir+filename)
            subject.metadata["image_{}".format(i)] = filename
        subject.metadata['telescope'] = "{} at {}".format(telescope[bk.telclass], site[bk.site])
        subject.metadata['date'] = "{}".format(bk.when_observed.isoformat())
        subject.metadata['quadrant'] = index
        subject.save()
        subject_ids.append({'id':subject.id, 'quad':index})
        subject_list.append(subject)

    # add subjects to subject set
    subject_set.add(subject_list)

    # Added these subjects to the 0th Workflow because thats all we have
    workflow = project.links.workflows[0]
    resp, error = workflow.http_post(
                 '{}/links/subject_sets'.format(workflow.id),
                 json={'subject_sets': [subject_set.id]}
             )
    if not error:
        return subject_ids
    else:
        return False

def create_panoptes_report(block, subject_ids):
    now = datetime.now()
    for subject in subject_ids:
        pr, created = PanoptesReport.objects.get_or_create(block = block, quad = int(subject['quad']))
        if not created:
            continue
        pr.when_submitted = now
        pr.last_check = now
        pr.active = True
        pr.subject_id = int(subject['id'])
        pr.save()
    return

def reorder_candidates(candidates):
    # Change candidates list from by candidate to by image
    new_cands = []
    num_candidates = len(candidates)
    num_frames = len(candidates[0]['coords'])
    for i in range(0,num_frames):
        cands_by_img = []
        for j in range(0, num_candidates):
            cands_by_img.append(candidates[j]['coords'][i])
        new_cands.append(cands_by_img)
    return new_cands

def download_images_block(blockid, frames, scale, download_dir):
    '''
    Finds all thumbnails for frames list, downloads them, adds markers for candidates,
    creates a mosaic of each frame see we can see more detail.
    '''
    current_files = glob.glob(download_dir+"*.jpg")
    mosaic_files = []
    for i, frame in enumerate(frames):
        filename = download_image(frame, current_files, download_dir, blockid)
        # if candidates:
        #     add_markers_to_image(filename, candidates[i], scale=scale, radius=10.)
        if not filename:
            logger.debug('Download problem with {}'.format(frame))
            return False
        else:
            files = create_mosaic(filename, frame['id'], download_dir)
            mosaic_files += files

    return mosaic_files

def create_mosaic(filename, frameid, download_dir):
    # Create a  3 x 3 mosaic of each image so we get better detail of where the moving object is
    # WARNING 640x640 will only work with 1m and 2m data NOT 0m4 data
    # 0m4 523x352
    full_filename =os.path.join(download_dir, filename)
    mosaic_options = "convert {} -crop 640x640 {}frame-{}-%d.jpg".format(full_filename,download_dir,frameid)
    logger.debug("Creating mosaic for {}".format(frameid))
    subprocess.call(mosaic_options, shell=True)
    files = ['frame-{}-{}.jpg'.format(frameid,i) for i in range(0,9)]
    return files

def download_image(frame, current_files, download_dir, blockid):
    # Download thumbnail images only if they do not exist
    file_name = 'block_%s_%s.jpg' % (blockid, frame['id'])
    full_filename = os.path.join(download_dir, file_name)
    if full_filename in current_files:
        logger.debug("Frame {} already present".format(file_name))
        return full_filename
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

    return full_filename

def add_markers_to_image(filename, candidates, scale, radius):
    image = Image.open(filename)
    draw = ImageDraw.Draw(image, 'RGBA')
    for coords in candidates:
        draw.ellipse((coords['x']/scale-radius, coords['y']/scale-radius, coords['x']/scale+radius, coords['y']/scale+radius), fill=(0,255,0,128))
    image.save(filename, 'jpeg')
    return

def read_classification_report(filename):
    '''
    Read classificiation report from Zooniverse, extracting position information
    for possible targets
    :param filename: full path to report file
    '''
    contents = []
    with open(filename, 'rb') as csvfile:
        report = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        for row in report:
            contents.append(row)

    subjects = parse_classifications(contents)
    retire_subjects(subjects)
    sources = identify_sources(subjects)
    return sources

def parse_classifications(contents):
    '''
    Take the parsed Zooniverse classification report, find all the retired subject sets
    and match them to blocks and frames using PanoptesReport model
    :param contents: a list of the classification data
    '''
    active_subjects = PanoptesReport.objects.filter(active=True).values_list('subject_id', flat=True)
    subjects = {str(a):[] for a in active_subjects}
    for content in contents:
        # Choose the 0th value because we only have 1 workflow
        value = json.loads(content['annotations'])[0]['value']
        if value and int(content['subject_ids']) in active_subjects:
            subject_data = json.loads(content['subject_data'])
            keys = subject_data.keys()
            if subject_data[keys[0]]['retired']:
                # Only send recently retired results
                for v in value:
                    data = {'user'  : content['user_name'],
                            'x'     : v['x'],
                            'y'     : v['y'],
                            'quad'  : subject_data[keys[0]]['quadrant'],
                            'frame' : subject_data[keys[0]]['image_0']
                            }
                    subjects[keys[0]].append(data)
    return subjects

def retire_subjects(subjects):
    for k,v in subjects.iteritems():
        if v and k:
            active_subjects = PanoptesReport.objects.filter(id=k)
            active_subjects.update(active=False)
            logger.debug('Retired {}'.format(active_subjects))
    return

def convert_image_to_sky(filename,x,y,quad,xscale,yscale):
    '''
    Translate coordinates from a quadranted image to RA and Dec
    Requires matching with first Frame in a sequence, which is obtained from quadrant filename
    :param filename: filename of the first quadrant file in the sequence
    :param x,y: pixel positions in quadrant image
    :param quad: quadrant of full image
    :param xscale, yscale: dimensions of the quad image
    '''
    frameid = filename.split('-')[1]
    frame = Frame.objects.get(frameid=frameid)
    xf = x + quad%3 * xscale
    yf = y + quad/3 * yscale
    sc = SkyCoord.from_pixel(xf,yf,frame.wcs)
    return sc.ra.degree, sc.dec.degree

def convert_coords(x,y,quad,xscale,yscale, xsize, ysize):
    '''
    Takes coordinates from a quadranted image and converts them into Frame x/y
    Requires matching with first Frame in a sequence, which is obtained from quadrant filename
    :param filename: filename of the first quadrant file in the sequence
    :param x,y: pixel positions in quadrant image
    :param quad: quadrant of full image
    :param xscale, yscale: dimensions of the quad image
    '''
    x = (x + quad%3 * xscale)*float(xsize)/xscale*3.
    y = float(ysize) - (y + quad/3 * yscale)*float(ysize)/yscale*3.
    x_min = x - 5
    y_min = y - 5
    x_max = x + 5
    y_max = y + 5
    return x_min, x_max, y_min, y_max

def filter_vals(vals):
    '''
    Filter list of vals to only those within 3 STD of mean
    '''
    output = [x for x in vals if sqrt(abs(x - mean(vals))) < 3.]
    mean_val = mean(output)
    return mean_val

def identify_sources(subjects):
    '''
    Align Panoptes classification with CatalogSources
    :param subject['frame']: Archive frame ID
    :param subject['x']: x positions from Panoptes
    :param subject['y']: y positions from Panoptes
    :param subject['quad']: quadrant of full image
    '''
    sources = []
    for subject_id, subject in subjects.iteritems():
        frameid = subject[0]['frame'].split('-')[1]
        try:
            frame = Frame.objects.get(frameid=frameid)
        except Frame.DoesNotExist:
            logger.debug("Frame {} does not exist".format(frameid))
            continue
        for data in subject:
            x_min, x_max, y_min, y_max = convert_coords(data['x'], data['y'], data['quad'], 640, 640, frame.get_x_size(), frame.get_y_size())
            cs = CatalogSources.objects.filter(frame=frame, obs_x__gte=x_min, obs_x__lte=x_max, obs_y__gte=y_min, obs_y__lte=y_max)
            sources += list(cs)
    # Return the distribution of sources and numbers who found them
    source_distrib = [(s,sources.count(s)) for s in set(sources)]
    return source_distrib
