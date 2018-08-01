from django.test import TestCase
from astropy import units as u
import numpy as np
import os

from photometrics.spectraplot import *

class Test_Read_Spectra(TestCase):

    def setUp(self):
        self.fitsdir  = '/home/atedeschi/test_spectra/398188/'
        self.fitsfile = 'ntt398188_ftn_20180722_merge_6.0_58322_1_2df_ex.fits'
        self.asciidir = '/home/atedeschi/test_spectra/calspec/'
        self.asciifile= 'eros_visnir_reference_to1um.ascii'
        self.txtdir   = '/home/atedeschi/test_spectra/'
        self.txtfile  = 'a001981.4.txt'
        self.datdir   = '/home/atedeschi/test_spectra/calspec/'
        self.datfile  = 'fhr9087.dat'

        self.tolerance = 1

    def test_read_fits_x(self):
        exp_x = 3103.14013672
        exp_x_units = u.AA
        exp_x_len = 4560

        x_data = read_spectra(self.fitsdir,self.fitsfile)[0].value
        x_units = read_spectra(self.fitsdir,self.fitsfile)[3]

        self.assertEqual(exp_x_len,len(x_data))
        self.assertAlmostEqual(exp_x,x_data[0],self.tolerance)
        self.assertEqual(exp_x_units,x_units)

    def test_read_fits_y(self):
        exp_y = 10.494265
        exp_y_units = u.erg/(u.cm**2)/u.s/u.AA
        exp_y_len = 4560

        y_data = read_spectra(self.fitsdir,self.fitsfile)[1].value
        y_units = read_spectra(self.fitsdir,self.fitsfile)[4]

        self.assertEqual(exp_y_len,len(y_data))
        self.assertAlmostEqual(exp_y,y_data[-1],self.tolerance)
        self.assertEqual(exp_y_units,y_units)

    def test_read_fits_error(self):
        exp_y_err = 3.2439897
        exp_y_err_len = 4560
        y_err = read_spectra(self.fitsdir,self.fitsfile)[2]

        self.assertEqual(exp_y_err_len,len(y_err))
        self.assertAlmostEqual(exp_y_err,y_err[0],self.tolerance)

    def test_read_ascii_x(self):
        exp_x = 4350
        exp_x_units = u.micron
        exp_x_len = 212

        x_data = read_spectra(self.asciidir,self.asciifile)[0].value
        x_units = read_spectra(self.asciidir,self.asciifile)[3]

        self.assertEqual(exp_x_len,len(x_data))
        self.assertAlmostEqual(exp_x,x_data[0],self.tolerance)
        self.assertEqual(exp_x_units,x_units)

    def test_read_ascii_y(self):
        exp_y = .7756
        exp_y_units = u.dimensionless_unscaled
        exp_y_len = 212

        y_data = read_spectra(self.asciidir,self.asciifile)[1].value
        y_units = read_spectra(self.asciidir,self.asciifile)[4]

        self.assertEqual(exp_y_len,len(y_data))
        self.assertAlmostEqual(exp_y,y_data[0],self.tolerance)
        self.assertEqual(exp_y_units,y_units)

    def test_read_ascii_error(self):
        exp_y_err = 0.0116
        exp_y_err_len = 212
        y_err = read_spectra(self.asciidir,self.asciifile)[2]

        self.assertEqual(exp_y_err_len,len(y_err))
        self.assertAlmostEqual(exp_y_err,y_err[0],self.tolerance)

    def test_read_txt_x(self):
        exp_x = 3600
        exp_x_units = u.micron
        exp_x_len = 257

        x_data = read_spectra(self.txtdir,self.txtfile)[0].value
        x_units = read_spectra(self.txtdir,self.txtfile)[3]

        self.assertEqual(exp_x_len,len(x_data))
        self.assertAlmostEqual(exp_x,x_data[0],self.tolerance)
        self.assertEqual(exp_x_units,x_units)

    def test_read_txt_y(self):
        exp_y = .5605
        exp_y_units = u.dimensionless_unscaled
        exp_y_len = 257

        y_data = read_spectra(self.txtdir,self.txtfile)[1].value
        y_units = read_spectra(self.txtdir,self.txtfile)[4]

        self.assertEqual(exp_y_len,len(y_data))
        self.assertAlmostEqual(exp_y,y_data[0],self.tolerance)
        self.assertEqual(exp_y_units,y_units)

    def test_read_txt_error(self):
        exp_y_err = .0046
        exp_y_err_len = 257
        y_err = read_spectra(self.txtdir,self.txtfile)[2]

        self.assertEqual(exp_y_err_len,len(y_err))
        self.assertAlmostEqual(exp_y_err,y_err[0],self.tolerance)

    def test_read_dat_x(self):
        exp_x = 3300
        exp_x_units = u.AA
        exp_x_len = 445

        x_data = read_spectra(self.datdir,self.datfile)[0].value
        x_units = read_spectra(self.datdir,self.datfile)[3]

        self.assertEqual(exp_x_len,len(x_data))
        self.assertAlmostEqual(exp_x,x_data[0],self.tolerance)
        self.assertEqual(exp_x_units,x_units)

    def test_read_dat_y(self):
        exp_y = 7.1022E+05
        exp_y_units = u.erg/(u.cm**2)/u.s/u.AA
        exp_y_len = 445

        y_data = read_spectra(self.datdir,self.datfile)[1].value
        y_units = read_spectra(self.datdir,self.datfile)[4]

        self.assertEqual(exp_y_len,len(y_data))
        self.assertAlmostEqual(exp_y,y_data[0],self.tolerance)
        self.assertEqual(exp_y_units,y_units)

    def test_read_txt_error(self):
        exp_y_err_len = 445
        y_err = read_spectra(self.datdir,self.datfile)[2]

        self.assertTrue(exp_y_err_len,len(y_err))
        self.assertTrue(np.isnan(y_err[0]))
