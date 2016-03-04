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

class ZeropointUnitTest(TestCase):

    def test_get_cat_ra_dec(self):
        #test getting a single ra, dec, and rmag out of the default PPMXL catalog
        
        cat_table = get_catalog_table(299.590, 35.201, "PPMXL")

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_first_source = cat_table['r2mag'][0]

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

        expected_rmag_first_source = 14.32

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
        self.assertEqual(expected_rmag_first_source, rmag_first_source)

    def test_no_cat(self):
        #test if no catalog input, use default catalog

        cat_table = get_catalog_table(299.590, 35.201)

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_first_source = cat_table['r2mag'][0]

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

        expected_rmag_first_source = 14.32

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
        self.assertEqual(expected_rmag_first_source, rmag_first_source)

    def test_get_cat_ra_dec_not_default(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, "UCAC4")

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_third_source = cat_table['rmag'][2]

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_third_source = 12.642000198364258

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
        self.assertEqual(expected_rmag_third_source, rmag_third_source)

    def test_get_cat_diff_rmag_limit(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, rmag_limit = "<=14.5")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]

        expected_ra_last_source = 299.82885099999999

        expected_dec_last_source = 34.998407

        expected_rmag_last_source = 14.5

        self.assertEqual(expected_ra_last_source, ra_last_source)
        self.assertEqual(expected_dec_last_source, dec_last_source)
        self.assertEqual(expected_rmag_last_source, rmag_last_source)

    def test_get_cat_diff_row_limit(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, set_row_limit = 40)

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_first_source = cat_table['r2mag'][0]

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

        expected_rmag_first_source = 14.32

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
        self.assertEqual(expected_rmag_first_source, rmag_first_source)

    def test_get_cat_diff_width(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, set_width = "30m")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]

        expected_ra_last_source = 299.88443899999999

        expected_dec_last_source = 34.978456999999999

        expected_rmag_last_source = 14.79

        self.assertEqual(expected_ra_last_source, ra_last_source)
        self.assertEqual(expected_dec_last_source, dec_last_source)
        self.assertEqual(expected_rmag_last_source, rmag_last_source)

    def test_more(self):
        self.fail("write more tests")

    def test_vizier_down(self):
        self.fail("write test for no internet")

