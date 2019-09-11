from __future__ import print_function

import os
from glob import glob
from math import atan2, degrees
from sys import path, exit
import requests
import io
import logging

import numpy as np
from astropy.io import fits, votable
from astropy.constants import au
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.stats import SigmaClip, sigma_clipped_stats, mad_std

import matplotlib.pyplot as plt
import calviacat as cvc
from photutils.utils import calc_total_error
from photutils.background import Background2D, MedianBackground

path.insert(0, os.path.join(os.getenv('HOME'), 'git/neoexchange_stable/neoexchange'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
import django
from django.conf import settings
django.setup()
from core.models import Frame
from photometrics.external_codes import run_sextractor

logger = logging.getLogger(__name__)

def determine_images_and_catalogs(datadir, output=True):

    fits_files, fits_catalogs = None, None

    datadir = os.path.join(os.path.abspath(datadir), '')
    if os.path.exists(datadir) and os.path.isdir(datadir):
        fits_files = sorted(glob(datadir + '*e??.fits'))
        fits_catalogs = sorted(glob(datadir + '*e??_cat.fits'))
        if len(fits_files) == 0 and len(fits_catalogs) == 0:
            print("No FITS files and catalogs found in directory %s" % datadir)
            fits_files, fits_catalogs = [], []
        else:
            print("Found %d FITS files and %d catalogs" % ( len(fits_files), len(fits_catalogs)))
    else:
        print("Could not open directory %s" % datadir)
        fits_files, fits_catalogs = [], []

    return fits_files, fits_catalogs

def open_image(fits_file):

    header, image = (None, None)
    try:
        hdulist = fits.open(fits_file)
        header = hdulist[0].header
        image = hdulist[0].data
        hdulist.close()
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

def subtract_background(header, image, mask, bkg_map):
    #   Determine background and subtract
    if bkg_map:
        bkg_estimator = MedianBackground()
        sigma_clip = SigmaClip(sigma=3.)
        bkg = Background2D(image, (50, 50), filter_size=(3, 3), bkg_estimator=bkg_estimator, sigma_clip=sigma_clip, mask=mask)
        sky_level = bkg.background
        sky_sigma = bkg.background_rms
        print("Background & rms=", bkg.background_median, bkg.background_rms_median)
        effective_gain = header['gain'] * header['exptime']
        print("Gain=", effective_gain)
        error = calc_total_error(image, sky_sigma, effective_gain)
        image_sub = image - sky_level
    else:
        mean, median, std = sigma_clipped_stats(image, sigma=3.0, iters=3, mask=mask)
        print("Mean, median, std. dev=", mean, median, std)
        image_sub = image - median

    return image_sub

def determine_aperture_size(delta, pixscale):
    '''Determine the size of a comet-photometry standard 10,000km aperture for
    the passed pixel scale <pixscale> (in arcsec/pixel) and distance <delta> (in AU)'''

    Mm_in_pix = degrees(atan2(1000.,(au.to('km').value*delta))) * 3600.0 / pixscale
    aperture_size = 10.0 * Mm_in_pix

    return aperture_size

def interpolate_ephemeris(ephem_file, jd, with_rdot=True):
    '''Interpolate a JPL ephemeris CSV file
    This needs to be generated from the website with the 'Table Settings' showing:
        `Table Settings [change] :  	QUANTITIES=1,3,4,8,19,20,24; date/time format=BOTH; extra precision=YES`
    and then turned into a CSV file via:
        cut -c 2-18,19-36,38,39,41-54,55-68,69-77,79-87,88-97,98-106,107-113,114-120,121-137,148-165,177- --output-delimiter="," \
        horizons_results.txt > [comet]_ephem
    Returns: RA and Dec (in degrees), RA and Dec rates, Earth-object distance (delta; in AU), phase

    '''
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
    if with_rdot is True:
        (edate,ejd2,sun,moon,ra2,dec2,delta_ra,delta_dec,amass,ext,r,rdot,delta,deldot,phase) = line.split(',',15)[0:15]
    else:
        (edate,ejd2,sun,moon,ra2,dec2,delta_ra,delta_dec,az,alt,amass,ext,r,delta,phase) = line.split(',',15)[0:15]
    (edate,ejd1,sun,moon,ra1,dec1) = lastline.split(',', 6)[0:6]

    ra_dec_2 = SkyCoord(ra2, dec2, unit=(u.hourangle, u.deg))
    ra_dec_1 = SkyCoord(ra1, dec1, unit=(u.hourangle, u.deg))
    frac=(jd - float(ejd1)) / (float(ejd2) - float(ejd1))
    ra = ra_dec_1.ra + frac*(ra_dec_2.ra - ra_dec_1.ra)
    dec = ra_dec_1.dec + frac*(ra_dec_2.dec - ra_dec_1.dec)
    print (ra.to_string(unit=u.hour, sep=('h ', 'm ', 's')), dec.to_string(alwayssign=True, unit=u.degree, sep=('d ', "' ", '"')))
    return ra.degree, dec.degree, float(delta_ra), float(delta_dec), float(delta), float(phase)

def retrieve_zp_err(fits_frame):
    zp = -99
    zp_err = -99
    try:
        frame = Frame.objects.get(filename=fits_frame)
    except Frame.DoesNotExist:
        print("No DB record of %s" % fits_frame)
        exit(-1)
    except Frame.MultipleObjectsReturned:
        print("Multiple processed frame records found for %s" % fits_frame)
        exit(-1)
    if frame.zeropoint is not None:
        zp = frame.zeropoint
    if frame.zeropoint_err is not None:
        zp_err = frame.zeropoint_err

    return zp, zp_err


def make_CSS_catalogs(source_dir, dest_dir, fits_file, catalog_type='CSS:ASCII_HEAD', aperture=None):

    new_output_catalog = os.path.basename(fits_file)
    new_output_catalog = new_output_catalog.replace('[SCI]', '').replace('.fits', '_cat.ascii')
    new_output_catalog_path = os.path.join(dest_dir, new_output_catalog)

    if os.path.exists(new_output_catalog_path):
        if os.path.getsize(new_output_catalog_path) > 0:
            logger.info("Catalog {} already exists".format(new_output_catalog))
            return 0, new_output_catalog_path
    print("source_dir= {}\ndest_dir= {}\nfits_file= {}".format(source_dir, dest_dir, fits_file))
    logger.info("Creating new SExtractor catalog for {}".format(fits_file))
    sext_status = run_sextractor(source_dir, dest_dir, fits_file, binary=None, catalog_type=catalog_type, dbg=False, aperture=aperture)
    print(sext_status)
    if sext_status == 0:
        output_catalog = 'test.cat'
        output_catalog_path = os.path.join(dest_dir, output_catalog)

        # Rename catalog to permanent name

        logger.debug("Renaming %s to %s" % (output_catalog_path, new_output_catalog_path))
        os.rename(output_catalog_path, new_output_catalog_path)

    else:
        logger.error("Execution of SExtractor failed")
        return sext_status, -4

    return sext_status, new_output_catalog_path

def great_circle_distance(ra1, dec1, ra2, dec2):
    """Calculates the great circle distance between two points specified by
    (ra1, dec1) and (ra2, dec2) (assumed to be in degrees).
    Resulting separation is returned in degrees
    """

    ra1_rad, dec1_rad = np.deg2rad([ra1, dec1])
    ra2_rad, dec2_rad = np.deg2rad([ra2, dec2])
    distance_rad = np.arccos(np.sin(dec1_rad) * np.sin(dec2_rad) + np.cos(dec1_rad) * np.cos(dec2_rad) * np.cos(ra2_rad - ra1_rad))
    return np.rad2deg(distance_rad)

def calibrate_catalog(catfile, cat_center, trim_limits, table_format='ascii.sextractor', radius=0.5, flux_column='FLUX_ISOCOR', fluxerr_column='FLUXERR_ISOCOR'):

    FLUX2MAG = 2.5/np.log(10)

    # Read in SExtractor catalog and rename columns
    logger.info("Reading catalog {}".format(catfile))
    phot = Table.read(catfile, format=table_format)
    phot['ALPHAWIN_J2000'].name = 'RA'
    phot['DELTAWIN_J2000'].name = 'DEC'
    # Filter out sources without good extraction FLAGS and off chip
    mask1 = phot['FLAGS'] == 0
    mask2 = phot['XWIN_IMAGE'] > trim_limits[0]
    mask3 = phot['YWIN_IMAGE'] > trim_limits[1]
    mask4 = phot['XWIN_IMAGE'] <= trim_limits[2]
    mask5 = phot['YWIN_IMAGE'] <= trim_limits[3]
    mask = mask1 & mask2 & mask3 & mask4 & mask5    # AND all the masks together
    clean_phot = phot[mask]
    logger.debug("Size of input and filtered catalogs= {}, {}".format(len(phot), len(clean_phot)))

    # Create SkyCoord and filter down to find sources within the specified
    # radius (since out field is bigger than the maximum allowed in the PS1
    # catalog query)
    lco = SkyCoord(clean_phot['RA'], clean_phot['DEC'], unit='deg')
    lco_cut = clean_phot[great_circle_distance(cat_center.ra.deg, cat_center.dec.deg, clean_phot['RA'], clean_phot['DEC']) <= radius]
    lco_cut_coords = SkyCoord(lco_cut['RA'], lco_cut['DEC'], unit='deg')

    match_radius = 3.5*u.arcsec
    object_cat = lco_cut[great_circle_distance(cat_center.ra.deg, cat_center.dec.deg, lco_cut['RA'], lco_cut['DEC']) <= match_radius.to(u.deg).value]
    if len(object_cat) == 1:
        logger.debug("Match at x={:.3f}, y={:.3f}".format(object_cat['XWIN_IMAGE'][0], object_cat['YWIN_IMAGE'][0]))
        obj_mag = -2.5 * np.log10(object_cat[flux_column])
        obj_err = object_cat[fluxerr_column] / object_cat[flux_column] * FLUX2MAG
    else:
        logger.warn("Found unexpected number of target match ({})".format(len(object_cat)))
        obj_mag = obj_err = None
    ps1_db_file = catfile.replace('.ascii', '.db')
    if os.path.exists(ps1_db_file):
        logger.info("Using existing PS1 DB")
        ps1 = cvc.PanSTARRS1(ps1_db_file)
    else:
        logger.info("Fetching PS1 catalog around {} with radius {} deg".format(cat_center.to_string('decimal'), radius))
        ps1 = fetch_ps1_field(cat_center, radius)
    objids, distances = ps1.xmatch(lco_cut_coords)
    r_inst = -2.5 * np.log10(lco_cut[flux_column])
    r_err = lco_cut[fluxerr_column] / lco_cut[flux_column] * FLUX2MAG
    zp, C, unc, r, gmr, gmi = ps1.cal_color(objids, r_inst, 'r', 'g-r',  mlim=[11, 18], gmi_lim=[0.2, 1.4])
    plotfile = catfile.replace('cat.ascii', 'ps1_cc.png')
    plot_color_correction(C, zp, r, gmr, r_inst, filename=plotfile, filter_name='r')

    return zp, C, unc, r, gmr, gmi, obj_mag, obj_err

def fetch_ps1_field(cat_center, radius=0.5, max_records=50001, db_name='cat.db'):

    ps1 = cvc.PanSTARRS1(db_name)
    ps1.max_records = max_records

    params = dict(RA=cat_center.ra.deg, DEC=cat_center.dec.deg,
                      SR=radius, max_records=ps1.max_records,
                      ordercolumn1='ndetections',
                      descending1='on',
                      selectedColumnsCsv=','.join(ps1.table.columns))
    q = requests.get('https://archive.stsci.edu/panstarrs/search.php',
                         params=params)
    with io.BytesIO(q.text.encode()) as xml:
        try:
            tab = votable.parse_single_table(xml).to_table()
        except Exception as e:
            logger.error(q.text)
            return None

    tab['objname'] = np.array(
        [str(x.decode()) for x in tab['objname']])
    tab['objid'] = np.array(
        [str(x.decode()) for x in tab['objid']], int)
    tab['rastack'] = np.array(
        [str(x.decode()) for x in tab['rastack']])
    tab['decstack'] = np.array(
        [str(x.decode()) for x in tab['decstack']])

    logger.debug('Updating {} with {} sources.'.format(
        ps1.table.name, len(tab)))

    ps1.db.executemany('''
    INSERT OR IGNORE INTO {}
      VALUES({})
    '''.format(ps1.table.name, ','.join('?' * len(ps1.table.columns))),
        tab)
    ps1.db.commit()

    return ps1

def plot_color_correction(C, zp, mag, color_index, mag_inst, filename='lco-ps1-color-corrected.png', filter_name='g'):
    fig = plt.figure(1)
    fig.clear()
    ax = fig.gca()
    ax.scatter(color_index, mag - mag_inst, marker='.', color='k')
    x = np.linspace(0, 1.5)
    ax.plot(x, C * x + zp, 'r-')
    ylabel_text = r'$'+filter_name+'-'+filter_name+r'_{\rm inst}$ (mag)'
    plt.setp(ax, xlabel='$g-r$ (mag)', ylabel=ylabel_text)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)

    # Plot zoomed version
    fig.clear()
    ax = fig.gca()
    ax.scatter(color_index, mag - mag_inst, marker='.', color='k')
    x = np.linspace(0, 1.5)
    ax.plot(x, C * x + zp, 'r-')
    ax.set_ylim(zp-0.25, zp+0.5)
    plt.setp(ax, xlabel='$g-r$ (mag)', ylabel=ylabel_text)
    plt.tight_layout()
    filename_clip = os.path.splitext(filename)[0] + '_clip' + os.path.splitext(filename)[1]
    plt.savefig(filename_clip, dpi=150)
    return
