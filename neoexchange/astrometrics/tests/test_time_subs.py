"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2023 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import logging
import os

from django.test import TestCase, SimpleTestCase
from datetime import datetime, timedelta
from math import radians, degrees
from mock import patch

from neox.tests.mocks import MockDateTime

from astropy.utils import iers

# Import module to test
import astrometrics.time_subs as time_subs
from astrometrics.time_subs import *


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


class TestHoursToDegrees(SimpleTestCase):

    def test_bad_value(self):
        value = 'foo'
        expected_value = ""

        time_value = hourstodegrees(value, " ")

        self.assertEqual(expected_value, time_value)

    def test_val1(self):
        value = 12.5
        expected_value = 187.5

        time_value = hourstodegrees(value, " ")

        self.assertEqual(expected_value, time_value)

    def test_colon_sep(self):
        value = "02:48:00.00"
        expected_value = "02:48:00.00"

        time_value = hourstodegrees(value, " ")

        self.assertEqual(expected_value, time_value)


class TestDegreesToHours(SimpleTestCase):

    def test_bad_value(self):
        value = 'foo'
        expected_value = ""

        time_value = degreestohours(value)

        self.assertEqual(expected_value, time_value)

    def test_val1(self):
        value = 187.5
        expected_value = 12.5

        time_value = degreestohours(value)

        self.assertEqual(expected_value, time_value)

    def test_colon_sep(self):
        value = "02:48:00.00"
        expected_value = "02:48:00.00"

        time_value = degreestohours(value)

        self.assertEqual(expected_value, time_value)


class TestDegreesToHMS(SimpleTestCase):

    def test_bad_value(self):
        value = 'foo'
        expected_string = ""

        time_string = degreestohms(value, " ")

        self.assertEqual(expected_string, time_string)


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

    def test_colon_sep(self):
        value = "02:48:00.00"
        expected_string = "02:48:00.00"

        time_string = degreestohms(value, " ")

        self.assertEqual(expected_string, time_string)


class TestDegreesToDMS(SimpleTestCase):

    def test_bad_value(self):
        value = "02:48:00.00"
        expected_string = "02:48:00.00"

        time_string = degreestodms(value, " ")

        self.assertEqual(expected_string, time_string)

    def test_space_sep(self):
        value = 42.5506
        expected_string = "+42 33 02.2"

        time_string = degreestodms(value, " ")

        self.assertEqual(expected_string, time_string)

    def test_colon_sep(self):
        value = -42.5506
        expected_string = "-42:33:02.2"

        time_string = degreestodms(value, ":")

        self.assertEqual(expected_string, time_string)


class TestRadiansToHMS(SimpleTestCase):

    def test_bad_value(self):
        value = 'foo'
        expected_string = ""

        time_string = radianstohms(value, " ")

        self.assertEqual(expected_string, time_string)

    def test_bad_rounding(self):
        value = radians(42.0)
        expected_string = "02 48 00.00"

        time_string = radianstohms(value, " ")

        self.assertEqual(expected_string, time_string)

    def test_colon_sep(self):
        value = "02:48:00.00"
        expected_string = "02:48:00.00"

        time_string = radianstohms(value, " ")

        self.assertEqual(expected_string, time_string)


class TestRadiansToHMS(SimpleTestCase):

    def test_bad_value(self):
        value = 'foo'
        expected_string = ""

        time_string = radianstohms(value, " ")

        self.assertEqual(expected_string, time_string)

    def test_bad_rounding(self):
        value = radians(42.0)
        expected_string = "02 48 00.00"

        time_string = radianstohms(value, " ")

        self.assertEqual(expected_string, time_string)

    def test_colon_sep(self):
        value = "02:48:00.00"
        expected_string = "02:48:00.00"

        time_string = radianstohms(value, " ")

        self.assertEqual(expected_string, time_string)


class TestHMSToHours(SimpleTestCase):

    def test_bad_value(self):
        value = 'foo'
        expected_value = "foo"

        hours_value = hmstohours(value)

        self.assertEqual(expected_value, hours_value)

    def test_val1(self):
        value = "02:48:00.00"
        expected_value = 2.8

        hours_value = hmstohours(value)

        self.assertEqual(expected_value, hours_value)

    def test_val2(self):
        value = "23:59:12.60"
        expected_value = 359.8025/15.0

        hours_value = hmstohours(value)

        self.assertEqual(expected_value, hours_value)

    def test_nocolon_sep(self):
        value = "02 48 00.00"
        expected_value = "02 48 00.00"

        hours_value = hmstohours(value)

        self.assertEqual(expected_value, hours_value)


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


class TestGetSemesterDates(SimpleTestCase):

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


class IERSTestMixin:
    """Isolates the module-level IERS table cache in astrometrics.time_subs
    between tests and provides a truncated IERS-A fixture (2026-08-20 to
    2026-11-27, predictions from 2026-10-09)."""

    iers_fixture = os.path.join(os.path.dirname(__file__), 'iers', 'finals2000A_truncated.all')

    def setUp(self):
        self.saved_iers_state = (time_subs._iers_table, time_subs._iers_table_loaded, time_subs._iers_range_warned)
        time_subs._iers_table = None
        time_subs._iers_table_loaded = None
        time_subs._iers_range_warned = False
        # Other test modules disable logging globally at import time, which
        # would defeat the assertLogs() checks below
        self.saved_logging_disable = logging.root.manager.disable
        logging.disable(logging.NOTSET)
        # The test settings pin NEOX_IERS_A_FILE; these tests exercise the cache path
        self.env_patcher = patch.dict(os.environ)
        self.env_patcher.start()
        os.environ.pop('NEOX_IERS_A_FILE', None)

    def tearDown(self):
        self.env_patcher.stop()
        time_subs._iers_table, time_subs._iers_table_loaded, time_subs._iers_range_warned = self.saved_iers_state
        logging.disable(self.saved_logging_disable)

    def load_fixture_table(self):
        with patch('astrometrics.time_subs.download_file', return_value=self.iers_fixture):
            return get_iers_table(force_reload=True)


class TestGetIERSTable(IERSTestMixin, SimpleTestCase):

    def test_loads_cached_iers_a_table(self):
        with patch('astrometrics.time_subs.download_file', return_value=self.iers_fixture) as mock_download:
            table = get_iers_table()

        mock_download.assert_called_once_with(IERS_A_URL, cache=True, sources=[])
        self.assertIsInstance(table, iers.IERS_A)
        self.assertEqual(100, len(table))
        self.assertEqual(61272.0, table['MJD'][0].value)
        self.assertEqual(61371.0, table['MJD'][-1].value)
        self.assertIs(table, iers.earth_orientation_table.get())

    def test_never_downloads(self):
        self.assertFalse(iers.conf.auto_download)

    def test_file_from_environment_overrides_cache(self):
        os.environ['NEOX_IERS_A_FILE'] = self.iers_fixture

        with patch('astrometrics.time_subs.download_file', side_effect=AssertionError('cache should not be used')):
            table = get_iers_table()

        self.assertIsInstance(table, iers.IERS_A)
        self.assertEqual(100, len(table))

    def test_falls_back_to_iers_b_when_not_cached(self):
        with patch('astrometrics.time_subs.download_file', side_effect=KeyError('not in cache')):
            with self.assertLogs('astrometrics.time_subs', level='WARNING') as cm:
                table = get_iers_table()

        self.assertIsInstance(table, iers.IERS_B)
        self.assertEqual(1, len(cm.output))
        self.assertIn('update_iers_data', cm.output[0])
        self.assertIs(table, iers.earth_orientation_table.get())

    def test_falls_back_to_iers_b_when_cached_file_unreadable(self):
        with patch('astrometrics.time_subs.download_file', return_value=__file__):
            with self.assertLogs('astrometrics.time_subs', level='WARNING'):
                table = get_iers_table()

        self.assertIsInstance(table, iers.IERS_B)

    def test_table_is_reused(self):
        table = self.load_fixture_table()

        with patch('astrometrics.time_subs.download_file', side_effect=AssertionError('should not reload')):
            self.assertIs(table, get_iers_table())

    def test_table_is_reread_after_reload_interval(self):
        table = self.load_fixture_table()
        time_subs._iers_table_loaded -= IERS_RELOAD_INTERVAL + 1

        with patch('astrometrics.time_subs.download_file', return_value=self.iers_fixture) as mock_download:
            new_table = get_iers_table()

        mock_download.assert_called_once()
        self.assertIsNot(table, new_table)
        self.assertIsInstance(new_table, iers.IERS_A)

    def test_force_reload(self):
        table = self.load_fixture_table()

        with patch('astrometrics.time_subs.download_file', side_effect=KeyError('gone')):
            with self.assertLogs('astrometrics.time_subs', level='WARNING'):
                new_table = get_iers_table(force_reload=True)

        self.assertIsNot(table, new_table)
        self.assertIsInstance(new_table, iers.IERS_B)


class TestUT1MinusUTC(IERSTestMixin, SimpleTestCase):

    def setUp(self):
        super().setUp()
        self.load_fixture_table()

    def test_final_value(self):
        self.assertAlmostEqual(-0.0087766, ut1_minus_utc(61300.5), 7)

    def test_predicted_value(self):
        self.assertAlmostEqual(-0.0643556, ut1_minus_utc(61350.5), 7)

    def test_value_is_float(self):
        self.assertIsInstance(ut1_minus_utc(61300.5), float)

    def test_dbg_output(self):
        with patch('builtins.print') as mock_print:
            ut1_minus_utc(61300.5, dbg=True)
        mock_print.assert_called_once_with('UT1-UTC= -0.008777 (status=1)')

    def test_before_table_start_uses_first_value_and_warns(self):
        with self.assertLogs('astrometrics.time_subs', level='WARNING') as cm:
            dut = ut1_minus_utc(61000.0)

        self.assertAlmostEqual(0.0067351, dut, 7)
        self.assertIn('outside the IERS table range (MJD 61272-61371)', cm.output[0])

    def test_beyond_table_end_uses_last_value(self):
        with self.assertLogs('astrometrics.time_subs', level='WARNING'):
            dut = ut1_minus_utc(61500.0)

        self.assertAlmostEqual(-0.0880703, dut, 7)

    def test_out_of_range_warns_only_once_per_table(self):
        with self.assertLogs('astrometrics.time_subs', level='WARNING') as cm:
            ut1_minus_utc(61500.0)
            ut1_minus_utc(61600.0)
        self.assertEqual(1, len(cm.output))

        self.load_fixture_table()
        with self.assertLogs('astrometrics.time_subs', level='WARNING') as cm:
            ut1_minus_utc(61500.0)
        self.assertEqual(1, len(cm.output))

    def test_iers_b_fallback_value(self):
        with patch('astrometrics.time_subs.download_file', side_effect=KeyError('not in cache')):
            with self.assertLogs('astrometrics.time_subs', level='WARNING'):
                get_iers_table(force_reload=True)

        self.assertAlmostEqual(-0.1703239, ut1_minus_utc(58635.5), 7)

    def test_compute_ut1(self):
        expected_ut1 = 0.5 + (-0.0087766 / 86400.0)

        self.assertAlmostEqual(expected_ut1, compute_ut1(61300.5), 12)
