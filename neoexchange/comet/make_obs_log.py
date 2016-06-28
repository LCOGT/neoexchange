#!/usr/bin/env python

import os
from glob import glob
from sys import path
from datetime import datetime,timedelta

path.insert(0, os.path.join(os.getenv('HOME'), 'git/neoexchange-comet/neoexchange'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
import django
from django.conf import settings
django.setup()

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes
from comet_subs import *

datadir = os.path.join(os.getenv('HOME'), 'Asteroids', '67P', 'Pipeline', 'Temp')
datadir = os.path.join(os.path.abspath(datadir), '')
# Find all images
images, catalogs = determine_images_and_catalogs(datadir)

# Create log file, write header
log_file = os.path.join(datadir, '67P_website.csv')

if os.path.exists(log_file):
    os.remove(log_file)
log_fh = open(log_file, 'w')
print >> log_fh,  "Observatory,Telescope/Instrument,PI (data owner),PI/contact e-mail address,Method,Band/Wavelength,Set up details,Start time,End time,Data Quality,Notes/Comments"

pi = 'Tim Lister'
pi_email = 'tlister@lcogt.net'
# Loop over all images
for fits_fpath in images:
    fits_frame = os.path.basename(fits_fpath)
    print "Processing %s" % fits_frame

    # Determine if good zeropoint
    zp, zp_err = retrieve_zp_err(fits_frame)

    #   Open image
    header, image = open_image(fits_fpath)
    sitecode = LCOGT_domes_to_site_codes(header['siteid'], header['encid'], header['telid'])

    start_time = datetime.strptime(header['date-obs'], '%Y-%m-%dT%H:%M:%S.%f')
    end_time = start_time + timedelta(seconds=header['exptime'])
    tel_inst = '1.0m/CCD'
    if '2m0a' in header['telid']:
        tel_inst = '2.0m/CCD'
    elif '0m4' in header['telid']:
        tel_inst = '0.4m/CCD'
    # Get observed filter, Connvert 'p' to prime
    obs_filter = header['filter']
    obs_filter = obs_filter[:-1] + obs_filter[-1].replace("p", "'")
    quality = 'OK'
    if zp < 0 and zp_err < 0:
        quality = 'No use'
    log_format = "%s,%3s,%s,%s,%s,IMG,%3s, ,%s,%s,%10s,"
    log_line = log_format % (fits_frame, sitecode, tel_inst, pi, pi_email, obs_filter, start_time.strftime('%d/%m/%Y %H:%M:%S'), end_time.strftime('%d/%m/%Y %H:%M:%S'), quality)
    print >> log_fh, log_line
log_fh.close()
