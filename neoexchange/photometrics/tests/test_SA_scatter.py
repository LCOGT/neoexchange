"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
from django.test import TestCase
from astropy.coordinates import SkyCoord, Galactic
from astropy import coordinates
from astropy import units as u
import numpy as np

#Import module to test
from photometrics.SA_scatter import *

class Test_readCoords(TestCase):
    def setUp(self):
        self.test_path = os.path.join(os.getcwd(), 'photometrics/data/Solar_Standards')
        self.test_lines = readFile(self.test_path)
            
    def test_readFile(self):
        expected_num_lines = 46
        
        coords = readCoords(self.test_lines)
        
        self.assertEqual(expected_num_lines, len(coords))
    
    def test_firstCoords(self):
        expected_coord = SkyCoord('01:53:18.0', '+00:22:25',unit=(u.hourangle, u.deg))
        
        coords = readCoords(self.test_lines)
        self.assertEqual(type(expected_coord),type(coords[0]))
        self.assertAlmostEqual(expected_coord.ra, coords[0].ra)
        self.assertAlmostEqual(expected_coord.dec, coords[0].dec)
            
    def test_firstLine(self):
        expected_coord = SkyCoord('01:53:18.0', '+00:22:25',unit=(u.hourangle, u.deg))
        test_lines = ['    Land (SA) 93-101     01:53:18.0  +00:22:25    9.7']
        coords = readCoords(test_lines)
        self.assertEqual(type(expected_coord),type(coords[0]))
        self.assertEqual(expected_coord.ra, coords[0].ra)
        self.assertEqual(expected_coord.dec, coords[0].dec)

class Test_Plotting(TestCase):
    def setUp(self):
        self.test_gal = Galactic(0*u.deg,0*u.deg).transform_to(coordinates.ICRS)
        
    def test_first_galcoord(self):
        expected_object = self.test_gal
        expected_coord_size = 360
        
        galcoords = genGalPlane()
        self.assertEqual(type(expected_object),type(galcoords))
        self.assertEqual(expected_object.ra,galcoords.ra[0])
        self.assertEqual(expected_object.dec,galcoords.dec[0])
        self.assertEqual(expected_coord_size,len(galcoords.ra))
    
        #How to test plotting?
