#!/usr/bin/env python
'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

download_archive_data.py -- Wrapper for downloading data from the LCOGT Archive

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
import os
from sys import argv

from archive_subs import archive_login, get_frame_data, get_catalog_data, determine_archive_start_end

usage = "Incorrect usage. Usage: %s [YYYYMMDD] [proposal code]" % ( argv[0] )

# Defaults
proposal='LCO2016A-021'
obs_date = datetime.utcnow()
obstype = '' # Set to blank to get frames and catalogs
redlevel = ['91', '11']

# Parse command line arguments
if len(argv) == 2:
    proposal_or_date = argv[1]
    if proposal_or_date[0:3].isdigit():
        try:
            obs_date = datetime.strptime(proposal_or_date, '%Y%m%d')
            obs_date += timedelta(seconds=17*3600)
        except ValueError:
            print usage
    else:
        proposal = proposal_or_date
elif len(argv) == 3:
    try:
        obs_date = datetime.strptime(argv[1], '%Y%m%d')
        obs_date += timedelta(seconds=17*3600)
    except ValueError:
        print usage
    proposal = argv[2]
elif len(argv) > 3:
    print usage

username = os.environ.get('NEOX_ODIN_USER', None)
password = os.environ.get('NEOX_ODIN_PASSWD',None)
if username and password:
    auth_headers = archive_login(username, password)
    start_date, end_date = determine_archive_start_end(obs_date)
    print "Looking for frames between %s->%s from %s" % ( start_date, end_date, proposal )
    frames = get_frame_data(start_date, end_date, auth_headers, obstype, proposal, red_lvls=redlevel)
    if 'CATALOG' in obstype or obstype == '':
        catalogs = get_catalog_data(frames, auth_headers)
        for red_lvl in frames.keys():
            frames[red_lvl] = frames[red_lvl] + catalogs[red_lvl]
    for red_lvl in frames.keys():
        print "Found %d frames for reduction level: %s" % ( len(frames[red_lvl]), red_lvl )
    daydir = start_date.strftime('%Y%m%d')
    out_path = os.path.join(os.environ.get('HOME'), 'Asteroids', daydir)
    if not os.path.exists(out_path):
        try:
            os.makedirs(out_path)
        except:
            print "Error creating output path", out_path
            os.sys.exit(-1)
    print "Downloading data to", out_path
    dl_frames = download_files(frames, out_path, verbose=True)
    print "Downloaded %d frames" % ( len(dl_frames) )
else:
    print "No username or password defined (set NEOX_ODIN_USER and NEOX_ODIN_PASSWD)"
