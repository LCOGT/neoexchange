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
        self.fitsdir  = os.getcwd()+'/photometrics/tests/test_spectra/'
        self.fitsfile = 'test_fits.fits'
        self.asciidir = os.getcwd()+'/photometrics/tests/test_spectra/'
        self.asciifile= 'test_ascii.ascii'
        self.txtdir   = os.getcwd()+'/photometrics/tests/test_spectra/'
        self.txtfile  = 'a001981.4.txt'
        self.datdir   = os.getcwd()+'/photometrics/tests/test_spectra/'
        self.datfile  = 'fhr9087.dat'

        self.tolerance = 1

    def test_read_fits_x(self):
        exp_x = 3103.14013672
        exp_x_units = u.AA
        exp_x_len = 4560

        x_data = read_spectra(self.fitsdir, self.fitsfile)[0].value
        x_units = read_spectra(self.fitsdir, self.fitsfile)[3]

        self.assertEqual(exp_x_len, len(x_data))
        self.assertAlmostEqual(exp_x, x_data[0], self.tolerance)
        self.assertEqual(exp_x_units, x_units)

    def test_read_fits_y(self):
        exp_y = 10.494265/10**20
        exp_y_units = u.erg/(u.cm**2)/u.s/u.AA
        exp_y_len = 4560

        y_data = read_spectra(self.fitsdir, self.fitsfile)[1].value
        y_units = read_spectra(self.fitsdir, self.fitsfile)[4]

        self.assertEqual(exp_y_len, len(y_data))
        self.assertAlmostEqual(exp_y, y_data[-1], self.tolerance)
        self.assertEqual(exp_y_units, y_units)

    def test_read_fits_error(self):
        exp_y_err = 3.2439897
        exp_y_err_len = 4560
        y_err = read_spectra(self.fitsdir, self.fitsfile)[2]

        self.assertEqual(exp_y_err_len, len(y_err))
        self.assertAlmostEqual(exp_y_err, y_err[0], self.tolerance)

    def test_read_ascii_x(self):
        exp_x = 4350
        exp_x_units = u.micron
        exp_x_len = 212

        x_data = read_spectra(self.asciidir, self.asciifile)[0].value
        x_units = read_spectra(self.asciidir, self.asciifile)[3]

        self.assertEqual(exp_x_len, len(x_data))
        self.assertAlmostEqual(exp_x, x_data[0], self.tolerance)
        self.assertEqual(exp_x_units, x_units)

    def test_read_ascii_y(self):
        exp_y = .7756
        exp_y_units = u.dimensionless_unscaled
        exp_y_len = 212

        y_data = read_spectra(self.asciidir, self.asciifile)[1].value
        y_units = read_spectra(self.asciidir, self.asciifile)[4]

        self.assertEqual(exp_y_len, len(y_data))
        self.assertAlmostEqual(exp_y, y_data[0], self.tolerance)
        self.assertEqual(exp_y_units, y_units)

    def test_read_ascii_error(self):
        exp_y_err = 0.0116
        exp_y_err_len = 212
        y_err = read_spectra(self.asciidir, self.asciifile)[2]

        self.assertEqual(exp_y_err_len, len(y_err))
        self.assertAlmostEqual(exp_y_err, y_err[0], self.tolerance)

    def test_read_txt_x(self):
        exp_x = 3600
        exp_x_units = u.micron
        exp_x_len = 257

        x_data = read_spectra(self.txtdir, self.txtfile)[0].value
        x_units = read_spectra(self.txtdir, self.txtfile)[3]

        self.assertEqual(exp_x_len, len(x_data))
        self.assertAlmostEqual(exp_x, x_data[0], self.tolerance)
        self.assertEqual(exp_x_units, x_units)

    def test_read_txt_y(self):
        exp_y = .5605
        exp_y_units = u.dimensionless_unscaled
        exp_y_len = 257

        y_data = read_spectra(self.txtdir, self.txtfile)[1].value
        y_units = read_spectra(self.txtdir, self.txtfile)[4]

        self.assertEqual(exp_y_len, len(y_data))
        self.assertAlmostEqual(exp_y, y_data[0], self.tolerance)
        self.assertEqual(exp_y_units, y_units)

    def test_read_txt_error(self):
        exp_y_err = .0046
        exp_y_err_len = 257
        y_err = read_spectra(self.txtdir, self.txtfile)[2]
        self.assertEqual(exp_y_err_len, len(y_err))
        self.assertAlmostEqual(exp_y_err, y_err[0], self.tolerance)

    def test_read_dat_x(self):
        exp_x = 3300
        exp_x_units = u.AA
        exp_x_len = 445

        x_data = read_spectra(self.datdir, self.datfile)[0].value
        x_units = read_spectra(self.datdir, self.datfile)[3]

        self.assertEqual(exp_x_len, len(x_data))
        self.assertAlmostEqual(exp_x, x_data[0], self.tolerance)
        self.assertEqual(exp_x_units, x_units)

    def test_read_dat_y(self):
        exp_y = 7.1022E+05/10**16
        exp_y_units = u.erg/(u.cm**2)/u.s/u.AA
        exp_y_len = 445

        y_data = read_spectra(self.datdir, self.datfile)[1].value
        y_units = read_spectra(self.datdir, self.datfile)[4]

        self.assertEqual(exp_y_len, len(y_data))
        self.assertAlmostEqual(exp_y, y_data[0], self.tolerance)
        self.assertEqual(exp_y_units, y_units)

    def test_read_dat_error(self):
        exp_y_err_len = 445
        y_err = read_spectra(self.datdir, self.datfile)[2]

        self.assertTrue(exp_y_err_len, len(y_err))
        self.assertTrue(np.isnan(y_err[0]))

    def test_read_fits_obj(self):
        exp_obj = '398188'

        obj_name = read_spectra(self.fitsdir, self.fitsfile)[5]

        self.assertEqual(exp_obj, obj_name)

    def test_read_txt_obj(self):
        exp_obj = '1981'

        obj_name = read_spectra(self.txtdir, self.txtfile)[5]

        self.assertEqual(exp_obj, obj_name)

    def test_read_dat_obj(self):
        exp_obj = 'hr9087'

        obj_name = read_spectra(self.datdir, self.datfile)[5]

        self.assertEqual(exp_obj, obj_name)

    def test_get_fits_y_units1(self):
        test_hdr1 = Header()
        test_hdr1.append(('BUNIT ', 'erg/cm2/s/A  10^20'))  # given valid key and unit and factor
        test_hdr2 = Header()
        test_hdr2.append(('TUNIT2', 'erg/cm2/s/A'))  # given valid key and unit
        test_hdr3 = Header()
        test_hdr3.append(('HI', 'LOL'))  # given invalid key and invalid unit
        test_hdr4 = Header()
        test_hdr4.append(('BUNIT', 'HI'))  # given valid keys and invalid unit
        test_hdr4.append(('TUNIT2', 'LOL'))
        test_hdr5 = Header()
        test_hdr5.append(('BUNIT', 'Normalized'))  # given valid key and norm unit
        exp_y5 = u.dimensionless_unscaled
        test_hdr6 = Header()
        test_hdr6.append(('BUNIT', 'FLAM'))  # given valid key and valid unit

        exp_y1 = u.erg/(u.cm**2)/u.s/u.AA
        exp_f1 = 1E+20
        y1, f1 = get_y_units(test_hdr1)
        exp_y2 = u.erg/(u.cm**2)/u.s/u.AA
        exp_f2 = 1
        y2, f2 = get_y_units(test_hdr2)
        exp_y3 = u.erg/(u.cm**2)/u.s/u.AA
        exp_f3 = 1
        y3, f3 = get_y_units(test_hdr3)
        exp_y4 = u.erg/(u.cm**2)/u.s/u.AA
        exp_f4 = 1
        y4, f4 = get_y_units(test_hdr4)
        exp_f5 = 1
        y5, f5 = get_y_units(test_hdr5)
        exp_y6 = u.erg/(u.cm**2)/u.s/u.AA
        exp_f6 = 1
        y6, f6 = get_y_units(test_hdr6)

        self.assertEqual(exp_y1, y1)
        self.assertEqual(exp_f1, f1)
        self.assertEqual(exp_y2, y2)
        self.assertEqual(exp_f2, f2)
        self.assertEqual(exp_y3, y3)
        self.assertEqual(exp_f3, f3)
        self.assertEqual(exp_y4, y4)
        self.assertEqual(exp_f4, f4)
        self.assertEqual(exp_y5, y5)
        self.assertEqual(exp_f5, f5)
        self.assertEqual(exp_y6, y6)
        self.assertEqual(exp_f6, f6)

    def test_get_ascii_y_units(self):
        test_dict1 = OrderedDict({'col1': 'microns', 'col2': 'erg/cm2/s/A', 'col3': 'error'})  # given valid x and y units
        test_dict2 = OrderedDict({'col1': 'microns', 'col2': 'Normalized', 'col3': 'error'})  # given valid x unit and norm y
        test_dict3 = OrderedDict({'col1': 'microns', 'col2': 'Normalized Reflectance', 'col3': 'error'})
        test_dict4 = OrderedDict({'col1': 'microns', 'col2': 'something else', 'col3': 'error'})  # given valid x unit and invalid y unit

        exp_y1 = u.erg/(u.cm**2)/u.s/u.AA
        exp_f1 = 1
        y1, f1 = get_y_units(test_dict1)
        exp_y2 = u.dimensionless_unscaled
        exp_f2 = 1
        y2, f2 = get_y_units(test_dict2)
        exp_y3 = u.dimensionless_unscaled
        exp_f3 = 1
        y3, f3 = get_y_units(test_dict3)
        exp_y4 = u.erg/(u.cm**2)/u.s/u.AA
        exp_f4 = 1
        y4, f4 = get_y_units(test_dict4)

        self.assertEqual(exp_y1, y1)
        self.assertEqual(exp_f1, f1)
        self.assertEqual(exp_y2, y2)
        self.assertEqual(exp_f2, f2)
        self.assertEqual(exp_y3, y3)
        self.assertEqual(exp_f3, f3)
        self.assertEqual(exp_y4, y4)
        self.assertEqual(exp_f4, f4)

    def test_get_x_units(self):
        test_x_data1 = [3103.14013672, 3104.88222365, 3106.62431058]  # given x range expected for Angstroms
        test_x_data2 = [0.435, 0.4375, 0.44]  # given x range expected for microns
        test_x_data3 = [404, 404.5, 405]  # given x range expected for nm
        test_x_data4 = [15, 16, 17]  # given nonsense
        test_x_data5 = [1500, 800, 500]  # given expected x range for nm, but not in order

        exp_x1 = u.AA
        x1 = get_x_units(test_x_data1)
        exp_x2 = u.micron
        x2 = get_x_units(test_x_data2)
        exp_x3 = u.nm
        x3 = get_x_units(test_x_data3)
        exp_x4 = u.AA
        x4 = get_x_units(test_x_data4)
        exp_x5 = u.nm
        x5 = get_x_units(test_x_data5)

        self.assertEqual(exp_x1, x1)
        self.assertEqual(exp_x2, x2)
        self.assertEqual(exp_x3, x3)
        self.assertEqual(exp_x4, x4)
        self.assertEqual(exp_x5, x5)

    def test_smoothing(self):
        test_x_data, test_y_data = read_spectra(self.fitsdir, self.fitsfile)[:2]
        exp_x_len = len(test_x_data)-30
        exp_y_len = len(test_y_data)-30

        smoothedx, smoothedy = smooth(test_x_data, test_y_data)

        self.assertEqual(exp_x_len, len(smoothedx))
        self.assertEqual(exp_y_len, len(smoothedy))

class TestGetSpecPlot(TestCase):
    
    def setUp(self):
        files_to_copy = ['fhr9087.dat', 'test_fits.fits', 'aaareadme.ctio', ]
        self.spectradir  = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))
        self.datfile  = files_to_copy[0]
        self.fitsfile  = files_to_copy[1]

        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        for test_file in files_to_copy:
            test_file_path = os.path.join(self.spectradir, test_file)
            shutil.copy(test_file_path, self.test_dir)

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

    def test_no_file(self):

        obs_num = '1'
        expected_save_file = None

        save_file = get_spec_plot(self.test_dir, 'foo.fits', obs_num)

        self.assertEqual(expected_save_file, save_file)

    def test_fits_1(self):

        obs_num = '1'
        expected_save_file = os.path.join(self.test_dir, '398188_1598411_spectra_' + obs_num + '.png')

        save_file = get_spec_plot(self.test_dir, self.fitsfile, obs_num)

        self.assertEqual(expected_save_file, save_file)

    def test_ctiostan_1(self):

        obs_num = 1
        expected_save_file = os.path.join(self.test_dir, 'hr9087_spectra_' + str(obs_num) + '.png')

        save_file = get_spec_plot(self.test_dir, self.datfile, obs_num)

        self.assertEqual(expected_save_file, save_file)

    def test_fits_2(self):

        obs_num = '2'
        expected_save_file = os.path.join(self.test_dir, '398188_1598411_spectra_' + obs_num + '.png')

        save_file = get_spec_plot(self.test_dir, self.fitsfile, obs_num)

        self.assertEqual(expected_save_file, save_file)

    def test_ctiostan_2(self):

        obs_num = 2
        expected_save_file = os.path.join(self.test_dir, 'hr9087_spectra_' + str(obs_num) + '.png')

        save_file = get_spec_plot(self.test_dir, self.datfile, obs_num)

        self.assertEqual(expected_save_file, save_file)
