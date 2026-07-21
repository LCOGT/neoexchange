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

class TestSplitLightCurveBlocks(TestCase):
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

        empty_block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'request_number' : '00001',
                         'num_exposures' : 0,
                         'exp_length' : 42.0,
                         'num_observed' : 1,
                         'active'   : True
                       }

        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2022-10-20 13:00:00',
                         'block_end'   : '2022-10-21 03:00:00',
                         'request_number' : '00002',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'num_observed' : 1,
                         'active'   : True
                       }
        self.empty_test_block = Block.objects.create(**empty_block_params)
        self.test_block = Block.objects.create(**block_params)

        frame_params = { 'sitecode' : 'K92',
                          'filter' : 'w',
                          'exptime' : 30,
                          'block' : self.test_block,
                          'midpoint' : datetime(2022,10,20,15,0,0),
                          'frametype' : Frame.NEOX_RED_FRAMETYPE
                        }
        self.test_frames = []

        for frame_num in range(block_params['num_exposures']):
            frame_params['midpoint'] += timedelta(minutes = frame_num * 10)
            test_frame = Frame.objects.create(**frame_params)
            self.test_frames.append(test_frame)

    def test_empty_block(self):
        expected_split_block = []
        frames, banzai, neox = find_frames(self.empty_test_block) 
        split_block = split_light_curve_blocks(frames)
        self.assertEquals(expected_split_block, split_block)

    def test_exptime(self):
        expected_split_block_len = 2
        frames, banzai, neox = find_frames(self.test_block)
        split_block = split_light_curve_blocks(frames, exptime=100)
        self.assertEquals(expected_split_block_len, len(split_block))

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
                         'request_number' : '00002',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'num_observed' : 1,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        frame_params = { 'sitecode' : 'K92',
                          'filter' : 'w',
                          'exptime' : 30,
                          'block' : self.test_block,
                          'midpoint' : datetime(2022,10,20,15,0,0),
                          'frametype' : Frame.NEOX_RED_FRAMETYPE
                        }
        self.test_frames = []

        for frame_num in range(block_params['num_exposures']):
            frame_params['midpoint'] += timedelta(minutes = frame_num * 10)
            test_frame = Frame.objects.create(**frame_params)
            self.test_frames.append(test_frame)

    def test_expected(self):
        self.assertEqual(1, Block.objects.all().count())
        self.assertEqual(5, Frame.objects.all().count())

    def test_didymos_block(self):
        expected_num_frames = 5

        frames, num_banzai, num_neox = find_frames(self.test_block)

        self.assertEqual(expected_num_frames, frames.count())
        self.assertEqual(self.test_frames[0].midpoint, frames[0].midpoint)
        self.assertEqual(self.test_frames[-1].midpoint, frames[frames.count()-1].midpoint)

    def test_counts_behave_as_ints(self):
        # The returned counts must remain usable as plain ints for existing callers
        frames, num_banzai, num_neox = find_frames(self.test_block)

        self.assertEqual(5, num_neox)
        self.assertEqual(0, num_banzai)
        self.assertIsInstance(num_neox, int)
        self.assertEqual(6, num_neox + 1)
        self.assertEqual('    5', f"{num_neox:>5d}")

    def test_single_frametype_breakdown(self):
        frames, num_banzai, num_neox = find_frames(self.test_block)

        self.assertEqual(5, num_neox[Frame.NEOX_RED_FRAMETYPE])

    def test_multiple_frametype_breakdown(self):
        # Add 2 BANZAI (e91) and 3 subtracted (e93) frames to the 5 existing e92s
        frame_params = { 'sitecode' : 'K92',
                         'filter' : 'w',
                         'exptime' : 30,
                         'block' : self.test_block,
                         'midpoint' : datetime(2022, 10, 20, 16, 0, 0),
                       }
        for frame_num in range(2):
            Frame.objects.create(frametype=Frame.BANZAI_RED_FRAMETYPE, **frame_params)
        for frame_num in range(3):
            Frame.objects.create(frametype=Frame.NEOX_SUB_FRAMETYPE, **frame_params)

        frames, num_banzai, num_neox = find_frames(self.test_block,
                                                   frametype=[Frame.NEOX_RED_FRAMETYPE,
                                                              Frame.NEOX_SUB_FRAMETYPE])

        self.assertEqual(2, num_banzai)
        # Total keeps its existing meaning: all frames of the requested type(s)
        self.assertEqual(8, num_neox)
        self.assertEqual(5, num_neox[Frame.NEOX_RED_FRAMETYPE])
        self.assertEqual(3, num_neox[Frame.NEOX_SUB_FRAMETYPE])
        self.assertEqual(0, num_neox.get(Frame.BANZAI_RED_FRAMETYPE, 0))

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

    def test_jd_value_start_time(self):
        expected_RA = []
        expected_DEC = []

        t = Time(datetime(2022, 11, 4, 9, 33, 0))

        result_RA, result_DEC = ephem_interpolate(t.jd, self.test_ephem)

        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)

    def test_jd_value_end_time(self):
        expected_RA = []
        expected_DEC = []

        t = Time(datetime(2022, 11, 4, 9, 54, 0))

        result_RA, result_DEC = ephem_interpolate(t.jd, self.test_ephem)

        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)

    def test_jd_datetime_start_time(self):
        expected_RA = []
        expected_DEC = []

        t = datetime(2022, 11, 4, 9, 33, 0)

        result_RA, result_DEC = ephem_interpolate(t, self.test_ephem)

        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)

    def test_jd_datetime_end_time(self):
        expected_RA = []
        expected_DEC = []

        t = datetime(2022, 11, 4, 9, 54, 0)

        result_RA, result_DEC = ephem_interpolate(t, self.test_ephem)

        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)

    def test_jd_datetimes_reversed(self):
        expected_RA = []
        expected_DEC = []

        t = datetime(2022, 11, 4, 9, 35, 30)
        t_2 = datetime(2022, 11, 4, 9, 32, 0)

        result_RA, result_DEC = ephem_interpolate([t, t_2], self.test_ephem)

        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)

    def test_jd_values_reversed(self):
        expected_RA = []
        expected_DEC = []

        t = Time(datetime(2022, 11, 4, 9, 35, 30))
        t_2 = Time(datetime(2022, 11, 4, 9, 54, 0))

        result_RA, result_DEC = ephem_interpolate([t_2.jd, t.jd], self.test_ephem)

        assert_allclose(expected_RA, result_RA, rtol=1e-8)
        assert_allclose(expected_DEC, result_DEC, rtol=1e-8)


class TestFrameQualityStats(SimpleTestCase):

    def make_frame(self, obs_filter='rp', rms=0.1, num_stars=40, zp=23.5, fwhm=1.8):
        '''Build a minimal stand-in for a Frame; these routines only read attributes'''
        frame = Frame(filter=obs_filter, rms_of_fit=rms, nstars_in_fit=num_stars,
                      zeropoint=zp, fwhm=fwhm, filename='test.fits')
        return frame

    def test_good_fit(self):
        self.assertTrue(good_astrometric_fit(self.make_frame()))

    def test_nan_rms_fails(self):
        self.assertFalse(good_astrometric_fit(self.make_frame(rms=float('nan'))))

    def test_null_rms_fails(self):
        self.assertFalse(good_astrometric_fit(self.make_frame(rms=None)))

    def test_large_rms_fails(self):
        self.assertFalse(good_astrometric_fit(self.make_frame(rms=5.0)))

    def test_too_few_stars_fails(self):
        self.assertFalse(good_astrometric_fit(self.make_frame(num_stars=2)))

    def test_good_zeropoint(self):
        self.assertTrue(good_zeropoint(self.make_frame()))

    def test_sentinel_zeropoint_fails(self):
        self.assertFalse(good_zeropoint(self.make_frame(zp=-99.0)))

    def test_nan_zeropoint_fails(self):
        self.assertFalse(good_zeropoint(self.make_frame(zp=float('nan'))))

    def test_null_zeropoint_fails(self):
        self.assertFalse(good_zeropoint(self.make_frame(zp=None)))

    def test_stats_exclude_bad_values(self):
        # 3 rp frames, one of which failed both the astrometric fit and the ZP
        frames = [self.make_frame('rp', zp=23.0, fwhm=1.5),
                  self.make_frame('rp', zp=24.0, fwhm=2.5),
                  self.make_frame('rp', rms=float('nan'), zp=-99.0, fwhm=float('nan')),
                  self.make_frame('gp', zp=22.0, fwhm=2.0)]

        stats = frame_quality_stats(frames)

        # Filters are reported in the conventional order, not the order found
        self.assertEqual(['gp', 'rp'], list(stats.keys()))
        rp_stats = stats['rp']
        self.assertEqual(3, rp_stats['num_frames'])
        self.assertEqual(2, rp_stats['num_good_astrometry'])
        self.assertEqual(2, rp_stats['num_good_zeropoint'])
        # The NaN FWHM and the -99 zeropoint must not skew the means
        self.assertEqual(2, rp_stats['num_fwhm'])
        self.assertAlmostEqual(2.0, rp_stats['fwhm_mean'], 6)
        self.assertEqual(2, rp_stats['num_zp'])
        self.assertAlmostEqual(23.5, rp_stats['zp_mean'], 6)

    def test_stats_no_valid_values(self):
        frames = [self.make_frame('rp', zp=None, fwhm=None)]

        stats = frame_quality_stats(frames)

        self.assertEqual(0, stats['rp']['num_fwhm'])
        self.assertNotEqual(stats['rp']['fwhm_mean'], stats['rp']['fwhm_mean'])  # NaN
