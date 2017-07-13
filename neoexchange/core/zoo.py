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
import six

from panoptes_client import SubjectSet, Subject, Panoptes, Project, Workflow
from panoptes_client.panoptes import PanoptesAPIException

from core.models import Frame, Block, SITE_CHOICES, TELESCOPE_CHOICES, PanoptesReport, \
    CatalogSources, Candidate

logger = logging.getLogger('neox')


def panoptes_add_set_mtd(candidates, blockid):
    Panoptes.connect(username=settings.ZOONIVERSE_USER, password=settings.ZOONIVERSE_PASSWD)
    bk = Block.objects.get(pk=blockid)

    project = Project.find(slug='zemogle/agent-neo')

    subject_set = SubjectSet()
    subject_set.links.project = project
    subject_set.display_name = 'block_{}'.format(blockid)
    try:
        subject_set.save()
    except PanoptesAPIException:
        if settings.ZOONIVERSE_USER == '' or settings.ZOONIVERSE_PASSWD == '':
            logger.warn('ZOONIVERSE_USER and/or ZOONIVERSE_PASSWD environment variables not set')
        else:            
            logger.debug('Subject set {} already exists'.format(subject_set.display_name))
        return False

    subject_list = []
    subject_ids = []
    telescope = dict(TELESCOPE_CHOICES)
    site = dict(SITE_CHOICES)
    for candidate in candidates:
        subject = Subject()
        subject.links.project = project
        if not candidate['cutouts']:
            logger.debug('No cut-out files for {}'.candidate['id'])
            continue
        for i, filename in enumerate(candidate['cutouts']):
            subject.add_location(filename)
            subject.metadata["image_{}".format(i)] = os.path.basename(filename)
            logger.debug('adding {}'.format(filename))
        subject.metadata['telescope'] = "{} at {}".format(telescope[bk.telclass], site[bk.site])
        subject.metadata['date'] = "{}".format(bk.when_observed.isoformat())
        subject.metadata['candidate_id'] = candidate['id']
        subject.metadata['speed (arcsecs/minute)'] = str(candidate['motion']['speed'])
        subject.metadata['magnitude'] = str(candidate['sky_coords'][0]['mag'])
        try:
            subject.save()
        except AttributeError:
            logger.error('Could not upload {}'.format(filename))
            continue
        except Exception, e:
            logger.error(''.format(e))
        logger.debug('saved subject {}'.format(subject.id))
        subject_ids.append({'id':subject.id, 'candidate':candidate['id']})
        subject_list.append(subject)

    # add subjects to subject set
    subject_set.add(subject_list)

    # Added these subjects to the 1st Workflow because thats all we have
    workflow = Workflow.find(_id='4154')

    resp, error = workflow.http_post(
                 '{}/links/subject_sets'.format(workflow.id),
                 json={'subject_sets': [subject_set.id]}
             )
    if not error:
        return subject_ids
    else:
        logger.error('Manually attach {} to workflow: {}'.format(subject_set.display_name, e))
        return False

def create_panoptes_report(block, subject_ids):
    now = datetime.now()
    for subject in subject_ids:
        candidate = Candidate.objects.get(id = int(subject['candidate']))
        pr, created = PanoptesReport.objects.get_or_create(block = block, candidate = candidate)
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

def add_markers_to_image(filename):
    logger.debug("Adding marker to {}".format(filename))
    img = Image.open(filename)
    image = img.convert('RGB')
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.line((135, 150, 110, 150), fill=(0,255,0,128), width=3)
    draw.line((150, 135, 150, 110), fill=(0,255,0,128), width=3)
    image.save(filename, 'jpeg')
    return

def make_cutouts(candidates, frameids, jpg_files, blockid, download_dir, ymax):
    for candidate in candidates:
        cutouts = []
        for frameid, filename, coords in zip(frameids, jpg_files,candidate['coords']):
            outfile = os.path.join(download_dir, "frame-{}-{}-{}.jpg".format(blockid, candidate['id'], frameid))
            if os.path.isfile(outfile):
                logger.debug("File exists: {}".format(outfile))
                cutouts.append(outfile)
                continue
            options = "convert {infile} -crop 300x300+{x}+{y} +repage {outfile}".format(infile=filename, x=coords['x']-150, y=ymax-coords['y']-150, outfile=outfile)
            logger.debug("Creating mosaic for Frame {} Candidate {}".format(frameid, candidate['id']))
            subprocess.call(options, shell=True)
            cutouts.append(outfile)
            # mark image with finder markers
            add_markers_to_image(outfile)
        candidate['cutouts'] = cutouts
    return candidates

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
    # sources = identify_sources(subjects)
    return subjects

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
        if value == 'Yes' and int(content['subject_ids']) in active_subjects:
            subject_data = json.loads(content['subject_data'])
            keys = subject_data.keys()
            if not subject_data[keys[0]]['retired']:
                # Only send recently retired results
                for v in value:
                    data = {'user'  : content['user_name'],
                            'candidate'  : subject_data[keys[0]]['candidate_id'],
                            }
                    subjects[keys[0]].append(data)
    return subjects

def identify_sources(sources):
    for k, source in sources.items():
        users = [dict(t) for t in set([tuple(d.items()) for d in source])]
        if len(users) > 6:
            print(k, users)
    return

def retire_subjects(subjects):
    for k,v in subjects.iteritems():
        if v and k:
            active_subjects = PanoptesReport.objects.filter(id=k)
            active_subjects.update(active=False)
            logger.debug('Retired {}'.format(active_subjects))
    return

def fix_panoptes_reports():
    Panoptes.connect(username=settings.ZOONIVERSE_USER, password=settings.ZOONIVERSE_PASSWD)

    ids = []

    report = {}
    ssids = {u'11368': u'7901',
             u'11461': u'7952',
             u'11462': u'7880',
             u'11992': u'8036',
             u'12497': u'7946'}

    for k,v in ssids.items():
     report[v] = []

    for k in ssids.keys():
        for ss in SubjectSet.find(_id=k).subjects():
             sr = ss.raw
             if not sr['metadata'].get('quadrant',None) and sr['metadata'].get('candidate_id',None):
                report[ssids[k]].append({'candidate':sr['metadata']['candidate_id'],'id':sr['id']})

    for k,v in report.items():
        block = Block.objects.get(id=k)
        cz.create_panoptes_report(block, v)

    return
