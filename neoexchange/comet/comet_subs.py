from __future__ import print_function
import os
from glob import glob
from math import atan2, degrees
from sys import path, exit

import numpy as np
from astropy.io import fits
from astropy.constants import au
from astropy import units as u
from astropy.coordinates import SkyCoord

path.insert(0, os.path.join(os.getenv('HOME'), 'GIT/neoexchange/neoexchange'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
import django
from django.conf import settings
django.setup()
from core.models import Frame

def determine_images_and_catalogs(datadir, output=True):

    fits_files, fits_catalogs = None, None

    datadir = os.path.join(os.path.abspath(datadir), '')
    if os.path.exists(datadir) and os.path.isdir(datadir):
        fits_files = sorted(glob(datadir + '*e??.fits'))
        fits_catalogs = sorted(glob(datadir + '*e??_cat.fits'))
        if len(fits_files) == 0 and len(fits_catalogs) == 0:
            print("No FITS files and catalogs found in directory %s" % datadir)
            fits_files, fits_catalogs = None, None
        else:
            print("Found %d FITS files and %d catalogs" % ( len(fits_files), len(fits_catalogs)))
    else:
        print("Could not open directory %s" % datadir)
        fits_files, fits_catalogs = None, None

    return fits_files, fits_catalogs

def open_image(fits_file):

    header, image = (None, None)
    try:
        hdulist = fits.open(fits_file)
        header = hdulist[0].header
        image = hdulist[0].data
    except IOError as e:
        print("Unable to open FITS file %s (Reason=%s)" % (fits_file, e))

    return header, image

def make_mask(image, saturation, low_clip=0.0):
    #   Make bad pixel mask of saturated and very low values
    sat_mask = np.where(image >= saturation, True, False)
    frac_sat_mask = (sat_mask == True).sum()
    percent_sat_mask = (frac_sat_mask / float(sat_mask.size)) * 100.0

    low_mask = np.where(image < low_clip, True, False)
    frac_low_mask = (low_mask == True).sum()
    percent_low_mask = (frac_low_mask / float(low_mask.size)) * 100.0

    print("Masked %d (%.1f%%) saturated and %d (%.1f%%) low pixels" \
        % ( frac_sat_mask, percent_sat_mask, frac_low_mask, percent_low_mask))

    mask = sat_mask + low_mask

    return mask

def determine_aperture_size(delta, pixscale):
    '''Determine the size of a comet-photometry standard 10,000km aperture for
    the passed pixel scale <pixscale> (in arcsec/pixel) and distance <delta> (in AU)'''

    Mm_in_pix = degrees(atan2(1000.,(au.to('km').value*delta))) * 3600.0 / pixscale
    aperture_size = 10.0 * Mm_in_pix

    return aperture_size

def interpolate_ephemeris(ephem_file, jd):

    ra = dec = delta = phase = None
    try:
        ephem_fh = open(ephem_file)
    except IOError:
        return None
    for line in ephem_fh.readlines():
        tmp = line.split(',')
        if len(tmp) < 2:
            continue
        try:
            float(tmp[1]) < 2450000
        except ValueError:
            continue
        if float(tmp[1]) > jd:
            break
        lastline = line
    ephem_fh.close()

    # Read last two lines (one after the passed JD and the one before) and 
    # interpolate RA, Dec between the two.
    # XXX TODO Interpolate other values also
    (edate,ejd2,sun,moon,ra2,dec2,delta_ra,delta_dec,amass,ext,r,rdot,delta,deldot,phase) = line.split(',',15)[0:15]
    (edate,ejd1,sun,moon,ra1,dec1) = lastline.split(',', 6)[0:6]

    ra_dec_2 = SkyCoord(ra2, dec2, unit=(u.hourangle, u.deg))
    ra_dec_1 = SkyCoord(ra1, dec1, unit=(u.hourangle, u.deg))
    frac=(jd - float(ejd1)) / (float(ejd2) - float(ejd1))
    ra = ra_dec_1.ra + frac*(ra_dec_2.ra - ra_dec_1.ra)
    dec = ra_dec_1.dec + frac*(ra_dec_2.dec - ra_dec_1.dec)
    print (ra.to_string(unit=u.hour, sep=('h ', 'm ', 's')), dec.to_string(alwayssign=True, unit=u.degree, sep=('d ', "' ", '"')))
    return ra.degree, dec.degree, float(delta_ra), float(delta_dec), float(delta), float(phase)

def retrieve_zp_err(fits_frame):
    try:
        frame = Frame.objects.get(filename=fits_frame)
    except Frame.DoesNotExist:
        print("No DB record of %s" % fits_frame)
        exit(-1)
    except Frame.MultipleObjectsReturned:
        print("Multiple processed frame records found for %s" % fits_frame)
        exit(-1)
    return frame.zeropoint, frame.zeropoint_err
