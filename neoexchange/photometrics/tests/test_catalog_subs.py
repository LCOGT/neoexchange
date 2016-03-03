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
        #test getting a single ra, dec, and rmag out of the catalog

        catalog = "UCAC4"
        ra = 299.590
        dec = 35.201
        
        result = get_catalog(catalog, ra, dec, default = 'false')

        cat_table = result[0]

        ra_first_source = cat_table.columns.get('_RAJ2000')[0]

        dec_first_source = cat_table.columns.get('_DEJ2000')[0]

        rmag_third_source = cat_table.columns.get('rmag')[2]

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_third_source = 12.642000198364258

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
        self.assertEqual(expected_rmag_third_source, rmag_third_source)

    def test_no_cat(self):
        #test if no catalog input (makes query hang indefinitely) force to ask for the default catalog

        catalog = ""
        ra = 299.590
        dec = 35.201

        result = get_catalog(catalog, ra, dec, default = 'false')

        cat_table = result[0]

        ra_first_source = cat_table.columns.get('_RAJ2000')[0]

        dec_first_source = cat_table.columns.get('_DEJ2000')[0]

        rmag_first_source = cat_table.columns.get('rmag')[2]

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_first_source = 12.642000198364258

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
        self.assertEqual(expected_rmag_first_source, rmag_first_source)

    def test_get_cat_ra_dec_default_equal_true(self):
        #test the default catalog

        catalog = "PPMXL"
        ra = 299.590
        dec = 35.201
        
        result = get_catalog(catalog, ra, dec, default = 'true')

        cat_table = result[0]

        ra_first_source = cat_table.columns.get('_RAJ2000')[0]

        dec_first_source = cat_table.columns.get('_DEJ2000')[0]

        rmag_first_source = cat_table.columns.get('rmag')[2]

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_first_source = 12.642000198364258

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
        self.assertEqual(expected_rmag_first_source, rmag_first_source)
        

    def test_more(self):
        self.fail("write more tests")

    def test_vizier_down(self):
        self.fail("write test for no internet")

