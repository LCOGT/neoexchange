"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2022-2022 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
from glob import glob
import tempfile
from unittest import skipIf
import warnings
import shutil
from pathlib import Path

from astropy.io import fits
from numpy import array, arange
from numpy.testing import assert_allclose

from django.test import TestCase
from django.forms.models import model_to_dict

from photometrics.tests.test_external_codes import ExternalCodeUnitTest
# Import module to test
from photometrics.image_subs import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)

class TestCreateWeightImage(ExternalCodeUnitTest):
    def setUp(self):
        super(TestCreateWeightImage, self).setUp()
        self.test_banzai_file = os.path.join(self.testfits_dir, 'banzai_test_frame.fits')
        self.test_banzai_comp_file = os.path.join(self.testfits_dir, 'banzai_test_frame.fits.fz')
        self.test_banzai_rms_file = os.path.join(self.testfits_dir, 'banzai_test_frame.rms.fits')

        """example-sbig-e10.fits"""
        # This image only has a 'PRIMARY' HDU
        shutil.copy(os.path.abspath(self.test_fits_file), self.test_dir)
        self.test_fits_file = os.path.join(self.test_dir, os.path.basename(self.test_fits_file))

        """banzai_test_frame.fits"""
        shutil.copy(os.path.abspath(self.test_banzai_file), self.test_dir)
        self.test_banzai_file = os.path.join(self.test_dir, os.path.basename(self.test_banzai_file))

        """banzai_test_frame.fits.fz"""
        shutil.copy(os.path.abspath(self.test_banzai_comp_file), self.test_dir)
        self.test_banzai_comp_file = os.path.join(self.test_dir, os.path.basename(self.test_banzai_comp_file))

        """banzai_test_frame.rms.fits"""
        shutil.copy(os.path.abspath(self.test_banzai_rms_file), self.test_dir)
        self.test_banzai_rms_file = os.path.join(self.test_dir, os.path.basename(self.test_banzai_rms_file))

        """swarp_neox.conf"""
        shutil.copy(os.path.abspath(os.path.join(self.source_dir, 'swarp_neox.conf')), self.test_dir)
        self.test_conf_file = os.path.join(self.test_dir, 'swarp_neox.conf')

        self.remove = True

    def test_doesnotexist(self):
        expected_status = -11

        status = create_weight_image('banana.fits')

        self.assertEqual(expected_status, status)

    def test_badfitsfile(self):
        expected_status = -12

        bad_file = os.path.join(self.source_dir, 'swarp_neox.conf')
        status = create_weight_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_noscihdu(self):
        expected_status = -13

        status = create_weight_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_nobpmhdu(self):
        expected_status = -14

        with fits.open(self.test_fits_file) as hdulist:
            # Rename the 'PRIMARY' HDU to 'SCI'
            header = hdulist[0].header
            header['EXTNAME'] = 'SCI'
            hdulist.writeto(self.test_fits_file, overwrite=True, checksum=True)

        status = create_weight_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_does_not_contain_fits(self):
        # A fits file that has all the correct HDUs and an rms file, but somehow does not contain ".fits"
        expected_status = -15

        bad_file = self.test_banzai_comp_file.replace(".fits.fz", ".pear")
        os.rename(self.test_banzai_comp_file, bad_file)

        status = create_weight_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_rms_doesnotexist(self):
        expected_status = -16

        os.remove(self.test_banzai_rms_file)
        status = create_weight_image(self.test_banzai_file)

        self.assertEqual(expected_status, status)

    def test_rms_badfitsfile(self):
        # Rename a non-fits file to be the rms file
        expected_status = -17

        good_file = self.test_banzai_file
        bad_rms = self.test_conf_file
        os.replace(bad_rms, self.test_banzai_rms_file)

        status = create_weight_image(good_file)

        self.assertEqual(expected_status, status)

    def test_rms_badhdus(self):
        #Wrong number of HDUs in the rms file
        expected_status = -18

        good_file = self.test_banzai_file
        bad_rms = self.test_banzai_comp_file
        os.replace(bad_rms, self.test_banzai_rms_file)

        status = create_weight_image(good_file)

        self.assertEqual(expected_status, status)


    def test_does_not_modify_input(self):
        expected_filename = self.test_banzai_file.replace(".fits", ".weights.fits")

        weight_filename = create_weight_image(self.test_banzai_file)

        self.assertEqual(expected_filename, weight_filename)

        # Ensuring that the input file has NOT been overwritten with the weight data
        header = fits.getheader(self.test_banzai_file, 0)
        self.assertEqual('SCI', header.get('EXTNAME', ''))
        self.assertTrue('L1FRMTYP' not in header)
        self.assertNotEqual('WEIGHT', header.get('L1FRMTYP', ''))

        header = fits.getheader(weight_filename, 0)
        self.assertEqual('', header.get('EXTNAME', ''))
        self.assertEqual('WEIGHT', header.get('L1FRMTYP', ''))

    def test_success(self):
        expected_filename = self.test_banzai_file.replace(".fits", ".weights.fits")

        weight_filename = create_weight_image(self.test_banzai_file)

        self.assertEqual(expected_filename, weight_filename)


        with fits.open(weight_filename) as hdul:
            header = hdul[0].header
            data = hdul[0].data

        self.assertEqual('', header.get('EXTNAME', ''))
        self.assertEqual('WEIGHT', header.get('L1FRMTYP', ''))
        # Test whether saturated pixels are 0.0
        assert_allclose(0.0, data[444, 394])
        # Test whether bad pixels are 0.0
        assert_allclose(0.0, data[1653:1663, 458])
        # Test whether central pixel is nonzero
        assert_allclose(0.0009511118, data[int(header['NAXIS1']/2), int(header['NAXIS2']/2)])


class TestCreateRMSImage(ExternalCodeUnitTest):
    def setUp(self):
        super(TestCreateRMSImage, self).setUp()
        self.test_fits_weight_file = os.path.join(self.testfits_dir, 'example-sbig-e10.weight.fits')

        """example-sbig-e10.fits"""
        # This image only has a 'PRIMARY' HDU
        shutil.copy(os.path.abspath(self.test_fits_file), self.test_dir)
        self.test_fits_file = os.path.join(self.test_dir, os.path.basename(self.test_fits_file))

        """example-sbig-e10.weight.fits"""
        shutil.copy(os.path.abspath(self.test_fits_weight_file), self.test_dir)
        self.test_fits_weight_file = os.path.join(self.test_dir, os.path.basename(self.test_fits_weight_file))

        """swarp_neox.conf"""
        shutil.copy(os.path.abspath(os.path.join(self.source_dir, 'swarp_neox.conf')), self.test_dir)
        self.test_conf_file = os.path.join(self.test_dir, 'swarp_neox.conf')

        self.remove = True

    def test_doesnotexist(self):
        expected_status = -11

        status = create_rms_image('banana.fits')

        self.assertEqual(expected_status, status)

    def test_badfitsfile(self):
        expected_status = -12

        bad_file = os.path.join(self.source_dir, 'swarp_neox.conf')
        status = create_rms_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_does_not_contain_fits(self):
        # A fits file that somehow does not contain ".fits"
        expected_status = -15

        bad_file = self.test_fits_file.replace(".fits", ".pear")
        os.rename(self.test_fits_file, bad_file)

        status = create_rms_image(bad_file)

        self.assertEqual(expected_status, status)

    def test_weight_doesnotexist(self):
        expected_status = -16

        os.remove(self.test_fits_weight_file)
        status = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_weight_badfitsfile(self):
        # Rename a non-fits file to be the weight file
        expected_status = -17

        good_file = self.test_fits_file
        bad_weight = self.test_conf_file
        os.replace(bad_weight, self.test_fits_weight_file)

        status = create_rms_image(good_file)

        self.assertEqual(expected_status, status)

    def test_weight_badhdus(self):
        #Wrong number of HDUs in the weight file
        expected_status = -18

        fits.append(self.test_fits_weight_file, np.empty(0))

        status = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_status, status)

    def test_does_not_modify_input(self):
        expected_filename = self.test_fits_weight_file.replace(".weight.fits", ".rms.fits")

        rms_filename = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_filename, rms_filename)

        # Ensuring that the input file has NOT been overwritten with the weight data
        header = fits.getheader(self.test_fits_file, 0)
        self.assertTrue('L1FRMTYP' not in header)

        header = fits.getheader(rms_filename, 0)
        self.assertTrue('L1FRMTYP' in header)

    def test_success(self):
        expected_filename = self.test_fits_weight_file.replace(".weight.fits", ".rms.fits")

        rms_filename = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_filename, rms_filename)

        with fits.open(rms_filename) as hdul:
            header = hdul[0].header
            data = hdul[0].data

        self.assertEqual('RMS', header.get('L1FRMTYP', ''))
        # Test whether saturated pixels have appropriate RMS value
        assert_allclose(223.6068, data[1000, 458])
        # Test whether central pixel is not saturated
        assert_allclose(25.846653, data[int(header['NAXIS1']/2), int(header['NAXIS2']/2)])

    def test_modified_MAXLIN(self):
        #manually override the MAXLIN value in the test image to make sure it's working right
        expected_filename = self.test_fits_weight_file.replace(".weight.fits", ".rms.fits")

        #sci_header = fits.getheader(self.test_fits_file)
        #sci_header['MAXLIN'] = 40000

        fits.setval(self.test_fits_file, 'MAXLIN', value=10000)

        rms_filename = create_rms_image(self.test_fits_file)

        self.assertEqual(expected_filename, rms_filename)

        with fits.open(rms_filename) as hdul:
            header = hdul[0].header
            data = hdul[0].data

        self.assertEqual('RMS', header.get('L1FRMTYP', ''))
        # Test whether saturated pixels have appropriate RMS value
        assert_allclose(223.6068, data[1007, 367])
        # Test whether central pixel is not saturated
        assert_allclose(25.846653, data[int(header['NAXIS1']/2), int(header['NAXIS2']/2)])

class TestGetReferenceName(ExternalCodeUnitTest):

    def test_ra_1dig_dec_p1dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_+04.44.fits"

        status = get_reference_name(1.111, 4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_1dig_dec_p2dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_+84.44.fits"

        status = get_reference_name(1.111, 84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_1dig_dec_m1dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_-04.44.fits"

        status = get_reference_name(1.111, -4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_1dig_dec_m2dig(self):
        expected_status = "reference_lsc_fa15_w_001.11_-84.44.fits"

        status = get_reference_name(1.111, -84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_p1dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_+04.44.fits"

        status = get_reference_name(11.111, 4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_p2dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_+84.44.fits"

        status = get_reference_name(11.111, 84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_m1dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_-04.44.fits"

        status = get_reference_name(11.111, -4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_2dig_dec_m2dig(self):
        expected_status = "reference_lsc_fa15_w_011.11_-84.44.fits"

        status = get_reference_name(11.111, -84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_p1dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_+04.44.fits"

        status = get_reference_name(111.111, 4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_p2dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_+84.44.fits"

        status = get_reference_name(111.111, 84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_m1dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_-04.44.fits"

        status = get_reference_name(111.111, -4.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_ra_3dig_dec_m2dig(self):
        expected_status = "reference_lsc_fa15_w_111.11_-84.44.fits"

        status = get_reference_name(111.111, -84.444,  "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_bad_coords_type_string(self):
        expected_status = -1

        status = get_reference_name("string", "string", "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_bad_coords_type_int(self):
        expected_status = -1

        status = get_reference_name(1, 1, "lsc", "fa15", "w")

        self.assertEqual(expected_status, status)

    def test_bad_site_type(self):
        expected_status = -99

        status = get_reference_name(111.111, 4.444, 1, "fa15", "w")

        self.assertEqual(expected_status, status)


class TestFindReferenceImage(ExternalCodeUnitTest):
    def test1(self):
        newfile1 = os.path.join(self.test_dir, "reference_222.22_-33.33_cpt_w.fits")
        newfile2 = os.path.join(self.test_dir, "reference_444.44_-55.55_lsc_rp.fits")
        newfile3 = os.path.join(self.test_dir, "cpt1m0.fits")
        Path(newfile1).touch()
        Path(newfile2).touch()
        Path(newfile3).touch()

        expected_output = [newfile1, newfile2]

        output = find_reference_images(self.test_dir, "reference*.fits")

        self.assertEqual(expected_output, output)

    def test2(self):
        newfile1 = os.path.join(self.test_dir, "reference_222.22_-33.33_cpt_w.fits")
        newfile2 = os.path.join(self.test_dir, "reference_444.44_-55.55_lsc_rp.fits")
        newfile3 = os.path.join(self.test_dir, "cpt1m0.fits")
        Path(newfile1).touch()
        Path(newfile2).touch()
        Path(newfile3).touch()

        expected_output = [newfile1]

        output = find_reference_images(self.test_dir, "reference*cpt*.fits")

        self.assertEqual(expected_output, output)
