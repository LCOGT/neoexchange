'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2018 LCO

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
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose

#Import module to test
from photometrics.spectroscopy_subs import *

class SpTypeToPicklesStd(TestCase):

    def test_F8V(self):

        expected_file = 'pickles_20.fits'
        standard_file = sptype_to_pickles_standard('F8V')

        self.assertEqual(expected_file, standard_file)

    def test_F8V_lowercase(self):

        expected_file = 'pickles_20.fits'
        standard_file = sptype_to_pickles_standard('f8v')

        self.assertEqual(expected_file, standard_file)

    def test_B5V(self):

        expected_file = 'pickles_6.fits'
        standard_file = sptype_to_pickles_standard('B5V')

        self.assertEqual(expected_file, standard_file)

    def test_B6V(self):

        expected_file = 'pickles_6.fits'
        standard_file = sptype_to_pickles_standard('B6V')

        self.assertEqual(expected_file, standard_file)

    def test_B7V(self):

        expected_file = 'pickles_6.fits'
        standard_file = sptype_to_pickles_standard('B7V')

        self.assertEqual(expected_file, standard_file)

    def test_M7V_nomatch(self):

        expected_file = None
        standard_file = sptype_to_pickles_standard('M7V')

        self.assertEqual(expected_file, standard_file)
