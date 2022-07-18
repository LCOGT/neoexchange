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

from astropy.io import fits
from numpy import array, arange

from django.test import TestCase
from django.forms.models import model_to_dict

# Import module to test
from photometrics.external_codes import *
from photometrics.catalog_subs import funpack_fits_file


class ExternalCodeUnitTest(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        # Path to the config files
        self.source_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

        self.testfits_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_fits_file = os.path.abspath(os.path.join(self.testfits_dir, 'example-sbig-e10.fits'))
        self.test_fits_catalog = os.path.abspath(os.path.join(self.testfits_dir, 'ldac_test_catalog.fits'))

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
        # LP 2022/06/30 Expected sources now 1929 after change in BACK_SIZE
        self.assertEqual(14+1929, len(test_lines))
        self.assertEqual(expected_line1, test_lines[0].rstrip())

    def test_setup_ldac_sextractor_dir(self):

        expected_configs = default_sextractor_config_files(catalog_type='FITS_LDAC')
        expected_status = 0

        status = setup_sextractor_dir(self.source_dir, self.test_dir, catalog_type='FITS_LDAC')

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')


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
        self.test_banzai_rms_file = os.path.join(self.testfits_dir, 'banzai_test_frame.rms.fits')
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

        expected_cmdline = f"./swarp -c swarp_neox.conf @{inlist} -BACK_SIZE 42 -IMAGEOUT_NAME reference.fits -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -WEIGHT_IMAGE @{inweight} -WEIGHTOUT_NAME reference.weight.fits"

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


class TestSwarpAlignRunner(ExternalCodeUnitTest):
    def test_make_ref_head(self):

        expected_headpath = os.path.join(self.test_dir, "example-sbig-e10_aligned_to_example-sbig-e10.head")

        headpath = make_ref_head(self.test_fits_file, self.test_fits_file, self.test_dir)

        self.assertEqual(expected_headpath, headpath)

        with open(headpath, 'r') as h:
            header = h.read()

        self.assertTrue('NAXIS' in header, msg="NAXIS data is not in this file.")
        self.assertTrue('CTYPE' in header, msg="WCS data is not in this file.")

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

        expected_cmdline = f"./swarp -c swarp_neox.conf {self.test_fits_file} -BACK_SIZE 42 -IMAGEOUT_NAME {outname} -NTHREADS 1 -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -SUBTRACT_BACK N -WEIGHTOUT_NAME {weightname} -WEIGHT_TYPE NONE -COMBINE_TYPE CLIPPED"
        cmdline = run_swarp_align(self.test_fits_file, self.test_fits_file, self.source_dir, self.test_dir, binary='./swarp', dbg=True)

        self.maxDiff = None
        self.assertEqual(expected_cmdline, cmdline)

        expected_status = 0
        status = run_swarp_align(self.test_fits_file, self.test_fits_file, self.source_dir, self.test_dir, dbg=False)

        self.assertEqual(expected_status, status)

        self.assertTrue(os.path.exists(outname))
        self.assertTrue(os.path.exists(weightname))
        self.assertTrue(os.path.exists(headname))


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

        options = determine_sextractor_options('wibble', self.test_dir)

        self.assertEqual(expected_options, options)

    def test_badfile(self):
        expected_options = ''

        options = determine_sextractor_options(os.path.join(self.source_dir, 'scamp_neox.cfg'), self.test_dir)

        self.assertEqual(expected_options, options)

    def test_rms(self):
        checkimage_name = os.path.join(self.test_dir, 'example-sbig-e10.rms.fits')
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.467 -SATUR_LEVEL 46000 -CHECKIMAGE_TYPE BACKGROUND_RMS -CHECKIMAGE_NAME {checkimage_name} -BACK_SIZE 42'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, checkimage_type='BACKGROUND_RMS')

        self.maxDiff = None
        self.assertEqual(expected_options, options)

    def test_bkgsub(self):
        checkimage_name = os.path.join(self.test_dir, 'example-sbig-e10.bkgsub.fits')
        expected_options = f'-GAIN 1.4 -PIXEL_SCALE 0.467 -SATUR_LEVEL 46000 -CHECKIMAGE_TYPE -BACKGROUND -CHECKIMAGE_NAME {checkimage_name} -BACK_SIZE 42'

        options = determine_sextractor_options(self.test_fits_file, self.test_dir, checkimage_type='-BACKGROUND')

        self.maxDiff = None
        self.assertEqual(expected_options, options)

    def test_bad_checkimage_type(self):
        expected_status = -4

        status = determine_sextractor_options(self.test_fits_file, self.test_dir, checkimage_type='banana')

        self.assertEqual(expected_status, status)


class TestDetermineSwarpOptions(ExternalCodeUnitTest):

    def test1(self):
        inweight = os.path.join(self.test_dir, 'weight.in')
        outname = "test_swarp_output.fits"

        expected_options = f'-BACK_SIZE 42 -IMAGEOUT_NAME test_swarp_output.fits -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -WEIGHT_IMAGE @{inweight} -WEIGHTOUT_NAME test_swarp_output.weight.fits '

        options = determine_swarp_options(inweight, outname, self.test_dir)

        self.assertEqual(expected_options, options)

class TestDetermineSwarpAlignOptions(ExternalCodeUnitTest):

    def test1(self):
        outname = os.path.join(self.test_dir, "example-sbig-e10_aligned_to_example-sbig-e10.fits")
        weightname = outname.replace('.fits', '.weight.fits')

        expected_options = f'-BACK_SIZE 42 -IMAGEOUT_NAME {outname} -NTHREADS 1 -VMEM_DIR {self.test_dir} -RESAMPLE_DIR {self.test_dir} -SUBTRACT_BACK N -WEIGHTOUT_NAME {weightname} -WEIGHT_TYPE NONE -COMBINE_TYPE CLIPPED '

        options = determine_swarp_align_options(self.test_fits_file, self.test_fits_file, self.test_dir)

        #self.maxDiff = None
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
