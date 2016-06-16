#!/usr/bin/env python

import os
from sys import path, exit
from glob import glob
from math import log10

from astropy.io import fits
import numpy as np
from astropy.stats import sigma_clipped_stats, mad_std
from astropy.wcs import WCS
from photutils import CircularAperture, aperture_photometry
from photutils.utils import calc_total_error
from photutils.background import Background

path.insert(0, os.path.join(os.getenv('HOME'), 'GIT/neoexchange/neoexchange'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
import django
from django.conf import settings
django.setup()

from core.models import Frame, Block
from astrometrics.ephem_subs import LCOGT_domes_to_site_codes
from comet_subs import *

datadir = os.path.join(os.getenv('HOME'), 'Asteroids', '67P', 'Pipeline', 'Temp')
datadir = os.path.join(os.path.abspath(datadir), '')
bkg_map = True

# Find all images
images, catalogs = determine_images_and_catalogs(datadir)

# Loop over all images
for fits_fpath in images[0:2]:
    fits_frame = os.path.basename(fits_fpath)
    print "Processing %s" % fits_frame

    # Determine if good zeropoint
    try:
        frame = Frame.objects.get(filename=fits_frame)
    except Frame.DoesNotExist:
        print "No DB record of %s" % fits_frame
        exit(-1)
    except Frame.MultipleObjectsReturned:
        print "Multiple processed frame records found for %s" % fits_frame
        exit(-1)
    zp = frame.zeropoint
    #   Open image
    header, image = open_image(fits_fpath)
    
    #   Make bad pixel mask of saturated and very low values
    low_clip = 100.0
    if bkg_map:
        low_clip = -50.0
    mask = make_mask(image, header['saturate'], low_clip)

    #   Determine background and subtract
    if bkg_map:
        bkg = Background(image, (50, 50), filter_size=(3, 3), method='median', mask=mask)
        sky_level = bkg.background    
        sky_sigma = bkg.background_rms
        effective_gain = header['gain']
        print "Gain=", effective_gain
        error = calc_total_error(image, sky_sigma, effective_gain)
        image_sub = image - sky_level
    else:
        mean, median, std = sigma_clipped_stats(image, sigma=3.0, iters=3, mask=mask)
        print "Mean, median, std. dev=", mean, median, std
        image_sub = image - median

    #   Determine position of comet in this frame
    sitecode = LCOGT_domes_to_site_codes(header['siteid'], header['encid'], header['telid'])
    ephem_file = "67P_ephem_%s_%s_%s.txt" % ( header['siteid'].upper(), header['instrume'].lower(), sitecode.upper())
    ephem_file = os.path.join(os.getenv('HOME'), 'Asteroids', ephem_file)

    jd = header['mjd-obs'] + 2400000.5
    print "JD=", jd, header['date-obs']
    ra, dec, del_ra, del_dec, delta, phase = interpolate_ephemeris(ephem_file, jd)
    fits_wcs = WCS(header)
    x, y = fits_wcs.wcs_world2pix(ra, dec, 1)

    #   Perform aperture photometry at that position
    radius = determine_aperture_size(delta, header['secpix'])
    print x,y, radius

    apertures = CircularAperture((x,y), r=radius)
    phot_table = aperture_photometry(image_sub, apertures, mask=mask, error=error)
    print phot_table

    #   Convert flux to absolute magnitude
    mag = -2.5*log10(phot_table['aperture_sum'])
    if zp < 0:
        print "Bad zeropoint for %s" % fits_frame
    else:
        print mag, mag+zp
    print

#   World Domination
