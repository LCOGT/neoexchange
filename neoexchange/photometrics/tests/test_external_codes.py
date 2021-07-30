
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

from astropy.io import fits
from astropy import units as u
from astropy.table import Table
from astropy.time import Time
from astropy.tests.helper import assert_quantity_allclose
from numpy import array, arange

from django.test import TestCase, SimpleTestCase
from django.forms.models import model_to_dict

# Import module to test
from photometrics.external_codes import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)


class ExternalCodeUnitTest(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        # Path to the config files
        self.source_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

        self.test_fits_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10.fits'))
        self.test_fits_catalog = os.path.abspath(os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits'))

        self.test_GAIADR2_catalog = os.path.abspath(os.path.join('photometrics', 'tests', 'GAIA-DR2.cat'))

        self.test_fits_file_set1_1 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0098-e90.fits'))
        self.test_fits_file_set1_2 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0099-e90.fits'))
        self.test_fits_file_set1_3 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0100-e90.fits'))
        self.test_fits_file_set1_4 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0101-e90.fits'))
        self.test_fits_file_set1_5 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0102-e90.fits'))
        self.test_fits_file_set1_6 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0103-e90.fits'))
        self.test_fits_file_set1_7 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0104-e90.fits'))
        self.test_fits_file_set1_8 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0105-e90.fits'))

        self.test_fits_file_set2_1 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'elp1m008-fl05-20160225-0095-e90.fits'))
        self.test_fits_file_set2_2 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'elp1m008-fl05-20160225-0096-e90.fits'))
        self.test_fits_file_set2_3 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'elp1m008-fl05-20160225-0097-e90.fits'))
        self.test_fits_file_set2_4 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'elp1m008-fl05-20160225-0098-e90.fits'))
        self.test_fits_file_set2_5 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'elp1m008-fl05-20160225-0099-e90.fits'))
        self.test_fits_file_set2_6 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'elp1m008-fl05-20160225-0100-e90.fits'))

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

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat'

        options = determine_scamp_options('foo.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_0m4_no_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat'

        options = determine_scamp_options('foo_0m4.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_2m0_no_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat'

        options = determine_scamp_options('foo_0m4.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_1m0_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -DISTORT_DEGREES 3 -PROJECTION_TYPE TPV'

        options = determine_scamp_options('test1m0-fa##-date.ldac')

        self.assertEqual(expected_options, options)

    def test_scamp_options_1m0_distortion_4th_order(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -DISTORT_DEGREES 4 -PROJECTION_TYPE TPV'

        options = determine_scamp_options('test1m0-fa##-date.ldac', distort_degrees=4)

        self.assertEqual(expected_options, options)

    def test_scamp_options_0m4_distortion_5th_order(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat -DISTORT_DEGREES 5 -PROJECTION_TYPE TPV'

        options = determine_scamp_options('test1m0-fa##-date.ldac', distort_degrees=5)

        self.assertEqual(expected_options, options)

    def test_scamp_options_1m0_no_distortion(self):

        expected_options = '-ASTREF_CATALOG FILE -ASTREFCAT_NAME GAIA-DR2.cat'

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



class TestSExtractorRunner(ExternalCodeUnitTest):

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

    def test_run_sextractor_nofile(self):

        expected_cmdline = './sex  -c sextractor_neox.conf'
        cmdline = run_sextractor(self.source_dir, self.test_dir, '', binary='./sex', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

    def test_run_sextractor_file(self):

        expected_cmdline = './sex foo.fits -c sextractor_neox.conf'
        cmdline = run_sextractor(self.source_dir, self.test_dir, 'foo.fits', binary='./sex', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

    @skipIf(find_binary("sex") is None, "Could not find SExtractor binary ('sex') in PATH")
    def test_run_sextractor_realfile(self):

        expected_status = 0
        expected_line1 = '#   1 NUMBER                 Running object number'

        status = run_sextractor(self.source_dir, self.test_dir, self.test_fits_file)

        self.assertEqual(expected_status, status)

        if self.debug_print:
            print(glob(os.path.join(self.test_dir, '*')))
        output_cat = os.path.join(self.test_dir, 'test.cat')
        self.assertTrue(os.path.exists(output_cat))
        test_fh = open(output_cat, 'r')
        test_lines = test_fh.readlines()
        test_fh.close()

        # Expected value is 14 lines of header plus 2086 sources
        self.assertEqual(14+2086, len(test_lines))
        self.assertEqual(expected_line1, test_lines[0].rstrip())

    def test_setup_ldac_sextractor_dir(self):

        expected_configs = default_sextractor_config_files(catalog_type='FITS_LDAC')
        expected_status = 0

        status = setup_sextractor_dir(self.source_dir, self.test_dir, catalog_type='FITS_LDAC')

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')


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

    def test_nofile(self):
        expected_options = ''

        options = determine_sext_options('wibble')

        self.assertEqual(expected_options, options)

    def test_badfile(self):
        expected_options = ''

        options = determine_sext_options(os.path.join(self.source_dir, 'scamp_neox.cfg'))

        self.assertEqual(expected_options, options)

    def test1(self):
        expected_options = '-GAIN 1.4 -PIXEL_SCALE 0.467 -SATUR_LEVEL 46000'

        options = determine_sext_options(self.test_fits_file)

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
                     'wcsnref' : 280, 'wcsmatch' : 23,
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
                     'crval1' : 2.283330189100E+02, 'crval2' : 3.839546339622E+01,
                     'crpix1' : 7.621032903029E+02, 'crpix2' : 5.105117960168E+02,
                     'cd1_1'  : -1.024825024633E-06, 'cd1_2' : 3.162727554070E-04,
                     'cd2_1'  : -3.162997037181E-04, 'cd2_2' : -1.075429228793E-06,
                     'secpix' : 1.13853,
                     'wcssolvr' : 'SCAMP-2.0.4',
                     'wcsrfcat' : 'GAIA-DR2.cat',
                     'wcsimcat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                     'wcsnref'  : 280, 'wcsmatch' : 23,
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
                     'wcsnref' : 280, 'wcsmatch' : 23, 'wccattyp' : 'GAIA-DR2@CDS',
                     'wcsrdres' : '0.30803/0.34776', # ASTRRMS1*3600/ASTRRMS2*3600 from .head file
                     'wcsdelra' : 44.619981558, 'wcsdelde' : -37.1150613409,
                     'wcserr' : 0,
                     'cunit1' : 'deg', 'cunit2' : 'deg',
                     'ctype1' : 'RA---TPV', 'ctype2' : 'DEC--TPV'
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


class TestGetSCAMPXMLInfo(TestCase):

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
                             'pixel_scale'  : 0.389669
                           }

        results = get_scamp_xml_info(self.test_scamp_xml)

        for key in expected_results.keys():
            if key == 'pixel_scale':
                self.assertAlmostEqual(expected_results[key], results[key], 6)
            else:
                self.assertEqual(expected_results[key], results[key])

    def test_read_extern_cat(self):

        expected_results = { 'num_refstars' : 280,
                             'num_match'    : 23,
                             'wcs_refcat'   : 'GAIA-DR2.cat',
                             'wcs_cattype'  : 'GAIA-DR2@CDS',
                             'wcs_imagecat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                             'pixel_scale'  : 1.13853
                           }

        results = get_scamp_xml_info(self.test_externcat_xml)

        for key in expected_results.keys():
            if key == 'pixel_scale':
                self.assertAlmostEqual(expected_results[key], results[key], 6)
            else:
                self.assertEqual(expected_results[key], results[key])

    def test_read_extern_cat_TPV(self):

        expected_results = { 'num_refstars' : 280,
                             'num_match'    : 23,
                             'wcs_refcat'   : 'GAIA-DR2_228.33+38.40_43.3488mx29.0321m.cat',
                             'wcs_cattype'  : 'GAIA-DR2@CDS',
                             'wcs_imagecat' : 'tfn0m414-kb99-20180529-0202-e91_ldac.fits',
                             'pixel_scale'  : 1.13853
                           }

        results = get_scamp_xml_info(self.test_externcat_tpv_xml)

        for key in expected_results.keys():
            if key == 'pixel_scale':
                self.assertAlmostEqual(expected_results[key], results[key], 6)
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


def dest_dir(args):
    pass


class TestDetermineListGPSOptions(ExternalCodeUnitTest):

    def setUp(self):
        self.rate = u.arcmin/u.minute
        super(TestDetermineListGPSOptions, self).setUp()
        self.remove = True

    def test_chile(self):
        expected_output = '2021-06-23T04:00:00 W86 -t1'

        output = determine_listGPS_options(datetime(2021,6,23,4,0,0), "W86")

        self.assertEqual(expected_output, output)

    def test_badsitecode(self):
        expected_output = ''

        output = determine_listGPS_options(datetime(2021,6,23,4,0,0),42)

        self.assertEqual(expected_output, output)

    def test_single_satellite(self):
        expected_output = '2021-06-23T04:00:00 W86 -t1 -oG42 -i1m -n600'

        output = determine_listGPS_options(datetime(2021, 6, 23, 4, 0, 0), "W86", "G42")

        self.assertEqual(expected_output, output)

    def test_setup_listgps_dir(self):

        expected_status = 0
        expected_files = { 'url_fail.txt' : "file",
                           'names.txt'    : "link",
                           'finals.all'   : "link",
                           'ObsCodes.htm' : "link"
                         }

        status = setup_listGPS_dir(self.source_dir, self.test_dir)

        self.assertTrue(os.path.exists(self.test_dir))
        self.assertEqual(expected_status, status)
        for config_file, filetype in expected_files.items():
            config_filepath = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(config_filepath))
            if filetype == "link":
                self.assertTrue(os.path.islink(config_filepath))
            else:
                # Links are files too, so can't just test that
                self.assertFalse(os.path.islink(config_filepath))
                self.assertTrue(os.path.isfile(config_filepath))

    def test_run_listGPS(self):

        expected_status = 0
        expected_lines = ['GPS positions for JD 2459388.666667 = 2021 Jun 23  4:00:00.000 UTC',
                        'Observatory (W86) Cerro Tololo-LCO B 2021 Jun 23  4:00:00.000',
                        'Longitude -70.804670, latitude -30.167328  alt 2204.09 m']
        ephem_date = datetime(2021,6,23,4,0,0)
        sitecode = 'W86'

        status = run_listGPS(self.source_dir, self.test_dir, ephem_date, sitecode)

        self.assertTrue(os.path.exists(self.test_dir))
        self.assertEqual(expected_status, status)


        # Test that output_file is being created using os.path.exists

        output_file = os.path.join(self.test_dir, 'list_gps_output.out')
        self.assertTrue(os.path.exists(output_file))


        # See if lines in file are equivalent to expected
        outputfile_fh= open(output_file, 'r')
        file_lines = outputfile_fh.readlines()
        outputfile_fh.close()

        for i, expected_line in enumerate(expected_lines):
            test_line = file_lines[i+2].rstrip()
            self.assertEqual(expected_line, test_line)

    def test_run_listGPS_single_satellite(self):

        expected_status = 0
        expected_lines = ['GPS positions for JD 2459388.666667 = 2021 Jun 23  4:00:00.000 UTC',
                        'Observatory (W85) Cerro Tololo-LCO A 2021 Jun 23  4:00:00.000',
                        'Longitude -70.804810, latitude -30.167407  alt 2201.78 m']
        ephem_date = datetime(2021,6,23,4,0,0)
        sitecode = 'W85'
        satellite = 'G25'

        status = run_listGPS(self.source_dir, self.test_dir, ephem_date, sitecode, satellite)

        self.assertTrue(os.path.exists(self.test_dir))
        self.assertEqual(expected_status, status)


        # Test that output_file is being created using os.path.exists

        output_file = os.path.join(self.test_dir, 'G25_W85_list_gps_output.out')
        self.assertTrue(os.path.exists(output_file))


        # See if lines in file are equivalent to expected
        outputfile_fh= open(output_file, 'r')
        file_lines = outputfile_fh.readlines()
        outputfile_fh.close()

        for i, expected_line in enumerate(expected_lines):
            test_line = file_lines[i+2].rstrip()
            self.assertEqual(expected_line, test_line)


class TestReadListGPSOutput(SimpleTestCase):

    def setUp(self):
        self.rate = u.arcmin/u.minute

        self.input_file = os.path.join('photometrics', 'tests', 'list_gps_output.out')
        self.single_input_file = os.path.join('photometrics', 'tests', 'G25_W85_example.out')
        self.bad_input_file = os.path.join('photometrics', 'tests', 'G03_K92_listgps_output.bad')
        self.bad_elo_input_file = os.path.join('photometrics', 'tests', 'G03_V37_listgps_output.bad')
        self.bad_site_input_file = os.path.join('photometrics', 'tests', 'F65_listgps_output.bad')

    def test_read_listGPS_output(self):
        """Tests first and last rows of created table object"""

        expected_numcolumns = 12
        expected_numrows = 37

        output = read_listGPS_output(self.input_file)
        self.assertTrue(isinstance(output, Table))

        self.assertEqual(expected_numcolumns, len(output.columns))
        self.assertEqual(expected_numrows, len(output))

        # Test contents of first and last rows
        expected_firstline = ['C34:', '*', '11 39 21.9774', '+01 32 46.175',
            26843.16644*u.km, 273.4*u.deg, 3.1*u.deg, 83*u.deg, 28.34*self.rate, 146.5*u.deg,
            '2018-078B Beidou-3 M16',
            SkyCoord('11 39 21.9774', '+01 32 46.175', unit=(u.hourangle, u.deg))]
        expected_lastline = ['E02:', '', '16 55 46.3996', '-20 23 19.273',
            23315.41979*u.km, 327.5*u.deg, 78.6*u.deg, 163*u.deg, 30.55*self.rate, 32.4*u.deg,
            '2016-030A GALILEO-2', SkyCoord('16 55 46.3996', '-20 23 19.273', unit=(u.hourangle, u.deg))]

        test_line1 = output[0]
        for i, test_value in enumerate(test_line1):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_firstline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_firstline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_firstline[i], test_value)

        test_last = output[-1]
        for i, test_value in enumerate(test_last):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_lastline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_lastline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_lastline[i], test_value)


    def test_read_listGPS_output_low_precision(self):
        """Tests handling low precision sitecodes warning message"""

        expected_numcolumns = 12
        expected_numrows = 37

        output = read_listGPS_output(self.bad_site_input_file)
        self.assertTrue(isinstance(output, Table))

        self.assertEqual(expected_numcolumns, len(output.columns))
        self.assertEqual(expected_numrows, len(output))


    def test_read_listGPS_single_satellite_output(self):
        """Tests first and last rows of created table object for single satellite"""

        expected_numcolumns = 10
        expected_numrows = 600

        output = read_listGPS_output(self.single_input_file, singlesat=True)
        self.assertTrue(isinstance(output, Table))

        self.assertEqual(expected_numcolumns, len(output.columns))
        self.assertEqual(expected_numrows, len(output))

        # Test contents of first and last rows
        expected_firstline = [Time(datetime(2021,6,23,4,00,00000)), '19 58 07.7654', '+24 16 48.964',
                              23108.73742*u.km, 38.9*u.deg, 23.9*u.deg, 125*u.deg, 33.13*self.rate,
                              34.1*u.deg, SkyCoord('19 58 07.7654', '+24 16 48.964', unit=(u.hourangle, u.deg))]
        expected_lastline = [Time(datetime(2021,6,23,13,59,00000)), '16 36 01.0247', '-23 11 15.764',
                             29620.56364*u.km, 200.4*u.deg, -33.7*u.deg, 159*u.deg, 29.07*self.rate,
                             49.5*u.deg, SkyCoord('16 36 01.0247', '-23 11 15.764', unit=(u.hourangle, u.deg))]

        test_line1 = output[0]
        for i, test_value in enumerate(test_line1):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_firstline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_firstline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_firstline[i], test_value)

        test_last = output[-1]
        for i, test_value in enumerate(test_last):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_lastline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_lastline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_lastline[i], test_value)


    def test_read_listGPS_single_satellite_bad_output(self):
        """Tests first and last rows of created table object for single
        satellite with badly formed data"""

        expected_numcolumns = 10
        expected_numrows = 3

        output = read_listGPS_output(self.bad_input_file, singlesat=True)
        self.assertTrue(isinstance(output, Table))

        self.assertEqual(expected_numcolumns, len(output.columns))
        self.assertEqual(expected_numrows, len(output))

        # Test contents of first and last rows
        expected_firstline = [Time(datetime(2021,7,19,22,42,0)), '04 36 40.6234', '-35 58 22.321',
                              26652.68026*u.km, 141.4*u.deg, -7.3*u.deg, 74*u.deg, 29.66*self.rate,
                              50.1*u.deg, SkyCoord('04 36 40.6234', '-35 58 22.321', unit=(u.hourangle, u.deg))]
        expected_lastline = [Time(datetime(2021,7,19,22,44,0)), '04 40 23.3893', '-35 20 08.567',
                             26731.76146*u.km, 141.2*u.deg,  -8.0*u.deg,  73*u.deg, 29.58*self.rate,
                             49.5*u.deg, SkyCoord('04 40 23.3893', '-35 20 08.567', unit=(u.hourangle, u.deg))]

        test_line1 = output[0]
        for i, test_value in enumerate(test_line1):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_firstline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_firstline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_firstline[i], test_value)

        test_last = output[-1]
        for i, test_value in enumerate(test_last):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_lastline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_lastline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_lastline[i], test_value)


    def test_read_listGPS_single_satellite_bad_elong(self):
        """Tests first and last rows of created table object for single
        satellite which goes into Earth's shadow and part of the Elo data is bad"""

        expected_numcolumns = 10
        expected_numrows = 3

        output = read_listGPS_output(self.bad_elo_input_file, singlesat=True)
        self.assertTrue(isinstance(output, Table))

        self.assertEqual(expected_numcolumns, len(output.columns))
        self.assertEqual(expected_numrows, len(output))

        # Test contents of first and last rows
        expected_firstline = [Time(datetime(2021,7,21, 7, 3,0)), '19 01 53.3612', '-22 14 34.879',
                              22441.37067*u.km, 197.3*u.deg, 35.1*u.deg, 166*u.deg, 33.0*self.rate,
                              150.0*u.deg, SkyCoord('19 01 53.3612', '-22 14 34.879', unit=(u.hourangle, u.deg))]
        expected_lastline = [Time(datetime(2021,7,21, 7,59,0)), '20 20 06.4459', '-46 45 17.517',
                             24559.05256*u.km, 186.7*u.deg, 12.1*u.deg, 153*u.deg, 29.61*self.rate,
                             142.6*u.deg, SkyCoord('20 20 06.4459', '-46 45 17.517', unit=(u.hourangle, u.deg))]

        assert_quantity_allclose(153*u.deg, output['Elo'].min())
        assert_quantity_allclose(166*u.deg, output['Elo'].max())


        test_line1 = output[0]
        for i, test_value in enumerate(test_line1):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_firstline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_firstline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_firstline[i], test_value)

        test_last = output[-1]
        for i, test_value in enumerate(test_last):
            if isinstance(test_value, SkyCoord):
                assert_quantity_allclose(expected_lastline[i].ra, test_value.ra, 1e-5)
                assert_quantity_allclose(expected_lastline[i].dec, test_value.dec, 1e-5)
            else:
                self.assertEqual(expected_lastline[i], test_value)


class TestFilterListGPSOutput(SimpleTestCase):
    #Doesn't need DB or directories so can be a SimpleTestCase

    def setUp(self):
        input_file = os.path.abspath(os.path.join('photometrics', 'tests', 'list_gps_output.out'))
        self.table = read_listGPS_output(input_file)

    def test_default(self):
        """Tests satellite filter for under 30 degrees altitude"""

        filter_table = filter_listGPS_output(self.table)
        self.assertNotEqual(len(self.table), len(filter_table))

    def test_noreverse(self):
        """Tests reverse"""

        filter_table = filter_listGPS_output(self.table, self.table['Alt']>0*u.deg, reverse=False)
        self.assertEqual(self.table['Alt'].min(), filter_table['Alt'][0])
        self.assertEqual(self.table['Alt'].max(), filter_table['Alt'][-1])

    def test_reverse(self):
        """Tests reverse"""

        filter_table = filter_listGPS_output(self.table, self.table['Alt']>0*u.deg, reverse=True)

        self.assertEqual(self.table['Alt'].max(), filter_table['Alt'][0])
        self.assertEqual(self.table['Alt'].min(), filter_table['Alt'][-1])

    def test_noreverse_specific_col(self):
        """Tests reverse"""

        filter_table = filter_listGPS_output(self.table, self.table['Alt']>0*u.deg, sort_column='Alt', reverse=False)
        self.assertEqual(self.table['Alt'].min(), filter_table['Alt'][0])
        self.assertEqual(self.table['Alt'].max(), filter_table['Alt'][-1])

    def test_reverse_specific_col(self):
        """Tests reverse"""

        filter_table = filter_listGPS_output(self.table, self.table['Alt']>0*u.deg, sort_column='Alt', reverse=True)

        self.assertEqual(self.table['Alt'].max(), filter_table['Alt'][0])
        self.assertEqual(self.table['Alt'].min(), filter_table['Alt'][-1])

    def test_noreverse_elong(self):
        """Tests sort, noreverse on elongation """

        filter_table = filter_listGPS_output(self.table, self.table['Alt']>0*u.deg, sort_column='Elo', reverse=False)
        self.assertEqual(self.table['Elo'].min(), filter_table['Elo'][0])
        self.assertEqual(self.table['Elo'].max(), filter_table['Elo'][-1])

    def test_reverse_elong(self):
        """Tests reversed sort on elongation"""

        filter_table = filter_listGPS_output(self.table, self.table['Elo']>0*u.deg, sort_column='Elo', reverse=True)

        self.assertEqual(self.table['Elo'].max(), filter_table['Elo'][0])
        self.assertEqual(self.table['Elo'].min(), filter_table['Elo'][-1])

    def test_sort_bad(self):
        """Tests sort on non-existent column"""

        filter_table = filter_listGPS_output(self.table, self.table['Alt']>0*u.deg, sort_column='foo', reverse=True)

        self.assertEqual(self.table['Alt'][0], filter_table['Alt'][0])
        self.assertEqual(self.table['Alt'][-1], filter_table['Alt'][-1])
        self.assertEqual(self.table['Elo'][0], filter_table['Elo'][0])
        self.assertEqual(self.table['Elo'][-1], filter_table['Elo'][-1])

