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

from astropy.table import Table

class ZeropointUnitTest(TestCase):

    def test_get_cat_ra_dec(self):
        #test getting a single ra, dec, and rmag out of the default PPMXL catalog
        
        cat_table = get_catalog_table(299.590, 35.201, "PPMXL")

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

#        rmag_first_source = cat_table['r2mag'][0]

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

#        expected_rmag_first_source = 14.32

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
#        self.assertEqual(expected_rmag_first_source, rmag_first_source)

    def test_no_cat(self):
        #test if no catalog input, use default catalog

        cat_table = get_catalog_table(299.590, 35.201)

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

#        rmag_first_source = cat_table['r2mag'][0]

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

#        expected_rmag_first_source = 14.32

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
#        self.assertEqual(expected_rmag_first_source, rmag_first_source)

    def test_get_cat_ra_dec_not_default(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, "UCAC4")

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

#        rmag_third_source = cat_table['rmag'][2]

        expected_ra_first_source = 299.29474599999998

        expected_dec_first_source = 34.973799999999997

#        expected_rmag_third_source = 12.642000198364258

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
#        self.assertEqual(expected_rmag_third_source, rmag_third_source)

    def test_get_cat_diff_rmag_limit(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, rmag_limit = "<=14.5")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

#        rmag_last_source = cat_table['r2mag'][-1]

        expected_ra_last_source = 299.82885099999999

        expected_dec_last_source = 34.998407

#        expected_rmag_last_source = 14.5

        self.assertEqual(expected_ra_last_source, ra_last_source)
        self.assertEqual(expected_dec_last_source, dec_last_source)
#        self.assertEqual(expected_rmag_last_source, rmag_last_source)

    def test_get_cat_diff_row_limit(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, set_row_limit = 40)

        ra_first_source = cat_table['_RAJ2000'][0]

        dec_first_source = cat_table['_DEJ2000'][0]

#        rmag_first_source = cat_table['r2mag'][0]

        expected_ra_first_source = 299.29136599999998

        expected_dec_first_source = 35.242404000000001

#        expected_rmag_first_source = 14.32

        self.assertEqual(expected_ra_first_source, ra_first_source)
        self.assertEqual(expected_dec_first_source, dec_first_source)
#        self.assertEqual(expected_rmag_first_source, rmag_first_source)

    def test_get_cat_diff_width(self):
        #test a catalog other than the default
        
        cat_table = get_catalog_table(299.590, 35.201, set_width = "30m")

        ra_last_source = cat_table['_RAJ2000'][-1]

        dec_last_source = cat_table['_DEJ2000'][-1]

#        rmag_last_source = cat_table['r2mag'][-1]

        expected_ra_last_source = 299.88443899999999

        expected_dec_last_source = 34.978456999999999

#        expected_rmag_last_source = 14.79

        self.assertEqual(expected_ra_last_source, ra_last_source)
        self.assertEqual(expected_dec_last_source, dec_last_source)
#        self.assertEqual(expected_rmag_last_source, rmag_last_source)

    def test_cross_match_PPMXL_UCAC4(self):
        #test with cat 1 as shorter PPMXL table values and cat 2 as longer UCAC4 table values

        table_cat_1_data = [(299.291366, 35.242404, 14.3199996948),
                            (299.304084, 35.201634, 13.8500003815),
                            (299.480004, 34.965488, 14.3800001144),
                            (299.308579, 35.165495, 14.8900003433),
                            (299.828851, 34.998407, 14.5),
                            (299.510143, 34.960303, 14.4499998093),
                            (299.709139, 35.218109, 12.7700004578),
                            (299.860871, 35.381474, 14.0799999237)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('_RAJ2000', '_DEJ2000', 'r2mag'), dtype=('f8', 'f8', 'e8'))

        table_cat_2_data = [(299.303973, 35.20152, 0.0),
                            (299.828851, 34.99841, 0.0),
                            (299.291455, 35.242368, 0.0),
                            (299.479984, 34.965502, 0.0),
                            (299.510127, 34.960327, 15.5469999313),
                            (299.308515, 35.165529, 15.0059995651),
                            (299.884478, 34.978454, 0.0),
                            (299.709162, 35.218112, 13.3520002365),
                            (299.860889, 35.381485, 14.9130001068)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'rmag'), dtype=('f8', 'f8', 'e8'))

        cross_match_table = cross_match(table_cat_1, table_cat_2)

        expected_cross_match_table_data = [(299.308579, 299.308515, 6.4015e-05, 35.165495, 35.165529, 3.3975e-05, 14.890625, 15.0078125, 0.1171875),
                                           (299.510143, 299.510127, 1.5974e-05, 34.960303, 34.960327, 2.4021e-05, 14.453125, 15.546875, 1.09375),
                                           (299.709139, 299.709162, 2.3007e-05, 35.218109, 35.218112, 2.9802e-06, 12.7734375, 13.3515625, 0.581999778748),
                                           (299.860871, 299.860889, 1.8001e-05, 35.381474, 35.381485, 1.1027e-05, 14.078125, 14.9140625, 0.833000183105)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag diff'), dtype=('f8', 'f8', 'e8', 'f8', 'f8', 'e8', 'f8', 'f8', 'f8'))

        self.assertEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3])

        self.assertEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3])

        self.assertEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0])
        self.assertEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1])
        self.assertEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2])
        self.assertEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3])

        self.assertEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3])

        self.assertEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3])

        self.assertEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0])
        self.assertEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1])
        self.assertEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2])
        self.assertEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3])

        self.assertEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3])

        self.assertEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3])

    def test_cross_match_UCAC4_PPMXL(self):
        #test with cat 1 as longer UCAC4 table values and cat 2  as shorter PPMXL table values to test cat reordering

        table_cat_1_data = [(299.303973, 35.20152, 0.0),
                            (299.828851, 34.99841, 0.0),
                            (299.291455, 35.242368, 0.0),
                            (299.479984, 34.965502, 0.0),
                            (299.510127, 34.960327, 15.5469999313),
                            (299.308515, 35.165529, 15.0059995651),
                            (299.884478, 34.978454, 0.0),
                            (299.709162, 35.218112, 13.3520002365),
                            (299.860889, 35.381485, 14.9130001068)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('_RAJ2000', '_DEJ2000', 'rmag'), dtype=('f8', 'f8', 'e8'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948),
                            (299.304084, 35.201634, 13.8500003815),
                            (299.480004, 34.965488, 14.3800001144),
                            (299.308579, 35.165495, 14.8900003433),
                            (299.828851, 34.998407, 14.5),
                            (299.510143, 34.960303, 14.4499998093),
                            (299.709139, 35.218109, 12.7700004578),
                            (299.860871, 35.381474, 14.0799999237)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'r2mag'), dtype=('f8', 'f8', 'e8'))

        cross_match_table = cross_match(table_cat_1, table_cat_2)

        expected_cross_match_table_data = [(299.308579, 299.308515, 6.4015e-05, 35.165495, 35.165529, 3.3975e-05, 14.890625, 15.0078125, 0.1171875),
                                           (299.510143, 299.510127, 1.5974e-05, 34.960303, 34.960327, 2.4021e-05, 14.453125, 15.546875, 1.09375),
                                           (299.709139, 299.709162, 2.3007e-05, 35.218109, 35.218112, 2.9802e-06, 12.7734375, 13.3515625, 0.581999778748),
                                           (299.860871, 299.860889, 1.8001e-05, 35.381474, 35.381485, 1.1027e-05, 14.078125, 14.9140625, 0.833000183105)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag diff'), dtype=('f8', 'f8', 'e8', 'f8', 'f8', 'e8', 'f8', 'f8', 'f8'))

        self.assertEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3])

        self.assertEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3])

        self.assertEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0])
        self.assertEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1])
        self.assertEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2])
        self.assertEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3])

        self.assertEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3])

        self.assertEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3])

        self.assertEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0])
        self.assertEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1])
        self.assertEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2])
        self.assertEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3])

        self.assertEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3])

        self.assertEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3])


    def test_cross_match_filtering(self):
        #test filtering of poor catalog cross matches

        table_cat_1_data = [(299.303973, 35.20152, 0.0),
                            (299.828851, 34.99841, 0.0),
                            (299.291455, 35.242368, 0.0),
                            (299.479984, 34.965502, 0.0),
                            (299.510127, 34.960327, 15.5469999313),
                            (299.308515, 35.165529, 15.0059995651),
                            (299.884478, 34.978454, 0.0),
                            (299.709162, 35.218112, 13.3520002365),
                            (299.860889, 35.381485, 14.9130001068),
                            (299.315295, 35.069564, 0.0),
                            (299.321592, 35.351089, 14.0190000534)]

        table_cat_1 = Table(rows=table_cat_1_data, names = ('_RAJ2000', '_DEJ2000', 'rmag'), dtype=('f8', 'f8', 'e8'))

        table_cat_2_data = [(299.291366, 35.242404, 14.3199996948),
                            (299.304084, 35.201634, 13.8500003815),
                            (299.480004, 34.965488, 14.3800001144),
                            (299.308579, 35.165495, 14.8900003433),
                            (299.828851, 34.998407, 14.5),
                            (299.510143, 34.960303, 14.4499998093),
                            (299.709139, 35.218109, 12.7700004578),
                            (299.860871, 35.381474, 14.0799999237),
                            (299.31235, 35.07259, 14.8500003815),
                            (299.362172, 35.351208, 14.2600002289)]

        table_cat_2 = Table(rows=table_cat_2_data, names = ('_RAJ2000', '_DEJ2000', 'r2mag'), dtype=('f8', 'f8', 'e8'))

        cross_match_table = cross_match(table_cat_1, table_cat_2)

        expected_cross_match_table_data = [(299.308579, 299.308515, 6.4015e-05, 35.165495, 35.165529, 3.3975e-05, 14.890625, 15.0078125, 0.1171875),
                                           (299.510143, 299.510127, 1.5974e-05, 34.960303, 34.960327, 2.4021e-05, 14.453125, 15.546875, 1.09375),
                                           (299.709139, 299.709162, 2.3007e-05, 35.218109, 35.218112, 2.9802e-06, 12.7734375, 13.3515625, 0.581999778748),
                                           (299.860871, 299.860889, 1.8001e-05, 35.381474, 35.381485, 1.1027e-05, 14.078125, 14.9140625, 0.833000183105)]

        expected_cross_match_table = Table(rows=expected_cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag diff'), dtype=('f8', 'f8', 'e8', 'f8', 'f8', 'e8', 'f8', 'f8', 'f8'))

        self.assertEqual(expected_cross_match_table['RA Cat 1'][0], cross_match_table['RA Cat 1'][0])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][1], cross_match_table['RA Cat 1'][1])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][2], cross_match_table['RA Cat 1'][2])
        self.assertEqual(expected_cross_match_table['RA Cat 1'][3], cross_match_table['RA Cat 1'][3])

        self.assertEqual(expected_cross_match_table['RA Cat 2'][0], cross_match_table['RA Cat 2'][0])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][1], cross_match_table['RA Cat 2'][1])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][2], cross_match_table['RA Cat 2'][2])
        self.assertEqual(expected_cross_match_table['RA Cat 2'][3], cross_match_table['RA Cat 2'][3])

        self.assertEqual(expected_cross_match_table['RA diff'][0], cross_match_table['RA diff'][0])
        self.assertEqual(expected_cross_match_table['RA diff'][1], cross_match_table['RA diff'][1])
        self.assertEqual(expected_cross_match_table['RA diff'][2], cross_match_table['RA diff'][2])
        self.assertEqual(expected_cross_match_table['RA diff'][3], cross_match_table['RA diff'][3])

        self.assertEqual(expected_cross_match_table['Dec Cat 1'][0], cross_match_table['Dec Cat 1'][0])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][1], cross_match_table['Dec Cat 1'][1])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][2], cross_match_table['Dec Cat 1'][2])
        self.assertEqual(expected_cross_match_table['Dec Cat 1'][3], cross_match_table['Dec Cat 1'][3])

        self.assertEqual(expected_cross_match_table['Dec Cat 2'][0], cross_match_table['Dec Cat 2'][0])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][1], cross_match_table['Dec Cat 2'][1])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][2], cross_match_table['Dec Cat 2'][2])
        self.assertEqual(expected_cross_match_table['Dec Cat 2'][3], cross_match_table['Dec Cat 2'][3])

        self.assertEqual(expected_cross_match_table['Dec diff'][0], cross_match_table['Dec diff'][0])
        self.assertEqual(expected_cross_match_table['Dec diff'][1], cross_match_table['Dec diff'][1])
        self.assertEqual(expected_cross_match_table['Dec diff'][2], cross_match_table['Dec diff'][2])
        self.assertEqual(expected_cross_match_table['Dec diff'][3], cross_match_table['Dec diff'][3])

        self.assertEqual(expected_cross_match_table['r mag Cat 1'][0], cross_match_table['r mag Cat 1'][0])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][1], cross_match_table['r mag Cat 1'][1])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][2], cross_match_table['r mag Cat 1'][2])
        self.assertEqual(expected_cross_match_table['r mag Cat 1'][3], cross_match_table['r mag Cat 1'][3])

        self.assertEqual(expected_cross_match_table['r mag Cat 2'][0], cross_match_table['r mag Cat 2'][0])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][1], cross_match_table['r mag Cat 2'][1])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][2], cross_match_table['r mag Cat 2'][2])
        self.assertEqual(expected_cross_match_table['r mag Cat 2'][3], cross_match_table['r mag Cat 2'][3])

    def test_get_zeropoint(self):
        #test zeropoint calculation

        cross_match_table_data = [(299.308579, 299.308515, 6.4015e-05, 35.165495, 35.165529, 3.3975e-05, 14.890625, 15.0078125, 0.1171875),
                                  (299.510143, 299.510127, 1.5974e-05, 34.960303, 34.960327, 2.4021e-05, 14.453125, 15.546875, 1.09375),
                                  (299.709139, 299.709162, 2.3007e-05, 35.218109, 35.218112, 2.9802e-06, 12.7734375, 13.3515625, 0.581999778748),
                                  (299.860871, 299.860889, 1.8001e-05, 35.381474, 35.381485, 1.1027e-05, 14.078125, 14.9140625, 0.833000183105),
                                  (299.480459, 299.480473, 1.4007e-05, 35.211664, 35.211664, 0.0, 14.1800003052, 14.2910003662, 0.111000061035),
                                  (299.497849, 299.497893, 4.3988e-05, 35.414674, 35.4147, 2.5988e-05, 13.5900001526, 13.6560001373, 0.0659999847412),
                                  (299.786581, 299.786549, 3.2008e-05, 35.349776, 35.349781, 5.0068e-06, 14.1000003815, 14.1780004501, 0.0780000686646),
                                  (299.759237, 299.75918, 5.6982e-05, 35.256782, 35.256786, 3.9935e-06, 13.0900001526, 14.3479995728, 1.25799942017),
                                  (299.789005, 299.788977, 2.8014e-05, 34.983303, 34.98333, 2.7001e-05, 14.5200004578, 13.795999527, 0.724000930786)]

        cross_match_table = Table(rows=cross_match_table_data, names = ('RA Cat 1', 'RA Cat 2', 'RA diff', 'Dec Cat 1', 'Dec Cat 2', 'Dec diff', 'r mag Cat 1', 'r mag Cat 2', 'r mag diff'), dtype=('f8', 'f8', 'e8', 'f8', 'f8', 'e8', 'f8', 'f8', 'f8'))

        avg_zeropoint, std_zeropoint, count = get_zeropoint(cross_match_table)

#        expected_avg_zeropoint = 0.54032643636108879
#        expected_avg_zeropoint = 0.45061731338497496
#        expected_avg_zeropoint = 0.19083747863775999
        expected_avg_zeropoint = 0.093046903610200002

#        expected_std_zeropoint = 0.4402728965426147
#        expected_std_zeropoint = 0.3816290222879874
#        expected_std_zeropoint = 0.19653140135977154
        expected_std_zeropoint = 0.02158140008063236

#        expected_count = 9
#        expected_count = 8
#        expected_count = 5
        expected_count = 4


        self.assertEqual(expected_avg_zeropoint, avg_zeropoint)
        self.assertEqual(expected_std_zeropoint, std_zeropoint)
        self.assertEqual(expected_count, count)

    def test_more(self):
        self.fail("write more tests")

    def test_vizier_down(self):
        self.fail("write test for no internet")

