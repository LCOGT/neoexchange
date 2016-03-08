import logging
from datetime import datetime, timedelta
from math import sqrt, log10, log

from astropy.io import fits

#from astrometrics.ephem_subs import LCOGT_domes_to_site_codes

from astroquery.vizier import Vizier
import astropy.units as u
import astropy.coordinates as coord

from astropy.table import Table

logger = logging.getLogger(__name__)

def get_catalog_table(ra, dec, cat = "PPMXL", set_row_limit = 10000, rmag_limit = "<=15.0", set_width = "30m"):
    '''Pulls a catalog from Vizier'''

    #query Vizier on a region of the sky with ra and dec coordinates of a specified catalog
    while set_row_limit < 100000:
        
        query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag":rmag_limit, "r1mag":rmag_limit})
        result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, catalog=[cat])

        #resulting catalog table
        cat_table = result[0]

        #if didn't get all of the table, try again with a larger row limit
        if len(cat_table) == set_row_limit:
            set_row_limit += 10000
            query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag":rmag_limit, "r1mag":rmag_limit})
            result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, catalog=[cat])

            #resulting catalog table
            cat_table = result[0]
        else:
            break

    return cat_table

def cross_match(cat_table_1, cat_table_2, cross_match_diff_threshold = 0.001):
    '''Cross matches RA and Dec for sources in two catalog tables. Every source in the shorter length catalog is cross matched with a source in the longer length catalog. Outputs a table of RA, Dec, and r-mag for each cross-matched source. NOTE: This is currently set up to cross match RAs and Decs in the UCAC4 and PPMXL catalogs, not one of these with the catalog produced by SExtractor for a FITS image.'''

    ra_min_diff_threshold = 1.0
    dec_min_diff_threshold = 1.0
    dec_cat_1 = 0.0
    dec_cat_2 = 0.0
    ra_cat_1 = 0.0
    ra_cat_2 = 0.0
    rmag_cat_1 = 0.0
    rmag_cat_2 = 0.0
    cross_match_list = []

    if len(cat_table_1) > len(cat_table_2):
        cat_table_temp = cat_table_1
        cat_table_1 = cat_table_2
        cat_table_2 = cat_table_temp

    y = 0
    for value in cat_table_1['_DEJ2000']:
        try:
            rmag_cat_1_test = cat_table_1['rmag'][y]
        except:
            rmag_cat_1_test = cat_table_1['r2mag'][y]
        if rmag_cat_1_test > 0.0:
            ra_min_diff = ra_min_diff_threshold
            dec_min_diff = dec_min_diff_threshold
            z = 0
            for source in cat_table_2['_DEJ2000']:
                try:
                    rmag_cat_2_test = cat_table_2['rmag'][z]
                except:
                    rmag_cat_2_test = cat_table_2['r2mag'][z]
                if rmag_cat_2_test > 0.0:
                    if abs(source - value) < dec_min_diff:
                        dec_min_diff = abs(source - value)
                        ra_cat_1_test = cat_table_1['_RAJ2000'][y]
                        ra_cat_2_test = cat_table_2['_RAJ2000'][z]
                        if abs(ra_cat_1_test - ra_cat_2_test) < ra_min_diff:
                            ra_min_diff = abs(ra_cat_1_test - ra_cat_2_test)
                            dec_cat_1 = value
                            dec_cat_2 = source
                            ra_cat_1 = ra_cat_1_test
                            ra_cat_2 = ra_cat_2_test
                            rmag_cat_1 = rmag_cat_1_test
                            rmag_cat_2 = rmag_cat_2_test
                            rmag_diff = abs(rmag_cat_1 - rmag_cat_2)
                z += 1
            y += 1
            if ra_min_diff < cross_match_diff_threshold and dec_min_diff < cross_match_diff_threshold:
                cross_match_list.append((ra_cat_1, ra_cat_2, ra_min_diff, dec_cat_1, dec_cat_2, dec_min_diff, rmag_cat_1, rmag_cat_2, rmag_diff))

    cross_match_table = Table(rows=cross_match_list, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag diff'), dtype=('f8', 'f8', 'e8', 'f8', 'f8', 'e8', 'f8', 'f8', 'f8'))

    return cross_match_table

def get_zeropoint(cross_match_table):
    '''Computes a zeropoint from the two catalogues in 'cross_match_table' and iterates until all outliers are thrown out.'''

    std_zeropoint = 10.0
    num_iter = 0
    r_mag_diff_threshold = 2.0

    while num_iter < 40:

        if std_zeropoint > 0.1:
            count = 0
            sum_r_mag_diff = 0.0
            avg_zeropoint = 0.0
            sum_diff = 0.0
            diff_from_avg_sq = []

            for value in cross_match_table['r mag diff']:
                if value < r_mag_diff_threshold:
                    sum_r_mag_diff += value
                    count += 1

            avg_zeropoint = sum_r_mag_diff / count

            for value in cross_match_table['r mag diff']:
                if value < r_mag_diff_threshold:
                    diff_from_avg_sq.append((value - avg_zeropoint)**2)

            for value in diff_from_avg_sq:
                sum_diff += value

            std_zeropoint = sqrt(sum_diff / len(diff_from_avg_sq))

        r_mag_diff_threshold -= 0.05
        num_iter += 1

    return avg_zeropoint, std_zeropoint, count

