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
        self.table_firstitem = self.test_table[0]
        self.table_lastitem = self.test_table[-1]

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

class FITSReadHeader(FITSUnitTest):

    def test_header(self):

        expected_params = { 'instrument' : self.test_header['INSTRUME'],
                            'filter'     : self.test_header['FILTER'],
                            'framename'  : self.test_header['ORIGNAME'],
                            'exptime'    : self.test_header['EXPTIME'],
                            'obs_date'   : self.test_header['DATE-OBS'],
                            'zeropoint'  : self.test_header['L1ZP'],
                            'zeropoint_err' : self.test_header['L1ZPERR'],
                            'zeropoint_src' : self.test_header['L1ZPSRC'],
                            'fwhm'          : self.test_header['L1FWHM'],
                            'astrometric_fit_rms'    : self.test_header['WCSRDRES'],
                            'astrometric_fit_status' : self.test_header['WCSERR'],
                            'astrometric_fit_nstars' : self.test_header['WCSMATCH'],
                            'astrometric_catalog'    : self.test_header['WCCATTYP'],

                          }

        header, table = open_fits_catalog(self.test_filename)
        frame_header = get_catalog_header(header)

        self.assertEqual(expected_params, frame_header)

@skipIf(True, "Foo")
class FITSReadCatalog(FITSUnitTest):


    def test_first_item(self):

        expected_params = { 'ccd_x' : 106.11764,
                            'ccd_y' :  18.611328,
                            'obs_ra'  :  86.86805182983244,
                            'obs_dec' : -27.575127242664802,
                          }
                          
        items = get_catalog_items(self.test_header, self.table_firstitem)

        self.assertEqual(expected_params, items)
