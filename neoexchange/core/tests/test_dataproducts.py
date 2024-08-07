"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
import builtins
import mock
import tempfile
import os
import shutil

from datetime import datetime, timedelta
from django.core.files.base import File
from django.db.utils import IntegrityError
from django.forms.models import model_to_dict
from django.test import TestCase, override_settings
from django.conf import settings

from core.models import DataProduct, Block, Body, Proposal, SuperBlock, Frame
from core.utils import save_dataproduct, save_to_default
from photometrics.gf_movie import make_gif


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
@override_settings(DATA_ROOT=tempfile.mkdtemp())
class DataProductTestCase(TestCase):
    def setUp(self):
        # Initialise with a test body and two test proposals
        params = {  'provisional_name' : 'N999r0q',
                    'name'          : '2255',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body, created = Body.objects.get_or_create(**params)

        params2 = { 'provisional_name': '763',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body2, created = Body.objects.get_or_create(**params2)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True,
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : None,
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        frame_params = {'sitecode': 'K92',
                        'instrument': 'kb76',
                        'filter': 'w',
                        'filename': 'banzai_test_frame.fits',
                        'exptime': 225.0,
                        'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                        'block': self.test_block,
                        'zeropoint': -99,
                        'zeropoint_err': -99,
                        'fwhm': 2.390,
                        'frametype': 0,
                        'rms_of_fit': 0.3,
                        'nstars_in_fit': -4,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

    def test_dataproduct_block_save_new_file(self):
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test_overwrite.fits'
        test_dp = DataProduct.objects.create(product=file_mock, filetype=DataProduct.FITS_IMAGE, content_object=self.test_block)
        tmppath = 'products/' + file_mock.name
        self.assertEqual(test_dp.product.name, tmppath)
        # file_mock2 = mock.MagicMock(spec=File)
        file_mock.name = 'test_overwrite.fits'
        test_dp.product = file_mock
        test_dp.save()
        self.assertEqual(test_dp.product.name, tmppath)
        self.assertTrue(test_dp.product.storage.exists(test_dp.product.name))

    def test_dataproduct_block_save(self):
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test.fits'
        test_dp = DataProduct(product=file_mock, filetype=DataProduct.FITS_IMAGE, content_object=self.test_block)
        test_dp.save()
        tmppath = 'products/' + file_mock.name
        self.assertEqual(test_dp.product.name, tmppath)
        new_blocks = DataProduct.content.block().filter(object_id=self.test_block.id)
        self.assertTrue(new_blocks.count() == 1)
        self.assertEqual(new_blocks[0], test_dp)
        self.assertTrue(new_blocks[0].product.storage.exists(test_dp.product.name))

    def test_dataproduct_body_save(self):
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test.gif'
        test_dp = DataProduct(product=file_mock, filetype=DataProduct.GUIDER_GIF, content_object=self.body)
        test_dp.save()
        tmppath = 'products/' + file_mock.name
        self.assertEqual(test_dp.product.name, tmppath)
        new_bodies = DataProduct.content.body().filter(object_id=self.body.id)
        self.assertTrue(new_bodies.count() == 1)
        self.assertEqual(new_bodies[0], test_dp)
        self.assertTrue(new_bodies[0].product.storage.exists(test_dp.product.name))

    def test_dataproduct_save_util(self):
        # file_mock = mock.MagicMock(spec=File)
        # out_path = settings.DATA_ROOT
        # all_frames = {}
        # dl_frames = download_files(all_frames, out_path)
        xml = os.path.abspath(os.path.join('photometrics', 'tests', 'example_scamp.xml'))
        file_name = 'test.xml'
        save_to_default(xml, os.path.dirname(xml))

        # Test with a block
        # with mock.patch('builtins.open', mock.mock_open()) as m:
        save_dataproduct(obj=self.test_block, filepath=os.path.basename(xml), filetype=DataProduct.PDS_XML, filename=file_name)

        new_blocks = DataProduct.content.block().filter(object_id=self.test_block.id)
        self.assertTrue(new_blocks.count() == 1)
        self.assertEqual(new_blocks[0].content_object, self.test_block)
        self.assertTrue(new_blocks[0].product.storage.exists(new_blocks[0].product.name))

        # Test with a body
        # with mock.patch('builtins.open', mock.mock_open()) as m:
        save_dataproduct(obj=self.body, filepath=os.path.basename(xml), filetype=DataProduct.PDS_XML, filename=file_name)

        new_body = DataProduct.content.body().filter(object_id=self.body.id)
        self.assertTrue(new_body.count() == 1)
        self.assertEqual(new_body[0].content_object, self.body)
        self.assertTrue(new_body[0].product.storage.exists(new_body[0].product.name))

    def test_dataproduct_save_util_from_dataroot(self):
        out_path = settings.DATA_ROOT
        xml_test = os.path.abspath(os.path.join('photometrics', 'tests', 'example_scamp.xml'))
        xml = os.path.join(out_path, os.path.basename(xml_test))
        file_name = 'test.xml'
        shutil.copyfile(xml_test, xml)

        # Test with a block
        # with mock.patch('builtins.open', mock.mock_open()) as m:
        save_dataproduct(obj=self.test_block, filepath=xml, filetype=DataProduct.PDS_XML, filename=file_name)

        new_blocks = DataProduct.content.block().filter(object_id=self.test_block.id)
        self.assertTrue(new_blocks.count() == 1)
        self.assertEqual(new_blocks[0].content_object, self.test_block)
        self.assertTrue(new_blocks[0].product.storage.exists(new_blocks[0].product.name))

    def test_dataproduct_save_ALCDEF(self):
        file_name = 'test_ALCDEF.txt'
        file_content = "some text here"

        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)

        dp = DataProduct.objects.get(product__contains=file_name)
        self.assertEqual(dp.content_object, self.test_sblock)
        self.assertEqual(dp.product.name, os.path.join('products', file_name))
        self.assertTrue(dp.product.storage.exists(dp.product.name))
        test_file = dp.product.open(mode='r')
        lines = test_file.readlines()
        dp.product.close()
        self.assertEqual(lines[0], file_content)
        first_time_stamp = dp.created

        # Overwrite file
        new_content = "some other text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=new_content)
        dp1 = DataProduct.objects.get(product__contains=file_name)
        self.assertEqual(dp1.content_object, self.test_sblock)
        self.assertEqual(dp1.product.name, os.path.join('products', file_name))
        self.assertTrue(dp1.product.storage.exists(dp1.product.name))
        test_file = dp1.product.open(mode='r')
        lines = test_file.readlines()
        dp1.product.close()
        self.assertEqual(lines[0], new_content)
        self.assertNotEqual(dp1.created, first_time_stamp)

    def test_dataproduct_retrieve_ALCDEF(self):
        # Create gif
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test.gif'
        gif_dp = DataProduct.objects.create(product=file_mock, filetype=DataProduct.FRAME_GIF,
                                            content_object=self.test_block)

        # Add Superblock linked ALCDEF
        file_name = 'test_SB_ALCDEF.txt'
        file_content = "some text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.ALCDEF_TXT)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.ALCDEF_TXT)
        dp_bod = DataProduct.content.body().filter(object_id=self.body.id, filetype=DataProduct.ALCDEF_TXT)
        dp_blk = DataProduct.content.block().filter(object_id=self.test_block.id, filetype=DataProduct.ALCDEF_TXT)
        self.assertEqual(len(dp_qset), 1)
        self.assertEqual(len(dp_sb), 1)
        self.assertEqual(len(dp_bod), 0)
        self.assertEqual(len(dp_blk), 0)

        # Add Block linked ALCDEF
        file_name = 'test_Bloc_ALCDEF.txt'
        file_content = "some other text here"
        save_dataproduct(obj=self.test_block, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.ALCDEF_TXT)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.ALCDEF_TXT)
        dp_bod = DataProduct.content.body().filter(object_id=self.body.id, filetype=DataProduct.ALCDEF_TXT)
        dp_blk = DataProduct.content.block().filter(object_id=self.test_block.id, filetype=DataProduct.ALCDEF_TXT)
        self.assertEqual(len(dp_qset), 2)
        self.assertEqual(len(dp_sb), 1)
        self.assertEqual(len(dp_bod), 0)
        self.assertEqual(len(dp_blk), 1)

        # Add Body linked ALCDEF
        file_name = 'test_Bod_ALCDEF.txt'
        file_content = "even other text here"
        save_dataproduct(obj=self.test_sblock.body, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.ALCDEF_TXT)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.ALCDEF_TXT)
        dp_bod = DataProduct.content.body().filter(object_id=self.body.id, filetype=DataProduct.ALCDEF_TXT)
        dp_blk = DataProduct.content.block().filter(object_id=self.test_block.id, filetype=DataProduct.ALCDEF_TXT)
        self.assertEqual(len(dp_qset), 3)
        self.assertEqual(len(dp_sb), 1)
        self.assertEqual(len(dp_bod), 1)
        self.assertEqual(len(dp_blk), 1)

        # Add unrelated body linked ALCDEF
        file_name = 'test_newBod_ALCDEF.txt'
        file_content = "woogaoooooowoo"
        save_dataproduct(obj=self.body2, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.ALCDEF_TXT)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.ALCDEF_TXT)
        dp_bod = DataProduct.content.body().filter(object_id=self.body.id, filetype=DataProduct.ALCDEF_TXT)
        dp_blk = DataProduct.content.block().filter(object_id=self.test_block.id, filetype=DataProduct.ALCDEF_TXT)
        self.assertEqual(len(dp_qset), 3)
        self.assertEqual(len(dp_sb), 1)
        self.assertEqual(len(dp_bod), 1)
        self.assertEqual(len(dp_blk), 1)

    def test_dataproduct_save_gif(self):
        # Create gif
        fits = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        frames = [fits, fits, fits, fits, fits]
        movie_file = make_gif(frames, sort=False, init_fr=100, out_path=settings.MEDIA_ROOT, center=3, progress=False)
        save_dataproduct(obj=self.test_block, filepath=movie_file, filetype=DataProduct.FRAME_GIF)
        dp = DataProduct.objects.get(product__contains=os.path.basename(movie_file))
        self.assertTrue(dp.product.storage.exists(dp.product.name))

    def test_dataproduct_save_robust(self):
        # Add Superblock linked CSV
        file_name = 'test_SB_CSV.txt'
        file_content = "some text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.CSV, filename=file_name, content=file_content)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.CSV)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.CSV)
        dp_bod = DataProduct.content.body().filter(object_id=self.body.id, filetype=DataProduct.CSV)
        dp_blk = DataProduct.content.block().filter(object_id=self.test_block.id, filetype=DataProduct.CSV)
        self.assertEqual(len(dp_qset), 1)
        self.assertEqual(len(dp_sb), 1)
        self.assertEqual(len(dp_bod), 0)
        self.assertEqual(len(dp_blk), 0)
        test_file = dp_sb[0].product.file
        lines = test_file.readlines()
        self.assertEqual(lines[0], file_content.encode('utf-8'))
        timestamp = dp_sb[0].created

        # overwrite with normal dataproduct
        file_content2 = "some other text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.CSV, filename=file_name, content=file_content2)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.CSV)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.CSV)
        self.assertEqual(len(dp_qset), 1)
        self.assertEqual(len(dp_sb), 1)
        test_file = dp_sb[0].product.file
        lines = test_file.readlines()
        self.assertEqual(lines[0], file_content2.encode('utf-8'))
        timestamp2 = dp_sb[0].created
        self.assertNotEqual(timestamp2, timestamp)

        # overwrite with robust dataproduct
        file_content3 = "even other text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.CSV, filename=file_name, content=file_content3, force=True)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.CSV)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.CSV)
        self.assertEqual(len(dp_qset), 1)
        self.assertEqual(len(dp_sb), 1)
        test_file = dp_sb[0].product.file
        lines = test_file.readlines()
        self.assertEqual(lines[0], file_content3.encode('utf-8'))
        self.assertFalse(dp_sb[0].update)
        timestamp3 = dp_sb[0].created
        self.assertNotEqual(timestamp2, timestamp3)

        # Fail to overwrite robust dataproduct
        file_content4 = "woogaoooooowoo"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.CSV, filename=file_name, content=file_content4)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.CSV)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.CSV)
        self.assertEqual(len(dp_qset), 1)
        self.assertEqual(len(dp_sb), 1)
        test_file = dp_sb[0].product.file
        lines = test_file.readlines()
        self.assertEqual(lines[0], file_content3.encode('utf-8'))
        self.assertFalse(dp_sb[0].update)
        timestamp4 = dp_sb[0].created
        self.assertEqual(timestamp4, timestamp3)

        # succeed to overwrite robust dataproduct
        file_content5 = "final text"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.CSV, filename=file_name, content=file_content5, force=True)

        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.CSV)
        dp_sb = DataProduct.content.sblock().filter(object_id=self.test_sblock.id, filetype=DataProduct.CSV)
        self.assertEqual(len(dp_qset), 1)
        self.assertEqual(len(dp_sb), 1)
        test_file = dp_sb[0].product.file
        lines = test_file.readlines()
        self.assertEqual(lines[0], file_content5.encode('utf-8'))
        self.assertFalse(dp_sb[0].update)
        timestamp5 = dp_sb[0].created
        self.assertNotEqual(timestamp4, timestamp5)

    def test_dataproduct_delete(self):
        # Build file/DP
        file_name = 'test_SB_png.txt'
        file_content = "some text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.PNG_ASTRO, filename=file_name, content=file_content)
        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.PNG_ASTRO)
        pathname = os.path.join(settings.MEDIA_ROOT, dp_qset[0].product.name)
        self.assertTrue(os.path.isfile(pathname))
        # Delete DP
        dp_qset.delete()
        # file is gone
        self.assertFalse(os.path.isfile(pathname))
        new_db_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.PNG_ASTRO)
        self.assertFalse(new_db_qset.exists())

        # Make new DP
        file_content2 = "some new text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.PNG_ASTRO, filename=file_name, content=file_content2)
        dp_qset = DataProduct.content.fullbody(bodyid=self.body.id).filter(filetype=DataProduct.PNG_ASTRO)
        # Overwrites old file
        self.assertIn(file_name, dp_qset[0].product.name)

    def test_reverse_lookup(self):
        file_name = 'test_ALCDEF.txt'
        file_content = "some text here"

        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)

        sb = SuperBlock.objects.filter(dataproduct__filetype=DataProduct.ALCDEF_TXT)
        raw_blk = Block.objects.filter(dataproduct__filetype=DataProduct.ALCDEF_TXT)
        sb_blk = Block.objects.filter(superblock__dataproduct__filetype=DataProduct.ALCDEF_TXT)

        self.assertEqual(len(sb), 1)
        self.assertEqual(len(raw_blk), 0)
        self.assertEqual(len(sb_blk), 1)
