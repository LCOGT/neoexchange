from django.conf import settings
from core.models import Frame
from astrometrics.ephem_subs import call_compute_ephem, compute_ephem, \
    determine_darkness_times, determine_slot_length, determine_exp_time_count, \
    MagRangeError,  LCOGT_site_codes
import requests
import logging

logger = logging.getLogger(__name__)

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes

def fetch_from_archive(tracking_num, proposal_code):
    filters = []
    origname = origname[0:31]
    url =settings.ARCHIVE_API + 'frames/?basename={}'.format(origname)
    headers = {'Authorization': 'Token {}'.format(settings.ARCHIVE_API_TOKEN)}
    try:
        response = requests.get(url, headers=headers, timeout=20).json()
    except:
        return []
    for datum in response['results']:
        filter_params = {
                'fits': datum['url'],
                'fullname' : filter_name
                }
        filters.append(filter_params)
    return filters

def fetch_headers(header_url):
    filters = []
    headers = {'Authorization': 'Token {}'.format(settings.ARCHIVE_API_TOKEN)}
    try:
        response = requests.get(header_url, headers=headers, timeout=20)
    except:
        return []
    if response.json().get('data', None):
        return response['data']
    else:
        return None

def create_frame(params, block=None):
    # Return None if params is just whitespace
    if not params:
        return None
    our_site_codes = LCOGT_site_codes()
    if params.get('GROUPID', None):
        # In these cases we are parsing the FITS header
        frame_params = frame_params_from_block(params, block)
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

def frame_params_from_block(params, block):
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
    for image in images:
        frame = create_frame(image, block)
    logger.debug("Ingested %s frames" % len(images))
    return

def parse_frames(frame_list):
    '''
    ODIN API returns all data products not just the final reduction
    For the most recent frame, find the date_obs from its FITS header
    returns list of frame headers which end in 91 == final reduction and date_obs
    '''
    frame_header = []
    date_obs = False
    for frame in frame_list:
        if frame['filename'].endswith('e91.fits.fz'):
            # API call to retrieve headers
            header = fetch_headers(frame['headers'])
            if header:
                frame_header.append(header)
            else:
                logger.error('No header returned for %s' % frame['filename'])
    # Find DATE_OBS of most recent frame
    if frame_header:
        date_obs = frame_header[0]['DATE_OBS']
    return frame_header, date_obs

def image_list(frames):
    '''
    Produces a list of image basenames/orignames from a request object
    '''
    frame_list = []
    for frame in frames:
        if frame['filename'].endswith('e91.fits.fz'):
            frame_list.append(frame['filename'][0:31])
    return frame_list
