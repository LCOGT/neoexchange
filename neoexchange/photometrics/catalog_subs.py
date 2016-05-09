'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

catalog_subs.py -- Code to retrieve source detection infomation from FITS catalogs.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import logging
import os
from datetime import datetime, timedelta
from math import sqrt, log10, log
from collections import OrderedDict

from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import Angle
from astroquery.vizier import Vizier
import astropy.units as u
import astropy.coordinates as coord
from astropy.wcs import WCS

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes
from core.models import CatalogSources, Frame

logger = logging.getLogger(__name__)

def call_cross_match_and_zeropoint(catfile, cat_name = "UCAC4",  set_row_limit = 10000, rmag_limit = "<=15.0"):

    if type(catfile) == str:

        header, table = extract_catalog(catfile)

    else:

        header, table = (catfile[0], catfile[1])

    cat_table, cat_name = get_vizier_catalog_table(header['field_center_ra'], header['field_center_dec'], header['field_width'], header['field_height'], cat_name, set_row_limit, rmag_limit)

    cross_match_table = cross_match(table, cat_table, cat_name)

    avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table)

    return header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc

def get_vizier_catalog_table(ra, dec, set_width, set_height, cat_name = "UCAC4", set_row_limit = 10000, rmag_limit = "<=15.0"):
    '''Pulls a catalog from Vizier'''

    #query Vizier on a region of the sky with ra and dec coordinates of a specified catalog
    while set_row_limit < 100000:

        query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag":rmag_limit, "r1mag":rmag_limit})
        result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=[cat_name])
#        print len(result), result.return_value

        #resulting catalog table
        if len(result) < 1:
            if "PPMXL" in cat_name:
                cat_name = "UCAC4"
                result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=[cat_name])
                if len(result) > 0:
                    cat_table = result[0]
                else:
                    zeros_list = list(0.0 for i in range(0,100000))
                    zeros_int_list = list(0 for i in range(0,100000))
                    cat_table = Table([zeros_list, zeros_list, zeros_list, zeros_int_list, zeros_int_list], names=('_RAJ2000', '_DEJ2000', 'rmag', 'flags', 'e_rmag'))
            else:
                cat_name = "PPMXL"
                result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=[cat_name])
                if len(result) > 0:
                    cat_table = result[0]
                else:
                    zeros_list = list(0.0 for i in range(0,100000))
                    zeros_int_list = list(0 for i in range(0,100000))
                    cat_table = Table([zeros_list, zeros_list, zeros_list, zeros_int_list], names=('_RAJ2000', '_DEJ2000', 'r2mag', 'fl'))
        else:
            cat_table = result[0]

        #if didn't get all of the table, try again with a larger row limit
        if len(cat_table) == set_row_limit:
            set_row_limit += 10000
            query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag":rmag_limit, "r1mag":rmag_limit})
            result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, catalog=[cat_name])

            #resulting catalog table
            cat_table = result[0]
        else:
            break

#    print cat_table, cat_name

    return cat_table, cat_name

def cross_match(FITS_table, cat_table, cat_name = "UCAC4", cross_match_diff_threshold = 0.001):
    '''Cross matches RA and Dec for sources in two catalog tables. Every source in the shorter length catalog is cross matched with a source in the longer length catalog. Cross matches with RA or Dec differences < 0.001 are not included in the final output table. Outputs a table of RA, Dec, and r-mag for each cross-matched source.'''

    ra_min_diff_threshold = 1.0
    dec_min_diff_threshold = 1.0
    ra_min_diff = ra_min_diff_threshold
    dec_min_diff = dec_min_diff_threshold
    dec_cat_1 = 0.0
    dec_cat_2 = 0.0
    ra_cat_1 = 0.0
    ra_cat_2 = 0.0
    rmag_cat_1 = 0.0
    rmag_cat_2 = 0.0
    cross_match_list = []

    if len(FITS_table) >= len(cat_table):
        table_1 = cat_table
        table_2 = FITS_table
        if "PPMXL" in cat_name:
            RA_table_1 = table_1['_RAJ2000']
            Dec_table_1 = table_1['_DEJ2000']
            rmag_table_1 = table_1['r2mag']
            flags_table_1 = table_1['fl']
            rmag_err_table_1 = table_1['_RAJ2000'] * 0 #PPMXL does not have r mag errors, so copy RA table column and turn values all to zeros
            RA_table_2 = table_2['obs_ra']
            Dec_table_2 = table_2['obs_dec']
            rmag_table_2 = table_2['obs_mag']
            flags_table_2 = table_2['flags']
            rmag_err_table_2 = 'nan'
        else:
            RA_table_1 = table_1['_RAJ2000']
            Dec_table_1 = table_1['_DEJ2000']
            rmag_table_1 = table_1['rmag']
            flags_table_1 = table_1['_RAJ2000'] * 0 #UCAC4 does not have flags, so copy RA table column and turn values all to zeros
            rmag_err_table_1 = table_1['e_rmag']
            RA_table_2 = table_2['obs_ra']
            Dec_table_2 = table_2['obs_dec']
            rmag_table_2 = table_2['obs_mag']
            flags_table_2 = table_2['flags']
            rmag_err_table_2 = 'nan'
    else:
        table_1 = FITS_table
        table_2 = cat_table
        if "PPMXL" in cat_name:
            RA_table_1 = table_1['obs_ra']
            Dec_table_1 = table_1['obs_dec']
            rmag_table_1 = table_1['obs_mag']
            flags_table_1 = table_1['flags']
            rmag_err_table_1 = 'nan'
            RA_table_2 = table_2['_RAJ2000']
            Dec_table_2 = table_2['_DEJ2000']
            rmag_table_2 = table_2['r2mag']
            flags_table_2 = table_2['fl']
            rmag_err_table_2 = table_2['_RAJ2000'] * 0 #PPMXL does not have r mag errors, so copy RA table column and turn values all to zeros
        else:
            RA_table_1 = table_1['obs_ra']
            Dec_table_1 = table_1['obs_dec']
            rmag_table_1 = table_1['obs_mag']
            flags_table_1 = table_1['flags']
            rmag_err_table_1 = 'nan'
            RA_table_2 = table_2['_RAJ2000']
            Dec_table_2 = table_2['_DEJ2000']
            rmag_table_2 = table_2['rmag']
            flags_table_2 = table_2['_RAJ2000'] * 0 #UCAC4 does not have flags, so copy RA table column and turn values all to zeros
            rmag_err_table_2 = table_2['e_rmag']

    y = 0
    for value in Dec_table_1:
        if flags_table_1[y] < 1:
            rmag_table_1_temp = rmag_table_1[y]
            z = 0
            for source in Dec_table_2:
                if flags_table_2[z] < 1:
                    rmag_table_2_temp = rmag_table_2[z]
                    if abs(source - value) < dec_min_diff:
                        dec_min_diff = abs(source - value)
                        ra_table_1_temp = RA_table_1[y]
                        ra_table_2_temp = RA_table_2[z]
                        if abs(ra_table_1_temp - ra_table_2_temp) < ra_min_diff:
                            ra_min_diff = abs(ra_table_1_temp - ra_table_2_temp)
                            dec_cat_1 = value
                            dec_cat_2 = source
                            ra_cat_1 = ra_table_1_temp
                            ra_cat_2 = ra_table_2_temp
                            rmag_cat_1 = rmag_table_1_temp
                            rmag_cat_2 = rmag_table_2_temp
                            rmag_diff = abs(rmag_cat_1 - rmag_cat_2)
                            if rmag_err_table_1 != 'nan':
                                rmag_error = rmag_err_table_1[y] / 100.0
                            else:
                                rmag_error = rmag_err_table_2[z] / 100.0
                z += 1
        if ra_min_diff < cross_match_diff_threshold and dec_min_diff < cross_match_diff_threshold:
            cross_match_list.append((ra_cat_1, ra_cat_2, ra_min_diff, dec_cat_1, dec_cat_2, dec_min_diff, rmag_cat_1, rmag_cat_2, rmag_error, rmag_diff))
        y += 1
        ra_min_diff = ra_min_diff_threshold
        dec_min_diff = dec_min_diff_threshold

    cross_match_table = Table(rows=cross_match_list, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

    return cross_match_table

def get_zeropoint(cross_match_table):
    '''Computes a zeropoint from the two catalogues in 'cross_match_table' and iterates until all outliers are thrown out.'''

    avg_zeropoint = 40.0
    std_zeropoint = 10.0
    num_iter = 0
    r_mag_diff_threshold = 40.0

    while num_iter < 800:

        if std_zeropoint > 0.1:
            count = 0
            sum_r_mag_mean_numerator = 0.0
            sum_r_mag_mean_denominator = 0.0
            std_zeropoint_numerator = 0.0
            std_zeropoint_denominator = 0.0

            y = 0
            for value in cross_match_table['r mag diff']:
                if cross_match_table['r mag Cat 1'][y] != 'nan' and cross_match_table['r mag Cat 2'][y] != 'nan':
                    if abs(value - avg_zeropoint) < r_mag_diff_threshold:
                        if cross_match_table['r mag err'][y] < 0.01:
                            cross_match_table['r mag err'][y] += 0.001
                        sum_r_mag_mean_numerator += (value / cross_match_table['r mag err'][y])
                        sum_r_mag_mean_denominator += (1.0 / cross_match_table['r mag err'][y])
                        count += 1
                        num_in_calc = count
                y += 1

            if count > 0:
                avg_zeropoint = sum_r_mag_mean_numerator / sum_r_mag_mean_denominator #weighted mean zeropoint

            y = 0
            for value in cross_match_table['r mag diff']:
                if cross_match_table['r mag Cat 1'][y] != 'nan' and cross_match_table['r mag Cat 2'][y] != 'nan':
                    if abs(value - avg_zeropoint) < r_mag_diff_threshold:
                        std_zeropoint_numerator += ((1.0 / cross_match_table['r mag err'][y]) * (cross_match_table['r mag diff'][y] - avg_zeropoint)**2)
                        std_zeropoint_denominator += (1.0 / cross_match_table['r mag err'][y])
                y += 1

            if count > 0:
                std_zeropoint = sqrt(std_zeropoint_numerator / (((float(count) - 1)/float(count)) * std_zeropoint_denominator))

        r_mag_diff_threshold -= 0.05
        num_iter += 1

    return avg_zeropoint, std_zeropoint, count, num_in_calc


class FITSHdrException(Exception):
    '''Raised when a required FITS header keyword is missing'''

    def __init__(self, keyword):
        self.keyword = keyword

    def __str__(self):
        return "Required keyword '" + self.keyword + "' missing"

class FITSTblException(Exception):
    '''Raised when a required FITS table column is missing'''

    def __init__(self, column):
        self.column = column

    def __str__(self):
        return "Required column '" + self.column + "' missing"

def oracdr_catalog_mapping():
    '''Returns two dictionaries of the mapping between the FITS header and table
    items and CatalogItem quantities for LCOGT ORAC-DR pipeline format catalog
    files.'''

    header_dict = { 'site_id'    : 'SITEID',
                    'enc_id'     : 'ENCID',
                    'tel_id'     : 'TELID',
                    'instrument' : 'INSTRUME',
                    'filter'     : 'FILTER',
                    'framename'  : 'ORIGNAME',
                    'exptime'    : 'EXPTIME',
                    'obs_date'   : 'DATE-OBS',
                    'field_center_ra' : 'RA',
                    'field_center_dec' : 'DEC',
                    'field_width' : 'SEXIMASX',
                    'field_height' : 'SEXIMASY',
                    'pixel_scale' : 'SECPIX',
                    'zeropoint'  : 'L1ZP',
                    'zeropoint_err' : 'L1ZPERR',
                    'zeropoint_src' : 'L1ZPSRC',
                    'fwhm'          : 'L1FWHM',
                    'astrometric_fit_rms'    : 'WCSRDRES',
                    'astrometric_fit_status' : 'WCSERR',
                    'astrometric_fit_nstars' : 'WCSMATCH',
                    'astrometric_catalog'    : 'WCCATTYP',
                    'gain'          : 'GAIN',
                    'saturation'    : 'SATURATE'
                  }

    table_dict = OrderedDict([
                    ('ccd_x'         , 'X_IMAGE'),
                    ('ccd_y'         , 'Y_IMAGE'),
                    ('obs_ra'        , 'ALPHA_J2000'),
                    ('obs_dec'       , 'DELTA_J2000'),
                    ('obs_ra_err'    , 'ERRX2_WORLD'),
                    ('obs_dec_err'   , 'ERRY2_WORLD'),
                    ('major_axis'    , 'A_IMAGE'),
                    ('minor_axis'    , 'B_IMAGE'),
                    ('ccd_pa'        , 'THETA_IMAGE'),
                    ('obs_mag'       , 'FLUX_AUTO'),
                    ('obs_mag_err'   , 'FLUXERR_AUTO'),
                    ('obs_sky_bkgd'  , 'BACKGROUND'),
                    ('flags'         , 'FLAGS'),
                    ('flux_max'      , 'FLUX_MAX'),
                    ('threshold'     , 'THRESHOLD'),
                 ])

    return header_dict, table_dict

def fitsldac_catalog_mapping():
    '''Returns two dictionaries of the mapping between the FITS header and table
    items and CatalogItem quantities for FITS_LDAC format catalog files (as used
    by SCAMP).'''

    header_dict = { 'site_id'    : 'SITEID',
                    'enc_id'     : 'ENCID',
                    'tel_id'     : 'TELID',
                    'instrument' : 'INSTRUME',
                    'filter'     : 'FILTER',
                    'framename'  : 'ORIGNAME',
                    'exptime'    : 'EXPTIME',
                    'obs_date'   : 'DATE-OBS',
                    'field_center_ra' : 'RA',
                    'field_center_dec' : 'DEC',
                    'field_width' : 'NAXIS1',
                    'field_height' : 'NAXIS2',
                    'pixel_scale' : 'SECPIX',
                    'zeropoint'  : 'L1ZP',
                    'zeropoint_err' : 'L1ZPERR',
                    'zeropoint_src' : 'L1ZPSRC',
                    'fwhm'          : 'L1FWHM',
                    'astrometric_fit_rms'    : 'WCSRDRES',
                    'astrometric_fit_status' : 'WCSERR',
                    'astrometric_fit_nstars' : 'WCSMATCH',
                    'astrometric_catalog'    : 'WCCATTYP',
                  }

    table_dict = OrderedDict([
                    ('ccd_x'         , 'XWIN_IMAGE'),
                    ('ccd_y'         , 'YWIN_IMAGE'),
                    ('obs_ra'        , 'ALPHA_J2000'),
                    ('obs_dec'       , 'DELTA_J2000'),
                    ('obs_ra_err'    , 'ERRX2_WORLD'),
                    ('obs_dec_err'   , 'ERRY2_WORLD'),
                    ('major_axis'    , 'AWIN_IMAGE'),
                    ('minor_axis'    , 'BWIN_IMAGE'),
                    ('ccd_pa'        , 'THETAWIN_IMAGE'),
                    ('obs_mag'       , 'FLUX_AUTO'),
                    ('obs_mag_err'   , 'FLUXERR_AUTO'),
                    ('obs_sky_bkgd'  , 'BACKGROUND'),
                    ('flags'         , 'FLAGS'),
                    ('flux_max'      , 'FLUX_MAX'),
                    ('threshold'     , 'MU_THRESHOLD'),
                 ])

    return header_dict, table_dict

def convert_to_string_value(value):
    left_end = value.find("'")
    right_end = value.rfind("'")
    value = value[left_end+1:right_end]
    string = value.strip()
    return string

def fits_ldac_to_header(header_array):
    header = fits.Header()
    i = 0
    # Ignore END
    while i < len(header_array)-1:
        card = header_array[i]
        keyword = card[0:8]
        if len(card.strip()) != 0:
            if keyword.rstrip() == "COMMENT":
                comment_text = card[8:]
                header.add_comment(comment_text)
            elif keyword.rstrip() != "HISTORY":
                comment_loc = card.rfind('/ ')
                # if no comment found, (comment_loc= -1), set to length of string
                # to ensure we get everything
                if comment_loc == -1:
                    comment_loc = len(card)
                value = card[10:comment_loc]
                if '.' in value:
                    try:
                        value = float(value)
                    except ValueError:
                        # String with periods in it
                        value = convert_to_string_value(value)
                elif "'" in value:
                    value = convert_to_string_value(value)
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        if value.strip() == 'T':
                            value =True
                        elif value.strip() == 'F':
                            value = False
                comment = ''
                if comment_loc > 8 and comment_loc <= len(card):
                    comment = card[comment_loc+2:]
                header.append((keyword, value, comment), bottom=True)

        i += 1

    return header

def open_fits_catalog(catfile, header_only=False):
    '''Opens a FITS source catalog specified by <catfile> and returns the header
    and table data. If [header_only]= is True, only the header is returned.'''

    header = {}
    table = {}

    try:
        hdulist = fits.open(catfile)
    except IOError as e:
        logger.error("Unable to open FITS catalog %s (Reason=%s)" % (catfile, e))
        return header, table

    if len(hdulist) == 2:
        header = hdulist[0].header
        if header_only == False:
            table = hdulist[1].data
    elif len(hdulist) == 3 and hdulist[1].header.get('EXTNAME', None) == 'LDAC_IMHEAD':
        # This is a FITS_LDAC catalog produced by SExtractor for SCAMP
        if header_only == False:
            table = hdulist[2].data
        header_array = hdulist[1].data[0][0]
        header = fits_ldac_to_header(header_array)
    else:
        logger.error("Unexpected number of catalog HDUs (Expected 2, got %d)" % len(hdulist))

    hdulist.close()

    return header, table

def convert_value(keyword, value):
    '''Routine to perform domain-specific transformation of values read from the
    FITS catalog.
    '''

    # Conversion factor for fluxes->magnitude
    FLUX2MAG = 2.5/log(10)

    newvalue = value

    if keyword == 'obs_date':
        try:
            newvalue = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            try:
                newvalue = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                pass
    elif keyword == 'astrometric_fit_rms':
        # Check for bad cases of '-99/-99' and replace with None
        if value.strip() == '-99/-99':
            newvalue = None
        else:
            try:
                (ra_rms, dec_rms) = value.strip().split('/')
                newvalue = (float(ra_rms) + float(dec_rms)) / 2.0
            except TypeError:
                pass
    elif keyword == 'astrometric_catalog':
        if '@' in value:
            newvalue = value.split('@')[0]
    elif keyword == 'obs_ra_err' or keyword == 'obs_dec_err':
        # Turn variance into an error
        newvalue = sqrt(value)
    elif keyword == 'obs_mag':
        try:
            newvalue = -2.5 * log10(value)
        except ValueError:
            logger.warn("Trying to convert a -ve flux to a magnitude")
    elif keyword == 'obs_mag_err':
        try:
            newvalue = FLUX2MAG * (value[0]/value[1])
        except IndexError:
            logger.warn("Need to pass a tuple of (flux error, flux) to compute a magnitude error")
    elif keyword == 'field_center_ra':
        ra = Angle(value, unit=u.hour)
        newvalue = ra.deg
    elif keyword == 'field_center_dec':
        dec = Angle(value, unit=u.deg)
        newvalue = dec.deg
    elif keyword == 'field_width' or keyword == 'field_height':
        try:
            #Calculate width/height by multiplying number of pixels by pixel scale and converting to arcmin
            dimension = (value[0]*value[1])/60.0
            newvalue = "%.4fm" % dimension
        except IndexError:
            logger.warn("Need to pass a tuple of (number of x/y pixels, pixel scale) to compute a width/height")
    elif keyword == 'mu_threshold':
        try:
            # Calculate threshold in magnitudes per sq. arcsec by dividing the
            # threshold counts by pixel area and converting to a magnitude
            newvalue = pow(10, (value[0]/-2.5)) * (value[1]*value[1])
        except IndexError:
            logger.warn("Need to pass a tuple of (threshold in mag per sq. arcsec, pixel scale) to compute a threshold")
        except TypeError:
            logger.warn("Need to pass a tuple of (threshold in mag per sq. arcsec, pixel scale) to compute a threshold")

    return newvalue

def get_catalog_header(catalog_header, catalog_type='LCOGT', debug=False):
    '''Look through the FITS catalog header for the concepts we want for which
    the keyword is given in the mapping specified for the [catalog_type]
    (Currently the LCOGT ORAC-DR FITS Catalog is the only supported mapping
    type)
    The required header items are returned in a dictionary. A FITSHdrException
    is raised if a required keyword is missing or the value of a keyword is
    'UNKNOWN'.
    '''

    header_items = {}
    if catalog_type == 'LCOGT':
        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
    elif catalog_type == 'FITS_LDAC':
        hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
    else:
        logger.error("Unsupported catalog mapping: %s", catalog_type)
        return header_items

    for item in hdr_mapping.keys():
        fits_keyword = hdr_mapping[item]
        if fits_keyword in catalog_header:
            # Found, extract value
            value = catalog_header[fits_keyword]
            if value == 'UNKNOWN':
                if debug: logger.debug('UNKNOWN value found for %s', fits_keyword)
                raise FITSHdrException(fits_keyword)
            # Convert if necessary
            if item != 'field_width' and item != 'field_height':
                new_value = convert_value(item, value)
            else:
                new_value = value
            header_item = { item: new_value }
            header_items.update(header_item)
        else:
            raise FITSHdrException(fits_keyword)

    if 'obs_date' in header_items and 'exptime' in header_items:
        header_items['obs_midpoint'] = header_items['obs_date']  + timedelta(seconds=header_items['exptime'] / 2.0)
    # Determine site code
    if 'site_id' in header_items and 'enc_id' in header_items and 'tel_id' in header_items:
        site_code = LCOGT_domes_to_site_codes(header_items['site_id'], header_items['enc_id'], header_items['tel_id'])
        if site_code != 'XXX':
            header_items['site_code'] = site_code
            del header_items['site_id']
            del header_items['enc_id']
            del header_items['tel_id']
        else:
            logger.error("Could not determine site code from %s-%s-%s", header_items['site_id'], header_items['enc_id'], header_items['tel_id'])
    if 'field_width' in header_items and 'field_height' in header_items and 'pixel_scale' in header_items:
        header_items['field_width'] = convert_value('field_width', (header_items['field_width'], header_items['pixel_scale']))
        header_items['field_height'] = convert_value('field_height', (header_items['field_height'], header_items['pixel_scale']))
    return header_items

def subset_catalog_table(fits_table, column_mapping):

    # Turn the fitrec fits_table into an Astropy Table object (Needed before
    # subsetting the columns)
    table = Table(fits_table)

    # Get the list of new columns we want
    new_columns = column_mapping.values()
    # Make a new table containing only the subset of columns we want and return
    # it
    new_table = Table(table.columns[tuple(new_columns)])

    return new_table

def get_catalog_items(header_items, table, catalog_type='LCOGT', flag_filter=0):
    '''Extract the needed columns specified in the mapping from the FITS
    binary table. Sources with a FLAGS value greater than [flag_filter]
    will not be returned.
    The sources in the catalog are returned as an AstroPy Table containing
    the subset of columns specified in the table mapping.'''

    if catalog_type == 'LCOGT':
        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
    elif catalog_type == 'FITS_LDAC':
        hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
    else:
        logger.error("Unsupported catalog mapping: %s", catalog_type)
        return None

   # Check if all columns exist first
    for column in tbl_mapping.values():
        if column not in table.names:
            raise FITSTblException(column)
            return None

    new_table = subset_catalog_table(table, tbl_mapping)
    # Rename columns
    for new_name in tbl_mapping:
        new_table.rename_column(tbl_mapping[new_name], new_name)

    # Create a new output table (it will likely be shorter due to filtering
    # on flags value)
    out_table = Table(dtype=new_table.dtype)

    for source in new_table:
        source_items = {}
        if 'flags' in tbl_mapping and source['flags'] <= flag_filter:

            for item in tbl_mapping.keys():
                value = source[item]
                # Don't convert magnitude or magnitude error yet
                if 'obs_mag' not in item:
                    new_value = convert_value(item, value)
                else:
                    new_value = value
                new_column = { item : new_value }
                source_items.update(new_column)
            # Convert flux error and flux to magnitude error and magnitude (needs to be this order as
            # the flux is needed for the magnitude error.
            # If a good zeropoint is available from the header, add that too.
            source_items['obs_mag_err'] = convert_value('obs_mag_err', (source_items['obs_mag_err'], source_items['obs_mag']))
            source_items['obs_mag'] = convert_value('obs_mag', source_items['obs_mag'])
            # Convert MU_THRESHOLD (in magnitudes per sq. arcsec) into a THRESHOLD
            # in counts
            if 'threshold' in tbl_mapping.keys() and 'MU_' in tbl_mapping['threshold'].upper():
                source_items['threshold'] = convert_value('mu_threshold', (source_items['threshold'], header_items['pixel_scale']))
            if header_items.get('zeropoint', -99) != -99:
                source_items['obs_mag'] += header_items['zeropoint']
            out_table.add_row(source_items)
    return out_table


def update_ldac_catalog_wcs(fits_image_file, fits_catalog, overwrite=True):
    '''Updates the world co-ordinates (ALPHA_J2000, DELTA_J2000) in a FITS LDAC
    catalog <fits_catalog> with a new WCS read from a FITS image
    <fits_image_file>.
    The transformation is done using the CCD XWIN_IMAGE, YWIN_IMAGE values
    passed through astropy's wcs_pix2world().
    '''

    needed_cols = ['ccd_x', 'ccd_y', 'obs_ra', 'obs_dec']
    status = 0
    # Open FITS image and extract WCS
    try:
        header = fits.getheader(fits_image_file)
        new_wcs = WCS(header)
    except IOError as e:
        logger.error("Error reading WCS from %s. Error was: %s" % (fits_image_file, e))
        return -1
    if header.get('WCSERR', 99) > 0:
        logger.error("Bad value of WCSERR in the header indicating bad fit")
        return -2

    # Extract FITS LDAC catalog
    try:
        hdulist = fits.open(fits_catalog)
    except IOError as e:
        logger.error("Unable to open FITS catalog %s (Reason=%s)" % (fits_catalog, e))
        return -3
    if len(hdulist) != 3:
        logger.error("Unable to open FITS catalog %s (Reason=%s)" % (fits_catalog, "No LDAC table found"))
        return -3
    if len(hdulist) > 2 and hdulist[1].header.get('EXTNAME', None) != 'LDAC_IMHEAD':
        logger.error("Unable to open FITS catalog %s (Reason=%s)" % (fits_catalog, "No LDAC table found"))
        return -3

    tbl_table = hdulist[2].data

    hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
    # Check if all columns exist first
    for column in needed_cols:
        if tbl_mapping[column] not in tbl_table.names:
            raise FITSTblException(column)
            return None

    # Pull out columns as arrays
    ccd_x = tbl_table[tbl_mapping['ccd_x']]
    ccd_y = tbl_table[tbl_mapping['ccd_y']]

    new_ra, new_dec = new_wcs.wcs_pix2world(ccd_x, ccd_y, 1)

    tbl_table[tbl_mapping['obs_ra']] = new_ra
    tbl_table[tbl_mapping['obs_dec']] = new_dec

    # Write out new catalog file
    new_fits_catalog = fits_catalog
    to_clobber = True
    if overwrite != True:
        new_fits_catalog = new_fits_catalog + '.new'
        to_clobber = False
    hdulist.writeto(new_fits_catalog, checksum=True, clobber=to_clobber)
    return status

def extract_catalog(catfile, catalog_type='LCOGT', flag_filter=0):
    '''High-level routine to read LCOGT FITS catalogs from <catfile>.
    This returns a dictionary of needed header items and an AstroPy table of
    the sources that pass the [flag_filter] cut-off or None if the file could
    not be opened.'''

    header = table = None
    fits_header, fits_table = open_fits_catalog(catfile)

    if fits_header != {} and fits_table != {}:
        header = get_catalog_header(fits_header, catalog_type)
        table = get_catalog_items(header, fits_table, catalog_type, flag_filter)

    return header, table

def update_zeropoint(header, table, avg_zeropoint, std_zeropoint):

    header['zeropoint'] = avg_zeropoint
    header['zeropoint_err'] = std_zeropoint
    header['zeropoint_src'] = 'py_zp_match-V0.1'

    for source in table:
        source['obs_mag'] += avg_zeropoint
        source['obs_mag_err'] = sqrt( ((source['obs_mag_err']/source['obs_mag'])**2.0) + ((header['zeropoint_err']/header['zeropoint'])**2.0) )

    return header, table

def store_catalog_sources(catfile, catalog_type='LCOGT'):

    num_sources_created = 0
    num_in_table = 0

    #read the catalog file
    header, table = extract_catalog(catfile, catalog_type)

    if header and table:

        #check for good zeropoints
        if header.get('zeropoint',-99) == -99 or header.get('zeropoint_err',-99) == -99:
            #if bad, determine new zeropoint
            header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint((header, table))

            #if crossmatch is good, update new zeropoint
            if std_zeropoint < 0.1:
                header, table = update_zeropoint(header, table, avg_zeropoint, std_zeropoint)

        #store sources in neoexchange(CatalogSources table)
        frame_params = {    'sitecode':header['site_code'],
                            'instrument':header['instrument'],
                            'filter':header['filter'],
                            'filename':header['framename'],
                            'exptime':header['exptime'],
                            'midpoint':header['obs_midpoint'],
                            'block':None,
                            'zeropoint':header['zeropoint'],
                            'zeropoint_err':header['zeropoint_err'],
                            'fwhm':header['fwhm'],
                            'frametype':Frame.SINGLE_FRAMETYPE,
                            'rms_of_fit':header['astrometric_fit_rms'],
                            'nstars_in_fit':header['astrometric_fit_nstars'],
                        }

        frame, created = Frame.objects.get_or_create(**frame_params)

        for source in table:
            source_params = {   'frame':frame,
                                'obs_x': source['ccd_x'],
                                'obs_y': source['ccd_y'],
                                'obs_ra': source['obs_ra'],
                                'obs_dec': source['obs_dec'],
                                'obs_mag': source['obs_mag'],
                                'err_obs_ra': source['obs_ra_err'],
                                'err_obs_dec': source['obs_dec_err'],
                                'err_obs_mag': source['obs_mag_err'],
                                'background': source['obs_sky_bkgd'],
                                'major_axis': source['major_axis'],
                                'minor_axis': source['minor_axis'],
                                'position_angle': source['ccd_pa'],
                                'ellipticity': 1.0-(source['minor_axis']/source['major_axis']),
                                'aperture_size': 3.0,
                                'flags': source['flags'],
                                'flux_max': source['flux_max'],
                                'threshold': source['threshold']
                            }
            cat_src, created = CatalogSources.objects.get_or_create(**source_params)
            if created == True:
                num_sources_created += 1
        num_in_table = len(table)
    else:
        logger.warn("Could not open %s" % catfile)

    return (num_sources_created, num_in_table)

def make_sext_dict(catsrc, num_iter):

    sext_params = { 'number':num_iter,
                    'obs_x':catsrc.obs_x,
                    'obs_y':catsrc.obs_y,
                    'obs_mag':catsrc.obs_mag,
                    'theta':catsrc.position_angle,
                    'elongation':catsrc.make_elongation(),
                    'fwhm':catsrc.make_fwhm(),
                    'flags':catsrc.flags,
                    'deltamu':catsrc.make_mu_threshold()-catsrc.make_mu_max(),
                    'flux':catsrc.make_flux(),
                    'area':catsrc.make_area(),
                    'ra':catsrc.obs_ra,
                    'dec':catsrc.obs_dec
                  }

    return sext_params

def make_sext_file_line(sext_params):

    print_format = "      %4i   %8.3f   %8.3f  %7.4f %5.1f    %5.3f     %4.2f   %1i  %4.2f   %6.1f   %2i %9.5f %9.5f"

    sext_line = print_format % (sext_params['number'], sext_params['obs_x'], sext_params['obs_y'], sext_params['obs_mag'], sext_params['theta'], sext_params['elongation'], sext_params['fwhm'], sext_params['flags'], sext_params['deltamu'], sext_params['flux'], sext_params['area'], sext_params['ra'], sext_params['dec'])

    return sext_line

def make_sext_dict_list():

    sext_dict_list = []

    num_iter = 1
    while num_iter <= CatalogSources.objects.count():
        source = CatalogSources.objects.get(pk=num_iter)
        sext_dict_list.append(make_sext_dict(source, num_iter))
        num_iter += 1

    return sext_dict_list

def make_sext_line_list(sext_dict_list):

    sext_line_list = []

    sext_dict_list_sorted = sorted(sext_dict_list, key=lambda k: k['obs_x'])

    for source in sext_dict_list_sorted:
        sext_line = make_sext_file_line(source)
        sext_line_list.append(sext_line)

    return sext_line_list

def make_sext_files(dest_dir):

    num_iter=1
    while num_iter <= Frame.objects.count():
        sext_dict_list = make_sext_dict_list()
        sext_line_list = make_sext_line_list(sext_dict_list)
        sext_filename = open(os.path.join(dest_dir, str(CatalogSources.objects.get(pk=num_iter).frame).replace('.fits', '.sext')), 'w')
        for line in sext_line_list:
            sext_filename.write(line)
            sext_filename.write('\n')
        sext_filename.close()
        num_iter += 1

    return

def determine_filenames(product):
    '''Given a passed <product> filename, determine the corresponding catalog
    filename and vice-versa
    '''

    new_product = None
    product = os.path.basename(product)
    if '_cat.fits' in product:
        new_product = product.replace('_cat', '', 1)
    else:
        file_bits =  product.split(os.extsep)
        if len(file_bits) == 2:
            filename_noext = file_bits[0]
            if filename_noext[-2:].isdigit():
                new_product = filename_noext + '_cat' + os.extsep + file_bits[1]
    return new_product

def increment_red_level(product):
    '''Determines the reduction level of a passed pipeline product <product>,
    and increments the reduction level by 1.'''

    new_product = None
    product = os.path.basename(product)
    if '_cat' in product :
        file_bits =  product.split('_cat')
        file_bits[1] = '_cat' + file_bits[1]
    elif '_ldac' in product :
        file_bits =  product.split('_ldac')
        file_bits[1] = '_ldac' + file_bits[1]
    else:
        file_bits =  product.split(os.extsep)
        file_bits[1] = os.extsep + file_bits[1]
    if len(file_bits) == 2:
        filename_noext = file_bits[0]
        red_level = filename_noext[-2:]
        if red_level.isdigit():
            red_level = "%02.2d" % (min(int(red_level)+1,99),)
            filename_noext = filename_noext[:-2] + red_level
            new_product = filename_noext + file_bits[1]
    return new_product
