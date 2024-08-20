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

import os
from glob import glob
import tempfile
from unittest import skipIf
import warnings
import shutil
from copy import deepcopy

import astropy.units as u
from astropy.io import fits
from astropy.table import QTable
from numpy import array, arange
from astropy.tests.helper import assert_quantity_allclose

from numpy import array, arange, dtype
from numpy.testing import assert_allclose

from django.test import TestCase, SimpleTestCase
from django.forms.models import model_to_dict

# Import module to test
from photometrics.external_codes import *
from photometrics.catalog_subs import funpack_fits_file, get_header

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)

from core.models import frame
from core.models.body import Body, Designations
from core.models.frame import Frame
from core.models.blocks import Block, SuperBlock

class ExternalCodeUnitTest(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        # Path to the config files
        self.source_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

        self.testfits_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_fits_file = os.path.abspath(os.path.join(self.testfits_dir, 'example-sbig-e10.fits'))
        self.test_fits_catalog = os.path.abspath(os.path.join(self.testfits_dir, 'ldac_test_catalog.fits'))
        self.test_banzai_file = os.path.abspath(os.path.join(self.testfits_dir, 'banzai_test_frame.fits'))
        self.test_banzai_rms_file = os.path.abspath(os.path.join(self.testfits_dir, 'banzai_test_frame.rms.fits'))

        self.test_GAIADR2_catalog = os.path.abspath(os.path.join('photometrics', 'tests', 'GAIA-DR2.cat'))

        self.test_fits_file_set1_1 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0098-e90.fits'))
        self.test_fits_file_set1_2 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0099-e90.fits'))
        self.test_fits_file_set1_3 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0100-e90.fits'))
        self.test_fits_file_set1_4 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0101-e90.fits'))
        self.test_fits_file_set1_5 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0102-e90.fits'))
        self.test_fits_file_set1_6 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0103-e90.fits'))
        self.test_fits_file_set1_7 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0104-e90.fits'))
        self.test_fits_file_set1_8 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'cpt1m010-kb70-20160225-0105-e90.fits'))

        self.test_fits_file_set2_1 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'elp1m008-fl05-20160225-0095-e90.fits'))
        self.test_fits_file_set2_2 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'elp1m008-fl05-20160225-0096-e90.fits'))
        self.test_fits_file_set2_3 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'elp1m008-fl05-20160225-0097-e90.fits'))
        self.test_fits_file_set2_4 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'elp1m008-fl05-20160225-0098-e90.fits'))
        self.test_fits_file_set2_5 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'elp1m008-fl05-20160225-0099-e90.fits'))
        self.test_fits_file_set2_6 = os.path.abspath(os.path.join(os.path.expanduser('~'), 'test_mtdlink', 'elp1m008-fl05-20160225-0100-e90.fits'))

        self.test_obs_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcobs_WSAE9A6.dat'))

        self.debug_print = False

        self.remove = True

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


class TestMTDLINKRunner(ExternalCodeUnitTest):

    def test_setup_mtdlink_dir_bad_destdir(self):

        expected_status = -2

        status = setup_mtdlink_dir(self.source_dir, os.path.join('/usr/share/wibble'))

        self.assertEqual(expected_status, status)

    def test_setup_mtdlink_dir_bad_srcdir(self):

        expected_status = -1

        status = setup_mtdlink_dir('wibble', self.test_dir)

        self.assertEqual(expected_status, status)

    def test_setup_mtdlink_dir(self):

        expected_status = 0

        status = setup_mtdlink_dir(self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

    def test_run_mtdlink_nofile(self):

        param_file = 'mtdi.lcogt.param'

        pa_rate_dict = make_pa_rate_dict(pa=255.0, deltapa=10.0, minrate=0.95, maxrate=1.0)

        catalog_type = 'LCOGT'

        expected_cmdline = 'time mtdlink -verbose -paramfile mtdi.lcogt.param -CPUTIME 1600 -MAXMISSES 3 -FILTER_PA 255.0 -FILTER_DELTAPA 10.0 -FILTER_MINRATE 0.38 -FILTER_MAXRATE 0.40'
        cmdline = run_mtdlink(self.source_dir, self.test_dir, [], 8, param_file, pa_rate_dict, catalog_type, binary='mtdlink', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

    def test_run_mtdlink_file(self):

        param_file = 'mtdi.lcogt.param'

        pa_rate_dict = make_pa_rate_dict(pa=255.0, deltapa=10.0, minrate=0.95, maxrate=1.0)

        catalog_type = 'FITS_LDAC'

        expected_status = -43
        status = run_mtdlink(self.source_dir, self.test_dir, ['foo.fits', 'foo2.fits', 'foo3.fits'], 3, param_file, pa_rate_dict, catalog_type, binary='mtdlink', dbg=True)

        self.assertEqual(expected_status, status)

#    @skipIf(find_binary("mtdlink") is None, "Could not find MTDLINK binary ('mtdlink') in PATH")
    @skipIf(True, "Needs FITS files")
    def test_run_mtdlink_realfile(self):

        expected_status = 0
        expected_line1_sext_file = '       418     17.195   1182.871  15.2507    6.1       1.244      4.62   0  4.20        59298.4    16 141.91405 -13.52058'
        expected_line1 = 'DETSV2.0'
        expected_line1_file = 'mtdlink: Starting verbose mode'

        test_fits_file_set1_1 = self.test_fits_file_set1_1
        test_fits_file_set1_2 = self.test_fits_file_set1_2
        test_fits_file_set1_3 = self.test_fits_file_set1_3
        test_fits_file_set1_4 = self.test_fits_file_set1_4
        test_fits_file_set1_5 = self.test_fits_file_set1_5
        test_fits_file_set1_6 = self.test_fits_file_set1_6
        test_fits_file_set1_7 = self.test_fits_file_set1_7
        test_fits_file_set1_8 = self.test_fits_file_set1_8

        test_file_list = []
        test_file_list.append(test_fits_file_set1_1)
        test_file_list.append(test_fits_file_set1_2)
        test_file_list.append(test_fits_file_set1_3)
        test_file_list.append(test_fits_file_set1_4)
        test_file_list.append(test_fits_file_set1_5)
        test_file_list.append(test_fits_file_set1_6)
        test_file_list.append(test_fits_file_set1_7)
        test_file_list.append(test_fits_file_set1_8)

        param_file = 'mtdi.lcogt.param'

        for f in test_file_list:
            sext_file = os.path.basename(f).replace('.fits', '.sext')
            sext_file = os.path.join(self.test_dir, sext_file)
            # If the file exists and is a link (or a broken link), then remove it
            if os.path.lexists(sext_file) and os.path.islink(sext_file):
                os.unlink(sext_file)
            if not os.path.exists(sext_file):
                os.symlink(f.replace('.fits', '.sext'), sext_file)

        pa_rate_dict = make_pa_rate_dict(pa=255.0, deltapa=10.0, minrate=0.95, maxrate=1.0)

        catalog_type = 'LCOGT'

        status = run_mtdlink(self.source_dir, self.test_dir, test_file_list, 8, param_file, pa_rate_dict, catalog_type)

        self.assertEqual(expected_status, status)

        if self.debug_print:
            print(glob(os.path.join(self.test_dir, '*')))
        input_fits_1 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0098-e90.fits')
        self.assertTrue(os.path.exists(input_fits_1))
        input_fits_2 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0099-e90.fits')
        self.assertTrue(os.path.exists(input_fits_2))
        input_fits_3 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0100-e90.fits')
        self.assertTrue(os.path.exists(input_fits_3))
        input_fits_4 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0101-e90.fits')
        self.assertTrue(os.path.exists(input_fits_4))
        input_fits_5 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0102-e90.fits')
        self.assertTrue(os.path.exists(input_fits_5))
        input_fits_6 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0103-e90.fits')
        self.assertTrue(os.path.exists(input_fits_6))
        input_fits_7 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0104-e90.fits')
        self.assertTrue(os.path.exists(input_fits_7))
        input_fits_8 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0105-e90.fits')
        self.assertTrue(os.path.exists(input_fits_8))

        input_sext_1 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0098-e90.sext')
        self.assertTrue(os.path.exists(input_sext_1))
        test_fh_file = open(input_sext_1, 'r')
        test_lines_file = test_fh_file.readlines()
        test_fh_file.close()
        self.assertEqual(472, len(test_lines_file))
        self.assertEqual(expected_line1_sext_file, test_lines_file[0].rstrip())
        input_sext_2 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0099-e90.sext')
        self.assertTrue(os.path.exists(input_sext_2))
        input_sext_3 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0100-e90.sext')
        self.assertTrue(os.path.exists(input_sext_3))
        input_sext_4 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0101-e90.sext')
        self.assertTrue(os.path.exists(input_sext_4))
        input_sext_5 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0102-e90.sext')
        self.assertTrue(os.path.exists(input_sext_5))
        input_sext_6 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0103-e90.sext')
        self.assertTrue(os.path.exists(input_sext_6))
        input_sext_7 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0104-e90.sext')
        self.assertTrue(os.path.exists(input_sext_7))
        input_sext_8 = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0105-e90.sext')
        self.assertTrue(os.path.exists(input_sext_8))

        output_mtds = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0098-e90.mtds')
        self.assertTrue(os.path.exists(output_mtds))
        test_fh = open(output_mtds, 'r')
        test_lines = test_fh.readlines()
        test_fh.close()

        # Expected value is 10 lines of intro plus 200 sources
        self.assertEqual(10+200, len(test_lines))
        self.assertEqual(expected_line1, test_lines[0].rstrip())

        output_file = os.path.join(self.test_dir, 'mtdlink_output.out')
        self.assertTrue(os.path.exists(output_file))
        test_fh_file = open(output_file, 'r')
        test_lines_file = test_fh_file.readlines()
        test_fh_file.close()

        # Expected value is 58 lines
        self.assertEqual(58, len(test_lines_file))
        self.assertEqual(expected_line1_file, test_lines_file[0].rstrip())

#    @skipIf(find_binary("mtdlink") is None, "Could not find MTDLINK binary ('mtdlink') in PATH")
    @skipIf(True, "Needs FITS files")
    def test_run_mtdlink_realfile_different_set(self):

        expected_status = 0
        expected_line1_sext_file = '      5021      5.602   3418.469  21.1217 -80.7    3.268     6.21   0  0.98   1506.9    4 164.15665  39.42453'
        expected_line1 = 'DETSV2.0'
        expected_line1_file = 'mtdlink: Starting verbose mode'

        test_fits_file_set2_1 = self.test_fits_file_set2_1
        test_fits_file_set2_2 = self.test_fits_file_set2_2
        test_fits_file_set2_3 = self.test_fits_file_set2_3
        test_fits_file_set2_4 = self.test_fits_file_set2_4
        test_fits_file_set2_5 = self.test_fits_file_set2_5
        test_fits_file_set2_6 = self.test_fits_file_set2_6

        test_file_list = [test_fits_file_set2_1, test_fits_file_set2_2, test_fits_file_set2_3, test_fits_file_set2_4,
                          test_fits_file_set2_5, test_fits_file_set2_6]

        param_file = 'mtdi.lcogt.param'

        for f in test_file_list:
            sext_file = os.path.basename(f).replace('.fits', '.sext')
            sext_file = os.path.join(self.test_dir, sext_file)
            # If the file exists and is a link (or a broken link), then remove it
            if os.path.lexists(sext_file) and os.path.islink(sext_file):
                os.unlink(sext_file)
            if not os.path.exists(sext_file):
                os.symlink(f.replace('.fits', '.sext'), sext_file)

        pa_rate_dict = make_pa_rate_dict(pa=345.0, deltapa=25.0, minrate=1.15, maxrate=1.25)

        catalog_type = 'LCOGT'

        status = run_mtdlink(self.source_dir, self.test_dir, test_file_list, 6, param_file, pa_rate_dict, catalog_type)

        self.assertEqual(expected_status, status)

        if self.debug_print:
            print(glob(os.path.join(self.test_dir, '*')))
        input_fits_1 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0095-e90.fits')
        self.assertTrue(os.path.exists(input_fits_1))
        input_fits_2 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0096-e90.fits')
        self.assertTrue(os.path.exists(input_fits_2))
        input_fits_3 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0097-e90.fits')
        self.assertTrue(os.path.exists(input_fits_3))
        input_fits_4 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0098-e90.fits')
        self.assertTrue(os.path.exists(input_fits_4))
        input_fits_5 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0099-e90.fits')
        self.assertTrue(os.path.exists(input_fits_5))
        input_fits_6 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0100-e90.fits')
        self.assertTrue(os.path.exists(input_fits_6))

        input_sext_1 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0095-e90.sext')
        self.assertTrue(os.path.exists(input_sext_1))
        test_fh_file = open(input_sext_1, 'r')
        test_lines_file = test_fh_file.readlines()
        test_fh_file.close()
        self.assertEqual(7189, len(test_lines_file))
        self.assertEqual(expected_line1_sext_file, test_lines_file[0].rstrip())
        input_sext_2 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0096-e90.sext')
        self.assertTrue(os.path.exists(input_sext_2))
        input_sext_3 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0097-e90.sext')
        self.assertTrue(os.path.exists(input_sext_3))
        input_sext_4 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0098-e90.sext')
        self.assertTrue(os.path.exists(input_sext_4))
        input_sext_5 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0099-e90.sext')
        self.assertTrue(os.path.exists(input_sext_5))
        input_sext_6 = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0100-e90.sext')
        self.assertTrue(os.path.exists(input_sext_6))

        output_mtds = os.path.join(self.test_dir, 'elp1m008-fl05-20160225-0095-e90.mtds')
        self.assertTrue(os.path.exists(output_mtds))
        test_fh = open(output_mtds, 'r')
        test_lines = test_fh.readlines()
        test_fh.close()

        # Expected value is 8 lines of intro plus 132 sources
        self.assertEqual(8+132, len(test_lines))
        self.assertEqual(expected_line1, test_lines[0].rstrip())

        output_file = os.path.join(self.test_dir, 'mtdlink_output.out')
        self.assertTrue(os.path.exists(output_file))
        test_fh_file = open(output_file, 'r')
        test_lines_file = test_fh_file.readlines()
        test_fh_file.close()

        # Expected value is 58 lines
        self.assertEqual(52, len(test_lines_file))
        self.assertEqual(expected_line1_file, test_lines_file[0].rstrip())


class TestSCAMPRunner(ExternalCodeUnitTest):

    def test_setup_scamp_dir_bad_destdir(self):

        expected_status = -2

        status = setup_scamp_dir(self.source_dir, os.path.join('/usr/share/wibble'))

        self.assertEqual(expected_status, status)

    def test_setup_scamp_dir_bad_srcdir(self):

        expected_status = -1

        status = setup_scamp_dir('wibble', self.test_dir)

        self.assertEqual(expected_status, status)

    def test_setup_scamp_dir(self):

        expected_status = 0

        status = setup_scamp_dir(self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'scamp_neox_gaiadr2.cfg')))

    def test_scamp_options(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -XML_NAME foo.xml'

        options = determine_scamp_options('foo.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_0m4_no_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -XML_NAME foo_0m4.xml'

        options = determine_scamp_options('foo_0m4.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_2m0_no_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -POSANGLE_MAXERR 1 -MATCH_FLIPPED N -XML_NAME foo_2m0.xml'

        options = determine_scamp_options('foo_2m0.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_1m0_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -DISTORT_DEGREES 3 -PROJECTION_TYPE TPV -XML_NAME test1m0-fa##-date.xml'

        options = determine_scamp_options('test1m0-fa##-date.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_1m0_distortion_4th_order(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -DISTORT_DEGREES 4 -PROJECTION_TYPE TPV -XML_NAME test1m0-fa##-date.xml'

        options = determine_scamp_options('test1m0-fa##-date.ldac', distort_degrees=4)

        self.assertEqual(expected_options, options)

    def test_scamp_options_0m4_distortion_5th_order(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -DISTORT_DEGREES 5 -PROJECTION_TYPE TPV -XML_NAME test1m0-fa##-date.xml'

        options = determine_scamp_options('test1m0-fa##-date.ldac', distort_degrees=5)

        self.assertEqual(expected_options, options)

    def test_scamp_options_1m0_no_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -XML_NAME test1m0-fa##-date.xml'

        options = determine_scamp_options('test1m0-fa##-date.ldac', distort_degrees=1)

        self.assertEqual(expected_options, options)

    @skipIf(find_binary("scamp") is None, "Could not find SCAMP binary ('scamp') in PATH")
    def test_run_scamp_realfile(self):
        # Symlink in DR2 and LDAC catalogs into test directory
        os.symlink(self.test_GAIADR2_catalog, os.path.join(self.test_dir,os.path.basename(self.test_GAIADR2_catalog)))
        os.symlink(self.test_fits_catalog, os.path.join(self.test_dir,os.path.basename(self.test_fits_catalog)))

        expected_status = 0
        expected_line1 = 'EQUINOX =        2000.00000000 / Mean equinox'

        status = run_scamp(self.source_dir, self.test_dir, self.test_fits_catalog)

        self.assertEqual(expected_status, status)
        if self.debug_print: print(glob(os.path.join(self.test_dir, '*')))

        header_file = os.path.basename(self.test_fits_catalog).replace('fits', 'head')
        output_header = os.path.join(self.test_dir, header_file)
        self.assertTrue(os.path.exists(output_header), msg=output_header + ' is missing')
        self.assertFalse(os.path.exists(self.test_fits_catalog.replace('fits', 'head')), msg=output_header + ' exists in the wrong place')

        test_fh = open(output_header, 'r')
        test_lines = test_fh.readlines()
        test_fh.close()

        # Expected value is 29 lines of FITS header
        self.assertEqual(29, len(test_lines))
        self.assertEqual(expected_line1, test_lines[3].rstrip())

        xml_file = os.path.basename(self.test_fits_catalog).replace('fits', 'xml')
        output_xml = os.path.join(self.test_dir, header_file)
        self.assertTrue(os.path.exists(output_xml), msg=output_xml + ' is missing')
        self.assertFalse(os.path.exists(self.test_fits_catalog.replace('fits', 'head')), msg=output_xml + ' exists in the wrong place')


class TestSExtractorRunner(ExternalCodeUnitTest):
    def setUp(self):
        super(TestSExtractorRunner, self).setUp()

        # needs to modify the original image for LDAC catalog_type
        shutil.copy(os.path.abspath(self.test_fits_file), self.test_dir)
        self.test_fits_file_COPIED = os.path.join(self.test_dir, 'example-sbig-e10.fits')

        # Disable anything below CRITICAL level as code is "noisy"
        logging.disable(logging.CRITICAL)

        self.remove = True
        self.debug_print = False

    def tearDown(self):
        super(TestSExtractorRunner, self).tearDown()

        if self.remove is False and self.debug_print is True:
            print(f"Test directory= {self.test_dir}")

    def test_setup_sextractor_dir_bad_destdir(self):

        expected_status = -2

        status = setup_sextractor_dir(self.source_dir, os.path.join('/usr/share/wibble'))

        self.assertEqual(expected_status, status)

    def test_setup_sextractor_dir_bad_srcdir(self):

        expected_status = -1

        status = setup_sextractor_dir('wibble', self.test_dir)

        self.assertEqual(expected_status, status)

    def test_setup_sextractor_dir(self):

        expected_configs = default_sextractor_config_files()
        expected_status = 0

        status = setup_sextractor_dir(self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')

    def test_setup_sextractor_dir_ascii(self):

        expected_configs = ['sextractor_neox.conf',
                            'sextractor_ascii.params']
        expected_status = 0

        status = setup_sextractor_dir(self.source_dir, self.test_dir, catalog_type='ASCII')

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')

    def test_setup_sextractor_dir_ldac(self):

        expected_configs = ['sextractor_neox_ldac.conf',
                            'sextractor_ldac.params']
        expected_status = 0

        status = setup_sextractor_dir(self.source_dir, self.test_dir, catalog_type='FITS_LDAC')

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')

    def test_setup_sextractor_dir_multiaper(self):

        expected_configs = ['sextractor_neox_ldac_multiaper.conf',
                            'sextractor_ldac_multiaper.params']
        expected_status = 0

        status = setup_sextractor_dir(self.source_dir, self.test_dir, catalog_type='FITS_LDAC_MULTIAPER')

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')

    def test_run_sextractor_nofile(self):

        expected_status = -4

        status = run_sextractor(self.source_dir, self.test_dir, '')
        self.assertEqual(expected_status, status)

        status = run_sextractor(self.source_dir, self.test_dir, '', catalog_type='ASCII')
        self.assertEqual(expected_status, status)

    def test_run_sextractor_nonfits(self):

        expected_status = -5

        status = run_sextractor(self.source_dir, self.test_dir, self.test_GAIADR2_catalog)
        self.assertEqual(expected_status, status)

        status = run_sextractor(self.source_dir, self.test_dir, self.test_GAIADR2_catalog, catalog_type='ASCII')
        self.assertEqual(expected_status, status)

    def test_run_sextractor_nonfits_sci(self):

        expected_status = -5

        status = run_sextractor(self.source_dir, self.test_dir, self.test_GAIADR2_catalog + '[SCI]')
        self.assertEqual(expected_status, status)

        status = run_sextractor(self.source_dir, self.test_dir, self.test_GAIADR2_catalog + '[SCI]', catalog_type='ASCII')
        self.assertEqual(expected_status, status)

    @skipIf(find_binary("sex") is None, "Could not find SExtractor binary ('sex') in PATH")
    def test_run_sextractor_realfile(self):

        expected_status = 0
        expected_line1 = '#   1 NUMBER                 Running object number'

        status = run_sextractor(self.source_dir, self.test_dir, self.test_fits_file_COPIED, checkimage_type=['BACKGROUND_RMS'], catalog_type='ASCII')

        self.assertEqual(expected_status, status)

        if self.debug_print:
            print(glob(os.path.join(self.test_dir, '*')))

        self.expected_catalog_name = os.path.join(self.test_dir, 'example-sbig-e10.cat')
        self.assertTrue(os.path.exists(self.expected_catalog_name))
        test_fh = open(self.expected_catalog_name, 'r')
        test_lines = test_fh.readlines()
        test_fh.close()

        # Expected value is 14 lines of header plus 2086 sources
        # LP 2022/06/30 Expected sources now 1929 after change in BACK_SIZE
        self.assertEqual(14+1929, len(test_lines))
        self.assertEqual(expected_line1, test_lines[0].rstrip())

        output_rms = os.path.join(self.test_dir, os.path.basename(self.test_fits_file.replace('.fits', '.rms.fits')))
        self.assertTrue(os.path.exists(output_rms))

    @skipIf(find_binary("sex") is None, "Could not find SExtractor binary ('sex') in PATH")
    def test_run_sextractor_realfile_defaultldac(self):

        expected_status = 0
        expected_hdus = ['PRIMARY', 'LDAC_IMHEAD', 'LDAC_OBJECTS']
        expected_row1 = (1, 106.72158852039514, 25.649854272268744, 215.6548927631294, -39.477292362087034, 2.3552754168060627e-11, 1.653809750683626e-11, 0.00213810408831188, 0.0020694796910492633, 107, 26, 5.718054717711681, 3.898199662063792, 0.21701803052330249, 2.020644, 1.8051586, 10.109293, 0.046268698, 0.04546198, 10.987773, 26001.604, 635.868, 8520.073, 138.29593, 670.50024, 3.3191917, -10.925921, 0.025971856, 498.63678, -6.374261, 78, 0.17886513, 78, 71, 56, 46, 37, 25, 15, 4, 6.396605, 0.9479728, 0, 0)

        status = run_sextractor(self.source_dir, self.test_dir, self.test_fits_file_COPIED, checkimage_type=['BACKGROUND_RMS'])

        self.assertEqual(expected_status, status)

        if self.debug_print:
            print(glob(os.path.join(self.test_dir, '*')))

        self.expected_catalog_name = os.path.join(self.test_dir, 'example-sbig-e10_ldac.fits')
        self.assertTrue(os.path.exists(self.expected_catalog_name))
        hdulist = fits.open(self.expected_catalog_name)
        self.assertEqual(len(expected_hdus), len(hdulist))
        for i, hdu in enumerate(hdulist):
            self.assertEqual(expected_hdus[i], hdu.name)

        # Expected value is 982 lines of FITS header plus 270 sources
        self.assertEqual(982, len(hdulist['LDAC_IMHEAD'].data[0][0]))
        tbl_data = hdulist['LDAC_OBJECTS'].data
        self.assertEqual(270, len(tbl_data))
        assert_allclose(expected_row1, tbl_data[0], 6)
        hdulist.close()

        output_rms = os.path.join(self.test_dir, os.path.basename(self.test_fits_file.replace('.fits', '.rms.fits')))
        self.assertTrue(os.path.exists(output_rms))


class TestSwarpRunner(ExternalCodeUnitTest):
    def setUp(self):
        # Copying over some files to the temp directory to manipulate
        super(TestSwarpRunner, self).setUp()

        """example-sbig-e10.fits"""
        # This image has a 'L1ZP' keyword in the header
        shutil.copy(os.path.abspath(self.test_fits_file), self.test_dir)
        self.test_fits_file_COPIED = os.path.join(self.test_dir, os.path.basename(self.test_fits_file))

        """banzai_test_frame.fits.fz"""
        # This image DOES NOT have a 'L1ZP' keyword in the header
        self.test_banzai_comp_file = os.path.join(self.testfits_dir, 'banzai_test_frame.fits.fz')
        shutil.copy(os.path.abspath(self.test_banzai_comp_file), self.test_dir)
        self.test_banzai_comp_file_COPIED = os.path.join(self.test_dir, os.path.basename(self.test_banzai_comp_file))

        # Decompress
        funpack_fits_file(self.test_banzai_comp_file_COPIED, all_hdus=True)
        self.test_banzai_file_COPIED = os.path.join(self.test_dir, os.path.basename('banzai_test_frame.fits'))

        """banzai_test_frame.rms.fits"""
        shutil.copy(os.path.abspath(self.test_banzai_rms_file), self.test_dir)


        self.remove = True

    def test_setup_swarp_dir_bad_destdir(self):

        expected_status = -2

        status = setup_swarp_dir(self.source_dir, os.path.join('/usr/share/wibble'))

        self.assertEqual(expected_status, status)

    def test_setup_swarp_dir_bad_srcdir(self):

        expected_status = -1

        status = setup_swarp_dir('wibble', self.test_dir)

        self.assertEqual(expected_status, status)

    def test_setup_swarp_dir(self):

        expected_configs = default_swarp_config_files()
        expected_status = 0

        status = setup_swarp_dir(self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')

    def test_badimages(self):

        expected_status = -3

        status = run_swarp(self.source_dir, self.test_dir, ["banana"])

        self.assertEqual(expected_status, status)

    def test_nonfits(self):

        expected_status = -5

        status = run_swarp(self.source_dir, self.test_dir, [self.test_GAIADR2_catalog])

        self.assertEqual(expected_status, status)

    def test_normalize_success(self):

        with fits.open(self.test_fits_file_COPIED) as hdulist:
            # Rename the 'PRIMARY' HDU to 'SCI'
            header = hdulist[0].header
            header['EXTNAME'] = 'SCI'
            hdulist.writeto(self.test_fits_file_COPIED, overwrite=True, checksum=True)

        expected_status = 0

        # Contains L1ZP keyword
        status = normalize([self.test_fits_file_COPIED], swarp_zp_key='L1ZP')
        self.assertEqual(expected_status, status)

        with fits.open(self.test_fits_file_COPIED) as hdulist:
            header = hdulist[0].header
            keylist = header.keys()

        self.assertTrue('L1ZP' in header, msg='L1ZP not in header')
        self.assertTrue('FLXSCALE' in header, msg='FLXSCALE not in header')
        self.assertTrue('FLXSCLZP' in header, msg='FLXSCLZP not in header')

    def test_normalize_fail(self):

        expected_status = -6

        # Does not contain L1ZP keyword
        status = normalize([self.test_banzai_file_COPIED], swarp_zp_key='L1ZP')
        self.assertEqual(expected_status, status)

        with fits.open(self.test_banzai_file_COPIED) as hdulist:
            header = hdulist['SCI'].header
            keylist = header.keys()

        self.assertTrue('L1ZP' not in header, msg='L1ZP is in header')
        self.assertTrue('FLXSCALE' not in header, msg='FLXSCALE is in header')
        self.assertTrue('FLXSCLZP' not in header, msg='FLXSCLZP is in header')

    def test_swarp_success(self):
        inlist = os.path.join(self.test_dir, 'images.in')
        inweight = os.path.join(self.test_dir, 'weight.in')

        expected_cmdline = f"./swarp -c swarp_neox.conf @{inlist} -BACK_SIZE 32 -IMAGEOUT_NAME reference.fits -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -WEIGHT_IMAGE @{inweight} -WEIGHTOUT_NAME reference.weight.fits"

        with fits.open(self.test_banzai_file_COPIED) as hdulist:
            # Add in a 'L1ZP' keyword into the header
            header = hdulist['SCI'].header
            header['L1ZP'] = 24
            hdulist.writeto(self.test_banzai_file_COPIED, overwrite=True, checksum=True)

        cmdline = run_swarp(self.source_dir, self.test_dir, [self.test_banzai_file_COPIED], binary='./swarp', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

        expected_status = 0
        status = run_swarp(self.source_dir, self.test_dir, [self.test_banzai_file_COPIED], dbg=False)

        self.assertEqual(expected_status, status)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "reference.weight.fits")))


class TestSwarpAlignRunner(ExternalCodeUnitTest):

    def test_make_ref_head(self):

        expected_headpath = os.path.join(self.test_dir, "example-sbig-e10_aligned_to_example-sbig-e10.head")

        headpath = make_ref_head(self.test_fits_file, self.test_fits_file, self.test_dir, expected_headpath)

        self.assertEqual(expected_headpath, headpath)

        with open(headpath, 'r') as h:
            head = h.read()

        self.assertTrue('NAXIS   =                    0' not in head, msg="NAXIS data is not valid.")
        self.assertTrue('NAXIS1' in head, msg="NAXIS data is not valid.")
        self.assertTrue('NAXIS2' in head, msg="NAXIS data is not valid.")
        self.assertTrue('CRPIX1  =                  0.0' not in head, msg="WCS data is not valid.")
        self.assertTrue('CUNIT1' in head, msg="WCS data is not valid.")
        self.assertTrue('CTYPE1' in head, msg="WCS data is not valid.")

    def test_make_ref_head2(self):

        expected_headpath = os.path.join(self.test_dir, "banzai_test_frame_aligned_to_banzai_test_frame.head")

        headpath = make_ref_head(self.test_banzai_file, self.test_banzai_file, self.test_dir, expected_headpath)

        self.assertEqual(expected_headpath, headpath)

        with open(headpath, 'r') as h:
            head = h.read()

        self.assertTrue('NAXIS   =                    0' not in head, msg="NAXIS data is not valid.")
        self.assertTrue('NAXIS1' in head, msg="NAXIS data is not valid.")
        self.assertTrue('NAXIS2' in head, msg="NAXIS data is not valid.")
        self.assertTrue('CRPIX1  =                  0.0' not in head, msg="WCS data is not valid.")
        self.assertTrue('CUNIT1' in head, msg="WCS data is not valid.")
        self.assertTrue('CTYPE1' in head, msg="WCS data is not valid.")

    def test_make_ref_head3(self):

        expected_headpath = os.path.join(self.test_dir, "banzai_test_frame.rms_aligned_to_banzai_test_frame.rms.head")

        headpath = make_ref_head(self.test_banzai_rms_file, self.test_banzai_rms_file, self.test_dir, expected_headpath)

        self.assertEqual(expected_headpath, headpath)

        with open(headpath, 'r') as h:
            head = h.read()

        self.assertTrue('NAXIS   =                    0' not in head, msg="NAXIS data is not valid.")
        self.assertTrue('NAXIS1' in head, msg="NAXIS data is not valid.")
        self.assertTrue('NAXIS2' in head, msg="NAXIS data is not valid.")
        self.assertTrue('CRPIX1  =                  0.0' not in head, msg="WCS data is not valid.")
        self.assertTrue('CUNIT1' in head, msg="WCS data is not valid.")
        self.assertTrue('CTYPE1' in head, msg="WCS data is not valid.")

    def test_setup_swarp_dir_bad_destdir(self):

        expected_status = -2

        status = setup_swarp_dir(self.source_dir, os.path.join('/usr/share/wibble'))

        self.assertEqual(expected_status, status)

    def test_setup_swarp_dir_bad_srcdir(self):

        expected_status = -1

        status = setup_swarp_dir('wibble', self.test_dir)

        self.assertEqual(expected_status, status)

    def test_setup_swarp_dir(self):

        expected_configs = default_swarp_config_files()
        expected_status = 0

        status = setup_swarp_dir(self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')

    def bad_ref(self):
        expected_status = -4

        status = run_swarp_align('banana', self.test_fits_file, self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

    def bad_sci(self):
        expected_status = -5

        status = run_swarp_align(self.test_fits_file, 'banana', self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

    def test_swarp_align_success(self):

        outname = os.path.join(self.test_dir, "example-sbig-e10_aligned_to_example-sbig-e10.fits")
        weightname = outname.replace('.fits', '.weight.fits')
        headname = outname.replace('.fits', '.head')

        expected_cmdline = f"./swarp -c swarp_neox.conf {self.test_fits_file} -BACK_SIZE 32 -IMAGEOUT_NAME {outname} -NTHREADS 1 -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -SUBTRACT_BACK N -WEIGHTOUT_NAME {weightname} -WEIGHT_TYPE NONE -COMBINE_TYPE CLIPPED"
        cmdline = run_swarp_align(self.test_fits_file, self.test_fits_file, self.source_dir, self.test_dir, outname, binary='./swarp', dbg=True)

        self.maxDiff = None
        self.assertEqual(expected_cmdline, cmdline)

        expected_status = 0
        status = run_swarp_align(self.test_fits_file, self.test_fits_file, self.source_dir, self.test_dir, outname, dbg=False)

        self.assertEqual(expected_status, status)

        self.assertTrue(os.path.exists(outname))
        self.assertTrue(os.path.exists(weightname))
        self.assertTrue(os.path.exists(headname))


class TestHotpantsRunner(ExternalCodeUnitTest):
    def setUp(self):
        super(TestHotpantsRunner, self).setUp()

        # needs to modify the original image when running sextractor
        shutil.copy(os.path.abspath(self.test_banzai_file), self.test_dir)
        self.test_banzai_file_COPIED = os.path.join(self.test_dir, 'banzai_test_frame.fits')

        # hotpants requires a reference rms image in the dest_dir
        shutil.copy(os.path.abspath(self.test_banzai_rms_file), self.test_dir)

        # Disable anything below CRITICAL level
        logging.disable(logging.CRITICAL)

        self.remove = True

    def test_no_ref(self):
        expected_status = -4

        status = determine_hotpants_options("banana", self.test_fits_file, self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

    def test_no_sci(self):
        expected_status = -5

        status = determine_hotpants_options(self.test_fits_file, "banana", self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

    def test_no_ref_rms(self):
        # This would also catch return code -7 since it's the same image
        # Return codes -8 and -9 are not easy to replicate
        expected_status = -6

        self.test_banzai_rms_file = os.path.join(self.test_dir, os.path.basename(self.test_banzai_rms_file))
        os.remove(self.test_banzai_rms_file)

        status = determine_hotpants_options(self.test_banzai_file_COPIED, self.test_banzai_file_COPIED, self.source_dir, self.test_dir)

        self.assertEqual(expected_status, status)

    def test_cmdline(self):
        bkgsub = os.path.join(self.test_dir, "banzai_test_frame.bkgsub.fits")
        aligned = os.path.join(self.test_dir, "banzai_test_frame_aligned_to_banzai_test_frame.fits")
        subtracted = os.path.join(self.test_dir, "banzai_test_frame.subtracted.fits")
        subtracted_rms = os.path.join(self.test_dir, "banzai_test_frame.subtracted.rms.fits")
        aligned_rms = os.path.join(self.test_dir, "banzai_test_frame.rms_aligned_to_banzai_test_frame.rms.fits")
        rms = os.path.join(self.test_dir, "banzai_test_frame.rms.fits")

        expected_cmdline = f"./hotpants -inim {bkgsub} -tmplim {aligned} -outim {subtracted} -tni {aligned_rms} -ini {rms} -oni {subtracted_rms} -hki -n i -c t -v 0 -tu 57959 -iu 57959 -tl 43.892452606201175 -il -342.03351336669925 -nrx 3 -nry 3 -nsx 6.760000000000001 -nsy 6.793333333333333 -r 11.235949458513854 -rss 26.96627870043325 -fin 223.60679774997897"
        cmdline = run_hotpants(self.test_banzai_file_COPIED, self.test_banzai_file_COPIED, self.source_dir, self.test_dir, binary='./hotpants', dbg=True, dbgOptions=True)
        self.maxDiff=None
        self.assertEqual(expected_cmdline, cmdline)

    def test_success(self):

        expected_status = 0

        status = run_hotpants(self.test_banzai_file_COPIED, self.test_banzai_file_COPIED, self.source_dir, self.test_dir, dbg=False, dbgOptions=True)

        self.assertEqual(expected_status, status)

        outname = os.path.join(self.test_dir, "banzai_test_frame.subtracted.fits")

        self.assertTrue(os.path.exists(outname))
        self.assertTrue(os.path.exists(outname.replace('.fits', '.rms.fits')))

        with fits.open(outname) as hdul:
            header = hdul[0].header
            data = hdul[0].data

        self.assertTrue('HOTPanTS', header.get('SOFTNAME', ''))
        self.assertTrue('TEMPLATE', header.get('CONVOL00', ''))
        self.assertTrue('0.9932  ', header.get('KSUM00', ''))
        assert_allclose(-194.2074, data[400, 400])
        assert_allclose(17.313549, data[640, 30])


class TestFindOrbRunner(ExternalCodeUnitTest):

    # These test use a fake binary name and set dbg=True to echo the generated
    # command line rather than actually executing the real find_orb code.
    @skipIf(True, 'FindOrb is still Broken')
    def test_sitecode_default(self):
        eph_time = datetime(2018, 4, 20)

        # expected_status = "fo_console {} -z -c -q -C 500 -e new.ephem -tE2018-04-21".format(self.test_obs_file)
        expected_status = "fo_console {} -z -c -q -C 500 -tE2018-04-21".format(self.test_obs_file)

        status = run_findorb(self.source_dir, self.test_dir, self.test_obs_file, binary="fo_console", start_time=eph_time, dbg=True)

        self.assertEqual(expected_status, status)

    @skipIf(True, 'FindOrb is still Broken')
    def test_sitecode_T03(self):
        site_code = 'T03'
        eph_time = datetime(2018, 12, 31, 23, 59)

        # expected_status = "fo_console {} -z -c -q -C {} -e new.ephem -tE2019-01-01".format(self.test_obs_file, site_code)
        expected_status = "fo_console {} -z -c -q -C {} -tE2019-01-01".format(self.test_obs_file, site_code)

        status = run_findorb(self.source_dir, self.test_dir, self.test_obs_file, site_code, binary="fo_console", start_time=eph_time, dbg=True)

        self.assertEqual(expected_status, status)


class TestDetermineSExtOptions(ExternalCodeUnitTest):

    def setUp(self):
        super(TestDetermineSExtOptions, self).setUp()

        # Copy BANZAI test file to test_dir to allow mods
        self.test_banzai_file_COPIED = shutil.copy(self.test_banzai_file, self.test_dir)

        self.expected_catalog_name = os.path.join(self.test_dir, 'example-sbig-e10_ldac.fits')
        self.expected_ascii_catalog_name = os.path.join(self.test_dir, 'example-sbig-e10.cat')
        self.expected_banzai_catalog_name = os.path.join(self.test_dir, 'banzai_test_frame_ldac.fits')

        # Disable anything below CRITICAL level
        logging.disable(logging.CRITICAL)

    def test_badfile(self):
        expected_options = ''

        options = determine_sextractor_options(os.path.join(self.source_dir, 'scamp_neox.cfg'), self.test_dir)

        self.assertEqual(expected_options, options)

    def test_no_checkimages(self):
        # No checkimages
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.46692 -SATUR_LEVEL 41400 -CATALOG_NAME {self.expected_catalog_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir)

        self.assertEqual(expected_options, options)

    def test_ascii_no_checkimages(self):
        # No checkimages
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.46692 -SATUR_LEVEL 41400 -CATALOG_NAME {self.expected_ascii_catalog_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, catalog_type='ASCII')

        self.assertEqual(expected_options, options)

    def test_asciihead_no_checkimages(self):
        # No checkimages
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.46692 -SATUR_LEVEL 41400 -CATALOG_NAME {self.expected_ascii_catalog_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, catalog_type='ASCII_HEAD')

        self.assertEqual(expected_options, options)

    def test_unknownhead_no_checkimages(self):
        # No checkimages
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.46692 -SATUR_LEVEL 41400 -CATALOG_NAME {self.expected_catalog_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, catalog_type='POTATO_HEAD')

        self.assertEqual(expected_options, options)

    def test_one_checkimage(self):
        # Single checkimage
        checkimage_name = os.path.join(self.test_dir, 'example-sbig-e10.rms.fits')
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.46692 -SATUR_LEVEL 41400 -CATALOG_NAME {self.expected_catalog_name} -CHECKIMAGE_TYPE BACKGROUND_RMS -CHECKIMAGE_NAME {checkimage_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, checkimage_type=['BACKGROUND_RMS'])

        self.assertEqual(expected_options, options)

    def test_multiple_checkimages(self):
        # Multiple checkimages
        rms_name = os.path.join(self.test_dir, 'example-sbig-e10.rms.fits')
        bkgsub_name = os.path.join(self.test_dir, 'example-sbig-e10.bkgsub.fits')
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.46692 -SATUR_LEVEL 41400 -CATALOG_NAME {self.expected_catalog_name} -CHECKIMAGE_TYPE BACKGROUND_RMS,-BACKGROUND -CHECKIMAGE_NAME {rms_name},{bkgsub_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, checkimage_type=['BACKGROUND_RMS', '-BACKGROUND'])

        self.assertEqual(expected_options, options)

    def test_multiple_checkimages2(self):
        # Multiple checkimages (REVERSED ORDER)
        rms_name = os.path.join(self.test_dir, 'example-sbig-e10.rms.fits')
        bkgsub_name = os.path.join(self.test_dir, 'example-sbig-e10.bkgsub.fits')
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.46692 -SATUR_LEVEL 41400 -CATALOG_NAME {self.expected_catalog_name} -CHECKIMAGE_TYPE -BACKGROUND,BACKGROUND_RMS -CHECKIMAGE_NAME {bkgsub_name},{rms_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, checkimage_type=['-BACKGROUND', 'BACKGROUND_RMS'])

        self.assertEqual(expected_options, options)

    def test_bad_checkimage(self):
        expected_status = -6

        status = determine_sextractor_options(self.test_fits_file, self.test_dir, checkimage_type=['banana'])

        self.assertEqual(expected_status, status)

    def test_banzai_no_secpix_no_checkimages(self):
        # Butcher the FITS header to make it look like a Sinistro frame
        with fits.open(self.test_banzai_file_COPIED, mode='update') as hdulist:
            header = hdulist[0].header
            header['gain'] = 1.0
            header['saturate'] = 128000
            header['maxlin'] = 120000
            new_scale = 0.389/3600.0
            header['cd1_1'] = -new_scale
            header['cd2_2'] = -new_scale
            hdulist.flush()

        # No checkimages
        expected_options = f'-GAIN 1.0 -PIXEL_SCALE 0.38903 -SATUR_LEVEL 120000 -CATALOG_NAME {self.expected_banzai_catalog_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_banzai_file_COPIED, self.test_dir)

        self.assertEqual(expected_options, options)

    def test_banzai_no_secpix_bad_maxlin_no_checkimages(self):
        # Butcher the FITS header to make it look like a Sinistro frame
        with fits.open(self.test_banzai_file_COPIED, mode='update') as hdulist:
            header = hdulist[0].header
            header['gain'] = 1.0
            header['saturate'] = 128000
            header['maxlin'] = 0.
            new_scale = 0.389/3600.0
            header['cd1_1'] = -new_scale
            header['cd2_2'] = -new_scale
            hdulist.flush()

        # No checkimages
        expected_options = f'-GAIN 1.0 -PIXEL_SCALE 0.38903 -SATUR_LEVEL 115200 -CATALOG_NAME {self.expected_banzai_catalog_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_banzai_file_COPIED, self.test_dir)

        self.assertEqual(expected_options, options)

    def test_banzai_no_secpix_bad_maxlin_saturate_no_checkimages(self):
        # Butcher the FITS header to make it look like a Sinistro frame
        with fits.open(self.test_banzai_file_COPIED, mode='update') as hdulist:
            header = hdulist[0].header
            header['gain'] = 1.0
            header['saturate'] = 0
            del(header['maxlin'])
            new_scale = 0.389/3600.0
            header['cd1_1'] = -new_scale
            header['cd2_2'] = -new_scale
            hdulist.flush()

        # No SATURATE or maxlin, should be default value
        expected_options = f'-GAIN 1.0 -PIXEL_SCALE 0.38903 -SATUR_LEVEL 65535 -CATALOG_NAME {self.expected_banzai_catalog_name} -BACK_SIZE 32'

        options = determine_sextractor_options(self.test_banzai_file_COPIED, self.test_dir)

        self.assertEqual(expected_options, options)


class TestDetermineSwarpOptions(ExternalCodeUnitTest):

    def setUp(self):
        super(TestDetermineSwarpOptions, self).setUp()

        self.maxDiff = None

    def test1(self):
        inweight = os.path.join(self.test_dir, 'weight.in')
        outname = "test_swarp_output.fits"

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME test_swarp_output.fits -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -WEIGHT_IMAGE @{inweight} -WEIGHTOUT_NAME test_swarp_output.weight.fits -PROJECTION_TYPE TPV '

        options = determine_swarp_options(inweight, outname, self.test_dir)

        self.assertEqual(expected_options, options)

    def test_1m(self):
        inweight = os.path.join(self.test_dir, 'weight.in')
        outname = "reference_coj_fa99_rp_282.77_-25.31.fits"

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME {outname} -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -WEIGHT_IMAGE @{inweight} -WEIGHTOUT_NAME {outname.replace(".fits","")}.weight.fits -PROJECTION_TYPE TPV '

        options = determine_swarp_options(inweight, outname, self.test_dir)

        self.assertEqual(expected_options, options)

    def test_2m_ogg(self):
        inweight = os.path.join(self.test_dir, 'weight.in')
        outname = "reference_ogg_ep04_rp_282.77_+25.31.fits"

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME {outname} -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -WEIGHT_IMAGE @{inweight} -WEIGHTOUT_NAME {outname.replace(".fits","")}.weight.fits -PROJECTION_TYPE TAN '

        options = determine_swarp_options(inweight, outname, self.test_dir)

        self.assertEqual(expected_options, options)

    def test_2m_coj(self):
        inweight = os.path.join(self.test_dir, 'weight.in')
        outname = "reference_coj_ep07_rp_282.77_-25.31.fits"

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME {outname} -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -WEIGHT_IMAGE @{inweight} -WEIGHTOUT_NAME {outname.replace(".fits","")}.weight.fits -PROJECTION_TYPE TAN '

        options = determine_swarp_options(inweight, outname, self.test_dir)

        self.assertEqual(expected_options, options)

class TestDetermineSwarpAlignOptions(ExternalCodeUnitTest):

    def setUp(self):
        super(TestDetermineSwarpAlignOptions, self).setUp()

        self.maxDiff = None

    def test1(self):
        outname = os.path.join(self.test_dir, "example-sbig-e10_aligned_to_example-sbig-e10.fits")
        weightname = outname.replace('.fits', '.weight.fits')

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME {outname} -NTHREADS 1 -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -SUBTRACT_BACK N -WEIGHTOUT_NAME {weightname} -WEIGHT_TYPE NONE -COMBINE_TYPE CLIPPED -PROJECTION_TYPE TPV '

        options = determine_swarp_align_options(self.test_fits_file, self.test_fits_file, self.test_dir, outname)

        self.assertEqual(expected_options, options)

    def test_1m(self):
        outname = os.path.join(self.test_dir, "reference_coj_fa99-e92_aligned_to_coj1m042-fa99-e92.fits")
        weightname = outname.replace('.fits', '.weight.fits')

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME {outname} -NTHREADS 1 -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -SUBTRACT_BACK N -WEIGHTOUT_NAME {weightname} -WEIGHT_TYPE NONE -COMBINE_TYPE CLIPPED -PROJECTION_TYPE TPV '

        options = determine_swarp_align_options(self.test_fits_file, self.test_fits_file, self.test_dir, outname)

        self.assertEqual(expected_options, options)

    def test_2m_coj(self):
        outname = os.path.join(self.test_dir, "reference_coj_ep99-e92_aligned_to_coj2m002-ep99-e92.fits")
        weightname = outname.replace('.fits', '.weight.fits')

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME {outname} -NTHREADS 1 -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -SUBTRACT_BACK N -WEIGHTOUT_NAME {weightname} -WEIGHT_TYPE NONE -COMBINE_TYPE CLIPPED -PROJECTION_TYPE TAN '

        options = determine_swarp_align_options(self.test_fits_file, self.test_fits_file, self.test_dir, outname)

        self.assertEqual(expected_options, options)

    def test_2m_ogg(self):
        outname = os.path.join(self.test_dir, "reference_ogg_ep99-e92_aligned_to_ogg2m001-ep99-e92.fits")
        weightname = outname.replace('.fits', '.weight.fits')

        expected_options = f'-BACK_SIZE 32 -IMAGEOUT_NAME {outname} -NTHREADS 1 -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -SUBTRACT_BACK N -WEIGHTOUT_NAME {weightname} -WEIGHT_TYPE NONE -COMBINE_TYPE CLIPPED -PROJECTION_TYPE TAN '

        options = determine_swarp_align_options(self.test_fits_file, self.test_fits_file, self.test_dir, outname)

        self.assertEqual(expected_options, options)


class TestDetermineHotpantsOptions(ExternalCodeUnitTest):
    def setUp(self):
        super(TestDetermineHotpantsOptions, self).setUp()

        # needs to modify the original image when running sextractor
        shutil.copy(os.path.abspath(self.test_banzai_file), self.test_dir)
        self.test_banzai_file_COPIED = os.path.join(self.test_dir, 'banzai_test_frame.fits')

        # hotpants requires a reference rms image in the dest_dir
        shutil.copy(os.path.abspath(self.test_banzai_rms_file), self.test_dir)


        self.remove = True

    def test1(self):
        bkgsub = os.path.join(self.test_dir, "banzai_test_frame.bkgsub.fits")
        aligned = os.path.join(self.test_dir, "banzai_test_frame_aligned_to_banzai_test_frame.fits")
        subtracted = os.path.join(self.test_dir, "banzai_test_frame.subtracted.fits")
        subtracted_rms = os.path.join(self.test_dir, "banzai_test_frame.subtracted.rms.fits")
        aligned_rms = os.path.join(self.test_dir, "banzai_test_frame.rms_aligned_to_banzai_test_frame.rms.fits")
        rms = os.path.join(self.test_dir, "banzai_test_frame.rms.fits")

        expected_options = f"-inim {bkgsub} -tmplim {aligned} -outim {subtracted} -tni {aligned_rms} -ini {rms} -oni {subtracted_rms} -hki -n i -c t -v 0 " \
                           f"-tu 57959 -iu 57959 -tl 43.892452606201175 -il -342.03351336669925 -nrx 3 -nry 3 -nsx 6.760000000000001 -nsy 6.793333333333333 -r 11.235949458513854 -rss 26.96627870043325 -fin 223.60679774997897"

        options = determine_hotpants_options(self.test_banzai_file_COPIED, self.test_banzai_file_COPIED, self.source_dir, self.test_dir, dbgOptions=True)

        self.maxDiff = None
        self.assertEqual(expected_options, options)


class TestDetermineMTDLINKOptions(ExternalCodeUnitTest):

    def test_nofile(self):
        expected_options = '-paramfile mtdi.lcogt.param -CPUTIME 1600 -MAXMISSES 3 -FILTER_PA 255.0 -FILTER_DELTAPA 10.0 -FILTER_MINRATE 0.38 -FILTER_MAXRATE 0.40'

        param_file = 'mtdi.lcogt.param'

        pa_rate_dict = {    'filter_pa': 255.0,
                            'filter_deltapa': 10.0,
                            'filter_minrate': 0.38,
                            'filter_maxrate': 0.4,
                        }

        options = determine_mtdlink_options(8, param_file, pa_rate_dict)

        self.assertEqual(expected_options, options)

    def test_badfile(self):
        expected_options = '-paramfile mtdi.lcogt.param -CPUTIME 1600 -MAXMISSES 3 -FILTER_PA 255.0 -FILTER_DELTAPA 10.0 -FILTER_MINRATE 0.38 -FILTER_MAXRATE 0.40'

        param_file = 'mtdi.lcogt.param'

        pa_rate_dict = {    'filter_pa': 255.0,
                            'filter_deltapa': 10.0,
                            'filter_minrate': 0.38,
                            'filter_maxrate': 0.4,
                        }

        options = determine_mtdlink_options(8, param_file, pa_rate_dict)

        self.assertEqual(expected_options, options)

    def test1(self):
        expected_options = '-paramfile mtdi.lcogt.param -CPUTIME 1600 -MAXMISSES 3 -FILTER_PA 255.0 -FILTER_DELTAPA 10.0 -FILTER_MINRATE 0.38 -FILTER_MAXRATE 0.40'

        param_file = 'mtdi.lcogt.param'

        pa_rate_dict = {    'filter_pa': 255.0,
                            'filter_deltapa': 10.0,
                            'filter_minrate': 0.38,
                            'filter_maxrate': 0.4,
                        }

        options = determine_mtdlink_options(8, param_file, pa_rate_dict)

        self.assertEqual(expected_options, options)


class TestUpdateFITSWCS(TestCase):

    def setUp(self):

        self.test_fits_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10.fits'))
        self.test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        self.test_scamp_headfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_scamp.head'))
        self.test_scamp_xml = os.path.join('photometrics', 'tests', 'example_scamp.xml')
        self.test_externscamp_headfile = os.path.join('photometrics', 'tests', 'example_externcat_scamp.head')
        self.test_externcat_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp.xml')
        self.test_externscamp_TPV_headfile = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.head')
        self.test_externcat_TPV_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.xml')
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.fits_file_output = os.path.abspath(os.path.join(self.test_dir, 'example-sbig-e10_output.fits'))
        self.banzai_file_output = os.path.abspath(os.path.join(self.test_dir, 'example-banzai-e92_output.fits'))

        self.precision = 7
        self.debug_print = False
        self.remove = True

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
                if self.debug_print: print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)

    def test_read_FITS_header(self):

        expected_object = 'S509435'

        hdu_number = 0
        header = fits.getheader(self.test_fits_file, hdu_number)
        object_val = header['OBJECT']

        self.assertEqual(expected_object, object_val)

    def test_read_SCAMP_header(self):

        test_scamp_file = open(self.test_scamp_headfile, 'r')

        expected_radesys_value = " 'ICRS    '           "

        for i in range(1, 100):
            line = test_scamp_file.readline()
            if 'RADESYS' in line:
                radesys_value = line[9:31]

        test_scamp_file.close()

        self.assertEqual(expected_radesys_value, radesys_value)

    def test_update_FITS_WCS_missing_FITS(self):
        expected_status = -1
        expected_header = None

        status, new_header = updateFITSWCS('wibble.fits', self.test_scamp_headfile, self.test_scamp_xml, self.fits_file_output)

        self.assertEqual(expected_status, status)
        self.assertEqual(expected_header, new_header)

    def test_update_FITS_WCS_missing_scamp_xml(self):
        expected_status = -2
        expected_header = None

        status, new_header = updateFITSWCS(self.test_fits_file, self.test_scamp_headfile, 'wibble.xml', self.fits_file_output)

        self.assertEqual(expected_status, status)
        self.assertEqual(expected_header, new_header)

    def test_update_FITS_WCS_missing_scamp_head(self):
        expected_status = -3
        expected_header = None

        status, new_header = updateFITSWCS(self.test_fits_file, 'wibble.head', self.test_scamp_xml, self.fits_file_output)

        self.assertEqual(expected_status, status)
        self.assertEqual(expected_header, new_header)

    def test_update_FITS_WCS(self):

        status, new_header = updateFITSWCS(self.test_fits_file, self.test_scamp_headfile, self.test_scamp_xml, self.fits_file_output)

        self.assertEqual(status, 0)

        expected = {
                     'crval1' : 1.783286919001E+02, 'crval2' : 1.169387882835E+01,
                     'crpix1' : 2.047592457311E+03, 'crpix2' : 2.048419571848E+03,
                     'cd1_1'  : 1.082433886779E-04,  'cd1_2' : 6.824629998000E-07,
                     'cd2_1'  : 7.053875928440E-07,  'cd2_2' : -1.082408809463E-04,
                     'secpix' : 0.389669,
                     'wcssolvr' : 'SCAMP-2.0.4',
                     'wcsrfcat' : '<Vizier/aserver.cgi?ucac4@cds>',
                     'wcsimcat' : 'ldac_test_catalog.fits',
                     'wcsnref' : 606, 'wcsmatch' : 64,
                     'wccattyp' : 'UCAC4@CDS',
                     'wcsrdres' : '0.21947/0.20434',
                     'wcsdelra' : 37.1754196, 'wcsdelde' : -51.2994992,
                     'wcserr' : 0,
                     'cunit1' : 'deg', 'cunit2' : 'deg'
                    }

        hdu_number = 0
        header = fits.getheader(self.fits_file_output, hdu_number)

        for key in expected:
            if type(expected[key]) == str:
                self.assertEqual(expected[key], header[key], msg="Failure on {}".format(key))
            else:
                self.assertAlmostEqual(expected[key], header[key], self.precision, msg="Failure on {}".format(key))

    def test_update_FITS_WCS_newer_SCAMP(self):

        # Make copy of header file, modify version number and writeout
        shutil.copy(self.test_scamp_headfile, self.test_dir)
        test_scamp_headfile = os.path.join(self.test_dir, os.path.basename(self.test_scamp_headfile))
        with open(test_scamp_headfile, 'r') as in_fh:
            header_lines = in_fh.readlines()
        test_scamp_headfile = test_scamp_headfile.replace('_scamp', '_newscamp')
        with open(test_scamp_headfile, 'w') as out_fh:
            for line in header_lines:
                if 'HISTORY' in line:
                    line = line.replace('2.0.4', '2.10.0')
                out_fh.write(line)

        status, new_header = updateFITSWCS(self.test_fits_file, test_scamp_headfile, self.test_scamp_xml, self.fits_file_output)

        self.assertEqual(status, 0)

        expected = {
                     'crval1' : 1.783286919001E+02, 'crval2' : 1.169387882835E+01,
                     'crpix1' : 2.047592457311E+03, 'crpix2' : 2.048419571848E+03,
                     'cd1_1'  : 1.082433886779E-04,  'cd1_2' : 6.824629998000E-07,
                     'cd2_1'  : 7.053875928440E-07,  'cd2_2' : -1.082408809463E-04,
                     'secpix' : 0.389669,
                     'wcssolvr' : 'SCAMP-2.10.0',
                     'wcsrfcat' : '<Vizier/aserver.cgi?ucac4@cds>',
                     'wcsimcat' : 'ldac_test_catalog.fits',
                     'wcsnref' : 606, 'wcsmatch' : 64,
                     'wccattyp' : 'UCAC4@CDS',
                     'wcsrdres' : '0.21947/0.20434',
                     'wcsdelra' : 37.1754196, 'wcsdelde' : -51.2994992,
                     'wcserr' : 0,
                     'cunit1' : 'deg', 'cunit2' : 'deg'
                    }

        hdu_number = 0
        header = fits.getheader(self.fits_file_output, hdu_number)

        for key in expected:
            if type(expected[key]) == str:
                self.assertEqual(expected[key], header[key], msg="Failure on {}".format(key))
            else:
                self.assertAlmostEqual(expected[key], header[key], self.precision, msg="Failure on {}".format(key))

    def test_update_FITS_WCS_GAIADR2(self):

        status, new_header = updateFITSWCS(self.test_banzai_file, self.test_externscamp_headfile, self.test_externcat_xml, self.banzai_file_output)

        self.assertEqual(status, 0)

        expected = {
                     'crval1' : 2.283330189100E+02, 'crval2' : 3.839546339622E+01,
                     'crpix1' : 7.621032903029E+02, 'crpix2' : 5.105117960168E+02,
                     'cd1_1'  : -1.024825024633E-06, 'cd1_2' : 3.162727554070E-04,
                     'cd2_1'  : -3.162997037181E-04, 'cd2_2' : -1.075429228793E-06,
                     'secpix' : 1.13853,
                     'wcssolvr' : 'SCAMP-2.0.4',
                     'wcsrfcat' : 'GAIA-DR2.cat',
                     'wcsimcat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                     'wcsnref' : 280, 'wcsmatch' : 106,
                     'wccattyp' : 'GAIA-DR2@CDS',
                     'wcsrdres' : '0.31469/0.30167', # ASTRRMS1*3600/ASTRRMS2*3600 from .head file
                     'wcsdelra' : 44.619981558,
                     'wcsdelde' : -37.1150613409,
                     'wcserr' : 0,
                     'cunit1' : 'deg',
                     'cunit2' : 'deg'
                    }

        hdu_number = 0
        header = fits.getheader(self.banzai_file_output, hdu_number)

        for key in expected:
            if type(expected[key]) == str:
                self.assertEqual(expected[key], header[key], msg="Failure on {}".format(key))
            else:
                self.assertAlmostEqual(expected[key], header[key], self.precision, msg="Failure on {}".format(key))

    def test_update_FITS_WCS_GAIADR2_new_header(self):

        status, new_header = updateFITSWCS(self.test_banzai_file, self.test_externscamp_headfile, self.test_externcat_xml, self.banzai_file_output)

        self.assertEqual(status, 0)

        expected = {
                     'pcrecipe' : 'BANZAI', 'pprecipe' : 'NEOEXCHANGE',
                     'crval1' : 2.283330189100E+02, 'crval2' : 3.839546339622E+01,
                     'crpix1' : 7.621032903029E+02, 'crpix2' : 5.105117960168E+02,
                     'cd1_1'  : -1.024825024633E-06, 'cd1_2' : 3.162727554070E-04,
                     'cd2_1'  : -3.162997037181E-04, 'cd2_2' : -1.075429228793E-06,
                     'secpix' : 1.13853,
                     'wcssolvr' : 'SCAMP-2.0.4',
                     'wcsrfcat' : 'GAIA-DR2.cat',
                     'wcsimcat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                     'wcsnref'  : 280, 'wcsmatch' : 106,
                     'wccattyp' : 'GAIA-DR2@CDS',
                     'wcsrdres' : '0.31469/0.30167', # ASTRRMS1*3600/ASTRRMS2*3600 from .head file
                     'wcsdelra' : 44.619981558, 'wcsdelde' : -37.1150613409,
                     'wcserr' : 0,
                     'cunit1' : 'deg', 'cunit2' : 'deg'
                    }

        for key in expected:
            if type(expected[key]) == str:
                self.assertEqual(expected[key], new_header[key], msg="Failure on {}".format(key))
            else:
                self.assertAlmostEqual(expected[key], new_header[key], self.precision, msg="Failure on {}".format(key))

    def test_update_FITS_WCS_GAIADR2_TPV_new_header(self):

        status, new_header = updateFITSWCS(self.test_banzai_file, self.test_externscamp_TPV_headfile, self.test_externcat_TPV_xml, self.banzai_file_output)

        self.assertEqual(status, 0)

        expected = { 'crval1' : 2.283330189100E+02, 'crval2' : 3.839546339622E+01,
                     'crpix1' : 7.620000000000E+02, 'crpix2' : 5.105000000000E+02,
                     'cd1_1'  : -1.083049787920E-06, 'cd1_2' : 3.162568176201E-04,
                     'cd2_1'  : -3.162568176201E-04, 'cd2_2' : -1.083049787920E-06,
                     'pv1_0'  : -3.493949558753E-05,
                     'pv1_1'  :  9.990845948728E-01,
                     'pv1_2'  :  5.944161242327E-04,
                     'pv1_4'  :  1.641289702411E-03,
                     'pv1_5'  :  2.859739464233E-03,
                     'pv1_6'  : -8.338448819528E-05,
                     'pv1_7'  :  4.778142218367E-02,
                     'pv1_8'  : -3.120516918032E-02,
                     'pv1_9'  :  1.005901992058E-02,
                     'pv1_10' : -1.475386390540E-02,
                     'pv2_0'  :  1.238320321566E-04,
                     'pv2_1'  :  9.992102543642E-01,
                     'pv2_2'  :  2.505722546811E-04,
                     'pv2_4'  : -1.613190458709E-03,
                     'pv2_5'  : -3.765739615064E-03,
                     'pv2_6'  : -6.917769250557E-03,
                     'pv2_7'  :  2.493514752913E-02,
                     'pv2_8'  :  1.947400823739E-02,
                     'pv2_9'  :  2.222081573598E-02,
                     'pv2_10' : -2.704416488002E-02,
                     'secpix' : 1.13853,
                     'wcssolvr' : 'SCAMP-2.0.4',
                     'wcsrfcat' : 'GAIA-DR2_228.33+38.40_43.3488mx29.0321m.cat',
                     'wcsimcat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                     'wcsnref' : 280, 'wcsmatch' : 103, 'wccattyp' : 'GAIA-DR2@CDS',
                     'wcsrdres' : '0.30803/0.34776', # ASTRRMS1*3600/ASTRRMS2*3600 from .head file
                     'wcsdelra' : 44.619981558, 'wcsdelde' : -37.1150613409,
                     'wcserr' : 0,
                     'cunit1' : 'deg', 'cunit2' : 'deg',
                     'ctype1' : 'RA---TPV', 'ctype2' : 'DEC--TPV',
                     'pcrecipe' : 'BANZAI', 'pprecipe' : 'NEOEXCHANGE'
                    }
        expected_pv_comment = 'TPV distortion coefficient'

        for key in expected:
            if type(expected[key]) == str:
                self.assertEqual(expected[key], new_header[key], msg="Failure on {}".format(key))
            else:
                self.assertAlmostEqual(expected[key], new_header[key], self.precision, msg="Failure on {}".format(key))
                if 'pv1_' in key or 'pv2_' in key:
                    self.assertEqual(expected_pv_comment, new_header.comments[key])
                else:
                    self.assertNotEqual(expected_pv_comment, new_header.comments[key])


class TestUpdateFITScalib(TestCase):

    def setUp(self):

        self.test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))

        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        # Need to copy files as we're modifying them. Example does not have existing L1ZP etc
        self.banzai_file_output = os.path.abspath(os.path.join(self.test_dir, 'example-banzai-e92_output.fits'))
        shutil.copy(self.test_banzai_file, self.banzai_file_output)

        self.test_header, self.test_cattype = get_header(self.banzai_file_output)

        self.precision = 7
        self.debug_print = False
        self.remove = True

        # Disable anything below CRITICAL level
        logging.disable(logging.CRITICAL)

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
                if self.debug_print: print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)

    def test_missing_file(self):
        expected_status = (-1, None)

        status = updateFITScalib({}, '/foo/bar.fits')

        self.assertEqual(expected_status, status)

    def test_bad_type(self):
        expected_status = (-2, None)

        status = updateFITScalib({}, self.banzai_file_output, 'ASCII')

        self.assertEqual(expected_status, status)

    def test_new_l1zp(self):
        header = deepcopy(self.test_header)
        header['zeropoint'] = 28.01
        header['zeropoint_err'] = 0.012
        header['zeropoint_src'] = 'py_zp_cvc-V0.1'

        expected_status = 0
        expected_keywords = { 'zeropoint' : 'L1ZP',
                              'zeropoint_err' : 'L1ZPERR',
                              'zeropoint_src' : 'L1ZPSRC',
                            }

        status, new_header = updateFITScalib(header,  self.banzai_file_output)

        self.assertEqual(expected_status, status)

        for key, fits_keyword in expected_keywords.items():
            self.assertTrue(fits_keyword in new_header, "Failure on " + fits_keyword)
            self.assertEqual(header[key], new_header[fits_keyword])

    def test_existing_l1zp(self):
        header = deepcopy(self.test_header)
        header['zeropoint'] = 28.01
        header['zeropoint_err'] = 0.012
        header['zeropoint_src'] = 'py_zp_cvc-V0.1'
        with fits.open(self.banzai_file_output, mode='update') as hdul:
            fits_header = hdul[0].header
            fits_header.set('L1ZP', 30.3, after='L1ELLIPA')
            fits_header.set('L1ZPERR', 0.003, after='L1ZP')
            hdul.flush()

        expected_status = 0
        expected_keywords = { 'zeropoint' : 'L1ZP',
                              'zeropoint_err' : 'L1ZPERR',
                              'zeropoint_src' : 'L1ZPSRC',
                            }

        status, new_header = updateFITScalib(header,  self.banzai_file_output)

        self.assertEqual(expected_status, status)

        for key, fits_keyword in expected_keywords.items():
            self.assertTrue(fits_keyword in new_header, "Failure on " + fits_keyword)
            self.assertEqual(header[key], new_header[fits_keyword])

    def test_new_l1zp_color(self):
        header = deepcopy(self.test_header)
        header['zeropoint'] = 28.01
        header['zeropoint_err'] = 0.012
        header['zeropoint_src'] = 'py_zp_cvc-V0.1'
        header['color_used'] = 'g-i'
        header['color'] = 0.1234
        header['color_err'] = 0.112

        expected_status = 0
        expected_keywords = { 'zeropoint' : 'L1ZP',
                              'zeropoint_err' : 'L1ZPERR',
                              'zeropoint_src' : 'L1ZPSRC',
                              'color_used' : 'L1COLORU',
                              'color' : 'L1COLOR',
                              'color_err' : 'L1COLERR',
                            }

        status, new_header = updateFITScalib(header,  self.banzai_file_output)

        self.assertEqual(expected_status, status)

        for key, fits_keyword in expected_keywords.items():
            self.assertTrue(fits_keyword in new_header, "Failure on " + fits_keyword)
            self.assertEqual(header[key], new_header[fits_keyword])


class TestGetSCAMPXMLInfo(SimpleTestCase):

    def setUp(self):

        self.test_scamp_xml = os.path.join('photometrics', 'tests', 'example_scamp.xml')
        self.test_externcat_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp.xml')
        self.test_externcat_tpv_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.xml')

        self.maxDiff = None

    def test_read(self):

        expected_results = { 'num_refstars' : 606,
                             'num_match'    : 64,
                             'wcs_refcat'   : '<Vizier/aserver.cgi?ucac4@cds>',
                             'wcs_cattype'  : 'UCAC4@CDS',
                             'wcs_imagecat' : 'ldac_test_catalog.fits',
                             'pixel_scale'  : 0.389669,
                             'as_contrast'  : 22.7779,
                             'xy_contrast'  : 18.6967
                           }

        results = get_scamp_xml_info(self.test_scamp_xml)

        self.assertEqual(len(expected_results), len(results))
        for key in expected_results.keys():
            if key == 'pixel_scale' or 'contrast' in key:
                self.assertAlmostEqual(expected_results[key], results[key], 5)
            else:
                self.assertEqual(expected_results[key], results[key])

    def test_read_extern_cat(self):

        expected_results = { 'num_refstars' : 280,
                             'num_match'    : 106,
                             'wcs_refcat'   : 'GAIA-DR2.cat',
                             'wcs_cattype'  : 'GAIA-DR2@CDS',
                             'wcs_imagecat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                             'pixel_scale'  : 1.13853,
                             'as_contrast'  : 20.1186,
                             'xy_contrast'  : 10.2858
                             }

        results = get_scamp_xml_info(self.test_externcat_xml)

        self.assertEqual(len(expected_results), len(results))
        for key in expected_results.keys():
            if key == 'pixel_scale' or 'contrast' in key:
                self.assertAlmostEqual(expected_results[key], results[key], 5)
            else:
                self.assertEqual(expected_results[key], results[key])

    def test_read_extern_cat_TPV(self):

        expected_results = { 'num_refstars' : 280,
                             'num_match'    : 103,
                             'wcs_refcat'   : 'GAIA-DR2_228.33+38.40_43.3488mx29.0321m.cat',
                             'wcs_cattype'  : 'GAIA-DR2@CDS',
                             'wcs_imagecat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                             'pixel_scale'  : 1.13853,
                             'as_contrast'  : 20.1186,
                             'xy_contrast'  : 10.2858
                           }

        results = get_scamp_xml_info(self.test_externcat_tpv_xml)

        self.assertEqual(len(expected_results), len(results))
        for key in expected_results.keys():
            if key == 'pixel_scale' or 'contrast' in key:
                self.assertAlmostEqual(expected_results[key], results[key], 5)
            else:
                self.assertEqual(expected_results[key], results[key], "Failure on " + key)


class TestReadMTDSFile(TestCase):

    def setUp(self):

        self.test_mtds_file = os.path.join('photometrics', 'tests', 'elp1m008-fl05-20160225-0095-e90.mtds')
        self.hdr_only_mtds_file = os.path.join('photometrics', 'tests', 'cpt1m013-kb76-20160505-0205-e11.mtds')

        self.maxDiff = None

        # Pylint can go to hell...
        self.dtypes =\
             {  'names' : ('det_number', 'frame_number', 'sext_number', 'jd_obs', 'ra', 'dec', 'x', 'y', 'mag', 'fwhm', 'elong', 'theta', 'rmserr', 'deltamu', 'area', 'score', 'velocity', 'sky_pos_angle', 'pixels_frame', 'streak_length'),
                'formats' : ('i4',       'i1',           'i4',          'f8',     'f8', 'f8', 'f4', 'f4', 'f4', 'f4',   'f4',    'f4',    'f4',     'f4',       'i4',   'f4',   'f4',       'f4',        'f4',           'f4')
             }

        # Map UserWarning to an exception for testing
        warnings.simplefilter('error', UserWarning)

    def test_no_file(self):

        expected_dets = {}

        dets = read_mtds_file('wibble')

        self.assertEqual(expected_dets, dets)

    def test_no_detections(self):

        expected_dets_dict = {  'version'   : 'DETSV2.0',
                                'num_frames': 6,
                                'frames' : [
                                            ('cpt1m013-kb76-20160505-0205-e11.fits', 2457514.335058),
                                            ('cpt1m013-kb76-20160505-0206-e11.fits', 2457514.336033),
                                            ('cpt1m013-kb76-20160505-0207-e10.fits', 2457514.336977),
                                            ('cpt1m013-kb76-20160505-0208-e10.fits', 2457514.337878),
                                            ('cpt1m013-kb76-20160505-0210-e10.fits', 2457514.339695),
                                            ('cpt1m013-kb76-20160505-0213-e11.fits', 2457514.342520),
                                           ],
                                'num_detections' : 0,
                                'detections': []
                             }

        dets = read_mtds_file(self.hdr_only_mtds_file)

        for key in expected_dets_dict.keys():
            if key == 'detections':
                self.assertEqual(len(expected_dets_dict[key]), len(dets[key]))
            else:
                self.assertEqual(expected_dets_dict[key], dets[key], msg="Failed on %s" % key)

    def test_read(self):

        expected_array = array([(1, 1, 3283, 2457444.656045, 10.924317, 39.27700, 2103.245, 2043.026, 19.26, 12.970, 1.764, -60.4, 0.27, 1.39, 34, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 2,    0, 2457444.657980, 10.924298, 39.27793, 2103.468, 2043.025,  0.00,  1.000, 1.000,   0.0, 0.27, 0.00,  0, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 3, 3409, 2457444.659923, 10.924271, 39.27887, 2104.491, 2043.034, 19.20, 11.350, 1.373, -57.3, 0.27, 1.38, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 4, 3176, 2457444.661883, 10.924257, 39.27990, 2104.191, 2043.844, 19.01, 10.680, 1.163, -41.5, 0.27, 1.52, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 5, 3241, 2457444.663875, 10.924237, 39.28087, 2104.365, 2043.982, 19.17, 12.940, 1.089, -31.2, 0.27, 1.27, 55, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 6, 3319, 2457444.665812, 10.924220, 39.28172, 2104.357, 2043.175, 18.82, 12.910, 1.254, -37.8, 0.27, 1.38, 69, 1.10, 0.497, 0.2, 9.0, 6.7)],
                                dtype=self.dtypes)

        expected_dets_dict = {  'version'   : 'DETSV2.0',
                                'num_frames': 6,
                                'frames' : [
                                            ('elp1m008-fl05-20160225-0095-e90.fits', 2457444.656045),
                                            ('elp1m008-fl05-20160225-0096-e90.fits', 2457444.657980),
                                            ('elp1m008-fl05-20160225-0097-e90.fits', 2457444.659923),
                                            ('elp1m008-fl05-20160225-0098-e90.fits', 2457444.661883),
                                            ('elp1m008-fl05-20160225-0099-e90.fits', 2457444.663875),
                                            ('elp1m008-fl05-20160225-0100-e90.fits', 2457444.665812),
                                           ],
                                'num_detections' : 23,
                                'detections': [None] * 23
                             }

        dets = read_mtds_file(self.test_mtds_file)

        for key in expected_dets_dict.keys():
            if key == 'detections':
                self.assertEqual(len(expected_dets_dict[key]), len(dets[key]))
            else:
                self.assertEqual(expected_dets_dict[key], dets[key])

        det1 = dets['detections'][0]
        for frame in arange(expected_dets_dict['num_frames']):
            for column in expected_array.dtype.names:
                self.assertAlmostEqual(expected_array[column][frame], det1[column][frame], 7)


class TestUnpackTarball(TestCase):
    def setUp(self):
        self.dir_path = os.path.join(os.getcwd(), 'photometrics', 'tests')
        self.tar_path = os.path.join(self.dir_path, 'test_tar2.tar.gz')
        self.unpack_dir = os.path.join(self.dir_path, 'test_unpacked')
        # self.spectra_path = os.path.join(self.dir_path,'LCOEngineering_0001588447_ftn_20180714_58314.tar.gz')
        # self.spectra_unpack_dir = os.path.join(self.dir_path,'spectra_unpacked')

    def test_unpack(self):
        expected_file_name = os.path.join(self.unpack_dir, 'file1.txt')
        expected_num_files = 3
        files = unpack_tarball(self.tar_path, self.unpack_dir)

        self.assertEqual(expected_num_files, len(files))
        self.assertIn(expected_file_name, files)

    # def test_unpack_spectra(self):
    #     expected_file_name = os.path.join(self.spectra_unpack_dir,'ogg2m001-en06-20180713-0009-e00.fits')
    #     expected_num_files = 27
    #
    #     files = unpack_tarball(self.spectra_path,self.spectra_unpack_dir)
    #
    #     self.assertEqual(expected_num_files,len(files))
    #     self.assertEqual(expected_file_name,files[1])

class TestFrameAperturePhotometry(ExternalCodeUnitTest):

    def setUp(self):
        super(TestFrameAperturePhotometry, self).setUp()
        # needs to copy and rename the hotpants file
        self.test_hotpants_file = os.path.join(self.testfits_dir, 'hotpants_test_frame.fits')
        self.test_hotpants_file_COPIED = os.path.join(self.test_dir, 'coj2m0-hotpants-test-e93.fits')
        self.test_hotpants_file_COPIED = shutil.copy(os.path.abspath(self.test_hotpants_file), self.test_hotpants_file_COPIED)
        self.test_hotpants_file_rms = os.path.join(self.testfits_dir, 'hotpants_test_frame.rms.fits')
        self.test_hotpants_file_rms_COPIED = os.path.join(self.test_dir, 'coj2m0-hotpants-test-e93.rms.fits')
        self.test_hotpants_file_rms_COPIED = shutil.copy(os.path.abspath(self.test_hotpants_file_rms), self.test_hotpants_file_rms_COPIED)

        body_params = {
                                'id': 5555500,
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

        desig_params = { 'body' : self.test_body, 'value' : 'Didymos', 'desig_type' : 'N', 'preferred' : True, 'packed' : False}
        test_desig, created = Designations.objects.get_or_create(**desig_params)
        desig_params['value'] = '65803'
        desig_params['desig_type'] = '#'
        test_desig, created = Designations.objects.get_or_create(**desig_params)

        block_params = {
                        'body' : self.test_body,
                        'request_number' : '12345',
                        'block_start' : datetime(2024, 6, 10, 0, 40),
                        'block_end' : datetime(2024, 6, 10, 17, 59),
                        'obstype' : Block.OPT_IMAGING,
                        'num_observed' : 1
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)

        frame_params = {
                        'sitecode' : 'E10',
                        'instrument' : 'ep07',
                        'exptime' : 170.0,
                        'filter' : 'rp',
                        'block' : self.test_block,
                        'frametype' : Frame.NEOX_SUB_FRAMETYPE,
                        'zeropoint' : 27.0,
                        'zeropoint_err' : 0.03,
                        'fwhm' : 2.7,
                        'midpoint' : block_params['block_start'] + timedelta(minutes=5)
                    }
        
        frame_params['filename'] = f"{self.test_hotpants_file_COPIED[-29:]}"
        frame_params['midpoint'] = datetime(2024, 6, 10, 11, 30)
        frame_params['frameid'] = 12345
        self.test_e93_frame, created = Frame.objects.get_or_create(**frame_params)
        # Create NEOX_RED_FRAMETYPE type also
        red_frame_params = frame_params.copy()
        red_frame_params['frametype'] = Frame.NEOX_RED_FRAMETYPE
        red_frame_params['filename'] = red_frame_params['filename'].replace('e93', 'e92')
        frame, created = Frame.objects.get_or_create(**red_frame_params)
        # Create NEOX_SUB_FRAMETYPE type also
        sub_frame_params = frame_params.copy()
        sub_frame_params['frametype'] = Frame.BANZAI_RED_FRAMETYPE
        sub_frame_params['filename'] = red_frame_params['filename'].replace('e92', 'e91')
        frame, created = Frame.objects.get_or_create(**sub_frame_params)

        self.ephem_ra = 283.5721268
        self.ephem_dec = -25.0549843
        #self.ephem_ra = 262.9291150055555
        #self.ephem_dec = -28.491441521497585
        self.remove = False
        self.debug_print = True

                

    def test_rms_file_not_present(self):
        #Remove RMS file for this test
        os.remove(self.test_hotpants_file_rms_COPIED)
        expected_results = None
        results = single_frame_aperture_photometry(self.test_hotpants_file_COPIED, self.ephem_ra, self.ephem_dec, False)
        self.assertEqual(expected_results, results)


    def compare_tables(self, expected_table, table, column, num_to_check, precision=6):
        for i in range(0, num_to_check+1):
            self.assertAlmostEqual(expected_table[column][i], table[column][i], precision)

    def test_single_frame_aperture_photometry(self):
        header, cattype = photometrics.catalog_subs.get_header(self.test_hotpants_file_COPIED)
        right_ascension = self.ephem_ra * u.deg
        declination = self.ephem_dec * u.deg
        positions = SkyCoord(right_ascension, declination, frame = "icrs")
        source_aperture = SkyCircularAperture(positions, r = 2.5*self.test_e93_frame.fwhm*u.arcsec)
        wcs = header['wcs']
        pix_source_aperture = source_aperture.to_pixel(wcs)
        FLUX2MAG = 2.5/np.log(10)
        expected_results = QTable()
        expected_results['id'] = [1]
        expected_results['xcenter'] = [48.45815299066739] *u.pix
        expected_results['ycenter'] = [48.576667811450456] * u.pix
        expected_results['aperture_sum'] = [135.01533390388389]
        expected_results['aperture_sum_err'] = [10.514787835583155]
        expected_results['FWHM'] = self.test_e93_frame.fwhm
        expected_results['ZP'] = self.test_e93_frame.zeropoint
        expected_results['ZP_sig'] = self.test_e93_frame.zeropoint_err
        expected_results['mag'] = -2.5*np.log10(expected_results['aperture_sum']) + self.test_e93_frame.zeropoint
        expected_results['magerr'] = FLUX2MAG * expected_results['aperture_sum_err'] / expected_results['aperture_sum']
        expected_results['filter'] = self.test_e93_frame.filter
        expected_results['aperture_radius'] = 2.5*self.test_e93_frame.fwhm
        exp_dtypes = expected_results.dtype
        results = single_frame_aperture_photometry(self.test_hotpants_file_COPIED, self.ephem_ra, self.ephem_dec, False)
        dtypes = results.dtype
        print(type(self.test_e93_frame.filter), type(results['filter'][0]))
        self.assertEqual(pix_source_aperture.positions[0], 48.45815299066739)
        self.assertEqual(pix_source_aperture.positions[1], 48.576667811450456)
        self.assertEqual(exp_dtypes, dtypes)
        self.compare_tables(expected_results, results, column = 'id',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'xcenter',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'ycenter',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'aperture_sum',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'aperture_sum_err',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'FWHM',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'ZP',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'ZP_sig',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'mag',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'magerr',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'filter',num_to_check= 0)
        self.compare_tables(expected_results, results, column = 'aperture_radius',num_to_check= 0)
