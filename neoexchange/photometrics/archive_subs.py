'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

archive_subs.py -- Routines for downloading data from the LCOGT Archive

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

import requests
# Check if Python version is less than 2.7.9. If so, disable SSL warnings
if sys.version_info < (2,7,9):
    requests.packages.urllib3.disable_warnings()

def get_base_url():
    '''Return the base URL of the archive service'''
    archive_url = 'https://archive-api.lcogt.net'
    return archive_url

def archive_login(username, password):

    base_url = get_base_url()
    archive_url = base_url + '/api-token-auth/'
    #  Get the authentication token
    response = requests.post(archive_url,
        data = {
                'username': username,
                'password': password
               }).json()

    try:
        token = response.get('token')

        # Store the Authorization header
        headers = {'Authorization': 'Token ' + token}
    except TypeError:
        headers = None

    return headers

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
    '''Obtain the list of frames between <start_date> and <end_date>. An authorization token (from e.g.
    archive_login()) will likely be needed to get a proprietary data. By default we download data from
    [proposal]=LCO2015B-005 and for reduction levels 90 (final processed) and 10 (quicklook).
    Each reduction level is queried in turn and results are added to a dictionary with the reduction level
    as the key(which is returned)'''

    limit = 1000
    base_url = get_base_url()
    archive_url = '%s/frames/?limit=%d&start=%s&end=%s&OBSTYPE=%s&PROPID=%s' % (base_url, limit, start_date, end_date, obstype, proposal)

    frames = {}
    for reduction_lvl in red_lvls:
        search_url = archive_url + '&RLEVEL='+ reduction_lvl
#        print "search_url=%s" % search_url
        response = requests.get(search_url, headers=auth_header).json()
        frames_for_red_lvl = { reduction_lvl : response['results'] }
        frames.update(frames_for_red_lvl)

    return frames

def get_catalog_data(frames, auth_header='', dbg=False):
    '''Get associated catalog files for the passed <frames>'''

    base_url = get_base_url()

    catalogs = {}
    for reduction_lvl in frames.keys():
        if dbg: print reduction_lvl
        frames_to_search = frames[reduction_lvl]
        catalogs_for_red_lvl = []
        for frame in frames_to_search:
            if dbg: print frame['filename'], frame['id']
            catquery_url = "%s/frames/%d/related/" % ( base_url, frame['id'] )
            response = requests.get(catquery_url, headers=auth_header).json()
            if len(response) >= 1:
                for catalog in response:
                    if catalog['OBSTYPE'] == 'CATALOG':
                        catalogs_for_red_lvl.append(catalog)
        catalogs.update({ reduction_lvl : catalogs_for_red_lvl })

    return catalogs

def check_for_existing_file(filename, archive_md5=None, dbg=False):
    '''Tries to determine whether a higher reduction level of the file exists. If it does, True is
    returned otherwise False is returned'''

    path = os.path.dirname(filename)
    output_file = os.path.splitext(os.path.basename(filename))[0]
    extension = os.path.splitext(os.path.basename(filename))[1]
    if output_file.count('-') == 4:
        # LCOGT format files will have 4 hyphens
        chunks = output_file.split('-')
        red_lvl = chunks[4][1:3]
        if dbg: print "red_lvl, digit?=", red_lvl, red_lvl.isdigit()
        if red_lvl.isdigit():
            if int(red_lvl) < 91:
                new_lvl = "%s90%s" % (chunks[4][0], chunks[4][3:])
                new_lvl2 = "%s91%s" % (chunks[4][0], chunks[4][3:])
                new_filename = "%s-%s-%s-%s-%s%s" % (chunks[0], chunks[1], chunks[2], chunks[3], new_lvl, extension)
                new_filename2 = "%s-%s-%s-%s-%s%s" % (chunks[0], chunks[1], chunks[2], chunks[3], new_lvl2, extension)
                if dbg: print "new_filename=",new_filename, new_filename2
                new_path = os.path.join(path, new_filename)
                new_path2 = os.path.join(path, new_filename2)
                if os.path.exists(new_path) or os.path.exists(new_path2):
                    print "Higher level reduction file exists"
                    return True
                if os.path.exists(filename) and archive_md5 != None:
                    md5sum = md5(open(filename, 'rb').read()).hexdigest()
                    if dbg: print filename, md5sum, archive_md5
                    if md5sum == archive_md5:
                        print "File exists with correct MD5 sum"
                        return True
            else:
                if os.path.exists(filename):
                    print "-90 level reduction file already exists."
                    return True
    return False

def check_for_bad_file(filename, reject_dir='Bad'):

    reject_file = False
    reject_dir_path = os.path.join(os.path.dirname(filename), reject_dir)
    if os.path.exists(reject_dir_path) and os.path.isdir(reject_dir_path):
        frame = os.path.basename(filename)
        bad_frame = os.path.join(reject_dir_path, frame)
        if os.path.exists(bad_frame):
            print "Skipping bad file", os.path.join(reject_dir, frame)
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
        if dbg: print reduction_lvl
        frames_to_download = frames[reduction_lvl]
        for frame in frames_to_download:
            if dbg: print frame['filename']
            filename = os.path.join(output_path, frame['filename'])
            archive_md5 = frame['version_set'][-1]['md5']
            if check_for_existing_file(filename, archive_md5, dbg) or \
                check_for_bad_file(filename):
                print "Skipping existing file", frame['filename']
            else:
                if dbg or verbose: print "Writing file to",filename
                downloaded_frames.append(filename)
                with open(filename, 'wb') as f:
                    f.write(requests.get(frame['url']).content)
    return downloaded_frames
