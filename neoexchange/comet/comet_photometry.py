#!/usr/bin/env python
from __future__ import print_function

import os
from sys import path, exit
from glob import glob
from math import log10, log, sqrt, pow

from astropy.io import fits
import numpy as np
from astropy.stats import sigma_clipped_stats, mad_std
from astropy.wcs import WCS
from astropy.wcs._wcs import InvalidTransformError
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.coordinates import SkyCoord
from astropy import units as u

from photutils import CircularAperture, SkyCircularAperture, aperture_photometry
from photutils.utils import calc_total_error
from photutils.background import Background2D, MedianBackground

path.insert(0, os.path.join(os.getenv('HOME'), 'git/neoexchange_stable/neoexchange'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
import django
from django.conf import settings
django.setup()

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes
from comet_subs import *

#comet = '67P'
comet = '243P'
datadir = os.path.join(os.getenv('HOME'), 'Asteroids', comet, 'Pipeline', 'Temp')
datadir = os.path.join(os.path.abspath(datadir), '')
if not os.path.exists(datadir):
    os.makedirs(datadir)
bkg_map = True

FLUX2MAG = 2.5/log(10)

# Find all images
images, catalogs = determine_images_and_catalogs(datadir)

# Create log file, write header
log_file = os.path.join(datadir, comet + '_phot.log')

if os.path.exists(log_file):
    os.remove(log_file)
log_fh = open(log_file, 'w')
print("# Filename                               Filter JD            MJD-57000.0         RA (J2000.0) Dec        X (pixels) Y        Radius  Mag (coords) Mag+ZP   Magerr   Mag (Skypos) Mag+ZP  Magerr     ZP      ZPerr", file=log_fh)
#                  elp1m008-fl05-20160127-0273-e90.fits   r'   2457416.02037 415.520368588 185.611169209 +08.200143039 2001.3375 2067.4000   23.4026 -11.84046 +16.11954   +0.08323 -11.84523 +16.11477  +0.08284   27.96000

# Loop over all images
for fits_fpath in images:
    fits_frame = os.path.basename(fits_fpath)
    print("Processing %s" % fits_frame)

    # Determine if good zeropoint
    zp, zp_err = retrieve_zp_err(fits_frame)

    #   Open image
    header, image = open_image(fits_fpath)
    
    #   Make bad pixel mask of saturated and very low values
    low_clip = 100.0
    if bkg_map:
        low_clip = -50.0
    sat_level = header.get('saturate', 55000)
    mask = make_mask(image, sat_level, low_clip)

    #   Determine background and subtract
    if bkg_map:
        bkg_estimator = MedianBackground()
        bkg = Background2D(image, (50, 50), filter_size=(3, 3), bkg_estimator=bkg_estimator, mask=mask)
        sky_level = bkg.background
        sky_sigma = bkg.background_rms
        effective_gain = header['gain']
        print("Gain=", effective_gain)
        error = calc_total_error(image, sky_sigma, effective_gain)
        image_sub = image - sky_level
    else:
        mean, median, std = sigma_clipped_stats(image, sigma=3.0, iters=3, mask=mask)
        print("Mean, median, std. dev=", mean, median, std)
        image_sub = image - median

    #   Determine position of comet in this frame
    if 'mpccode' in header:
        sitecode = header['mpccode']
        siteid = 'CSS'
        instrument = '703_STA10k'
    else:
        sitecode = LCOGT_domes_to_site_codes(header['siteid'], header['encid'], header['telid'])
        siteid = header['siteid'].upper()
        instrument = header['instrume'].lower()
    ephem_file = comet + "_ephem_%s_%s_%s.txt" % ( siteid, instrument, sitecode.upper())
    print("Reading ephemeris from", ephem_file)
    ephem_file = os.path.join(os.getenv('HOME'), 'Asteroids', ephem_file)

    if 'mjdmid' in header:
        mjd_utc_mid = header['mjdmid']
        date_obs = header['date-mid']
    else:
        mjd_utc_mid = header['mjd-obs'] + (header['exptime']/2.0/86400.0)
        date_obs =  header['date-obs']
    jd_utc_mid = mjd_utc_mid + 2400000.5
    print("JD=", jd_utc_mid, date_obs, header['exptime'], header['exptime']/2.0/86400.0)
    ra, dec, del_ra, del_dec, delta, phase = interpolate_ephemeris(ephem_file, jd_utc_mid)
    print("RA, Dec, delta for frame=", ra, dec, delta)

    try:
        fits_wcs = WCS(header)
    except InvalidTransformError:
        print("Changing WCS CTYPEi to TPV")
        if 'CTYPE1' in header and 'CTYPE2' in header:
            header['CTYPE1'] = 'RA---TPV'
            header['CTYPE2'] = 'DEC--TPV'
            fits_wcs = WCS(header)
        else:
            print("Could not find needed WCS header keywords")
            exit(-2)
    x, y = fits_wcs.wcs_world2pix(ra, dec, 1)
    pixscale = proj_plane_pixel_scales(fits_wcs).mean()*3600.0
    print("Pixelscales=", pixscale, header.get('secpix', ''))

    #   Determine aperture size and perform aperture photometry at the position
    radius = determine_aperture_size(delta, pixscale)
    print("X, Y, Radius=", x, y, radius)

    apertures = CircularAperture((x,y), r=radius)
    phot_table = aperture_photometry(image_sub, apertures, mask=mask, error=error)
    print(phot_table)

    sky_position = SkyCoord(ra, dec, unit='deg', frame='icrs')
    sky_apertures = SkyCircularAperture(sky_position, r=radius * pixscale * u.arcsec)
    skypos_phot_table = aperture_photometry(image_sub, sky_apertures, wcs=fits_wcs, mask=mask, error=error)
    print("%13.7f %16.8f %s" % (skypos_phot_table['aperture_sum'].data[0], skypos_phot_table['aperture_sum_err'].data[0], sky_position.to_string('hmsdms')))

    #   Convert flux to absolute magnitude
    try:
        mag = -2.5*log10(phot_table['aperture_sum'])
        magerr = FLUX2MAG * (phot_table['aperture_sum_err'] / phot_table['aperture_sum'])
    except ValueError:
        print("-ve flux value")
        mag = magerr = -99.0
    try:
        skypos_mag = -2.5*log10(skypos_phot_table['aperture_sum'])
        skypos_magerr = FLUX2MAG * (skypos_phot_table['aperture_sum_err'] / skypos_phot_table['aperture_sum'])
    except ValueError:
        print("-ve flux value")
        skypos_mag = skypos_magerr = -99.0

    # Get observed filter, Connvert 'p' to prime
    obs_filter = header['filter']
    obs_filter = obs_filter[:-1] + obs_filter[-1].replace("p", "'")
    if zp < 0 and zp_err < 0:
        print("Bad zeropoint for %s" % fits_frame)
        abs_mag = abs_mag_err = -99.0
        abs_skypos_mag = abs_skypos_mag_err = -99.0
    elif mag < -90:
        print("Bad magntiude determination")
    else:
        abs_mag = mag+zp
        abs_mag_err = sqrt(pow(magerr, 2) + pow(zp_err, 2))
        abs_skypos_mag = skypos_mag+zp
        abs_skypos_mag_err = sqrt(pow(skypos_magerr, 2) + pow(zp_err, 2))
        if obs_filter == "r'":
            print("Correcting r' magnitude to R")
            abs_mag = abs_mag - 0.2105
        print(mag, abs_mag, abs_mag_err, skypos_mag, abs_skypos_mag, abs_skypos_mag_err, zp, zp_err)


    log_format = "%s   %3s  %.5f %.9f %013.9f %+013.9f %9.4f %9.4f %9.4f %+8.5f %8.5f  %9.5f %+9.5f %+9.5f %+9.5f  %7.3f %7.3f"
    log_line = log_format % (fits_frame, obs_filter, jd_utc_mid, mjd_utc_mid-57000.0, ra, dec, x, y, radius, mag, abs_mag, abs_mag_err, skypos_mag, abs_skypos_mag, abs_skypos_mag_err, zp, zp_err)
    print(log_line, file=log_fh)
    print

#   World Domination
log_fh.close()
