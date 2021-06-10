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

from datetime import datetime

from django.test import TestCase
from mock import patch, Mock
from astropy.wcs import WCS

from core.models import Body, Proposal, Block, SuperBlock, StaticSource
from neox.tests.mocks import mock_fetch_archive_frames, mock_archive_spectra_header,\
    mock_check_for_archive_images, mock_lco_api_call, mock_check_result_status,\
    mock_check_request_status_spectro
from core.frames import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL
logging.disable(logging.CRITICAL)


class TestBlockStatus(TestCase):

    def setUp(self):
        # Initialise with a test body, test proposal, and cadence SuperBlock
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

        analog_params = {'name': 'HD 15445',
                         'ra': 17,
                         'dec': -1,
                         'vmag': 12
                         }
        self.analog, created = StaticSource.objects.get_or_create(**analog_params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        sb_params = {  'cadence'       : 'True',
                       'body'          : self.body,
                       'proposal'      : self.neo_proposal,
                       'block_start'   : '2015-04-20 13:00:00',
                       'block_end'     : '2015-04-21 03:00:00',
                       'tracking_number' : '00042',
                       'active'        : True
                    }
        self.super_block, created = SuperBlock.objects.get_or_create(**sb_params)

        # Create test blocks
        block_params = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '01003',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        block_params2 = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '1430663',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block2 = Block.objects.create(**block_params2)

        block_params3 = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '00015',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block3 = Block.objects.create(**block_params3)

        block_params4 = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '00009',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block4 = Block.objects.create(**block_params4)

    def insert_spectro_blocks(self):

        sb_params = {'cadence': 'False',
                     'body': self.body,
                     'proposal': self.neo_proposal,
                     'block_start': '2015-04-20 05:00:00',
                     'block_end': '2015-04-21 15:00:00',
                     'tracking_number': '4242',
                     'active': True
                     }
        self.spec_super_block, created = SuperBlock.objects.get_or_create(**sb_params)

        spec_block_params1 = {'telclass': '2m0',
                              'site': 'ogg',
                              'body': self.body,
                              'superblock': self.spec_super_block,
                              'obstype': Block.OPT_SPECTRA,
                              'block_start': '2015-04-20 13:00:00',
                              'block_end': '2015-04-21 03:00:00',
                              'request_number': '1391169',
                              'num_exposures': 1,
                              'exp_length': 1800.0,
                              'active': True,
                              'num_observed': 0,
                              'reported': False
                              }
        self.spec_test_block1 = Block.objects.create(**spec_block_params1)

        spec_block_params2 = {'telclass': '2m0',
                              'site': 'ogg',
                              'body': None,
                              'calibsource': self.analog,
                              'superblock': self.spec_super_block,
                              'obstype': Block.OPT_SPECTRA_CALIB,
                              'block_start': '2015-04-20 13:00:00',
                              'block_end': '2015-04-21 03:00:00',
                              'request_number': '1391169',
                              'num_exposures': 1,
                              'exp_length': 50.0,
                              'active': True,
                              'num_observed': 0,
                              'reported': False
                              }
        self.spec_test_block2 = Block.objects.create(**spec_block_params2)

    @patch('core.frames.lco_api_call', side_effect=mock_lco_api_call)
    @patch('core.frames.check_request_status', side_effect=mock_check_result_status)
    @patch('core.frames.check_for_archive_images', side_effect=mock_check_for_archive_images)
    def test_block_status_updates_num_observed(self, check_request_status, check_for_archive_images, lco_api_call):
        expected = ('3/4', '0/4')

        blocks = Block.objects.filter(superblock=self.super_block, active=True)
        self.assertEqual(4, blocks.count())
        for block in blocks:
            block_status(block.id)

        result = self.body.get_block_info()
        self.assertEqual(expected, result)

    @patch('core.frames.lco_api_call', side_effect=mock_lco_api_call)
    @patch('core.frames.check_request_status', side_effect=mock_check_result_status)
    @patch('core.frames.check_for_archive_images', side_effect=mock_check_for_archive_images)
    def test_correct_frames_per_block(self, check_request_status, check_for_archive_images, lco_api_call):
        expected = ['1test_1003.fits', '2test_1003.fits', '3test_1003.fits']
        blocks = Block.objects.filter(active=True)
        for block in blocks:
            block_status(block.id)

        frame_names_blk1 = []
        frames = Frame.objects.filter(block=blocks[0])
        for frame in frames:
            frame_names_blk1.append(frame.filename)
        self.assertEqual(expected, frame_names_blk1)

        frame_names_blk2 = []
        frames = Frame.objects.filter(block=blocks[1])
        for frame in frames:
            frame_names_blk2.append(frame.filename)
        for element in expected:
            self.assertNotIn(element, frame_names_blk2)

    @patch('core.frames.check_request_status', mock_check_request_status_spectro)
    @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
    @patch('core.frames.lco_api_call', mock_archive_spectra_header)
    def test_check_spectro_block(self):
        self.insert_spectro_blocks()

        self.assertEqual(0, self.spec_test_block1.num_observed)
        self.assertEqual(0, self.spec_test_block2.num_observed)

        self.assertEqual(True, block_status(self.spec_test_block1.id))
        self.assertEqual(True, block_status(self.spec_test_block2.id))
        spec_block = Block.objects.get(id=self.spec_test_block1.id)
        analog_block = Block.objects.get(id=self.spec_test_block2.id)
        self.assertEqual(1, spec_block.num_observed)
        self.assertEqual(1, analog_block.num_observed)

        spec_frames = Frame.objects.filter(block=spec_block)
        analog_frames = Frame.objects.filter(block=analog_block)
        self.assertEqual(len(spec_frames), 4)
        self.assertEqual(len(analog_frames), 4)


class TestFrameParamsFromHeader(TestCase):

    def setUp(self):
        # Initialise with a test body, test proposal, and SuperBlock
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

        sb_params = {  'cadence'       : False,
                       'body'          : self.body,
                       'proposal'      : self.neo_proposal,
                       'block_start'   : '2015-04-20 13:00:00',
                       'block_end'     : '2015-04-21 03:00:00',
                       'tracking_number' : '00042',
                       'active'        : True
                    }
        self.super_block, created = SuperBlock.objects.get_or_create(**sb_params)

        # Create test blocks
        block_params = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '00103',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        self.maxDiff = None

    def test_expose_red_good_rlevel(self):
        expected_params = {  'midpoint' : datetime(2015, 4, 20, 16, 00, 14, int(0.4105*1e6)),
                             'sitecode' : 'V38',
                             'filter'   : 'w',
                             'frametype': 91,
                             'block'    : self.test_block,
                             'instrument': 'kb92',
                             'filename'  : 'elp0m411-kb92-20150420-0236-e91.fits',
                             'exptime'   : 20.003,
                             'wcs'       : WCS()
                             }

        header_params = { 'SITEID'   : 'elp',
                          'ENCID'    : 'aqwa',
                          'TELID'    : '0m4a',
                          'DATE_OBS' : '2015-04-20T16:00:04.409',
                          'EXPTIME'  : 20.0,
                          'INSTRUME' : 'kb92',
                          'FILTER'   : 'w',
                          'OBSTYPE'  : 'EXPOSE',
                          'ORIGNAME' : 'elp0m411-kb92-20150420-0236-e00',
                          'RLEVEL'   : 91,
                          'L1FWHM'   : 1.42,
                          'UTSTOP'   : '16:00:24.412'
                        }

        frame_params = frame_params_from_header(header_params, self.test_block)
        for key in expected_params:
            if key != 'wcs':
                self.assertEqual(expected_params[key], frame_params[key], "Comparison failed on " + key)

    def test_expose_red_bad_rlevel(self):
        expected_params = {  'midpoint' : datetime(2015, 4, 20, 16, 00, 14, int(0.409*1e6)),
                             'sitecode' : 'V38',
                             'filter'   : 'w',
                             'frametype': 91,
                             'block'    : self.test_block,
                             'instrument': 'kb92',
                             'filename'  : 'elp0m411-kb92-20150420-0236-e91.fits',
                             'exptime'   : 20.0,
                             'wcs'       : WCS()
                             }

        header_params = { 'SITEID'   : 'elp',
                          'ENCID'    : 'aqwa',
                          'TELID'    : '0m4a',
                          'DATE_OBS' : '2015-04-20T16:00:04.409',
                          'EXPTIME'  : 20.0,
                          'INSTRUME' : 'kb92',
                          'FILTER'   : 'w',
                          'OBSTYPE'  : 'EXPOSE',
                          'ORIGNAME' : 'elp0m411-kb92-20150420-0236-e00',
                          'RLEVEL'   : '91',
                          'L1FWHM'   : 1.42
                        }

        frame_params = frame_params_from_header(header_params, self.test_block)

        for key in expected_params:
            if key != 'wcs':
                self.assertEqual(expected_params[key], frame_params[key], "Comparison failed on " + key)
