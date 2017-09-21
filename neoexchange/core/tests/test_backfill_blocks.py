import os
import tempfile
from glob import glob

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from astropy.io import fits
import numpy as np

from core.models import Block, Frame, Body, Proposal

class BackFillBlocksTest(TestCase):

    def create_fake_fits_file(self, filepath):

        header_items = {'tracknum' : '0000489463',
                        'object'   : self.test_target,
                        'blksdate' : '2017-09-20T16:44:56',
                        'blkedate' : '2017-09-20T17:02:20',
                        'exptime'  :  1.0000000,
                        'groupid'  : self.test_target + '-' + self.test_date,
                        'molfrnum' : np.random.randint(1,24),
                        'frmtotal' : 24,
                        'propid'  : 'LCOTest',
                        'siteid'   : 'coj     ',
                        'telid'    : '1m0a    '
                        }
        n = np.arange(1.0, dtype=np.float32)
        priheader = fits.Header()
        for key in header_items:
            priheader[key] = header_items[key]
        hdu = fits.PrimaryHDU(n, header=priheader)
        hdu.name = 'SCI'
        hdu.writeto(filepath)

    def setUp(self):

        self.temp_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')
        self.test_date = '20990420'
        self.test_dataroot = os.path.join(self.temp_dir, self.test_date)
        self.test_target = 'P10w5z5'
        self.test_rockblocknum = self.test_target + '_1234567'
        self.test_rockdir = os.path.join(self.test_dataroot, self.test_rockblocknum)
        os.makedirs(self.test_rockdir)
        self.debug_print = False

        frame1 = os.path.join(self.test_rockdir, 'frame1-e91.fits')
        self.create_fake_fits_file(frame1)

        frame2 = os.path.join(self.test_rockdir, 'frame2-e91.fits')
        self.create_fake_fits_file(frame2)

        # Insert test body
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

        proposal_params = { 'code': 'LCOTest',
                            'title': 'test',
                            'pi':'bart.simpson@lcogt.net',
                            'tag': 'LCOGT',
                            'active': True
                          }
        self.test_proposal, created = Proposal.objects.get_or_create(**proposal_params)

    def tearDown(self):
        remove = True
        if remove:
            try:
                path = os.path.join(self.temp_dir, self.test_date, self.test_rockblocknum)
                files_to_remove = glob(os.path.join(path, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print "Error removing files in temporary test directory", path
            try:
                path = os.path.join(self.temp_dir, self.test_date)
                files_to_remove = glob(os.path.join(path, '*'))
                for file_to_rm in files_to_remove:
                    os.rmdir(file_to_rm)
            except OSError:
                print "Error removing files in temporary test directory", path
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

        blocks = Block.objects.filter(body=self.test_body)
        self.assertEqual(0, blocks.count())

        out = StringIO()
        call_command('backfill_blocks', datadir=self.temp_dir, date=self.test_date, stdout=out)
        print
        print out.getvalue()
        expected = 'Processing target %s/%s in %s' % (self.test_dataroot, self.test_rockblocknum, self.test_dataroot)
        self.assertIn(expected, out.getvalue())

        expected = 'Found 2 FITS files in %s' % (self.test_dataroot)
        self.assertIn(expected, out.getvalue())

        blocks = Block.objects.filter(body=self.test_body)
        self.assertEqual(1, blocks.count())

        print blocks, blocks[0].id
        frames = Frame.objects.filter(block=blocks[0])
        print frames
        self.assertEqual(2, frames.count())
