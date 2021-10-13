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
