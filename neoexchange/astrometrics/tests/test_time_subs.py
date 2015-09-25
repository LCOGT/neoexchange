'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2015-2015 LCOGT

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
from datetime import datetime, timedelta
#Import module to test
from astrometrics.time_subs import jd_utc2datetime

class TestJD2datetime(TestCase):

    def test_jd1(self):
        expected_dt = datetime(2015, 9, 24, 22, 47, 17)
        jd = 2457290.449504
        
        dt = jd_utc2datetime(jd)

        self.assertEqual(expected_dt, dt)

    def test_jd_string1(self):
        expected_dt = datetime(2015, 9, 24, 18, 25, 49)
        jd = '2457290.267925'
        
        dt = jd_utc2datetime(jd)

        self.assertEqual(expected_dt, dt)
        self.assertEqual(expected_dt, dt)

    def test_jd_bad_input(self):
        jd = datetime(2015, 9, 24, 22, 48, 0)
        expected_dt = None
        
        dt = jd_utc2datetime(jd)

        self.assertEqual(expected_dt, dt)
