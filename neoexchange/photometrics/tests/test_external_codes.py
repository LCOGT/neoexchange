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

        pa_rate_dict = {    'filter_pa': 255.0,
                            'filter_detlapa': 5.0,
                            'filter_minrate': 0.38,
                            'filter_maxrate': 0.4,
                        }

        expected_cmdline = 'mtdlink'
        cmdline = run_mtdlink(self.source_dir, self.test_dir, '', 8, pa_rate_dict, binary='mtdlink', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

    def test_run_mtdlink_file(self):

        pa_rate_dict = {    'filter_pa': 255.0,
                            'filter_detlapa': 5.0,
                            'filter_minrate': 0.38,
                            'filter_maxrate': 0.4,
                        }


        expected_cmdline = 'mtdlink  foo.fits foo2.fits foo3.fits'
        cmdline = run_mtdlink(self.source_dir, self.test_dir, 'foo.fits foo2.fits foo3.fits', 3, pa_rate_dict, binary='mtdlink', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

    @skipIf(find_binary("mtdlink") == None, "Could not find MTDLINK binary ('mtdlink') in PATH")
    def test_run_mtdlink_realfile(self):

        expected_status = 0
        expected_line1 = 'DETSV2.0'

        test_fits_file_1 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0098-e90.fits'))
        test_fits_file_2 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0099-e90.fits'))
        test_fits_file_3 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0100-e90.fits'))
        test_fits_file_4 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0101-e90.fits'))
        test_fits_file_5 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0102-e90.fits'))
        test_fits_file_6 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0103-e90.fits'))
        test_fits_file_7 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0104-e90.fits'))
        test_fits_file_8 = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'cpt1m010-kb70-20160225-0105-e90.fits'))

        data, header = fits.getdata(test_fits_file_1, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_1, data, header, clobber=True, checksum=True)

        data, header = fits.getdata(test_fits_file_2, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_2, data, header, clobber=True, checksum=True)

        data, header = fits.getdata(test_fits_file_3, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_3, data, header, clobber=True, checksum=True)

        data, header = fits.getdata(test_fits_file_4, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_4, data, header, clobber=True, checksum=True)

        data, header = fits.getdata(test_fits_file_5, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_5, data, header, clobber=True, checksum=True)

        data, header = fits.getdata(test_fits_file_6, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_6, data, header, clobber=True, checksum=True)

        data, header = fits.getdata(test_fits_file_7, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_7, data, header, clobber=True, checksum=True)

        data, header = fits.getdata(test_fits_file_8, header=True)
        if header['MJD'] == None:
            mjd = header['MJD-OBS']
            header.insert('MJD-OBS', ('MJD', mjd, '[UTC days] Start date/time (Modified Julian Dat'), after=True)
            fits.writeto(test_fits_file_8, data, header, clobber=True, checksum=True)

        test_file_string = str(test_fits_file_1)+' '+str(test_fits_file_2)+' '+str(test_fits_file_3)+' '+str(test_fits_file_4)+' '+str(test_fits_file_5)+' '+str(test_fits_file_6)+' '+str(test_fits_file_7)+' '+str(test_fits_file_8)

        pa_rate_dict = {    'filter_pa': 255.0,
                            'filter_detlapa': 5.0,
                            'filter_minrate': 0.38,
                            'filter_maxrate': 0.4,
                        }

        status = run_mtdlink(self.source_dir, self.test_dir, test_file_string, 8, pa_rate_dict)

        self.assertEqual(expected_status, status)

        if self.debug_print: print glob(os.path.join(self.test_dir, '*'))
        output_mtds = os.path.join(self.test_dir, 'cpt1m010-kb70-20160225-0098-e90.mtds')
        self.assertTrue(os.path.exists(output_mtds))
        test_fh = open(output_mtds, 'r')
        test_lines = test_fh.readlines()
        test_fh.close()

        # Expected value is 10 lines of intro plus 336 sources
        self.assertEqual(10+336, len(test_lines))
        self.assertEqual(expected_line1, test_lines[0].rstrip())

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

class TestDetermineMTDLINKOptions(ExternalCodeUnitTest):

    def test_nofile(self):
        expected_options = ''

        options = determine_mtdlink_options('wibble', 8)

        self.assertEqual(expected_options, options)

    def test_badfile(self):
        expected_options = ''

        options = determine_mtdlink_options(os.path.join(self.source_dir, 'scamp_neox.cfg'), 8)

        self.assertEqual(expected_options, options)

    def test1(self):
        expected_options = '-IP_MAXADU 46000 -CPUTIME 1600 -MAXMISSES 3'

        options = determine_mtdlink_options(self.test_fits_file, 8)

        self.assertEqual(expected_options, options)

class TestUpdateFITSWCS(TestCase):

    def setUp(self):

        self.test_fits_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10.fits'))
        self.test_scamp_headfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_scamp.head'))
        self.test_scamp_xml = os.path.join('photometrics', 'tests', 'example_scamp.xml')

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

        fits_file_output = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10_output.fits'))
        status = updateFITSWCS(self.test_fits_file, self.test_scamp_headfile, self.test_scamp_xml, fits_file_output)

        self.assertEqual(status, 0)

        expected_crval1 = 1.783286919001E+02
        expected_crval2 = 1.169387882835E+01
        expected_crpix1 = 2.047592457311E+03
        expected_crpix2 = 2.048419571848E+03
        expected_cd1_1 = 1.082433886779E-04
        expected_cd1_2 = 6.824629998000E-07
        expected_cd2_1 = 7.053875928440E-07
        expected_cd2_2 = -1.082408809463E-04
        expected_wcssolvr = 'SCAMP-2.0.4'
        expected_wcsrfcat = '<Vizier/aserver.cgi?ucac4@cds>'
        expected_wcsimcat = 'ldac_test_catalog.fits'
        expected_wcsnref = 606
        expected_wcsmatch = 64
        expected_wccattyp = 'UCAC4@CDS'
        expected_wcsrdres = '0.21947/0.20434'
        expected_wcsdelra = 37.175
        expected_wcsdelde = -51.299
        expected_wcserr = 0
        expected_units = 'deg'

        hdu_number = 0
        header = fits.getheader(fits_file_output, hdu_number)
        cunit1 = header['CUNIT1']
        cunit2 = header['CUNIT2']
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

        self.assertEqual(expected_units, cunit1)
        self.assertEqual(expected_units, cunit2)
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
