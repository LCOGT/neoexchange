'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2017 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from django.test import TestCase

#Import module to test
from photometrics.photometry_subs import *

class TestTransformVmag(TestCase):

    def test_taxon_default_to_i(self):

        V = 20.0
        new_passband = 'i'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_to_i(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'Mean'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_uppercase_to_i(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'MEAN'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_lowercase_to_i(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'mean'

        expected_mag = V-0.39

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_bad(self):

        V = 20.0
        new_passband = 'i'
        taxonomy = 'foo'

        expected_mag = None

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_bad_passband(self):

        V = 20.0
        new_passband = 'U'
        taxonomy = 'mean'

        expected_mag = None

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_bad_uc_passband(self):

        V = 20.0
        new_passband = 'R'  # Bessell-R not the same as (SDSS/PS)-r
        taxonomy = 'mean'

        expected_mag = None

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_solar_to_i(self):

        V = 20.5
        new_passband = 'i'
        taxonomy = 'Solar'

        expected_mag = V-0.293

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_to_w(self):

        V = 19.0
        new_passband = 'w'
        taxonomy = 'Mean'

        expected_mag = V-0.16

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_solar_to_w(self):

        V = 16.25
        new_passband = 'w'
        taxonomy = 'Solar'

        expected_mag = V-0.114

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_mean_to_r(self):

        V = 19.1
        new_passband = 'r'
        taxonomy = 'MeAn'

        expected_mag = V-0.23

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_solar_to_r(self):

        V = 16.25
        new_passband = 'r'
        taxonomy = 'solaR'

        expected_mag = V-0.183

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Stype_to_r(self):

        V = 10
        new_passband = 'r'
        taxonomy = 'S'

        expected_mag = V-0.275

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Stype_to_i(self):

        V = 10
        new_passband = 'i'
        taxonomy = 'S'

        expected_mag = V-0.470

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Stype_to_w(self):

        V = 10
        new_passband = 'w'
        taxonomy = 'S'

        expected_mag = V-0.199

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Ctype_to_r(self):

        V = 10
        new_passband = 'r'
        taxonomy = 'C'

        expected_mag = V-0.194

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Ctype_to_i(self):

        V = 10
        new_passband = 'i'
        taxonomy = 'c'

        expected_mag = V-0.308

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Ctype_to_w(self):

        V = 10
        new_passband = 'w'
        taxonomy = 'C'

        expected_mag = V-0.120

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Xtype_to_r(self):

        V = 10
        new_passband = 'r'
        taxonomy = 'X'

        expected_mag = V-0.207

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Xtype_to_i(self):

        V = 10
        new_passband = 'i'
        taxonomy = 'x'

        expected_mag = V-0.367

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Xtype_to_w(self):

        V = 10
        new_passband = 'w'
        taxonomy = 'X'

        expected_mag = V-0.146

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Qtype_to_r(self):

        V = 15.1
        new_passband = 'r'
        taxonomy = 'Q'

        expected_mag = V-0.252

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Qtype_to_i(self):

        V = 12.5
        new_passband = 'i'
        taxonomy = 'q'

        expected_mag = V-0.379

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_Qtype_to_w(self):

        V = 14
        new_passband = 'w'
        taxonomy = 'Q'

        expected_mag = V-0.156

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_NEOtype_to_r(self):

        V = 15.1
        new_passband = 'r'
        taxonomy = 'NeO'

        expected_mag = V-0.213

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_NEOtype_to_i(self):

        V = 12.5
        new_passband = 'i'
        taxonomy = 'neo'

        expected_mag = V-0.356

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

    def test_taxon_NEOtype_to_w(self):

        V = 14
        new_passband = 'w'
        taxonomy = 'NEO'

        expected_mag = V-0.148

        new_mag = transform_Vmag(V, new_passband, taxonomy)

        self.assertEqual(expected_mag, new_mag)

class TestComputeFloydsSNR(TestCase):

    def setUp(self):

        self.ftn_zp = 25.3
        self.fts_zp = 23.1

        self.precision = 3

    def test_faint_ftn1(self):

        mag_i = 18.0
        exp_time = 100.0

        expected_snr = 42.0

        snr =  compute_floyds_snr(mag_i, self.ftn_zp)

        self.assertAlmostEqual(expected_snr, snr, self.precision)
