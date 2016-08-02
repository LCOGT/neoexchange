'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

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
from unittest import skipIf

import mock
from django.test import TestCase

from neox.tests.mocks import MockDateTime
#Import module to test
from core.archive_subs import *

class Test_Determine_Archive_Start_End(TestCase):

    def test_date_before_utc_midnight(self):
        dt = datetime(2016, 4, 12,  23, 00, 5)

        expected_start = datetime(2016, 4, 12, 17, 0, 0)
        expected_end = datetime(2016, 4, 13, 16, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_closeto_utc_midnight(self):
        dt = datetime(2016, 4, 12,  23, 59, 59)

        expected_start = datetime(2016, 4, 12, 17, 0, 0)
        expected_end = datetime(2016, 4, 13, 16, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_after_utc_midnight(self):
        dt = datetime(2016, 4, 13,  3, 00, 5)

        expected_start = datetime(2016, 4, 12, 17, 0, 0)
        expected_end = datetime(2016, 4, 13, 16, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_closeto_day_rollover(self):
        dt = datetime(2016, 4, 13, 15, 59, 59)

        expected_start = datetime(2016, 4, 12, 17, 0, 0)
        expected_end = datetime(2016, 4, 13, 16, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_just_past_day_rollover(self):
        dt = datetime(2016, 4, 13, 17, 00, 01)

        expected_start = datetime(2016, 4, 13, 17, 0, 0)
        expected_end = datetime(2016, 4, 14, 16, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_supplied_date_midnight(self):
        dt = datetime(2016, 4, 18, 00, 00, 00)

        expected_start = datetime(2016, 4, 17, 17, 0, 0)
        expected_end = datetime(2016, 4, 18, 16, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)
