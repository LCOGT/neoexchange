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

from datetime import datetime, timedelta
from django.core.files.base import File
from django.db import connection
from django.db.utils import IntegrityError
from django.forms.models import model_to_dict
from django.test import TestCase, override_settings

from core.models import DataProduct, Block, Body, Proposal, SuperBlock
from core.utils import save_dataproduct


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DataProductTestCase(TestCase):
    def setUp(self):
        # Initialise with a test body and two test proposals
        params = {  'provisional_name' : 'N999r0q',
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

    def test_dataproduct_block_save(self):
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test.fits'
        test_dp = DataProduct(product=file_mock, filetype=DataProduct.FITS_IMAGE, content_object=self.test_block)
        test_dp.save()
        tmppath = 'products/' + file_mock.name
        self.assertEqual(test_dp.product.name, tmppath)
        new_blocks = DataProduct.block_objects.filter(object_id=self.test_block.id)
        self.assertTrue(new_blocks.count() == 1)
        self.assertEqual(new_blocks[0], test_dp)

    def test_dataproduct_body_save(self):
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test.gif'
        test_dp = DataProduct(product=file_mock, filetype=DataProduct.GUIDER_GIF, content_object=self.body)
        test_dp.save()
        tmppath = 'products/' + file_mock.name
        self.assertEqual(test_dp.product.name, tmppath)
        new_bodies = DataProduct.body_objects.filter(object_id=self.body.id)
        self.assertTrue(new_bodies.count() == 1)
        self.assertEqual(new_bodies[0], test_dp)

    def test_dataproduct_save_util(self):
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test.png'

        # Test with a block
        with mock.patch('builtins.open', mock.mock_open()) as m:
            save_dataproduct(obj=self.test_block, filepath=file_mock, filetype=DataProduct.PNG_ASTRO, filename=file_mock.name)

        new_blocks = DataProduct.block_objects.filter(object_id=self.test_block.id)
        self.assertTrue(new_blocks.count() == 1)
        self.assertEqual(new_blocks[0].content_object, self.test_block)

        # Test with a body
        with mock.patch('builtins.open', mock.mock_open()) as m:
            save_dataproduct(obj=self.body, filepath=file_mock, filetype=DataProduct.PNG_ASTRO, filename=file_mock.name)

        new_body = DataProduct.body_objects.filter(object_id=self.body.id)
        self.assertTrue(new_body.count() == 1)
        self.assertEqual(new_body[0].content_object, self.body)
