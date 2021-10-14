import os
import shutil
import tempfile
from glob import glob
from datetime import datetime

from photometrics.lightcurve_subs import *

from django.test import SimpleTestCase

class TestReadPhotomPipe(SimpleTestCase):

    def setUp(self):
        self.test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))

        self.debug_print = False
        self.maxDiff = None


    def test_read(self):
        expected_length = 62

        table = read_photompipe_file(self.test_lc_file)

        self.assertEqual(expected_length, len(table))

class TestWriteDartFormatFile(SimpleTestCase):

    def setUp(self):
        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))

        self.test_table = read_photompipe_file(test_lc_file)
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.remove = True
        self.debug_print = False
        self.maxDiff = None

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
        else:
            if self.debug_print:
                print("Test directory", self.test_dir, "not removed")

    def test_write(self):
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  SExtractor_flag  aprad',
        ' tfn1m001-fa11-20211012-0073-e91.fits  2459500.3339392  14.8400  0.0397  27.1845  0.0394  -12.3397    0.0052                0   2.14',
        ' tfn1m001-fa11-20211012-0074-e91.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0300  -12.3187    0.0053                3   2.20'
        ]

        # Modify some values to test rounding
        self.test_table[0]['mag'] = 14.84
        self.test_table[1]['ZP_sig'] = 0.03
        output_file = os.path.join(self.test_dir, 'test.tab')
        write_dartformat_file(self.test_table[0:2], output_file)

        with open(output_file, 'r') as table_file:
            lines = table_file.readlines()

        self.assertEqual(3, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i].rstrip())
