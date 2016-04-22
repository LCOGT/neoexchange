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

from django.test import TestCase
from django.forms.models import model_to_dict

#Import module to test
from photometrics.external_codes import *

class ExternalCodeUnitTest(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')

        # Path to the config files
        self.source_dir = os.path.join('photometrics', 'configs')

        self.test_fits_file = os.path.join('photometrics', 'tests', 'example-sbig-e10.fits')

    def tearDown(self):
        try:
            files_to_remove = glob(os.path.join(self.test_dir, '*'))
            for file_to_rm in files_to_remove:
                os.remove(file_to_rm)
        except OSError:
            print "Error removing files in temporary test directory", self.test_dir
        try:
            os.rmdir(self.test_dir)
            print "Removed", self.test_dir
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
        self.assertTrue(os.path.exists(test_file))

    def test_run_sextractor_nofile(self):

        expected_cmdline = './sex  -c sextractor_neox.conf'
        cmdline= run_sextractor(self.source_dir, self.test_dir, '', binary='./sex', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

    def test_run_sextractor_file(self):

        expected_cmdline = './sex foo.fits -c sextractor_neox.conf'
        cmdline= run_sextractor(self.source_dir, self.test_dir, 'foo.fits', binary='./sex', dbg=True)

        self.assertEqual(expected_cmdline, cmdline)

class TestDetermineOptions(ExternalCodeUnitTest):

    def test1(self):
        expected_options = '-GAIN 1.4 -PIXEL_SCALE 0.467 -SATUR_LEVEL 46000'

        options = determine_options(self.test_fits_file)

        self.assertEqual(expected_options, options)
