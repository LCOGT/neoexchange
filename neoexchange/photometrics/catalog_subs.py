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
from datetime import datetime, timedelta
from math import sqrt, log10, log
from collections import OrderedDict

from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import Angle
import astropy.units as u

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes

logger = logging.getLogger(__name__)


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

    if len(hdulist) == 2:
        header = hdulist[0].header
        table = hdulist[1].data
    elif len(hdulist) == 3 and hdulist[1].header.get('EXTNAME', None) == 'LDAC_IMHEAD':
        # This is a FITS_LDAC catalog produced by SExtractor for SCAMP
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
