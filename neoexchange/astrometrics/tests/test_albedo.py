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

from datetime import datetime, timedelta
from django.test import TestCase

#Import module to test
from astrometrics.albedo import *

class TestAsteroidDiameter(TestCase):
    '''Unit tests for asteroid_diameter'''
    
    def no_magnitude(self):
        expected_diameter = 'Missing Magnitude'
        
        albedo = 0.3
        H_mag = None
        
        diameter = asteroid_diameter(albedo, H_mag)
        self.Equal(expected_diameter, diameter)
    
    def test_big_bright(self):
        expected_diameter = 375.0075
        
        albedo = 0.5
        H_mag = 18.5
        
        diameter = asteroid_diameter(albedo, H_mag)
        self.assertAlmostEqual(expected_diameter, diameter, 4)
        
        
    def test_small_shiny(self):
        expected_diameter = 83.6556       
        
        albedo = 0.4
        H_mag = 22.0
        
        diameter = asteroid_diameter(albedo, H_mag)
        self.assertAlmostEqual(expected_diameter, diameter, 4)
        
    def test_large_dim(self):
        expected_diameter = 4825.3073
        
        albedo = 0.1
        H_mag = 14.7
        
        diameter = asteroid_diameter(albedo, H_mag)
        self.assertAlmostEqual(expected_diameter, diameter, 4)
        
    def test_tiny_not_shiny(self):
        expected_diameter = 57.8755
        
        albedo = 0.04
        H_mag = 25.3
        
        diameter = asteroid_diameter(albedo, H_mag)
        self.assertAlmostEqual(expected_diameter, diameter, 4)
        
    def test_negative_albedo(self):
        expected_diameter = 'You cannot have a negative albedo!'
        
        albedo = -0.3
        H_mag = 17.1
        diameter = asteroid_diameter(albedo, H_mag)
        self.assertEqual(expected_diameter, diameter)


class TestAsteroidAlbedoDistribution(TestCase):
    '''Unit test for albedo_distribution'''
    
    def test_large_albedo(self):
        expected_distribution = 0.009661
        
        albedo = 0.65
        distribution = albedo_distribution(a = albedo)
        self.assertAlmostEqual(expected_distribution, distribution, 4)
    
    def test_small_albedo(self):
        expected_distribution = 5.651816
        
        albedo = 0.04
        distribution = albedo_distribution(a = albedo)
        self.assertAlmostEqual(expected_distribution, distribution, 4)
    
    def test_zero_albedo(self):
        expected_distribution = 0.00
        
        albedo = 0.00
        distribution = albedo_distribution(a = albedo)
        self.assertAlmostEqual(expected_distribution, distribution, 4)
    
    def test_negative_albedo(self):
        expected_distribution = 'Check your albedo!'
        
        albedo = -0.20
        distribution = albedo_distribution(a = albedo)
        self.assertAlmostEqual(expected_distribution, distribution, 4)
    
    def test_albedo_equal_to_one(self):
        expected_distribution = 0.0000
        
        albedo = 1.00
        distribution = albedo_distribution(a = albedo)
        self.assertAlmostEqual(expected_distribution, distribution, 4)
        
    def test_not_in_albedo_range(self):
        expected_distribution = 'Check your albedo!'

        albedo = 5.20
        distribution = albedo_distribution(a = albedo)
        self.assertEqual(expected_distribution, distribution)












