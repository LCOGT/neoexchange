"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime, timedelta
from unittest import skipIf
from hashlib import md5
import tempfile

from mock import patch
from django.test import TestCase
from django.conf import settings

from neox.tests.mocks import MockDateTime, mock_fetch_archive_frames
# Import module to test
from core.archive_subs import *


class Test_Determine_Archive_Start_End(TestCase):

    def test_date_before_utc_midnight(self):
        dt = datetime(2016, 4, 12,  23, 00, 5)

        expected_start = datetime(2016, 4, 12, 16, 0, 0)
        expected_end = datetime(2016, 4, 13, 20, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_closeto_utc_midnight(self):
        dt = datetime(2016, 4, 12,  23, 59, 59)

        expected_start = datetime(2016, 4, 12, 16, 0, 0)
        expected_end = datetime(2016, 4, 13, 20, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_after_utc_midnight(self):
        dt = datetime(2016, 4, 13,  3, 00, 5)

        expected_start = datetime(2016, 4, 13, 16, 0, 0)
        expected_end = datetime(2016, 4, 14, 20, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_closeto_day_rollover(self):
        dt = datetime(2016, 12, 31, 15, 59, 59)
        expected_start = datetime(2016, 12, 31, 16, 0, 0)
        expected_end = datetime(2017, 1, 1, 20, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_date_just_past_day_rollover(self):
        dt = datetime(2016, 4, 13, 17, 00, 1)

        expected_start = datetime(2016, 4, 13, 16, 0, 0)
        expected_end = datetime(2016, 4, 14, 20, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_supplied_date_midnight(self):
        dt = datetime(2016, 4, 18, 00, 00, 00)

        expected_start = datetime(2016, 4, 18, 16, 0, 0)
        expected_end = datetime(2016, 4, 19, 20, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    @patch('core.archive_subs.datetime', MockDateTime)
    def test_no_supplied_date(self):
        MockDateTime.change_datetime(2015, 11, 18, 12, 0, 0)
        dt = None

        expected_start = datetime(2015, 11, 17, 16, 0, 0)
        expected_end = datetime(2015, 11, 19, 20, 0, 0)

        start, end = determine_archive_start_end(dt)

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)


class TestCheckForExistingFile(TestCase):

    def create_temp(self, filename):

        md5sum = None
        with open(filename, "wb") as f:
            f.write(b"Delete me!")
            f.close()
            md5sum = md5(open(filename, 'rb').read()).hexdigest()
            return md5sum

    def setUp(self):
        self.test_ql_file_comp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e11.fits.fz')
        self.test_ql_file_uncomp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e11.fits')
        self.test_red_file_comp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e91.fits.fz')
        self.test_red_file_uncomp = os.path.join(tempfile.gettempdir(), 'cpt1m010-fl16-20170111-0211-e91.fits')
        self.test_FLOYDS_comp_tarball = os.path.join(tempfile.gettempdir(), 'LCOEngineering_0001651275_ftn_20181005_58397.tar.gz')
        self.test_FLOYDS_uncomp_tarball = os.path.join(tempfile.gettempdir(), 'LCOEngineering_0001651275_ftn_20181005_58397.tar')
        self.test_files = [ self.test_ql_file_comp, self.test_ql_file_uncomp,
                            self.test_red_file_comp, self.test_red_file_uncomp,
                            self.test_FLOYDS_comp_tarball, self.test_FLOYDS_uncomp_tarball
                          ]

    def tearDown(self):
        for test_file in self.test_files:
            if os.path.exists(test_file):
                os.remove(test_file)

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

    def test_FLOYDS_comp_tarball(self):
        md5sum = self.create_temp(self.test_FLOYDS_comp_tarball)
        self.assertTrue(check_for_existing_file(self.test_FLOYDS_comp_tarball, md5sum), "Wrong result")

    def test_FLOYDS_uncomp_tarball(self):
        md5sum = self.create_temp(self.test_FLOYDS_uncomp_tarball)
        self.assertFalse(check_for_existing_file(self.test_FLOYDS_uncomp_tarball, md5sum), "Wrong result")

    def test_badfile(self):
        self.assertFalse(check_for_existing_file('wibble'), "Wrong result")


@patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
class TestFetchArchiveFrames(TestCase):

    def test_fetch_spectra(self):
        auth_header = {'Authorization': 'Token LetMeInPrettyPlease'}
        request_id = 1391169
        archive_url = '%s?limit=%d&REQNUM=%s&OBSTYPE=%s' % (settings.ARCHIVE_FRAMES_URL, 3000, request_id, 'SPECTRUM')

        expected_data = { 'obstypes' : ['SPECTRUM', 'SPECTRUM'],
                          'redlevels' : [90, 0]}

        data = mock_fetch_archive_frames(auth_header, archive_url, [])

        self.assertEqual(2, len(data))
        self.assertEqual(expected_data['obstypes'], [x['OBSTYPE'] for x in data])
        self.assertEqual([request_id, request_id], [x['REQNUM'] for x in data])
        self.assertEqual(expected_data['redlevels'], [x['RLEVEL'] for x in data])


@patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
class TestCheckArchiveImages(TestCase):

    def test_fetch_imaging(self):
        request_id = 42

        expected_data = { 'obstypes' : ['EXPOSE', ],
                          'redlevels' : [91, ],
                          'files' : ['ogg0m406-kb27-20160531-0063-e91.fits.fz', ]
                        }
        frames, num_frames = check_for_archive_images(request_id)

        self.assertEqual(2, num_frames)
        self.assertEqual(expected_data['obstypes'], [x['OBSTYPE'] for x in frames])
        self.assertEqual(expected_data['redlevels'], [x['RLEVEL'] for x in frames])
        self.assertEqual(expected_data['files'], [x['filename'] for x in frames])

    def test_fetch_spectra(self):
        request_id = 1391169
        obstype = 'SPECTRUM'

        expected_data = { 'obstypes' : ['SPECTRUM', 'SPECTRUM'],
                          'redlevels' : [90, 0],
                          'files' : ['LCOEngineering_0001391169_ftn_20180111_58130.tar.gz', 'ogg2m001-en06-20180110-0005-e00.fits.fz', ]
                          }

        frames, num_frames = check_for_archive_images(request_id, obstype)

        self.assertEqual(2, num_frames)
        self.assertEqual(expected_data['obstypes'], [x['OBSTYPE'] for x in frames])
        self.assertEqual(expected_data['redlevels'], [x['RLEVEL'] for x in frames])
        self.assertEqual(expected_data['files'], [x['filename'] for x in frames])
