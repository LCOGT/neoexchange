"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from django.test import TestCase, SimpleTestCase
from datetime import datetime, timedelta
from mock import patch

from neox.tests.mocks import MockDateTime

# Import module to test
from astrometrics.time_subs import jd_utc2datetime, dttodecimalday, decimaldaytodt, \
    degreestohms, parse_neocp_date, parse_neocp_decimal_date, get_semester_dates


class TestJD2datetime(SimpleTestCase):

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


class TestDT2DecimalDay(SimpleTestCase):

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


class TestDecimalDay2DT(SimpleTestCase):

    def test_no_microdays(self):
        date_string = '2013 10 31.16159'
        expected_dt = datetime(2013, 10, 31, 3, 52, 41, 376000)

        dt = decimaldaytodt(date_string)

        self.assertEqual(expected_dt, dt)

    def test_microdays(self):
        date_string = '2013 11 01.051812'
        expected_dt = datetime(2013, 11, 1, 1, 14, 36, 556800)

        dt = decimaldaytodt(date_string)

        self.assertEqual(expected_dt, dt)


class TestDegreesToHMS(SimpleTestCase):

    def test_bad_rounding(self):
        value = 42.0
        expected_string = "02 48 00.00"

        time_string = degreestohms(value, " ")

        self.assertEqual(expected_string, time_string)


@patch('astrometrics.time_subs.datetime', MockDateTime)
class TestParseNeocpDate(SimpleTestCase):

    def setUp(self):
        MockDateTime.change_datetime(2015, 12, 31, 22, 0, 0)

    def test_good_date(self):
        date_string = '(Nov. 16.81 UT)'
        expected_dt = datetime(2015, 11, 16, 19, 26, 24)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_bad_string(self):
        date_string = '(Nov. 16.81UT)'
        expected_dt = None

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_bad_string2(self):
        date_string = '(Nov.16.81UT)'
        expected_dt = None

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_bad_date(self):
        MockDateTime.change_datetime(2016, 3, 1, 22, 0, 0)
        date_string = '(Feb. 30.00 UT)'
        expected_dt = datetime(2016, 3, 1, 00, 00, 00)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_extra_spaces(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)

        date_string = u'(Mar.  9.97 UT)'
        expected_dt = datetime(2016, 3, 9, 23, 16, 48)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_extra_spaces2(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)

        date_string = u'(Mar.    9.97    UT)'
        expected_dt = datetime(2016, 3, 9, 23, 16, 48)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_extra_spaces3(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)

        date_string = u'(Mar.  19.97 UT)'
        expected_dt = datetime(2016, 3, 19, 23, 16, 48)

        dt = parse_neocp_date(date_string)

        self.assertEqual(expected_dt, dt)


class TestParseNEOCPDecimalDate(SimpleTestCase):

    def test_no_microdays(self):
        date_string = '2013 10 31.16159'
        expected_dt = datetime(2013, 10, 31, 3, 52, 41, 376000)

        dt = parse_neocp_decimal_date(date_string)

        self.assertEqual(expected_dt, dt)

    def test_microdays(self):
        date_string = '2013 11 01.051812'
        expected_dt = datetime(2013, 11, 1, 1, 14, 36, 556800)

        dt = parse_neocp_decimal_date(date_string)

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

    def test_start_of_17AB_semester(self):
        date = datetime(2017, 4, 1, 0, 0, 1)
        expected_start = datetime(2017, 4, 1, 0, 0, 0)
        expected_end = datetime(2017, 11, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_17AB_semester(self):
        date = datetime(2017, 11, 30, 22, 0, 0)
        expected_start = datetime(2017, 4, 1, 0, 0, 0)
        expected_end = datetime(2017, 11, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_before_start_of_17AB_semester(self):
        date = datetime(2017, 3, 31,  23, 59, 58)
        expected_start = datetime(2016, 10, 1, 0, 0, 0)
        expected_end = datetime(2017, 3, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_17AB_semester2(self):
        date = datetime(2017, 10, 1,  0, 0, 1)  # Just over old boundary
        expected_start = datetime(2017, 4, 1, 0, 0, 0)
        expected_end = datetime(2017, 11, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_start_of_18A_semester(self):
        date = datetime(2017, 12, 1,  0, 0, 1)
        expected_start = datetime(2017, 12, 1, 0, 0, 0)
        expected_end = datetime(2018, 5, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_start_of_18A_semester2(self):
        date = datetime(2018, 1, 1,  0, 0, 1)
        expected_start = datetime(2017, 12, 1, 0, 0, 0)
        expected_end = datetime(2018, 5, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_18A_semester(self):
        date = datetime(2018, 5, 31,  23, 0, 1)
        expected_start = datetime(2017, 12, 1, 0, 0, 0)
        expected_end = datetime(2018, 5, 31, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_start_of_18B_semester(self):
        date = datetime(2018, 6, 1, 0, 1, 0)
        expected_start = datetime(2018, 6, 1, 0, 0, 0)
        expected_end = datetime(2018, 11, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_end_of_18B_semester(self):
        date = datetime(2018, 11, 30, 23, 30, 0)
        expected_start = datetime(2018, 6, 1, 0, 0, 0)
        expected_end = datetime(2018, 11, 30, 23, 59, 59)

        start, end = get_semester_dates(date)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)
