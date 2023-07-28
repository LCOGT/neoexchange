"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2023-2023 LCO
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
import tempfile
import os
import shutil
from datetime import datetime, timedelta

from django.test import SimpleTestCase, TestCase, override_settings
from django.conf import settings

# Import module to test
from core.utils import *


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
@override_settings(DATA_ROOT=tempfile.mkdtemp())
class TestSearch(SimpleTestCase):

    def setUp(self):
        self.test_dir = settings.MEDIA_ROOT


    def touch(self, fname, times=None):
        with open(fname, 'a'):
            os.utime(fname, times)

    def test_bad_dir(self):
        expected_result = False

        files = search(os.path.join(self.test_dir, 'wibble'), '*')

        self.assertEqual(expected_result, files)

    def test_empty_dir(self):
        expected_result = []

        files = search(self.test_dir, '*')

        self.assertEqual(expected_result, files)

    def test_dir_search(self):
        os.makedirs(os.path.join(self.test_dir, '20239999_K92'))
        os.makedirs(os.path.join(self.test_dir, '20239999_Z24'))

        expected_result = ['20239999_K92']

        files = search(self.test_dir, '.*_K92', dir_search=True)

        self.assertEqual(expected_result, files)

    def test_file_search(self):
        fits_dir = os.path.join(self.test_dir, '20239999_K92')
        os.makedirs(fits_dir, exist_ok=True)
        for extn in ['e91.fits', 'e92.fits', 'e92_rms.fits']:
            self.touch(os.path.join(fits_dir, 'foo_'+extn))
        for extn in ['e91.fits', 'e92.fits', 'e92_rms.fits']:
            self.touch(os.path.join(self.test_dir, 'bar_'+extn))
        os.makedirs(os.path.join(self.test_dir, '20239999_Z24'), exist_ok=True)

        expected_result = ['foo_e92.fits']

        files = search(fits_dir, '.*_e92.fits', dir_search=False)

        self.assertEqual(expected_result, files)

    def test_file_search_not_latest(self):
        fits_dir = os.path.join(self.test_dir, '20239999_K92')
        os.makedirs(fits_dir, exist_ok=True)
        for extn in ['e91.fits', 'e92.fits', 'e92_rms.fits']:
            self.touch(os.path.join(fits_dir, 'foo_'+extn))
            self.touch(os.path.join(fits_dir, 'bar_'+extn))
        os.makedirs(os.path.join(self.test_dir, '20239999_Z24'), exist_ok=True)

        expected_result = ['foo_e92.fits', 'bar_e92.fits']

        files = search(fits_dir, '.*_e92.fits', dir_search=False)

        self.assertEqual(expected_result, files)

    def test_file_search_latest(self):
        fits_dir = os.path.join(self.test_dir, '20239999_K92')
        os.makedirs(fits_dir, exist_ok=True)
        t = datetime.utcnow()
        t_ts = int(datetime.timestamp(t))
        t1 = t-timedelta(seconds=60)
        t1_ts = int(datetime.timestamp(t1))
        
        for extn in ['e91.fits', 'e92.fits', 'e92_rms.fits']:
            self.touch(os.path.join(fits_dir, 'foo_'+extn), (t1_ts, t1_ts))
            self.touch(os.path.join(fits_dir, 'bar_'+extn), (t_ts, t_ts))
        os.makedirs(os.path.join(self.test_dir, '20239999_Z24'), exist_ok=True)

        expected_result = os.path.join(fits_dir, 'bar_e92.fits')

        files = search(fits_dir, '.*_e92.fits', dir_search=False, latest=True)

        self.assertEqual(expected_result, files)
