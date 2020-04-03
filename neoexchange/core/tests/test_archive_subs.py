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


class TestFetchArchiveFrames(TestCase):

    def test_fetch_spectra(self):
        auth_header = {'Authorization': 'Token LetMeInPrettyPlease'}
        request_id = 1391169
        archive_url = '%s?limit=%d&REQNUM=%s&OBSTYPE=%s' % (settings.ARCHIVE_FRAMES_URL, 3000, request_id, 'SPECTRUM')

        expected_data = {'obstypes': ['SPECTRUM', 'SPECTRUM'], 'redlevels': [90, 0]}

        data = mock_fetch_archive_frames(auth_header, archive_url, [])

        self.assertEqual(2, len(data))
        self.assertEqual(expected_data['obstypes'], [x['OBSTYPE'] for x in data])
        self.assertEqual([request_id, request_id], [x['REQNUM'] for x in data])
        self.assertEqual(expected_data['redlevels'], [x['RLEVEL'] for x in data])

    def lco_api_fail(self, data_url):
        return None

    @patch('core.archive_subs.lco_api_call', lco_api_fail)
    def test_fetch_nothing(self):
        auth_header = {'Authorization': 'Token LetMeInPrettyPlease'}
        request_id = 1391169
        archive_url = '%s?limit=%d&REQNUM=%s&OBSTYPE=%s' % (settings.ARCHIVE_FRAMES_URL, 3000, request_id, 'SPECTRUM')
        frames = []

        data = fetch_archive_frames(auth_header, archive_url, frames)
        self.assertEqual(data, frames)


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


class TestMakeDataDir(TestCase):

    def test_basic_file(self):
        frame = {'id': 11683740,
                 'basename': 'lsc1m004-fa03-20190515-0219-e91',
                 'area': {'type': 'Polygon',
                          'coordinates': [[[-119.60667247040064, -80.84910808755131],
                                           [-119.67692747520755, -81.29223462128944],
                                           [-116.74877284149923, -81.29221942699515],
                                           [-116.81921869244925, -80.84909362321092],
                                           [-119.60667247040064, -80.84910808755131]]]},
                 'related_frames': [9741441, 11683739, 11678988, 11678997, 11638089],
                 'version_set': [{'id': 12114354,
                                  'created': '2019-05-16T07:04:57.636775Z',
                                  'key': 'rfjZxBPi1S0r0BsAjxp9t4jKn7VjrDkl',
                                  'md5': 'a29e391ebc7dd2d74f9816e846690498',
                                  'extension': '.fits.fz',
                                  'url': 'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/30b8/lsc1m004-fa03-20190515-0219-e91?versionId=rfjZxBPi1S0r0BsAjxp9t4jKn7VjrDkl&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=9JGuXQ3MLyJoGrpmyjF81uI03eo%3D&Expires=1558206826'}],
                 'filename': 'lsc1m004-fa03-20190515-0219-e91.fits.fz',
                 'url': 'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/30b8/lsc1m004-fa03-20190515-0219-e91?versionId=rfjZxBPi1S0r0BsAjxp9t4jKn7VjrDkl&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=9JGuXQ3MLyJoGrpmyjF81uI03eo%3D&Expires=1558206826',
                 'RLEVEL': 91,
                 'DATE_OBS': '2019-05-16T07:03:49.689000Z',
                 'PROPID': 'LCO2019A-006',
                 'INSTRUME': 'fa03',
                 'OBJECT': '2018 VX8',
                 'SITEID': 'lsc',
                 'TELID': '1m0a',
                 'EXPTIME': '10.032',
                 'FILTER': 'w',
                 'L1PUBDAT': '2020-05-15T07:03:49.689000Z',
                 'OBSTYPE': 'EXPOSE',
                 'BLKUID': 532567027,
                 'REQNUM': 1797014}

        data_dir = 'foo/bar'

        expected_out_dir = 'foo/bar/20190515'

        outpath = make_data_dir(data_dir, frame)

        self.assertEqual(expected_out_dir, outpath)

    def test_tar_file(self):
        frame = {'id': 11677339,
                  'basename': 'LCOEngineering_0001796128_ftn_20190515_58619',
                  'area': {'type': 'Polygon',
                           'coordinates': [[[-103.68601696562837, 4.039698072765181],
                                            [-103.71972148528238, 4.073683129762399],
                                            [-103.85824703065822, 3.936951185095777],
                                            [-103.82454233802372, 3.902971787782345],
                                            [-103.68601696562837, 4.039698072765181]]]},
                  'related_frames': [11675673],
                  'version_set': [{'id': 12107875,
                                   'created': '2019-05-15T19:14:05.537193Z',
                                   'key': '36W5tzp4JbYVqSyvz3akoZ7Z1kK39fqv',
                                   'md5': 'b66e09be8c21c906e6112bbc677ffe47',
                                   'extension': '.tar.gz',
                                   'url': 'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/7761/LCOEngineering_0001796128_ftn_20190515_58619?versionId=36W5tzp4JbYVqSyvz3akoZ7Z1kK39fqv&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=UBe%2FifqiRBepVcUPQDD6ov2q0NU%3D&Expires=1558207304'}],
                  'filename': 'LCOEngineering_0001796128_fts_20190514_58619.tar.gz',
                  'url': 'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/7761/LCOEngineering_0001796128_ftn_20190515_58619?versionId=36W5tzp4JbYVqSyvz3akoZ7Z1kK39fqv&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=UBe%2FifqiRBepVcUPQDD6ov2q0NU%3D&Expires=1558207304',
                  'RLEVEL': 90,
                  'DATE_OBS': '2019-05-14T13:38:20.059000Z',
                  'PROPID': 'LCOEngineering',
                  'INSTRUME': 'en06',
                  'OBJECT': '2008 HS3',
                  'SITEID': 'coj',
                  'TELID': '2m0a',
                  'EXPTIME': '1800.019',
                  'FILTER': 'air',
                  'L1PUBDAT': '2020-05-14T13:38:20.059000Z',
                  'OBSTYPE': 'SPECTRUM',
                  'BLKUID': 531938815,
                  'REQNUM': 1796128}

        data_dir = 'foo/bar'

        expected_out_dir = data_dir + '/20190514'

        outpath = make_data_dir(data_dir, frame)

        self.assertEqual(expected_out_dir, outpath)

    def test_ogg_tar_file(self):
        frame = {'id': 11677339,
                  'basename': 'LCOEngineering_0001796128_ftn_20190515_58619',
                  'area': {'type': 'Polygon',
                           'coordinates': [[[-103.68601696562837, 4.039698072765181],
                                            [-103.71972148528238, 4.073683129762399],
                                            [-103.85824703065822, 3.936951185095777],
                                            [-103.82454233802372, 3.902971787782345],
                                            [-103.68601696562837, 4.039698072765181]]]},
                  'related_frames': [11675673],
                  'version_set': [{'id': 12107875,
                                   'created': '2019-03-01T19:14:05.537193Z',
                                   'key': '36W5tzp4JbYVqSyvz3akoZ7Z1kK39fqv',
                                   'md5': 'b66e09be8c21c906e6112bbc677ffe47',
                                   'extension': '.tar.gz',
                                   'url': 'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/7761/LCOEngineering_0001796128_ftn_20190515_58619?versionId=36W5tzp4JbYVqSyvz3akoZ7Z1kK39fqv&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=UBe%2FifqiRBepVcUPQDD6ov2q0NU%3D&Expires=1558207304'}],
                  'filename': 'LCOEngineering_0001796128_fts_20190301_58619.tar.gz',
                  'url': 'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/7761/LCOEngineering_0001796128_ftn_20190515_58619?versionId=36W5tzp4JbYVqSyvz3akoZ7Z1kK39fqv&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=UBe%2FifqiRBepVcUPQDD6ov2q0NU%3D&Expires=1558207304',
                  'RLEVEL': 90,
                  'DATE_OBS': '2019-03-01T13:38:20.059000Z',
                  'PROPID': 'LCOEngineering',
                  'INSTRUME': 'en06',
                  'OBJECT': '2008 HS3',
                  'SITEID': 'ogg',
                  'TELID': '2m0a',
                  'EXPTIME': '1800.019',
                  'FILTER': 'air',
                  'L1PUBDAT': '2020-05-14T13:38:20.059000Z',
                  'OBSTYPE': 'SPECTRUM',
                  'BLKUID': 531938815,
                  'REQNUM': 1796128}

        data_dir = 'foo/bar'

        expected_out_dir = data_dir + '/20190228'

        outpath = make_data_dir(data_dir, frame)

        self.assertEqual(expected_out_dir, outpath)
