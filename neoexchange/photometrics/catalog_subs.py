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

from astropy.io import fits

logger = logging.getLogger(__name__)


class FITSHdrException(Exception):
    '''Raised when a required FITS header keyword is missing'''
    
    def __init__(self, keyword):
    	self.keyword = keyword
    
    def __str__(self):
    	return "Required keyword '" + self.keyword + "' missing"

def oracdr_catalog_mapping():
    '''Returns two dictionaries of the mapping between the FITS header and table
    items and CatalogItem quantities for LCOGT ORAC-DR pipeline format catalog
    files.'''

    header_dict = { 'instrument' : 'INSTRUME',
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
        logger.error("Unsupported catalog mapping: %s" % catalog_type)
        return header_items

    for item in hdr_mapping.keys():
        fits_keyword = hdr_mapping[item]
        if fits_keyword in catalog_header:
            # Found, extract value
    	    value = catalog_header[fits_keyword]
	    if value == 'UNKNOWN':
	        if debug: logger.debug('UNKNOWN value found for %s' % fits_keyword)
    	        raise FITSHdrException(fits_keyword)
            header_item = { item: value }
            header_items.update(header_item)
        else:
            raise FITSHdrException(fits_keyword)
    return header_items

def get_catalog_items(header, table, catalog_type='LCOGT'):

    return {}
