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

from core.models import Body

#Import module to test
from photometrics.catalog_subs import *

class ZeropointUnitTest(TestCase):

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_ra_dec(self, mock_vizier):
#    def test_get_cat_ra_dec(self):
        #test getting a single ra, dec, and rmag out of the default UCAC4 catalog
#        test_data = __file__.replace('.py', '_UCAC4.dat') #test_data_file captured with cat_table.write('test_catalog_subs_UCAC4.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
#        test_query_result = []
#        test_query_result.append(Table.read(test_data, format='csv'))
#        mock_vizier().query_region().return_value=test_query_result
#        print mock_vizier().query_region().return_value#[0]['_RAJ2000'][0]
#        print len(mock_vizier().query_region().return_value)
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')
#        print mock_vizier().query_region().__getitem__.return_value['_RAJ2000'][0]
#        print len(mock_vizier().query_region().__getitem__.return_value)

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_third_source = 12.642

        expected_len_cat_table = 1607

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", "UCAC4")
#        print cat_table['_RAJ2000'][0], cat_table['_DEJ2000'][0]#, cat_table['rmag'][2]
#        print cat_name
#        print cat_table

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_third_source = cat_table['rmag'][2]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 8)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 8)
        self.assertAlmostEqual(expected_rmag_third_source, rmag_third_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_no_cat(self, mock_vizier):
#    def test_no_cat(self):
        #test if no catalog input, use default catalog
#        test_data = __file__.replace('.py', '_UCAC4.dat') #test_data_file captured with cat_table.write('test_catalog_subs_UCAC4.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_third_source = 12.642

        expected_len_cat_table = 1607

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m")

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_third_source = cat_table['rmag'][2]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 8)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 8)
        self.assertAlmostEqual(expected_rmag_third_source, rmag_third_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_ra_dec_not_default(self, mock_vizier):
#    def test_get_cat_ra_dec_not_default(self):
        #test a catalog other than the default
#        test_data = __file__.replace('.py', '_PPMXL.dat') #test_data_file captured with cat_table.write('test_catalog_subs_PPMXL.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

        expected_rmag_first_source = 14.32

        expected_len_cat_table = 737

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", "PPMXL")

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_first_source = cat_table['r2mag'][0]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 8)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 8)
        self.assertAlmostEqual(expected_rmag_first_source, rmag_first_source, 3)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_diff_rmag_limit(self, mock_vizier):
#    def test_get_cat_diff_rmag_limit(self):
        #test a catalog with an r mag limit
#        test_data = __file__.replace('.py', '_PPMXL_diff_rmag_limit.dat') #test_data_file captured with cat_table.write('test_catalog_subs_PPMXL_diff_rmag_limit.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_last_source = 299.82885099999999

        expected_dec_last_source = 34.998407

        expected_rmag_last_source = 14.5

        expected_len_cat_table = 443

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", rmag_limit = "<=14.5", cat_name = "PPMXL")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 6)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 1)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_diff_row_limit(self, mock_vizier):
#    def test_get_cat_diff_row_limit(self):
        #test a catalog with a different row limit
#        test_data = __file__.replace('.py', '_PPMXL_diff_row_limit.dat') #test_data_file captured with cat_table.write('test_catalog_subs_PPMXL_diff_row_limit.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

        expected_rmag_first_source = 14.32

        expected_len_cat_table = 737

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", set_row_limit = 40, cat_name = "PPMXL")

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

        rmag_first_source = cat_table['r2mag'][0]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 8)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 8)
        self.assertAlmostEqual(expected_rmag_first_source, rmag_first_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_diff_width(self, mock_vizier):
#    def test_get_cat_diff_width(self):
        #test a catalog with a different width and height
#        test_data = __file__.replace('.py', '_UCAC4_diff_width_height.dat') #test_data_file captured with cat_table.write('test_catalog_subs_UCAC4_diff_width_height.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_last_source = 299.74110200000001

        expected_dec_last_source = 35.313324999999999

        expected_rmag_3rdlast_source = 14.81

        expected_len_cat_table = 408

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "15m", "15m")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

        rmag_3rdlast_source = cat_table['rmag'][-3]

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_3rdlast_source, rmag_3rdlast_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_ra_dec_above_row_limit(self, mock_vizier):
#    def test_get_cat_ra_dec_above_row_limit(self):
        #test a catalog with a different width and height
#        test_data = __file__.replace('.py', '_PPMXL_above_row_limit.dat') #test_data_file captured with cat_table.write('test_catalog_subs_PPMXL_above_row_limit.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_last_source = 267.35990700000002

        expected_dec_last_source = -28.212005999999999

        expected_rmag_last_source = 14.54

        expected_len_cat_table = 11838

        cat_table, cat_name = get_vizier_catalog_table(266.4168, -29.0078, "100m", "100m", "PPMXL")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_ra_dec_empty_list_PPMXL(self, mock_vizier):
#    def test_get_cat_ra_dec_empty_list_PPMXL(self):
        #test a catalog with a different width and height
#        test_data = __file__.replace('.py', '_UCAC4_empty.dat') #test_data_file captured with cat_table.write('test_catalog_subs_UCAC4_empty.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_last_source = 0.0

        expected_dec_last_source = 0.0

        expected_rmag_last_source = 0.0

        expected_len_cat_table = 100000

        cat_table, cat_name = get_vizier_catalog_table(298.590, 35.201, "0.5m", "0.5m", "PPMXL")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

        rmag_last_source = cat_table['rmag'][-1] #will replace cat_name with UCAC4 after failing with PPMXL

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    @mock.patch('photometrics.catalog_subs.Vizier')
    def test_get_cat_ra_dec_empty_list_UCAC4(self, mock_vizier):
#    def test_get_cat_ra_dec_empty_list_UCAC4(self):
        #test a catalog with a different width and height
#        test_data = __file__.replace('.py', '_PPMXL_empty.dat') #test_data_file captured with cat_table.write('test_catalog_subs_PPMXL_empty.dat', format='csv')
        test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')

        expected_ra_last_source = 0.0

        expected_dec_last_source = 0.0

        expected_rmag_last_source = 0.0

        expected_len_cat_table = 100000

        cat_table, cat_name = get_vizier_catalog_table(298.590, 35.201, "0.5m", "0.5m")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1] #will replace cat_name with PPMXL after failing with UCAC4

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    def test_cross_match_UCAC4_longerThan_testFITS(self):
        #test with cat 1 as longer UCAC4 table values and cat 2 as shorter test FITS table values

        expected_cross_match_table_data = [(299.303973, 299.304084, 1.11e-04, 35.20152, 35.201634, 1.1400e-04, 0.0, 13.8500003815, 0.05, 13.8500003815),
                                           (299.828851, 299.828851, 0.0, 34.99841, 34.998407, 3.0000e-06, 0.0, 14.5, 0.01, 14.5),
                                           (299.291455, 299.291366, 8.9000e-5, 35.242368, 35.242404, 3.6000e-05, 0.0, 14.3199996948, 0.03, 14.3199996948),
                                           (299.510127, 299.510143, 1.6000e-05, 34.960327, 34.960303, 2.4000e-05, 15.5469999313, 14.4499998093, 0.05, 1.097000),
                                           (299.308515, 299.308579, 6.4000e-05, 35.165529, 35.165495, 3.4000e-05, 15.0059995651, 14.8900003433, 0.02, 0.115999),
                                           (299.709162, 299.709139, 2.3000e-05, 35.218112, 35.218109, 3.0000e-06, 13.3520002365, 12.7700004578, 0.0, 0.582000),
                                           (299.860889, 299.860871, 1.8000e-05, 35.381485, 35.381474, 1.1000e-05, 14.9130001068, 14.0799999237, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 3, 0),
                            (299.304084, 35.201634, 13.8500003815, 5, 0),
                            (299.480004, 34.965488, 14.3800001144, 3, 0),
                            (299.308579, 35.165495, 14.8900003433, 2, 0),
                            (299.828851, 34.998407, 14.5, 1, 0),
                            (299.510143, 34.960303, 14.4499998093, 5, 0),
                            (299.709139, 35.218109, 12.7700004578, 0, 0),
                            (299.860871, 35.381474, 14.0799999237, 0, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'rmag', 'e_rmag', 'flags'), dtype=('f8', 'f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2)

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][4], cross_match_table['RA Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][5], cross_match_table['RA Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][6], cross_match_table['RA Cat 1'][6], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][4], cross_match_table['RA Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][5], cross_match_table['RA Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][6], cross_match_table['RA Cat 2'][6], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][4], cross_match_table['RA diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][5], cross_match_table['RA diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][6], cross_match_table['RA diff'][6], 9)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][4], cross_match_table['Dec Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][5], cross_match_table['Dec Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][6], cross_match_table['Dec Cat 1'][6], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][4], cross_match_table['Dec Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][5], cross_match_table['Dec Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][6], cross_match_table['Dec Cat 2'][6], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][4], cross_match_table['Dec diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][5], cross_match_table['Dec diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][6], cross_match_table['Dec diff'][6], 9)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][4], cross_match_table['r mag Cat 1'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][5], cross_match_table['r mag Cat 1'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][6], cross_match_table['r mag Cat 1'][6], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][4], cross_match_table['r mag Cat 2'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][5], cross_match_table['r mag Cat 2'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][6], cross_match_table['r mag Cat 2'][6], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag err'][0], cross_match_table['r mag err'][0], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][1], cross_match_table['r mag err'][1], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][2], cross_match_table['r mag err'][2], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][3], cross_match_table['r mag err'][3], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][4], cross_match_table['r mag err'][4], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][5], cross_match_table['r mag err'][5], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][6], cross_match_table['r mag err'][6], 2)

        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][0], cross_match_table['r mag diff'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][1], cross_match_table['r mag diff'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][2], cross_match_table['r mag diff'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][3], cross_match_table['r mag diff'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][4], cross_match_table['r mag diff'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][5], cross_match_table['r mag diff'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][6], cross_match_table['r mag diff'][6], 6)

    def test_cross_match_UCAC4_shorterThan_testFITS(self):
        #test with cat 1 as longer test FITS table values and cat 2 as shorter UCAC4 table values to test cat reordering
        #also tests filtering of poor cross matches

        expected_cross_match_table_data = [(299.291366, 299.291455, 8.9000e-5, 35.242404, 35.242368, 3.6000e-05, 14.3199996948, 0.0, 0.03, 14.3199996948),
                                           (299.304084, 299.303973, 1.11e-04, 35.201634, 35.20152, 1.1400e-04, 13.8500003815, 0.0, 0.05, 13.8500003815),
                                           (299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.03, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.02, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5, 0.0, 0.01, 14.5),
                                           (299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.05, 1.097000),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.479984, 34.965502, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.884478, 34.978454, 0.0, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 3, 0),
                            (299.304084, 35.201634, 13.8500003815, 5, 0),
                            (299.480004, 34.965488, 14.3800001144, 3, 0),
                            (299.308579, 35.165495, 14.8900003433, 2, 0),
                            (299.828851, 34.998407, 14.5, 1, 0),
                            (299.510143, 34.960303, 14.4499998093, 5, 0),
                            (299.709139, 35.218109, 12.7700004578, 0, 0),
                            (299.860871, 35.381474, 14.0799999237, 0, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'rmag', 'e_rmag', 'flags'), dtype=('f8', 'f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2)

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][4], cross_match_table['RA Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][5], cross_match_table['RA Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][6], cross_match_table['RA Cat 1'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][7], cross_match_table['RA Cat 1'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][4], cross_match_table['RA Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][5], cross_match_table['RA Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][6], cross_match_table['RA Cat 2'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][7], cross_match_table['RA Cat 2'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][4], cross_match_table['RA diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][5], cross_match_table['RA diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][6], cross_match_table['RA diff'][6], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][7], cross_match_table['RA diff'][7], 9)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][4], cross_match_table['Dec Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][5], cross_match_table['Dec Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][6], cross_match_table['Dec Cat 1'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][7], cross_match_table['Dec Cat 1'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][4], cross_match_table['Dec Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][5], cross_match_table['Dec Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][6], cross_match_table['Dec Cat 2'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][7], cross_match_table['Dec Cat 2'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][4], cross_match_table['Dec diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][5], cross_match_table['Dec diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][6], cross_match_table['Dec diff'][6], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][7], cross_match_table['Dec diff'][7], 9)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][4], cross_match_table['r mag Cat 1'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][5], cross_match_table['r mag Cat 1'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][6], cross_match_table['r mag Cat 1'][6], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][7], cross_match_table['r mag Cat 1'][7], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][4], cross_match_table['r mag Cat 2'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][5], cross_match_table['r mag Cat 2'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][6], cross_match_table['r mag Cat 2'][6], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][7], cross_match_table['r mag Cat 2'][7], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag err'][0], cross_match_table['r mag err'][0], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][1], cross_match_table['r mag err'][1], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][2], cross_match_table['r mag err'][2], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][3], cross_match_table['r mag err'][3], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][4], cross_match_table['r mag err'][4], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][5], cross_match_table['r mag err'][5], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][6], cross_match_table['r mag err'][6], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][7], cross_match_table['r mag err'][7], 2)

        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][0], cross_match_table['r mag diff'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][1], cross_match_table['r mag diff'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][2], cross_match_table['r mag diff'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][3], cross_match_table['r mag diff'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][4], cross_match_table['r mag diff'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][5], cross_match_table['r mag diff'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][6], cross_match_table['r mag diff'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][7], cross_match_table['r mag diff'][7], 6)

    def test_cross_match_PPMXL_shorterThan_testFITS(self):
        #test with cat 1 as longer test FITS table values and cat 2 as shorter PPMXL table values to test cat reordering
        #also tests filtering of poor cross matches

        expected_cross_match_table_data = [(299.291366, 299.291455, 8.9000e-5, 35.242404, 35.242368, 3.6000e-05, 14.3199996948, 0.0, 0.0, 14.3199996948),
                                           (299.304084, 299.303973, 1.11e-04, 35.201634, 35.20152, 1.1400e-04, 13.8500003815, 0.0, 0.0, 13.8500003815),
                                           (299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.0, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.0, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5,0.0,  0.0, 14.5),
                                           (299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.0, 1.097000),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.479984, 34.965502, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.884478, 34.978454, 0.0, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 0),
                            (299.304084, 35.201634, 13.8500003815, 0),
                            (299.480004, 34.965488, 14.3800001144, 0),
                            (299.308579, 35.165495, 14.8900003433, 0),
                            (299.828851, 34.998407, 14.5, 0),
                            (299.510143, 34.960303, 14.4499998093, 0),
                            (299.709139, 35.218109, 12.7700004578, 0),
                            (299.860871, 35.381474, 14.0799999237, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'r2mag', 'fl'), dtype=('f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2, "PPMXL")

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][4], cross_match_table['RA Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][5], cross_match_table['RA Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][6], cross_match_table['RA Cat 1'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][7], cross_match_table['RA Cat 1'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][4], cross_match_table['RA Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][5], cross_match_table['RA Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][6], cross_match_table['RA Cat 2'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][7], cross_match_table['RA Cat 2'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][4], cross_match_table['RA diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][5], cross_match_table['RA diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][6], cross_match_table['RA diff'][6], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][7], cross_match_table['RA diff'][7], 9)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][4], cross_match_table['Dec Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][5], cross_match_table['Dec Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][6], cross_match_table['Dec Cat 1'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][7], cross_match_table['Dec Cat 1'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][4], cross_match_table['Dec Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][5], cross_match_table['Dec Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][6], cross_match_table['Dec Cat 2'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][7], cross_match_table['Dec Cat 2'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][4], cross_match_table['Dec diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][5], cross_match_table['Dec diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][6], cross_match_table['Dec diff'][6], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][7], cross_match_table['Dec diff'][7], 9)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][4], cross_match_table['r mag Cat 1'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][5], cross_match_table['r mag Cat 1'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][6], cross_match_table['r mag Cat 1'][6], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][7], cross_match_table['r mag Cat 1'][7], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][4], cross_match_table['r mag Cat 2'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][5], cross_match_table['r mag Cat 2'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][6], cross_match_table['r mag Cat 2'][6], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][7], cross_match_table['r mag Cat 2'][7], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag err'][0], cross_match_table['r mag err'][0], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][1], cross_match_table['r mag err'][1], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][2], cross_match_table['r mag err'][2], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][3], cross_match_table['r mag err'][3], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][4], cross_match_table['r mag err'][4], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][5], cross_match_table['r mag err'][5], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][6], cross_match_table['r mag err'][6], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][7], cross_match_table['r mag err'][7], 2)

        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][0], cross_match_table['r mag diff'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][1], cross_match_table['r mag diff'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][2], cross_match_table['r mag diff'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][3], cross_match_table['r mag diff'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][4], cross_match_table['r mag diff'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][5], cross_match_table['r mag diff'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][6], cross_match_table['r mag diff'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][7], cross_match_table['r mag diff'][7], 6)

    def test_cross_match_UCAC_shorterThan_testFITS(self):
        #test with cat 1 as longer test FITS table values and cat 2 as shorter UCAC table values to test cat reordering NOTE: UCAC not UCAC4 tested here...need to add a test for something other than a variation of PPMXL or UCAC.
        #also tests filtering of poor cross matches

        expected_cross_match_table_data = [(299.291366, 299.291455, 8.9000e-5, 35.242404, 35.242368, 3.6000e-05, 14.3199996948, 0.0, 0.03, 14.3199996948),
                                           (299.304084, 299.303973, 1.11e-04, 35.201634, 35.20152, 1.1400e-04, 13.8500003815, 0.0, 0.05, 13.8500003815),
                                           (299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.03, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.02, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5, 0.0, 0.01, 14.5),
                                           (299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.05, 1.097000),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.479984, 34.965502, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.884478, 34.978454, 0.0, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 3, 0),
                            (299.304084, 35.201634, 13.8500003815, 5, 0),
                            (299.480004, 34.965488, 14.3800001144, 3, 0),
                            (299.308579, 35.165495, 14.8900003433, 2, 0),
                            (299.828851, 34.998407, 14.5, 1, 0),
                            (299.510143, 34.960303, 14.4499998093, 5, 0),
                            (299.709139, 35.218109, 12.7700004578, 0, 0),
                            (299.860871, 35.381474, 14.0799999237, 0, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'rmag', 'e_rmag', 'flags'), dtype=('f8', 'f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2, "UCAC")

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][4], cross_match_table['RA Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][5], cross_match_table['RA Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][6], cross_match_table['RA Cat 1'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][7], cross_match_table['RA Cat 1'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][4], cross_match_table['RA Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][5], cross_match_table['RA Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][6], cross_match_table['RA Cat 2'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][7], cross_match_table['RA Cat 2'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][4], cross_match_table['RA diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][5], cross_match_table['RA diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][6], cross_match_table['RA diff'][6], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][7], cross_match_table['RA diff'][7], 9)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][4], cross_match_table['Dec Cat 1'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][5], cross_match_table['Dec Cat 1'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][6], cross_match_table['Dec Cat 1'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][7], cross_match_table['Dec Cat 1'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][4], cross_match_table['Dec Cat 2'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][5], cross_match_table['Dec Cat 2'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][6], cross_match_table['Dec Cat 2'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][7], cross_match_table['Dec Cat 2'][7], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][4], cross_match_table['Dec diff'][4], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][5], cross_match_table['Dec diff'][5], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][6], cross_match_table['Dec diff'][6], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][7], cross_match_table['Dec diff'][7], 9)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][4], cross_match_table['r mag Cat 1'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][5], cross_match_table['r mag Cat 1'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][6], cross_match_table['r mag Cat 1'][6], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][7], cross_match_table['r mag Cat 1'][7], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][4], cross_match_table['r mag Cat 2'][4], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][5], cross_match_table['r mag Cat 2'][5], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][6], cross_match_table['r mag Cat 2'][6], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][7], cross_match_table['r mag Cat 2'][7], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag err'][0], cross_match_table['r mag err'][0], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][1], cross_match_table['r mag err'][1], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][2], cross_match_table['r mag err'][2], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][3], cross_match_table['r mag err'][3], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][4], cross_match_table['r mag err'][4], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][5], cross_match_table['r mag err'][5], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][6], cross_match_table['r mag err'][6], 2)
        self.assertAlmostEqual(expected_cross_match_table['r mag err'][7], cross_match_table['r mag err'][7], 2)

        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][0], cross_match_table['r mag diff'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][1], cross_match_table['r mag diff'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][2], cross_match_table['r mag diff'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][3], cross_match_table['r mag diff'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][4], cross_match_table['r mag diff'][4], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][5], cross_match_table['r mag diff'][5], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][6], cross_match_table['r mag diff'][6], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][7], cross_match_table['r mag diff'][7], 6)

    def test_cross_match_filtering(self):
        #test filtering of poor catalog cross matches

        expected_cross_match_table_data = [(299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.0, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.0, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5, 0.0, 0.0, 14.5),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.479984, 34.965502, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.884478, 34.978454, 0.0, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0),
                            (299.315295, 35.069564, 0.0, 0),
                            (299.321592, 35.351089, 14.0190000534, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 1),
                            (299.304084, 35.201634, 13.8500003815, 1),
                            (299.480004, 34.965488, 14.3800001144, 0),
                            (299.308579, 35.165495, 14.8900003433, 0),
                            (299.828851, 34.998407, 14.5, 0),
                            (299.510143, 34.960303, 14.4499998093, 1),
                            (299.709139, 35.218109, 12.7700004578, 0),
                            (299.860871, 35.381474, 14.0799999237, 0),
                            (299.31235, 35.07259, 14.8500003815, 0),
                            (299.362172, 35.351208, 14.2600002289, 1)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'r2mag', 'fl'), dtype=('f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2, "PPMXL")

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 1'][4], cross_match_table['RA Cat 1'][4], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['RA Cat 2'][4], cross_match_table['RA Cat 2'][4], 6)

        self.assertAlmostEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['RA diff'][4], cross_match_table['RA diff'][4], 9)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 1'][4], cross_match_table['Dec Cat 1'][4], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['Dec Cat 2'][4], cross_match_table['Dec Cat 2'][4], 6)

        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3], 9)
        self.assertAlmostEqual(expected_cross_match_table['Dec diff'][4], cross_match_table['Dec diff'][4], 9)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 1'][4], cross_match_table['r mag Cat 1'][4], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3], 10)
        self.assertAlmostEqual(expected_cross_match_table['r mag Cat 2'][4], cross_match_table['r mag Cat 2'][4], 10)

        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][0], cross_match_table['r mag diff'][0], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][1], cross_match_table['r mag diff'][1], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][2], cross_match_table['r mag diff'][2], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][3], cross_match_table['r mag diff'][3], 6)
        self.assertAlmostEqual(expected_cross_match_table['r mag diff'][4], cross_match_table['r mag diff'][4], 6)

    def test_get_zeropoint(self):
        #test zeropoint calculation

        expected_avg_zeropoint = 0.7785

        expected_std_zeropoint = 0.077074639149

        expected_count = 2

        expected_num_in_calc = 2

        cross_match_table_data = [(299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.05, 1.097000),
                                  (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.03, 0.833000),
                                  (299.789005, 299.788977, 2.8000e-05, 34.983303, 34.98333, 2.7000e-05, 14.5200004578, 13.795999527, 0.03, 0.724000)]

        cross_match_table = Table(rows=cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 4)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 4)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)

    def test_get_zeropoint_larger_dataset(self):
        #test zeropoint calculation

        expected_avg_zeropoint = 0.095078815789473692

        expected_std_zeropoint = 0.0212772458577

        expected_count = 4

        expected_num_in_calc = 4

        cross_match_table_data = [(299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.03, 0.115999),
                                  (299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.05, 1.097000),
                                  (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.03, 0.582000),
                                  (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.02, 0.833000),
                                  (299.480459, 299.480473, 1.4000e-05, 35.211664, 35.211664, 0.0, 14.1800003052, 14.2910003662, 0.01, 0.111000),
                                  (299.497849, 299.497893, 4.4000e-05, 35.414674, 35.4147, 2.6000e-05, 13.5900001526, 13.6560001373, 0.05, 0.066000),
                                  (299.786581, 299.786549, 3.2000e-05, 35.349776, 35.349781, 5.0000e-06, 14.1000003815, 14.1780004501, 0.0, 0.078000),
                                  (299.759237, 299.75918, 5.7000e-05, 35.256782, 35.256786, 4.0000e-06, 13.0900001526, 14.3479995728, 0.0, 1.258000),
                                  (299.789005, 299.788977, 2.8000e-05, 34.983303, 34.98333, 2.7000e-05, 14.5200004578, 13.795999527, 0.06, 0.724000),
                                  (299.999005, 299.998977, 2.8000e-05, 34.223303, 34.22333, 2.7000e-05, 14.5200004578, 0.0, 0.08, 14.5200004578)]

        cross_match_table = Table(rows=cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 4)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 4)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)

    def test_get_zeropoint_inconclusive_value(self):
        #test zeropoint calculation

        expected_avg_zeropoint = 4.47955

        expected_std_zeropoint = 0.716794144089

        expected_count = 0

        expected_num_in_calc = 2

        cross_match_table_data = [(209.146558, 209.146514825, 4.3175e-05, -17.450514, -17.4505721629, 5.8163e-05, 13.9300003052, 12.8761520386, 0.01, 1.0538),
                                  (209.107363, 209.107484127, 0.0001, -17.524826, -17.5249530573, 0.0001, 12.8000001907, 17.7864189148, 0.01, 4.9864),
                                  (209.319028, 209.319387053, 0.0004, -17.577961, -17.5778475751, 0.0001, 13.4300003052, 17.4026889801, 0.01, 3.9727)]

        cross_match_table = Table(rows=cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 4)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 4)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)

    def test_call_cross_match_and_zeropoint_with_PPMXL(self):

        expected_avg_zeropoint = 27.389040152231853

        expected_std_zeropoint = 0.08511626631873609

        expected_count = 12

        expected_num_in_calc = 12

        expected_len_cross_match_table = 21

        catfile = os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint(catfile, cat_name="PPMXL")

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 8)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 8)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_cross_match_and_zeropoint_with_UCAC4(self):

        expected_avg_zeropoint = 27.3076036537

        expected_std_zeropoint = 0.0818534024596

        expected_count = 26

        expected_num_in_calc = 26

        expected_len_cross_match_table = 56

        catfile = os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint(catfile)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 8)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 8)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_with_diff_test_cat_force_to_UCAC4(self):
        #test the call with a different FITS catalog file that will return an empty vizier query table for the PPMXL catalog and a zeropoint already in the header, so that the computed avg_zeropoint is the difference between the FITS catalog ZP (in the header) and the Vizier catalog computed ZP

        expected_avg_zeropoint = 0.276944994033

        expected_std_zeropoint = 0.0857935965306

        expected_count = 9

        expected_num_in_calc = 9

        expected_len_cross_match_table = 19

        catfile = os.path.join(os.getenv('HOME'), 'Asteroids', 'CatalogFiles', 'cpt1m010-kb70-20160210-0365-e90_cat.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint(catfile, "PPMXL")

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 8)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 8)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_with_diff_test_cat_UCAC4(self):
        #test the call with a different FITS catalog file and the default UCAC4 catalog

        expected_avg_zeropoint = 27.2969494845

        expected_std_zeropoint = 0.0512114572605

        expected_count = 8

        expected_num_in_calc = 8

        expected_len_cross_match_table = 16

        catfile = os.path.join(os.getenv('HOME'), 'Asteroids', 'CatalogFiles', 'elp1m008-fl05-20160217-0218-e90_cat.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint(catfile)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 8)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 8)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_with_diff_test_cat_PPMXL(self):
        #test the call with a different FITS catalog file and the default UCAC4 catalog

        expected_avg_zeropoint = 27.0946609497

        expected_std_zeropoint = 0.0643614354292

        expected_count = 5

        expected_num_in_calc = 5

        expected_len_cross_match_table = 8

        catfile = os.path.join(os.getenv('HOME'), 'Asteroids', 'CatalogFiles', 'elp1m008-fl05-20160217-0218-e90_cat.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint(catfile, "PPMXL")

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 8)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 8)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_more(self):
        self.fail("write more tests")

    def test_vizier_down(self):
        self.fail("write test for no internet")

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

        column_types = [('ccd_x', '>f4'), 
                        ('ccd_y', '>f4'), 
                        ('obs_ra', '>f8'), 
                        ('obs_dec', '>f8'), 
                        ('obs_ra_err', '>f8'), 
                        ('obs_dec_err', '>f8'), 
                        ('major_axis', '>f4'), 
                        ('minor_axis', '>f4'), 
                        ('ccd_pa', '>f4'), 
                        ('obs_mag', '>f4'), 
                        ('obs_mag_err', '>f4'), 
                        ('obs_sky_bkgd', '>f4'), 
                        ('flags', '>i2')
                       ]
        self.basic_table = Table(dtype = column_types)

        self.maxDiff = None
        self.precision = 7

        self.flux2mag = 2.5/log(10)

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

    def test_ra_to_decimal_degrees(self):

        expected_value = 86.7366375 #conversion of 05:46:56.793 to decimal degrees

        value = convert_value('field_center_ra', '05:46:56.793')

        self.assertAlmostEqual(expected_value, value, 7)

    def test_dec_to_decimal_degrees(self):

        expected_value = -27.7043417 #conversion of -27:42:15.63 to decimal degrees

        value = convert_value('field_center_dec', '-27:42:15.63')

        self.assertAlmostEqual(expected_value, value, 7)

    def test_field_width(self):

        expected_value = '15.7846m' #2028 pixels x 0.467"/pixel converted to arcmin

        value = convert_value('field_width', (2028, 0.467))

        self.assertEqual(expected_value, value)

    def test_field_height(self):

        expected_value = '15.8624m' #2038 pixels x 0.467"/pixel converted to arcmin

        value = convert_value('field_height', (2038, 0.467))

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
                            'field_center_ra' : Angle(self.test_header['RA'], unit=u.hour).deg,
                            'field_center_dec' : Angle(self.test_header['DEC'], unit=u.deg).deg,
                            'field_width'   : '15.7846m',
                            'field_height'  : '15.8624m',
                            'pixel_scale'   : self.test_header['SECPIX'],
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

class FITSSubsetCatalogTable(FITSUnitTest):

    def test_dimensions(self):
        expected_rows = 360
        expected_columns = 13

        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
        new_table = subset_catalog_table(self.test_table, tbl_mapping)

        self.assertEqual(expected_rows, len(new_table))
        self.assertEqual(expected_columns, len(new_table.colnames))

class FITSReadCatalog(FITSUnitTest):


    def test_first_item(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
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
                                 })

        catalog_items = get_catalog_items(self.test_header, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)


    def test_last_item(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 1067.94714355,
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
                                 })

        catalog_items = get_catalog_items(self.test_header, self.table_lastitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_reject_item_flags24(self):

        expected_catalog = self.basic_table

        catalog_items = get_catalog_items(self.test_header, self.table_item_flags24)

        self.assertEqual(len(expected_catalog), len(catalog_items))

    def test_accept_item_flags24(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' :  234.52952576,
                                   'ccd_y' :    8.05962372,
                                   'major_axis'  : 2.38448,
                                   'minor_axis'  : 2.3142395,
                                   'ccd_pa'      : 54.71178436,
                                   'obs_ra'  :  86.849261129458455,
                                   'obs_dec' : -27.573775115523741,
                                   'obs_ra_err'  : 3.1925407884572581e-06,
                                   'obs_dec_err' : 2.9221911507086037e-06,
                                   'obs_mag' : -2.5*log10(67883.703125),
                                   'obs_mag_err'  : self.flux2mag * self.table_item_flags24['FLUXERR_AUTO']/self.table_item_flags24['FLUX_AUTO'],
                                   'obs_sky_bkgd' :741.20977783,
                                   'flags' : 24,
                                 })

        catalog_items = get_catalog_items(self.test_header, self.table_item_flags24, flag_filter=24)

        for column in expected_catalog.colnames:
            self.assertAlmostEqual(expected_catalog[column], catalog_items[column], 9, \
                msg="Failure on %s (%s != %s)" % (column, expected_catalog[column], catalog_items[column]))

    def test_first_item_with_bad_zeropoint(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
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
                                 })

        header_items = {'zeropoint' : -99}
        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_first_item_with_good_zeropoint(self):

        header_items = {'zeropoint' : 23.0}
        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
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
                                 })

        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_first_item_with_no_zeropoint(self):

        header_items = {'zerowibble' : -99}
        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
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
                                 })

        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)
