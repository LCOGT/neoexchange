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

from photometrics.archive_subs import *

proposal='LCO2016A-021'

username = os.environ.get('NEOX_ODIN_USER', None) 
password = os.environ.get('NEOX_ODIN_PASSWD',None):
if username and password:
    auth_headers = archive_login(username, password)
    start_date, end_date = determine_archive_start_end()
    frames = get_frame_data(start_date, end_date, auth_headers, proposal, red_lvls=['90', '10'])
    daydir = start_date.strftime('%Y%m%d')
    out_path = os.path.join(os.environ.get('HOME'), 'Asteroids', daydir)
    try:
        os.makedirs(out_path)
    except:
        print "Error creating output path", out_path
        os.sys.exit(-1)
    download_files(frames, out_path)
