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
from astropy.table import Table
from astropy.coordinates import Angle
import astropy.units as u

from core.models import Body, CatalogSources
from test_catalog_subs import FITSUnitTest

#Import module to test
from photometrics.catalog_subs import *

class StoreCatalogSourcesTest(FITSUnitTest):

    def test1(self):

        ###
        num_sources_created, num_in_table = store_catalog_sources(self.test_filename)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)
        self.assertEqual(num_sources_created, self.table_num_flags0)
        self.assertEqual(num_in_table, self.table_num_flags0)

        last_catsrc=CatalogSources.objects.last()

        self.assertAlmostEqual(last_catsrc.obs_x, 1067.9471, 4)
        self.assertAlmostEqual(last_catsrc.obs_y, 1973.7445, 4)

    def test_zeropoint_update(self):

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)

        header, table = extract_catalog(self.test_filename)

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint((header, table))

        self.assertLess(header['zeropoint'], 0.0)
        self.assertLess(header['zeropoint_err'], 0.0)

        header, table = update_zeropoint(header, table, avg_zeropoint, std_zeropoint)

        self.assertGreater(header['zeropoint'], 0.0)
        self.assertGreater(header['zeropoint_err'], 0.0)

        first_catsrc=CatalogSources.objects.first()

        self.assertGreater(first_catsrc.obs_mag, 0.0)
        self.assertAlmostEqual(first_catsrc.err_obs_mag, 0.0037, 4)

    def test_duplicate_entries(self):

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)
        self.assertEqual(num_sources_created, self.table_num_flags0)
        self.assertEqual(num_in_table, self.table_num_flags0)

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)
        self.assertEqual(num_sources_created, 0)
        self.assertEqual(num_in_table, self.table_num_flags0)

    def test_bad_catalog(self):

        bad_filename = os.path.join('photometrics','tests','__init__.py')

        num_sources_created, num_in_table = store_catalog_sources(bad_filename)

        self.assertEqual(CatalogSources.objects.count(), 0)
        self.assertEqual(num_sources_created, 0)
        self.assertEqual(num_in_table, 0)

class MakeSEXTFileTest(FITSUnitTest):

    def test_dictionary_creation(self):

        test_dict = {   'number':1,
                        'obs_x':106.118,
                        'obs_y':18.611,
                        'obs_mag':17.1818,
                        'theta':-79.4,
                        'elongation':1.076,
                        'fwhm':3.63,
                        'flags':0,
                        'deltamu':3.0,
                        'flux':7459839.6,
                        'area':10.3126,
                        'ra':86.86805,
                        'dec':-27.57513
                  }

        num_iter = 1

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename)

        sext_params = make_sext_dict(CatalogSources.objects.first(), num_iter)

        self.assertEqual(sext_params['number'], test_dict['number'])
        self.assertAlmostEqual(sext_params['obs_x'], test_dict['obs_x'], 3)
        self.assertAlmostEqual(sext_params['obs_y'], test_dict['obs_y'], 3)
        self.assertAlmostEqual(sext_params['obs_mag'], test_dict['obs_mag'], 4)
        self.assertAlmostEqual(sext_params['theta'], test_dict['theta'], 1)
        self.assertAlmostEqual(sext_params['elongation'], test_dict['elongation'], 3)
        self.assertAlmostEqual(sext_params['fwhm'], test_dict['fwhm'], 2)
        self.assertEqual(sext_params['flags'], test_dict['flags'])
        self.assertAlmostEqual(sext_params['deltamu'], test_dict['deltamu'], 1)
        self.assertAlmostEqual(sext_params['flux'], test_dict['flux'], 1)
        self.assertAlmostEqual(sext_params['area'], test_dict['area'], 4)
        self.assertAlmostEqual(sext_params['ra'], test_dict['ra'], 5)
        self.assertAlmostEqual(sext_params['dec'], test_dict['dec'], 5)

    def test_line_creation(self):

        test_dict = {   'number':1,
                        'obs_x':106.118,
                        'obs_y':18.611,
                        'obs_mag':17.1818,
                        'theta':-79.4,
                        'elongation':1.076,
                        'fwhm':3.63,
                        'flags':0,
                        'deltamu':3.0,
                        'flux':7459839.6,
                        'area':10.3126,
                        'ra':86.86805,
                        'dec':-27.57513
                  }

        test_line = '         1    106.118     18.611  17.1818 -79.4    1.076     3.63   0  3.00   7459839.6   10  86.86805 -27.57513'

        num_iter = 1

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename)

        sext_line = make_sext_file_line(test_dict)

        self.assertEqual(sext_line, test_line)

