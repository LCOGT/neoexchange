import os
from datetime import datetime, timedelta

from django.test import TestCase, SimpleTestCase, override_settings
from django.forms.models import model_to_dict
from numpy.testing import assert_allclose
from core.models import Proposal, SuperBlock, Block, Body, Frame
from astropy.table import Table
from astropy.time import Time

from core.blocksfind import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)

class TestFindDidymosBlocks(TestCase):
    def setUp(self):

        didymos_params = { 'name' : '65803',
                         }
        self.test_body = Body.objects.create(**didymos_params)

        WV2997A_params = { 'name' : 'WV2997A',
                         }
        self.test_body2 = Body.objects.create(**WV2997A_params)

        neo_proposal_params = { 'code'  : 'LCO2022A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)
        
        eng_proposal_params = { 'code'  : 'LCOEngineering',
                                'title' : 'LCOGT Engineering'
                              }
        self.eng_proposal, created = Proposal.objects.get_or_create(**eng_proposal_params)
        
        # Create test blocks
        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'tracking_number' : '00001',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'request_number' : '00001',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'num_observed' : 1,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2022-12-11 13:00:00',
                         'block_end'   : '2022-12-12 03:00:00',
                         'tracking_number' : '522289',
                         'active'   : True
                       }
        self.test_sblock_0m4 = SuperBlock.objects.create(**sblock_params)
        
        block_params = { 'telclass' : '0m4',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock_0m4,
                         'block_start' : '2022-12-11 13:00:00',
                         'block_end'   : '2022-12-12 03:00:00',
                         'request_number' : '522289',
                         'num_exposures' : 5,
                         'exp_length' : 145.0,
                         'num_observed' : 2,
                         'active'   : True
                       }
        self.test_block_0m4 = Block.objects.create(**block_params)

        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP_spectra',
                         'block_start' : '2022-12-11 13:00:00',
                         'block_end'   : '2022-12-12 03:00:00',
                         'tracking_number' : '1509481',
                         'active'   : True
                       }
        self.test_sblock_spec = SuperBlock.objects.create(**sblock_params)
        
        block_params = { 'obstype' : Block.OPT_SPECTRA,
                         'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock_spec,
                         'block_start' : '2022-12-11 13:00:00',
                         'block_end'   : '2022-12-12 03:00:00',
                         'request_number' : '1509481',
                         'num_exposures' : 1,
                         'exp_length' : 1800.0,
                         'num_observed' : 1,
                         'active'   : True
                       }
        self.test_spec_block = Block.objects.create(**block_params)
        
        # create SuperBlock and Block that point to Didymos, but are from engineering proposal
        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.eng_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'tracking_number' : '00013',
                         'active'   : True
                       }
        self.test_sblock_eng = SuperBlock.objects.create(**sblock_params)
        
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock_eng,
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'request_number' : '00113',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'num_observed' : 1,
                         'active'   : True
                       }
        self.test_block_eng = Block.objects.create(**block_params)
        
        # create SuperBlock and Block that point to other asteroid
        sblock_params = {
                         'body'     : self.test_body2,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'tracking_number' : '00285',
                         'active'   : True
                       }
        self.test_sblock_ast2 = SuperBlock.objects.create(**sblock_params)
        
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body2,
                         'superblock' : self.test_sblock,
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'request_number' : '00726',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'num_observed' : 1,
                         'active'   : True
                       }
        self.test_block_ast2 = Block.objects.create(**block_params)
        
    def test_didymos(self):
        expected_num_blocks = 2

        blocks = find_didymos_blocks()
        
        self.assertEqual(expected_num_blocks, blocks.count())
        
        for block in blocks:
            self.assertTrue(hasattr(block, 'request_number'))
            self.assertEqual(block.body, self.test_body)
            self.assertNotEqual(block.superblock.proposal, self.eng_proposal)
            
class TestFindFrames(TestCase):
    def setUp(self):
        didymos_params = { 'name' : '65803'
                         }
        self.test_body = Body.objects.create(**didymos_params)
        
        neo_proposal_params = { 'code'  : 'LCO2022A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)
        
        # Create test blocks
        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'tracking_number' : '00001',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'request_number' : '00001',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'num_observed' : 1,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        frame_params = { 'sitecode' : 'K92',
                          'filter' : 'w',
                          'block' : self.test_block,
                          'midpoint' : datetime(2022,10,20,15,0,0),
                          'frametype' : Frame.BANZAI_RED_FRAMETYPE
                        }
        self.test_frames = []
        
        for frame_num in range(block_params['num_exposures']):
            frame_params['midpoint'] += timedelta(minutes = frame_num * 10)
            test_frame = Frame.objects.create(**frame_params)
            self.test_frames.append(test_frame)
        
        #create ldac catalog versions of the same frame
        frame_params['midpoint'] =  datetime(2022,10,20,15,0,0)
        frame_params['frametype'] = Frame.BANZAI_LDAC_CATALOG   
        for frame_num in range(block_params['num_exposures']):
            frame_params['midpoint'] += timedelta(minutes = frame_num * 10)
            test_frame = Frame.objects.create(**frame_params)
        
    def test_expected(self):
        self.assertEqual(1, Block.objects.all().count())
        self.assertEqual(10, Frame.objects.all().count())
        
    def test_didymos_block(self):
        expected_num_frames = 5

        frames = find_frames(self.test_block)
        
        self.assertEqual(expected_num_frames, frames.count())
        self.assertEqual(self.test_frames[0].midpoint, frames[0].midpoint)
        self.assertEqual(self.test_frames[-1].midpoint, frames[frames.count()-1].midpoint)


class TestEphemInterpolate(SimpleTestCase):
    def setUp(self):
        self.test_ephem = Table.read(os.path.join('core', 'tests', 'test_ephem.fits'))
        
    def test_jd_value(self):
        expected_RA = 118.80145
        expected_DEC = 7.948245
        
        t = Time(datetime(2022, 11, 4, 9, 35, 30))
        
        result_RA, result_DEC = ephem_interpolate([t.jd,], self.test_ephem)
        
        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)
        
    def test_jd_values(self):
        expected_RA = [118.80145, 118.80154]
        expected_DEC = [7.948245, 7.9483575]
        
        t = Time(datetime(2022, 11, 4, 9, 35, 30))
        t_2 = Time(datetime(2022, 11, 4, 9, 35, 45))

        result_RA, result_DEC = ephem_interpolate([t.jd, t_2.jd], self.test_ephem)
        
        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)
        
    def test_jd_value_single(self):
        expected_RA = 118.80145
        expected_DEC = 7.948245
        
        t = Time(datetime(2022, 11, 4, 9, 35, 30))
        
        result_RA, result_DEC = ephem_interpolate(t.jd, self.test_ephem)
        
        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)
        
    def test_jd_datetime(self):
        expected_RA = 118.80145
        expected_DEC = 7.948245
        
        t = datetime(2022, 11, 4, 9, 35, 30)

        result_RA, result_DEC = ephem_interpolate([t,], self.test_ephem)
        
        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)
    
    def test_jd_datetimes(self):
        expected_RA = [118.80145, 118.80154]
        expected_DEC = [7.948245, 7.9483575]
        
        t = datetime(2022, 11, 4, 9, 35, 30)
        t_2 = datetime(2022, 11, 4, 9, 35, 45)

        result_RA, result_DEC = ephem_interpolate([t, t_2], self.test_ephem)
        
        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)
        
    def test_jd_datetime_single(self):
        expected_RA = 118.80145
        expected_DEC = 7.948245
        
        t = datetime(2022, 11, 4, 9, 35, 30)

        result_RA, result_DEC = ephem_interpolate(t, self.test_ephem)
        
        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)
        
        
