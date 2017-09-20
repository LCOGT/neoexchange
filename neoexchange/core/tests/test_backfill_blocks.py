import os
import tempfile
from glob import glob

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from core.models import Block, Frame, Body

class BackFillBlocksTest(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')
        self.test_date = '20990420'
        self.test_dataroot = os.path.join(self.temp_dir, self.test_date)
        self.test_target = 'P10w5z5'
        self.test_rockblocknum = self.test_target + '_1234567'
        self.test_rockdir = os.path.join(self.test_dataroot, self.test_rockblocknum)
        os.makedirs(self.test_rockdir)
        self.debug_print = False

        body_params = {     'provisional_name': 'P10w5z5',
                            'origin': 'M',
                            'source_type': 'U',
                            'elements_type': 'MPC Minor Planet',
                            'active': True,
                            'epochofel': '2016-07-11 00:00:00',
                            'orbinc': 6.35992,
                            'longascnode': 108.82267,
                            'argofperih': 202.15361,
                            'eccentricity': 0.384586,
                            'meandist': 2.3057577,
                            'meananom': 352.55523,
                            'abs_mag': 21.3,
                            'slope': 0.15,
                        }
        self.test_body, created = Body.objects.get_or_create(**body_params)

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, self.test_date, '*'))
                for file_to_rm in files_to_remove:
                    os.rmdir(file_to_rm)
            except OSError:
                print "Error removing files in temporary test directory", os.path.join(self.temp_dir, self.test_date)
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.rmdir(file_to_rm)
            except OSError:
                print "Error removing files in temporary test directory", self.temp_dir
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print: print "Removed", self.temp_dir
            except OSError:
                print "Error removing temporary test directory", self.temp_dir
        else:
            files_to_remove = glob(os.path.join(self.temp_dir, '*'))
            print "Would try to remove:", files_to_remove

    def test_no_superblock(self):
        out = StringIO()
        call_command('backfill_blocks', datadir=self.temp_dir, date=self.test_date, stdout=out)
        print out.readlines()
        expected = 'Processing target %s/%s in %s' % (self.test_dataroot, self.test_rockblocknum, self.test_dataroot)
        self.assertIn(expected, out.getvalue())

        blocks = Block.objects.filter(body=self.test_body)
        self.assertEqual(1, blocks.count())
