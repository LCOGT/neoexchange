'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2015-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime
from django.test import TestCase
from django.forms.models import model_to_dict
from django.db.utils import IntegrityError
from numpy import array, arange
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from unittest import skipIf
from mock import patch
from neox.tests.mocks import MockDateTime

#Import module to test
from core.models import Body, Proposal, Block, Frame, SourceMeasurement, \
    CatalogSources, Candidate
from astrometrics.ephem_subs import compute_ephem


class TestBody(TestCase):

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

        params['provisional_name'] = 'V92818q'
        self.body2, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'I22871'
        self.body3, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Ntheiqo'
        self.body4, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Q488391r'
        self.body5, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : None,
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        block_params2 = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body3,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block2 = Block.objects.create(**block_params2)

        block_params3 = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body4,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00044',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 2,
                         'reported' : False
                       }
        self.test_block3 = Block.objects.create(**block_params3)

        block_params5a = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body5,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00045',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block5a = Block.objects.create(**block_params5a)

        block_params5b = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body5,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00045',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 2,
                         'reported' : False
                       }
        self.test_block5b = Block.objects.create(**block_params5b)

    def test_get_block_info_NoBlock(self):
        expected = ('Not yet', 'Not yet')

        result = self.body2.get_block_info()

        self.assertEqual(expected, result)

    def test_get_block_info_OneBlock_NoObs_NotReported(self):
        expected = ('0/1', '0/1')

        result = self.body.get_block_info()

        self.assertEqual(expected, result)

    def test_get_block_info_OneBlock_Reported(self):
        expected = ('1/1', '1/1')

        result = self.body3.get_block_info()

        self.assertEqual(expected, result)

    def test_get_block_info_OneBlock_MultiObs_NotReported(self):
        expected = ('1/1', '0/1')

        result = self.body4.get_block_info()

        self.assertEqual(expected, result)

    def test_get_block_info_TwoBlocks(self):
        expected = ('2/2', '1/2')

        result = self.body5.get_block_info()

        self.assertEqual(expected, result)

@patch('core.models.datetime', MockDateTime)
class TestComputeFOM(TestCase):

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
                    'not_seen'      : 2.3942,
                    'arc_length'    : 0.4859,
                    'score'         : 83,
                    'abs_mag'       : 19.8
                    }
        self.body, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : '29182875',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    'not_seen'      : 2.3942,
                    'arc_length'    : 0.4859,
                    'score'         : 83,
                    'abs_mag'       : 19.8
                    }
        self.body2, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : 'C94028',
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
                    'not_seen'      : None,
                    'arc_length'    : None,
                    'score'         : 83,
                    'abs_mag'       : 19.8
                    }
        self.body3, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : 't392019fci',
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
                    'not_seen'      : 2.3942,
                    'arc_length'    : 0.4859,
                    'score'         : None,
                    'abs_mag'       : 19.8
                    }
        self.body4, created = Body.objects.get_or_create(**params)

    def test_FOM_with_body(self):
        MockDateTime.change_datetime(2015, 4, 21, 17, 0, 0)
        expected_FOM = 137.11876450346662

        FOM = self.body.compute_FOM()

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_wrong_source_type(self):
        MockDateTime.change_datetime(2015, 4, 21, 17, 0, 0)
        expected_FOM = None

        FOM = self.body2.compute_FOM()

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_BadBody(self):
        MockDateTime.change_datetime(2015, 4, 21, 17, 0, 0)
        expected_FOM = None

        FOM = self.body3.compute_FOM()

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_NoScore(self):
        MockDateTime.change_datetime(2015, 4, 21, 17, 0, 0)
        expected_FOM = None

        FOM = self.body4.compute_FOM()

        self.assertEqual(expected_FOM, FOM)


class TestFrame(TestCase):

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

        params['provisional_name'] = 'V92818q'
        self.body2, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'I22871'
        self.body3, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Ntheiqo'
        self.body4, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Q488391r'
        self.body5, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-07-13 21:20:00',
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        # Hand-rolled WCS for pickling testing
        self.naxis_header = {'NAXIS1' : 2028, 'NAXIS2' : 2038, 'NAXIS' :2}
        self.w = WCS(self.naxis_header)
        self.w.wcs.crpix = [ 1024.0, 1024.0]
        self.pixel_scale = 0.469/3600.0
        self.w.wcs.cd = array([[self.pixel_scale, 0.0], [0.0, -self.pixel_scale]])
        self.w.wcs.crval = [150.0, -30.0]
        self.w.wcs.ctype = ["RA---TAN", "DEC--TAN"]

    def test_create_LCOGT_K93_w_single(self):
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e10.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2015-07-13 21:09:51',
                    'block'         : self.test_block,
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(self.test_block, frame.block)
        self.assertEqual(0, frame.frametype)
        self.assertEqual(' ', frame.quality)
        self.assertEqual(None, frame.extrainfo)

    def test_create_LCOGT_W86_r_stack(self):
        params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'r',
                    'filename'      : 'lsc1m009-fl03-20150713-0130-e10+2.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2015-07-13 21:09:51',
                    'block'         : self.test_block,
                    'quality'       : 'K',
                    'frametype'     : 1,
                    'extrainfo'    : 'lsc1m009-fl03-20150713-0130-e10.fits,lsc1m009-fl03-20150713-0131-e10.fits,lsc1m009-fl03-20150713-0132-e10.fits',
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(self.test_block, frame.block)
        self.assertEqual(1, frame.frametype)
        self.assertEqual('K', frame.quality)
        self.assertEqual(params['extrainfo'], frame.extrainfo)
        self.assertEqual(params['filename'], str(frame))

    def test_create_LCOGT_W86_w_stack_starhitnrun(self):
        params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'r',
                    'filename'      : 'lsc1m009-fl03-20150713-0130-e10+2.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2015-07-13 21:09:51',
                    'block'         : self.test_block,
                    'quality'       : 'K,I',
                    'frametype'     : 1,
                    'extrainfo'    : 'lsc1m009-fl03-20150713-0130-e10.fits,lsc1m009-fl03-20150713-0131-e10.fits,lsc1m009-fl03-20150713-0132-e10.fits',
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(self.test_block, frame.block)
        self.assertEqual(1, frame.frametype)
        self.assertEqual('K,I', frame.quality)
        self.assertEqual(params['extrainfo'], frame.extrainfo)
        self.assertEqual(params['filename'], str(frame))

    def test_create_PS2_F52_i_single(self):
        params = {  'sitecode'      : 'F52',
                    'instrument'    : '',
                    'filter'        : 'i',
                    'filename'      : '',
                    'exptime'       : None,
                    'midpoint'      : '2015-10-17 02:33:17.28',
                    'block'         : None,
                    'frametype'     : 2,
                    'extrainfo'     : ''
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(None, frame.block)
        self.assertEqual(2, frame.frametype)
        self.assertEqual(' ', frame.quality)
        self.assertEqual(params['extrainfo'], frame.extrainfo)
        self.assertEqual('', frame.instrument)
        self.assertEqual('', frame.filename)
        self.assertEqual(None, frame.exptime)
        self.assertEqual(params['midpoint'], frame.midpoint)
        self.assertEqual(params['midpoint'] + '@F52', str(frame))

    def test_create_WISE_C51_V_single(self):
        params = {  'sitecode'      : 'C51',
                    'instrument'    : '',
                    'filter'        : 'V',
                    'filename'      : '',
                    'exptime'       : None,
                    'midpoint'      : '2015-10-17 02:33:17.28',
                    'block'         : None,
                    'frametype'     : 3,
                    'extrainfo'     : '     N008jm9  s2015 10 17.10645 1 + 3347.3755 - 3628.1490 - 4781.4778   NEOCPC51'
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(None, frame.block)
        self.assertEqual(3, frame.frametype)
        self.assertEqual(' ', frame.quality)
        self.assertEqual(params['extrainfo'], frame.extrainfo)
        self.assertEqual('', frame.instrument)
        self.assertEqual('', frame.filename)
        self.assertEqual(None, frame.exptime)
        self.assertEqual(params['midpoint'], frame.midpoint)
        self.assertEqual(params['midpoint'] + '@C51', str(frame))

    def test_create_FLOYDS_E10_spectrum(self):
        params = {  'sitecode'      : 'E10',
                    'instrument'    : 'en05',
                    'filter'        : 'SLIT_1.6AS',
                    'filename'      : 'coj2m002-en05-20151029-0011-e00.fits',
                    'exptime'       : 1800.0,
                    'midpoint'      : '2015-10-29T14:03:19.343',
                    'block'         : self.test_block,
                    'frametype'     : 4,
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(self.test_block, frame.block)
        self.assertEqual(4, frame.frametype)
        self.assertEqual(' ', frame.quality)
        self.assertEqual(None, frame.extrainfo)
        self.assertEqual(params['instrument'], frame.instrument)
        self.assertEqual(params['filename'], frame.filename)
        self.assertEqual(params['exptime'], frame.exptime)
        self.assertEqual(params['midpoint'], frame.midpoint)

# For transactional reasons, these assertRaises need to be in their own test
# blocks (see https://code.djangoproject.com/ticket/21540)

    def test_invalid_blank_entry(self):
        params = {}
        with self.assertRaises(IntegrityError):
            frame = Frame.objects.create(**params)

    def test_invalid_blank_entry_no_filter_or_midpoint(self):
        params = { 'sitecode' : 'V37'}
        with self.assertRaises(IntegrityError):
            frame = Frame.objects.create(**params)

    def test_invalid_blank_entry_no_midpoint(self):
        params = { 'sitecode' : 'V37', 'filter' : 'R' }
        with self.assertRaises(IntegrityError):
            frame = Frame.objects.create(**params)

    def test_valid_minimal_entry(self):
        params = { 'sitecode' : 'V37', 'filter' : 'R', 'midpoint'  : '2015-10-29T14:03:19.343' }
        frame = Frame.objects.create(**params)

        self.assertEqual(type(frame), Frame)
        self.assertEqual(params['sitecode'], frame.sitecode)
        self.assertEqual(params['filter'], frame.filter)
        self.assertEqual(params['midpoint'], frame.midpoint)

    def test_store_null_WCS_info(self):
        null_wcs = WCS()
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e10.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2015-07-13 21:09:51',
                    'block'         : self.test_block,
                    'wcs'           : null_wcs
                 }
        frame = Frame.objects.create(**params)
        frame.refresh_from_db()     # Ensure pickling happens

        self.assertNotEqual(None, frame.wcs)
        self.assertEqual(null_wcs, frame.wcs)

    def test_store_TAN_WCS_info(self):
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e10.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2015-07-13 21:09:51',
                    'block'         : self.test_block,
                    'wcs'           : self.w
                 }
        frame = Frame.objects.create(**params)
        frame.refresh_from_db()     # Ensure pickling happens

        pix_coord = array([[512.0, 512.0]])
        self.assertEqual(self.w, frame.wcs)
        self.assertEqual(self.w.wcs_pix2world(pix_coord, 1)[0][0], frame.wcs.wcs_pix2world(pix_coord, 1)[0][0])
        self.assertEqual(self.w.wcs_pix2world(pix_coord, 1)[0][1], frame.wcs.wcs_pix2world(pix_coord, 1)[0][1])
        self.assertEqual(self.pixel_scale, proj_plane_pixel_scales(frame.wcs)[0])
        self.assertEqual(self.pixel_scale, proj_plane_pixel_scales(frame.wcs)[1])

    def test_restore_WCS_naxis(self):
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e10.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2015-07-13 21:09:51',
                    'block'         : self.test_block,
                    'wcs'           : self.w
                 }
        frame = Frame.objects.create(**params)
        frame.refresh_from_db()     # Ensure pickling happens

        self.assertEqual(self.w.naxis, frame.wcs.naxis)
        self.assertEqual(self.w._naxis1, frame.wcs._naxis1)
        self.assertEqual(self.w._naxis2, frame.wcs._naxis2)

class TestSourceMeasurement(TestCase):

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

        params['provisional_name'] = 'P10pyQA'
        params['name'] = '2015 XS54'
        self.body2, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'I22871'
        self.body3, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Ntheiqo'
        self.body4, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Q488391r'
        self.body5, created = Body.objects.get_or_create(**params)

        params['name'] = 'C/2016 C2'
        params['source_type'] = 'MPC_COMET'
        self.body_confirmed, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-07-13 21:20:00',
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        block_params = { 'telclass' : '1m0',
                         'site'     : 'lsc',
                         'body'     : self.body2,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-12-04 00:40:00',
                         'block_end'   : '2015-12-04 08:10:00',
                         'tracking_number' : '0000117781',
                         'num_exposures' : 15,
                         'exp_length' : 95.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'when_observed' : '2015-12-04 02:03:00',
                         'reported' : False
                       }
        self.test_block2 = Block.objects.create(**block_params)

        frame_params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e10.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : datetime(2015,07,13,21,9,51),
                    'block'         : self.test_block,
                 }
        self.test_frame = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'R',
                    'frametype'     : Frame.STACK_FRAMETYPE,
                    'midpoint'      : datetime(2015,12,05,01,10,49,int(0.9*1e6)),
                    'block'         : self.test_block,
                 }
        self.test_frame_stack = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'C51',
                    'filter'        : 'R',
                    'frametype'     : Frame.SATELLITE_FRAMETYPE,
                    'midpoint'      : datetime(2016,2,8,21,24,22,int(0.752*1e6)),
                    'block'         : None,
                    'extrainfo'     : '     N999r0q  s2016 02 08.89193 1 - 3471.6659 - 5748.3475 - 1442.3263        C51'
                 }
        self.test_frame_satellite = Frame.objects.create(**frame_params)

    def test_mpc_1(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "UCAC-4",
                         }
                                 
        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  C2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 wq     K93'
        mpc_line = measure.format_mpc_line()
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_2(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "UCAC-4",
                         }
                                 
        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  C2015 07 13.88184000 30 00.00 -00 30 00.0          21.5 wq     K93'
        mpc_line = measure.format_mpc_line()
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_Kflag(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 20.7,
                            'astrometric_catalog' : "PPMXL",
                            'flags' : 'K'
                         }
                                 
        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q KC2015 07 13.88184010 30 00.00 -32 45 00.0          20.7 wt     K93'
        mpc_line = measure.format_mpc_line()
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_packed_Kflag(self):
        measure_params = {  'body' : self.body2,
                            'frame' : self.test_frame_stack,
                            'obs_ra' : 346.01716666666667,
                            'obs_dec' : -3.8430833333333333,
                            'obs_mag' : 21.6,
                            'flags' : 'K'
                         }
                                 
        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     K15X54S KC2015 12 05.04918923 04 04.12 -03 50 35.1          21.6 R      W86'
        mpc_line = measure.format_mpc_line()
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_nomag(self):
        measure_params = {  'body': self.body2,
                            'aperture_size': None,
                            'astrometric_catalog': u'UCAC4',
                            'err_obs_dec': None,
                            'err_obs_mag': None,
                            'err_obs_ra': None,
                            'flags': u'K',
                            'frame': self.test_frame_stack,
                            'obs_dec': -29.5003055555556,
                            'obs_mag': None,
                            'obs_ra': 106.933,
                            'photometric_catalog': u'UCAC4',
                            'snr': None}
                                 
        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     K15X54S KC2015 12 05.04918907 07 43.92 -29 30 01.1               R      W86'
        mpc_line = measure.format_mpc_line()
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_satellite(self):
        measure_params = {  'body': self.body,
                            'aperture_size': None,
                            'astrometric_catalog': u'2MASS',
                            'err_obs_dec': None,
                            'err_obs_mag': None,
                            'err_obs_ra': None,
                            'flags': '',
                            'frame': self.test_frame_satellite,
                            'obs_dec': -9.834166666666667,
                            'obs_mag': 19,
                            'obs_ra': 228.6245,
                            'photometric_catalog': u'2MASS',
                            'snr': None}
                                 
        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  S2016 02 08.89193 15 14 29.88 -09 50 03.0          19.0 RL     C51' +\
                          '\n' + '     N999r0q  s2016 02 08.89193 1 - 3471.6659 - 5748.3475 - 1442.3263        C51'
        mpc_lines = measure.format_mpc_line()
        self.assertEqual(expected_mpcline, mpc_lines)

    def test_mpc_satellite_confirmed(self):
        measure_params = {  'body': self.body_confirmed,
                            'aperture_size': None,
                            'astrometric_catalog': u'2MASS',
                            'err_obs_dec': None,
                            'err_obs_mag': None,
                            'err_obs_ra': None,
                            'flags': '',
                            'frame': self.test_frame_satellite,
                            'obs_dec': -9.834166666666667,
                            'obs_mag': 19,
                            'obs_ra': 228.6245,
                            'photometric_catalog': u'2MASS',
                            'snr': None}
                                 
        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '    CK16C020  S2016 02 08.89193 15 14 29.88 -09 50 03.0          19.0 RL     C51' +\
                          '\n' + '    CK16C020  s2016 02 08.89193 1 - 3471.6659 - 5748.3475 - 1442.3263        C51'
        mpc_lines = measure.format_mpc_line()
        self.assertEqual(expected_mpcline, mpc_lines)

class TestCatalogSources(TestCase):

    def setUp(self):
        # Initialise with a test body, a test proposal and a test frame
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
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-07-13 21:20:00',
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        frame_params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e10.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : datetime(2015,07,13,21,9,51),
                    'block'         : self.test_block,
                 }
        self.test_frame = Frame.objects.create(**frame_params)

    def test_create_catsrc(self):
        catsrc_params = {   'frame'     : self.test_frame,
                            'obs_x'     : 42.0,
                            'obs_y'     : 1042.0,
                            'obs_ra'    : 123.0,
                            'obs_dec'   : -42.1,
                            'obs_mag'   : 20.1,
                            'err_obs_ra': 1.8/3600.0,
                            'err_obs_dec': 0.9/3600.0,
                            'err_obs_mag': 0.1,
                            'background' : 4.2,
                            'major_axis' : 5.2,
                            'minor_axis' : 2.6,
                            'position_angle' : -30.0,
                            'ellipticity' : 0.5,
                            'aperture_size' : 4.0,
                        }

        CatalogSources.objects.create(**catsrc_params)

        self.assertEqual(CatalogSources.objects.count(), 1)
        new_catsrc = CatalogSources.objects.first()
        self.assertEqual(new_catsrc.obs_x, 42.0)
        self.assertEqual(new_catsrc.frame.filter, 'w')
        self.assertEqual(new_catsrc.frame.exptime, 40.0)

class TestCandidate(TestCase):

    def setUp(self):
        # Initialise with a test body, a test proposal and a test frame
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
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-07-13 21:20:00',
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        frame_params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e10.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : datetime(2015,07,13,21,9,51),
                    'block'         : self.test_block,
                 }
        self.test_frame = Frame.objects.create(**frame_params)

        # Pylint can go to hell...
        self.dtypes =\
             {  'names' : ('det_number', 'frame_number', 'sext_number', 'jd_obs', 'ra', 'dec', 'x', 'y', 'mag', 'fwhm', 'elong', 'theta', 'rmserr', 'deltamu', 'area', 'score', 'velocity', 'sky_pos_angle', 'pixels_frame', 'streak_length'),
                'formats' : ('i4',       'i1',           'i4',          'f8',     'f8', 'f8', 'f4', 'f4', 'f4', 'f4',   'f4',    'f4',    'f4',     'f4',       'i4',   'f4',   'f4',       'f4',        'f4',           'f4' )
             }

        self.dets_array = array([(0001, 1, 3283, 2457444.656045, 10.924317, 39.27700, 2103.245, 2043.026, 19.26, 12.970, 1.764, -60.4, 0.27, 1.39, 34, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (0001, 2,    0, 2457444.657980, 10.924298, 39.27793, 2103.468, 2043.025,  0.00,  1.000, 1.000,   0.0, 0.27, 0.00,  0, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (0001, 3, 3409, 2457444.659923, 10.924271, 39.27887, 2104.491, 2043.034, 19.20, 11.350, 1.373, -57.3, 0.27, 1.38, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (0001, 4, 3176, 2457444.661883, 10.924257, 39.27990, 2104.191, 2043.844, 19.01, 10.680, 1.163, -41.5, 0.27, 1.52, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (0001, 5, 3241, 2457444.663875, 10.924237, 39.28087, 2104.365, 2043.982, 19.17, 12.940, 1.089, -31.2, 0.27, 1.27, 55, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (0001, 6, 3319, 2457444.665812, 10.924220, 39.28172, 2104.357, 2043.175, 18.82, 12.910, 1.254, -37.8, 0.27, 1.38, 69, 1.10, 0.497, 0.2, 9.0, 6.7),],
                                dtype=self.dtypes)

        self.dets_byte_array = self.dets_array.tostring()
        cand_params = { 'block'  : self.test_block,
                        'cand_id' : 0001,
                        'score'  : 1.42,
                        'avg_midpoint' : datetime(2016, 2, 26, 3, 53, 7),
                        'avg_x'  : 1024.0,
                        'avg_y'  : 1042.3,
                        'avg_ra' : 123.42,
                        'avg_dec' : -42.3,
                        'avg_mag' : 20.7,
                        'speed'   : 0.497,
                        'sky_motion_pa' : 90.4,
                        'detections' : self.dets_byte_array
                       }
        self.test_candidate = Candidate.objects.create(**cand_params)

        self.maxDiff = None


    def test_convert_speed(self):

        expected_value = 1.2425

        new_speed = self.test_candidate.convert_speed()

        self.assertEqual(expected_value, new_speed)

    def test_unpack_dets_array(self):
        new_dets_array = self.test_candidate.unpack_dets()

        self.assertEqual(type(self.dets_array), type(new_dets_array))
        for frame in arange(self.dets_array.shape[0]):
            for column in self.dets_array.dtype.names:
                self.assertAlmostEqual(self.dets_array[column][frame], new_dets_array[column][frame], 7)
