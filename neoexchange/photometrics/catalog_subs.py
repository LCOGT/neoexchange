import logging
from datetime import datetime, timedelta
from math import sqrt, log10, log

from astropy.io import fits

#from astrometrics.ephem_subs import LCOGT_domes_to_site_codes

from astroquery.vizier import Vizier
import astropy.units as u
import astropy.coordinates as coord

logger = logging.getLogger(__name__)

def get_catalog_table(ra, dec, cat = "PPMXL", set_row_limit = 10000, rmag_limit = "<=15.0", set_width = "30m"):
    '''Pulls a catalog from Vizier'''

    #query Vizier on a region of the sky with ra and dec coordinates a specified catalog
    query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag":rmag_limit, "r1mag":rmag_limit})
    result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, catalog=[cat])

    #resulting catalog table
    cat_table = result[0]

    return cat_table

