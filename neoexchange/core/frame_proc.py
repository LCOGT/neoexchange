from django.conf import settings
import requests

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
    origname = origname[0:31]
    headers = {'Authorization': 'Token {}'.format(settings.ARCHIVE_API_TOKEN)}
    try:
        response = requests.get(header_url, headers=headers, timeout=20).json()
    except:
        return []
    if response.get('data', None):
        date_obs = datetime.strptime(data['DATE_OBS'][:19],'%Y-%m-%d %H:%M:%S')
    else:
        date_obs = None

    return date_obs

def fetch_observations(tracking_num, proposal_code):
    query = "/find?propid=%s&order_by=-date_obs&tracknum=%s" % (proposal_code,tracking_num)
    data = framedb_lookup(query)
    if data:
        imgs = [(d["date_obs"],d["origname"][:-5]) for d in data]
        return imgs
    else:
        return False

def check_for_images(eventid=False):
    images = None
    client = requests.session()
    login_data = dict(username=settings.NEO_ODIN_USER, password=settings.NEO_ODIN_PASSWD)
    data_url = 'https://data.lcogt.net/find?blkuid=%s&order_by=-date_obs&full_header=1' % eventid
    try:
        resp = client.post(data_url, data=login_data, timeout=20)
        images = resp.json()
    except ValueError:
        logger.error("Request API did not return JSON %s" % resp.text)
    except requests.exceptions.Timeout:
        logger.error("Data view timed out")
    return images

def create_frame(params, block=None):
    # Return None if params is just whitespace
    if not params:
        return None
    our_site_codes = LCOGT_site_codes()
    if params.get('groupid', None):
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
    for image in images:
        frame = create_frame(image, block)
    logger.debug("Ingested %s frames" % len(images))
    return

def parse_frames(frame_list):
    '''
    ODIN API returns all data products not just the final reduction
    For the most recent frame, find the date_obs from its FITS header
    returns list of frames which end in 91 == final reduction and date_obs
    '''
    frames = []
    for frame in frame_list:
        if frame['filename'].endswith('e91.fits.fz'):
            frames.append(frame)
    # Find DATE_OBS
    date_obs = fetch_headers(frame[0]['headers'])

    return frames, date_obs
