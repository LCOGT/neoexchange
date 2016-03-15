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

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes

logger = logging.getLogger(__name__)

def call_cross_match_and_zeropoint(catfile, cat_name = "UCAC4",  set_row_limit = 10000, rmag_limit = "<=15.0"):

    header, table = extract_catalog(catfile)

    cat_table, cat_name = get_vizier_catalog_table(header['field_center_ra'], header['field_center_dec'], header['field_width'], header['field_height'], cat_name, set_row_limit, rmag_limit)

    cross_match_table = cross_match(table, cat_table, cat_name)

    avg_zeropoint, std_zeropoint, count = get_zeropoint(cross_match_table)

    return header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count

def get_vizier_catalog_table(ra, dec, set_width, set_height, cat_name = "UCAC4", set_row_limit = 10000, rmag_limit = "<=15.0"):
    '''Pulls a catalog from Vizier'''

    #query Vizier on a region of the sky with ra and dec coordinates of a specified catalog
    while set_row_limit < 100000:

        query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag":rmag_limit, "r1mag":rmag_limit})
        result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=[cat_name])

        #resulting catalog table
        if len(result) < 1:
            if "PPMXL" in cat_name:
                cat_name = "UCAC4"
                result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=[cat_name])
                cat_table = result[0]
            else:
                cat_name = "PPMXL"
                result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=[cat_name])
                cat_table = result[0]
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
            RA_table_2 = table_2['obs_ra']
            Dec_table_2 = table_2['obs_dec']
            rmag_table_2 = table_2['obs_mag']
            flags_table_2 = table_2['flags']
        else:
            RA_table_1 = table_1['_RAJ2000']
            Dec_table_1 = table_1['_DEJ2000']
            rmag_table_1 = table_1['rmag']
            flags_table_1 = table_1['_RAJ2000'] * 0 #UCAC4 does not have flags, so get copy RA table column and turn values all to zeros
            RA_table_2 = table_2['obs_ra']
            Dec_table_2 = table_2['obs_dec']
            rmag_table_2 = table_2['obs_mag']
            flags_table_2 = table_2['flags']
    else:
        table_1 = FITS_table
        table_2 = cat_table
        if "PPMXL" in cat_name:
            RA_table_1 = table_1['obs_ra']
            Dec_table_1 = table_1['obs_dec']
            rmag_table_1 = table_1['obs_mag']
            flags_table_1 = table_1['flags']
            RA_table_2 = table_2['_RAJ2000']
            Dec_table_2 = table_2['_DEJ2000']
            rmag_table_2 = table_2['r2mag']
            flags_table_2 = table_2['fl']
        else:
            RA_table_1 = table_1['obs_ra']
            Dec_table_1 = table_1['obs_dec']
            rmag_table_1 = table_1['obs_mag']
            flags_table_1 = table_1['flags']
            RA_table_2 = table_2['_RAJ2000']
            Dec_table_2 = table_2['_DEJ2000']
            rmag_table_2 = table_2['rmag']
            flags_table_2 = table_2['_RAJ2000'] * 0 #UCAC4 does not have flags, so get copy RA table column and turn values all to zeros

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
                z += 1
        if ra_min_diff < cross_match_diff_threshold and dec_min_diff < cross_match_diff_threshold:
            cross_match_list.append((ra_cat_1, ra_cat_2, ra_min_diff, dec_cat_1, dec_cat_2, dec_min_diff, rmag_cat_1, rmag_cat_2, rmag_diff))
        y += 1
        ra_min_diff = ra_min_diff_threshold
        dec_min_diff = dec_min_diff_threshold

    cross_match_table = Table(rows=cross_match_list, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

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
            sum_r_mag_diff = 0.0
            sum_diff = 0.0
            diff_from_avg_sq = []

            y = 0
            for value in cross_match_table['r mag diff']:
                if cross_match_table['r mag Cat 1'][y] != 'nan' and cross_match_table['r mag Cat 2'][y] != 'nan':
                    if abs(value - avg_zeropoint) < r_mag_diff_threshold:
                        sum_r_mag_diff += value
                        count += 1
                y += 1

            if count > 0:
                avg_zeropoint = sum_r_mag_diff / count

            y = 0
            for value in cross_match_table['r mag diff']:
                if cross_match_table['r mag Cat 1'][y] != 'nan' and cross_match_table['r mag Cat 2'][y] != 'nan':
                    if abs(value - avg_zeropoint) < r_mag_diff_threshold:
                        diff_from_avg_sq.append((value - avg_zeropoint)**2)
                y += 1

            for value in diff_from_avg_sq:
                sum_diff += value

            if len(diff_from_avg_sq) > 0:
                std_zeropoint = sqrt(sum_diff / len(diff_from_avg_sq))

        r_mag_diff_threshold -= 0.05
        num_iter += 1

    return avg_zeropoint, std_zeropoint, count


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
                 ])

    return header_dict, table_dict

def open_fits_catalog(catfile):
    '''Opens a FITS source catalog specified by <catfile> and returns the header
    and table data'''

    header = {}
    table = {}

    try:
        hdulist = fits.open(catfile)
    except IOError as e:
        logger.error("Unable to open FITS catalog %s (Reason=%s)" % (catfile, e))
        return header, table

    if len(hdulist) != 2:
        logger.error("Unexpected number of catalog HDUs (Expected 2, got %d)" % len(hdulist))
        return header, table

    header = hdulist[0].header
    table = hdulist[1].data

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
            if header_items.get('zeropoint', -99) != -99:
                source_items['obs_mag'] += header_items['zeropoint']
            out_table.add_row(source_items)
    return out_table

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
