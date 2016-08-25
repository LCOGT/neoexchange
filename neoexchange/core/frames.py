import requests
from datetime import datetime
from math import ceil
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from core.models import Block, Frame
from astrometrics.ephem_subs import LCOGT_domes_to_site_codes, LCOGT_site_codes
from core.urlsubs import get_lcogt_headers
from core.archive_subs import archive_login
import logging

logger = logging.getLogger('core')


def odin_login(username, password):
    '''
    Wrapper function to get ODIN headers
    '''
    auth_url = settings.REQUEST_AUTH_API_URL

    return get_lcogt_headers(auth_url,username, password)


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


def lcogt_api_call(auth_header, url):
    data = None
    try:
        resp = requests.get(url, headers=auth_header, timeout=20)
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
    data_url = settings.FRAMES_API_URL % request_id
    data = lcogt_api_call(auth_header, data_url)
    for datum in data:
        if 'e91' in datum['filename']:
            reduced_data.append(datum)
    return reduced_data


def create_frame(params, block=None):
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
    frame, frame_created = Frame.objects.get_or_create(**frame_params)
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
                     'frametype': Frame.SINGLE_FRAMETYPE,
                     'block'    : block,
                     'instrument': params.get('INSTRUME', None),
                     'filename'  : params.get('ORIGNAME', None),
                     'exptime'   : params.get('EXPTIME', None),
                 }
    return frame_params

def frame_params_from_block(params, block):
    # In these cases we are parsing the FITS header
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
    archive_headers = archive_login(settings.NEO_ODIN_USER, settings.NEO_ODIN_PASSWD)
    for image in images:
        image_header = lcogt_api_call(archive_headers, image.get('headers', None))
        if image_header:
            frame = create_frame(image_header['data'], block)
        else:
            logger.error("Could not obtain header for %s" % image)
    logger.debug("Ingested %s frames" % len(images))
    return

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
    if not data:
        return False
    # Although this is a loop, we should only have a single request so it is executed once
    exposure_count = 0
    for r in data:
        images = check_for_images(headers, request_id=r['request_number'])
        logger.debug('Request no. %s x %s images' % (r['request_number'],len(images)))
        if images:
            if len(images) >= 3:
                exposure_count = sum([x['exposure_count'] for x in r['molecules']])
                # Look in the archive at the header of the most recent frame for a timestamp of the observation
                archive_headers = archive_login(settings.NEO_ODIN_USER, settings.NEO_ODIN_PASSWD)
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
#                block.num_observed = exposure_count
                # This is not correct either but better than it is currently working
                # which is just setting # of times the block has been observed to the
                # number of exposures in the block... XXX to fix
                block.num_observed = int( ceil( len(images) / float(exposure_count) ) )
                block.save()
                status = True
                logger.debug("Block %s updated" % block)
                # Add frames
                resp = ingest_frames(images, block)
            else:
                logger.debug("No update to block %s" % block)
    return status
