'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2015-2016 LCOGT

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
from mock import patch
from math import radians

from neox.tests.mocks import MockDateTime

#Import module to test
from astrometrics.time_subs import jd_utc2datetime, dttodecimalday, \
    degreestohms, parse_neocp_date, get_semester_dates, time_of_full_moon, \
    determine_approx_moon_cycle, time_in_julian_centuries, \
    moon_fundamental_arguments

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

class TestDT2DecimalDay(TestCase):

    def test_microday1(self):
        dt = datetime(2015, 10, 12, 23, 45, 56, int(0.7*1e6))
        expected_string = '2015 10 12.990240'

        dt_string = dttodecimalday(dt, True)

        self.assertEqual(expected_string, dt_string)

    def test_microday2(self):
        dt = datetime(2015, 1, 1, 2, 3, 4, int(0.7*1e6))
        expected_string = '2015 01 01.085471'

        dt_string = dttodecimalday(dt, True)

        self.assertEqual(expected_string, dt_string)

    def test_nomicroday1(self):
        dt = datetime(2015, 10, 12, 23, 45, 56, int(0.7*1e6))
        expected_string = '2015 10 12.99024 '

        dt_string = dttodecimalday(dt, False)

        self.assertEqual(expected_string, dt_string)

    def test_nomicroday2(self):
        dt = datetime(2015, 1, 1, 2, 3, 4, int(0.7*1e6))
        expected_string = '2015 01 01.08547 '

        dt_string = dttodecimalday(dt, False)

        self.assertEqual(expected_string, dt_string)

    def test_badinput(self):
        dt = "Wibble"
        expected_string = ''

        dt_string = dttodecimalday(dt, False)

        self.assertEqual(expected_string, dt_string)
       

    def test_badinput_microday(self):
        dt = 42.0
        expected_string = ''

        dt_string = dttodecimalday(dt, True)

        self.assertEqual(expected_string, dt_string)

class TestDegreesToHMS(TestCase):

    def test_bad_rounding(self):
        value = 42.0
        expected_string = "02 48 00.00"

        time_string = degreestohms(value, " ")

        self.assertEqual(expected_string, time_string)

@patch('astrometrics.time_subs.datetime', MockDateTime)
class TestParseNeocpDate(TestCase):

    def setUp(self):
        MockDateTime.change_datetime(2015, 12, 31, 22, 0, 0)

    def test_good_date(self):
        date_string = '(Nov. 16.81 UT)'
        expected_dt =  datetime(2015, 11, 16, 19, 26, 24)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_bad_string(self):
        date_string = '(Nov. 16.81UT)'
        expected_dt =  None

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_bad_string2(self):
        date_string = '(Nov.16.81UT)'
        expected_dt =  None

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_bad_date(self):
        MockDateTime.change_datetime(2016, 3, 1, 22, 0, 0)
        date_string = '(Feb. 30.00 UT)'
        expected_dt =  datetime(2016, 3, 1, 00, 00, 00)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_extra_spaces(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)

        date_string = u'(Mar.  9.97 UT)'
        expected_dt =  datetime(2016, 3, 9, 23, 16, 48)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_extra_spaces2(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)

        date_string = u'(Mar.    9.97    UT)'
        expected_dt =  datetime(2016, 3, 9, 23, 16, 48)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_extra_spaces3(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)

        date_string = u'(Mar.  19.97 UT)'
        expected_dt =  datetime(2016, 3, 19, 23, 16, 48)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

class TestGetSemesterDates(TestCase):

    def test_start_of_B_semester(self):
        date = datetime(2015, 10, 1, 0, 0, 1)
        expected_start = datetime(2015, 10, 1, 0, 0, 0)
        expected_end = datetime(2016, 3, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_B_semester(self):
        date = datetime(2016, 3, 31, 22, 0, 0)
        expected_start = datetime(2015, 10, 1, 0, 0, 0)
        expected_end = datetime(2016, 3, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_start_of_A_semester(self):
        date = datetime(2016, 4, 1,  0, 0, 1)
        expected_start = datetime(2016, 4, 1, 0, 0, 0)
        expected_end = datetime(2016, 9, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_A_semester(self):
        date = datetime(2016, 9, 30,  23, 0, 1)
        expected_start = datetime(2016, 4, 1, 0, 0, 0)
        expected_end = datetime(2016, 9, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_start_of_17B_semester(self):
        date = datetime(2017, 10, 1, 0, 1, 0)
        expected_start = datetime(2017, 10, 1, 0, 0, 0)
        expected_end = datetime(2018, 3, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_17B_semester(self):
        date = datetime(2018, 3, 31, 22, 0, 0)
        expected_start = datetime(2017, 10, 1, 0, 0, 0)
        expected_end = datetime(2018, 3, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_start_of_17A_semester(self):
        date = datetime(2017, 4, 1,  0, 0, 1)
        expected_start = datetime(2017, 4, 1, 0, 0, 0)
        expected_end = datetime(2017, 9, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_17A_semester(self):
        date = datetime(2017, 9, 30,  23, 0, 1)
        expected_start = datetime(2017, 4, 1, 0, 0, 0)
        expected_end = datetime(2017, 9, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

class TestDetermineApproxMoonCycle(TestCase):

    def test_meeus_example(self):

        dt = datetime(1977, 2, 18)

        expected_cycle = -283

        cycle = determine_approx_moon_cycle(dt, 'NEW_MOON', dbg=False)

        self.assertEqual(expected_cycle, cycle)

    def test_full_moon_defaulting(self):

        dt = datetime(1977, 2, 18)

        expected_cycle = -282.5

        cycle = determine_approx_moon_cycle(dt)

        self.assertEqual(expected_cycle, cycle)

    def test_2016may_full_moon(self):

        dt = datetime(2016, 4, 22)

        expected_cycle = 202.5

        cycle = determine_approx_moon_cycle(dt, 'FULL_MOON', dbg=False)

        self.assertEqual(expected_cycle, cycle)

class TestTimeInJulianCenturies(TestCase):

    def test_example_jd(self):
        jd = 2446895.5

        expected_T = -0.127296372348

        T = time_in_julian_centuries(jd)

        self.assertAlmostEqual(expected_T, T, 12)

    def test_example_mjd(self):
        jd = 46895.0

        expected_T = -0.127296372348

        T = time_in_julian_centuries(jd)

        self.assertAlmostEqual(expected_T, T, 12)

    def test_example_datetime(self):
        dt = datetime(1987, 4, 10, 0, 0, 0)

        expected_T = -0.127296372348

        T = time_in_julian_centuries(dt)

        self.assertAlmostEqual(expected_T, T, 12)

class TestMoonFundamentalArguments(TestCase):

    def test_fundarg_meeus_example(self):
        k = -283
        T = -0.22881

        expected_E      = 1.0005753
        expected_M      = radians( 45.7375) # Un-normalized    -8234.2625
        expected_Mprime = radians( 95.3722) # Un-normalized  -108984.6278
        expected_F      = radians(120.9584) # Un-normalized  -110399.0416
        expected_Omega  = radians(207.3176) # Un-normalized      567.3176

        E, M, Mprime, F, Omega = moon_fundamental_arguments(k, T)

        precision = 4
        self.assertAlmostEqual(expected_E, E, 7)
        self.assertAlmostEqual(expected_M, M, precision)
        self.assertAlmostEqual(expected_Mprime, Mprime, precision)
        self.assertAlmostEqual(expected_F, F, precision)
        self.assertAlmostEqual(expected_Omega, Omega, precision)

class TestTimeOfFullMoon(TestCase):

    def test_meeus_example(self):


        dt = datetime(1977, 2, 14)

# Value from Meeus p. 353 back converted to datetime
        expected_dt = datetime(1977, 2, 18, 10, 35, 4)

        moon_time = time_of_full_moon(dt, 'NEW_MOON')

        self.assertEqual(expected_dt, moon_time)

    def test_2016may_full_moon(self):

        dt = datetime(2016, 4, 25, 17, 21, 0)

# Value from http://aa.usno.navy.mil/cgi-bin/aa_phases.pl?year=2016&month=4&day=25&nump=50&format=p
        expected_dt = datetime(2016, 5, 21, 21, 14, 0)

        moon_time = time_of_full_moon(dt, 'FULL_MOON', True)

        self.assertEqual(expected_dt, moon_time)
