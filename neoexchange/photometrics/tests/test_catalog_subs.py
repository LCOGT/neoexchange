'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime, timedelta
from unittest import skipIf
from math import sqrt, log10, log
import os

import mock
from django.test import TestCase
from django.forms.models import model_to_dict
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import Angle
import astropy.units as u

from core.models import Body

#Import module to test
from photometrics.catalog_subs import *

class FITSUnitTest(TestCase):
    def __init__(self, *args, **kwargs):
        super(FITSUnitTest, self).__init__(*args, **kwargs)

    def setUp(self):
        # Read in example FITS source catalog
        self.test_filename = os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits')
        hdulist = fits.open(self.test_filename)
        self.test_header = hdulist[0].header
        self.test_table = hdulist[1].data
        hdulist.close()
        self.table_firstitem = self.test_table[0:1]
        self.table_lastitem = self.test_table[-1:]
        self.table_item_flags24 = self.test_table[2:3]

        self.test_ldacfilename = os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits')
        hdulist = fits.open(self.test_ldacfilename)
        self.test_ldactable = hdulist[2].data
        hdulist.close()
        self.ldac_table_firstitem = self.test_ldactable[0:1]

        column_types = [('ccd_x', '>f4'), 
                        ('ccd_y', '>f4'), 
                        ('obs_ra', '>f8'), 
                        ('obs_dec', '>f8'), 
                        ('obs_ra_err', '>f8'), 
                        ('obs_dec_err', '>f8'), 
                        ('major_axis', '>f4'), 
                        ('minor_axis', '>f4'), 
                        ('ccd_pa', '>f4'), 
                        ('obs_mag', '>f4'), 
                        ('obs_mag_err', '>f4'), 
                        ('obs_sky_bkgd', '>f4'), 
                        ('flags', '>i2')
                       ]
        self.basic_table = Table(dtype = column_types)

        self.maxDiff = None
        self.precision = 7

        self.flux2mag = 2.5/log(10)

    def compare_tables(self, expected_catalog, catalog, precision = 4):
        for column in expected_catalog.colnames:
            self.assertAlmostEqual(expected_catalog[column], catalog[column], precision, \
                msg="Failure on %s (%.*f != %.*f)" % (column, precision, expected_catalog[column], \
                    precision, catalog[column]))

class OpenFITSCatalog(FITSUnitTest):


    def test_catalog_does_not_exist(self):
        expected_hdr = {}
        expected_tbl = {}

        hdr, tbl = open_fits_catalog('wibble')

        self.assertEqual(expected_hdr, hdr)
        self.assertEqual(expected_tbl, tbl)

    def test_catalog_is_not_FITS(self):
        expected_hdr = {}
        expected_tbl = {}

        hdr, tbl = open_fits_catalog(os.path.join('photometrics', 'tests', '__init__.py'))

        self.assertEqual(expected_hdr, hdr)
        self.assertEqual(expected_tbl, tbl)

    def test_catalog_read_length(self):
        expected_hdr_len = len(self.test_header)
        expected_tbl_len = len(self.test_table)

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))

    def test_catalog_read_hdr_keyword(self):
        expected_hdr_value = self.test_header['INSTRUME']

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])

    def test_catalog_read_tbl_column(self):
        expected_tbl_value = 'X_IMAGE'
        expected_tbl_units = 'pixel'

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertEqual(expected_tbl_value, tbl.columns[1].name)
        self.assertEqual(expected_tbl_units, tbl.columns[1].unit)

    def test_catalog_read_xy(self):
        # X,Y CCD Co-ordinates of the last detection
        expected_x = 1067.9471
        expected_y = 1973.7445

        hdr, tbl = open_fits_catalog(self.test_filename)

        self.assertAlmostEqual(expected_x, tbl[-1]['X_IMAGE'], 4)
        self.assertAlmostEqual(expected_y, tbl[-1]['Y_IMAGE'], 4)

    def test_ldac_read_catalog(self):
        unexpected_value = {}

        hdr, tbl = open_fits_catalog(self.test_ldacfilename)
        self.assertNotEqual(unexpected_value, hdr)
        self.assertNotEqual(unexpected_value, tbl)

    def test_ldac_catalog_read_length(self):
        expected_hdr_len = 293 + 46
        expected_tbl_len = len(self.test_ldactable)

        hdr, tbl = open_fits_catalog(self.test_ldacfilename)

        self.assertEqual(expected_hdr_len, len(hdr))
        self.assertEqual(expected_tbl_len, len(tbl))

    def test_ldac_catalog_header(self):
        outpath = os.path.join("photometrics", "tests")
        expected_header = fits.Header.fromfile(os.path.join(outpath,"test_header"), sep='\n', endcard=False, padding=False)

        hdr, tbl = open_fits_catalog(self.test_ldacfilename)

        for key in expected_header:
            self.assertEqual(expected_header[key], hdr[key], \
                msg="Failure on %s (%s != %s)" % (key, expected_header[key], hdr[key]))

    def test_ldac_catalog_read_hdr_keyword(self):
        expected_hdr_value = 'fl03'

        hdr, tbl = open_fits_catalog(self.test_ldacfilename)

        self.assertEqual(expected_hdr_value, hdr['INSTRUME'])

    def test_catalog_read_tbl_column(self):
        expected_tbl_value = 'XWIN_IMAGE'
        expected_tbl_units = 'pixel'

        hdr, tbl = open_fits_catalog(self.test_ldacfilename)

        self.assertEqual(expected_tbl_value, tbl.columns[1].name)
        self.assertEqual(expected_tbl_units, tbl.columns[1].unit)

    def test_ldac_catalog_read_xy(self):
        # X,Y CCD Co-ordinates of the last detection
        expected_x = 1134.2564770504712
        expected_y = 2992.2858194541695

        hdr, tbl = open_fits_catalog(self.test_ldacfilename)

        self.assertAlmostEqual(expected_x, tbl[-1]['XWIN_IMAGE'], self.precision)
        self.assertAlmostEqual(expected_y, tbl[-1]['YWIN_IMAGE'], self.precision)

class Test_Convert_Values(FITSUnitTest):

    def test_dateobs_conversion(self):

        expected_value = datetime(2016, 2, 22, 19, 16, 42, 664000)

        value = convert_value('obs_date' , self.test_header['DATE-OBS'])

        self.assertEqual(expected_value, value)

    def test_dateobs_no_frac_seconds(self):

        expected_value = datetime(2016, 2, 22, 19, 16, 42)

        value = convert_value('obs_date' , '2016-02-22T19:16:42')

        self.assertEqual(expected_value, value)

    def test_bad_astrometric_rms(self):

        expected_value = None

        value = convert_value('astrometric_fit_rms' , '-99/-99 ')

        self.assertEqual(expected_value, value)

    def test_avg_astrometric_rms(self):

        expected_value = 0.15

        value = convert_value('astrometric_fit_rms' , '0.16/0.14 ')

        self.assertAlmostEqual(expected_value, value, 4)

    def test_astrometric_catalog(self):

        expected_value = 'UCAC3'

        value = convert_value('astrometric_catalog' , 'UCAC3@CDS ')

        self.assertEqual(expected_value, value)

    def test_no_conversion(self):

        expected_value = 100.0

        value = convert_value('exptime' , self.test_header['EXPTIME'])

        self.assertEqual(expected_value, value)

    def test_flux_to_mag(self):

        expected_value = -7.5

        value = convert_value('obs_mag' , 1000.0)

        self.assertEqual(expected_value, value)

    def test_negflux_to_mag(self):

        expected_value = -1.5

        value = convert_value('obs_mag' , -1.5)

        self.assertEqual(expected_value, value)

    def test_flux_to_magerr(self):

        expected_value = self.flux2mag * (10.0/360.0)

        value = convert_value('obs_mag_err' , (10.0, 360.0))

        self.assertEqual(expected_value, value)

    def test_ra_to_decimal_degrees(self):

        expected_value = 86.7366375 #conversion of 05:46:56.793 to decimal degrees

        value = convert_value('field_center_ra', '05:46:56.793')

        self.assertAlmostEqual(expected_value, value, 7)

    def test_dec_to_decimal_degrees(self):

        expected_value = -27.7043417 #conversion of -27:42:15.63 to decimal degrees

        value = convert_value('field_center_dec', '-27:42:15.63')

        self.assertAlmostEqual(expected_value, value, 7)

    def test_field_width(self):

        expected_value = '15.7846m' #2028 pixels x 0.467"/pixel converted to arcmin

        value = convert_value('field_width', (2028, 0.467))

        self.assertEqual(expected_value, value)

    def test_field_height(self):

        expected_value = '15.8624m' #2038 pixels x 0.467"/pixel converted to arcmin

        value = convert_value('field_height', (2038, 0.467))

        self.assertEqual(expected_value, value)

class FITSReadHeader(FITSUnitTest):

    def test_header(self):

        obs_date = datetime.strptime(self.test_header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S.%f')
        expected_params = { 'site_code'  : 'K92',
                            'instrument' : self.test_header['INSTRUME'],
                            'filter'     : self.test_header['FILTER'],
                            'framename'  : self.test_header['ORIGNAME'],
                            'exptime'    : self.test_header['EXPTIME'],
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=self.test_header['EXPTIME'] / 2.0),
                            'field_center_ra' : Angle(self.test_header['RA'], unit=u.hour).deg,
                            'field_center_dec' : Angle(self.test_header['DEC'], unit=u.deg).deg,
                            'field_width'   : '15.7846m',
                            'field_height'  : '15.8624m',
                            'pixel_scale'   : self.test_header['SECPIX'],
                            'zeropoint'     : self.test_header['L1ZP'],
                            'zeropoint_err' : self.test_header['L1ZPERR'],
                            'zeropoint_src' : self.test_header['L1ZPSRC'],
                            'fwhm'          : self.test_header['L1FWHM'],
                            'astrometric_fit_rms'    : None,
                            'astrometric_fit_status' : self.test_header['WCSERR'],
                            'astrometric_fit_nstars' : self.test_header['WCSMATCH'],
                            'astrometric_catalog'    : 'UCAC3',
                            'gain'          : self.test_header['GAIN'],
                            'saturation'    : self.test_header['SATURATE'],
                          }

        header, table = open_fits_catalog(self.test_filename)
        frame_header = get_catalog_header(header)

        self.assertEqual(expected_params, frame_header)

    def test_ldac_header(self):
        obs_date = datetime.strptime('2016-03-04T05:30:56.261', '%Y-%m-%dT%H:%M:%S.%f')
        expected_params = { 'site_code'  : 'W86',
                            'instrument' : 'fl03',
                            'filter'     : 'rp',
                            'framename'  : 'lsc1m009-fl03-20160303-0170-e00.fits',
                            'exptime'    : 120.0,
                            'obs_date'      : obs_date,
                            'obs_midpoint'  : obs_date + timedelta(seconds=120.0 / 2.0),
                            'field_center_ra'  : Angle('11:53:17.856', unit=u.hour).deg,
                            'field_center_dec' : Angle('+11:41:59.53', unit=u.deg).deg,
                            'field_width'   : '26.0969m',
                            'field_height'  : '25.8111m',
                            'pixel_scale'   : 0.3897,
                            'zeropoint'     : 28.55,
                            'zeropoint_err' : 0.0,
                            'zeropoint_src' : 'NOT_FIT(LCOGTCAL-V0.0.2-r8174)',
                            'fwhm'          : 2.42,
                            'astrometric_fit_rms'    : (0.21994+0.19797)/2.0,
                            'astrometric_fit_status' : 0,
                            'astrometric_fit_nstars' : 64,
                            'astrometric_catalog'    : 'UCAC4',
                          }

        header, table = open_fits_catalog(self.test_ldacfilename)
        frame_header = get_catalog_header(header, "FITS_LDAC")

        self.assertEqual(expected_params, frame_header)

class FITSSubsetCatalogTable(FITSUnitTest):

    def test_dimensions(self):
        expected_rows = 360
        expected_columns = 13

        hdr_mapping, tbl_mapping = oracdr_catalog_mapping()
        new_table = subset_catalog_table(self.test_table, tbl_mapping)

        self.assertEqual(expected_rows, len(new_table))
        self.assertEqual(expected_columns, len(new_table.colnames))

    def test_ldac_dimensions(self):
        expected_rows = 860
        expected_columns = 13

        hdr_mapping, tbl_mapping = fitsldac_catalog_mapping()
        new_table = subset_catalog_table(self.test_ldactable, tbl_mapping)

        self.assertEqual(expected_rows, len(new_table))
        self.assertEqual(expected_columns, len(new_table.colnames))

class FITSReadCatalog(FITSUnitTest):


    def test_first_item(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
                                   'ccd_y' :  18.61132812,
                                   'major_axis'  : 1.87925231,
                                   'minor_axis'  : 1.74675643,
                                   'ccd_pa'      : -79.38792419,
                                   'obs_ra'  :  86.868051829832439,
                                   'obs_dec' : -27.575127242664802,
                                   'obs_ra_err'  : 7.464116913258858e-06,
                                   'obs_dec_err' : 7.516842315248245e-06,
                                   'obs_mag'      : -2.5*log10(11228.246),
                                   'obs_mag_err'  : 0.037939535221954708,
                                   'obs_sky_bkgd' : 746.41577148,
                                   'flags' : 0,
                                 })

        catalog_items = get_catalog_items(self.test_header, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)


    def test_last_item(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 1067.94714355,
                                   'ccd_y' :  1973.74450684,
                                   'major_axis'  : 2.7380364,
                                   'minor_axis'  : 2.454973,
                                   'ccd_pa'      : 85.39698792,
                                   'obs_ra'  :  86.727294383019555,
                                   'obs_dec' : -27.82876912480173,
                                   'obs_ra_err'  : 1.5709768391021522e-06,
                                   'obs_dec_err' : 1.733559011455713e-06,
                                   'obs_mag' : -2.5*log10(215428.83),
                                   'obs_mag_err'  : self.flux2mag * self.table_lastitem['FLUXERR_AUTO']/self.table_lastitem['FLUX_AUTO'],
                                   'obs_sky_bkgd' : 744.8538208,
                                   'flags' : 0,
                                 })

        catalog_items = get_catalog_items(self.test_header, self.table_lastitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_reject_item_flags24(self):

        expected_catalog = self.basic_table

        catalog_items = get_catalog_items(self.test_header, self.table_item_flags24)

        self.assertEqual(len(expected_catalog), len(catalog_items))

    def test_accept_item_flags24(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' :  234.52952576,
                                   'ccd_y' :    8.05962372,
                                   'major_axis'  : 2.38448,
                                   'minor_axis'  : 2.3142395,
                                   'ccd_pa'      : 54.71178436,
                                   'obs_ra'  :  86.849261129458455,
                                   'obs_dec' : -27.573775115523741,
                                   'obs_ra_err'  : 3.1925407884572581e-06,
                                   'obs_dec_err' : 2.9221911507086037e-06,
                                   'obs_mag' : -2.5*log10(67883.703125),
                                   'obs_mag_err'  : self.flux2mag * self.table_item_flags24['FLUXERR_AUTO']/self.table_item_flags24['FLUX_AUTO'],
                                   'obs_sky_bkgd' :741.20977783,
                                   'flags' : 24,
                                 })

        catalog_items = get_catalog_items(self.test_header, self.table_item_flags24, flag_filter=24)

        for column in expected_catalog.colnames:
            self.assertAlmostEqual(expected_catalog[column], catalog_items[column], 9, \
                msg="Failure on %s (%s != %s)" % (column, expected_catalog[column], catalog_items[column]))

    def test_first_item_with_bad_zeropoint(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
                                   'ccd_y' :  18.61132812,
                                   'major_axis'  : 1.87925231,
                                   'minor_axis'  : 1.74675643,
                                   'ccd_pa'      : -79.38792419,
                                   'obs_ra'  :  86.868051829832439,
                                   'obs_dec' : -27.575127242664802,
                                   'obs_ra_err'  : 7.464116913258858e-06,
                                   'obs_dec_err' : 7.516842315248245e-06,
                                   'obs_mag'      : -2.5*log10(11228.246),
                                   'obs_mag_err'  : 0.037939535221954708,
                                   'obs_sky_bkgd' : 746.41577148,
                                   'flags' : 0,
                                 })

        header_items = {'zeropoint' : -99}
        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_first_item_with_good_zeropoint(self):

        header_items = {'zeropoint' : 23.0}
        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
                                   'ccd_y' :  18.61132812,
                                   'major_axis'  : 1.87925231,
                                   'minor_axis'  : 1.74675643,
                                   'ccd_pa'      : -79.38792419,
                                   'obs_ra'  :  86.868051829832439,
                                   'obs_dec' : -27.575127242664802,
                                   'obs_ra_err'  : 7.464116913258858e-06,
                                   'obs_dec_err' : 7.516842315248245e-06,
                                   'obs_mag'      : -2.5*log10(11228.246) + header_items['zeropoint'],
                                   'obs_mag_err'  : 0.037939535221954708,
                                   'obs_sky_bkgd' : 746.41577148,
                                   'flags' : 0,
                                 })

        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_first_item_with_no_zeropoint(self):

        header_items = {'zerowibble' : -99}
        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 106.11763763,
                                   'ccd_y' :  18.61132812,
                                   'major_axis'  : 1.87925231,
                                   'minor_axis'  : 1.74675643,
                                   'ccd_pa'      : -79.38792419,
                                   'obs_ra'  :  86.868051829832439,
                                   'obs_dec' : -27.575127242664802,
                                   'obs_ra_err'  : 7.464116913258858e-06,
                                   'obs_dec_err' : 7.516842315248245e-06,
                                   'obs_mag'      : -2.5*log10(11228.246),
                                   'obs_mag_err'  : 0.037939535221954708,
                                   'obs_sky_bkgd' : 746.41577148,
                                   'flags' : 0,
                                 })

        catalog_items = get_catalog_items(header_items, self.table_firstitem)

        self.assertEqual(expected_catalog, catalog_items)

    def test_ldac_first_item(self):

        expected_catalog = self.basic_table
        expected_catalog.add_row({ 'ccd_x' : 2189.4019002323894,
                                   'ccd_y' :  35.979511838066465,
                                   'major_axis'  : 2.806724,
                                   'minor_axis'  : 2.686966,
                                   'ccd_pa'      : 33.54286,
                                   'obs_ra'  :  178.3429720052357,
                                   'obs_dec' :  11.91179225051301,
                                   'obs_ra_err'  : 8.92232262319e-06,
                                   'obs_dec_err' : 8.12455029148e-06,
                                   'obs_mag'      : -2.5*log10(15599.6777344) +28.55,
                                   'obs_mag_err'  : 0.037677686175571018,
                                   'obs_sky_bkgd' : 175.43216,
                                   'flags' : 0,
                                 })


        header, table = open_fits_catalog(self.test_ldacfilename)
        header_items = get_catalog_header(header, "FITS_LDAC")
        catalog_items = get_catalog_items(header_items, self.ldac_table_firstitem, "FITS_LDAC")


        self.compare_tables(expected_catalog, catalog_items, 4)
