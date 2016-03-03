import logging
from datetime import datetime, timedelta
from math import sqrt, log10, log

from astropy.io import fits

#from astrometrics.ephem_subs import LCOGT_domes_to_site_codes

from astroquery.vizier import Vizier
import astropy.units as u
import astropy.coordinates as coord

logger = logging.getLogger(__name__)

def get_catalog(catalog, ra, dec, default):
    '''Pulls a catalog from Vizier'''

    #set the default catalog
    if default == 'true':
        cat = "UCAC4"
    else:
        #if catalog is an empty string, force the query to ask for the default catalog to ensure the query doesn't hang indefinitely
        if len(catalog) > 0:
            cat = catalog
        else:
            cat = "UCAC4"

    #query Vizier on a region of the sky with ra and dec coordinates a specified catalog
    result = Vizier.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width="30m", catalog=[cat])

    #resulting catalog table
    cat_table = result[0]

    #pull out the table column with ra
    ra_column = cat_table.columns[0]

    #convert the data in the ra column to a list
    ra_cat_list = ra_column.data.data.tolist()

    #pull out the table column with dec
    dec_column = cat_table.columns[1]

    #convert the data in the dec column to a list
    dec_cat_list = dec_column.data.data.tolist()

    #pull out the table column with rmag
    rmag_column = cat_table.columns[48]

    #convert the data in the rmag column to a list
    rmag_cat_list = rmag_column.data.data.tolist()

    return ra_cat_list, dec_cat_list, rmag_cat_list

