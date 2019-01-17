import os

from django.test import TestCase
from numpy.testing import assert_array_almost_equal
from astropy.io import fits

# Import module to test
from comet.comet_subs import *

class DetermineImagesAndCatalogsUnitTest(TestCase):

    def test_missingdir(self):
        expected_files = []
        expected_catalogs = []

        files, catalogs = determine_images_and_catalogs('/tmp/wibble')

        self.assertEqual(expected_files, files)
        self.assertEqual(expected_catalogs, catalogs)

    def test_emptydir(self):
        expected_files = []
        expected_catalogs = []

        files, catalogs = determine_images_and_catalogs('comet')

        self.assertEqual(expected_files, files)
        self.assertEqual(expected_catalogs, catalogs)

    def test_realdir(self):
        expected_files = ['/home/tlister/git/neoexchange_stable/neoexchange/comet/tests/ogg2m001-fs02-20150827-0106-e91.fits']
        expected_catalogs = []

        files_path = os.path.join('comet', 'tests')
        files, catalogs = determine_images_and_catalogs(files_path)

        self.assertEqual(expected_files, files)
        self.assertEqual(expected_catalogs, catalogs)

class TestOpenImage(TestCase):

    def setUp(self):
        self.test_fits_file = os.path.join('comet', 'tests', 'ogg2m001-fs02-20150827-0106-e91.fits')
        hdulist = fits.open(self.test_fits_file)
        self.test_header = hdulist[0].header
        self.test_data = hdulist[0].data

    def test_open_image(self):
        header, image = open_image(self.test_fits_file)

        self.assertEqual(self.test_header, header)
        assert_array_almost_equal(self.test_data, image)

class TestDetermineApertureSize(TestCase):

    def test1(self):
        expected_value = 17.9434161251171

        delta = 1.63499738548543
        pixel_scale = 0.469978
        ap_size = determine_aperture_size(delta, pixel_scale)

        self.assertAlmostEqual(expected_value, ap_size, 7)

    def test_ELP_Sinistro(self):
        expected_value = 23.402630605907784

        delta = 1.51289568602651
        pixel_scale = 0.389427

        ap_size = determine_aperture_size(delta, pixel_scale)

        self.assertAlmostEqual(expected_value, ap_size, 7)

    def test_1AU_1arcsec(self):
        expected_value = 13.78795068

        delta = 1.0
        pixel_scale = 1.0

        ap_size = determine_aperture_size(delta, pixel_scale)

        self.assertAlmostEqual(expected_value, ap_size, 7)

    def test_msk1(self):
        expected_value = 7.48125375801

        delta = 1.843
        pixel_scale = 1.0

        ap_size = determine_aperture_size(delta, pixel_scale)

        self.assertAlmostEqual(expected_value, ap_size, 7)

    def test_msk2(self):
        expected_value = 7.2875003573

        delta = 1.892
        pixel_scale = 1.0

        ap_size = determine_aperture_size(delta, pixel_scale)

        self.assertAlmostEqual(expected_value, ap_size, 7)

    def test_msk3(self):
        expected_value = 7.2875003573

        delta = 1.892
        pixel_scale = 1.0

        ap_size = determine_aperture_size(delta, pixel_scale)

        self.assertAlmostEqual(expected_value, ap_size, 7)

    def test_CSS1(self):
        expected_value = 2.42916679

        delta = 1.892
        pixel_scale = 3.0

        ap_size = determine_aperture_size(delta, pixel_scale)

        self.assertAlmostEqual(expected_value, ap_size, 7)

class TestInterpolateEphemeris(TestCase):

    def setUp(self):
        self.test_ephem_file = os.path.join('comet', 'tests', '67P_ephem_COJ_kb71_Q64.txt')

        self.test_ELP_ephem_file = os.path.join('comet', 'tests', '67P_ephem_ELP_fl05_V37.txt')

    def test1(self):

        expected_values = (184.090475019278, 7.46493421991147, 25.11074, -3.79655, 1.63499738548543, 29.1990)

        jd = 2457386.22153299

        values = interpolate_ephemeris(self.test_ephem_file, jd)

        i = 0
        while i < len(expected_values):
            self.assertAlmostEqual(expected_values[i], values[i], 8)
            i+=1

    def test2(self):

        expected_values = (185.6111692090867, 8.2001430387953246, -12.7807, 10.75357,1.51289568602651, 21.1041)
        jd = 2457416.02002136574 + (60.0/2.0/86400.0)

        values = interpolate_ephemeris(self.test_ELP_ephem_file, jd)

        i = 0
        while i < len(expected_values):
            self.assertAlmostEqual(expected_values[i], values[i], 8)
            i+=1
