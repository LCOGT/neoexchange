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

import os
from glob import glob
import tempfile
from unittest import skipIf
from astropy.io import fits

from django.test import TestCase
from django.forms.models import model_to_dict

#Import module to test
from photometrics.external_codes import *

class ExternalCodeUnitTest(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')

        # Path to the config files
        self.source_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

        self.test_fits_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10.fits'))
        self.test_fits_catalog = os.path.abspath(os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits'))

        self.debug_print = False

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print "Error removing files in temporary test directory", self.test_dir
            try:
                os.rmdir(self.test_dir)
                if self.debug_print: print "Removed", self.test_dir
            except OSError:
                print "Error removing temporary test directory", self.test_dir

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
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'scamp_neox.cfg')))

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

    @skipIf(find_binary("sex") == None, "Could not find SExtractor binary ('sex') in PATH")
    def test_run_sextractor_realfile(self):

        expected_status = 0
        expected_line1 = '#   1 NUMBER                 Running object number'

        status = run_sextractor(self.source_dir, self.test_dir, self.test_fits_file)

        self.assertEqual(expected_status, status)

        if self.debug_print: print glob(os.path.join(self.test_dir, '*'))
        output_cat = os.path.join(self.test_dir, 'test.cat')
        self.assertTrue(os.path.exists(output_cat))
        test_fh = open(output_cat, 'r')
        test_lines = test_fh.readlines()
        test_fh.close()

        # Expected value is 14 lines of header plus 2086 sources
        self.assertEqual(14+2086, len(test_lines))
        self.assertEqual(expected_line1, test_lines[0].rstrip())

    def test_setup_ldac_sextractor_dir(self):

        expected_configs = default_sextractor_config_files(catalog_type = 'FITS_LDAC')
        expected_status = 0

        status = setup_sextractor_dir(self.source_dir, self.test_dir, catalog_type = 'FITS_LDAC')

        self.assertEqual(expected_status, status)

        for config_file in expected_configs:
            test_file = os.path.join(self.test_dir, config_file)
            self.assertTrue(os.path.exists(test_file), msg=config_file + ' is missing')

    @skipIf(find_binary("scamp") == None, "Could not find SCAMP binary ('scamp') in PATH")
    def test_run_scamp_realfile(self):

        expected_status = 0
        expected_line1 = 'EQUINOX =        2000.00000000 / Mean equinox'

        status = run_scamp(self.source_dir, self.test_dir, self.test_fits_catalog)

        self.assertEqual(expected_status, status)
        if self.debug_print: print glob(os.path.join(self.test_dir, '*'))

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


class TestDetermineOptions(ExternalCodeUnitTest):

    def test_nofile(self):
        expected_options = ''

        options = determine_options('wibble')

        self.assertEqual(expected_options, options)

    def test_badfile(self):
        expected_options = ''

        options = determine_options(os.path.join(self.source_dir, 'scamp_neox.cfg'))

        self.assertEqual(expected_options, options)

    def test1(self):
        expected_options = '-GAIN 1.4 -PIXEL_SCALE 0.467 -SATUR_LEVEL 46000'

        options = determine_options(self.test_fits_file)

        self.assertEqual(expected_options, options)

class TestUpdateFITSWCS(TestCase):

    def setUp(self):

        self.test_fits_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10.fits'))
        self.test_scamp_headfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_scamp.head'))

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

    def test_update_FITS_WCS(self):

        test_scamp_file = open(self.test_scamp_headfile, 'r')

        fits_file, fits_file_output, scamp_file = updateFITSWCS(self.test_fits_file, test_scamp_file)

        test_scamp_file.close()

        expected_crval1 = 1.783286919001E+02
        expected_crval2 = 1.169387882835E+01
        expected_crpix1 = 2.047592457311E+03
        expected_crpix2 = 2.048419571848E+03
        expected_cd1_1 = 1.082433886779E-04
        expected_cd1_2 = 6.824629998000E-07
        expected_cd2_1 = 7.053875928440E-07
        expected_cd2_2 = -1.082408809463E-04
        expected_wcssolvr = 'SCAMP-2.0.4'
        expected_wcsrfcat = 'null'
        expected_wcsimcat = 'null'
        expected_wcsnref = 0
        expected_wcsmatch = 0
        expected_wccattyp = 'null'
        expected_wcsrdres = '6.1e-05/5.68e-05'
        expected_wcsdelra = 37.175
        expected_wcsdelde = -51.299
        expected_wcserr = 0

        hdu_number = 0
        header = fits.getheader(fits_file_output, hdu_number)
        crval1 = header['CRVAL1']
        crval2 = header['CRVAL2']
        crpix1 = header['CRPIX1']
        crpix2 = header['CRPIX2']
        cd1_1 = header['CD1_1']
        cd1_2 = header['CD1_2']
        cd2_1 = header['CD2_1']
        cd2_2 = header['CD2_2']
        wcssolvr = header['WCSSOLVR']
        wcsrfcat = header['WCSRFCAT']
        wcsimcat = header['WCSIMCAT']
        wcsnref = header['WCSNREF']
        wcsmatch = header['WCSMATCH']
        wccattyp = header['WCCATTYP']
        wcsrdres = header['WCSRDRES']
        wcsdelra = header['WCSDELRA']
        wcsdelde = header['WCSDELDE']
        wcserr = header['WCSERR']

        self.assertEqual(expected_crval1, crval1)
        self.assertEqual(expected_crval2, crval2)
        self.assertEqual(expected_crpix1, crpix1)
        self.assertEqual(expected_crpix2, crpix2)
        self.assertEqual(expected_cd1_1, cd1_1)
        self.assertEqual(expected_cd1_2, cd1_2)
        self.assertEqual(expected_cd2_1, cd2_1)
        self.assertEqual(expected_cd2_2, cd2_2)
        self.assertEqual(expected_wcssolvr, wcssolvr)
        self.assertEqual(expected_wcsrfcat, wcsrfcat)
        self.assertEqual(expected_wcsimcat, wcsimcat)
        self.assertEqual(expected_wcsnref, wcsnref)
        self.assertEqual(expected_wcsmatch, wcsmatch)
        self.assertEqual(expected_wccattyp, wccattyp)
        self.assertEqual(expected_wcsrdres, wcsrdres)
        self.assertAlmostEqual(expected_wcsdelra, wcsdelra, 3)
        self.assertAlmostEqual(expected_wcsdelde, wcsdelde, 3)
        self.assertEqual(expected_wcserr, wcserr)

class TestGetSCAMPXMLInfo(TestCase):

    def setUp(self):

        self.test_scamp_xml = os.path.join('photometrics', 'tests', 'example_scamp.xml')

    def test_read(self):

        expected_results = { 'num_refstars' : 606,
                             'num_match'    : 64,
                             'wcs_refcat'   : '<Vizier/aserver.cgi?ucac4@cds>',
                             'wcs_cattype'  : 'UCAC4@CDS',
                             'wcs_imagecat' : 'ldac_test_catalog.fits'
                           }

        results = get_scamp_xml_info(self.test_scamp_xml)

        self.assertEqual(expected_results, results)
