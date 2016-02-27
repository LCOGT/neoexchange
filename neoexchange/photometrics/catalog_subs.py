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

from astropy.io import fits

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
                    'zeropoint'  : 'L1ZP',
                    'zeropoint_err' : 'L1ZPERR',
                    'zeropoint_src' : 'L1ZPSRC',
                    'fwhm'          : 'L1FWHM',
                    'astrometric_fit_rms'    : 'WCSRDRES',
                    'astrometric_fit_status' : 'WCSERR',
                    'astrometric_fit_nstars' : 'WCSMATCH',
                    'astrometric_catalog'    : 'WCCATTYP',
                  }

    table_dict = {  'ccd_x'         : 'X_IMAGE',
                    'ccd_y'         : 'Y_IMAGE',
                    'major_axis'    : 'A_IMAGE',
                    'minor_axis'    : 'B_IMAGE',
                    'ccd_pa'        : 'THETA_IMAGE',
                    'obs_ra'        : 'ALPHA_J2000',
                    'obs_dec'       : 'DELTA_J2000',
                    'obs_ra_err'    : 'ERRX2_WORLD',
                    'obs_dec_err'   : 'ERRY2_WORLD',
                    'obs_mag'       : 'FLUX_AUTO',
                    'obs_mag_err'   : 'FLUXERR_AUTO',
                    'obs_sky_bkgd'  : 'BACKGROUND',
                    'flags'         : 'FLAGS',
                 }

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
            new_value = convert_value(item, value)
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
    return header_items

def get_catalog_items(header_items, table, catalog_type='LCOGT', flag_filter=0):
    '''Extract the needed columns specified in the mapping from the FITS
    binary table. Sources with a FLAGS value greater than [flag_filter]
    will not be returned.
    The sources in the catalog are returned in a list of dictionaries containing
    the keys specified in the table mapping.'''

    catalog_items = []
    if catalog_type == 'LCOGT':
        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
    else:
        logger.error("Unsupported catalog mapping: %s", catalog_type)
        return catalog_items

   # Check if all columns exist first
    for column in tbl_mapping.values():
        if column not in table.names:
            raise FITSTblException(column)
            return catalog_items

    for source in table:
        source_items = {}
        if 'flags' in tbl_mapping and source[tbl_mapping['flags']] <= flag_filter:
        
            for item in tbl_mapping.keys():
                column = tbl_mapping[item]
                value = source[column]
                # Don't convert magnitude or magnitude error yet
                if 'obs_mag' not in item:
                    new_value = convert_value(item, source[column])
                else:
                    new_value = value
                new_column = { item : new_value }
                source_items.update(new_column)
            # Convert flux error and flux to magnitude error and magnitude (needs to be this order as
            # the flux is needed for the magnitude error.
            # If a good zerpoint is available from the header, add that too.
            source_items['obs_mag_err'] = convert_value('obs_mag_err', (source_items['obs_mag_err'], source_items['obs_mag']))
            source_items['obs_mag'] = convert_value('obs_mag', source_items['obs_mag'])
            if header_items.get('zeropoint', -99) != -99:
                source_items['obs_mag'] += header_items['zeropoint']
            catalog_items.append(source_items)

    return catalog_items
