"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

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
import shutil
import tempfile
from collections import OrderedDict

from django.test import TestCase
from astropy import units as u
from astropy.io.fits import Header
import numpy as np

from photometrics.spectraplot import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)


class TestReadSpectra(TestCase):

    def setUp(self):

        self.spectradir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))

        self.fitsfile = 'test_2df_ex.fits'
        self.asciifile = 'test_ascii.ascii'
        self.txtfile = 'a001981.4.txt'
        self.datfile = 'ctiostan.fhr9087.dat'

        files_to_copy = [self.fitsfile, self.asciifile, self.txtfile, self.datfile, 'aaareadme.ctio']

        self.tolerance = 1

        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        for test_file in files_to_copy:
            test_file_path = os.path.join(self.spectradir, test_file)
            shutil.copy(test_file_path, self.test_dir)

        self.fitsfile = os.path.join(self.test_dir, self.fitsfile)
        self.asciifile = os.path.join(self.test_dir, self.asciifile)
        self.txtfile = os.path.join(self.test_dir, self.txtfile)
        self.datfile = os.path.join(self.test_dir, self.datfile)

        self.remove = True
        self.debug_print = False

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

    def test_read_fits_x(self):
        exp_x = 3103.14013672
        exp_x_units = u.AA
        exp_x_len = 4560

        with self.settings(MEDIA_ROOT=self.test_dir):
            x_data = pull_data_from_spectrum(self.fitsfile)[0]

        self.assertEqual(exp_x_len, len(x_data))
        self.assertAlmostEqual(exp_x, x_data[0].value, self.tolerance)
        self.assertEqual(exp_x_units, x_data[0].unit)

    def test_read_fits_y(self):
        exp_y = 10.494265/10**20
        exp_y_units = u.erg/(u.cm**2)/u.s/u.AA
        exp_y_len = 4560

        with self.settings(MEDIA_ROOT=self.test_dir):
            y_data = pull_data_from_spectrum(self.fitsfile)[1]

        self.assertEqual(exp_y_len, len(y_data))
        self.assertAlmostEqual(exp_y, y_data[-1].value, self.tolerance)
        self.assertEqual(exp_y_units, y_data[-1].unit)

    def test_read_txt_x(self):
        exp_x = 3600
        exp_x_units = u.AA
        exp_x_len = 257

        with self.settings(MEDIA_ROOT=self.test_dir):
            x_data = pull_data_from_text(self.txtfile)[0]

        self.assertEqual(exp_x_len, len(x_data))
        self.assertAlmostEqual(exp_x, x_data[0].value, self.tolerance)
        self.assertEqual(exp_x_units, x_data[0].unit)

    def test_read_txt_y(self):
        exp_y = .5605
        exp_y_units = u.dimensionless_unscaled
        exp_y_len = 257

        with self.settings(MEDIA_ROOT=self.test_dir):
            y_data = pull_data_from_text(self.txtfile)[1]

        self.assertEqual(exp_y_len, len(y_data))
        self.assertAlmostEqual(exp_y, y_data[0].value, self.tolerance)
        self.assertEqual(exp_y_units, y_data[0].unit)

    def test_read_txt_error(self):
        exp_y_err = .0046
        exp_y_err_len = 257

        with self.settings(MEDIA_ROOT=self.test_dir):
            y_err = pull_data_from_text(self.txtfile)[2]

        self.assertEqual(exp_y_err_len, len(y_err))
        self.assertAlmostEqual(exp_y_err, y_err[0], self.tolerance)

    def test_read_dat_file(self):
        exp_x = 3300
        exp_x_units = u.AA
        exp_x_len = 445
        exp_y = 7.1022E+05/10**16
        exp_y_units = u.erg/(u.cm**2)/u.s/u.AA
        exp_y_len = 445

        with self.settings(MEDIA_ROOT=self.test_dir):
            x_data, y_data, extra = pull_data_from_text(self.datfile)

        self.assertEqual(exp_x_len, len(x_data))
        self.assertAlmostEqual(exp_x, x_data[0].value, self.tolerance)
        self.assertEqual(exp_x_units, x_data[0].unit)
        self.assertEqual(exp_y_len, len(y_data))
        self.assertAlmostEqual(exp_y, y_data[0].value, self.tolerance)
        self.assertEqual(exp_y_units, y_data[0].unit)

    def test_get_x_units(self):
        test_x_data1 = [3103.14013672, 3104.88222365, 3106.62431058]  # given x range expected for Angstroms
        test_x_data2 = [0.435, 0.4375, 0.44]  # given x range expected for microns
        test_x_data3 = [404, 404.5, 405]  # given x range expected for nm
        test_x_data4 = [15, 16, 17]  # given nonsense
        test_x_data5 = [1500, 800, 500]  # given expected x range for nm, but not in order

        exp_x1 = u.AA
        val_x1 = [3103.14013672, 3104.88222365, 3106.62431058]
        x1 = get_x_units(test_x_data1)
        exp_x2 = u.AA
        val_x2 = [4350, 4375, 4400]
        x2 = get_x_units(test_x_data2)
        exp_x3 = u.AA
        val_x3 = [4040, 4045, 4050]
        x3 = get_x_units(test_x_data3)
        exp_x4 = u.AA
        val_x4 = [15, 16, 17]
        x4 = get_x_units(test_x_data4)
        exp_x5 = u.AA
        val_x5 = [15000, 8000, 5000]
        x5 = get_x_units(test_x_data5)

        self.assertEqual(exp_x1, x1[0].unit)
        self.assertEqual(exp_x2, x2[0].unit)
        self.assertEqual(exp_x3, x3[0].unit)
        self.assertEqual(exp_x4, x4[0].unit)
        self.assertEqual(exp_x5, x5[0].unit)
        self.assertAlmostEqual(val_x1[0], x1[0].value, self.tolerance)
        self.assertAlmostEqual(val_x2[0], x2[0].value, self.tolerance)
        self.assertAlmostEqual(val_x3[0], x3[0].value, self.tolerance)
        self.assertAlmostEqual(val_x4[0], x4[0].value, self.tolerance)
        self.assertAlmostEqual(val_x5[0], x5[0].value, self.tolerance)

    def test_smoothing(self):
        with self.settings(MEDIA_ROOT=self.test_dir):
            test_x_data, test_y_data, header, error = pull_data_from_spectrum(self.fitsfile)

        exp_y_len = len(test_y_data)

        smoothedy = smooth(test_y_data, 100)

        self.assertEqual(exp_y_len, len(smoothedy))


class TestBuildSpectra(TestCase):

    def setUp(self):

        self.spectradir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))

        self.fitsfile = 'target_2df_ex.fits'
        self.analogfile = 'analog_2df_ex.fits'

        files_to_copy = [self.fitsfile, self.analogfile]

        self.tolerance = 1

        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        for test_file in files_to_copy:
            test_file_path = os.path.join(self.spectradir, test_file)
            shutil.copy(test_file_path, self.test_dir)

        self.fitsfile = os.path.join(self.test_dir, self.fitsfile)
        self.analogfile = os.path.join(self.test_dir, self.analogfile)

        self.remove = True
        self.debug_print = False

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

    def test_spectrum_plot(self):
        expected_label = '455432 -- 20190727 (1.266) [ // ]'
        wav_range = [3100*u.AA, 10000*u.AA]
        expected_flux_mean = 0.7641197364877771
        expected_error_mean = 0.0008555421156313763

        with self.settings(MEDIA_ROOT=self.test_dir):
            label, flux, wavelength, error = spectrum_plot(self.fitsfile)

        self.assertEqual(expected_label, label)
        self.assertGreater(wav_range[1], max(wavelength))
        self.assertLess(wav_range[0], min(wavelength))
        self.assertEqual(np.mean(flux), expected_flux_mean)
        self.assertEqual(np.mean(error).value, expected_error_mean)

    def test_reflectance_plot(self):
        expected_label = '455432 -- HD 196164 -- 20190727'
        wav_range = [4000*u.AA, 10000*u.AA]
        expected_flux_mean = 1.0377393269850517
        expected_error_mean = 0.001171595630670704

        with self.settings(MEDIA_ROOT=self.test_dir):
            label, flux, wavelength, error = spectrum_plot(self.fitsfile, analog=self.analogfile)

        self.assertEqual(expected_label, label)
        self.assertGreater(wav_range[1], max(wavelength))
        self.assertLess(wav_range[0], min(wavelength))
        self.assertEqual(np.mean(flux), expected_flux_mean)
        self.assertEqual(np.mean(error), expected_error_mean)


