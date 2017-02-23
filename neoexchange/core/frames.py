from datetime import datetime, timedelta
from math import ceil
import sys

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from astropy.wcs import WCS

from core.models import Block, Frame, Candidate, SourceMeasurement
from astrometrics.ephem_subs import LCOGT_domes_to_site_codes, LCOGT_site_codes
from core.urlsubs import get_lcogt_headers
from core.archive_subs import archive_login
import logging
import requests

ssl_verify = True
# Check if Python version is less than 2.7.9. If so, disable SSL warnings and SNI verification
if sys.version_info < (2,7,9):
    requests.packages.urllib3.disable_warnings()
    ssl_verify = False # Danger, danger !

logger = logging.getLogger('core')


def odin_login(username, password):
    '''
    Wrapper function to get ODIN headers
    '''
    auth_url = settings.REQUEST_AUTH_API_URL

    return get_lcogt_headers(auth_url,username, password)

def measurements_from_block(blockid):
    block = Block.objects.get(pk=blockid)
    frames = Frame.objects.filter(block=block).values_list('id',flat=True)
    measures = SourceMeasurement.objects.filter(frame__in=frames)
    return {'body':block.body,'measures':measures,'slot':block}

def fetch_observations(tracking_num):
    image_list = []
    headers = odin_login(settings.NEO_ODIN_USER, settings.NEO_ODIN_PASSWD)
    data = check_request_status(headers, tracking_num)
    if type(data) != list and data.get('detail','') == 'Not found.':
        return image_list
    for r in data:
        images = check_for_images(headers,request_id=r['request_number'])
        image_list += [i['id'] for i in images]
    return image_list

def find_images_for_block(blockid):
    '''
    Look up Frames and Candidates in Block.
    Output all candidates coords for each frame for Light Monitor to display
    '''
    frames = Frame.objects.filter(block__id=blockid, frametype=Frame.BANZAI_RED_FRAMETYPE).order_by('midpoint')
    candidates = candidates_by_block(blockid)
    img_list = []
    if not frames:
        return False
    x_size = frames[0].wcs._naxis1
    y_size = frames[0].wcs._naxis2
    if not frames[0].frameid:
        return False
    frames_list = [{'img':str(f.frameid)} for f in frames]
    return frames_list, candidates, x_size, y_size

def candidates_by_block(blockid):
    targets = []
    cands = Candidate.objects.filter(block__id=blockid).order_by('score')
    for cand in cands:
        coords = []
        dets = cand.unpack_dets()
        d_zip = zip(dets['frame_number'], dets['x'], dets['y'])
        for a in d_zip:
            coords.append({'x':a[1], 'y':a[2]})
        targets.append({'id': str(cand.id), 'coords':coords})
    return targets


def lcogt_api_call(auth_header, url):
    data = None
    try:
        resp = requests.get(url, headers=auth_header, timeout=20, verify=ssl_verify)
        data = resp.json()
    except requests.exceptions.InvalidSchema, err:
        data = None
        logger.error("Request call to %s failed with: %s" % (url, err))
    except ValueError, err:
        logger.error("Request %s API did not return JSON: %s" % (url, resp.status_code))
    except requests.exceptions.Timeout:
        logger.error("Request API timed out")
    return data

def check_request_status(auth_header, tracking_num=None):
    data_url = settings.REQUEST_API_URL % tracking_num
    return lcogt_api_call(auth_header, data_url)

def check_for_images(auth_header, request_id):
    '''
    Call ODIN request API to obtain all frames for request_id
    Filter out non-reduced frames
    '''
    reduced_data = []
    quicklook_data = []
    data_url = settings.FRAMES_API_URL % request_id
    data = lcogt_api_call(auth_header, data_url)
    for datum in data:
        if 'e91' in datum['filename']:
            reduced_data.append(datum)
        elif 'e11' in datum['filename']:
            quicklook_data.append(datum)
    if len(reduced_data) >= len(quicklook_data):
        return reduced_data
    else:
        return quicklook_data

def check_for_archive_images(auth_header, request_id=None, obstype='EXPOSE', limit=3000):
    '''
    Call Archive API to obtain all frames for request_id
    Follow links to get all frames and filter out non-reduced frames and returns
    fully-reduced data in preference to quicklook data
    '''
    reduced_data = []
    quicklook_data = []

    base_url = settings.ARCHIVE_FRAMES_URL
    archive_url = '%s?limit=%d&REQNUM=%s&OBSTYPE=%s' % (base_url, limit, request_id, obstype)

    frames = []
    data = fetch_archive_frames(auth_header, archive_url, frames)
    for datum in data:
        headers_url = u'%s%d/headers' % (settings.ARCHIVE_FRAMES_URL, datum['id'])
        datum[u'headers'] = headers_url
        if datum['RLEVEL'] == 91:
            reduced_data.append(datum)
        elif datum['RLEVEL'] == 11:
            quicklook_data.append(datum)
    if len(reduced_data) >= len(quicklook_data):
        return reduced_data
    else:
        return quicklook_data

def fetch_archive_frames(auth_header, archive_url, frames):

    data = lcogt_api_call(auth_header, archive_url)
    if data.get('count', 0) > 0:
        frames += data['results']
        if data['next']:
            fetch_archive_frames(auth_header, data['next'], frames)

    return frames

def create_frame(params, block=None, frameid=None):
    # Return None if params is just whitespace
    if not params:
        return None
    our_site_codes = LCOGT_site_codes()
    if params.get('GROUPID', None):
    # In these cases we are parsing the FITS header
        frame_params = frame_params_from_header(params, block)
    else:
        # We are parsing observation logs
        frame_params = frame_params_from_log(params, block)

    try:
        frame, frame_created = Frame.objects.get_or_create(**frame_params)
        frame.frameid = frameid
        frame.save()
    except Frame.MultipleObjectsReturned:
        logger.error("Duplicate frames:")
        frames = Frame.objects.filter(**frame_params)
        for frame in frames:
            logger.error(frame.id)
        raise(Frame.MultipleObjectsReturned)

    # Update catalogue information if we have it
    if params.get('astrometric_catalog',None):
        frame.astrometric_catalog = params.get('astrometric_catalog')
        frame.save()
    if params.get('photometric_catalog',None):
        frame.photometric_catalog = params.get('photometric_catalog')
        frame.save()

    if frame_created:
        msg = "created"
    else:
        msg = "updated"
    logger.debug("Frame %s %s" % (frame, msg))
    return frame

def frame_params_from_header(params, block):
    # In these cases we are parsing the FITS header
    sitecode = LCOGT_domes_to_site_codes(params.get('SITEID', None), params.get('ENCID', None), params.get('TELID', None))

    frame_params = { 'midpoint' : params.get('DATE_OBS', None),
                     'sitecode' : sitecode,
                     'filter'   : params.get('FILTER', "B"),
                     'frametype': params.get('RLEVEL', 0),
                     'block'    : block,
                     'instrument': params.get('INSTRUME', None),
                     'filename'  : params.get('ORIGNAME', None),
                     'exptime'   : params.get('EXPTIME', None),
                     'fwhm'      : params.get('L1FWHM', None),
                 }
    # Try and create a WCS object from the header. If successful, add to frame
    # params
    wcs = None
    try:
        wcs = WCS(params)
        frame_params['wcs'] = wcs
    except ValueError:
        logger.warn("Error creating WCS entry from frameid=%s" % frameid)


    # Correct filename for missing trailing .fits extension
    if '.fits' not in frame_params['filename']:
        frame_params['filename'] = frame_params['filename'].rstrip() + '.fits'
    rlevel = params.get('RLEVEL', '00')
    frame_extn = str(rlevel) + '.fits'
    frame_params['filename'] = frame_params['filename'].replace('00.fits', frame_extn)
    # Correct midpoint for 1/2 the exposure time
    if frame_params['midpoint'] and frame_params['exptime']:
        try:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            midpoint = datetime.strptime(frame_params['midpoint'], "%Y-%m-%dT%H:M:%S")

        midpoint = midpoint + timedelta(seconds=float(frame_params['exptime']) / 2.0)
        frame_params['midpoint'] = midpoint
    return frame_params

def frame_params_from_block(params, block):
    # In these cases we are parsing the Block info
    sitecode = LCOGT_domes_to_site_codes(params.get('siteid', None), params.get('encid', None), params.get('telid', None))
    frame_params = { 'midpoint' : params.get('date_obs', None),
                     'sitecode' : sitecode,
                     'filter'   : params.get('filter_name', "B"),
                     'frametype': Frame.SINGLE_FRAMETYPE,
                     'block'    : block,
                     'instrument': params.get('instrume', None),
                     'filename'  : params.get('origname', None),
                     'exptime'   : params.get('exptime', None),
                 }
    return frame_params

def frame_params_from_log(params, block):
    # Called when parsing MPC NEOCP observations lines/logs
    our_site_codes = LCOGT_site_codes()
    # We are parsing observation logs
    sitecode = params.get('site_code', None)
    if sitecode in our_site_codes:
        if params.get('flags', None) != 'K':
            frame_type = Frame.SINGLE_FRAMETYPE
        else:
            frame_type = Frame.STACK_FRAMETYPE
    else:
        if params.get('obs_type', None) == 'S':
            frame_type = Frame.SATELLITE_FRAMETYPE
        else:
            frame_type = Frame.NONLCO_FRAMETYPE
    frame_params = { 'midpoint' : params.get('obs_date', None),
                     'sitecode' : sitecode,
                     'block'    : block,
                     'filter'   : params.get('filter', "B"),
                     'frametype' : frame_type
                   }
    return frame_params

def ingest_frames(images, block):
    '''

    - Also find out how many scheduler blocks were used
    '''
    archive_headers = archive_login(settings.NEO_ODIN_USER, settings.NEO_ODIN_PASSWD)
    sched_blocks = []
    for image in images:
        image_header = lcogt_api_call(archive_headers, image.get('headers', None))
        if image_header:
            frame = create_frame(image_header['data'], block, image['id'])
            sched_blocks.append(image_header['data']['BLKUID'])
        else:
            logger.error("Could not obtain header for %s" % image)
    logger.debug("Ingested %s frames" % len(images))
    block_ids = set(sched_blocks)
    return block_ids

def block_status(block_id):
    '''
    Check if a block has been observed. If it has, record when the longest run finished
    - RequestDB API is used for block status
    - FrameDB API is used for number and datestamp of images
    - We do not count scheduler blocks which include < 3 exposures
    '''
    status = False
    try:
        block = Block.objects.get(id=block_id)
        tracking_num = block.tracking_number
    except ObjectDoesNotExist:
        logger.error("Block with id %s does not exist" % block_id)
        return False

    # Get authentication token for ODIN
    headers = odin_login(settings.NEO_ODIN_USER, settings.NEO_ODIN_PASSWD)
    logger.debug("Checking request status for %s" % block_id)
    data = check_request_status(headers, tracking_num)
    # data is a full LCOGT request dict for this tracking number.
    if not data or type(data) == dict:
        return False
    # Although this is a loop, we should only have a single request so it is executed once
    exposure_count = 0

    # Get authentication token for Archive
    archive_headers = archive_login(settings.NEO_ODIN_USER, settings.NEO_ODIN_PASSWD)

    for r in data:
        images = check_for_archive_images(archive_headers, request_id=r['request_number'])
        logger.debug('Request no. %s x %s images' % (r['request_number'],len(images)))
        if images:
            if len(images) >= 3:
                exposure_count = sum([x['exposure_count'] for x in r['molecules']])
                # Look in the archive at the header of the most recent frame for a timestamp of the observation
                last_image_dict = images[0]
                last_image_header = lcogt_api_call(archive_headers, last_image_dict.get('headers', None))
                if last_image_header == None:
                    logger.error('Image header was not returned for %s' % last_image_dict)
                    return False
                try:
                    last_image = datetime.strptime(last_image_header['data']['DATE_OBS'][:19],'%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    logger.error('Image datetime stamp is badly formatted %s' % last_image_header['data']['DATE_OBS'])
                    return False
                if (not block.when_observed or last_image > block.when_observed):
                    block.when_observed = last_image
                if block.block_end < datetime.utcnow():
                    block.active = False
                # Add frames and get list of scheduler block IDs used
                block_ids = ingest_frames(images, block)
                block.num_observed = len(block_ids)
                block.save()
                status = True
                logger.debug("Block %s updated" % block)
            else:
                logger.debug("No update to block %s" % block)
    return status
