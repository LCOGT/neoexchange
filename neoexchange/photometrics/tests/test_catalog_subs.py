"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime, timedelta
from unittest import skipIf, skip
from math import sqrt, log10, log
import os
from glob import glob
import tempfile
import shutil
import stat

from mock import patch
from django.test import TestCase
from django.forms.models import model_to_dict
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.table import Table
from astropy.coordinates import Angle
import astropy.units as u
from numpy import where, array
from numpy.testing import assert_allclose

from core.models import Body, Proposal, Block, Frame, SuperBlock
from neox.tests.mocks import mock_get_vizier_catalog_table

# Import module to test
from photometrics.catalog_subs import *
from core.views import check_catalog_and_refit

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)


class ZeropointUnitTest(TestCase):

    def setUp(self):
        # Maybe do some static test catalog reading later
        # test if no catalog input, use default catalog
        # test_data = __file__.replace('.py', '_UCAC4.dat') #test_data_file captured with cat_table.write('test_ca
        # test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.d
        # mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')
        pass

    def compare_tables(self, expected_table, table, column, num_to_check=6, precision=6):

        for i in range(0, num_to_check+1):
            self.assertAlmostEqual(expected_table[column][i], table[column][i], precision)

    # @patch('photometrics.catalog_subs.Vizier')
    # def test_get_cat_ra_dec(self, mock_vizier):
    def test_get_cat_ra_dec(self):
        # test getting a single ra, dec, and rmag out of the default UCAC4 catalog
        # test_data = __file__.replace('.py', '_UCAC4.dat') #test_data_file captured with cat_table.write('test_catalog_subs_UCAC4.dat', format='csv')
        # test_data = '/home/sgreenstreet/git/neoexchange/neoexchange/photometrics/tests/test_catalog_subs_UCAC4.dat'
        # test_query_result = []
        # test_query_result.append(Table.read(test_data, format='csv'))
        # mock_vizier().query_region().__getitem__.return_value=test_query_result
        # print mock_vizier().query_region().__getitem__.return_value#['_RAJ2000'][0]
        # print len(mock_vizier().query_region().__getitem__.return_value)
        # print mock_vizier().query_region().__getitem__(0)
        # print test_query_result.__getitem__(0)
        # print test_query_result[0]
        # print len(test_query_result)
        # mock_vizier().query_region().__getitem__.return_value=Table.read(test_data, format='csv')
        # print mock_vizier().query_region().__getitem__.return_value[0]#['_RAJ2000'][0]
        # print len(mock_vizier().query_region().__getitem__.return_value[0])

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_third_source = 12.642

        expected_len_cat_table = 1607

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", "UCAC4")
        # print(cat_table['_RAJ2000'][0], cat_table['_DEJ2000'][0]#, cat_table['rmag'][2])
        # print(cat_name)
        # print(cat_table)

        ra_first_source = cat_table['RAJ2000'][0]

        dec_first_source = cat_table['DEJ2000'][0]

        rmag_third_source = cat_table['rmag'][2]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 6)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 6)
        self.assertAlmostEqual(expected_rmag_third_source, rmag_third_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    # @patch('photometrics.catalog_subs.Vizier')
    # def test_no_cat(self, mock_vizier):
    def test_no_cat(self):

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

        expected_rmag_third_source = 12.642

        expected_len_cat_table = 1607

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m")

        ra_first_source = cat_table['RAJ2000'][0]

        dec_first_source = cat_table['DEJ2000'][0]

        rmag_third_source = cat_table['rmag'][2]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 6)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 6)
        self.assertAlmostEqual(expected_rmag_third_source, rmag_third_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

#    @patch('photometrics.catalog_subs.Vizier')
#    def test_get_cat_ra_dec_not_default(self, mock_vizier):
    def test_get_cat_ra_dec_not_default(self):

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

        expected_rmag_first_source = 14.32

        expected_len_cat_table = 737

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", "PPMXL")

        ra_first_source = cat_table['RAJ2000'][0]

        dec_first_source = cat_table['DEJ2000'][0]

        rmag_first_source = cat_table['r2mag'][0]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 8)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 8)
        self.assertAlmostEqual(expected_rmag_first_source, rmag_first_source, 3)
        self.assertEqual(expected_len_cat_table, len(cat_table))

#    @patch('photometrics.catalog_subs.Vizier')
#    def test_get_cat_diff_rmag_limit(self, mock_vizier):
    def test_get_cat_diff_rmag_limit(self):

        expected_ra_last_source = 299.82885099999999

        expected_dec_last_source = 34.998407

        expected_rmag_last_source = 14.5

        expected_len_cat_table = 443

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", rmag_limit="<=14.5", cat_name="PPMXL")

        ra_last_source = cat_table['RAJ2000'][-1]

        dec_last_source = cat_table['DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 6)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 1)
        self.assertEqual(expected_len_cat_table, len(cat_table))

#    @patch('photometrics.catalog_subs.Vizier')
#    def test_get_cat_diff_row_limit(self, mock_vizier):
    def test_get_cat_diff_row_limit(self):

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

        expected_rmag_first_source = 14.32

        expected_len_cat_table = 737

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", set_row_limit=40, cat_name="PPMXL")

        ra_first_source = cat_table['RAJ2000'][0]

        dec_first_source = cat_table['DEJ2000'][0]

        rmag_first_source = cat_table['r2mag'][0]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 8)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 8)
        self.assertAlmostEqual(expected_rmag_first_source, rmag_first_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

#    @patch('photometrics.catalog_subs.Vizier')
#    def test_get_cat_diff_width(self, mock_vizier):
    def test_get_cat_diff_width(self):

        expected_ra_last_source = 299.74110200000001

        expected_dec_last_source = 35.313324999999999

        expected_rmag_3rdlast_source = 14.81

        expected_len_cat_table = 408

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "15m", "15m")

        ra_last_source = cat_table['RAJ2000'][-1]

        dec_last_source = cat_table['DEJ2000'][-1]

        rmag_3rdlast_source = cat_table['rmag'][-3]

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 6)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 6)
        self.assertAlmostEqual(expected_rmag_3rdlast_source, rmag_3rdlast_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

#    @patch('photometrics.catalog_subs.Vizier')
#    def test_get_cat_ra_dec_above_row_limit(self, mock_vizier):
    def test_get_cat_ra_dec_above_row_limit(self):

        expected_ra_last_source = 267.35990700000002

        expected_dec_last_source = -28.212005999999999

        expected_rmag_last_source = 14.54

        expected_len_cat_table = 11838

        cat_table, cat_name = get_vizier_catalog_table(266.4168, -29.0078, "100m", "100m", "PPMXL")

        ra_last_source = cat_table['RAJ2000'][-1]

        dec_last_source = cat_table['DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

#    @patch('photometrics.catalog_subs.Vizier')
#    def test_get_cat_ra_dec_empty_list_PPMXL(self, mock_vizier):
    @skip("Defunct catalog / needs mock")
    def test_get_cat_ra_dec_empty_list_PPMXL(self):

        expected_ra_last_source = 0.0

        expected_dec_last_source = 0.0

        expected_rmag_last_source = 0.0

        expected_len_cat_table = 100000

        cat_table, cat_name = get_vizier_catalog_table(298.590, 35.201, "0.5m", "0.5m", "PPMXL")

        ra_last_source = cat_table['RAJ2000'][-1]

        dec_last_source = cat_table['DEJ2000'][-1]

        rmag_last_source = cat_table['rmag'][-1]  # will replace cat_name with UCAC4 after failing with PPMXL

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

#    @patch('photometrics.catalog_subs.Vizier')
#    def test_get_cat_ra_dec_empty_list_UCAC4(self, mock_vizier):
    @skip("Defunct catalog / needs mock")
    def test_get_cat_ra_dec_empty_list_UCAC4(self):

        expected_ra_last_source = 0.0

        expected_dec_last_source = 0.0

        expected_rmag_last_source = 0.0

        expected_len_cat_table = 100000

        cat_table, cat_name = get_vizier_catalog_table(298.590, 35.201, "0.5m", "0.5m")

        ra_last_source = cat_table['RAJ2000'][-1]

        dec_last_source = cat_table['DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]  # will replace cat_name with PPMXL after failing with UCAC4

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    def test_get_cat_ra_dec_empty_rmag_column_UCAC4(self):

        expected_ra_last_source = 306.66333600

        expected_dec_last_source = -26.750156

        expected_rmag_last_source = 14.7

        expected_len_cat_table = 52

        cat_table, cat_name = get_vizier_catalog_table(306.6792, -26.6278, "15m", "15m")

        ra_last_source = cat_table['RAJ2000'][-1]

        dec_last_source = cat_table['DEJ2000'][-1]

        rmag_last_source = cat_table['r2mag'][-1]  # will replace cat_name with PPMXL after failing with UCAC4

        self.assertAlmostEqual(expected_ra_last_source, ra_last_source, 8)
        self.assertAlmostEqual(expected_dec_last_source, dec_last_source, 8)
        self.assertAlmostEqual(expected_rmag_last_source, rmag_last_source, 2)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    def test_get_cat_ra_dec_GAIA_DR2(self):

        expected_ra_first_source = 299.84644068600
        expected_dec_first_source = 34.96403374990
        expected_rmag_first_source = 14.7231
        expected_e_rmag_first_source = 0.0003
        expected_flags_first_source = 0
        expected_len_cat_table = 574

        cat_table, cat_name = get_vizier_catalog_table(299.590, 35.201, "30m", "30m", "GAIA-DR2")

        ra_first_source = cat_table['RAJ2000'][0]
        dec_first_source = cat_table['DEJ2000'][0]
        rmag_first_source = cat_table['Gmag'][0]
        e_rmag_first_source = cat_table['e_Gmag'][0]
        flags_first_source = cat_table['Dup'][0]

        self.assertAlmostEqual(expected_ra_first_source, ra_first_source, 8)
        self.assertAlmostEqual(expected_dec_first_source, dec_first_source, 8)
        self.assertAlmostEqual(expected_rmag_first_source, rmag_first_source, 5)
        self.assertAlmostEqual(expected_e_rmag_first_source, e_rmag_first_source, 5)
        self.assertEqual(expected_flags_first_source, flags_first_source)
        self.assertEqual(expected_len_cat_table, len(cat_table))

    def test_cross_match_UCAC4_longerThan_testFITS(self):
        # test with cat 1 as longer UCAC4 table values and cat 2 as shorter test FITS table values

        expected_cross_match_table_data = [(299.303973, 299.304084, 1.11e-04, 35.20152, 35.201634, 1.1400e-04, 0.0, 13.8500003815, 0.05, 13.8500003815),
                                           (299.828851, 299.828851, 0.0, 34.99841, 34.998407, 3.0000e-06, 0.0, 14.5, 0.01, 14.5),
                                           (299.291455, 299.291366, 8.9000e-5, 35.242368, 35.242404, 3.6000e-05, 0.0, 14.3199996948, 0.03, 14.3199996948),
                                           (299.510127, 299.510143, 1.6000e-05, 34.960327, 34.960303, 2.4000e-05, 15.5469999313, 14.4499998093, 0.05, 1.097000),
                                           (299.308515, 299.308579, 6.4000e-05, 35.165529, 35.165495, 3.4000e-05, 15.0059995651, 14.8900003433, 0.02, 0.115999),
                                           (299.709162, 299.709139, 2.3000e-05, 35.218112, 35.218109, 3.0000e-06, 13.3520002365, 12.7700004578, 0.0, 0.582000),
                                           (299.860889, 299.860871, 1.8000e-05, 35.381485, 35.381474, 1.1000e-05, 14.9130001068, 14.0799999237, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff',
                                                                                        'Dec Cat 1', 'Dec Cat 2', 'Dec diff',
                                                                                        'r mag Cat 1', 'r mag Cat 2', 'r mag err',
                                                                                        'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names=('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 3, 0),
                            (299.304084, 35.201634, 13.8500003815, 5, 0),
                            (299.480004, 34.965488, 14.3800001144, 3, 0),
                            (299.308579, 35.165495, 14.8900003433, 2, 0),
                            (299.828851, 34.998407, 14.5, 1, 0),
                            (299.510143, 34.960303, 14.4499998093, 5, 0),
                            (299.709139, 35.218109, 12.7700004578, 0, 0),
                            (299.860871, 35.381474, 14.0799999237, 0, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names=('RAJ2000', 'DEJ2000', 'rmag', 'e_rmag', 'flags'), dtype=('f8', 'f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2)

        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 1')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 2')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA diff', precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 1')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 2')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec diff', precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 1', precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 2', precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag err', precision=2)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag diff')

    def test_cross_match_UCAC4_shorterThan_testFITS(self):
        # test with cat 1 as longer test FITS table values and cat 2 as shorter UCAC4 table values to test cat reordering
        # also tests filtering of poor cross matches

        expected_cross_match_table_data = [(299.291366, 299.291455, 8.9000e-5, 35.242404, 35.242368, 3.6000e-05, 14.3199996948, 0.0, 0.03, 14.3199996948),
                                           (299.304084, 299.303973, 1.11e-04, 35.201634, 35.20152, 1.1400e-04, 13.8500003815, 0.0, 0.05, 13.8500003815),
                                           (299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.03, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.02, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5, 0.0, 0.01, 14.5),
                                           (299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.05, 1.097000),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1',
                                                                                        'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2',
                                                                                        'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8',
                                                                                                                           'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.479984, 34.965502, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.884478, 34.978454, 0.0, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names=('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 3, 0),
                            (299.304084, 35.201634, 13.8500003815, 5, 0),
                            (299.480004, 34.965488, 14.3800001144, 3, 0),
                            (299.308579, 35.165495, 14.8900003433, 2, 0),
                            (299.828851, 34.998407, 14.5, 1, 0),
                            (299.510143, 34.960303, 14.4499998093, 5, 0),
                            (299.709139, 35.218109, 12.7700004578, 0, 0),
                            (299.860871, 35.381474, 14.0799999237, 0, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names=('RAJ2000', 'DEJ2000', 'rmag', 'e_rmag', 'flags'), dtype=('f8', 'f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2)

        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 1', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 2', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA diff', num_to_check=7, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 1', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 2', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec diff', num_to_check=7, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 1', num_to_check=7, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 2', num_to_check=7, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag err', num_to_check=7, precision=2)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag diff', 7)

    def test_cross_match_PPMXL_shorterThan_testFITS(self):
        # test with cat 1 as longer test FITS table values and cat 2 as shorter PPMXL table values to test cat reordering
        # also tests filtering of poor cross matches

        expected_cross_match_table_data = [(299.291366, 299.291455, 8.9000e-5, 35.242404, 35.242368, 3.6000e-05, 14.3199996948, 0.0, 0.0, 14.3199996948),
                                           (299.304084, 299.303973, 1.11e-04, 35.201634, 35.20152, 1.1400e-04, 13.8500003815, 0.0, 0.0, 13.8500003815),
                                           (299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.0, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.0, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5, 0.0,  0.0, 14.5),
                                           (299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.0, 1.097000),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1',
                                                                                        'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2',
                                                                                        'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8',
                                                                                                                           'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.479984, 34.965502, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.884478, 34.978454, 0.0, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names=('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 0),
                            (299.304084, 35.201634, 13.8500003815, 0),
                            (299.480004, 34.965488, 14.3800001144, 0),
                            (299.308579, 35.165495, 14.8900003433, 0),
                            (299.828851, 34.998407, 14.5, 0),
                            (299.510143, 34.960303, 14.4499998093, 0),
                            (299.709139, 35.218109, 12.7700004578, 0),
                            (299.860871, 35.381474, 14.0799999237, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names=('RAJ2000', 'DEJ2000', 'r2mag', 'fl'), dtype=('f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2, "PPMXL")

        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 1', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 2', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA diff', num_to_check=7, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 1', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 2', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec diff', num_to_check=7, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 1', num_to_check=7, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 2', num_to_check=7, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag err', num_to_check=7, precision=2)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag diff', 7)

    def test_cross_match_UCAC_shorterThan_testFITS(self):
        # test with cat 1 as longer test FITS table values and cat 2 as shorter UCAC table values to test cat reordering NOTE: UCAC not UCAC4 tested here...need to add a test for something other than a variation of PPMXL or UCAC.
        # also tests filtering of poor cross matches

        expected_cross_match_table_data = [(299.291366, 299.291455, 8.9000e-5, 35.242404, 35.242368, 3.6000e-05, 14.3199996948, 0.0, 0.03, 14.3199996948),
                                           (299.304084, 299.303973, 1.11e-04, 35.201634, 35.20152, 1.1400e-04, 13.8500003815, 0.0, 0.05, 13.8500003815),
                                           (299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.03, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.02, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5, 0.0, 0.01, 14.5),
                                           (299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.05, 1.097000),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1',
                                                                                        'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2',
                                                                                        'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8',
                                                                                                                           'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.479984, 34.965502, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.884478, 34.978454, 0.0, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names=('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 3, 0),
                            (299.304084, 35.201634, 13.8500003815, 5, 0),
                            (299.480004, 34.965488, 14.3800001144, 3, 0),
                            (299.308579, 35.165495, 14.8900003433, 2, 0),
                            (299.828851, 34.998407, 14.5, 1, 0),
                            (299.510143, 34.960303, 14.4499998093, 5, 0),
                            (299.709139, 35.218109, 12.7700004578, 0, 0),
                            (299.860871, 35.381474, 14.0799999237, 0, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names=('RAJ2000', 'DEJ2000', 'rmag', 'e_rmag', 'flags'), dtype=('f8', 'f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2, "UCAC")

        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 1', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 2', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA diff', num_to_check=7, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 1', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 2', 7)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec diff', num_to_check=7, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 1', num_to_check=7, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 2', num_to_check=7, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag err', num_to_check=7, precision=2)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag diff', 7)

    def test_cross_match_filtering(self):
        # test filtering of poor catalog cross matches

        expected_cross_match_table_data = [(299.480004, 299.479984, 2.0000e-05, 34.965488, 34.965502, 1.4000e-05, 14.3800001144, 0.0, 0.0, 14.3800001144),
                                           (299.308579, 299.308515, 6.4000e-05, 35.165495, 35.165529, 3.4000e-05, 14.8900003433, 15.0059995651, 0.0, 0.115999),
                                           (299.828851, 299.828851, 0.0, 34.998407, 34.99841, 3.0000e-06, 14.5, 0.0, 0.0, 14.5),
                                           (299.709139, 299.709162, 2.3000e-05, 35.218109, 35.218112, 3.0000e-06, 12.7700004578, 13.3520002365, 0.0, 0.582000),
                                           (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1',
                                                                                        'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2',
                                                                                        'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8',
                                                                                                                           'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

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

        table_cat_1 = Table(rows=table_cat_1_data, names=('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

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

        table_cat_2 = Table(rows=table_cat_2_data, names=('RAJ2000', 'DEJ2000', 'r2mag', 'fl'), dtype=('f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2, "PPMXL")

        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 1', num_to_check=4)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 2', num_to_check=4)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA diff', num_to_check=4, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 1', 4)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 2', 4)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec diff', num_to_check=4, precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 1', num_to_check=4, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 2', num_to_check=4, precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag diff', 4)

    def test_cross_match_GAIA_longerThan_testFITS(self):
        # test with cat 1 as longer GAIA table values and cat 2 as shorter test FITS table values

        expected_cross_match_table_data = [(299.303973, 299.304084, 1.11e-04, 35.20152, 35.201634, 1.1400e-04, 0.0, 13.8500003815, 0.05, 13.8500003815),
                                           (299.828851, 299.828851, 0.0, 34.99841, 34.998407, 3.0000e-06, 0.0, 14.5, 0.01, 14.5),
                                           (299.291455, 299.291366, 8.9000e-5, 35.242368, 35.242404, 3.6000e-05, 0.0, 14.3199996948, 0.03, 14.3199996948),
                                           (299.510127, 299.510143, 1.6000e-05, 34.960327, 34.960303, 2.4000e-05, 15.5469999313, 14.4499998093, 0.05, 1.097000),
                                           (299.308515, 299.308579, 6.4000e-05, 35.165529, 35.165495, 3.4000e-05, 15.0059995651, 14.8900003433, 0.02, 0.115999),
                                           (299.709162, 299.709139, 2.3000e-05, 35.218112, 35.218109, 3.0000e-06, 13.3520002365, 12.7700004578, 0.0, 0.582000),
                                           (299.860889, 299.860871, 1.8000e-05, 35.381485, 35.381474, 1.1000e-05, 14.9130001068, 14.0799999237, 0.0, 0.833000)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff',
                                                                                        'Dec Cat 1', 'Dec Cat 2', 'Dec diff',
                                                                                        'r mag Cat 1', 'r mag Cat 2', 'r mag err',
                                                                                        'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        table_cat_1_data = [(299.303973, 35.20152, 0.0, 0),
                            (299.828851, 34.99841, 0.0, 0),
                            (299.291455, 35.242368, 0.0, 0),
                            (299.510127, 34.960327, 15.5469999313, 0),
                            (299.308515, 35.165529, 15.0059995651, 0),
                            (299.709162, 35.218112, 13.3520002365, 0),
                            (299.860889, 35.381485, 14.9130001068, 0)]

        table_cat_1 = Table(rows=table_cat_1_data, names=('obs_ra', 'obs_dec', 'obs_mag', 'flags'), dtype=('f8', 'f8', 'f8', 'i2'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948, 3, 0),
                            (299.304084, 35.201634, 13.8500003815, 5, 0),
                            (299.480004, 34.965488, 14.3800001144, 3, 0),
                            (299.308579, 35.165495, 14.8900003433, 2, 0),
                            (299.828851, 34.998407, 14.5, 1, 0),
                            (299.510143, 34.960303, 14.4499998093, 5, 0),
                            (299.709139, 35.218109, 12.7700004578, 0, 0),
                            (299.860871, 35.381474, 14.0799999237, 0, 0)]

        table_cat_2 = Table(rows=table_cat_2_data, names=('RAJ2000', 'DEJ2000', 'Gmag', 'e_Gmag', 'Dup'), dtype=('f8', 'f8', 'f8', 'f8', 'i2'))

        cross_match_table = cross_match(table_cat_1, table_cat_2, cat_name='GAIA-DR2')

        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 1')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA Cat 2')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'RA diff', precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 1')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec Cat 2')
        self.compare_tables(expected_cross_match_table, cross_match_table, 'Dec diff', precision=9)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 1', precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag Cat 2', precision=10)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag err', precision=2)
        self.compare_tables(expected_cross_match_table, cross_match_table, 'r mag diff')

    def test_get_zeropoint(self):
        # test zeropoint calculation

        expected_avg_zeropoint = 0.8520

        expected_std_zeropoint = 0.1745

        expected_count = 3

        expected_num_in_calc = 3

        cross_match_table_data = [(299.510143, 299.510127, 1.6000e-05, 34.960303, 34.960327, 2.4000e-05, 14.4499998093, 15.5469999313, 0.05, 1.097000),
                                  (299.860871, 299.860889, 1.8000e-05, 35.381474, 35.381485, 1.1000e-05, 14.0799999237, 14.9130001068, 0.03, 0.833000),
                                  (299.789005, 299.788977, 2.8000e-05, 34.983303, 34.98333, 2.7000e-05, 14.5200004578, 13.795999527, 0.03, 0.724000)]

        cross_match_table = Table(rows=cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff',
                                                                      'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8',
                                                                                                                                       'f8', 'f8', 'f8', 'f8', 'f8',
                                                                                                                                       'f8', 'f8'))

        avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table, std_zeropoint_tolerance=0.2)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 4)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 4)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)

    def test_get_zeropoint_larger_dataset(self):
        # test zeropoint calculation

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

        cross_match_table = Table(rows=cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table, std_zeropoint_tolerance=0.1)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 4)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 4)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)

    def test_get_zeropoint_inconclusive_value(self):
        # test zeropoint calculation

        expected_avg_zeropoint = 40.0

        expected_std_zeropoint = 10.0

        expected_count = 0

        expected_num_in_calc = 2

        cross_match_table_data = [(209.146558, 209.146514825, 4.3175e-05, -17.450514, -17.4505721629, 5.8163e-05, 13.9300003052, 12.8761520386, 0.01, 1.0538),
                                  (209.107363, 209.107484127, 0.0001, -17.524826, -17.5249530573, 0.0001, 12.8000001907, 17.7864189148, 0.01, 4.9864),
                                  (209.319028, 209.319387053, 0.0004, -17.577961, -17.5778475751, 0.0001, 13.4300003052, 17.4026889801, 0.01, 3.9727)]

        cross_match_table = Table(rows=cross_match_table_data, names=('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag err', 'r mag diff'), dtype=('f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8', 'f8'))

        avg_zeropoint, std_zeropoint, count, num_in_calc = get_zeropoint(cross_match_table, std_zeropoint_tolerance=0.1)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 4)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 4)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)

    def test_call_cross_match_and_zeropoint_with_PPMXL(self):

        expected_avg_zeropoint = 27.389039993231853 - 5.0 # Correcting for 100s exptime

        expected_std_zeropoint = 0.08511636159289811

        expected_count = 12

        expected_num_in_calc = 12

        expected_cat_name = "PPMXL"

        expected_len_cross_match_table = 21

        catfile = os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name = call_cross_match_and_zeropoint(catfile, cat_name="PPMXL")

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 7)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 7)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertEqual(expected_cat_name, cat_name)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_cross_match_and_zeropoint_with_UCAC4(self):

        expected_avg_zeropoint = 27.30760348193786 - 5.0 # Correcting for 100s exptime

        expected_std_zeropoint = 0.0818536464006553

        expected_count = 26

        expected_num_in_calc = 26

        expected_cat_name = "UCAC4"

        expected_len_cross_match_table = 56

        catfile = os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name = call_cross_match_and_zeropoint(catfile)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 7)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 7)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertEqual(expected_cat_name, cat_name)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_cross_match_and_zeropoint_with_GAIADR2(self):

        expected_avg_zeropoint = 27.368678593401157 - 5.0 # Correcting for 100s exptime

        expected_std_zeropoint = 0.018250135920613784

        expected_count = 10

        expected_num_in_calc = 10

        expected_cat_name = "GAIA-DR2"

        expected_len_cross_match_table = 20

        catfile = os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name = call_cross_match_and_zeropoint(catfile, cat_name='GAIA-DR2')

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 7)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 7)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertEqual(expected_cat_name, cat_name)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    @skip("Defunct catalog / needs mock")
    def test_call_with_diff_test_cat_force_to_UCAC4(self):
        """test the call with a different FITS catalog file that will return an empty vizier query table for the PPMXL
        catalog and a zeropoint already in the header, so that the computed avg_zeropoint is the difference between
        the FITS catalog ZP (in the header) and the Vizier catalog computed ZP
        """

        expected_avg_zeropoint = 0.27694574038664266

        expected_std_zeropoint = 0.0857936711126839

        expected_count = 9

        expected_num_in_calc = 9

        expected_cat_name = "UCAC4"

        expected_len_cross_match_table = 19

        catfile = os.path.join('photometrics', 'tests', 'CatalogFiles', 'cpt1m010-kb70-20160210-0365-e90_cat.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name = call_cross_match_and_zeropoint(catfile, cat_name="PPMXL")

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 8)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 8)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertEqual(expected_cat_name, cat_name)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_with_diff_test_cat_UCAC4(self):
        # test the call with a different FITS catalog file and the default UCAC4 catalog

        expected_avg_zeropoint = 27.29694970829 - 2.5*log10(15) # correct for exptime

        expected_std_zeropoint = 0.05121124525367079

        expected_count = 8

        expected_num_in_calc = 8

        expected_cat_name = "UCAC4"

        expected_len_cross_match_table = 16

        catfile = os.path.join('photometrics', 'tests', 'CatalogFiles', 'elp1m008-fl05-20160217-0218-e90_cat.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name = call_cross_match_and_zeropoint(catfile)

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 7)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 7)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertEqual(expected_cat_name, cat_name)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    def test_call_with_diff_test_cat_PPMXL(self):
        # test the call with a different FITS catalog file and the default UCAC4 catalog

        expected_avg_zeropoint = 27.09466082586 - 2.5*log10(15) # correct for exptime

        expected_std_zeropoint = 0.064360751790

        expected_count = 5

        expected_num_in_calc = 5

        expected_cat_name = "PPMXL"

        expected_len_cross_match_table = 8

        catfile = os.path.join('photometrics', 'tests', 'CatalogFiles', 'elp1m008-fl05-20160217-0218-e90_cat.fits')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name = call_cross_match_and_zeropoint(catfile, cat_name="PPMXL")

        self.assertAlmostEqual(expected_avg_zeropoint, avg_zeropoint, 7)
        self.assertAlmostEqual(expected_std_zeropoint, std_zeropoint, 7)
        self.assertAlmostEqual(expected_count, count, 1)
        self.assertAlmostEqual(expected_num_in_calc, num_in_calc, 1)
        self.assertEqual(expected_cat_name, cat_name)
        self.assertAlmostEqual(expected_len_cross_match_table, len(cross_match_table))

    @skipIf(True, "write test for no internet")
    def test_vizier_down(self):
        self.fail("write test for no internet")


class TestGetReferenceCatalog(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.header = { 'ra' : 228.33284875,
                        'dec': 38.395874166666665,
                        'width': '4.5m',
                        'height': '3.0m',
                      }
        self.expected_ref_catalog = os.path.join(self.temp_dir, 'GAIA-DR2_228.33+38.40_6.7500mx4.5000m.cat')

        self.remove = True
        self.debug_print = False

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.temp_dir)
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print:
                    print("Removed", self.temp_dir)
            except OSError:
                print("Error removing temporary test directory", self.temp_dir)
        else:
            print("Temporary test directory=", self.temp_dir)

    def touch(self, fname, times=None):
        with open(fname, 'a'):
            os.utime(fname, times)

    def test_fetch_catalog(self):

        expected_num_sources = 10

        refcat, num_sources = get_reference_catalog(self.temp_dir, self.header['ra'], self.header['dec'], self.header['width'], self.header['height'])

        self.assertTrue(os.path.exists(self.expected_ref_catalog))
        self.assertEqual(self.expected_ref_catalog, refcat)
        self.assertEqual(expected_num_sources, num_sources)

    def test_fetch_catalog_existing(self):

        self.touch(self.expected_ref_catalog)
        expected_num_sources = -1

        refcat, num_sources = get_reference_catalog(self.temp_dir, self.header['ra'], self.header['dec'], self.header['width'], self.header['height'])

        self.assertTrue(os.path.exists(self.expected_ref_catalog))
        self.assertEqual(self.expected_ref_catalog, refcat)
        self.assertEqual(expected_num_sources, num_sources)

    @patch('photometrics.catalog_subs.get_vizier_catalog_table', mock_get_vizier_catalog_table)
    def test_Sinistro_SH(self):

        expected_refcat = os.path.join(self.temp_dir, 'GAIA-DR2_122.50-57.75_39.7500mx39.7500m.cat')
        expected_numsrcs = 2

        ra = 122.5
        dec = -57.75
        frame_width = '26.5m'
        frame_height = '26.5m'
        refcat, num_ref_srcs = get_reference_catalog(self.temp_dir, ra, dec, frame_width, frame_height, cat_name="GAIA-DR2")

        self.assertEqual(expected_refcat, refcat)
        self.assertEqual(expected_numsrcs, num_ref_srcs)

    @patch('photometrics.catalog_subs.get_vizier_catalog_table', mock_get_vizier_catalog_table)
    def test_Sinistro_NH(self):

        expected_refcat = os.path.join(self.temp_dir, 'GAIA-DR2_0.12+0.75_39.7200mx39.7200m.cat')
        expected_numsrcs = 2

        ra = 0.12345
        dec = 0.752
        frame_width = '26.48m'
        frame_height = '26.48m'
        refcat, num_ref_srcs = get_reference_catalog(self.temp_dir, ra, dec, frame_width, frame_height, cat_name="GAIA-DR2")

        self.assertEqual(expected_refcat, refcat)
        self.assertEqual(expected_numsrcs, num_ref_srcs)

    @patch('photometrics.catalog_subs.get_vizier_catalog_table', mock_get_vizier_catalog_table)
    def test_Sinistro_NH_existing(self):

        expected_refcat = os.path.join(self.temp_dir, 'GAIA-DR2_10.12+0.75_39.7200mx39.7200m.cat')
        expected_numsrcs = -1

        self.touch(expected_refcat)
        ra = 10.12345
        dec = 0.752
        frame_width = '26.48m'
        frame_height = '26.48m'
        refcat, num_ref_srcs = get_reference_catalog(self.temp_dir, ra, dec, frame_width, frame_height, cat_name="GAIA-DR2")

        self.assertEqual(expected_refcat, refcat)
        self.assertEqual(expected_numsrcs, num_ref_srcs)

    @patch('photometrics.catalog_subs.get_vizier_catalog_table', mock_get_vizier_catalog_table)
    def test_Sinistro_NH_existing_RAwrap(self):

        expected_refcat = os.path.join(self.temp_dir, 'GAIA-DR2_0.12+0.75_39.7200mx39.7200m.cat')
        expected_numsrcs = -1

        self.touch(expected_refcat)
        ra = 0.12345
        dec = 0.752
        frame_width = '26.48m'
        frame_height = '26.48m'
        refcat, num_ref_srcs = get_reference_catalog(self.temp_dir, ra, dec, frame_width, frame_height, cat_name="GAIA-DR2")

        self.assertEqual(expected_refcat, refcat)
        self.assertEqual(expected_numsrcs, num_ref_srcs)

    @patch('photometrics.catalog_subs.get_vizier_catalog_table', mock_get_vizier_catalog_table)
    def test_Sinistro_NH_existing_overlap(self):

        expected_refcat = os.path.join(self.temp_dir, 'GAIA-DR2_0.12+0.75_39.72mx39.72m.cat')
        expected_numsrcs = -1

        self.touch(expected_refcat)
        ra = 0.134
        dec = 0.743
        frame_width = '26.48m'
        frame_height = '26.48m'
        refcat, num_ref_srcs = get_reference_catalog(self.temp_dir, ra, dec, frame_width, frame_height, cat_name="GAIA-DR2")

        self.assertEqual(expected_refcat, refcat)
        self.assertEqual(expected_numsrcs, num_ref_srcs)


class TestExistingCatalogCoverage(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.header = { 'ra' : 228.25,
                        'dec': 38.40,
                        'width': '4.5m',
                        'height': '3.0m',
                      }
        self.expected_ref_catalog = os.path.join(self.temp_dir, 'GAIA-DR2_228.25+38.40_6.7500mx4.5000m.cat')

        self.remove = True
        self.debug_print = False

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.temp_dir)
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print:
                    print("Removed", self.temp_dir)
            except OSError:
                print("Error removing temporary test directory", self.temp_dir)
        else:
            print("Temporary test directory=", self.temp_dir)

    def touch(self, fname, times=None):
        with open(fname, 'a'):
            os.utime(fname, times)

    def test_empty_dir(self):

        existing_catalog = existing_catalog_coverage(self.temp_dir, self.header['ra'], self.header['dec'], self.header['width'], self.header['height'])

        self.assertEqual(None, existing_catalog)

    def test_not_a_dir(self):

        existing_catalog = existing_catalog_coverage(self.expected_ref_catalog, self.header['ra'], self.header['dec'], self.header['width'], self.header['height'])

        self.assertEqual(None, existing_catalog)

    def test_wrong_cattype(self):
        self.touch(self.expected_ref_catalog)

        ra = self.header['ra'] + 0.25
        dec = self.header['dec'] - 0.01
        existing_catalog = existing_catalog_coverage(self.temp_dir, ra, dec, self.header['width'], self.header['height'], cat_name='PPMXL')

        self.assertEqual(None, existing_catalog)

    def test_1cat(self):
        self.touch(self.expected_ref_catalog)

        ra = self.header['ra'] + 0.0125
        dec = self.header['dec'] - 0.005
        existing_catalog = existing_catalog_coverage(self.temp_dir, ra, dec, self.header['width'], self.header['height'])

        self.assertEqual(self.expected_ref_catalog, existing_catalog)

    def test_1cat_nooverlap(self):
        self.touch(self.expected_ref_catalog)

        ra = self.header['ra'] + 10
        dec = self.header['dec'] - 10
        existing_catalog = existing_catalog_coverage(self.temp_dir, ra, dec, self.header['width'], self.header['height'])

        self.assertEqual(None, existing_catalog)

    def test_2cat_lhs(self):
        self.touch(self.expected_ref_catalog)
        second_cat = os.path.join(self.temp_dir, 'GAIA-DR2_228.14+38.40_6.7500mx4.500m.cat')
        self.touch(second_cat)

        ra = self.header['ra'] + 0.01
        dec = self.header['dec'] - 0.01
        existing_catalog = existing_catalog_coverage(self.temp_dir, ra, dec, self.header['width'], self.header['height'])

        self.assertEqual(self.expected_ref_catalog, existing_catalog)

    def test_2cat_rhs(self):
        self.touch(self.expected_ref_catalog)
        second_cat = os.path.join(self.temp_dir, 'GAIA-DR2_228.14+38.40_6.7500mx4.500m.cat')
        self.touch(second_cat)

        ra = self.header['ra'] - 0.10
        dec = self.header['dec'] + 0.01
        existing_catalog = existing_catalog_coverage(self.temp_dir, ra, dec, self.header['width'], self.header['height'])

        self.assertEqual(second_cat, existing_catalog)

    def test_1cat_SH(self):
        ref_catalog = os.path.join(self.temp_dir, 'GAIA-DR2_120.55-59.00_40.000mx40.000m.cat')

        self.touch(ref_catalog)

        ra = 120.58
        dec = -59.01
        width = '26.4m'
        height = '26.4m'
        existing_catalog = existing_catalog_coverage(self.temp_dir, ra, dec, width, height)

        self.assertEqual(ref_catalog, existing_catalog)


class TestConvertCatfileToCorners(TestCase):

    def test_nopath1(self):
        expected_tl = (228.5, 38.65)
        expected_br = (228.0, 38.15)

        cat_file = 'GAIA-DR2_228.25+38.40_30.0000mx30.0000m.cat'

        top_left, bottom_right = convert_catfile_to_corners(cat_file)

        self.assertEqual(expected_tl, top_left)
        self.assertEqual(expected_br, bottom_right)

    def test_nopath2(self):
        expected_tl = (28.5, -38.15)
        expected_br = (28.0, -38.65)

        cat_file = 'GAIA-DR2_28.25-38.40_30.0000mx30.0000m.cat'

        top_left, bottom_right = convert_catfile_to_corners(cat_file)

        self.assertEqual(expected_tl, top_left)
        self.assertEqual(expected_br, bottom_right)

    def test_nopath3(self):
        expected_tl = (328.503525, -38.229465)
        expected_br = (327.996475, -38.570535)

        cat_file = 'GAIA-DR2_328.25-38.40_30.4230mx20.4642m.cat'

        top_left, bottom_right = convert_catfile_to_corners(cat_file)

        self.assertEqual(expected_tl, top_left)
        self.assertEqual(expected_br, bottom_right)

    def test_withpath1(self):
        expected_tl = (228.5, 38.65)
        expected_br = (228.0, 38.15)

        cat_file = os.path.join('/tmp', 'tmp_neox_cucumber', 'GAIA-DR2_228.25+38.40_30.0000mx30.0000m.cat')

        top_left, bottom_right = convert_catfile_to_corners(cat_file)

        self.assertEqual(expected_tl, top_left)
        self.assertEqual(expected_br, bottom_right)

    def test_withpath2(self):
        expected_tl = (120.8, -58.75)
        expected_br = (120.3, -59.25)

        cat_file = os.path.join('/tmp', 'tmp_neox_cucumber', 'GAIA-DR2_120.55-59.00_30.0000mx30.0000m.cat')

        top_left, bottom_right = convert_catfile_to_corners(cat_file)

        self.assertEqual(expected_tl, top_left)
        self.assertEqual(expected_br, bottom_right)

    def test_withpath3(self):
        expected_tl = None
        expected_br = None

        cat_file = os.path.join('/tmp', 'tmp_neox_cucumber', 'GAIA-DR2.cat')

        top_left, bottom_right = convert_catfile_to_corners(cat_file)

        self.assertEqual(expected_tl, top_left)
        self.assertEqual(expected_br, bottom_right)


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
        self.table_num_flags0 = len(where(self.test_table['flags'] == 0)[0])

        self.test_bad_ldacfilename = os.path.join('photometrics', 'tests', 'ldac_test_catalog_corrupt.fits')
        self.test_ldacfilename = os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits')
        hdulist = fits.open(self.test_ldacfilename)
        header_array = hdulist[1].data[0][0]
        header = fits_ldac_to_header(header_array)
        self.test_ldacwcs = WCS(header)
        self.test_ldac_pixscale = round(proj_plane_pixel_scales(self.test_ldacwcs).mean()*3600.0, 5)
        self.test_ldactable = hdulist[2].data
        hdulist.close()
        self.ldac_table_firstitem = self.test_ldactable[0:1]

        self.test_photpipefilename = os.path.join('photometrics', 'tests', 'photpipe_test_ldac.fits')
        hdulist = fits.open(self.test_photpipefilename)
        # FITS header in the example above is broken (as it is from photometrypipeline)
        # so need to read a fixed version to make the WCS from
        header = fits.Header.fromtextfile(os.path.join('photometrics', 'tests', 'example_photpipe.head'))
        self.test_photpipe_ldacwcs = WCS(header)
        self.test_photpipe_ldac_pixscale = round(proj_plane_pixel_scales(self.test_photpipe_ldacwcs).mean()*3600.0, 5)
        self.test_photpipe_ldactable = hdulist[2].data
        hdulist.close()
        self.photpipe_table_firstitem = self.test_photpipe_ldactable[0:1]

        self.test_banzaifilename = os.path.join('photometrics', 'tests', 'banzai_test_frame.fits.fz')
        hdulist = fits.open(self.test_banzaifilename)
        self.test_banzaiheader = hdulist['SCI'].header
        self.test_banzaitable = hdulist['CAT'].data
        self.test_banzaiwcs = WCS(self.test_banzaiheader)
        hdulist.close()
        self.banzai_table_firstitem = self.test_banzaitable[0:1]

        self.test_uncomp_banzaifilename = os.path.join('photometrics', 'tests', 'banzai_test_frame.fits')
        hdulist = fits.open(self.test_uncomp_banzaifilename)
        self.test_uncomp_banzaiheader = hdulist['SCI'].header
        self.test_uncomp_banzaitable = hdulist['CAT'].data
        hdulist.close()
        self.uncomp_banzai_table_firstitem = self.test_banzaitable[0:1]

        self.test_swopefilename = os.path.join('photometrics', 'tests', 'swope_test_frame.fits')
        hdulist = fits.open(self.test_swopefilename)
        self.test_swopeheader = hdulist[0].header
        hdulist.close()

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
                        ('flags', '>i2'),
                        ('flux_max', '>f4'),
                        ('threshold', '>f4')
                       ]
        self.basic_table = Table(dtype=column_types)

        self.maxDiff = None
        self.precision = 7
        self.rtol = 10**-self.precision

        self.flux2mag = 2.5/log(10)

    def compare_tables(self, expected_catalog, catalog, precision=4):
        for column in expected_catalog.colnames:
            expected_column_value = float(expected_catalog[column].quantity)
            catalog_column_value = float(catalog[column].quantity)
            self.assertAlmostEqual(expected_column_value, catalog_column_value, precision,
                msg="Failure on %s (%.*f != %.*f)" % (column, precision, expected_column_value,
                    precision, catalog_column_value))

    def compare_headers(self, expected_params, frame_header, rtol=1e-8):
        self.assertEqual(len(expected_params), len(frame_header))
        for key in expected_params:
            err_msg = 'Failure on key='+key
            if key != 'wcs':
                if type(expected_params[key]) == float:
                    assert_allclose(expected_params[key], frame_header[key],rtol=1e-5, err_msg=err_msg)
                else:
                    self.assertEqual(expected_params[key], frame_header[key], msg=err_msg)
            else:
                expected_wcs = expected_params[key].wcs
                frame_wcs = frame_header[key].wcs
                assert_allclose(expected_wcs.crval, frame_wcs.crval, rtol=rtol, err_msg=err_msg)
                assert_allclose(expected_wcs.crpix, frame_wcs.crpix, rtol=rtol, err_msg=err_msg)
                assert_allclose(expected_wcs.cd, frame_wcs.cd, rtol=rtol, err_msg=err_msg)


class OpenFITSCatalog(FITSUnitTest):

    def test_catalog_does_not_exist(self):
        expected_hdr = {}
        expected_tbl = {}
        expected_cattype = None

        hdr, tbl, cattype = open_fits_catalog('wibble')

        self.assertEqual(expected_hdr, hdr)
        self.assertEqual(expected_tbl, tbl)
        self.assertEqual(expected_cattype, cattype)

    def test_catalog_is_not_FITS(self):
        expected_hdr = {}
        expected_tbl = {}
        expected_cattype = None

        hdr, tbl, cattype = open_fits_catalog(os.path.join('photometrics', 'tests', '__init__.py'))

        self.assertEqual(expected_hdr, hdr)
        self.assertEqual(expected_tbl, tbl)
        self.assertEqual(expected_cattype, cattype)

    def test_catalog_read_length(self):
        expected_hdr_len = len(self.test_header)
        expected_tbl_len = len(self.test_table)
        expected_cattype = 'LCOGT'

        hdr, tbl, cattype = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))
        self.assertEqual(expected_cattype, cattype)

    def test_catalog_read_hdr_keyword(self):
        expected_hdr_value = self.test_header['INSTRUME']

        hdr, tbl, cattype = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])

    def test_catalog_read_tbl_column(self):
        expected_tbl_value = 'X_IMAGE'
        expected_tbl_units = 'pixel'

        hdr, tbl, cattype = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_tbl_value, tbl.columns[1].name)
        self.assertEqual(expected_tbl_units, tbl.columns[1].unit)

    def test_catalog_read_xy(self):
        # X,Y CCD Co-ordinates of the last detection
        expected_x = 1067.9471
        expected_y = 1973.7445

        hdr, tbl, cattype = open_fits_catalog(self.test_filename)

        self.assertAlmostEqual(expected_x, tbl[-1]['X_IMAGE'], 4)
        self.assertAlmostEqual(expected_y, tbl[-1]['Y_IMAGE'], 4)

    def test_ldac_read_catalog(self):
        unexpected_value = {}

        hdr, tbl, cattype = open_fits_catalog(self.test_ldacfilename)
        self.assertNotEqual(unexpected_value, hdr)
        self.assertNotEqual(unexpected_value, tbl)
        self.assertNotEqual(unexpected_value, cattype)

    def test_ldac_catalog_read_length(self):
        expected_hdr_len = 352
        expected_tbl_len = len(self.test_ldactable)
        expected_cattype = 'FITS_LDAC'

        hdr, tbl, cattype = open_fits_catalog(self.test_ldacfilename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))
        self.assertEqual(expected_cattype, cattype)

    def test_ldac_catalog_header(self):
        outpath = os.path.join("photometrics", "tests")
        expected_header = fits.Header.fromfile(os.path.join(outpath, "test_header"), sep='\n', endcard=False, padding=False)

        hdr, tbl, cattype = open_fits_catalog(self.test_ldacfilename)

        for key in expected_header:
            self.assertEqual(expected_header[key], hdr[key],
                msg="Failure on %s (%s != %s)" % (key, expected_header[key], hdr[key]))

    def test_ldac_catalog_read_hdr_keyword(self):
        expected_hdr_value = 'kb76'

        hdr, tbl, cattype = open_fits_catalog(self.test_ldacfilename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])

    def test_catalog_read_tbl_column2(self):
        expected_tbl_value = 'XWIN_IMAGE'
        expected_tbl_units = 'pixel'

        hdr, tbl, cattype = open_fits_catalog(self.test_ldacfilename)

        self.assertEqual(expected_tbl_value, tbl.columns[1].name)
        self.assertEqual(expected_tbl_units, tbl.columns[1].unit)

    def test_ldac_catalog_read_xy(self):
        # X,Y CCD Co-ordinates of the last detection
        expected_x = 1758.0389801526617
        expected_y = 2024.9652134253395

        hdr, tbl, cattype = open_fits_catalog(self.test_ldacfilename)

        self.assertAlmostEqual(expected_x, tbl[-1]['XWIN_IMAGE'], self.precision)
        self.assertAlmostEqual(expected_y, tbl[-1]['YWIN_IMAGE'], self.precision)

    def test_ldac_catalog_bad(self):
        expected_value = {}
        expected_cattype = 'CORRUPT'

        try:
            hdr, tbl, cattype = open_fits_catalog(self.test_bad_ldacfilename)
        except OSError:
            self.fail("open_fits_catalog raised OSError unexpectedly")
        self.assertEqual(expected_value, hdr)
        self.assertEqual(expected_value, tbl)
        self.assertEqual(expected_cattype, cattype)

    def test_banzai_read_catalog(self):
        unexpected_value = {}

        hdr, tbl, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertNotEqual(unexpected_value, hdr)
        self.assertNotEqual(unexpected_value, tbl)
        self.assertNotEqual(unexpected_value, cattype)

    def test_banzai_catalog_read_length(self):
        expected_hdr_len = 278-23  # Total-compression keywords
        expected_tbl_len = len(self.test_banzaitable)
        expected_cattype = 'BANZAI'

        hdr, tbl, cattype = open_fits_catalog(self.test_banzaifilename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))
        self.assertEqual(expected_cattype, cattype)

    def test_banzai_catalog_read_hdr_keyword(self):
        expected_hdr_value = 'kb76'

        hdr, tbl, cattype = open_fits_catalog(self.test_banzaifilename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])

    def test_catalog_read_tbl_column3(self):
        expected_tbl_value = 'XWIN'
#        expected_tbl_units = 'pixel'   # No units in the new table (yet?)

        hdr, tbl, cattype = open_fits_catalog(self.test_banzaifilename)

        self.assertEqual(expected_tbl_value, tbl.columns[2].name)
#        self.assertEqual(expected_tbl_units, tbl.columns[2].unit)

    def test_banzai_catalog_read_xy(self):
        # X,Y CCD Co-ordinates of the last detection
        expected_x = 1990.0072393055439
        expected_y = 1219.86182435688

        hdr, tbl, cattype = open_fits_catalog(self.test_banzaifilename)

        self.assertAlmostEqual(expected_x, tbl[-1]['XWIN'], self.precision)
        self.assertAlmostEqual(expected_y, tbl[-1]['YWIN'], self.precision)

    def test_banzai_catalog_no_cat_HDU(self):
        # Copy file, funpack, remove CAT HDU
        test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        shutil.copy(self.test_banzaifilename, test_dir)
        test_banzaifilename = os.path.join(test_dir, os.path.basename(self.test_banzaifilename))
        status = funpack_fits_file(test_banzaifilename, all_hdus=True)
        self.assertEqual(0, status)
        test_banzaifilename = test_banzaifilename.replace('.fz', '')
        hdulist = fits.open(test_banzaifilename)
        del(hdulist['CAT'])
        errdata = np.zeros((hdulist[0].data.shape), dtype=np.float32)
        hdulist.append(fits.ImageHDU(errdata, name='ERR'))
        hdulist.writeto(test_banzaifilename, overwrite=True, checksum=True)

        expected_hdr_len = 278-24  # Total-compression keywords
        expected_tbl_len = {}
        expected_cattype = 'BANZAI'

        hdr, tbl, cattype = open_fits_catalog(test_banzaifilename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, tbl)
        self.assertEqual(expected_cattype, cattype)

        shutil.rmtree(test_dir)

    def test_uncomp_banzai_read_catalog(self):
        unexpected_value = {}

        hdr, tbl, cattype = open_fits_catalog(self.test_uncomp_banzaifilename)
        self.assertNotEqual(unexpected_value, hdr)
        self.assertNotEqual(unexpected_value, tbl)
        self.assertNotEqual(unexpected_value, cattype)

    def test_uncomp_banzai_catalog_read_length(self):
        expected_hdr_len = 251
        expected_tbl_len = len(self.test_uncomp_banzaitable)
        expected_cattype = 'BANZAI'

        hdr, tbl, cattype = open_fits_catalog(self.test_uncomp_banzaifilename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))
        self.assertEqual(expected_cattype, cattype)

    def test_uncomp_banzai_catalog_read_hdr_keyword(self):
        expected_hdr_value = 'kb76'

        hdr, tbl, cattype = open_fits_catalog(self.test_uncomp_banzaifilename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])

    def test_uncomp_banzai_catalog_read_tbl_column(self):
        expected_tbl_value = 'XWIN'
#        expected_tbl_units = 'pixel'   # No units in the new table (yet?)

        hdr, tbl, cattype = open_fits_catalog(self.test_uncomp_banzaifilename)

        self.assertEqual(expected_tbl_value, tbl.columns[2].name)
#        self.assertEqual(expected_tbl_units, tbl.columns[2].unit)

    def test_uncomp_banzai_catalog_read_xy(self):
        # X,Y CCD Co-ordinates of the last detection
        expected_x = 1990.0072393055439
        expected_y = 1219.86182435688

        hdr, tbl, cattype = open_fits_catalog(self.test_uncomp_banzaifilename)

        self.assertAlmostEqual(expected_x, tbl[-1]['XWIN'], self.precision)
        self.assertAlmostEqual(expected_y, tbl[-1]['YWIN'], self.precision)

    def test_photpipe_read_catalog(self):
        unexpected_value = {}

        hdr, tbl, cattype = open_fits_catalog(self.test_photpipefilename)
        self.assertNotEqual(unexpected_value, hdr)
        self.assertNotEqual(unexpected_value, tbl)
        self.assertNotEqual(unexpected_value, cattype)

    def test_photpipe_catalog_read_length(self):
        expected_hdr_len = 352
        expected_tbl_len = len(self.test_photpipe_ldactable)
        expected_cattype = 'PHOTPIPE_LDAC'

        hdr, tbl, cattype = open_fits_catalog(self.test_photpipefilename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))
        self.assertEqual(expected_cattype, cattype)

    def test_photpipe_catalog_read_hdr_keyword(self):
        expected_hdr_value = 'fa15'
        expected_hdr_value2 = '0.0003023852695117'


        hdr, tbl, cattype = open_fits_catalog(self.test_photpipefilename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])
        self.assertEqual(str, type(hdr['PV2_10']))
        self.assertEqual(expected_hdr_value2, hdr['PV2_10'])

    def test_swope_header(self):
        outpath = os.path.join("photometrics", "tests")
        expected_header = fits.Header.fromfile(os.path.join(outpath, "swope_test_header"), sep='\n', endcard=False, padding=False)
        expected_tbl = {}
        expected_cattype = 'SWOPE'

        hdr, tbl, cattype = open_fits_catalog(self.test_swopefilename)

        self.assertEqual(expected_cattype, cattype)
        self.assertEqual(expected_tbl, tbl)
        for key in expected_header:
            self.assertEqual(expected_header[key], hdr[key],
                msg="Failure on %s (%s != %s)" % (key, expected_header[key], hdr[key]))

class TestConvertValues(FITSUnitTest):

    def test_dateobs_conversion(self):

        expected_value = datetime(2016, 2, 22, 19, 16, 42, 664000)

        value = convert_value('obs_date' , self.test_header['DATE-OBS'])

        self.assertEqual(expected_value, value)

    def test_dateobs_no_frac_seconds(self):

        expected_value = datetime(2016, 2, 22, 19, 16, 42)

        value = convert_value('obs_date' , '2016-02-22T19:16:42')

        self.assertEqual(expected_value, value)

    def test_swope_block_start(self):

        expected_value = datetime(2022, 9, 24, 22, 30)

        value = convert_value('block_start', '24Sep2022')

        self.assertEqual(expected_value, value)

    def test_swope_block_end(self):

        expected_value = datetime(2022, 9, 25, 10, 30)

        value = convert_value('block_end', '24Sep2022')

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

        expected_value = 86.7366375  # conversion of 05:46:56.793 to decimal degrees

        value = convert_value('field_center_ra', '05:46:56.793')

        self.assertAlmostEqual(expected_value, value, 7)

    def test_dec_to_decimal_degrees(self):

        expected_value = -27.7043417  # conversion of -27:42:15.63 to decimal degrees

        value = convert_value('field_center_dec', '-27:42:15.63')

        self.assertAlmostEqual(expected_value, value, 7)

    def test_field_width(self):

        expected_value = '15.7846m'  # 2028 pixels x 0.467"/pixel converted to arcmin

        value = convert_value('field_width', (2028, 0.467))

        self.assertEqual(expected_value, value)

    def test_field_height(self):

        expected_value = '15.8624m'  # 2038 pixels x 0.467"/pixel converted to arcmin

        value = convert_value('field_height', (2038, 0.467))

        self.assertEqual(expected_value, value)

    def test_mu_threshold(self):

        expected_value = 34.158398

        value = convert_value('mu_threshold', (-5.4871593, 0.467))

        self.assertAlmostEqual(expected_value, value, 5)


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
                            'gain'          : self.test_header['GAIN'],
                            'saturation'    : self.test_header['SATURATE'],
                          }

        header, table, cattype = open_fits_catalog(self.test_filename)
        frame_header = get_catalog_header(header)

        self.assertEqual(expected_params, frame_header)

    def test_ldac_header(self):
        obs_date = datetime.strptime('2016-04-28T20:11:54.303', '%Y-%m-%dT%H:%M:%S.%f')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160428-0141-e00.fits',
                            'exptime'    : 115.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=115.0 / 2.0),
                            'field_center_ra'  : Angle('14:39:19.402', unit=u.hour).deg,
                            'field_center_dec' : Angle('-09:46:03.82', unit=u.deg).deg,
                            'field_width'   : '15.8779m',
                            'field_height'  : '15.9562m',
                            'pixel_scale'   : 0.46976,
                            'reduction_level' : 91,
                            'zeropoint'     : -99.0,
                            'zeropoint_err' : -99.0,
                            'zeropoint_src' : 'NOT_FIT(LCOGTCAL-V0.0.2-r8174)',
                            'fwhm'          : 2.886,
                            'astrometric_fit_rms'    : (0.13495+0.15453)/2.0,
                            'astrometric_fit_status' : 0,
                            'astrometric_fit_nstars' : 22,
                            'astrometric_catalog'    : 'UCAC4',
                            'wcs'                    : self.test_ldacwcs,
                            'aperture_radius_pixels' : 2.5,
                            'aperture_radius_arcsec' : 2.5*self.test_ldac_pixscale,
                          }
        expected_cattype = "FITS_LDAC"

        header, table, cattype = open_fits_catalog(self.test_ldacfilename)
        self.assertEqual(expected_cattype, cattype)
        frame_header = get_catalog_header(header, "FITS_LDAC")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : '2MASS',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header_gaiadr2(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : 'GAIA-DR2',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        # Modify PIPEVER to version number after switch to solving with GAIA-DR2
        header['PIPEVER'] = '0.20.0  '
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header_gaiadr2_devversion(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : 'GAIA-DR2',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        # Modify PIPEVER to version number after switch to solving with GAIA-DR2
        header['PIPEVER'] = '0.20.0dev1234'
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header_gaiadr2_version1_0(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : 'GAIA-DR2',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        # Modify PIPEVER to version number after switch to solving with GAIA-DR2
        header['PIPEVER'] = '1.0.42'
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header_bad_version(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : '2MASS',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        # Modify PIPEVER to version number after switch to solving with GAIA-DR2
        header['PIPEVER'] = 'wibble'
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header_blank_version(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : '2MASS',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        # Modify PIPEVER to blank bad version number
        header['PIPEVER'] = '      '
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header_bad_major_version(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : '2MASS',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        # Modify PIPEVER to blank bad version number
        header['PIPEVER'] = 'FOO.42.0'
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_banzai_header_bad_minor_version(self):
        obs_date = datetime.strptime('2016-06-06T22:48:14', '%Y-%m-%dT%H:%M:%S')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : 'kb76',
                            'filter'     : 'w',
                            'framename'  : 'cpt1m013-kb76-20160606-0396-e00.fits',
                            'exptime'    : 100.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=100.0 / 2.0),
                            'field_center_ra'  : Angle('18:11:47.017', unit=u.hour).deg,
                            'field_center_dec' : Angle('+01:16:54.21', unit=u.deg).deg,
                            'field_width'   : '15.8715m',
                            'field_height'  : '15.9497m',
                            'pixel_scale'   : 0.46957,
                            'fwhm'          : 2.110443536975972,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : '2MASS',
                            'astrometric_fit_rms'    : 0.3,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_banzaiwcs,
                            'reduction_level' : 91,
                            'gain'          : 1.0
                          }
        expected_cattype = "BANZAI"

        header, table, cattype = open_fits_catalog(self.test_banzaifilename)
        self.assertEqual(expected_cattype, cattype)
        # Modify PIPEVER to blank bad version number
        header['PIPEVER'] = '0.BAR.42    '
        frame_header = get_catalog_header(header, "BANZAI")

        self.compare_headers(expected_params, frame_header)

    def test_photpipe_header(self):
        obs_date = datetime.strptime('2022-07-31T03:38:08.692', '%Y-%m-%dT%H:%M:%S.%f')
        expected_params = { 'site_code'  : 'W85',
                            'instrument' : 'fa15',
                            'filter'     : 'w',
                            'framename'  : 'lsc1m005-fa15-20220730-0319-e00.fits',
                            'exptime'    : 124.973,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=124.973 / 2.0),
                            'field_center_ra'  : Angle('22:48:28.106', unit=u.hour).deg,
                            'field_center_dec' : Angle('-20:48:08.61', unit=u.deg).deg,
                            'field_width'   : '26.5953m',
                            'field_height'  : '26.5953m',
                            'pixel_scale'   : 0.38958,
                            'fwhm'          : -99,
                            'astrometric_fit_status' : 0,
                            'astrometric_catalog'    : 'GAIA',
                            'astrometric_fit_rms'    : 0.046402414945362,
                            'astrometric_fit_nstars' : -4,
                            'zeropoint'     : -99,
                            'zeropoint_err' : -99,
                            'zeropoint_src' : 'BANZAI',
                            'wcs'           : self.test_photpipe_ldacwcs,
                            'reduction_level' : 91,
                            'aperture_radius_pixels' : 11.47,
                            'aperture_radius_arcsec' : round(11.47*self.test_photpipe_ldac_pixscale, 4),
                          }
        expected_cattype = "PHOTPIPE_LDAC"

        header, table, cattype = open_fits_catalog(self.test_photpipefilename)
        self.assertEqual(expected_cattype, cattype)
        frame_header = get_catalog_header(header, cattype)

        self.assertEqual(len(expected_params), len(frame_header))
        self.compare_headers(expected_params, frame_header)


class FITSLDACToHeader(FITSUnitTest):

    def setUp(self):

        self.header_array = array(['SIMPLE  =                    T / conforms to FITS standard',
                                   'BITPIX  =                  -32 / array data type',
                                   'NAXIS   =                    2 / number of array dimensions',
                                   'NAXIS1  =                 2028',
                                   'NAXIS2  =                 2038',
                                   "COMMENT   FITS (Flexible Image Transport System) format is defined in 'Astronomy",
                                   "COMMENT   and Astrophysics', volume 376, page 359; bibcode: 2001A&A...376..359H"], 
                                   dtype='|U80')

    def test_nocomment(self):

        header = fits_ldac_to_header(self.header_array)

        self.assertEqual(header['BITPIX'], -32)
        self.assertEqual(header['NAXIS1'], 2028)
        self.assertEqual(header['NAXIS2'], 2038)

    def test_comments(self):

        self.header_array[2] = 'NAXIS1  =                 2028 / length of data axis 1'
        self.header_array[3] = 'NAXIS2  =                 2038 / length of data axis 2'

        header = fits_ldac_to_header(self.header_array)

        self.assertEqual(header['BITPIX'], -32)
        self.assertEqual(header['NAXIS1'], 2028)
        self.assertEqual(header['NAXIS2'], 2038)


class FITSSubsetCatalogTable(FITSUnitTest):

    def test_dimensions(self):
        expected_rows = 360
        expected_columns = 15

        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
        new_table = subset_catalog_table(self.test_table, tbl_mapping)

        self.assertEqual(expected_rows, len(new_table))
        self.assertEqual(expected_columns, len(new_table.colnames))

    def test_ldac_dimensions(self):
        expected_rows = 974
        expected_columns = 15

        hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
        new_table = subset_catalog_table(self.test_ldactable, tbl_mapping)

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
                                   'flux_max' : 486.95441,
                                   'threshold' : 43.438805,
                                 })

        catalog_items = get_catalog_items_old(self.test_header, self.table_firstitem)

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
                                   'flux_max' : 9418.0869,
                                   'threshold' : 43.438805,
                                 })

        catalog_items = get_catalog_items_old(self.test_header, self.table_lastitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_reject_item_flags24(self):

        expected_catalog = self.basic_table

        catalog_items = get_catalog_items_old(self.test_header, self.table_item_flags24)

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
                                   'obs_sky_bkgd' : 741.20977783,
                                   'flags' : 24,
                                   'flux_max' : 2913.0918,
                                   'threshold' : 43.438805,
                                 })

        catalog_items = get_catalog_items_old(self.test_header, self.table_item_flags24, flag_filter=24)

        self.compare_tables(expected_catalog, catalog_items, 9)

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
                                   'flux_max' : 486.95441,
                                   'threshold' : 43.438805,
                                 })

        header_items = {'zeropoint' : -99}
        catalog_items = get_catalog_items_old(header_items, self.table_firstitem)

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
                                   'flux_max' : 486.95441,
                                   'threshold' : 43.438805,
                                 })

        catalog_items = get_catalog_items_old(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_first_item_with_no_zeropoint(self):

        header_items = {'zerowibble' : -99}
        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
                                   'ccd_y' :  18.61132812,
                                   'major_axis'  : 1.87925231,
                                   'minor_axis'  : 1.74675643,
                                   'ccd_pa'      : -79.38792419,
                                   'obs_ra'  : 86.868051829832439,
                                   'obs_dec' : -27.575127242664802,
                                   'obs_ra_err'  : 7.464116913258858e-06,
                                   'obs_dec_err' : 7.516842315248245e-06,
                                   'obs_mag'      : -2.5*log10(11228.246),
                                   'obs_mag_err'  : 0.037939535221954708,
                                   'obs_sky_bkgd' : 746.41577148,
                                   'flags' : 0,
                                   'flux_max' : 486.95441,
                                   'threshold' : 43.438805,
                                 })

        catalog_items = get_catalog_items_old(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_ldac_first_item(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 1375.7452509015964,
                                   'ccd_y' :  42.12366067399433,
                                   'major_axis'  : 1.88223171,
                                   'minor_axis'  : 1.73628092,
                                   'ccd_pa'      : 7.76751757,
                                   'obs_ra'  :  219.7877046646191,
                                   'obs_dec' : -9.6401399241501036,
                                   'obs_ra_err'  : 8.92232262319e-06,
                                   'obs_dec_err' : 8.12455029148e-06,
                                   'obs_mag'      : -2.5*log10(206447.5625) + 00.00,
                                   'obs_mag_err'  : 0.0034573016162758306,
                                   'obs_sky_bkgd' : 343.17666626,
                                   'flags' : 0,
                                   'flux_max' : 5177.54296875,
                                   'threshold' : 29.552521897228782 # Old version using SECPIX: 29.2062811208271
                                 })

        header, table, cattype = open_fits_catalog(self.test_ldacfilename)
        header_items = get_catalog_header(header, cattype)
        catalog_items = get_catalog_items_old(header_items, self.ldac_table_firstitem, "FITS_LDAC")
        self.compare_tables(expected_catalog, catalog_items, 4)


class TestExtractCatalog(FITSUnitTest):

    def setUp(self):
        super(TestExtractCatalog, self).setUp()
        self.temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        shutil.copy(os.path.abspath(self.test_bad_ldacfilename), self.temp_dir)
        self.test_bad_ldacfilename = os.path.join(self.temp_dir, os.path.basename(self.test_bad_ldacfilename))
        self.remove = True
        self.debug_print = False

        self.expected_hdrtbl = None
        self.maxDiff = None

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.chmod(file_to_rm, stat.S_IWUSR)
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.temp_dir)
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print:
                    print("Removed", self.temp_dir)
            except OSError:
                print("Error removing temporary test directory", self.temp_dir)
        else:
            print("Temporary test directory=", self.temp_dir)

    def test_bad_ldac_dontremove_default(self):

        header, table = extract_catalog(self.test_bad_ldacfilename, 'BANZAI_LDAC')

        self.assertTrue(os.path.exists(self.test_bad_ldacfilename))
        self.assertEqual(self.expected_hdrtbl, header)
        self.assertEqual(self.expected_hdrtbl, table)

    def test_bad_ldac_dontremove(self):

        header, table = extract_catalog(self.test_bad_ldacfilename, 'BANZAI_LDAC', remove=False)

        self.assertTrue(os.path.exists(self.test_bad_ldacfilename))
        self.assertEqual(self.expected_hdrtbl, header)
        self.assertEqual(self.expected_hdrtbl, table)

    def test_bad_ldac_remove_bad_perms(self):

        os.chmod(self.test_bad_ldacfilename, 0o000)
        header, table = extract_catalog(self.test_bad_ldacfilename, 'BANZAI_LDAC', remove=True)

        self.assertTrue(os.path.exists(self.test_bad_ldacfilename))
        self.assertEqual(self.expected_hdrtbl, header)
        self.assertEqual(self.expected_hdrtbl, table)

    def test_bad_ldac_remove(self):

        header, table = extract_catalog(self.test_bad_ldacfilename, 'BANZAI_LDAC', remove=True)

        self.assertFalse(os.path.exists(self.test_bad_ldacfilename))
        self.assertEqual(self.expected_hdrtbl, header)
        self.assertEqual(self.expected_hdrtbl, table)

    def test_good_ldac_remove_on(self):

        expected_hdr = {'astrometric_catalog': 'UCAC4',
                       'astrometric_fit_nstars': 22,
                       'astrometric_fit_rms': 0.14473999999999998,
                       'astrometric_fit_status': 0,
                       'exptime': 115.0,
                       'field_center_dec': -9.767727777777779,
                       'field_center_ra': 219.83084166666666,
                       'field_height': '15.9562m',
                       'field_width': '15.8779m',
                       'filter': 'w',
                       'framename': 'cpt1m013-kb76-20160428-0141-e00.fits',
                       'fwhm': 2.886,
                       'instrument': 'kb76',
                       'obs_date': datetime(2016, 4, 28, 20, 11, 54, 303000),
                       'obs_midpoint': datetime(2016, 4, 28, 20, 12, 51, 803000),
                       'pixel_scale': 0.46976,
                       'site_code': 'K92',
                       'reduction_level' : 91,
                       'zeropoint': -99.0,
                       'zeropoint_err': -99.0,
                       'zeropoint_src': 'NOT_FIT(LCOGTCAL-V0.0.2-r8174)',
                       'wcs' : self.test_ldacwcs,
                       'aperture_radius_pixels' : 2.5,
                       'aperture_radius_arcsec' : round(2.5*self.test_ldac_pixscale, 4)}

        shutil.copy(os.path.abspath(self.test_ldacfilename), self.temp_dir)
        test_ldacfilename = os.path.join(self.temp_dir, os.path.basename(self.test_ldacfilename))
        header, table = extract_catalog(test_ldacfilename, 'FITS_LDAC', remove=True)

        self.assertTrue(os.path.exists(test_ldacfilename))
        self.compare_headers(expected_hdr, header)

        self.assertEqual(883, len(table))

    def test_good_ldac(self):

        expected_hdr = {'astrometric_catalog': 'UCAC4',
                       'astrometric_fit_nstars': 22,
                       'astrometric_fit_rms': 0.14473999999999998,
                       'astrometric_fit_status': 0,
                       'exptime': 115.0,
                       'field_center_dec': -9.767727777777779,
                       'field_center_ra': 219.83084166666666,
                       'field_height': '15.9562m',
                       'field_width': '15.8779m',
                       'filter': 'w',
                       'framename': 'cpt1m013-kb76-20160428-0141-e00.fits',
                       'fwhm': 2.886,
                       'instrument': 'kb76',
                       'obs_date': datetime(2016, 4, 28, 20, 11, 54, 303000),
                       'obs_midpoint': datetime(2016, 4, 28, 20, 12, 51, 803000),
                       'pixel_scale': 0.46976,
                       'site_code': 'K92',
                       'reduction_level' : 91,
                       'zeropoint': -99.0,
                       'zeropoint_err': -99.0,
                       'zeropoint_src': 'NOT_FIT(LCOGTCAL-V0.0.2-r8174)',
                       'wcs' : self.test_ldacwcs,
                       'aperture_radius_pixels' : 2.5,
                       'aperture_radius_arcsec' : round(2.5*self.test_ldac_pixscale, 4)}

        shutil.copy(os.path.abspath(self.test_ldacfilename), self.temp_dir)
        test_ldacfilename = os.path.join(self.temp_dir, os.path.basename(self.test_ldacfilename))
        header, table = extract_catalog(test_ldacfilename)

        self.assertTrue(os.path.exists(test_ldacfilename))
        self.compare_headers(expected_hdr, header)

        self.assertEqual(883, len(table))

    def test_photpipe_ldac(self):

        expected_hdr = {'astrometric_catalog': 'GAIA',
                       'astrometric_fit_nstars': -4,
                       'astrometric_fit_rms': 0.046402414945362,
                       'astrometric_fit_status': 0,
                       'exptime': 124.973,
                       'field_center_dec': -20.80239166666667,
                       'field_center_ra': 342.1171083333333,
                       'field_height': '26.5953m',
                       'field_width': '26.5953m',
                       'filter': 'w',
                       'framename': 'lsc1m005-fa15-20220730-0319-e00.fits',
                       'fwhm': 3.335374522705078,
                       'instrument': 'fa15',
                       'obs_date': datetime(2022, 7, 31,  3, 38,  8, 692000),
                       'obs_midpoint': datetime(2022, 7, 31,  3, 39, 11, 178500),
                       'pixel_scale': 0.38958,
                       'site_code': 'W85',
                       'reduction_level' : 91,
                       'zeropoint': -99.0,
                       'zeropoint_err': -99.0,
                       'zeropoint_src': 'BANZAI',
                       'wcs' : self.test_photpipe_ldacwcs,
                       'aperture_radius_pixels' : 11.47,
                       'aperture_radius_arcsec' : round(11.47*self.test_photpipe_ldac_pixscale, 4)}

        shutil.copy(os.path.abspath(self.test_photpipefilename), self.temp_dir)
        test_photpipefilename = os.path.join(self.temp_dir, os.path.basename(self.test_photpipefilename))
        header, table = extract_catalog(test_photpipefilename)

        self.assertTrue(os.path.exists(test_photpipefilename))
        self.compare_headers(expected_hdr, header)

        self.assertEqual(651, len(table))


class TestRemoveCorruptCatalog(FITSUnitTest):

    def setUp(self):
        super(TestRemoveCorruptCatalog, self).setUp()
        self.temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        shutil.copy(os.path.abspath(self.test_bad_ldacfilename), self.temp_dir)
        self.test_bad_ldacfilename = os.path.join(self.temp_dir, os.path.basename(self.test_bad_ldacfilename))

        frame_params = { 'filename' : os.path.basename(self.test_bad_ldacfilename),
                         'midpoint' : datetime(2020, 12, 3, 1, 30, 0),
                         'frametype' : Frame.BANZAI_LDAC_CATALOG
                       }
        self.frame, created = Frame.objects.get_or_create(**frame_params)
        self.expected_hdrtbl = None

        self.remove = True
        self.debug_print = False
        self.maxDiff = None

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.chmod(file_to_rm, stat.S_IWUSR)
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.temp_dir)
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print:
                    print("Removed", self.temp_dir)
            except OSError:
                print("Error removing temporary test directory", self.temp_dir)
        else:
            print("Temporary test directory=", self.temp_dir)

    def test_single_catalog(self):
        expected_num_removed = 1

        self.assertEqual(1, Frame.objects.count())

        removed, num_removed = remove_corrupt_catalog(self.test_bad_ldacfilename)

        self.assertTrue(removed)
        self.assertEqual(0, Frame.objects.count())
        self.assertEqual(expected_num_removed, num_removed)

    def test_single_catalog_disk_not_found(self):
        expected_num_removed = 1

        frames = Frame.objects.all()
        frame = frames[0]
        frame.filename = 'elp1m006-fa07-20201203-0225-e92_ldac.fits'
        frame.save()

        self.assertEqual(1, frames.count())
        removed, num_removed = remove_corrupt_catalog(os.path.join(self.temp_dir, frame.filename))

        self.assertFalse(removed)
        self.assertEqual(0, Frame.objects.count())
        self.assertEqual(expected_num_removed, num_removed)

    def test_multiple_catalogs_disk_not_found(self):
        expected_num_removed = 2

        frames = Frame.objects.all()
        frame = frames[0]
        frame.filename = 'elp1m006-fa07-20201203-0225-e91_ldac.fits'
        frame.save()

        frame.pk = None
        frame.filename = 'elp1m006-fa07-20201203-0225-e92_ldac.fits'
        frame.save()
        frames = Frame.objects.all()

        self.assertEqual(2, frames.count())
        removed, num_removed = remove_corrupt_catalog(os.path.join(self.temp_dir, frame.filename))

        self.assertFalse(removed)
        self.assertEqual(0, Frame.objects.count())
        self.assertEqual(expected_num_removed, num_removed)

    def test_multiple_catalogs_existing_frame(self):
        expected_num_removed = 2

        frames = Frame.objects.all()
        frame = frames[0]
        frame.filename = 'elp1m006-fa07-20201203-0225-e91.fits'
        frame.frametype = Frame.BANZAI_RED_FRAMETYPE
        frame.save()

        frame.pk = None
        frame.filename = 'elp1m006-fa07-20201203-0225-e91_ldac.fits'
        frame.frametype = Frame.BANZAI_LDAC_CATALOG
        frame.save()

        frame.pk = None
        frame.filename = 'elp1m006-fa07-20201203-0225-e92_ldac.fits'
        frame.frametype = Frame.BANZAI_LDAC_CATALOG
        frame.save()

        frames = Frame.objects.all()
        self.assertEqual(3, frames.count())
        removed, num_removed = remove_corrupt_catalog(os.path.join(self.temp_dir, frame.filename))

        self.assertFalse(removed)
        self.assertEqual(1, Frame.objects.count())
        self.assertEqual(expected_num_removed, num_removed)


class TestUpdateLDACCatalogWCS(FITSUnitTest):

    def setUp(self):
        super(TestUpdateLDACCatalogWCS, self).setUp()
        self.new_test_ldacfilename = self.test_ldacfilename + '.new'
        if os.path.exists(self.new_test_ldacfilename):
            os.unlink(self.new_test_ldacfilename)

    def tearDown(self):
        remove = True
        if os.path.exists(self.new_test_ldacfilename) and remove:
            os.unlink(self.new_test_ldacfilename)

    def test_bad_image_file(self):
        test_file = os.path.join('photometrics', 'tests', '__init__.py')

        expected_status = -1

        status = update_ldac_catalog_wcs(test_file, test_file, False)

        self.assertEqual(expected_status, status)

    def test_bad_image_wcs(self):
        test_file = os.path.join('photometrics', 'tests', 'example-sbig-e10.fits')

        expected_status = -2

        status = update_ldac_catalog_wcs(test_file, test_file, False)

        self.assertEqual(expected_status, status)

    def test_bad_catalog(self):
        test_fits_file = os.path.join('photometrics', 'tests', 'example-good_wcs.fits')
        test_file = os.path.join('photometrics', 'tests', 'example-sbig-e10.fits')

        expected_status = -3

        status = update_ldac_catalog_wcs(test_fits_file, test_file, False)

        self.assertEqual(expected_status, status)

    def test_null_update(self):
        test_fits_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example-good_wcs.fits'))

        expected_status = 0

        status = update_ldac_catalog_wcs(test_fits_file, self.test_ldacfilename, False)

        self.assertEqual(expected_status, status)
        self.assertTrue(os.path.exists(self.test_ldacfilename + '.new'))


class TestDetermineFilenames(TestCase):

    def test_catalog_to_image(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e90.fits'

        filename = determine_filenames('cpt1m013-kb76-20160222-0110-e90_cat.fits')

        self.assertEqual(expected_product, filename)

    def test_ql_catalog_to_image(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e10.fits'

        filename = determine_filenames('cpt1m013-kb76-20160222-0110-e10_cat.fits')

        self.assertEqual(expected_product, filename)

    def test_catalog_to_image_with_path(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e10.fits'

        product = os.path.join('photometrics', 'tests', 'cpt1m013-kb76-20160222-0110-e10_cat.fits')
        filename = determine_filenames(product)

        self.assertEqual(expected_product, filename)

    def test_image_to_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e90_cat.fits'

        filename = determine_filenames('cpt1m013-kb76-20160222-0110-e90.fits')

        self.assertEqual(expected_product, filename)

    def test_ql_image_to_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e10_cat.fits'

        filename = determine_filenames('cpt1m013-kb76-20160222-0110-e10.fits')

        self.assertEqual(expected_product, filename)

    def test_catalog_wrong_format(self):

        expected_product = None

        filename = determine_filenames('oracdr_test_catalog.fits')

        self.assertEqual(expected_product, filename)

    def test_banzai_image_to_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e91.fits'

        filename = determine_filenames('cpt1m013-kb76-20160222-0110-e91.fits')

        self.assertEqual(expected_product, filename)

    def test_banzai_ql_image_to_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e11.fits'

        filename = determine_filenames('cpt1m013-kb76-20160222-0110-e11.fits')

        self.assertEqual(expected_product, filename)


class TestIncrementRedLevel(TestCase):

    def test_quicklook_image(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e11.fits'
        product = 'cpt1m013-kb76-20160222-0110-e10.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_quicklook_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e11_cat.fits'
        product = 'cpt1m013-kb76-20160222-0110-e10_cat.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_finalred_image(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e91.fits'
        product = 'cpt1m013-kb76-20160222-0110-e90.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_finalred_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e91_cat.fits'
        product = 'cpt1m013-kb76-20160222-0110-e90_cat.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_curtisred_image(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e92.fits'
        product = 'cpt1m013-kb76-20160222-0110-e91.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_curtisred_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e92_cat.fits'
        product = 'cpt1m013-kb76-20160222-0110-e91_cat.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_finalred_ldac_catalog(self):

        expected_product = 'cpt1m013-kb76-20160222-0110-e91_ldac.fits'
        product = 'cpt1m013-kb76-20160222-0110-e90_ldac.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_semiraw_ldac_catalog(self):

        expected_product = 'oracdr_test_e09_ldac.fits'
        product = 'oracdr_test_e08_ldac.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)

    def test_maxvalue_image(self):

        expected_product = 'lsc0m4990kb29-20160420-0099-e99.fits'
        product = 'lsc0m4990kb29-20160420-0099-e99.fits'

        filename = increment_red_level(product)

        self.assertEqual(expected_product, filename)


class ExternalCodeUnitTest(TestCase):

    def __init__(self, *args, **kwargs):
        super(ExternalCodeUnitTest, self).__init__(*args, **kwargs)
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.debug_print = False

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)
        else:
            print("NOT removing temporary test directory", self.test_dir)

class UpdateFrameZeropointTest(FITSUnitTest):

    def setUp(self):

        # Create test body
        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body_with_provname, created = Body.objects.get_or_create(**params)

        # Create test proposal
        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test block
        sblock_params = {
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_CPT-20150420',
                         'block_start' : '2017-03-08 05:05:00',
                         'block_end'   : '2017-03-08 05:22:36',
                         'tracking_number' : '0000358587',
                         'active'   : False
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'LSC',
                         'body'     : self.body_with_provname,
                         'superblock' : self.test_sblock,
                         'block_start' : '2017-03-08 05:05:00',
                         'block_end'   : '2017-03-08 05:22:36',
                         'request_number' : '0001358587',
                         'num_exposures' : 6,
                         'exp_length' : 120.0,
                         'active'   : False
                       }
        self.test_block = Block.objects.create(**block_params)

        self.test_header = { 'astrometric_catalog': '2MASS',
                        'astrometric_fit_nstars': -4,
                        'astrometric_fit_rms': 0.3,
                        'astrometric_fit_status': 0,
                        'exptime': 120.0,
                        'field_center_dec': -28.85420305555556,
                        'field_center_ra': 131.64724583333333,
                        'field_height': '26.5940m',
                        'field_width': '26.5940m',
                        'filter': 'w',
                        'framename': 'lsc1m005-fl15-20170307-0121-e00.fits',
                        'fwhm': 1.908032083525876,
                        'instrument': 'fl15',
                        'obs_date': datetime(2017, 3, 8, 5, 5, 40, 100000),
                        'obs_midpoint': datetime(2017, 3, 8, 5, 6, 40, 100000),
                        'pixel_scale': 0.38956,
                        'reduction_level': 91,
                        'site_code': 'W85',
                        'zeropoint': 29.6113857745,
                        'zeropoint_err': 0.0414642608048,
                        'zeropoint_src': 'N/A'
                      }

        # Create test frame
        frame_params = {    'sitecode': 'W85',
                            'instrument': 'fl15',
                            'filter': 'w',
                            'filename': 'lsc1m005-fl15-20170307-0121-e91.fits',
                            'exptime': 120.0,
                            'midpoint': datetime(2017, 3, 8, 5, 6, 40),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 1.9080,
                            'frametype': 91,
                            'rms_of_fit': None,
                            'nstars_in_fit': None,
                            'astrometric_catalog': ' ',
                            'photometric_catalog': ' '
                        }

        self.test_frame1, created = Frame.objects.get_or_create(**frame_params)

        frame_params = {    'sitecode': 'W85',
                            'instrument': 'fl15',
                            'filter': 'w',
                            'filename': 'lsc1m005-fl15-20170307-0121-e91_ldac.fits',
                            'exptime': 120.0,
                            'midpoint': datetime(2017, 3, 8, 5, 6, 40),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 1.9080,
                            'frametype': 6,
                            'rms_of_fit': None,
                            'nstars_in_fit': None,
                            'astrometric_catalog': ' ',
                            'photometric_catalog': ' '
                        }

        self.test_frame2, created = Frame.objects.get_or_create(**frame_params)

    def test_update_SINGLE_frame_zeropoint(self):

        ast_cat_name = "2MASS"
        phot_cat_name = "UCAC4"
        fits_file = 'lsc1m005-fl15-20170307-0121-e91.fits'

        frame = update_frame_zeropoint(self.test_header, ast_cat_name, phot_cat_name, frame_filename=fits_file, frame_type=self.test_frame1.frametype)

        self.assertEqual(frame.zeropoint, 29.6113857745)
        self.assertEqual(frame.zeropoint_err, 0.0414642608048)
        self.assertEqual(frame.rms_of_fit, 0.3)
        self.assertEqual(frame.nstars_in_fit, -4)
        self.assertEqual(frame.astrometric_catalog, '2MASS')
        self.assertEqual(frame.photometric_catalog, 'UCAC4')

    def test_update_BANZAI_LDAC_frame_zeropoint(self):

        ast_cat_name = "2MASS"
        phot_cat_name = "UCAC4"
        fits_file = 'lsc1m005-fl15-20170307-0121-e91_ldac.fits'

        frame = update_frame_zeropoint(self.test_header, ast_cat_name, phot_cat_name, frame_filename=fits_file, frame_type=self.test_frame2.frametype)

        self.assertEqual(frame.zeropoint, 29.6113857745)
        self.assertEqual(frame.zeropoint_err, 0.0414642608048)
        self.assertEqual(frame.rms_of_fit, 0.3)
        self.assertEqual(frame.nstars_in_fit, -4)
        self.assertEqual(frame.astrometric_catalog, '2MASS')
        self.assertEqual(frame.photometric_catalog, 'UCAC4')


class MakeSEXTFileTest(FITSUnitTest):

    def setUp(self):

        # Hand-rolled WCS for pickling testing
        self.naxis_header = {'NAXIS1' : 4096, 'NAXIS2' : 4096, 'NAXIS' : 2}
        self.w = WCS(self.naxis_header)

        frame_params = {    'sitecode': 'V37',
                            'instrument': 'fl05',
                            'filter': 'w',
                            'filename': 'elp1m008-fl05-20160225-0100-e91.fits',
                            'exptime': 125.0,
                            'midpoint': datetime(2016, 2, 26, 3, 58, 46, 189000),
                            'block': None,
                            'zeropoint': 29.6113857745,
                            'zeropoint_err': 0.0414642608048,
                            'fwhm': 3.246,
                            'frametype': 0,
                            'rms_of_fit': None,
                            'nstars_in_fit': 10.0,
                            'wcs': self.w
                        }

        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

        source_params = {   'frame': self.test_frame,
                            'obs_x': 2165.8260536,
                            'obs_y': 57.1152786081,
                            'obs_ra': 163.864883508,
                            'obs_dec': 39.0624181436,
                            'obs_mag': 21.4522571564,
                            'err_obs_ra': 0.0000143653990456,
                            'err_obs_dec': 0.0000414534439506,
                            'err_obs_mag': 0.0147576071322,
                            'background': 1712.08544922,
                            'major_axis': 1.71870410442,
                            'minor_axis': 1.58122706413,
                            'position_angle': -74.1212539673,
                            'ellipticity': 0.0799887776375,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 126.969825745,
                            'threshold': 59.2340202332
                        }
        self.test_cat_src, created = CatalogSources.objects.get_or_create(**source_params)

        frame_params = {    'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'cpt1m013-kb76-20160505-0205-e11.fits',
                            'exptime': 60.0,
                            'midpoint': datetime(2016, 5, 5, 20, 2, 29),
                            'block': None,
                            'zeropoint': 27.7305864552,
                            'zeropoint_err': 0.0776317342309,
                            'fwhm': 2.825,
                            'frametype': 0,
                            'rms_of_fit': None,
                            'nstars_in_fit': 3.0,
                            'wcs': self.w
                        }

        self.test_frame_2, created = Frame.objects.get_or_create(**frame_params)

        source_params = {   'frame': self.test_frame_2,
                            'obs_x': 886.244640655,
                            'obs_y': 18.2107121645,
                            'obs_ra': 218.143035602,
                            'obs_dec': 9.89449095608,
                            'obs_mag': 16.2081203461,
                            'err_obs_ra': 0.0000039612496427,
                            'err_obs_dec': 0.0000041685561005,
                            'err_obs_mag': 0.00291323265992,
                            'background': 169.387756348,
                            'major_axis': 1.67034721375,
                            'minor_axis': 1.67034721375,
                            'position_angle': -77.6206283569,
                            'ellipticity': 0.0477138161659,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 1086.3104248,
                            'threshold': 29.7845497131
                        }
        self.test_cat_src_2, created = CatalogSources.objects.get_or_create(**source_params)

        source_params = {   'frame': self.test_frame_2,
                            'obs_x': 886.244640655,
                            'obs_y': 4078.2107121645,
                            'obs_ra': 218.143035602,
                            'obs_dec': 9.89449095608,
                            'obs_mag': 16.2081203461,
                            'err_obs_ra': 0.0000039612496427,
                            'err_obs_dec': 0.0000041685561005,
                            'err_obs_mag': 0.00291323265992,
                            'background': 169.387756348,
                            'major_axis': 1.67034721375,
                            'minor_axis': 1.67034721375,
                            'position_angle': -77.6206283569,
                            'ellipticity': 0.0477138161659,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 1086.3104248,
                            'threshold': 29.7845497131
                        }
        self.test_cat_src_3, created = CatalogSources.objects.get_or_create(**source_params)

        source_params = {   'frame': self.test_frame_2,
                            'obs_x': 4086.244640655,
                            'obs_y': 178.2107121645,
                            'obs_ra': 218.143035602,
                            'obs_dec': 9.89449095608,
                            'obs_mag': 16.2081203461,
                            'err_obs_ra': 0.0000039612496427,
                            'err_obs_dec': 0.0000041685561005,
                            'err_obs_mag': 0.00291323265992,
                            'background': 169.387756348,
                            'major_axis': 1.67034721375,
                            'minor_axis': 1.67034721375,
                            'position_angle': -77.6206283569,
                            'ellipticity': 0.0477138161659,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 1086.3104248,
                            'threshold': 29.7845497131
                        }
        self.test_cat_src_4, created = CatalogSources.objects.get_or_create(**source_params)

        source_params = {   'frame': self.test_frame_2,
                            'obs_x': 708.002750723,
                            'obs_y': 1960.00075651,
                            'obs_ra': 218.164206491,
                            'obs_dec': 9.64089784636,
                            'obs_mag': 18.4867630005,
                            'err_obs_ra': 0.0000016381997233,
                            'err_obs_dec': 0.0000016349852456,
                            'err_obs_mag': 0.00311457808129,
                            'background': 43.1037330627,
                            'major_axis': 0.651648461819,
                            'minor_axis': 0.648237645626,
                            'position_angle': 7.21760177612,
                            'ellipticity': 0.00523412227631,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 4937.96289062,
                            'threshold': 28.2903823853
                        }
        self.test_cat_src_5, created = CatalogSources.objects.get_or_create(**source_params)

        # Hand-rolled WCS for pickling testing
        self.naxis_header2 = {'NAXIS1' : 1500, 'NAXIS2' : 2000, 'NAXIS' : 2}
        self.w2 = WCS(self.naxis_header2)

        frame_params = {    'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'ldac_test_catalog.fits',
                            'exptime': 115.0,
                            'midpoint': datetime(2016, 4, 28, 20, 11, 54),
                            'block': None,
                            'zeropoint': 27.7305864552,
                            'zeropoint_err': 0.0776317342309,
                            'fwhm': 2.886,
                            'frametype': 0,
                            'rms_of_fit': None,
                            'nstars_in_fit': 3.0,
                            'wcs': self.w2
                        }

        self.test_frame_3, created = Frame.objects.get_or_create(**frame_params)

        source_params = {   'frame': self.test_frame_3,
                            'obs_x': 886.244640655,
                            'obs_y': 18.2107121645,
                            'obs_ra': 218.143035602,
                            'obs_dec': 9.89449095608,
                            'obs_mag': 16.2081203461,
                            'err_obs_ra': 0.0000039612496427,
                            'err_obs_dec': 0.0000041685561005,
                            'err_obs_mag': 0.00291323265992,
                            'background': 169.387756348,
                            'major_axis': 1.67034721375,
                            'minor_axis': 1.67034721375,
                            'position_angle': -77.6206283569,
                            'ellipticity': 0.0477138161659,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 1086.3104248,
                            'threshold': 29.7845497131
                        }
        self.test_cat_src_6, created = CatalogSources.objects.get_or_create(**source_params)

        source_params = {   'frame': self.test_frame_3,
                            'obs_x': 886.244640655,
                            'obs_y': 1078.2107121645,
                            'obs_ra': 218.143035602,
                            'obs_dec': 9.89449095608,
                            'obs_mag': 16.2081203461,
                            'err_obs_ra': 0.0000039612496427,
                            'err_obs_dec': 0.0000041685561005,
                            'err_obs_mag': 0.00291323265992,
                            'background': 169.387756348,
                            'major_axis': 1.67034721375,
                            'minor_axis': 1.67034721375,
                            'position_angle': -77.6206283569,
                            'ellipticity': 0.0477138161659,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 1086.3104248,
                            'threshold': 29.7845497131
                        }
        self.test_cat_src_7, created = CatalogSources.objects.get_or_create(**source_params)

        source_params = {   'frame': self.test_frame_3,
                            'obs_x': 1086.244640655,
                            'obs_y': 178.2107121645,
                            'obs_ra': 218.143035602,
                            'obs_dec': 9.89449095608,
                            'obs_mag': 16.2081203461,
                            'err_obs_ra': 0.0000039612496427,
                            'err_obs_dec': 0.0000041685561005,
                            'err_obs_mag': 0.00291323265992,
                            'background': 169.387756348,
                            'major_axis': 1.67034721375,
                            'minor_axis': 1.67034721375,
                            'position_angle': -77.6206283569,
                            'ellipticity': 0.0477138161659,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 1086.3104248,
                            'threshold': 29.7845497131
                        }
        self.test_cat_src_8, created = CatalogSources.objects.get_or_create(**source_params)

        source_params = {   'frame': self.test_frame_3,
                            'obs_x': 708.002750723,
                            'obs_y': 1960.00075651,
                            'obs_ra': 218.164206491,
                            'obs_dec': 9.64089784636,
                            'obs_mag': 18.4867630005,
                            'err_obs_ra': 0.0000016381997233,
                            'err_obs_dec': 0.0000016349852456,
                            'err_obs_mag': 0.00311457808129,
                            'background': 43.1037330627,
                            'major_axis': 0.651648461819,
                            'minor_axis': 0.648237645626,
                            'position_angle': 7.21760177612,
                            'ellipticity': 0.00523412227631,
                            'aperture_size': 3,
                            'flags': 0,
                            'flux_max': 4937.96289062,
                            'threshold': 28.2903823853
                        }
        self.test_cat_src_9, created = CatalogSources.objects.get_or_create(**source_params)

    def test_dictionary_creation(self):

        test_dict = {   'number': 1,
                        'obs_x': 2165.826,
                        'obs_y': 57.115,
                        'obs_mag': 21.4523,
                        'theta': -74.1,
                        'elongation': 1.087,
                        'fwhm': 3.30,
                        'flags': 0,
                        'deltamu': 0.828,
                        'flux': 1835.1,
                        'area': 8.5378,
                        'ra': 163.86488,
                        'dec': 39.06242
                    }

        num_iter = 1

        sext_params = make_sext_dict(self.test_cat_src, num_iter)

        self.assertEqual(sext_params['number'], test_dict['number'])
        self.assertAlmostEqual(sext_params['obs_x'], test_dict['obs_x'], 3)
        self.assertAlmostEqual(sext_params['obs_y'], test_dict['obs_y'], 3)
        self.assertAlmostEqual(sext_params['obs_mag'], test_dict['obs_mag'], 4)
        self.assertAlmostEqual(sext_params['theta'], test_dict['theta'], 1)
        self.assertAlmostEqual(sext_params['elongation'], test_dict['elongation'], 3)
        self.assertAlmostEqual(sext_params['fwhm'], test_dict['fwhm'], 2)
        self.assertEqual(sext_params['flags'], test_dict['flags'])
        self.assertAlmostEqual(sext_params['deltamu'], test_dict['deltamu'], 3)
        self.assertAlmostEqual(sext_params['flux'], test_dict['flux'], 1)
        self.assertAlmostEqual(sext_params['area'], test_dict['area'], 4)
        self.assertAlmostEqual(sext_params['ra'], test_dict['ra'], 5)
        self.assertAlmostEqual(sext_params['dec'], test_dict['dec'], 5)

    def test_line_creation(self):

        test_dict = {   'number': 1,
                        'obs_x': 106.118,
                        'obs_y': 18.611,
                        'obs_mag': 17.1818,
                        'theta': -79.4,
                        'elongation': 1.076,
                        'fwhm': 3.63,
                        'flags': 0,
                        'deltamu': 2.624,
                        'flux': 11228.2,
                        'area': 10.3126,
                        'ra': 86.86805,
                        'dec': -27.57513
                    }

        test_line = '         1    106.118     18.611  17.1818  -79.4       1.076      3.63   0  2.62        11228.2    10  86.86805 -27.57513'

        sext_line = make_sext_file_line(test_dict)

        self.assertEqual(sext_line, test_line)

    def test_multiple_sources_sext_dict_trimmed(self):

        test_dict_first = { 'number': 1,
                            'obs_x': 708.003,
                            'obs_y': 1960.001,
                            'obs_mag': 18.4868,
                            'theta': 7.218,
                            'elongation': 1.005,
                            'fwhm': 1.30,
                            'flags': 0,
                            'deltamu': 5.605,
                            'flux': 4983.4,
                            'area': 1.3271,
                            'ra': 218.16421,
                            'dec': 9.64090
                         }

        cat_ldacfilename = os.path.join(os.path.sep, 'tmp', 'tmp_neox_2016GS2', 'cpt1m013-kb76-20160505-0205-e11_ldac.fits')
        catalog_type = 'FITS_LDAC'

        sext_dict_list, fits_filename = make_sext_dict_list(cat_ldacfilename, catalog_type)

        self.assertEqual(len(sext_dict_list), 1)

        self.assertEqual(sext_dict_list[0]['number'], test_dict_first['number'])
        self.assertAlmostEqual(sext_dict_list[0]['obs_x'], test_dict_first['obs_x'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['obs_y'], test_dict_first['obs_y'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['obs_mag'], test_dict_first['obs_mag'], 4)
        self.assertAlmostEqual(sext_dict_list[0]['theta'], test_dict_first['theta'], 1)
        self.assertAlmostEqual(sext_dict_list[0]['elongation'], test_dict_first['elongation'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['fwhm'], test_dict_first['fwhm'], 2)
        self.assertEqual(sext_dict_list[0]['flags'], test_dict_first['flags'])
        self.assertAlmostEqual(sext_dict_list[0]['deltamu'], test_dict_first['deltamu'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['flux'], test_dict_first['flux'], 1)
        self.assertAlmostEqual(sext_dict_list[0]['area'], test_dict_first['area'], 4)
        self.assertAlmostEqual(sext_dict_list[0]['ra'], test_dict_first['ra'], 5)
        self.assertAlmostEqual(sext_dict_list[0]['dec'], test_dict_first['dec'], 5)

    def test_multiple_sources_sext_dict_untrimmed(self):

        test_dict_first = { 'number': 1,
                            'obs_x': 886.245,
                            'obs_y': 18.211,
                            'obs_mag': 16.2081,
                            'theta': -77.62,
                            'elongation': 1.00,
                            'fwhm': 3.34,
                            'flags': 0,
                            'deltamu': 3.9049,
                            'flux': 40643.1,
                            'area': 8.7652,
                            'ra': 218.14304,
                            'dec': 9.89449
                          }

        test_dict_middle1 = { 'number': 2,
                              'obs_x': 886.245,
                              'obs_y': 1078.211,
                              'obs_mag': 16.2081,
                              'theta': -77.62,
                              'elongation': 1.00,
                              'fwhm': 3.34,
                              'flags': 0,
                              'deltamu': 3.9049,
                              'flux': 40643.1,
                              'area': 8.7652,
                              'ra': 218.14304,
                              'dec': 9.89449
                           }

        test_dict_middle2 = { 'number': 3,
                              'obs_x': 1086.245,
                              'obs_y': 178.211,
                              'obs_mag': 16.2081,
                              'theta': -77.62,
                              'elongation': 1.00,
                              'fwhm': 3.34,
                              'flags': 0,
                              'deltamu': 3.9049,
                              'flux': 40643.1,
                              'area': 8.7652,
                              'ra': 218.14304,
                              'dec': 9.89449
                           }

        test_dict_last = {  'number': 4,
                            'obs_x': 708.003,
                            'obs_y': 1960.001,
                            'obs_mag': 18.4868,
                            'theta': 7.218,
                            'elongation': 1.005,
                            'fwhm': 1.30,
                            'flags': 0,
                            'deltamu': 5.605,
                            'flux': 4983.4,
                            'area': 1.3271,
                            'ra': 218.16421,
                            'dec': 9.64090
                         }

        cat_ldacfilename = os.path.join(os.path.sep, 'photometrics', 'tests', 'ldac_test_catalog.fits')
        catalog_type = 'FITS_LDAC'

        sext_dict_list, fits_filename = make_sext_dict_list(cat_ldacfilename, catalog_type)

        self.assertEqual(len(sext_dict_list), 4)

        self.assertEqual(sext_dict_list[0]['number'], test_dict_first['number'])
        self.assertAlmostEqual(sext_dict_list[0]['obs_x'], test_dict_first['obs_x'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['obs_y'], test_dict_first['obs_y'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['obs_mag'], test_dict_first['obs_mag'], 4)
        self.assertAlmostEqual(sext_dict_list[0]['theta'], test_dict_first['theta'], 1)
        self.assertAlmostEqual(sext_dict_list[0]['elongation'], test_dict_first['elongation'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['fwhm'], test_dict_first['fwhm'], 2)
        self.assertEqual(sext_dict_list[0]['flags'], test_dict_first['flags'])
        self.assertAlmostEqual(sext_dict_list[0]['deltamu'], test_dict_first['deltamu'], 3)
        self.assertAlmostEqual(sext_dict_list[0]['flux'], test_dict_first['flux'], 1)
        self.assertAlmostEqual(sext_dict_list[0]['area'], test_dict_first['area'], 4)
        self.assertAlmostEqual(sext_dict_list[0]['ra'], test_dict_first['ra'], 5)
        self.assertAlmostEqual(sext_dict_list[0]['dec'], test_dict_first['dec'], 5)

        self.assertEqual(sext_dict_list[1]['number'], test_dict_middle1['number'])
        self.assertAlmostEqual(sext_dict_list[1]['obs_x'], test_dict_middle1['obs_x'], 3)
        self.assertAlmostEqual(sext_dict_list[1]['obs_y'], test_dict_middle1['obs_y'], 3)
        self.assertAlmostEqual(sext_dict_list[1]['obs_mag'], test_dict_middle1['obs_mag'], 4)
        self.assertAlmostEqual(sext_dict_list[1]['theta'], test_dict_middle1['theta'], 1)
        self.assertAlmostEqual(sext_dict_list[1]['elongation'], test_dict_middle1['elongation'], 3)
        self.assertAlmostEqual(sext_dict_list[1]['fwhm'], test_dict_middle1['fwhm'], 2)
        self.assertEqual(sext_dict_list[1]['flags'], test_dict_middle1['flags'])
        self.assertAlmostEqual(sext_dict_list[1]['deltamu'], test_dict_middle1['deltamu'], 3)
        self.assertAlmostEqual(sext_dict_list[1]['flux'], test_dict_middle1['flux'], 1)
        self.assertAlmostEqual(sext_dict_list[1]['area'], test_dict_middle1['area'], 4)
        self.assertAlmostEqual(sext_dict_list[1]['ra'], test_dict_middle1['ra'], 5)
        self.assertAlmostEqual(sext_dict_list[1]['dec'], test_dict_middle1['dec'], 5)

        self.assertEqual(sext_dict_list[2]['number'], test_dict_middle2['number'])
        self.assertAlmostEqual(sext_dict_list[2]['obs_x'], test_dict_middle2['obs_x'], 3)
        self.assertAlmostEqual(sext_dict_list[2]['obs_y'], test_dict_middle2['obs_y'], 3)
        self.assertAlmostEqual(sext_dict_list[2]['obs_mag'], test_dict_middle2['obs_mag'], 4)
        self.assertAlmostEqual(sext_dict_list[2]['theta'], test_dict_middle2['theta'], 1)
        self.assertAlmostEqual(sext_dict_list[2]['elongation'], test_dict_middle2['elongation'], 3)
        self.assertAlmostEqual(sext_dict_list[2]['fwhm'], test_dict_middle2['fwhm'], 2)
        self.assertEqual(sext_dict_list[2]['flags'], test_dict_middle2['flags'])
        self.assertAlmostEqual(sext_dict_list[2]['deltamu'], test_dict_middle2['deltamu'], 3)
        self.assertAlmostEqual(sext_dict_list[2]['flux'], test_dict_middle2['flux'], 1)
        self.assertAlmostEqual(sext_dict_list[2]['area'], test_dict_middle2['area'], 4)
        self.assertAlmostEqual(sext_dict_list[2]['ra'], test_dict_middle2['ra'], 5)
        self.assertAlmostEqual(sext_dict_list[2]['dec'], test_dict_middle2['dec'], 5)

        self.assertEqual(sext_dict_list[-1]['number'], test_dict_last['number'])
        self.assertAlmostEqual(sext_dict_list[-1]['obs_x'], test_dict_last['obs_x'], 3)
        self.assertAlmostEqual(sext_dict_list[-1]['obs_y'], test_dict_last['obs_y'], 3)
        self.assertAlmostEqual(sext_dict_list[-1]['obs_mag'], test_dict_last['obs_mag'], 4)
        self.assertAlmostEqual(sext_dict_list[-1]['theta'], test_dict_last['theta'], 1)
        self.assertAlmostEqual(sext_dict_list[-1]['elongation'], test_dict_last['elongation'], 3)
        self.assertAlmostEqual(sext_dict_list[-1]['fwhm'], test_dict_last['fwhm'], 2)
        self.assertEqual(sext_dict_list[-1]['flags'], test_dict_last['flags'])
        self.assertAlmostEqual(sext_dict_list[-1]['deltamu'], test_dict_last['deltamu'], 3)
        self.assertAlmostEqual(sext_dict_list[-1]['flux'], test_dict_last['flux'], 1)
        self.assertAlmostEqual(sext_dict_list[-1]['area'], test_dict_last['area'], 4)
        self.assertAlmostEqual(sext_dict_list[-1]['ra'], test_dict_last['ra'], 5)
        self.assertAlmostEqual(sext_dict_list[-1]['dec'], test_dict_last['dec'], 5)

    def test_make_sext_line_list(self):

        test_dict_list = [{  'number': 405,
                            'obs_x': 5.959,
                            'obs_y': 800.006,
                            'obs_mag': 20.7902,
                            'theta': -89.1,
                            'elongation': 1.070,
                            'fwhm': 0.63,
                            'flags': 0,
                            'deltamu': 2.82,
                            'flux': 597.2,
                            'area': 0,
                            'ra': 218.25847,
                            'dec': 9.79143
                          },
                          {  'number': 456,
                            'obs_x': 2017.041,
                            'obs_y': 655.951,
                            'obs_mag': 20.1782,
                            'theta': 80.4,
                            'elongation': 1.006,
                            'fwhm': 1.30,
                            'flags': 0,
                            'deltamu': 3.91,
                            'flux': 1049.4,
                            'area': 1,
                            'ra': 217.99272,
                            'dec': 9.81255
                          }]

        test_line_list = ['       405      5.959    800.006  20.7902  -89.1       1.070      0.63   0  2.82          597.2     0 218.25847   9.79143', '       456   2017.041    655.951  20.1782   80.4       1.006      1.30   0  3.91         1049.4     1 217.99272   9.81255']

        sext_line_list = make_sext_line_list(test_dict_list)

        self.assertEqual(len(sext_line_list), 2)
        self.assertEqual(sext_line_list[0], test_line_list[0])
        self.assertEqual(sext_line_list[-1], test_line_list[1])


class TestDetermineImageForCatalog(TestCase):

    def setUp(self):
        pass

    def test_ql_ldac_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e11_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_ldac_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e91_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_ql_ldac_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e11_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_ldac_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e91_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_ql_cat_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e11_cat.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_cat_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e91_cat.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_ql_cat_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e11_cat.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_cat_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e91_cat.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_ql_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e11.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e91.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_ql_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e11.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e91.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_ql_gaia_ldac_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e12_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_gaia_ldac_no_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = 'lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('lsc1m005-fl15-20171109-0139-e92_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_ql_gaia_ldac_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e11.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e11.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e12_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)

    def test_red_gaia_ldac_path(self):
        expected_filename = 'lsc1m005-fl15-20171109-0139-e91.fits'
        expected_filepath = '/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e91.fits'

        fits_filename, fits_filepath = determine_image_for_catalog('/apophis/eng/rocks/20171109/lsc1m005-fl15-20171109-0139-e92_ldac.fits')

        self.assertEqual(expected_filename, fits_filename)
        self.assertEqual(expected_filepath, fits_filepath)


class TestSanitizeObjectName(TestCase):

    def test_none(self):
        expected_obj_name = None

        object_name = sanitize_object_name(None)

        self.assertEqual(expected_obj_name, object_name)

    def test_nonstring(self):
        expected_obj_name = None

        object_name = sanitize_object_name(12345)

        self.assertEqual(expected_obj_name, object_name)

    def test_numpy_string(self):
        expected_obj_name = '2016WW2'

        name_array = array(['(2016 WW2)'])
        object_name = sanitize_object_name(name_array[0])

        self.assertEqual(expected_obj_name, object_name)

    def test_regular_asteroid(self):
        expected_obj_name = '12345'

        object_name = sanitize_object_name('12345')

        self.assertEqual(expected_obj_name, object_name)

    def test_asteroid_with_space(self):
        expected_obj_name = '2020BR10'

        object_name = sanitize_object_name('2020 BR10')

        self.assertEqual(expected_obj_name, object_name)

    def test_asteroid_with_two_desigs(self):
        expected_obj_name = '85989_1999JD6'

        object_name = sanitize_object_name('85989 (1999 JD6)')

        self.assertEqual(expected_obj_name, object_name)

    def test_asteroid_with_two_desigs_and_extra_space(self):
        expected_obj_name = '85989_1999JD6'

        object_name = sanitize_object_name('85989  (1999 JD6)')

        self.assertEqual(expected_obj_name, object_name)

    def test_asteroid_with_brackets(self):
        expected_obj_name = '123456'

        object_name = sanitize_object_name('(123456)')

        self.assertEqual(expected_obj_name, object_name)

    def test_comet_periodic(self):
        expected_obj_name = '46P'

        object_name = sanitize_object_name('46/P')

        self.assertEqual(expected_obj_name, object_name)

    def test_comet_nonperiodic(self):
        expected_obj_name = 'C_2019Y4'

        object_name = sanitize_object_name('C/2019 Y4')

        self.assertEqual(expected_obj_name, object_name)

    def test_comet_whitespace(self):
        expected_obj_name = 'C_2019Y4'

        object_name = sanitize_object_name('  C/2019 Y4 ')

        self.assertEqual(expected_obj_name, object_name)

    def test_unnumbered_comet_with_longname(self):
        name = 'Machholz-Fujikawa-Iwamo (C/2018 V1'
        expected_name = 'Machholz_Fujikawa_Iwamo_C_2018V1'

        new_name = sanitize_object_name(name)

        self.assertEqual(expected_name, new_name)

    def test_staticsource_names(self):
        expected_obj_names = ['agk81d266', 'bd25d4655', 'cd_34d241', 'eg21', 'feige110', 'g138_31', 'g191_b2b', 'gd108', 'grw70d5824',
            'hd49798', 'hd60753', 'hilt600', 'hr153', 'hr1544', 'hz2', 'hz21', 'lb227', 'lds749b', 'ltt1020', 'ngc7293']

        statsrc_names = ['AGK+81d266', 'BD+25d4655', 'CD-34d241', 'EG21', 'Feige110', 'G138-31', 'G191-B2B', 'GD108', 'GRW+70d5824',
            'HD 49798', 'HD60753', 'HILT600', 'HR153', 'HR1544', 'HZ2', 'HZ21', 'LB227', 'LDS749B', 'LTT1020', 'NGC 7293']

        for i,stat_src in enumerate(statsrc_names):
            object_name = sanitize_object_name(stat_src)
            self.assertEqual(expected_obj_names[i], object_name.lower())

    def test_horizons_names(self):
        expected_obj_names = ['2016WW2', '5604_1992FE', 'PANSTARRS_C_2017D5', '66391_Moshup_1999KW4', 'PANSTARRS_C_2015ER61',
            'Lemmon_C_2017S7', 'ATLAS_C_2017M4', '11Parthenope', '328P_LONEOS_Tucker', 'A_2018V3', '155P_Shoemaker3',
            '29P_Schwassmann_Wachmann1', 'Groeller_P_2019V2', 'Pruyne_P_2019X1', '4581_Asclepius_1989FC', '289P_Blanpain',
            '469219_Kamo`oalewa_2016HO3', '2100_Ra_Shalom_1978RA', 'NEOWISE_C_2016U1']

        horizons_names = ['(2016 WW2)',
                          '5604 (1992 FE)',
                          'PANSTARRS (C/2017 D5)',
                          '66391 Moshup (1999 KW4)',
                          'PANSTARRS (C/2015 ER61)',
                          'Lemmon (C/2017 S7)',
                          'ATLAS (C/2017 M4)',
                          '11 Parthenope',
                          '328P/LONEOS-Tucker',
                          'A/2018 V3',
                          '155P/Shoemaker 3',
                          '29P/Schwassmann-Wachmann 1',
                          'Groeller (P/2019 V2)',
                          'Pruyne (P/2019 X1)',
                          '4581 Asclepius (1989 FC)',
                          '289P/Blanpain',
                          '469219 Kamo`oalewa (2016 HO3)',
                          '2100 Ra-Shalom (1978 RA)',
                          'NEOWISE (C/2016 U1)']

        for i, name in enumerate(horizons_names):
            object_name = sanitize_object_name(name)
            self.assertEqual(expected_obj_names[i], object_name)


class TestMakeObjectDirectory(ExternalCodeUnitTest):

    def __init__(self, *args, **kwargs):
        super(TestMakeObjectDirectory, self).__init__(*args, **kwargs)

        self.test_filepath = os.path.join(self.test_dir, 'lsc1m004-fa03-20200212-0088-e91.fits')

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.rmdir(file_to_rm)
            except OSError:
                print("Error removing directories in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)

    def test_regular_object_noblock(self):
        object_name = 'N999q0q'
        expected_object_dir = os.path.join(self.test_dir, object_name)

        object_dir = make_object_directory(self.test_filepath, object_name, '')

        self.assertEqual(expected_object_dir, object_dir)

    def test_regular_object(self):
        object_name = 'N999q0q'
        block_id = '12345'
        expected_object_dir = os.path.join(self.test_dir, object_name+'_'+block_id)

        object_dir = make_object_directory(self.test_filepath, object_name, block_id)

        self.assertEqual(expected_object_dir, object_dir)

    def test_object_with_space(self):
        object_name = '2020 BR10'
        block_id = '12345'
        expected_object_dir = os.path.join(self.test_dir, object_name.replace(' ', '')+'_'+block_id)

        object_dir = make_object_directory(self.test_filepath, object_name, block_id)

        self.assertEqual(expected_object_dir, object_dir)

    def test_comet(self):
        object_name = 'C/2019 Y4'
        block_id = '12345'
        expected_object_dir = os.path.join(self.test_dir, object_name.replace(' ', '').replace('/', '_')+'_'+block_id)

        object_dir = make_object_directory(self.test_filepath, object_name, block_id)

        self.assertEqual(expected_object_dir, object_dir)


class TestFunpackFITSFile(ExternalCodeUnitTest):

    def setUp(self):
        #
        # setUp is called once before each test
        #
        super(TestFunpackFITSFile, self).setUp()

        self.testfits_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_fz_file = os.path.abspath(os.path.join(self.testfits_dir, 'banzai_test_frame.fits.fz'))
        shutil.copy(self.test_fz_file, self.test_dir)
        self.test_fz_file = os.path.abspath(os.path.join(self.test_dir, os.path.basename(self.test_fz_file)))

    def tearDown(self):
        #
        # tearDown is called once after each test
        #
        super(TestFunpackFITSFile, self).tearDown()

    def test_single_hdu(self):
        expected_name = self.test_fz_file.replace('.fz', '')
        expected_nhdu = 1

        funpack_fits_file(self.test_fz_file)

        self.assertTrue(os.path.exists(self.test_fz_file))
        self.assertTrue(os.path.exists(expected_name))

        hdulist = fits.open(expected_name)
        self.assertEqual(expected_nhdu, len(hdulist))

    def test_multihdu(self):
        expected_name = self.test_fz_file.replace('.fz', '')
        expected_nhdu = 3 # Should be 4 with additional ImageHDU but this example is old and has no ERR extension
        expected_hdu_types = [  'PrimaryHDU',
                                'BinTableHDU',
                                'ImageHDU',
                             ]
        expected_hdu_names = [  'SCI',
                                'CAT',
                                'BPM',
                             ]

        funpack_fits_file(self.test_fz_file, all_hdus=True)

        self.assertTrue(os.path.exists(self.test_fz_file))
        self.assertTrue(os.path.exists(expected_name))

        hdulist = fits.open(expected_name)
        self.assertEqual(expected_nhdu, len(hdulist))
        for index, hdu in enumerate(hdulist):
            hdu_type = hdu._summary()[2]
            self.assertEqual(expected_hdu_types[index], hdu_type, f"Mismatch in index {index}: {expected_hdu_types[index]} not equal to {hdu_type}")
            self.assertEqual(expected_hdu_names[index], hdu.name)


class TestDetermineFWHM(FITSUnitTest):

    def setUp(self):
        super(TestDetermineFWHM, self).setUp()

        self.test_table = Table(names=('major_axis', 'minor_axis', 'flags', 'fwhm'), dtype=('f4', 'f4', 'i2', 'f4'))
        self.test_table.add_row([2.0, 2.0, 0, 4])
        self.test_table.add_row([2.0, 2.0, 1, 4])
        self.test_table.add_row([1.75, 1.9, 0, 3.5])
        self.test_table.add_row([np.nan, np.nan, 0, np.nan])

        self.test_header = {'pixel_scale' : 0.389}

    def test_fwhm_column(self):
        expected_fwhm = 3.75 * self.test_header['pixel_scale']

        fwhm = determine_fwhm(self.test_header, self.test_table)

        assert_allclose(expected_fwhm, fwhm, rtol=self.rtol)

    def test_nofwhm_column(self):
        expected_fwhm = 4.5054073 * self.test_header['pixel_scale']

        del self.test_table['fwhm']

        fwhm = determine_fwhm(self.test_header, self.test_table)

        assert_allclose(expected_fwhm, fwhm, rtol=self.rtol)

    def test_nofwhm_or_majaxis_column(self):
        expected_fwhm = None

        del self.test_table['fwhm']
        del self.test_table['major_axis']

        fwhm = determine_fwhm(self.test_header, self.test_table)

        self.assertEqual(expected_fwhm, fwhm)

    def test_nofwhm_or_minaxis_column(self):
        expected_fwhm = None

        del self.test_table['fwhm']
        del self.test_table['minor_axis']

        fwhm = determine_fwhm(self.test_header, self.test_table)

        self.assertEqual(expected_fwhm, fwhm)

    def test_fwhm_photpipe(self):
        header, table = extract_catalog(self.test_photpipefilename)
        expected_fwhm = 3.335374522

        fwhm = determine_fwhm(header, table)

        assert_allclose(expected_fwhm, fwhm, rtol=self.rtol)

