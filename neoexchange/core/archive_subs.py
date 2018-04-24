'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2018 LCO

archive_subs.py -- Routines for downloading data from the LCO Archive

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime, timedelta
import os, sys
from hashlib import md5
import glob
import logging
from urlparse import urljoin

import requests
from django.conf import settings

from core.urlsubs import get_lcogt_headers

logger = logging.getLogger(__name__)


ssl_verify = True
# Check if Python version is less than 2.7.9. If so, disable SSL warnings
if sys.version_info < (2,7,9):
    requests.packages.urllib3.disable_warnings()
    ssl_verify = False # Danger, danger !


def archive_login(username, password):
    '''
    Wrapper function to get API token for Archive
    '''
    archive_url = settings.ARCHIVE_TOKEN_URL
    return get_lcogt_headers(archive_url, username, password)

def lco_api_call(url):
    if 'archive' in url:
        token = settings.ARCHIVE_TOKEN
    else:
        token = settings.PORTAL_TOKEN
    headers = {'Authorization': 'Token ' + token}
    data = None
    try:
        resp = requests.get(url, headers=headers, timeout=20, verify=ssl_verify)
        data = resp.json()
    except requests.exceptions.InvalidSchema, err:
        data = None
        logger.error("Request call to %s failed with: %s" % (url, err))
    except ValueError, err:
        logger.error("Request {} API did not return JSON: {}".format(url, resp.status_code))
    except requests.exceptions.Timeout:
        logger.error("Request API timed out")
    return data

def determine_archive_start_end(dt=None):

    dt = dt or datetime.utcnow()
    start = datetime(dt.year, dt.month, dt.day, 17, 0, 0)
    end = datetime(dt.year, dt.month, dt.day, 16, 0, 0)
    if dt.hour >= 0 and dt.hour <= 16:
        start = start - timedelta(days=1)
    elif dt.hour >= 17 and dt.hour <= 23:
        end = end + timedelta(days=1)

    return start, end

def get_frame_data(start_date, end_date, auth_header='', obstype='EXPOSE', proposal='LCO2015B-005', red_lvls=['90', '10']):
    '''Obtain the list of frames between <start_date> and <end_date>. An
    authorization token (from e.g. odin_login()) will likely be needed to get
    proprietary data. By default we download data from [proposal]=LCO2015B-005
    and for reduction levels 90 (final processed) and 10 (quicklook).
    Each reduction level is queried in turn and results are added to a
    dictionary with the reduction level as the key (which is returned)'''

    limit = 1000
    base_url = settings.ARCHIVE_FRAMES_URL
    archive_url = '%s?limit=%d&start=%s&end=%s&OBSTYPE=%s&PROPID=%s' % (base_url, limit, start_date, end_date, obstype, proposal)

    frames = {}
    for reduction_lvl in red_lvls:
        search_url = archive_url + '&RLEVEL='+ reduction_lvl
#        print("search_url=%s" % search_url)
        resp = requests.get(search_url, headers=auth_header)
        if resp.status_code in [200,201]:
            response = resp.json()
            frames_for_red_lvl = { reduction_lvl : response.get('results', []) }
            frames.update(frames_for_red_lvl)
        else:
            logger.error("Request {} API did not return JSON: {}".format(search_url, resp.status_code))
    return frames

def get_catalog_data(frames, auth_header='', dbg=False):
    '''Get associated catalog files for the passed <frames>'''

    base_url = settings.ARCHIVE_FRAMES_URL

    catalogs = {}
    for reduction_lvl in frames.keys():
        logger.debug(reduction_lvl)
        frames_to_search = frames[reduction_lvl]
        catalogs_for_red_lvl = []
        for frame in frames_to_search:
            logger.debug(frame['filename'], frame['id'])
            catquery_url = "%s%d/related/" % ( base_url, frame['id'] )
            response = requests.get(catquery_url, headers=auth_header).json()
            if len(response) >= 1:
                for catalog in response:
                    if catalog['OBSTYPE'] == 'CATALOG':
                        catalogs_for_red_lvl.append(catalog)
        catalogs.update({ reduction_lvl : catalogs_for_red_lvl })

    return catalogs


def check_for_archive_images(request_id=None, obstype='EXPOSE', limit=3000):
    '''
    Call Archive API to obtain all frames for request_id
    Follow links to get all frames and filter out non-reduced frames and returns
    fully-reduced data in preference to quicklook data
    '''
    reduced_data = []
    quicklook_data = []
    auth_header = {'Authorization': 'Token {}'.format(settings.ARCHIVE_TOKEN)}

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
    num_total_frames = len(quicklook_data) + len(reduced_data)
    if len(reduced_data) >= len(quicklook_data):
        return reduced_data, num_total_frames
    else:
        return quicklook_data, num_total_frames

def fetch_observations(tracking_num):
    '''
    Convert tracking number to a list of archive frames at the highest level of reduction
    :param tracking_num: ID of the user request, containing all sub-requests
    '''
    data_url = urljoin(settings.PORTAL_REQUEST_API, tracking_num)
    data = lco_api_call(data_url)
    if data.get('requests','') == 'Not found.':
        return []
    for r in data['requests']:
        images = check_for_archive_images(request_id=r['id'])
    return images

def fetch_archive_frames(auth_header, archive_url, frames):

    data = lco_api_call(archive_url)
    if data.get('count', 0) > 0:
        frames += data['results']
        if data['next']:
            fetch_archive_frames(auth_header, data['next'], frames)

    return frames

def check_for_existing_file(filename, archive_md5=None, dbg=False, verbose=False):
    '''Tries to determine whether a higher reduction level of the file exists. If it does, True is
    returned otherwise False is returned'''

    path = os.path.dirname(filename)
    uncomp_filepath = os.path.splitext(filename)[0]
    output_file = os.path.splitext(os.path.basename(filename))[0]
    extension = os.path.splitext(os.path.basename(filename))[1]
    if output_file.count('-') == 4:
        # LCOGT format files will have 4 hyphens
        chunks = output_file.split('-')
        red_lvl = chunks[4][1:3]
        logger.debug("red_lvl={}, digit?={}".format(red_lvl, red_lvl.isdigit()))
        if red_lvl.isdigit():
            if int(red_lvl) < 91:
                new_lvl = "%s90%s" % (chunks[4][0], chunks[4][3:])
                new_lvl2 = "%s91%s" % (chunks[4][0], chunks[4][3:])
                new_filename = "%s-%s-%s-%s-%s%s" % (chunks[0], chunks[1], chunks[2], chunks[3], new_lvl, extension)
                new_filename2 = "%s-%s-%s-%s-%s%s" % (chunks[0], chunks[1], chunks[2], chunks[3], new_lvl2, extension)
                logger.debug("new_filename=file {}, {}".format(new_filename, new_filename2))
                new_path = os.path.join(path, new_filename)
                new_path2 = os.path.join(path, new_filename2)
                uncomp_filepath2 = os.path.splitext(new_path2)[0]
                if os.path.exists(new_path) or os.path.exists(new_path2):
                    if verbose: print("Higher level reduction file exists")
                    return True
                if os.path.exists(uncomp_filepath2):
                    if verbose: print("Uncompressed higher level reduction file exists")
                    return True
                if os.path.exists(uncomp_filepath):
                    if verbose: print("Uncompressed reduction file exists")
                    return True
                if os.path.exists(filename) and archive_md5 != None:
                    md5sum = md5(open(filename, 'rb').read()).hexdigest()
                    logger.debug("{} {} {}".format(filename, md5sum, archive_md5))
                    if md5sum == archive_md5:
                        if verbose: print("File exists with correct MD5 sum")
                        return True
            else:
                if os.path.exists(filename) and archive_md5 != None:
                    md5sum = md5(open(filename, 'rb').read()).hexdigest()
                    logger.debug("{} {} {}".format(filename, md5sum, archive_md5))
                    if md5sum == archive_md5:
                        if verbose: print("-91 level reduction file already exists with correct MD5 sum.")
                        return True
                if os.path.exists(uncomp_filepath):
                    if verbose: print("Uncompressed -91 level reduction file already exists.")
                    return True

    return False

def check_for_bad_file(filename, reject_dir='Bad'):

    reject_file = False
    reject_dir_path = os.path.join(os.path.dirname(filename), reject_dir)
    if os.path.exists(reject_dir_path) and os.path.isdir(reject_dir_path):
        frame = os.path.basename(filename)
        bad_frame = os.path.join(reject_dir_path, frame)
        if os.path.exists(bad_frame):
            logger.debug("Skipping bad file {}".format(os.path.join(reject_dir, frame)))
            reject_file = True
    return reject_file

def download_files(frames, output_path, verbose=False, dbg=False):
    '''Downloads and saves to disk, the specified files from the new Science
    Archive. Returns a list of the frames that were downloaded.
    Takes a dictionary <frames> (keyed by reduction levels and produced by
    get_frame_data() or get_catalog_data()) of lists of JSON responses from the
    archive API and downloads the files to <output_path>. Lower reduction level
    files (e.g. -e10 quicklook files) will not be downloaded if a higher
    reduction level already exists and frames will not be downloaded if they
    already exist. If [verbose] is set to True, the filename of the downloaded
    file will be printed.'''

    if not os.path.exists(output_path):
        os.makedirs(output_path)
    downloaded_frames = []
    for reduction_lvl in frames.keys():
        logger.debug(reduction_lvl)
        frames_to_download = frames[reduction_lvl]
        for frame in frames_to_download:
            logger.debug(frame['filename'])
            filename = os.path.join(output_path, frame['filename'])
            archive_md5 = frame['version_set'][-1]['md5']
            if check_for_existing_file(filename, archive_md5, dbg, verbose) or \
                check_for_bad_file(filename):
                logger.info("Skipping existing file {}".format(frame['filename']))
            else:
                logger.info("Writing file to {}".format(filename))
                downloaded_frames.append(filename)
                with open(filename, 'wb') as f:
                    f.write(requests.get(frame['url']).content)
    return downloaded_frames

def archive_lookup_images(images):
    '''
    user_reqs: Full User Request dict, or list of dictionaries, containing individual observation requests
    header: provide auth token from the request API so we don't need to get it twice
    '''
    headers = {'Authorization': 'Token ' + settings.ARCHIVE_TOKEN}
    frame_urls = []
    for frame in images:
        thumbnail_url = "{}{}/?width=1920&height=1920&median=true&percentile=98".format(settings.THUMBNAIL_URL, frame['img'])
        try:
            resp = requests.get(thumbnail_url, headers=headers)
            frame_info = {'id':frame['img'], 'url':resp.json()['url']}
            frame_urls.append(frame_info)
            logger.debug("Found {}".format(resp.json()['url']))
        except ValueError:
            logger.error("Failed to get thumbnail URL for %s - %s" % (frame, resp.status_code))
    logger.debug("Total frames=%s" % (len(frame_urls)))
    return frame_urls
