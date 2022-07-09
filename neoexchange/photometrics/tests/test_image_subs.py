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


        hdul = fits.open(weight_filename)
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
