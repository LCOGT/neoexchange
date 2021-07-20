"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

catalog_subs.py -- Code to retrieve source detection infomation from FITS catalogs.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import logging
import os
from glob import glob
import numpy as np
from datetime import datetime, timedelta
from math import sqrt, log10, log, degrees, cos
from collections import OrderedDict
import time
from requests.exceptions import ReadTimeout, ConnectTimeout, ConnectionError
import re
import warnings

from astropy.utils.exceptions import AstropyDeprecationWarning
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import Angle
warnings.simplefilter('ignore', category = AstropyDeprecationWarning)
from astroquery.vizier import Vizier
import astropy.units as u
import astropy.coordinates as coord
from astropy.wcs import WCS, FITSFixedWarning
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy import __version__ as astropyversion

from astrometrics.ephem_subs import LCOGT_domes_to_site_codes
from astrometrics.time_subs import timeit
from core.models import CatalogSources, Frame

logger = logging.getLogger(__name__)


def reset_database_connection():
    """Reset the Django DB connection. This will cause Django to reconnect and
    get around the OperationalError: (2006, 'MySQL server has gone away')
    problems from timeouts on long-running processes"""

    from django import db
    db.close_old_connections()


def call_cross_match_and_zeropoint(catfile, std_zeropoint_tolerance=0.1, cat_name="UCAC4",  set_row_limit=10000, rmag_limit="<=15.0"):

    if type(catfile) == str:
        header, table = extract_catalog(catfile)
    else:
        header, table = (catfile[0], catfile[1])

    start = time.time()
    cat_table, cat_name = get_vizier_catalog_table(header['field_center_ra'], header['field_center_dec'], header['field_width'], header['field_height'], cat_name, set_row_limit, rmag_limit)
    end = time.time()
    logger.debug("TIME: get_vizier_catalog took {:.1f} seconds".format(end-start))

    start = time.time()
    cross_match_table = cross_match(table, cat_table, cat_name)
    end = time.time()
    logger.debug("TIME: cross_match took {:.1f} seconds".format(end-start))

    # cross_match can be a very slow process (tens of minutes) which can cause
    # the DB connection to time out. If we reset and explicitly close the
    # connection, Django will auto-reconnect.
    reset_database_connection()

    if cross_match_table is not None:
        start = time.time()
        avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table, std_zeropoint_tolerance)
        end = time.time()
        logger.debug("TIME: get_zeropoint took {:.1f} seconds".format(end-start))
    else:
        avg_zeropoint = -99
        std_zeropoint = 99.0
        count = 0
        num_in_calc = 0

    return header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name


def get_vizier_catalog_table(ra, dec, set_width, set_height, cat_name="UCAC4", set_row_limit=10000, rmag_limit="<=15.0"):
    """Pulls a catalog from Vizier"""

    # Mapping of NEOx catalog names to Vizier catalogs
    cat_mapping = { "GAIA-DR2" : "I/345/gaia2",
                    "UCAC4" : "I/322A",
                    "PPMXL" : "I/317"
                  }

    # query Vizier on a region of the sky with ra and dec coordinates of a specified catalog
    while set_row_limit < 100000:

        if "UCAC4" in cat_name:
            query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag": rmag_limit, "r1mag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'rmag', 'e_rmag'])
        elif "GAIA-DR2" in cat_name:
            query_service = Vizier(row_limit=set_row_limit, column_filters={"Gmag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'e_RAJ2000', 'e_DEJ2000', 'Gmag', 'e_Gmag', 'Dup'])
        else:
            query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag": rmag_limit, "r1mag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'r2mag', 'fl'])

        vizier_servers_list = ['vizier.cfa.harvard.edu', 'vizier.hia.nrc.ca'] # Preferred first
        query_service.VIZIER_SERVER = vizier_servers_list[0]

        query_service.TIMEOUT = 60
        try:
            result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=cat_mapping[cat_name])
        except (ReadTimeout, ConnectionError):
            logger.warning("Timeout seen querying {}".format(query_service.VIZIER_SERVER))
            query_service.TIMEOUT = 120
            result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=cat_mapping[cat_name])
        except ConnectTimeout:
            old_server = query_service.VIZIER_SERVER
            query_service.VIZIER_SERVER = vizier_servers_list[-1]
            logger.warning("Timeout querying {}. Switching to {}".format(old_server, query_service.VIZIER_SERVER))
            result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=cat_mapping[cat_name])
        if len(result) == 0:
            old_server = query_service.VIZIER_SERVER
            query_service.VIZIER_SERVER = vizier_servers_list[-1]
            logger.warning("Error querying {}. Switching to {}".format(old_server, query_service.VIZIER_SERVER))
            result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=cat_mapping[cat_name])
        # resulting catalog table
        # if resulting catalog table is empty or the r mag column has only masked values, try the other catalog and redo
        # the query; if the resulting catalog table is still empty, fill the table with zeros
        if cat_name == "UCAC4":
            rmag = 'rmag'
        elif cat_name == "GAIA-DR2":
            rmag = 'Gmag'
        else:
            rmag = 'r2mag'
        if (len(result) < 1) or (np.sum(~result[0][rmag].mask) < 1):
            if "PPMXL" in cat_name:
                cat_name = "UCAC4"
                query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag": rmag_limit, "r1mag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'rmag', 'e_rmag'])
                result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=cat_mapping[cat_name])
                if len(result) > 0:
                    cat_table = result[0]
                else:
                    zeros_list = [0.0] * 100000
                    zeros_int_list = [0] * 100000
                    cat_table = Table([zeros_list, zeros_list, zeros_list, zeros_int_list, zeros_int_list], names=('RAJ2000', 'DEJ2000', 'rmag', 'flags', 'e_rmag'))
            else:
                cat_name = "PPMXL"
                query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag": rmag_limit, "r1mag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'r2mag', 'fl'])
                result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, height=set_height, catalog=cat_mapping[cat_name])
                if len(result) > 0:
                    cat_table = result[0]
                else:
                    zeros_list = [0.0] * 100000
                    zeros_int_list = [0] * 100000
                    cat_table = Table([zeros_list, zeros_list, zeros_list, zeros_int_list], names=('RAJ2000', 'DEJ2000', 'r2mag', 'fl'))
        # if the resulting table is neither empty nor missing columns values, set the cat_table
        else:
            cat_table = result[0]

        # if didn't get all of the table, try again with a larger row limit
        if len(cat_table) == set_row_limit:
            set_row_limit += 10000
            if "UCAC4" in cat_name:
                query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag": rmag_limit, "r1mag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'rmag', 'e_rmag'])
            elif "GAIA-DR2" in cat_name:
                query_service = Vizier(row_limit=set_row_limit, column_filters={"Gmag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'e_RAJ2000', 'e_DEJ2000', 'Gmag', 'e_Gmag', 'Dup'])
            else:
                query_service = Vizier(row_limit=set_row_limit, column_filters={"r2mag": rmag_limit, "r1mag": rmag_limit}, columns=['RAJ2000', 'DEJ2000', 'r2mag', 'fl'])
            result = query_service.query_region(coord.SkyCoord(ra, dec, unit=(u.deg, u.deg), frame='icrs'), width=set_width, catalog=cat_mapping[cat_name])

            # resulting catalog table
            cat_table = result[0]
        else:
            break

    return cat_table, cat_name


def cross_match(FITS_table, cat_table, cat_name="UCAC4", cross_match_diff_threshold=0.001):
    """
    Cross matches RA and Dec for sources in two catalog tables. Every source in the shorter length catalog is cross
    matched with a source in the longer length catalog. Cross matches with RA or Dec differences < 0.001 are not
    included in the final output table. Outputs a table of RA, Dec, and r-mag for each cross-matched source.
    """

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
        RA_table_2 = table_2['obs_ra']
        Dec_table_2 = table_2['obs_dec']
        rmag_table_2 = table_2['obs_mag']
        flags_table_2 = table_2['flags']
        table1_has_errs = True
        RA_table_1 = table_1['RAJ2000']
        Dec_table_1 = table_1['DEJ2000']
        if "PPMXL" in cat_name:
            rmag_table_1 = table_1['r2mag']
            flags_table_1 = table_1['fl']
            rmag_err_table_1 = table_1['RAJ2000'] * 0  # PPMXL does not have r mag errors, so copy RA table column and turn values all to zeros
        elif "GAIA-DR2" in cat_name:
            rmag_table_1 = table_1['Gmag']
            rmag_err_table_1 = table_1['e_Gmag']
            flags_table_1 = table_1['Dup']
        else:
            rmag_table_1 = table_1['rmag']
            flags_table_1 = table_1['RAJ2000'] * 0  # UCAC4 does not have flags, so copy RA table column and turn values all to zeros
            rmag_err_table_1 = table_1['e_rmag']
    else:
        table_1 = FITS_table
        table_2 = cat_table
        RA_table_1 = table_1['obs_ra']
        Dec_table_1 = table_1['obs_dec']
        rmag_table_1 = table_1['obs_mag']
        flags_table_1 = table_1['flags']
        rmag_err_table_1 = 'nan'
        RA_table_2 = table_2['RAJ2000']
        Dec_table_2 = table_2['DEJ2000']
        table1_has_errs = False

        if "PPMXL" in cat_name:
            rmag_table_2 = table_2['r2mag']
            flags_table_2 = table_2['fl']
            rmag_err_table_2 = table_2['RAJ2000'] * 0  # PPMXL does not have r mag errors, so copy RA table column and turn values all to zeros
        elif "GAIA-DR2" in cat_name:
            rmag_table_2 = table_2['Gmag']
            rmag_err_table_2 = table_2['e_Gmag']
            flags_table_2 = table_2['Dup']
        else:
            rmag_table_2 = table_2['rmag']
            flags_table_2 = table_2['RAJ2000'] * 0  # UCAC4 does not have flags, so copy RA table column and turn values all to zeros
            rmag_err_table_2 = table_2['e_rmag']
    y = 0
    logger.debug("TIME: Table lengths: {} {}".format(len(Dec_table_1), len(Dec_table_2)))
    for value in Dec_table_1:
        if flags_table_1[y] < 1:
            # Convert masked elements to None to avoid warning error from Table.
            if not np.ma.is_masked(rmag_table_1[y]):
                rmag_table_1_temp = rmag_table_1[y]
            else:
                rmag_table_1_temp = None
            z = 0
            start = time.time()
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
                            if rmag_cat_1 is not None and rmag_cat_2 is not None and not np.isnan(rmag_cat_1) and not np.isnan(rmag_cat_2):
                                rmag_diff = abs(rmag_cat_1 - rmag_cat_2)
                            else:
                                rmag_diff = None
                            rmag_error = None
                            # Calculate errors when possible, ignore when not.
                            try:
                                if table1_has_errs:
                                    rmag_error = float(rmag_err_table_1[y]) / 100.0
                                else:
                                    rmag_error = float(rmag_err_table_2[z]) / 100.0
                            except ValueError:
                                rmag_error = None
                z += 1
            end = time.time()
            if y <= 10:
                logger.debug("TIME: inner loop took {:.2f} seconds".format(end-start))
        if ra_min_diff < cross_match_diff_threshold and dec_min_diff < cross_match_diff_threshold:
            cross_match_list.append((ra_cat_1, ra_cat_2, ra_min_diff, dec_cat_1, dec_cat_2, dec_min_diff, rmag_cat_1, rmag_cat_2, rmag_error, rmag_diff))
        y += 1
        ra_min_diff = ra_min_diff_threshold
        dec_min_diff = dec_min_diff_threshold

    if len(cross_match_list) > 0:
        cross_match_table = Table(rows=cross_match_list, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2',
                                                                'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err',
                                                                'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))
    else:
        logger.warning("Did not find any cross matches")
        cross_match_table = None

    return cross_match_table


def get_zeropoint(cross_match_table, std_zeropoint_tolerance):
    """Computes a zeropoint from the two catalogues in 'cross_match_table' and iterates until all outliers are thrown out."""

    avg_zeropoint = 40.0
    std_zeropoint = 10.0
    num_iter = 0
    num_in_calc = 0
    r_mag_diff_threshold = 40.0
    count = 0

    while num_iter < 800:

        if std_zeropoint > std_zeropoint_tolerance:
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

            if count > 2:
                avg_zeropoint = sum_r_mag_mean_numerator / sum_r_mag_mean_denominator  # weighted mean zeropoint
            else:
                avg_zeropoint = 40.0

            y = 0
            for value in cross_match_table['r mag diff']:
                if cross_match_table['r mag Cat 1'][y] != 'nan' and cross_match_table['r mag Cat 2'][y] != 'nan':
                    if abs(value - avg_zeropoint) < r_mag_diff_threshold:
                        std_zeropoint_numerator += ((1.0 / cross_match_table['r mag err'][y]) * (cross_match_table['r mag diff'][y] - avg_zeropoint)**2)
                        std_zeropoint_denominator += (1.0 / cross_match_table['r mag err'][y])
                y += 1

            if count > 2:
                std_zeropoint = sqrt(std_zeropoint_numerator / (((float(count) - 1)/float(count)) * std_zeropoint_denominator))
            else:
                std_zeropoint = 10.0

        r_mag_diff_threshold -= 0.05
        num_iter += 1

    return avg_zeropoint, std_zeropoint, count, num_in_calc


def write_ldac(table, output_file):
    """
    write out a reference catalog table in new FITS_LDAC file (mainly for use in SCAMP)
    input: <table>, an Astropy Table of data, <output_file>, filename to write out
    return: number of sources written to file
    """

    # create primary header (empty)
    primaryhdu = fits.PrimaryHDU(header=fits.Header())

    # create header table
    hdr_col = fits.Column(name='Field Header Card', format='1680A',
                          array=["obtained through Vizier"])
    hdrhdu = fits.BinTableHDU.from_columns(fits.ColDefs([hdr_col]))
    hdrhdu.header['EXTNAME'] = 'LDAC_IMHEAD'
    # hdrhdu.header['TDIM1'] = ('(80, 36)') # remove?

    # create data table
    colname_dict = { 'RAJ2000'  : 'XWIN_WORLD',
                     'DEJ2000'  : 'YWIN_WORLD',
                     'e_RAJ2000': 'ERRAWIN_WORLD',
                     'e_DEJ2000': 'ERRBWIN_WORLD',
                     'mag'      : 'MAG',
                     'e_mag'    : 'MAGERR'
                   }
    format_dict = { 'RAJ2000'   : '1D',
                    'DEJ2000'   : '1D',
                    'e_RAJ2000' : '1E',
                    'e_DEJ2000' : '1E',
                    'mag'       : '1E',
                    'e_mag'     : '1E'
                  }
    disp_dict = { 'RAJ2000'   : 'E15',
                  'DEJ2000'   : 'E15',
                  'e_RAJ2000' : 'E12',
                  'e_DEJ2000' : 'E12',
                  'mag'       : 'F8.4',
                  'e_mag'     : 'F8.5'
                }
    unit_dict = { 'RAJ2000'   : 'deg', 
                  'DEJ2000'   : 'deg',
                  'e_RAJ2000' : 'deg',
                  'e_DEJ2000' : 'deg',
                  'mag'       : 'mag',
                  'e_mag'     : 'mag'
                }

    data_cols = []
    for col_name in table.columns:
        if col_name not in list(colname_dict.keys()):
            continue
        data_cols.append(fits.Column(name=colname_dict[col_name],
                                     format=format_dict[col_name],
                                     array=table[col_name],
                                     unit=unit_dict[col_name],
                                     disp=disp_dict[col_name]))

    data_cols.append(fits.Column(name='OBSDATE',
                                 disp='F13.8',
                                 format='1D',
                                 unit='yr',
                                 array=np.ones(len(table))*2015.5))

    datahdu = fits.BinTableHDU.from_columns(fits.ColDefs(data_cols))
    datahdu.header['EXTNAME'] = 'LDAC_OBJECTS'

    num_sources = len(table)

    # # combine HDUs and write file
    hdulist = fits.HDUList([primaryhdu, hdrhdu, datahdu])
    if float(astropyversion.split('.')[0]) > 1:
        hdulist.writeto(output_file, overwrite=True)
    elif float(astropyversion.split('.')[1]) >= 3:
        hdulist.writeto(output_file, overwrite=True)
    else:
        hdulist.writeto(output_file, clobber=True)

    logger.info('wrote {:d} sources from {} to LDAC file'.format(num_sources, output_file))

    return num_sources


def convert_catfile_to_corners(cat_file):
    regex = re.compile(r"([a-zA-Z0-9-]+)_(\d{0,3}.\d*)([+-]\d*.\d*)_(\d*.\d*)mx(\d*.\d*)m.cat")
    top_left = None
    bottom_right = None

    m = regex.search(cat_file)
    if m:
        if len(m.groups()) == 5:
            ra = float(m.group(2))
            dec = float(m.group(3))
            width = float(m.group(4)) / 60.0 / 2.0
            height = float(m.group(5)) / 60.0 / 2.0
            top_left = (ra+width, dec+height)
            bottom_right = (ra-width, dec-height)
    return top_left, bottom_right


def existing_catalog_coverage(dest_dir, ra, dec, width, height, cat_name="GAIA-DR2", dbg=False):
    """Search in <dest_dir> for catalogs of type [cat_name] that cover the
    pointing specified by <ra, dec> and with area <width, height>. The first
    match that covers the area is returned otherwise None is returned"""

    cat_file = None
    cat_path = os.path.join(dest_dir, '')
    if os.path.isdir(cat_path):
        cat_files = glob(cat_path + cat_name + '*.cat')
        if len(cat_files) >= 1:
            unit = width[-1]
            if unit == 'm':
                half_width = float(width[0:-1]) / 60.0 / 2.0
            elif unit == 'd':
                half_width = float(width[0:-1]) / 2.0
            else:
                logger.error("Unrecognized unit")
                half_width = float(width) / 2.0
            unit = height[-1]
            if unit == 'm':
                half_height = float(height[0:-1]) / 60.0 / 2.0
            elif unit == 'd':
                half_height = float(height[0:-1]) / 2.0
            else:
                logger.error("Unrecognized unit")
                half_height = float(height) / 2.0
            top_left = (ra + half_width, dec + half_height)
            bottom_right = (ra - half_width, dec - half_height)
            if dbg:
                print("Frame=", top_left, bottom_right)
            for test_file in cat_files:
                if dbg:
                    print("catalog=", test_file)
                cat_top_left, cat_bottom_right = convert_catfile_to_corners(test_file)
                if dbg:
                    print("Catalog=", cat_top_left, cat_bottom_right)
                if cat_top_left is not None and cat_bottom_right is not None:
                    if cat_top_left[0] >= top_left[0] and cat_bottom_right[0] <= bottom_right[0] and\
                            cat_top_left[1] >= top_left[1] and cat_bottom_right[1] <= bottom_right[1]:
                        cat_file = test_file
                        if dbg:
                            print(" Inside bounds")
                    else:
                        if dbg:
                            print("Outside bounds")
    return cat_file


def get_reference_catalog(dest_dir, ra, dec, set_width, set_height, cat_name="GAIA-DR2", set_row_limit=10000, rmag_limit="<=18.0", dbg=False):
    """Download and save a catalog from [cat_name] (defaults to 'GAIA-DR2') into
    the passed <dest_dir> around the passed (ra, dec) co-ordinates and width and
    height. The catalog file will be of the form <dest_dir/<cat_name>.cat, with
    any hyphens removed.
    The path to the reference catalog and the number of sources written are
    returned. If the catalog already exists, the path and '-1' will be returned.
    """

    num_sources = None

    # Check for existing reference catalog
    refcat = existing_catalog_coverage(dest_dir, ra, dec, set_width, set_height, cat_name, dbg)
    if dbg:
        print("refcat=", refcat)
    if refcat is not None and os.path.exists(refcat):
        logger.debug("Reference catalog {} already exists".format(refcat))
        return refcat, -1

    # Add 50% to passed width and height in lieu of actual calculation of extent
    # of a series of frames
    units = set_width[-1]
    try:
        ref_width = float(set_width[:-1]) * 1.5
        ref_width = "{:.4f}{}".format(ref_width, units)
    except ValueError:
        ref_width = set_width
    units = set_height[-1]
    try:
        ref_height = float(set_height[:-1]) * 1.5
        ref_height = "{:.4f}{}".format(ref_height, units)
    except ValueError:
        ref_height = set_height
    cat_table, final_cat_name = get_vizier_catalog_table(ra, dec, ref_width, ref_height, cat_name, set_row_limit, rmag_limit)

    # Rewrite name of catalog to include position and size
    refcat = "{}_{ra:.2f}{dec:+.2f}_{width}x{height}.cat".format(cat_name, ra=ra, dec=dec, width=ref_width, height=ref_height)
    refcat = os.path.join(dest_dir, refcat)

    if final_cat_name != cat_name:
        logger.warning("Did not get catalog type that was expected ({} vs {})".format(final_cat_name, cat_name))
        refcat = None
    else:
        # Rename and standardize column names, add error units and convert to degrees
        cat_table.rename_column('Gmag', 'mag')
        cat_table.rename_column('e_Gmag', 'e_mag')
        if type(cat_table['e_RAJ2000'].unit) == 'str':
            cat_table['e_RAJ2000'] = cat_table['e_RAJ2000'] * u.mas
        cat_table['e_RAJ2000'] = cat_table['e_RAJ2000'].to(u.deg)
        if type(cat_table['e_DEJ2000'].unit) == 'str':
            cat_table['e_DEJ2000'] = cat_table['e_DEJ2000'] * u.mas
        cat_table['e_DEJ2000'] = cat_table['e_DEJ2000'].to(u.deg)
        num_sources = write_ldac(cat_table, refcat)
    return refcat, num_sources


class FITSHdrException(Exception):
    """Raised when a required FITS header keyword is missing"""

    def __init__(self, keyword):
        self.keyword = keyword

    def __str__(self):
        return "Required keyword '" + self.keyword + "' missing"


class FITSTblException(Exception):
    """Raised when a required FITS table column is missing"""

    def __init__(self, column):
        self.column = column

    def __str__(self):
        return "Required column '" + self.column + "' missing"


def oracdr_catalog_mapping():
    """Returns two dictionaries of the mapping between the FITS header and table
    items and CatalogItem quantities for LCOGT ORAC-DR pipeline format catalog
    files."""

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
    """Returns two dictionaries of the mapping between the FITS header and table
    items and CatalogItem quantities for FITS_LDAC format catalog files (as used
    by SCAMP)."""

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


def banzai_catalog_mapping():
    """Returns two dictionaries of the mapping between the FITS header and table
    items and CatalogItem quantities for new pipeline (BANZAI) format catalog
    files. Items in angle brackets (<FOO>) need to be derived (pixel scale)
    or assumed as they are missing from the headers."""

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
                    'pixel_scale' : '<WCS>',
                    'zeropoint'     : '<ZP>',
                    'zeropoint_err' : '<ZP>',
                    'zeropoint_src' : '<ZPSRC>',
                    'fwhm'          : 'L1FWHM',
                    'astrometric_fit_rms'    : '<WCSRDRES>',
                    'astrometric_fit_status' : 'WCSERR',
                    'astrometric_fit_nstars' : '<WCSMATCH>',
                    'astrometric_catalog'    : '<WCCATTYP>',
                    'reduction_level'        : 'RLEVEL'
                  }

    table_dict = OrderedDict([
                    ('ccd_x'         , 'XWIN'),
                    ('ccd_y'         , 'YWIN'),
                    ('obs_ra'        , 'RA'),
                    ('obs_dec'       , 'DEC'),
                    # ('obs_ra_err'    , 'ERRX2_WORLD'),
                    # ('obs_dec_err'   , 'ERRY2_WORLD'),
                    ('major_axis'    , 'A'),
                    ('minor_axis'    , 'B'),
                    ('ccd_pa'        , 'THETA'),
                    ('obs_mag'       , 'FLUX'),
                    ('obs_mag_err'   , 'FLUXERR'),
                    ('obs_sky_bkgd'  , 'BACKGROUND'),
                    ('flags'         , 'FLAG'),
                    # ('flux_max'      , 'FLUX_MAX'),
                    # ('threshold'     , 'MU_THRESHOLD'),
                 ])

    return header_dict, table_dict


def banzai_ldac_catalog_mapping():
    """Returns two dictionaries of the mapping between the FITS header and table
    items and CatalogItem quantities for FITS_LDAC catalogs extracted from the
    new pipeline (BANZAI) format files. Items in angle brackets (<FOO>) need to
    be derived (pixel scale) or assumed as they are missing from the headers."""

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
                    'pixel_scale' : '<WCS>',
                    'zeropoint'     : '<ZP>',
                    'zeropoint_err' : '<ZP>',
                    'zeropoint_src' : '<ZPSRC>',
                    'fwhm'          : 'L1FWHM',
                    'astrometric_fit_rms'    : '<WCSRDRES>',
                    'astrometric_fit_status' : 'WCSERR',
                    'astrometric_fit_nstars' : '<WCSMATCH>',
                    'astrometric_catalog'    : '<WCCATTYP>',
                    'reduction_level'        : 'RLEVEL'
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
                            value = True
                        elif value.strip() == 'F':
                            value = False
                comment = ''
                if 8 < comment_loc <= len(card):
                    comment = card[comment_loc+2:]
                header.append((keyword, value, comment), bottom=True)

        i += 1

    return header


def open_fits_catalog(catfile, header_only=False):
    """Opens a FITS source catalog specified by <catfile> and returns the header,
    table data and catalog type. If [header_only]= is True, only the header is
    returned, and <table> is set to an empty dictionary."""

    header = {}
    table = {}
    cattype = None

    try:
        hdulist = fits.open(catfile)
    except IOError as e:
        logger.error("Unable to open FITS catalog %s (Reason=%s)" % (catfile, e))
        return header, table, cattype

    # Verify HDUs first
    try:
        for hdu in hdulist:
            hdu.verify('exception')
    except OSError:
        logger.error("Verification of FITS catalog {} failed".format(catfile))
        return header, table, 'CORRUPT'

    if len(hdulist) == 2:
        header = hdulist[0].header
        cattype = 'LCOGT'
        if header_only is False:
            table = hdulist[1].data
    elif len(hdulist) == 3 and hdulist[1].header.get('EXTNAME', None) == 'LDAC_IMHEAD':
        # This is a FITS_LDAC catalog produced by SExtractor for SCAMP
        if header_only is False:
            table = hdulist[2].data
        cattype = 'FITS_LDAC'
        if 'e92_ldac' in catfile or 'e12_ldac' in catfile:
            cattype = 'BANZAI_LDAC'
        header_array = hdulist[1].data[0][0]
        header = fits_ldac_to_header(header_array)
    elif len(hdulist) == 4 or (len(hdulist) == 3 and hdulist[1].header.get('EXTNAME', None) != 'LDAC_IMHEAD'):
        # New BANZAI-format data
        cattype = 'BANZAI'
        try:
            sci_index = hdulist.index_of('SCI')
        except KeyError:
            sci_index = -1
        try:
            cat_index = hdulist.index_of('CAT')
        except KeyError:
            cat_index = -1

        if sci_index != -1 and cat_index != -1:
            header = hdulist[sci_index].header
            if header_only is False:
                table = hdulist[cat_index].data
        else:
            logger.error("Could not find SCI and CAT HDUs in file")
    elif len(hdulist) == 1:
        # BANZAI-format after extraction of image
        cattype = 'BANZAI'
        try:
            sci_index = hdulist.index_of('SCI')
        except KeyError:
            sci_index = -1

        if sci_index != -1:
            header = hdulist[sci_index].header
        else:
            logger.error("Could not find SCI HDU in file")
    else:
        logger.error("Unexpected number of catalog HDUs (Expected 2, got %d)" % len(hdulist))

    hdulist.close()

    return header, table, cattype


def convert_value(keyword, value):
    """Routine to perform domain-specific transformation of values read from the
    FITS catalog.
    """

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
            logger.warning("Trying to convert a -ve flux to a magnitude")
    elif keyword == 'obs_mag_err':
        try:
            newvalue = FLUX2MAG * (value[0]/value[1])
        except IndexError:
            logger.warning("Need to pass a tuple of (flux error, flux) to compute a magnitude error")
    elif keyword == 'field_center_ra':
        ra = Angle(value, unit=u.hour)
        newvalue = ra.deg
    elif keyword == 'field_center_dec':
        dec = Angle(value, unit=u.deg)
        newvalue = dec.deg
    elif keyword == 'field_width' or keyword == 'field_height':
        try:
            # Calculate width/height by multiplying number of pixels by pixel scale and converting to arcmin
            dimension = (value[0]*value[1])/60.0
            newvalue = "%.4fm" % dimension
        except IndexError:
            logger.warning("Need to pass a tuple of (number of x/y pixels, pixel scale) to compute a width/height")
    elif keyword == 'mu_threshold':
        try:
            # Calculate threshold in magnitudes per sq. arcsec by dividing the
            # threshold counts by pixel area and converting to a magnitude
            newvalue = pow(10, (value[0]/-2.5)) * (value[1]*value[1])
        except IndexError:
            logger.warning("Need to pass a tuple of (threshold in mag per sq. arcsec, pixel scale) to compute a threshold")
        except TypeError:
            logger.warning("Need to pass a tuple of (threshold in mag per sq. arcsec, pixel scale) to compute a threshold")

    return newvalue


def get_catalog_header(catalog_header, catalog_type='LCOGT', debug=False):
    """Look through the FITS catalog header for the concepts we want for which
    the keyword is given in the mapping specified for the [catalog_type]

    The required header items are returned in a dictionary. A FITSHdrException
    is raised if a required keyword is missing or the value of a keyword is
    'UNKNOWN'.
    """

    fixed_values_map = {'<WCCATTYP>'  : '2MASS',  # Hardwire catalog to 2MASS for BANZAI's astrometry.net-based solves 
                                                  # (but could be modified based on version number further down)
                        '<ZP>'        : -99,      # Hardwire zeropoint to -99.0 for BANZAI catalogs
                        '<ZPSRC>'     : 'N/A',    # Hardwire zeropoint src to 'N/A' for BANZAI catalogs
                        '<WCSRDRES>'  : 0.3,      # Hardwire RMS to 0.3"
                        '<WCSMATCH>'  : -4        # Hardwire no. of stars matched to 4 (1 quad)
                        }

    header_items = {}
    if catalog_type == 'LCOGT':
        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
    elif catalog_type == 'FITS_LDAC':
        hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
    elif catalog_type == 'BANZAI':
        hdr_mapping, tbl_mapping = banzai_catalog_mapping()
    elif catalog_type == 'BANZAI_LDAC':
        hdr_mapping, tbl_mapping = banzai_ldac_catalog_mapping()
    else:
        logger.error("Unsupported catalog mapping: %s", catalog_type)
        return header_items

    for item in hdr_mapping.keys():
        fits_keyword = hdr_mapping[item]
        if fits_keyword in catalog_header:
            # Found, extract value
            value = catalog_header[fits_keyword]
            if value == 'UNKNOWN':
                if debug:
                    logger.debug('UNKNOWN value found for %s', fits_keyword)
                raise FITSHdrException(fits_keyword)
            # Convert if necessary
            if item != 'field_width' and item != 'field_height':
                new_value = convert_value(item, value)
            else:
                new_value = value
            header_item = { item: new_value}
            header_items.update(header_item)
        elif fits_keyword[0] == '<' and fits_keyword[-1] == '>':
            header_item = None
            if fits_keyword == '<WCS>':
                # Suppress warnings from newer astropy versions which raise
                # FITSFixedWarning on the lack of OBSGEO-L,-B,-H keywords even
                # though we have OBSGEO-X,-Y,-Z as recommended by the FITS
                # Paper VII standard...
                warnings.simplefilter('ignore', category=FITSFixedWarning)
                fits_wcs = WCS(catalog_header)
                pixscale = proj_plane_pixel_scales(fits_wcs).mean()*3600.0
                header_item = {item: round(pixscale, 5), 'wcs' : fits_wcs}
            if catalog_type == 'BANZAI' or catalog_type == 'BANZAI_LDAC':
                # See if there is a version of the keyword in the file first
                file_fits_keyword = fits_keyword[1:-1]
                if catalog_header.get(file_fits_keyword, None):
                    value = catalog_header[file_fits_keyword]
                    # Convert if necessary
                    if item != 'field_width' and item != 'field_height':
                        new_value = convert_value(item, value)
                    else:
                        new_value = value
                    header_item = { item: new_value}
                else:
                    if fits_keyword in fixed_values_map:
                        if fits_keyword == "<WCCATTYP>":
                            # This now needs special handling as the value
                            # is BANZAI version dependent...
                            pipever = catalog_header.get("PIPEVER", None)
                            if pipever is not None:
                                # Determine major and minor version
                                pipe_versions = pipever.split('.')
                                try:
                                    major = int(pipe_versions[0])
                                    minor = int(pipe_versions[1])
                                    astrom_catalog = fixed_values_map[fits_keyword]
                                    if major >= 1 or (major == 0 and minor >= 20):
                                        # BANZAI versions after 0.20.0 use GAIA-DR2
                                        astrom_catalog = 'GAIA-DR2'
                                    header_item = {item: astrom_catalog}
                                except ValueError:
                                    filename = catalog_header['origname'].replace('00.fits', str(catalog_header['rlevel']) + '.fits')
                                    logger.warning("Could not extract a pipeline version from " + filename)
                                    header_item = {item: fixed_values_map[fits_keyword]}
                        else:
                            header_item = {item: fixed_values_map[fits_keyword]}
            if header_item:
                header_items.update(header_item)
        else:
            raise FITSHdrException(fits_keyword)

    if 'obs_date' in header_items and 'exptime' in header_items:
        try:
            header_items['exptime'] = float(header_items['exptime'])
        except ValueError:
            pass
        header_items['obs_midpoint'] = header_items['obs_date'] + timedelta(seconds=header_items['exptime'] / 2.0)
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


def get_catalog_items_old(header_items, table, catalog_type='LCOGT', flag_filter=0):
    """Extract the needed columns specified in the mapping from the FITS
    binary table. Sources with a FLAGS value greater than [flag_filter]
    will not be returned.
    The sources in the catalog are returned as an AstroPy Table containing
    the subset of columns specified in the table mapping."""

    if catalog_type == 'LCOGT':
        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
    elif catalog_type == 'FITS_LDAC':
        hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
    elif catalog_type == 'BANZAI':
        hdr_mapping, tbl_mapping = banzai_catalog_mapping()
    elif catalog_type == 'BANZAI_LDAC':
        hdr_mapping, tbl_mapping = banzai_ldac_catalog_mapping()
    else:
        logger.error("Unsupported catalog mapping: %s", catalog_type)
        return None

    # Check if all columns exist first
    for column in tbl_mapping.values():
        if column not in table.names:
            raise FITSTblException(column)

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
                new_column = {item : new_value}
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


def get_catalog_items_new(header_items, table, catalog_type='LCOGT', flag_filter=0, neg_flux_mask=True):
    """Extract the needed columns specified in the mapping from the FITS
    binary table. Sources with a FLAGS value greater than [flag_filter]
    will not be returned.
    If [neg_flux_mask] is True (the default), then sources with -ve flux will
    be removed from the returned table.
    The sources in the catalog are returned as an AstroPy Table containing
    the subset of columns specified in the table mapping."""

    if catalog_type == 'LCOGT':
        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
    elif catalog_type == 'FITS_LDAC':
        hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
    elif catalog_type == 'BANZAI':
        hdr_mapping, tbl_mapping = banzai_catalog_mapping()
    elif catalog_type == 'BANZAI_LDAC':
        hdr_mapping, tbl_mapping = banzai_ldac_catalog_mapping()
    else:
        logger.error("Unsupported catalog mapping: %s", catalog_type)
        return None

    # Check if all columns exist first
    for column in tbl_mapping.values():
        if column not in table.names:
            raise FITSTblException(column)

    new_table = subset_catalog_table(table, tbl_mapping)
    # Rename columns
    for new_name in tbl_mapping:
        new_table.rename_column(tbl_mapping[new_name], new_name)

    # Filter on flags first
    if 'flags' in tbl_mapping:
        size_before = len(new_table)
        new_table = new_table[new_table['flags'] <= flag_filter]
        size_after = len(new_table)
        logger.debug("Filtered table. Number of sources {}->{}".format(size_before, size_after))

    # Filter out -ve fluxes
    if neg_flux_mask:
        good_flux_mask = new_table['obs_mag'] > 0.0
        new_table = new_table[good_flux_mask]
    # Convert columns
    new_table['obs_ra_err'] = np.sqrt(new_table['obs_ra_err'])
    new_table['obs_dec_err'] = np.sqrt(new_table['obs_dec_err'])
    FLUX2MAG = 2.5/log(10)
    new_table['obs_mag_err'] = FLUX2MAG * (new_table['obs_mag_err'] / new_table['obs_mag'])
    new_table['obs_mag'] = -2.5 * np.log10(new_table['obs_mag'])
    if 'threshold' in tbl_mapping.keys() and 'MU_' in tbl_mapping['threshold'].upper():
        scale = header_items['pixel_scale'] * header_items['pixel_scale']
        new_table['threshold'] = np.power(10, (new_table['threshold']/-2.5)) * scale
    if header_items.get('zeropoint', -99) != -99:
        new_table['obs_mag'] += header_items['zeropoint']

    return new_table


def update_ldac_catalog_wcs(fits_image_file, fits_catalog, overwrite=True):
    """Updates the world co-ordinates (ALPHA_J2000, DELTA_J2000) in a FITS LDAC
    catalog <fits_catalog> with a new WCS read from a FITS image
    <fits_image_file>.
    The transformation is done using the CCD XWIN_IMAGE, YWIN_IMAGE values
    passed through astropy's all_pix2world().
    """

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

    # Pull out columns as arrays
    ccd_x = tbl_table[tbl_mapping['ccd_x']]
    ccd_y = tbl_table[tbl_mapping['ccd_y']]

    new_ra, new_dec = new_wcs.all_pix2world(ccd_x, ccd_y, 1)

    tbl_table[tbl_mapping['obs_ra']] = new_ra
    tbl_table[tbl_mapping['obs_dec']] = new_dec

    # Write out new catalog file
    new_fits_catalog = fits_catalog
    to_overwrite = True
    if overwrite is not True:
        new_fits_catalog += '.new'
        to_overwrite = False
    hdulist.writeto(new_fits_catalog, checksum=True, overwrite=to_overwrite)
    return status


def remove_corrupt_catalog(catfile):
    """Removes the corrupted file <catfile> from disk and from the DB (if able).
    Returns a tuple of whether the disk files was removed (True/False) and the
    number of db records deleted (or -1 if the Frame wasn't found in the db)
    """

    removed = False
    try:
        os.unlink(catfile)
        logger.warning(f'Removed corrupted file {catfile}')
        removed = True
    except OSError as e:
        logger.error(f'Unable to remove corrupted {catfile}')

    num_deleted = 0
    fileroot = os.path.basename(catfile)
    split_loc = fileroot.rfind('-e9')
    if split_loc > 0:
        fileroot = fileroot[:split_loc]
    try:
        frames = Frame.objects.filter(filename__startswith=fileroot, \
            frametype__in=(Frame.BANZAI_LDAC_CATALOG, Frame.FITS_LDAC_CATALOG))
        # No way will this ever end badly...
        num_deleted, types_deleted = frames.delete()
        logger.info(f'Deleted Frames {frames}')
    except Frame.DoesNotExist:
        logger.warning(f'Unable to delete DB records associated with {fileroot}')
        num_deleted = -1

    return removed, num_deleted

def extract_catalog(catfile, catalog_type='LCOGT', flag_filter=0, new=True, remove=False):
    """High-level routine to read LCOGT FITS catalogs from <catfile>.
    This returns a dictionary of needed header items and an AstroPy table of
    the sources that pass the [flag_filter] cut-off or None if the file could
    not be opened. If [remove]=True, then if the <catfile> fails header
    verification in open_fits_catalog(), it will be deleted here."""

    header = table = None
    fits_header, fits_table, cattype = open_fits_catalog(catfile)

    if cattype == 'CORRUPT' and remove is True:
        removed, num_db_deleted = remove_corrupt_catalog(catfile)
        remove_str = 'was not'
        if removed:
            remove_str = 'was'
        logger.warning(f'Corrupt {catfile} {remove_str} removed from disk. {num_db_deleted} Frame records removed from DB')

    if len(fits_header) != 0 and len(fits_table) != 0:
        header = get_catalog_header(fits_header, catalog_type)
        # get_catalog_items() is the slow part
        if new:
            table = get_catalog_items_new(header, fits_table, catalog_type, flag_filter)
        else:
            table = get_catalog_items_old(header, fits_table, catalog_type, flag_filter)

    return header, table


def update_zeropoint(header, table, avg_zeropoint, std_zeropoint):

    header['zeropoint'] = avg_zeropoint
    header['zeropoint_err'] = std_zeropoint
    header['zeropoint_src'] = 'py_zp_match-V0.3'

    for source in table:
        source['obs_mag'] += avg_zeropoint
        # source['obs_mag_err'] = sqrt(((source['obs_mag_err']/source['obs_mag'])**2.0) + ((header['zeropoint_err']/header['zeropoint'])**2.0))
        source['obs_mag_err'] = sqrt((source['obs_mag_err']**2.0) + (header['zeropoint_err']**2.0))

    return header, table


def update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filename, frame_type):
    """update the Frame zeropoint, astrometric fit, astrometric catalog
    and photometric catalog used"""

    # if a Frame exists for the file, update the zeropoint,
    # astrometric catalog, rms_of_fit, nstars_in_fit, and
    # photometric catalog in the Frame
    try:
        frame = Frame.objects.get(filename=frame_filename, block__isnull=False)
        frame.zeropoint = header['zeropoint']
        frame.zeropoint_err = header['zeropoint_err']
        frame.rms_of_fit = header['astrometric_fit_rms']
        frame.nstars_in_fit = header['astrometric_fit_nstars']
        frame.astrometric_catalog = header.get('astrometric_catalog', ast_cat_name)
        frame.photometric_catalog = header.get('photometric_catalog', phot_cat_name)
        frame.save()
    except Frame.MultipleObjectsReturned:
        pass
    # except Frame.DoesNotExist:
    #     store sources in neoexchange(CatalogSources table)
    #     frame_params = {    'sitecode':header['site_code'],
    #                         'instrument':header['instrument'],
    #                         'filter':header['filter'],
    #                         'filename':frame_filename,
    #                         'exptime':header['exptime'],
    #                         'midpoint':header['obs_midpoint'],
    #                         'block':frame.block,
    #                         'zeropoint':header['zeropoint'],
    #                         'zeropoint_err':header['zeropoint_err'],
    #                         'fwhm':header['fwhm'],
    #                         'frametype':frame_type,
    #                         'rms_of_fit':header['astrometric_fit_rms'],
    #                         'nstars_in_fit':header['astrometric_fit_nstars'],
    #                     }
    #
    #     frame, created = Frame.objects.get_or_create(**frame_params)
    #     if created == True:
    #         num_new_frames_created += 1
    #         frame.astrometric_catalog = ast_cat_name
    #         frame.photometric_catalog = phot_cat_name
    #         frame.save()

    return frame


@timeit
def store_catalog_sources(catfile, catalog_type='LCOGT', std_zeropoint_tolerance=0.1, phot_cat_name="UCAC4", ast_cat_name="2MASS"):

    num_new_frames_created = 0
    num_in_table = 0
    num_sources_created = 0

    # read the catalog file. Allow removal of corrupted LDAC files.
    start = time.time()
    header, table = extract_catalog(catfile, catalog_type, remove=True)
    end = time.time()
    logger.debug("TIME: extract_catalog took {:.1f} seconds".format(end-start))

    if header and table:

        # check for good zeropoints
        if header.get('zeropoint', -99) == -99 or header.get('zeropoint_err', -99) == -99:
            # if bad, determine new zeropoint
            logger.debug("Refitting zeropoint, tolerance set to {}".format(std_zeropoint_tolerance))
            start = time.time()
            if '2m0' in header.get('framename', ''):
                rmag_limit = '<=18.0'
            else:
                rmag_limit = '<=15.0'
            header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, phot_cat_name = call_cross_match_and_zeropoint((header, table), std_zeropoint_tolerance, phot_cat_name, rmag_limit=rmag_limit)
            end = time.time()
            logger.debug("TIME: compute_zeropoint took {:.1f} seconds".format(end-start))
            logger.debug("New zp={} {} {} {}".format(avg_zeropoint, std_zeropoint, count, num_in_calc))
            # if crossmatch is good, update new zeropoint
            if std_zeropoint < std_zeropoint_tolerance:
                logger.debug("Got good zeropoint - updating header")
                header, table = update_zeropoint(header, table, avg_zeropoint, std_zeropoint)

                # get the fits filename from the catfile in order to get the Block from the Frame
                if 'e90_cat.fits' in os.path.basename(catfile):
                    fits_file = os.path.basename(catfile.replace('e90_cat.fits', 'e90.fits'))
                if 'e91_ldac.fits' in os.path.basename(catfile):
                    fits_file = os.path.basename(catfile.replace('e91_ldac.fits', 'e91.fits'))
                elif 'e10_cat.fits' in os.path.basename(catfile):
                    fits_file = os.path.basename(catfile.replace('e10_cat.fits', 'e10.fits'))
                elif 'e11_ldac.fits' in os.path.basename(catfile):
                    fits_file = os.path.basename(catfile.replace('e11_ldac.fits', 'e11.fits'))
                elif 'e92_ldac.fits' in os.path.basename(catfile):
                    fits_file = os.path.basename(catfile.replace('e92_ldac.fits', 'e91.fits'))
                elif 'e12_ldac.fits' in os.path.basename(catfile):
                    fits_file = os.path.basename(catfile.replace('e12_ldac.fits', 'e11.fits'))
                else:
                    fits_file = os.path.basename(catfile)

                # update the zeropoint computed above in the FITS file Frame
                frame = update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filename=fits_file, frame_type=Frame.SINGLE_FRAMETYPE)

                # update the zeropoint computed above in the CATALOG file Frame
                frame_cat = update_frame_zeropoint(header, ast_cat_name, phot_cat_name, frame_filename=os.path.basename(catfile), frame_type=Frame.BANZAI_LDAC_CATALOG)

                # store the CatalogSources
                num_sources_created, num_in_table = get_or_create_CatalogSources(table, frame)
            else:
                logger.warning("Didn't get good zeropoint - not updating header")
    else:
        logger.warning("Could not open %s" % catfile)

    return num_sources_created, num_in_table


def get_or_create_CatalogSources(table, frame):

    num_sources_created = 0

    num_in_table = len(table)
    num_cat_sources = CatalogSources.objects.filter(frame=frame).count()
    if num_cat_sources == 0:
        new_sources = []
        for source in table:
            new_source = CatalogSources(frame=frame, obs_x=source['ccd_x'], obs_y=source['ccd_y'], 
                                        obs_ra=source['obs_ra'], obs_dec=source['obs_dec'], obs_mag=source['obs_mag'], 
                                        err_obs_ra=source['obs_ra_err'], err_obs_dec=source['obs_dec_err'], 
                                        err_obs_mag=source['obs_mag_err'], background=source['obs_sky_bkgd'], 
                                        major_axis=source['major_axis'], minor_axis=source['minor_axis'], 
                                        position_angle=source['ccd_pa'], ellipticity=1.0-(source['minor_axis']/source['major_axis']), 
                                        aperture_size=3.0, flags=source['flags'], flux_max=source['flux_max'], threshold=source['threshold'])
            new_sources.append(new_source)
        try:
            with transaction.atomic():
                CatalogSources.objects.bulk_create(new_sources, batch_size=200)
        except:
            CatalogSources.objects.bulk_create(new_sources)
        num_sources_created = len(new_sources)
    elif num_in_table != num_cat_sources:
        for source in table:
            source_params = {   'frame': frame,
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
            if created is True:
                num_sources_created += 1
    else:
        logger.info("Number of sources in catalog match number in DB; skipping")

    return num_sources_created, num_in_table


def make_sext_dict(catsrc, num_iter):
    """create a dictionary of needed parameters
    for the .sext file creation needed for mtdlink"""
    sext_params = { 'number': num_iter,
                    'obs_x': catsrc.obs_x,
                    'obs_y': catsrc.obs_y,
                    'obs_mag': catsrc.obs_mag,
                    'theta': catsrc.position_angle,
                    'elongation': catsrc.make_elongation(),
                    'fwhm': catsrc.make_fwhm(),
                    'flags': catsrc.flags,
                    'deltamu': catsrc.make_mu_threshold()-catsrc.make_mu_max(),
                    'flux': catsrc.make_flux(),
                    'area': catsrc.make_area(),
                    'ra': catsrc.obs_ra,
                    'dec': catsrc.obs_dec
                  }

    return sext_params


def make_sext_file_line(sext_params):
    """format the print line for the .sext files
    needed for mtdlink"""

    print_format = "      %4i   %8.3f   %8.3f  %7.4f %6.1f    %8.3f     %5.2f   %1i  %4.2f   %12.1f   %3i %9.5f %9.5f"

    sext_line = print_format % (sext_params['number'], sext_params['obs_x'], sext_params['obs_y'], sext_params['obs_mag'], 
                                sext_params['theta'], sext_params['elongation'], sext_params['fwhm'], sext_params['flags'], 
                                sext_params['deltamu'], sext_params['flux'], sext_params['area'], sext_params['ra'], sext_params['dec'])

    return sext_line


def determine_image_for_catalog(new_catalog):
    """Determines the originating FITS filename for the passed catalog name,
    allowing correct naming for the corresponding .sext file"""
    if 'e92_ldac.fits' in new_catalog or 'e12_ldac.fits' in new_catalog:
        real_fits_filename = os.path.basename(new_catalog).replace('2_ldac.fits', '1.fits')
        fits_filename_path = new_catalog.replace('2_ldac.fits', '1.fits')
    elif '_ldac.fits' in new_catalog:
        real_fits_filename = os.path.basename(new_catalog).replace('_ldac.fits', '.fits')
        fits_filename_path = new_catalog.replace('_ldac.fits', '.fits')
    elif '_cat.fits' in new_catalog:
        real_fits_filename = os.path.basename(new_catalog).replace('_cat.fits', '.fits')
        fits_filename_path = new_catalog.replace('_cat.fits', '.fits')
    else:
        real_fits_filename = os.path.basename(new_catalog)
        fits_filename_path = new_catalog

    return real_fits_filename, fits_filename_path


def make_sext_dict_list(new_catalog, catalog_type, edge_trim_limit=75.0):
    """create a list of dictionary entries for
    creating the .sext files needed for mtdlink"""

    sext_dict_list = []

    # get correct fits filename for naming .sext file
    real_fits_filename, fits_filename_path = determine_image_for_catalog(new_catalog)

    # May need to filter objects within 5 pixels of frame edge as does in cleansex.tcl
    try:
        frame = Frame.objects.get(filename=real_fits_filename)
        edge_trim_limit, num_x_pixels, num_y_pixels = get_trim_limit(frame, edge_trim_limit)
    except Frame.MultipleObjectsReturned:
        logger.error("Found multiple versions of fits frame %s pointing at multiple blocks" % real_fits_filename)
        return -3, -3
    except Frame.DoesNotExist:
        logger.error("Frame entry for fits file %s does not exist" % real_fits_filename)
        return -3, -3
    sources = CatalogSources.objects.filter(frame__filename=real_fits_filename, obs_mag__gt=0.0, obs_x__gt=edge_trim_limit, 
                                            obs_x__lt=num_x_pixels-edge_trim_limit, obs_y__gt=edge_trim_limit, obs_y__lt=num_y_pixels-edge_trim_limit)
    num_iter = 1
    for source in sources:
        sext_dict_list.append(make_sext_dict(source, num_iter))
        num_iter += 1

    return sext_dict_list, fits_filename_path


def get_trim_limit(frame, edge_trim_limit):
    """determine if the image is a square 1-m image and trim
    or if the image is a non-square 0.4-m image and don't trim"""

    num_x_pixels = frame.get_x_size()
    num_y_pixels = frame.get_y_size()
    if abs(num_x_pixels-num_y_pixels) < 10.0:
        edge_trim_limit = edge_trim_limit
    else:
        edge_trim_limit = 0.0
    return edge_trim_limit, num_x_pixels, num_y_pixels


def make_sext_line_list(sext_dict_list):
    """sort the list of dictionary entries and
    create a list of formatted strings to be
    printed in the .sext files needed for mtdlink"""

    sext_line_list = []

    sext_dict_list_sorted = sorted(sext_dict_list, key=lambda k: k['obs_x'])

    for source in sext_dict_list_sorted:
        sext_line = make_sext_file_line(source)
        sext_line_list.append(sext_line)

    return sext_line_list


def make_sext_file(dest_dir, new_catalog, catalog_type):
    """Synthesizes the .sext file needed for running
    mtdlink instead of running sextractor again"""

    sext_dict_list, fits_filename_path = make_sext_dict_list(new_catalog, catalog_type)
    try:
        int(fits_filename_path)
        if fits_filename_path != 0:
            logger.error("Error making SExtractor file for %s" % new_catalog)
            return None
    except ValueError:
        pass
    sext_line_list = make_sext_line_list(sext_dict_list)
    sext_filename = open(os.path.join(dest_dir, os.path.basename(fits_filename_path).replace('.fits', '.sext')), 'w')
    for line in sext_line_list:
        sext_filename.write(line)
        sext_filename.write('\n')
    sext_filename.close()

    return fits_filename_path


def determine_filenames(product):
    """Given a passed <product> filename, determine the corresponding catalog
    filename and vice-versa
    """

    new_product = None
    full_path = product
    product = os.path.basename(product)
    if '_cat.fits' in product:
        new_product = product.replace('_cat', '', 1)
    elif '_ldac.fits' in product:
        new_product = product.replace('_ldac', '', 1)
    else:
        file_bits = product.split(os.extsep)
        if len(file_bits) == 2:
            filename_noext = file_bits[0]
            red_level = filename_noext[-2:]
            if red_level.isdigit():
                if int(red_level) == 90 or int(red_level) == 10:
                    new_product = filename_noext + '_cat' + os.extsep + file_bits[1]
                else:
                    # Uncompressed BANZAI product - output is input
                    new_product = file_bits[0] + os.extsep + file_bits[1]
        elif len(file_bits) == 3:
            # Fpacked BANZAI product - output is input
            new_product = None
            funpack_status = funpack_fits_file(full_path)
            if funpack_status == 0:
                new_product = file_bits[0] + os.extsep + file_bits[1]
    return new_product


def increment_red_level(product):
    """Determines the reduction level of a passed pipeline product <product>,
    and increments the reduction level by 1."""

    new_product = None
    product = os.path.basename(product)
    if '_cat' in product :
        file_bits = product.split('_cat')
        file_bits[1] = '_cat' + file_bits[1]
    elif '_ldac' in product :
        file_bits = product.split('_ldac')
        file_bits[1] = '_ldac' + file_bits[1]
    else:
        file_bits = product.split(os.extsep)
        file_bits[1] = os.extsep + file_bits[1]
    if len(file_bits) == 2:
        filename_noext = file_bits[0]
        red_level = filename_noext[-2:]
        if red_level.isdigit():
            red_level = "%02.2d" % (min(int(red_level)+1, 99),)
            filename_noext = filename_noext[:-2] + red_level
            new_product = filename_noext + file_bits[1]
    return new_product


def funpack_fits_file(fpack_file):
    """Calls 'funpack' on the passed <fpack_file> to uncompress it. A status
    value of 0 is returned if the unpacked file already exists or the uncompress
    was successful, -1 is returned otherwise"""

    file_bits = fpack_file.split(os.extsep)
    if len(file_bits) != 3 and file_bits[-1].lower() != 'fz':
        return -1
    unpacked_file = file_bits[0] + os.extsep + file_bits[1]
    if os.path.exists(unpacked_file):
        return 0
    hdulist = fits.open(fpack_file)
    header = hdulist['SCI'].header
    data = hdulist['SCI'].data
    hdu = fits.PrimaryHDU(data, header)
    hdu._bscale = 1.0
    hdu._bzero = 0.0
    hdu.header.insert("NAXIS2", ("BSCALE", 1.0), after=True)
    hdu.header.insert("BSCALE", ("BZERO", 0.0), after=True)
    hdu.writeto(unpacked_file, checksum=True)
    hdulist.close()

    return 0


def extract_sci_image(file_path, catalog_path):
    """Extracts the science image out of the BANZAI multi-extension fits files."""

    fits_file = os.path.basename(file_path)
    fits_filename_path = os.path.join(os.path.dirname(catalog_path), fits_file)

    if os.path.exists(fits_filename_path):
        return fits_filename_path

    try:
        hdulist = fits.open(file_path)
    except IOError as e:
        logger.error("Unable to open FITS catalog %s (Reason=%s)" % (catfile, e))

    try:
        sci_index = hdulist.index_of('SCI')
        hdulist = hdulist[sci_index]
        hdulist.writeto(fits_filename_path)
    except KeyError:
        sci_index = -1

    return fits_filename_path


def search_box(frame, ra, dec, box_halfwidth=3.0, dbg=False):
    """Search CatalogSources for the passed Frame object for sources within a
    box of <box_halfwidth> centered on <ra>, <dec>.
    <ra>, <dec> are in radians, <box_halfwidth> is in arcseconds, default is 3.0"
    """
    box_halfwidth_deg = box_halfwidth / 3600.0
    ra_deg = degrees(ra)
    dec_deg = degrees(dec)
    ra_min = ra_deg - box_halfwidth_deg / cos(dec)
    ra_max = ra_deg + box_halfwidth_deg / cos(dec)
    box_dec_min = dec_deg - box_halfwidth_deg
    box_dec_max = dec_deg + box_halfwidth_deg
    dec_min = min(box_dec_min, box_dec_max)
    dec_max = max(box_dec_min, box_dec_max)
    if dbg: 
        logger.debug("Searching %.4f->%.4f, %.4f->%.4f in %s" % (ra_min, ra_max, dec_min, dec_max , frame.filename))
    sources = CatalogSources.objects.filter(frame=frame, obs_ra__range=(ra_min, ra_max), obs_dec__range=(dec_min, dec_max))
    return sources


def get_fits_files(fits_path):
    """Look through a directory, uncompressing any fpacked files and return a
    list of all the .fits files"""

    sorted_fits_files = []
    fits_path = os.path.join(fits_path, '')
    if os.path.isdir(fits_path):

        fpacked_files = sorted(glob(fits_path + '*e91.fits.fz') + glob(fits_path + '*e11.fits.fz'))
        for fpack_file in fpacked_files:
            funpack_fits_file(fpack_file)

        sorted_fits_files = sorted(glob(fits_path + '*e91.fits') + glob(fits_path + '*e11.fits'))

    else:
        logger.error("Not a directory")

    return sorted_fits_files


def sanitize_object_name(object_name):
    """Remove problematic characters (space, slash) from object names so it
    can be used for e.g. directory names"""

    clean_object_name = None
    if type(object_name) == str or type(object_name) == np.str_:
        clean_object_name = object_name.strip().replace('(', '').replace(')', '')
        # collapse multiple sequential spaces into a single space.
        clean_object_name = ' '.join(clean_object_name.split())
        # Find the rightmost space and then do space->underscore mapping *left*
        # of that but space->empty string right of that.
        index = clean_object_name.rfind(' ')
        if index > 0:
            first_part = clean_object_name[0:index].replace(' ', '_')
            second_part = clean_object_name[index:].replace(' ', '')
            clean_object_name = first_part + second_part
        clean_object_name = clean_object_name.replace('/P', 'P').replace('/', '_')
        # Additional mangling for calibration stars (StaticSources)
        clean_object_name = clean_object_name.replace('+', '').replace('-', '_')

    return clean_object_name


def make_object_directory(filepath, object_name, block_id):

    object_directory = sanitize_object_name(object_name)
    if block_id != '':
        object_directory = object_directory + '_' + str(block_id)
    object_directory = os.path.join(os.path.dirname(filepath), object_directory)
    if not os.path.exists(object_directory):
        oldumask = os.umask(0o002)
        os.makedirs(object_directory)
        os.umask(oldumask)
    return object_directory


def sort_rocks(fits_files):
    """Takes a list of FITS files and creates directories for each asteroid
    object and unique block number (i.e. if an object is observed more than
    once, it will get a separate directory). The input fits files are then
    symlinked into the appropriate directory.
    A list of the directory names is return, with the entries being of the form
    <object name>_<block id #>"""

    objects = []
    for fits_filepath in fits_files:
        fits_header, fits_table, cattype = open_fits_catalog(fits_filepath, header_only=True)
        object_name = fits_header.get('OBJECT', None)
        block_id = fits_header.get('BLKUID', '').replace('/', '')
        if object_name:
            object_directory = make_object_directory(fits_filepath, object_name, block_id)
            if os.path.basename(object_directory) not in objects:
                objects.append(os.path.basename(object_directory))
            dest_filepath = os.path.join(object_directory, os.path.basename(fits_filepath))
            # if the file is an e91 and an e11 exists in the working directory, remove the link to the e11 and link the e91
            if 'e91' in fits_filepath:
                if os.path.lexists(dest_filepath.replace('e91.fits', 'e11.fits')):
                    os.unlink(dest_filepath.replace('e91.fits', 'e11.fits'))
                if not os.path.lexists(dest_filepath):
                    os.symlink(fits_filepath, dest_filepath)
            # if the file is an e11 and an e91 doesn't exit in the working directory, create link to the e11
            elif 'e11' in fits_filepath and not os.path.exists(dest_filepath.replace('e11.fits', 'e91.fits')):
                if not os.path.exists(dest_filepath):
                    os.symlink(fits_filepath, dest_filepath)
    return objects


def find_first_last_frames(fits_files):
    """Determines the first and last reduced frames in the DB for a list of
    passed <fits_files> (which may have paths).
    The Frame objects for the earliest and latest frames are returned if all
    are found, otherwise None is returned.
    """

    first_frame = Frame(midpoint=datetime.max)
    last_frame = Frame(midpoint=datetime.min)
    for fits_filepath in fits_files:
        fits_file = os.path.basename(fits_filepath)
        try:
            frame = Frame.objects.get(filename=fits_file, frametype__in=(Frame.BANZAI_QL_FRAMETYPE, Frame.BANZAI_RED_FRAMETYPE))
        except Frame.DoesNotExist:
            logger.error("Cannot find Frame DB entry for %s" % fits_file)
            first_frame = last_frame = None
            break
        except Frame.MultipleObjectsReturned:
            logger.error("Found multiple entries in DB for %s" % fits_file)
            first_frame = last_frame = None
            break
        if frame.midpoint < first_frame.midpoint:
            first_frame = frame
        if frame.midpoint > last_frame.midpoint:
            last_frame = frame
    return first_frame, last_frame
