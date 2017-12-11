'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2017 LCO

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
from hashlib import md5
import tempfile

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

class TestCheckForExistingFile(TestCase):

    def create_temp(self, filename):

        md5sum = None
        with open(filename, "wb") as f:
            f.write("Delete me!")
            f.close()
            md5sum = md5(open(filename, 'rb').read()).hexdigest()
            return md5sum

    def setUp(self):
        self.test_ql_file_comp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e11.fits.fz')
        self.test_ql_file_uncomp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e11.fits')
        self.test_red_file_comp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e91.fits.fz')
        self.test_red_file_uncomp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e91.fits')

    def tearDown(self):
        if os.path.exists(self.test_ql_file_comp):
            os.remove(self.test_ql_file_comp)
        if os.path.exists(self.test_red_file_comp):
            os.remove(self.test_red_file_comp)
        if os.path.exists(self.test_ql_file_uncomp):
            os.remove(self.test_ql_file_uncomp)
        if os.path.exists(self.test_red_file_uncomp):
            os.remove(self.test_red_file_uncomp)

    def test_ql_exists_noMD5(self):
        md5sum = self.create_temp(self.test_ql_file_comp)
        self.assertFalse(check_for_existing_file(self.test_ql_file_comp), "Wrong result")

    def test_ql_and_red_exists(self):
        ql_md5sum = self.create_temp(self.test_ql_file_comp)
        red_md5sum = self.create_temp(self.test_red_file_comp)
        self.assertTrue(check_for_existing_file(self.test_ql_file_comp, ql_md5sum), "Wrong result")

    def test_ql_exists_goodMD5(self):
        md5sum = self.create_temp(self.test_ql_file_comp)
        self.assertTrue(check_for_existing_file(self.test_ql_file_comp, md5sum), "Wrong result")

    def test_ql_exists_badMD5(self):
        md5sum = self.create_temp(self.test_ql_file_comp)
        self.assertFalse(check_for_existing_file(self.test_ql_file_comp, 'foo'), "Wrong result")

    def test_red_exists_noMD5(self):
        md5sum = self.create_temp(self.test_red_file_comp)
        self.assertFalse(check_for_existing_file(self.test_red_file_comp), "Wrong result")

    def test_red_exists_goodMD5(self):
        md5sum = self.create_temp(self.test_red_file_comp)
        self.assertTrue(check_for_existing_file(self.test_red_file_comp, md5sum), "Wrong result")

    def test_red_exists_badMD5(self):
        md5sum = self.create_temp(self.test_red_file_comp)
        self.assertFalse(check_for_existing_file(self.test_red_file_comp, 'foo'), "Wrong result")

    def test_ql_uncomp(self):
        md5sum = self.create_temp(self.test_ql_file_uncomp)
        self.assertTrue(check_for_existing_file(self.test_ql_file_comp), "Wrong result")

    def test_ql_both(self):
        md5sum = self.create_temp(self.test_ql_file_uncomp)
        md5sum = self.create_temp(self.test_ql_file_comp)
        self.assertTrue(check_for_existing_file(self.test_ql_file_comp, md5sum), "Wrong result")

    def test_red_uncomp(self):
        md5sum = self.create_temp(self.test_red_file_uncomp)
        self.assertTrue(check_for_existing_file(self.test_red_file_comp), "Wrong result")

    def test_red_both(self):
        md5sum = self.create_temp(self.test_red_file_uncomp)
        md5sum = self.create_temp(self.test_red_file_comp)
        self.assertTrue(check_for_existing_file(self.test_red_file_comp, md5sum), "Wrong result")

    def test_ql_red_comp(self):
        md5sum = self.create_temp(self.test_ql_file_comp)
        md5sum = self.create_temp(self.test_red_file_comp)
        self.assertTrue(check_for_existing_file(self.test_red_file_comp, md5sum), "Wrong result")

    def test_badfile(self):
        self.assertFalse(check_for_existing_file('wibble'), "Wrong result")
