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

from archive_subs import *

proposal='LCO2016A-021'

username = os.environ.get('NEOX_ODIN_USER', None) 
password = os.environ.get('NEOX_ODIN_PASSWD',None)
if username and password:
    auth_headers = archive_login(username, password)
    start_date, end_date = determine_archive_start_end()
    print "Looking for frames between %s->%s" % ( start_date, end_date )
    frames = get_frame_data(start_date, end_date, auth_headers, proposal, red_lvls=['90', '10'])
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
    print "Downloading data"
    dl_frames = download_files(frames, out_path)
    print "Downloaded %d frames" % ( len(dl_frames) )
