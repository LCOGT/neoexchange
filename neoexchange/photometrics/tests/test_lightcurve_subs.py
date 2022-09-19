import os
import shutil
import tempfile
from glob import glob
from datetime import datetime, timedelta

import numpy as np
from astropy.time import Time
from astropy.wcs import WCS

from core.models import Body, SuperBlock, Block, Frame, SourceMeasurement
from photometrics.lightcurve_subs import *

from django.test import SimpleTestCase, TestCase
from numpy.testing import assert_allclose, assert_array_equal

class TestReadPhotomPipe(SimpleTestCase):

    def setUp(self):
        self.test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))

        self.debug_print = False
        self.maxDiff = None


    def test_read(self):
        expected_length = 62

        table = read_photompipe_file(self.test_lc_file)

        self.assertEqual(expected_length, len(table))

class TestWriteDartFormatFile(SimpleTestCase):

    def setUp(self):
        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))

        self.test_table = read_photompipe_file(test_lc_file)
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.remove = True
        self.debug_print = False
        self.maxDiff = None

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)
        else:
            if self.debug_print:
                print("Test directory", self.test_dir, "not removed")

    def test_write(self):
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad',
        ' tfn1m001-fa11-20211012-0073-e92.fits  2459500.3339392  14.8400  0.0397  27.1845  0.0394  -12.3397    0.0052       r                0  10.00',
        ' tfn1m001-fa11-20211012-0074-e92.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0300  -12.3187    0.0053       r                3  10.00'
        ]

        # Modify some values to test rounding
        self.test_table[0]['mag'] = 14.84
        self.test_table[1]['ZP_sig'] = 0.03
        output_file = os.path.join(self.test_dir, 'test.tab')
        write_dartformat_file(self.test_table[0:2], output_file, aprad=10)

        with open(output_file, 'r') as table_file:
            lines = table_file.readlines()

        self.assertEqual(3, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i].rstrip())


class TestExtractApRadius(SimpleTestCase):

    def setUp(self):
        self.test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))

    def test_nofile(self):

        aper_radius = extract_photompipe_aperradius('/foo/bar/log')

        self.assertEqual(None, aper_radius)

    def test_log(self):
        expected_radius = 10.0

        aper_radius = extract_photompipe_aperradius(self.test_logfile)

        self.assertEqual(expected_radius, aper_radius)

class TestCreateTableFromSrcMeasure(TestCase):

    def setUp(self):

        body_params = {
                         'id': 36254,
                         'provisional_name': None,
                         'provisional_packed': None,
                         'name': '65803',
                         'origin': 'N',
                         'source_type': 'N',
                         'source_subtype_1': 'N3',
                         'source_subtype_2': 'PH',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': False,
                         'fast_moving': False,
                         'urgency': None,
                         'epochofel': datetime(2021, 2, 25, 0, 0),
                         'orbit_rms': 0.56,
                         'orbinc': 3.40768,
                         'longascnode': 73.20234,
                         'argofperih': 319.32035,
                         'eccentricity': 0.3836409,
                         'meandist': 1.6444571,
                         'meananom': 77.75787,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.27,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(1996, 4, 11, 0, 0),
                         'num_obs': 829,
                         'arc_length': 7305.0,
                         'not_seen': 2087.29154187494,
                         'updated': True,
                         'ingest': datetime(2018, 8, 14, 17, 45, 42),
                         'update_time': datetime(2021, 3, 1, 19, 59, 56, 957500)
                         }

        self.test_body, created = Body.objects.get_or_create(**body_params)

        block_params = {
                         'body' : self.test_body,
                         'request_number' : '12345',
                         'block_start' : datetime(2021, 10, 13, 0, 40),
                         'block_end' : datetime(2021, 10, 14, 0, 40),
                         'obstype' : Block.OPT_IMAGING,
                         'num_observed' : 1
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)
        # Second block with no frames attached
        block_params['num_observed'] = 0
        self.test_block2, created = Block.objects.get_or_create(**block_params)

        frame_params = {
                         'sitecode' : 'Z24',
                         'instrument' : 'fa11',
                         'filter' : 'ip',
                         'block' : self.test_block,
                         'frametype' : Frame.NEOX_RED_FRAMETYPE,
                         'zeropoint' : 27.0,
                         'zeropoint_err' : 0.03,
                         'midpoint' : block_params['block_start'] + timedelta(minutes=5),
                         'astrometric_catalog' : 'GAIA-DR2',
                         'photometric_catalog' : 'PANSTARRS',
                       }

        self.test_filenames = []
        for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
            frame_params['filename'] = f"tfn1m001-fa11-20211013-{frame_num:04d}-e92.fits"
            frame_offset = frame_num-65
            frame_params['midpoint'] += timedelta(minutes=frame_offset)
            frame_params['frameid'] = frameid
            # Hand-rolled WCS
            naxis_header = {'NAXIS1' : 4096, 'NAXIS2' : 4096, 'NAXIS' : 2}
            w = WCS(naxis_header)
            w.wcs.crpix = [ 2048.0, 2048.0]
            pixel_scale = 0.389/3600.0
            w.wcs.cd = np.array([[pixel_scale, 0.0], [0.0, -pixel_scale]])
            w.wcs.crval = [270.01 + frame_offset*0.01, -27.02 - frame_offset*0.01]
            w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
            frame_params['wcs'] = w
            frame, created = Frame.objects.get_or_create(**frame_params)
            self.test_filenames.append(frame_params['filename'])

            mag_err = (frame_offset*0.0003) + 0.003
            source_params = { 'body' : self.test_body,
                              'frame' : frame,
                              'obs_ra' : 270 + frame_offset*0.01,
                              'obs_dec' : -27 - frame_offset*0.01,
                              'obs_mag' : 14.6 + frame_offset * 0.001,
                              'err_obs_ra' : 0.3/3600.0,
                              'err_obs_dec' : 0.3/3600.0,
                              'err_obs_mag' : mag_err,
                              'astrometric_catalog' : frame.astrometric_catalog,
                              'photometric_catalog' : frame.photometric_catalog,
                              'aperture_size' : 3.89,
                              'snr' : 1/mag_err,
                              'flags' : ''
                            }
            source, created = SourceMeasurement.objects.get_or_create(**source_params)

        self.maxDiff = None

    def test1(self):

        midpoints = Frame.objects.all().values_list('midpoint', flat=True)
        midpoints_jd = [Time(d).jd for d in midpoints]
        data_rows = [[self.test_filenames[0], midpoints_jd[0], 14.60, 0.03015, 27, 0.03, 14.60-27, 0.003, 'ip', 0, 10.0],
                     [self.test_filenames[1], midpoints_jd[1], 14.63, 0.03231, 27, 0.03, 14.63-27, 0.012, 'ip', 0, 10.0],
                     [self.test_filenames[2], midpoints_jd[2], 14.66, 0.03662, 27, 0.03, 14.66-27, 0.021, 'ip', 0, 10.0],
                    ]
        col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad']
        expected_table = Table(rows=data_rows, names=col_names)

        table = create_table_from_srcmeasures(self.test_block)

        self.assertEqual(len(expected_table), len(table))
        self.assertEqual(expected_table.colnames, table.colnames)
        for column in col_names:
            if expected_table[column].dtype.kind in ['U', 'S']:
                assert_array_equal(expected_table[column], table[column])
            else:
                assert_allclose(expected_table[column], table[column], rtol=1e-4, err_msg=f"Compare failure on column: {column}")
