'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime, timedelta
from unittest import skipIf
from math import sqrt, log10, log
import os

import mock
from django.test import TestCase
from django.forms.models import model_to_dict
from astropy.io import fits

from core.models import Body

#Import module to test
from photometrics.catalog_subs import *

class FITSUnitTest(TestCase):
    def __init__(self, *args, **kwargs):
        super(FITSUnitTest, self).__init__(*args, **kwargs)

    def setUp(self):
        # Read in example FITS source catalog
        self.test_filename = os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits')
        hdulist = fits.open(self.test_filename)
        self.test_header = hdulist[0].header
        self.test_table = hdulist[1].data
        hdulist.close()
        self.table_firstitem = self.test_table[0:1]
        self.table_lastitem = self.test_table[-1:]
        self.table_item_flags24 = self.test_table[2:3]

        self.max_diff = None
        self.precision = 7

        self.flux2mag = 2.5/log(10)

    def compare_list_of_dicts(self, expected_catalog, catalog_items):
        self.assertEqual(len(expected_catalog), len(catalog_items))

        number = 0 
        while number < len(expected_catalog):
            expected_params = expected_catalog[number]
            items = catalog_items[number]
            self.assertEqual(len(expected_params), len(items))

            for key in expected_params:
                self.assertAlmostEqual(expected_params[key], items[key], places=self.precision, msg="Failure verifying " + key)
            number += 1
    
class OpenFITSCatalog(FITSUnitTest):


    def test_catalog_does_not_exist(self):
        expected_hdr = {}
        expected_tbl = {}

        hdr, tbl = open_fits_catalog('wibble')

        self.assertEqual(expected_hdr, hdr)
        self.assertEqual(expected_tbl, tbl)

    def test_catalog_is_not_FITS(self):
        expected_hdr = {}
        expected_tbl = {}

        hdr, tbl = open_fits_catalog(os.path.join('photometrics', 'tests', '__init__.py'))

        self.assertEqual(expected_hdr, hdr)
        self.assertEqual(expected_tbl, tbl)

    def test_catalog_read_length(self):
        expected_hdr_len = len(self.test_header)
        expected_tbl_len = len(self.test_table)

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))

    def test_catalog_read_hdr_keyword(self):
        expected_hdr_value = self.test_header['INSTRUME']

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])

    def test_catalog_read_tbl_column(self):
        expected_tbl_value = 'X_IMAGE'
        expected_tbl_units = 'pixel'

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_tbl_value, tbl.columns[1].name)
        self.assertEqual(expected_tbl_units, tbl.columns[1].unit)

    def test_catalog_read_xy(self):
        # X,Y CCD Co-ordinates of the last detection
        expected_x = 1067.9471
        expected_y = 1973.7445

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertAlmostEqual(expected_x, tbl[-1]['X_IMAGE'], 4)
        self.assertAlmostEqual(expected_y, tbl[-1]['Y_IMAGE'], 4)

class Test_Convert_Values(FITSUnitTest):

    def test_dateobs_conversion(self):

        expected_value = datetime(2016, 2, 22, 19, 16, 42, 664000)

        value = convert_value('obs_date' , self.test_header['DATE-OBS'])

        self.assertEqual(expected_value, value)

    def test_dateobs_no_frac_seconds(self):

        expected_value = datetime(2016, 2, 22, 19, 16, 42)

        value = convert_value('obs_date' , '2016-02-22T19:16:42')

        self.assertEqual(expected_value, value)

    def test_bad_astrometric_rms(self):

        expected_value = None

        value = convert_value('astrometric_fit_rms' , '-99/-99 ')

        self.assertEqual(expected_value, value)

    def test_avg_astrometric_rms(self):

        expected_value = 0.15

        value = convert_value('astrometric_fit_rms' , '0.16/0.14 ')

        self.assertAlmostEqual(expected_value, value, 4)

    def test_astrometric_catalog(self):

        expected_value = 'UCAC3'

        value = convert_value('astrometric_catalog' , 'UCAC3@CDS ')

        self.assertEqual(expected_value, value)

    def test_no_conversion(self):

        expected_value = 100.0

        value = convert_value('exptime' , self.test_header['EXPTIME'])

        self.assertEqual(expected_value, value)

    def test_flux_to_mag(self):

        expected_value = -7.5

        value = convert_value('obs_mag' , 1000.0)

        self.assertEqual(expected_value, value)

    def test_negflux_to_mag(self):

        expected_value = -1.5

        value = convert_value('obs_mag' , -1.5)

        self.assertEqual(expected_value, value)

    def test_flux_to_magerr(self):

        expected_value = self.flux2mag * (10.0/360.0)

        value = convert_value('obs_mag_err' , (10.0, 360.0))

        self.assertEqual(expected_value, value)

class FITSReadHeader(FITSUnitTest):

    def test_header(self):

        obs_date = datetime.strptime(self.test_header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S.%f')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : self.test_header['INSTRUME'],
                            'filter'     : self.test_header['FILTER'],
                            'framename'  : self.test_header['ORIGNAME'],
                            'exptime'    : self.test_header['EXPTIME'],
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=self.test_header['EXPTIME'] / 2.0),
                            'zeropoint'     : self.test_header['L1ZP'],
                            'zeropoint_err' : self.test_header['L1ZPERR'],
                            'zeropoint_src' : self.test_header['L1ZPSRC'],
                            'fwhm'          : self.test_header['L1FWHM'],
                            'astrometric_fit_rms'    : None,
                            'astrometric_fit_status' : self.test_header['WCSERR'],
                            'astrometric_fit_nstars' : self.test_header['WCSMATCH'],
                            'astrometric_catalog'    : 'UCAC3',

                          }

        header, table = open_fits_catalog(self.test_filename)
        frame_header = get_catalog_header(header)

        self.assertEqual(expected_params, frame_header)

class FITSReadCatalog(FITSUnitTest):


    def test_first_item(self):

        expected_catalog = [{ 'ccd_x' : 106.11763763,
                              'ccd_y' :  18.61132812,
                              'major_axis'  : 1.87925231,
                              'minor_axis'  : 1.74675643,
                              'ccd_pa'      : -79.38792419,
                              'obs_ra'  :  86.868051829832439,
                              'obs_dec' : -27.575127242664802,
                              'obs_ra_err'  : 7.464116913258858e-06,
                              'obs_dec_err' : 7.516842315248245e-06,
                              'obs_mag'      : -2.5*log10(11228.246),
                              'obs_mag_err'  : 0.037939535221954708,
                              'obs_sky_bkgd' : 746.41577148,
                              'flags' : 0,
                            },
                            ]
                          
        catalog_items = get_catalog_items(self.test_header, self.table_firstitem)

        self.compare_list_of_dicts(expected_catalog, catalog_items)

    def test_last_item(self):

        expected_catalog = [{ 'ccd_x' : 1067.94714355,
                              'ccd_y' :  1973.74450684,
                              'major_axis'  : 2.7380364,
                              'minor_axis'  : 2.454973,
                              'ccd_pa'      : 85.39698792,
                              'obs_ra'  :  86.727294383019555,
                              'obs_dec' : -27.82876912480173,
                              'obs_ra_err'  : 1.5709768391021522e-06,
                              'obs_dec_err' : 1.733559011455713e-06,
                              'obs_mag' : -2.5*log10(215428.83),
                              'obs_mag_err'  : self.flux2mag * self.table_lastitem['FLUXERR_AUTO']/self.table_lastitem['FLUX_AUTO'],
                              'obs_sky_bkgd' : 744.8538208,
                              'flags' : 0,
                            },
                            ]
                          
        catalog_items = get_catalog_items(self.test_header, self.table_lastitem)

        self.compare_list_of_dicts(expected_catalog, catalog_items)

    def test_reject_item_flags24(self):

        expected_catalog = []

        catalog_items = get_catalog_items(self.test_header, self.table_item_flags24)

        self.assertEqual(expected_catalog, catalog_items)

    def test_accept_item_flags24(self):

        expected_catalog = [{ 'ccd_x' :  234.52952576,
                              'ccd_y' :    8.05962372,
                              'major_axis'  : 2.38448,
                              'minor_axis'  : 2.3142395,
                              'ccd_pa'      : 54.71178436,
                              'obs_ra'  :  86.84926113,
                              'obs_dec' : -27.57377512,
                              'obs_ra_err'  : 3.192540788457258e-06,
                              'obs_dec_err' : 2.9221911507086037e-06,
                              'obs_mag' : -2.5*log10(67883.703125),
                              'obs_mag_err'  : self.flux2mag * self.table_item_flags24['FLUXERR_AUTO']/self.table_item_flags24['FLUX_AUTO'],
                              'obs_sky_bkgd' :741.20977783,
                              'flags' : 24,
                            },
                            ]

        catalog_items = get_catalog_items(self.test_header, self.table_item_flags24, flag_filter=24)

        self.compare_list_of_dicts(expected_catalog, catalog_items)

    def test_first_item_with_bad_zeropoint(self):

        expected_catalog = [{ 'ccd_x' : 106.11763763,
                              'ccd_y' :  18.61132812,
                              'major_axis'  : 1.87925231,
                              'minor_axis'  : 1.74675643,
                              'ccd_pa'      : -79.38792419,
                              'obs_ra'  :  86.868051829832439,
                              'obs_dec' : -27.575127242664802,
                              'obs_ra_err'  : 7.464116913258858e-06,
                              'obs_dec_err' : 7.516842315248245e-06,
                              'obs_mag'      : -2.5*log10(11228.246),
                              'obs_mag_err'  : 0.037939535221954708,
                              'obs_sky_bkgd' : 746.41577148,
                              'flags' : 0,
                            },
                            ]
        header_items = {'zeropoint' : -99}
        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.compare_list_of_dicts(expected_catalog, catalog_items)

    def test_first_item_with_good_zeropoint(self):

        header_items = {'zeropoint' : 23.0}
        expected_catalog = [{ 'ccd_x' : 106.11763763,
                              'ccd_y' :  18.61132812,
                              'major_axis'  : 1.87925231,
                              'minor_axis'  : 1.74675643,
                              'ccd_pa'      : -79.38792419,
                              'obs_ra'  :  86.868051829832439,
                              'obs_dec' : -27.575127242664802,
                              'obs_ra_err'  : 7.464116913258858e-06,
                              'obs_dec_err' : 7.516842315248245e-06,
                              'obs_mag'      : -2.5*log10(11228.246) + header_items['zeropoint'],
                              'obs_mag_err'  : 0.037939535221954708,
                              'obs_sky_bkgd' : 746.41577148,
                              'flags' : 0,
                            },
                            ]
        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.compare_list_of_dicts(expected_catalog, catalog_items)

    def test_first_item_with_no_zeropoint(self):

        header_items = {'zerowibble' : -99}
        expected_catalog = [{ 'ccd_x' : 106.11763763,
                              'ccd_y' :  18.61132812,
                              'major_axis'  : 1.87925231,
                              'minor_axis'  : 1.74675643,
                              'ccd_pa'      : -79.38792419,
                              'obs_ra'  :  86.868051829832439,
                              'obs_dec' : -27.575127242664802,
                              'obs_ra_err'  : 7.464116913258858e-06,
                              'obs_dec_err' : 7.516842315248245e-06,
                              'obs_mag'      : -2.5*log10(11228.246),
                              'obs_mag_err'  : 0.037939535221954708,
                              'obs_sky_bkgd' : 746.41577148,
                              'flags' : 0,
                            },
                            ]
        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.compare_list_of_dicts(expected_catalog, catalog_items)
