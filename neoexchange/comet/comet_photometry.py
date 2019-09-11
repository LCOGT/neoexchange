#!/usr/bin/env python
from __future__ import print_function

import os
from sys import path, exit
from glob import glob
from math import log10, log, sqrt, pow

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from astropy.wcs._wcs import InvalidTransformError
from astropy.wcs.utils import proj_plane_pixel_scales

from photutils import CircularAperture, SkyCircularAperture, aperture_photometry

path.insert(0, os.path.join(os.getenv('HOME'), 'git/neoexchange_comet/neoexchange'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
import django
from django.conf import settings
django.setup()

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes
from comet_subs import *

#comet = '67P'
#comet = '243P'
#comet_color = 0.56
comet = '46P'

datadir = os.path.join(os.getenv('HOME'), 'Asteroids', comet, 'Pipeline' ) #, 'Temp')
datadir = os.path.join(os.path.abspath(datadir), '')
if not os.path.exists(datadir):
    os.makedirs(datadir)
bkg_map = True

configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

FLUX2MAG = 2.5/log(10)

# Find all images
images, catalogs = determine_images_and_catalogs(datadir)

# Create log file, write header
log_file = os.path.join(datadir, comet + '_phot.log')

if os.path.exists(log_file):
    os.remove(log_file)
log_fh = open(log_file, 'w')
print('# Filename                               Filter JD            MJD-57000.0         RA (J2000.0) Dec             RA (J2000.0) Dec         X (pixels) Y      Radius (pixels/") Mag (coords) Mag+ZP   Magerr   Mag (Skypos) Mag+ZP  Magerr    ZP       ZPerr Mag(SEX) Magerr Mag(PS1 CC) Magerr ZP(PS1) ZPerr(PS1) C(PS1)', file=log_fh)
#                  elp1m008-fl05-20160127-0273-e90.fits   r'   2457416.02037 415.520368588 185.611169209 +08.200143039 2001.3375 2067.4000   23.4026 -11.84046 +16.11954   +0.08323 -11.84523 +16.11477  +0.08284   27.96000

# Loop over all images
for fits_fpath in images:
    fits_frame = os.path.basename(fits_fpath)
    print("Processing %s" % fits_frame)

    # Determine if good zeropoint
    zp, zp_err = retrieve_zp_err(fits_frame)

    #   Open image
    header, image = open_image(fits_fpath)

    # Determine site id, MPC site code, instrument and set catalog type for later
    if 'mpccode' in header:
        sitecode = header['mpccode']
        siteid = 'CSS'
        instrument = sitecode.upper() + '_STA10k'
        cat_type = 'CSS:ASCII_HEAD'
    else:
        sitecode = LCOGT_domes_to_site_codes(header['siteid'], header['encid'], header['telid'])
        siteid = header['siteid'].upper()
        instrument = header['instrume'].lower()
        cat_type = 'COMETCAM:ASCII_HEAD'
        default_pixelscale = 0.1838220980370765

    #   Determine position of comet in this frame
    ephem_file = comet + "_ephem_%s_%s_%s.txt" % ( siteid, instrument, sitecode.upper())
    print("Reading ephemeris from", ephem_file)
    ephem_file = os.path.join(os.getenv('HOME'), 'Asteroids', ephem_file)

    if 'mjdmid' in header:
        mjd_utc_mid = header['mjdmid']
        date_obs = Time(mjd_utc_mid, format='mjd', scale='utc')
        date_obs.format = 'isot'
    else:
        date_obs = Time(header['date-obs'], format='isot', scale='utc')
        date_obs += header['exptime']/2.0/86400.0
        mjd_utc_mid = date_obs.mjd
        date_obs.format = 'isot'
    jd_utc_mid = mjd_utc_mid + 2400000.5
    print("JD=", jd_utc_mid, date_obs, header['exptime'], header['exptime']/2.0/86400.0)
    ra, dec, del_ra, del_dec, delta, phase = interpolate_ephemeris(ephem_file, jd_utc_mid, with_rdot=False)
    sky_position = SkyCoord(ra, dec, unit='deg', frame='icrs')
    print("RA, Dec, delta for frame=", ra, dec, delta)

    # Get observed filter, Convert 'p' to prime
    obs_filter = header['filter']
    obs_filter = obs_filter[:-1] + obs_filter[-1].replace("p", "'")


    #   Make bad pixel mask of saturated and very low values
    low_clip = 100.0
    if bkg_map:
        low_clip = -50.0
    sat_level = header.get('saturate', 55000)
    mask = make_mask(image, sat_level, low_clip)

    image_sub = subtract_background(header, image, mask, bkg_map)

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

    if header.get('wcserr', 99) == 0:
        pixscale = proj_plane_pixel_scales(fits_wcs).mean()*3600.0
    else:
        # Bad WCS
        print("WCS was bad, predicted positions will be wrong and assuming pixelscale")
        pixscale = default_pixelscale

    print("Pixelscales=", pixscale, header.get('secpix', ''))

    trim_limits = [0, 0, fits_wcs.pixel_shape[0], fits_wcs.pixel_shape[1]]

    x, y = fits_wcs.wcs_world2pix(ra, dec, 1)


    #   Determine aperture size and perform aperture photometry at the position
    radius = determine_aperture_size(delta, pixscale)
    print("Pixel photometry:")
    print("X, Y, Radius (pixels, arcsec)= {:.3f} {:.3f} {:9.5f} {:9.5f}".format(x, y, radius, radius*pixscale))

    if header.get('wcserr', 99) == 0:

        apertures = CircularAperture((x,y), r=radius)
        phot_table = aperture_photometry(image_sub, apertures, mask=mask, method='exact', error=error)
        print(phot_table)

        print("Sky Coords aperture photometry:")
        sky_apertures = SkyCircularAperture(sky_position, r=radius * pixscale * u.arcsec)
        skypos_phot_table = aperture_photometry(image_sub, sky_apertures, wcs=fits_wcs, mask=mask, method='exact', error=error)
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

        if zp < 0 and zp_err < 0:
            print("Bad zeropoint for %s" % fits_frame)
            abs_mag = abs_mag_err = -99.0
            abs_skypos_mag = abs_skypos_mag_err = -99.0
        elif mag < -90:
            print("Bad magnitude determination")
        else:
            abs_mag = mag+zp
            abs_mag_err = sqrt(pow(magerr, 2) + pow(zp_err, 2))
            abs_skypos_mag = skypos_mag+zp
            abs_skypos_mag_err = sqrt(pow(skypos_magerr, 2) + pow(zp_err, 2))
            if obs_filter == "r'":
                print("Correcting r' magnitude to R")
                abs_mag = abs_mag - 0.2105
            print(mag, abs_mag, abs_mag_err, skypos_mag, abs_skypos_mag, abs_skypos_mag_err, zp, zp_err)

    # Make SExtractor catalog
    status, catalog = make_CSS_catalogs(configs_dir, datadir, fits_fpath, catalog_type=cat_type, aperture=radius*2.0)
    if status == 0:
        if header.get('wcserr', 99) == 0:
            zp_PS1, C_PS1, zp_err_PS1, r, gmr, gmi, obj_mag, obj_err = calibrate_catalog(catalog, sky_position, trim_limits, flux_column='FLUX_APER', fluxerr_column='FLUXERR_APER')
            print("ZP, color slope, uncertainty= {:7.3f} {:.6f} {:.3f}".format(zp_PS1, C_PS1, zp_err_PS1))
            rmag_cc = (C_PS1 * comet_color) + zp_PS1 + obj_mag
            rmag_err_cc = sqrt(pow(obj_err, 2) + pow(zp_err_PS1, 2))
        else:
            mag = magerr = -99.0
            abs_mag = abs_mag_err = -99.0
            abs_skypos_mag = abs_skypos_mag_err = -99.0
            skypos_mag = skypos_magerr = -99.0
            obj_mag = obj_err = -99.0
            rmag_cc = rmag_err_cc = -99.0
            zp_PS1 = C_PS1 = zp_err_PS1 = -99.0

    log_format = "%s   %3s  %.5f %.9f %013.9f %+013.9f %s %9.4f %9.4f %8.3f (%6.3f) %+9.5f %8.5f  %9.5f %+9.5f %9.5f %9.5f  %7.3f %7.3f %7.3f %7.3f %7.4f    %7.3f %7.3f %7.3f    %+7.5f"
    log_line = log_format % (fits_frame, obs_filter, jd_utc_mid, mjd_utc_mid-57000.0, \
        ra, dec, sky_position.to_string('hmsdms', sep=' ', precision=4), x, y, radius, radius*pixscale, \
        mag, abs_mag, abs_mag_err, skypos_mag, abs_skypos_mag, abs_skypos_mag_err, zp, zp_err,\
        obj_mag, obj_err, rmag_cc, rmag_err_cc, zp_PS1, zp_err_PS1, C_PS1)
    print(log_line, file=log_fh)
    print

#   World Domination
log_fh.close()
