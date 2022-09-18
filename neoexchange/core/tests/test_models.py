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

from datetime import datetime, timedelta
from django.test import TestCase
from django.forms.models import model_to_dict
from django.db import connection
from django.db.utils import IntegrityError
from numpy import array, arange, frombuffer
from numpy.testing import assert_allclose
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from unittest import skipIf
from mock import patch
from neox.tests.mocks import MockDateTime

# Import module to test
from core.models import Body, Proposal, SuperBlock, Block, Frame, \
    SourceMeasurement, CatalogSources, Candidate, WCSField, PreviousSpectra,\
    StaticSource


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
        params['ingest'] = datetime(2019, 4, 20, 3, 2, 1)
        self.body2, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'I22871'
        params['update_time'] = params['ingest'] - timedelta(seconds=1)
        self.body3, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Ntheiqo'
        params['update_time'] = params['ingest'] + timedelta(seconds=1)
        self.body4, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'Q488391r'
        self.body5, created = Body.objects.get_or_create(**params)

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

        sblock_params2 = {
                         'body'     : self.body3,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'active'   : False,
                       }
        self.test_sblock2 = SuperBlock.objects.create(**sblock_params2)
        block_params2 = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body3,
                         'superblock' : self.test_sblock2,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block2 = Block.objects.create(**block_params2)

        sblock_params3 = {
                         'body'     : self.body4,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00044',
                         'active'   : False,
                       }
        self.test_sblock3 = SuperBlock.objects.create(**sblock_params3)
        block_params3 = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body4,
                         'superblock' : self.test_sblock3,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10044',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 2,
                         'reported' : False
                       }
        self.test_block3 = Block.objects.create(**block_params3)

        sblock_params5a = {
                         'body'     : self.body5,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00045',
                         'active'   : False,
                       }
        self.test_sblock5a = SuperBlock.objects.create(**sblock_params5a)
        block_params5a = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body5,
                         'superblock' : self.test_sblock5a,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10045',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block5a = Block.objects.create(**block_params5a)

        sblock_params5b = {
                         'body'     : self.body5,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00045',
                         'active'   : False,
                       }
        self.test_sblock5b = SuperBlock.objects.create(**sblock_params5b)
        block_params5b = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body5,
                         'superblock' : self.test_sblock5b,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10045',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 2,
                         'reported' : False
                       }
        self.test_block5b = Block.objects.create(**block_params5b)

        frame_params = { 'sitecode' : 'E10',
                         'instrument' : 'fs03',
                         'midpoint' : self.body5.ingest + timedelta(days=1),
                         'block' : self.test_block5b
                       }
        self.test_frame = Frame.objects.create(**frame_params)

        srcm_params = { 'body' : self.body5,
                        'frame' : self.test_frame
                      }
        self.test_srcmeasure = SourceMeasurement.objects.create(**srcm_params)

        spectra_params = {'body'         : self.body,
                          'spec_wav'     : 'Vis',
                          'spec_vis'     : 'sp233/a265962.sp233.txt',
                          'spec_ref'     : 'sp[233]',
                          'spec_source'  : 'S',
                          'spec_date'    : '2017-09-25',
                          }
        self.test_spectra = PreviousSpectra.objects.create(pk=1, **spectra_params)

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

    def test_no_absmag(self):
        test_body = self.body
        test_body.abs_mag = None
        test_body.save()

        diameter = test_body.diameter()
        self.assertEqual(None, diameter)

    def test_bad_absmag(self):
        test_body = self.body
        test_body.abs_mag = -99
        test_body.save()

        diameter = test_body.diameter()
        self.assertEqual(None, diameter)

    def test_compute_obs_window_mid(self):
        test_body = self.body
        test_body.abs_mag = 19.0
        test_body.save()

        expected_start = datetime(2015, 8, 10, 17, 0)
        expected_end = datetime(2015, 9, 29, 17, 0)
        obs_window = test_body.compute_obs_window(d=datetime(2015, 7, 1, 17, 0, 0))
        self.assertEqual(obs_window[0], expected_start)
        self.assertEqual(obs_window[1], expected_end)

    def test_compute_obs_window_full(self):
        test_body = self.body
        test_body.abs_mag = 17.0
        test_body.save()

        expected_start = datetime(2015, 7, 1, 17, 0, )
        expected_end = ''
        obs_window = test_body.compute_obs_window(d=datetime(2015, 7, 1, 17, 0, 0))
        self.assertEqual(obs_window[0], expected_start)
        self.assertEqual(obs_window[1], expected_end)

    def test_compute_obs_window_none(self):
        test_body = self.body
        test_body.save()

        expected_start = ''
        expected_end = ''
        obs_window = test_body.compute_obs_window(d=datetime(2015, 7, 1, 17, 0, 0))
        self.assertEqual(obs_window[0], expected_start)
        self.assertEqual(obs_window[1], expected_end)

    def test_compute_obs_window_sun(self):
        test_body = self.body
        test_body.abs_mag = 8.0
        test_body.meananom = 180
        test_body.save()

        expected_start = ''
        expected_end = ''
        obs_window = test_body.compute_obs_window(d=datetime(2015, 7, 1, 17, 0, 0))
        self.assertEqual(obs_window[0], expected_start)
        self.assertEqual(obs_window[1], expected_end)

    def test_return_latest_measurement_no_ingest(self):
        expected_dt = self.body.ingest
        expected_type = 'Ingest Time'

        update_type, update_dt = self.body.get_latest_update()

        self.assertEqual(expected_type, update_type)
        self.assertEqual(expected_dt, update_dt)

    def test_return_latest_measurement_ingest(self):
        expected_dt = self.body2.ingest
        expected_type = 'Ingest Time'

        update_type, update_dt = self.body2.get_latest_update()

        self.assertEqual(expected_type, update_type)
        self.assertEqual(expected_dt, update_dt)

    def test_return_latest_measurement_update_earlier(self):
        expected_dt = self.body3.ingest
        expected_type = 'Ingest Time'

        update_type, update_dt = self.body3.get_latest_update()

        self.assertEqual(expected_type, update_type)
        self.assertEqual(expected_dt, update_dt)

    def test_return_latest_measurement_update_later(self):
        expected_dt = self.body4.update_time
        expected_type = 'Last Update'

        update_type, update_dt = self.body4.get_latest_update()

        self.assertEqual(expected_type, update_type)
        self.assertEqual(expected_dt, update_dt)

    def test_return_later_srcmeasure(self):
        expected_dt = self.test_frame.midpoint
        expected_type = 'Last Measurement'

        update_type, update_dt = self.body5.get_latest_update()

        self.assertEqual(expected_type, update_type)
        self.assertEqual(expected_dt, update_dt)

    def test_return_earlier_srcmeasure(self):
        self.body5.update_time += timedelta(days=2)
        self.body5.save()
        self.body5.refresh_from_db()

        expected_dt = self.body5.update_time
        expected_type = 'Last Update'

        update_type, update_dt = self.body5.get_latest_update()

        self.assertEqual(expected_type, update_type)
        self.assertEqual(expected_dt, update_dt)


@patch('core.models.body.datetime', MockDateTime)
class TestComputeFOM(TestCase):

    def setUp(self):
        # Initialise with a test body and two test proposals
        params = {  'provisional_name' : 'N999r0q',
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
        expected_FOM = 137.11876237236538

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


class TestComputePeriod(TestCase):

    def setUp(self):
        # Initialise with a few test bodies
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

        params['eccentricity'] = 1.0
        self.body_parabolic, created = Body.objects.get_or_create(**params)

        params['eccentricity'] = 1.001
        self.body_hyperbolic, created = Body.objects.get_or_create(**params)

        params['eccentricity'] = None
        self.body_bad_e, created = Body.objects.get_or_create(**params)

        params = {
                     'provisional_name': None,
                     'provisional_packed': None,
                     'name': '46P',
                     'origin': 'O',
                     'source_type': 'C',
                     'source_subtype_1': 'JF',
                     'source_subtype_2': None,
                     'elements_type': 'MPC_COMET',
                     'active': True,
                     'fast_moving': False,
                     'urgency': None,
                     'epochofel': datetime(2018, 12, 13, 0, 0),
                     'orbit_rms': 0.5,
                     'orbinc': 11.7476819127047,
                     'longascnode': 82.1575744851216,
                     'argofperih': 356.341231360739,
                     'eccentricity': 0.6587595570783943,
                     'meandist': None,
                     'meananom': None,
                     'perihdist': 1.055355764253904,
                     'epochofperih': datetime(2018, 12, 12, 22, 21, 2),
                     'abs_mag': 14.9,
                     'slope': 6.4,
                     'score': 58,
                     'discovery_date': datetime(1948, 1, 17, 9, 36),
                     'num_obs': 14,
                     'arc_length': 2.61,
                     'not_seen': 0.023,
                     'updated': True,
                     'ingest': datetime(2017, 5, 21, 19, 50, 9),
                     'update_time': datetime(2017, 5, 24, 2, 51, 58)}
        self.body_46P, created = Body.objects.get_or_create(**params)

        params = {
                     'provisional_name': None,
                     'provisional_packed': None,
                     'name': 'C/2013 US10',
                     'origin': 'O',
                     'source_type': 'C',
                     'source_subtype_1': 'H',
                     'source_subtype_2': None,
                     'elements_type': 'MPC_COMET',
                     'active': True,
                     'fast_moving': False,
                     'urgency': None,
                     'epochofel': datetime(2019, 4, 27, 0, 0),
                     'orbit_rms': 99.0,
                     'orbinc': 148.83797,
                     'longascnode': 186.25239,
                     'argofperih': 340.51541,
                     'eccentricity': 1.0005522,
                     'meandist': None,
                     'meananom': None,
                     'perihdist': 0.8244693,
                     'epochofperih': datetime(2015, 11, 16, 1, 5, 31),
                     'abs_mag': 8.1,
                     'slope': 2.8,
                     'score': None,
                     'discovery_date': datetime(2013, 8, 14, 0, 0),
                     'num_obs': 4703,
                     'arc_length': 1555.0,
                     'not_seen': 963.9336267593403,
                     'updated': True,
                     'ingest': datetime(2020, 7, 6, 22, 23, 23),
                     'update_time': datetime(2017, 11, 16, 0, 0)
                    }
        self.body_US10, created = Body.objects.get_or_create(**params)

    def test_asteroid(self):
        expected_period = 1.3436113120948885

        period = self.body.period

        self.assertAlmostEqual(expected_period, period, 5)

    def test_asteroid_parabolic(self):
        expected_period = 1e99

        period = self.body_parabolic.period

        self.assertEqual(expected_period, period)

    def test_asteroid_hyperbolic(self):
        expected_period = 1e99

        period = self.body_hyperbolic.period

    def test_asteroid_no_e(self):
        expected_period = None

        period = self.body_bad_e.period

        self.assertEqual(expected_period, period)

    def test_comet(self):
        expected_period = 5.4388562985454545

        period = self.body_46P.period

        self.assertAlmostEqual(expected_period, period, 5)

    def test_comet_hyperbolic(self):
        expected_period = 1e99

        period = self.body_US10.period


class TestSavePhysicalParameters(TestCase):

    def setUp(self):
        params = {  'name' : '21545',
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

        self.phys1 = {'parameter_type': 'H',
                 'value': 24.56,
                 'error': 0.05,
                 'units': 'mag',
                 'reference' : "Bob and Friends, 2019",
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }

        self.phys2 = {'parameter_type': 'P',
                 'value': 8.7,
                 'error': 0.5,
                 'units': 'h',
                 'reference': "Bob and Friends, 2019",
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }

        self.col1 = {'color_band': 'V-R',
                 'value': .87,
                 'error': 0.05,
                 'units': 'mag',
                 'reference': "Bob and Friends, 2019",
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }

        self.des1 = {'desig_type': 'N',
                 'value': 'Rock&Roll',
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }

    def test_save_get_param(self):
        self.body.save_physical_parameters(self.phys1)
        self.body.save_physical_parameters(self.phys2)

        get_db = self.body.get_physical_parameters()

        self.assertEqual(self.phys1['value'], get_db[0]['value'])
        self.assertEqual(self.phys2['value'], get_db[1]['value'])
        self.assertEqual('Absolute Magnitude', get_db[0]['type_display'])

    def test_wont_save_same_data_twice(self):
        self.body.save_physical_parameters(self.phys1)
        self.body.save_physical_parameters(self.phys1)
        self.body.save_physical_parameters(self.phys2)
        self.body.save_physical_parameters(self.phys1)
        self.body.save_physical_parameters(self.phys2)

        get_db = self.body.get_physical_parameters()

        self.assertEqual(len(get_db), 2)

    def test_overwrite_priority(self):
        self.body.save_physical_parameters(self.phys1)
        self.body.save_physical_parameters(self.phys2)

        new_data = self.phys1
        new_data['value'] = 12.5
        self.body.save_physical_parameters(new_data)

        get_db = self.body.get_physical_parameters()

        self.assertFalse(get_db[0]['preferred'])
        self.assertTrue(get_db[1]['preferred'])
        self.assertTrue(get_db[2]['preferred'])

    def test_change_priority(self):

        new_data1 = self.phys1.copy()
        new_data_old = self.phys1.copy()
        self.body.save_physical_parameters(self.phys1)

        new_data1['value'] = 12.5
        self.body.save_physical_parameters(new_data1)

        self.body.save_physical_parameters(self.phys2)

        new_data_old['preferred'] = True

        self.body.save_physical_parameters(new_data_old)

        get_db = self.body.get_physical_parameters()

        self.assertFalse(get_db[0]['preferred'])
        self.assertTrue(get_db[1]['preferred'])
        self.assertTrue(get_db[2]['preferred'])

    def test_ingest_not_preferred(self):
        phys3 = {'parameter_type': 'D',
                 'value': 8.7,
                 'error': 0.5,
                 'units': 'm',
                 'reference': "Bob and Friends, 2019",
                 'notes': 'This is a fake entry'}
        # save 1st diameter (not preferred)
        self.body.save_physical_parameters(phys3)
        d1 = self.body.get_physical_parameters(param_type='D')
        self.assertTrue(d1[0]['preferred'])

        # save new diameter (also not preferred)
        phys3['value'] = 10.5
        phys3.pop('preferred')
        self.body.save_physical_parameters(phys3)
        d2 = self.body.get_physical_parameters(param_type='D')
        self.assertTrue(d2[0]['preferred'])
        self.assertFalse(d2[1]['preferred'])

        # change so there is no preferred diameter
        phys3['preferred'] = False
        phys3['value'] = 8.7
        self.body.save_physical_parameters(phys3)
        d3 = self.body.get_physical_parameters(param_type='D')
        self.assertFalse(d3[0]['preferred'])
        self.assertFalse(d3[1]['preferred'])

        # re-save original diameter
        self.body.save_physical_parameters(phys3)
        d4 = self.body.get_physical_parameters(param_type='D')
        self.assertFalse(d4[0]['preferred'])
        self.assertFalse(d4[1]['preferred'])

        # save new diameter while none are preferred. (make sure units work)
        phys3['units'] = 'km'
        self.body.save_physical_parameters(phys3)
        d5 = self.body.get_physical_parameters(param_type='D')
        self.assertFalse(d5[0]['preferred'])
        self.assertFalse(d5[1]['preferred'])
        self.assertTrue(d5[2]['preferred'])
        self.assertEqual(d5[2]['units'], 'km')

    def test_mpc_default(self):
        phys3 = {'parameter_type': 'D',
                 'value': 8.7,
                 'error': 0.5,
                 'units': 'm',
                 'reference': "MPC Default",
                 'notes': 'This is a fake entry',
                 'preferred': True}
        # Save MPC Default entry
        self.body.save_physical_parameters(phys3)
        phys3['value'] = 12.5
        # test Overwrite of MPC Default
        self.body.save_physical_parameters(phys3)
        d1 = self.body.get_physical_parameters(param_type='D')
        self.assertEqual(len(d1), 1)
        self.assertEqual(d1[0]['value'], 12.5)

        # Add non MPC Default
        phys3['value'] = 15.4
        phys3['reference'] = 'Some Guy'
        self.body.save_physical_parameters(phys3)
        d2 = self.body.get_physical_parameters(param_type='D')
        self.assertEqual(len(d2), 2)
        self.assertEqual(d2[0]['value'], 12.5)
        self.assertEqual(d2[1]['value'], 15.4)
        self.assertFalse(d2[0]['preferred'])
        self.assertTrue(d2[1]['preferred'])

        # Overwrite MPC Default, and leave other entry as preferred.
        phys3['value'] = 10.1
        phys3['reference'] = 'MPC Default'
        self.body.save_physical_parameters(phys3)
        d3 = self.body.get_physical_parameters(param_type='D')
        self.assertEqual(len(d3), 2)
        self.assertEqual(d3[1]['value'], 10.1)
        self.assertEqual(d3[0]['value'], 15.4)
        self.assertFalse(d3[1]['preferred'])
        self.assertTrue(d3[0]['preferred'])


class TestGetPhysicalParameters(TestCase):

    def setUp(self):
        params = {  'name' : 'nameless',
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

        phys1 = {'parameter_type': 'H',
                 'value': 24.56,
                 'error': 0.05,
                 'units': 'mag',
                 'reference' : "Bob and Friends, 2019",
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }
        self.body.save_physical_parameters(phys1)

        phys2 = {'parameter_type': 'P',
                 'value': 8.7,
                 'error': 0.5,
                 'units': 'h',
                 'reference': "Bob and Friends, 2019",
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }
        self.body.save_physical_parameters(phys2)

        phys3 = {'parameter_type': 'P',
                 'value': 82,
                 'error': 5,
                 'units': 'h',
                 'reference': "Bob and Friends, 2014",
                 'notes': 'This is a fake entry',
                 'preferred': False
                 }
        self.body.save_physical_parameters(phys3)

        col1 = {'color_band': 'V-R',
                 'value': .87,
                 'error': 0.05,
                 'units': 'mag',
                 'reference': "Bob and Friends, 2019",
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }
        self.body.save_physical_parameters(col1)

        col2 = {'color_band': 'B-V',
                 'value': .24,
                 'error': 0.05,
                 'units': 'mag',
                 'reference': "Bob and Friends, 2019",
                 'notes': 'This is a fake entry',
                 'preferred': True
                 }
        self.body.save_physical_parameters(col2)

    def test_get_everything(self):
        expected_returns = [(24.56, 'Absolute Magnitude'), (8.7, 'Rotation Period'), (82, 'Rotation Period'), (.87, 'V-R'), (.24, 'B-V')]
        get_db = self.body.get_physical_parameters()
        for param in get_db:
            test_param = (param['value'], param['type_display'])
            self.assertIn(test_param, expected_returns)
            expected_returns.remove(test_param)
        self.assertEqual(expected_returns, [])

    def test_get_preferred(self):
        expected_returns = [(24.56, 'Absolute Magnitude'), (8.7, 'Rotation Period'), (.87, 'V-R'), (.24, 'B-V')]
        get_db = self.body.get_physical_parameters(return_all=False)
        for param in get_db:
            test_param = (param['value'], param['type_display'])
            self.assertIn(test_param, expected_returns)
            expected_returns.remove(test_param)
        self.assertEqual(expected_returns, [])

    def test_get_abs_mag(self):
        expected_returns = [(24.56, 'Absolute Magnitude')]
        get_db = self.body.get_physical_parameters(param_type='H')
        for param in get_db:
            test_param = (param['value'], param['type_display'])
            self.assertIn(test_param, expected_returns)
            expected_returns.remove(test_param)
        self.assertEqual(expected_returns, [])

    def test_get_prefered_period(self):
        expected_returns = [(8.7, 'Rotation Period')]
        get_db = self.body.get_physical_parameters(param_type='P', return_all=False)
        for param in get_db:
            test_param = (param['value'], param['type_display'])
            self.assertIn(test_param, expected_returns)
            expected_returns.remove(test_param)
        self.assertEqual(expected_returns, [])

    def test_get_colors(self):
        expected_returns = [(.87, 'V-R'), (.24, 'B-V')]
        get_db = self.body.get_physical_parameters(param_type='Colors')
        for param in get_db:
            test_param = (param['value'], param['type_display'])
            self.assertIn(test_param, expected_returns)
            expected_returns.remove(test_param)
        self.assertEqual(expected_returns, [])

    def test_get_specific_color(self):
        expected_returns = [(.87, 'V-R')]
        get_db = self.body.get_physical_parameters(param_type='V-R')
        for param in get_db:
            test_param = (param['value'], param['type_display'])
            self.assertIn(test_param, expected_returns)
            expected_returns.remove(test_param)
        self.assertEqual(expected_returns, [])

    def test_get_mag_by_name(self):
        expected_returns = [(24.56, 'Absolute Magnitude')]
        get_db = self.body.get_physical_parameters(param_type='absolute magnitude')
        for param in get_db:
            test_param = (param['value'], param['type_display'])
            self.assertIn(test_param, expected_returns)
            expected_returns.remove(test_param)
        self.assertEqual(expected_returns, [])


class TestGetFullName(TestCase):

    def setUp(self):
        params = {  'name' : 'nameless',
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

        self.des1 = {'desig_type': 'N',
                     'value': 'Rock&Roll',
                     'notes': 'This is a fake entry',
                     'preferred': True
                     }

        self.des2 = {'desig_type': '#',
                     'value': '4224',
                     'notes': 'This is a fake entry',
                     'preferred': True
                     }

        self.des3 = {'desig_type': 'P',
                     'value': '1969 QQ3',
                     'notes': 'This is a fake entry',
                     'preferred': True
                     }

        self.des4 = {'desig_type': 'P',
                     'value': '1888 UT3',
                     'notes': 'This is a fake entry',
                     'preferred': False
                     }

    def test_full_name_no_entries(self):
        expected_name = 'nameless'
        full_name = self.body.full_name()
        self.assertEqual(full_name, expected_name)

    def test_full_name_prov_only(self):
        expected_name = '1969 QQ3'
        self.body.save_physical_parameters(self.des4)
        self.body.save_physical_parameters(self.des3)
        full_name = self.body.full_name()
        self.assertEqual(full_name, expected_name)

    def test_full_name_provnum_only(self):
        expected_name = '4224 (1969 QQ3)'
        self.body.save_physical_parameters(self.des3)
        self.body.save_physical_parameters(self.des4)
        self.body.save_physical_parameters(self.des2)
        full_name = self.body.full_name()
        self.assertEqual(full_name, expected_name)

    def test_full_name_all(self):
        expected_name = '4224 Rock&Roll (1969 QQ3)'
        self.body.save_physical_parameters(self.des3)
        self.body.save_physical_parameters(self.des4)
        self.body.save_physical_parameters(self.des2)
        self.body.save_physical_parameters(self.des1)
        full_name = self.body.full_name()
        self.assertEqual(full_name, expected_name)

    def test_full_namenum_only(self):
        expected_name = '4224 Rock&Roll'
        self.body.save_physical_parameters(self.des2)
        self.body.save_physical_parameters(self.des1)
        full_name = self.body.full_name()
        self.assertEqual(full_name, expected_name)

    def test_comet_num(self):
        expected_name = '4224P/Rock&Roll'
        self.des2['value'] += 'P'
        self.body.save_physical_parameters(self.des2)
        self.body.save_physical_parameters(self.des1)
        full_name = self.body.full_name()
        self.assertEqual(full_name, expected_name)

    def test_comet_num_old(self):
        expected_name = 'P/1876 W2 (New)'
        self.des2['value'] = 'P'
        self.des1['value'] = '1876 W2'
        self.des3['value'] = 'New'
        self.body.save_physical_parameters(self.des2)
        self.body.save_physical_parameters(self.des1)
        self.body.save_physical_parameters(self.des3)
        full_name = self.body.full_name()
        self.assertEqual(full_name, expected_name)


@patch('core.models.body.datetime', MockDateTime)
class TestGetCadenceInfo(TestCase):

    def setUp(self):
        params = {
                 'name': 'C/2013 US10',
                 'origin': 'O',
                 'source_type': 'C',
                 'source_subtype_1': 'H',
                 'source_subtype_2': 'DN',
                 'elements_type': 'MPC_COMET',
                 'active': True,
                 'epochofel': datetime(2019, 4, 27, 0, 0),
                 'orbinc': 148.83797,
                 'longascnode': 186.25239,
                 'argofperih': 340.51541,
                 'eccentricity': 1.0005522,
                 'perihdist': 0.8244693,
                 'epochofperih': datetime(2015, 11, 16, 1, 5, 31, 200000),
                 'abs_mag': 8.1,
                 'slope': 2.8,
                 'discovery_date': datetime(2013, 8, 14, 0, 0),
                 'updated': True,
                 }
        self.comet_US10, created = Body.objects.get_or_create(**params)
        params = {
                   'name': 'C/2017 K2',
                   'origin': 'O',
                   'source_type': 'C',
                   'source_subtype_1': 'H',
                   'source_subtype_2': None,
                   'elements_type': 'MPC_COMET',
                   'active': True,
                   'epochofel': datetime(2020, 5, 31, 0, 0),
                   'orbit_rms': 0.4,
                   'orbinc': 87.54274,
                   'longascnode': 88.26626,
                   'argofperih': 236.15875,
                   'eccentricity': 1.0004242,
                   'perihdist': 1.7996145,
                   'epochofperih': datetime(2022, 12, 19, 23, 32, 38, 400000),
                   'abs_mag': 6.6,
                   'slope': 2.2,
                   'discovery_date': datetime(2013, 5, 12, 0, 0)
                   }
        self.comet_K2, created = Body.objects.get_or_create(**params)

        params = { 'code' : 'KEY2020A-001',
                   'title' : 'LOOK Projectal'
                 }
        self.proposal = Proposal.objects.create(**params)
        return

    def insert_sblock(self, body, cadence):
        sblock_params = {   'cadence' : cadence,
                            'body' : body,
                            'proposal' : self.proposal,
                            'block_start' : datetime(2017, 7, 1, 3),
                            'block_end' : datetime(2017, 7, 20, 23),
                            'active' : True
                        }
        sblock,created = SuperBlock.objects.get_or_create(**sblock_params)

        return sblock

    def test_nosblocks(self):
        expected_result = "Nothing scheduled"

        result = self.comet_K2.get_cadence_info()

        self.assertEqual(expected_result, result)

    def test_no_cadence_sblocks(self):
        sblock = self.insert_sblock(self.comet_K2, cadence=False)

        expected_result = "Nothing scheduled"

        result = self.comet_K2.get_cadence_info()

        self.assertEqual(expected_result, result)

    def test_active_cadence_sblocks(self):
        sblock = self.insert_sblock(self.comet_K2, cadence=True)

        expected_result = "Active until 07/20"

        result = self.comet_K2.get_cadence_info()

        self.assertEqual(expected_result, result)

    def test_inactive_cadence_sblocks(self):
        sblock = self.insert_sblock(self.comet_K2, cadence=True)
        MockDateTime.change_datetime(2017, 7, 21, 1, 2, 3)

        expected_result = "Inactive since 07/20"

        result = self.comet_K2.get_cadence_info()

        self.assertEqual(expected_result, result)

    def test_inactive_cadence_sblocks_future(self):
        sblock = self.insert_sblock(self.comet_K2, cadence=True)
        sblock.active = False
        sblock.save()
        MockDateTime.change_datetime(2017, 7, 15, 1, 2, 3)

        expected_result = "Inactive"

        result = self.comet_K2.get_cadence_info()

        self.assertEqual(expected_result, result)

class TestSuperBlock(TestCase):

    def setUp(self):
        params = {  'provisional_name' : 'N999r0q',
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

        params = { 'code' : 'LCOEngineering',
                   'title' : 'Engineering proposal'
                 }
        self.proposal = Proposal.objects.create(**params)

        sblock_params = {   'cadence' : False,
                            'body' : self.body,
                            'proposal' : self.proposal,
                            'block_start' : datetime(2015, 4, 20, 3),
                            'block_end' : datetime(2015, 4, 20, 23),
                            'active' : True
                        }
        self.sblock = SuperBlock.objects.create(**sblock_params)

        params1 = { 'telclass' : '2m0',
                    'site' : 'coj',
                    'body' : self.body,
                    'superblock' : self.sblock,
                    'obstype' : Block.OPT_SPECTRA,
                    'block_start' : datetime(2015, 4, 20, 4, 0),
                    'block_end' : datetime(2015, 4, 20, 5, 15),
                    'request_number' : '1',
                    'num_exposures' : 1,
                    'exp_length' : 1800
                  }
        self.block1 = Block.objects.create(**params1)

        params2 = { 'telclass' : '1m0',
                    'site' : 'coj',
                    'body' : self.body,
                    'superblock' : self.sblock,
                    'obstype' : Block.OPT_IMAGING,
                    'block_start' : datetime(2015, 4, 20, 6, 15),
                    'block_end' : datetime(2015, 4, 20, 6, 30),
                    'request_number' : '2',
                    'num_exposures' : 4,
                    'exp_length' : 120.0
                  }
        self.block2 = Block.objects.create(**params2)

        params3 = { 'telclass' : '1m0',
                    'site' : 'coj',
                    'body' : self.body,
                    'superblock' : self.sblock,
                    'obstype' : Block.OPT_IMAGING,
                    'block_start' : datetime(2015, 4, 20, 8, 0),
                    'block_end' : datetime(2015, 4, 20, 10, 15),
                    'request_number' : '3',
                    'num_exposures' : 120,
                    'exp_length' : 60.0
                  }
        self.block3 = Block.objects.create(**params3)

    def test_telclass(self):
        expected_telclass1 = "2m0(S)"
        expected_telclass2 = "1m0"

        tel_class = self.sblock.get_telclass()

        self.assertIn(expected_telclass1, tel_class)
        self.assertIn(expected_telclass2, tel_class)

    def test_telclass_spectro_only(self):
        # Remove non spectroscopic blocks
        self.block2.delete()
        self.block3.delete()

        expected_telclass = "2m0(S)"

        tel_class = self.sblock.get_telclass()

        self.assertEqual(expected_telclass, tel_class)

    def test_obstypes(self):
        expected_obstypes = "1,0"

        obs_types = self.sblock.get_obstypes()

        self.assertEqual(expected_obstypes, obs_types)

    def test_obstypes_noblocks(self):
        expected_obstypes = ''

        # Create new SuperBlock for the next day and assert that there are
        # no Block's associated with it.
        new_sblock = SuperBlock(body = self.body,
                                proposal = self.proposal,
                                block_start = self.sblock.block_start + timedelta(days=1, seconds=300),
                                block_end   = self.sblock.block_end + timedelta(days=1, seconds=300)
                               )
        new_sblock.save()

        self.assertEqual(2, SuperBlock.objects.count())
        num_assoc_blocks = Block.objects.filter(superblock=new_sblock.id).count()

        self.assertEqual(0, num_assoc_blocks)

        obs_types = new_sblock.get_obstypes()

        self.assertEqual(expected_obstypes, obs_types)


class TestBlock(TestCase):
    @classmethod
    def setUpTestData(cls):
        params = {  'provisional_name' : 'N999r0q',
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
        cls.body, created = Body.objects.get_or_create(**params)

        params = { 'code' : 'LCOEngineering',
                   'title' : 'Engineering proposal'
                 }
        cls.proposal = Proposal.objects.create(**params)

        sblock_params = {   'cadence' : False,
                            'body' : cls.body,
                            'proposal' : cls.proposal,
                            'block_start' : datetime(2015, 4, 20, 3),
                            'block_end' : datetime(2015, 4, 20, 23),
                            'active' : True
                        }
        cls.sblock = SuperBlock.objects.create(**sblock_params)

        staticsrc_params = { 'name' : 'Landolt SA107-684',
                             'ra'   : 234.325,
                             'dec'  : -0.164,
                             'vmag' : 8.2,
                             'source_type' : StaticSource.SOLAR_STANDARD,
                             'spectral_type' : 'G2V'
                           }
        cls.staticsrc = StaticSource.objects.create(**staticsrc_params)

        cls.params_spectro = { 'telclass' : '2m0',
                    'site' : 'coj',
                    'body' : cls.body,
                    'calibsource' : None,
                    'superblock' : cls.sblock,
                    'obstype' : Block.OPT_SPECTRA,
                    'block_start' : datetime(2015, 4, 20, 4, 0),
                    'block_end' : datetime(2015, 4, 20, 5, 15),
                    'request_number' : '1',
                    'num_exposures' : 1,
                    'exp_length' : 1800
                  }
        cls.params_imaging1 = { 'telclass' : '1m0',
                    'site' : 'coj',
                    'body' : cls.body,
                    'calibsource' : None,
                    'superblock' : cls.sblock,
                    'obstype' : Block.OPT_IMAGING,
                    'block_start' : datetime(2015, 4, 20, 6, 15),
                    'block_end' : datetime(2015, 4, 20, 6, 30),
                    'request_number' : '2',
                    'num_exposures' : 4,
                    'exp_length' : 120.0
                  }

        cls.params_imaging2 = { 'telclass' : '1m0',
                    'site' : 'coj',
                    'body' : cls.body,
                    'calibsource' : None,
                    'superblock' : cls.sblock,
                    'obstype' : Block.OPT_IMAGING,
                    'block_start' : datetime(2015, 4, 20, 8, 0),
                    'block_end' : datetime(2015, 4, 20, 10, 15),
                    'request_number' : '3',
                    'num_exposures' : 120,
                    'exp_length' : 60.0
                  }

        cls.params_calib = { 'telclass' : '2m0',
                    'site' : 'coj',
                    'body' : None,
                    'calibsource' : cls.staticsrc,
                    'superblock' : cls.sblock,
                    'obstype' : Block.OPT_SPECTRA,
                    'block_start' : datetime(2015, 4, 20, 4, 0),
                    'block_end' : datetime(2015, 4, 20, 5, 15),
                    'request_number' : '4',
                    'num_exposures' : 1,
                    'exp_length' : 300.0
                  }

    def test_spectro_block(self):

        block = Block.objects.create(**self.params_spectro)

        self.assertEqual(self.body.current_name(), block.current_name())

    def test_solar_analog_block(self):

        block = Block.objects.create(**self.params_calib)

        self.assertEqual(self.staticsrc.current_name(), block.current_name())

    def test_where_observed(self):

        from astrometrics.site_config import valid_telescope_codes

        self.params_imaging1['num_observed'] = 1
        block = Block.objects.create(**self.params_imaging1)

        params = {
                    'instrument'    : 'fa99',
                    'filter'        : 'w',
                    'filename'      : 'cpt1m012-fa99-20150713-0130-e91.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2015-07-13 21:09:51',
                    'block'         : block,
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE
                 }
        frame = Frame.objects.create(**params)

        for site in valid_telescope_codes:
            # Don't test generic sites
            if site[0].isdigit() is False:
                frame.sitecode = site
                frame.save()
                obs_string = block.where_observed()
                self.assertNotEqual('', obs_string)
                self.assertNotIn('Unknown LCO site', obs_string)


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
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True,
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-07-13 21:20:00',
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        # Hand-rolled WCS for pickling testing
        self.naxis_header = {'NAXIS1' : 2028, 'NAXIS2' : 2038, 'NAXIS' : 2}
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

    def test_create_catalog(self):
        params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'w',
                    'filename'      : 'lsc1m009-fl03-20161108-0065-e91_ldac.fits',
                    'exptime'       : 260.0,
                    'midpoint'      : '2016-11-09T06:53:01.750',
                    'block'         : self.test_block,
                    'frametype'     : Frame.FITS_LDAC_CATALOG,
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(self.test_block, frame.block)
        self.assertEqual(5, frame.frametype)
        self.assertEqual(' ', frame.quality)
        self.assertEqual(None, frame.extrainfo)
        self.assertEqual(params['instrument'], frame.instrument)
        self.assertEqual(params['filename'], frame.filename)
        self.assertEqual(params['exptime'], frame.exptime)
        self.assertEqual(params['midpoint'], frame.midpoint)
        self.assertTrue(frame.is_catalog())

    def test_create_banzai_ql(self):
        params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'w',
                    'filename'      : 'lsc1m009-fl03-20161108-0065-e11.fits',
                    'exptime'       : 260.0,
                    'midpoint'      : '2016-11-09T06:53:01.750',
                    'block'         : self.test_block,
                    'frametype'     : Frame.BANZAI_QL_FRAMETYPE,
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(self.test_block, frame.block)
        self.assertEqual(11, frame.frametype)
        self.assertEqual(' ', frame.quality)
        self.assertEqual(None, frame.extrainfo)
        self.assertEqual(params['instrument'], frame.instrument)
        self.assertEqual(params['filename'], frame.filename)
        self.assertEqual(params['exptime'], frame.exptime)
        self.assertEqual(params['midpoint'], frame.midpoint)
        self.assertTrue(frame.is_quicklook())
        self.assertTrue(frame.is_processed())

    def test_create_banzai_red(self):
        params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'w',
                    'filename'      : 'lsc1m009-fl03-20161108-0065-e91.fits',
                    'exptime'       : 260.0,
                    'midpoint'      : '2016-11-09T06:53:01.750',
                    'block'         : self.test_block,
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                 }
        frame = Frame.objects.create(**params)

        self.assertEqual(self.test_block, frame.block)
        self.assertEqual(91, frame.frametype)
        self.assertEqual(' ', frame.quality)
        self.assertEqual(None, frame.extrainfo)
        self.assertEqual(params['instrument'], frame.instrument)
        self.assertEqual(params['filename'], frame.filename)
        self.assertEqual(params['exptime'], frame.exptime)
        self.assertEqual(params['midpoint'], frame.midpoint)
        self.assertFalse(frame.is_quicklook())
        self.assertTrue(frame.is_reduced())
        self.assertTrue(frame.is_processed())

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
        params = { 'sitecode' : 'V37', 'filter' : 'R'}
        with self.assertRaises(IntegrityError):
            frame = Frame.objects.create(**params)

    def test_valid_minimal_entry(self):
        params = { 'sitecode' : 'V37', 'filter' : 'R', 'midpoint'  : '2015-10-29T14:03:19.343'}
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

        pix_coord = array([[512.0, 512.0]])
        assert_allclose(null_wcs.wcs.pc, frame.wcs.wcs.cd, rtol=1e-8)
        self.assertEqual(null_wcs.all_pix2world(pix_coord, 1)[0][0], frame.wcs.all_pix2world(pix_coord, 1)[0][0])
        self.assertEqual(null_wcs.all_pix2world(pix_coord, 1)[0][1], frame.wcs.all_pix2world(pix_coord, 1)[0][1])
        self.assertAlmostEqual(1.0, proj_plane_pixel_scales(frame.wcs)[0], 10)
        self.assertAlmostEqual(1.0, proj_plane_pixel_scales(frame.wcs)[1], 10)

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
        assert_allclose(self.w.wcs.cd, frame.wcs.wcs.cd, rtol=1e-8)
        self.assertEqual(self.w.all_pix2world(pix_coord, 1)[0][0], frame.wcs.all_pix2world(pix_coord, 1)[0][0])
        self.assertEqual(self.w.all_pix2world(pix_coord, 1)[0][1], frame.wcs.all_pix2world(pix_coord, 1)[0][1])
        self.assertAlmostEqual(self.pixel_scale, proj_plane_pixel_scales(frame.wcs)[0], 10)
        self.assertAlmostEqual(self.pixel_scale, proj_plane_pixel_scales(frame.wcs)[1], 10)

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
        self.assertEqual(self.w.pixel_shape[0], frame.wcs.pixel_shape[0])
        self.assertEqual(self.w.pixel_shape[1], frame.wcs.pixel_shape[1])


class TestWCSField(TestCase):

    def setUp(self):
        pass

    def test_deconstruct_editable_default(self):

        instance_WCSField = WCSField()
        name, path, args, kwargs = instance_WCSField.deconstruct()
        new_instance = WCSField(*args, **kwargs)
        self.assertEqual(instance_WCSField.editable, new_instance.editable)

    def test_deconstruct_editable_force_true(self):

        instance_WCSField = WCSField(editable=True)
        name, path, args, kwargs = instance_WCSField.deconstruct()
        new_instance = WCSField(*args, **kwargs)
        self.assertEqual(instance_WCSField.editable, new_instance.editable)
        self.assertFalse(instance_WCSField.editable)
        self.assertFalse(new_instance.editable)

    def test_db_parameters_respects_db_type(self):
        f = WCSField()
        self.assertEqual(f.db_parameters(connection)['type'], 'text')


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
        params['elements_type'] = 'MPC_COMET'
        params['source_type'] = 'C'
        self.body_confirmed, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True,
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-07-13 21:20:00',
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        sblock_params = {
                         'body'     : self.body2,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-12-04 00:40:00',
                         'block_end'   : '2015-12-04 08:10:00',
                         'tracking_number' : '0000117781',
                         'active'   : False,
                       }
        self.test_sblock2 = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'lsc',
                         'body'     : self.body2,
                         'superblock' : self.test_sblock2,
                         'block_start' : '2015-12-04 00:40:00',
                         'block_end'   : '2015-12-04 08:10:00',
                         'request_number' : '0010117781',
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
                    'midpoint'      : datetime(2015, 7, 13, 21, 9, 51),
                    'block'         : self.test_block,
                    'fwhm'          : 1.0
                 }
        self.test_frame = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'R',
                    'frametype'     : Frame.STACK_FRAMETYPE,
                    'midpoint'      : datetime(2015, 12, 5, 1, 10, 49, int(0.9*1e6)),
                    'block'         : self.test_block,
                 }
        self.test_frame_stack = Frame.objects.create(**frame_params)

        frame_params = { 'sitecode'      : 'F65',
                         'instrument'    : 'ep02',
                         'filter'        : 'rp',
                         'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                         'extrainfo'     : 'MUSCAT_FAST',
                         'midpoint'      : datetime(2021, 11,12, 6, 10, 49, int(0.9*1e6)),
                         'block'         : self.test_block,
                         'astrometric_catalog' : "GAIA-DR2",
                         'photometric_catalog' : "GAIA-DR2",
                     }
        self.test_frame_extrainfo = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'C51',
                    'filter'        : 'R',
                    'frametype'     : Frame.SATELLITE_FRAMETYPE,
                    'midpoint'      : datetime(2016, 2, 8, 21, 24, 22, int(0.752*1e6)),
                    'block'         : None,
                    'extrainfo'     : '     N999r0q  s2016 02 08.89193 1 - 3471.6659 - 5748.3475 - 1442.3263        C51'
                 }
        self.test_frame_satellite = Frame.objects.create(**frame_params)

        frame_params = { 'sitecode': u'F51',
                         'block': None,
                         'exptime': None,
                         'extrainfo': None,
                         'filename': None,
                         'filter': u'w',
                         'frametype': Frame.NONLCO_FRAMETYPE,
                         'fwhm': None,
                         'instrument': None,
                         'midpoint': datetime(2017, 3, 7, 15, 29, 0, 960000),
                         'nstars_in_fit': None,
                         'quality': u' ',
                         'rms_of_fit': None,
                         'time_uncertainty': None,
                         'zeropoint': None,
                         'zeropoint_err': None}
        self.test_frame_nonLCO_F51 = Frame.objects.create(**frame_params)

        self.maxDiff = None

    def test_mpc_1(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  C2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
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
        expected_mpcline = '     N999r0q  C2015 07 13.88184000 30 00.00 -00 30 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_3(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "GAIA-DR1",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  C2015 07 13.88184000 30 00.00 -00 30 00.0          21.5 RU     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_4(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "GAIA-DR2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  C2015 07 13.88184000 30 00.00 -00 30 00.0          21.5 RV     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_extrainfo(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame_extrainfo,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "GAIA-DR2",
                            'photometric_catalog' : "GAIA-DR2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  C2021 11 12.25752200 30 00.00 -00 30 00.0          21.5 GV     F65'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_mpc_F51_no_filter_mapping(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame_nonLCO_F51,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "2MASS",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q  C2017 03 07.64515000 30 00.00 -00 30 00.0          21.5 wL     F51'
        mpc_line = measure.format_mpc_line(include_catcode=True)
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
        expected_mpcline = '     N999r0q KC2015 07 13.88184010 30 00.00 -32 45 00.0          20.7 Rt     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
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
        mpc_lines = measure.format_mpc_line(include_catcode=True)
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
        mpc_lines = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_lines)

    def test_discovery(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'flags' : '*',
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q* C2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_discovery_on_stacked(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'flags' : '*,K',
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q*KC2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_discovery_on_starlover(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'flags' : '*,I',
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q*IC2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_discovery_on_starlover_reversed_order(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'flags' : 'I,*',
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q*IC2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_discovery_on_twoflags(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'flags' : '*,K,I',
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q*KC2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_too_many_flags(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'flags' : 'K,I',
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q KC2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_discovery_and_too_many_flags(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'flags' : 'K,I,*',
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_mpcline = '     N999r0q*KC2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 Rq     K93'
        mpc_line = measure.format_mpc_line(include_catcode=True)
        self.assertEqual(expected_mpcline, mpc_line)

    def test_psv_1(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|157.500000 |-32.750000 |   UCAC4|21.5 |   R|   UCAC4|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_2(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 |   UCAC4|21.5 |   R|   UCAC4|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_3(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "GAIA-DR1",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 |   Gaia1|21.5 |   R|   Gaia1|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_4(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'astrometric_catalog' : "GAIA-DR2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 |   Gaia2|21.5 |   R|   Gaia2|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_nomag_1(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 220.5224583333333,
                            'obs_dec' : -13.814777777777778,
                            'obs_mag' : None,
                            'astrometric_catalog' : "GAIA-DR2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|220.522458 |-13.814778 |   Gaia2|     |    |        |     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_nomag_1(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 220.5224583333333,
                            'obs_dec' : -13.814777777777778,
                            'obs_mag' : None,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'astrometric_catalog' : "GAIA-DR2",
                            'photometric_catalog' : "GAIA-DR2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|220.522458 |-13.814778 | 0.14|  0.16|   Gaia2|     |      |    |        |      |      |1.0000|     |'

        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_1(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'astrometric_catalog' : "GAIA-DR2",
                            'photometric_catalog' : "GAIA-DR2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        """
                                   |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|     7.50000|    -0.50000|   Gaia2|21.5 |     R|   Gaia2|     |'
                                   |2019 GC6   |        | CCD|K91 |2019-04-17T17:20:52.34Z|  174.304775|  -44.161550| 0.14|  0.16|   Gaia2|13.9 |  0.01|   G|   Gaia2|  1.56|1.3945|1.0000|     |
        """
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 | 0.14|  0.16|   Gaia2|21.5 |0.12  |   R|   Gaia2|      |      |1.0000|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_2(self):
        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'aperture_size' : 1.56,
                            'snr' : 24.8,
                            'astrometric_catalog' : "GAIA-DR2",
                            'photometric_catalog' : "GAIA-DR2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        """
                                   |           | N999r0q| CCD|K93 |    |2015-07-13T21:09:51.00Z|     7.50000|    -0.50000|   Gaia2|21.5 |     R|   Gaia2|     |'
                                   |2019 GC6   |        | CCD|K91 |    |2019-04-17T17:20:52.34Z|  174.304775|  -44.161550| 0.14|  0.16|   Gaia2|13.9 |  0.01|   G|   Gaia2|  1.56|1.3945|1.0000|     |
        """
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 | 0.14|  0.16|   Gaia2|21.5 |0.12  |   R|   Gaia2|  1.56|1.3945|1.0000|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_3(self):

        # Add an astrometric fit RMS to the Frame.
        self.test_frame.rms_of_fit = 0.3
        self.test_frame.save()

        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'aperture_size' : 1.56,
                            'snr' : 24.8,
                            'astrometric_catalog' : "2MASS",
                            'photometric_catalog' : "UCAC-4",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 | 0.33|  0.34|   2MASS|21.5 |0.12  |   R|   UCAC4|  1.56|1.3945|1.0000|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_4(self):

        # Add an astrometric fit RMS to the Frame.
        self.test_frame.rms_of_fit = 0.3
        self.test_frame.save()

        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'aperture_size' : 1.56,
                            'snr' : 24.8,
                            'astrometric_catalog' : "GAIA-DR3",
                            'photometric_catalog' : "GAIA-DR3",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 | 0.33|  0.34|   Gaia3|21.5 |0.12  |   R|   Gaia3|  1.56|1.3945|1.0000|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_5(self):

        # Add an astrometric fit RMS to the Frame.
        self.test_frame.rms_of_fit = 0.3
        self.test_frame.astrometric_catalog = "GAIA-DR3"
        self.test_frame.photometric_catalog = "ATLAS-2"
        self.test_frame.save()

        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'aperture_size' : 1.56,
                            'snr' : 24.8,
                            'astrometric_catalog' : "GAIA-DR3",
                            'photometric_catalog' : "ATLAS-2",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 | 0.33|  0.34|   Gaia3|21.5 |0.12  |   R|  ATLAS2|  1.56|1.3945|1.0000|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_6(self):

        # Add an astrometric fit RMS to the Frame.
        self.test_frame.rms_of_fit = 0.3
        self.test_frame.astrometric_catalog = "GAIA-DR2"
        self.test_frame.photometric_catalog = "PS1"
        self.test_frame.save()

        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'aperture_size' : 1.56,
                            'snr' : 24.8,
                            'astrometric_catalog' : "GAIA-DR2",
                            'photometric_catalog' : "PS1",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 | 0.33|  0.34|   Gaia2|21.5 |0.12  |   R| PS1_DR1|  1.56|1.3945|1.0000|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)

    def test_psv_rms_7(self):

        # Add an astrometric fit RMS to the Frame.
        self.test_frame.rms_of_fit = 0.3
        self.test_frame.astrometric_catalog = "GAIA-DR2"
        self.test_frame.photometric_catalog = "PS2"
        self.test_frame.save()

        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 7.5,
                            'obs_dec' : -00.5,
                            'obs_mag' : 21.5,
                            'err_obs_ra' : 0.14/3600.0,
                            'err_obs_dec': 0.16/3600.0,
                            'err_obs_mag' : 0.12,
                            'aperture_size' : 1.56,
                            'snr' : 24.8,
                            'astrometric_catalog' : "GAIA-DR2",
                            'photometric_catalog' : "PS1",
                         }

        measure = SourceMeasurement.objects.create(**measure_params)
        expected_psvline = '       |           | N999r0q| CCD|K93 |2015-07-13T21:09:51.00Z|  7.500000 | -0.500000 | 0.33|  0.34|   Gaia2|21.5 |0.12  |   R| PS1_DR2|  1.56|1.3945|1.0000|     |'
        psv_line = measure.format_psv_line()
        self.assertEqual(expected_psvline, psv_line)


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
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True,
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'request_number' : '10042',
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
                    'midpoint'      : datetime(2015, 7, 13, 21, 9, 51),
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
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True,
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-07-13 18:00:00',
                         'block_end'   : '2015-07-14 03:00:00',
                         'request_number' : '10042',
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
                    'midpoint'      : datetime(2015, 7, 13, 21, 9, 51),
                    'block'         : self.test_block,
                 }
        self.test_frame = Frame.objects.create(**frame_params)

        # Pylint can go to hell...
        self.dtypes =\
             {  'names' : ('det_number', 'frame_number', 'sext_number', 'jd_obs', 'ra', 'dec', 'x', 'y', 'mag', 'fwhm', 'elong', 'theta', 'rmserr', 'deltamu', 'area', 'score', 'velocity', 'sky_pos_angle', 'pixels_frame', 'streak_length'),
                'formats' : ('i4',       'i1',           'i4',          'f8',     'f8', 'f8', 'f4', 'f4', 'f4', 'f4',   'f4',    'f4',    'f4',     'f4',       'i4',   'f4',   'f4',       'f4',        'f4',           'f4' )
             }

        self.dets_array = array([(1, 1, 3283, 2457444.656045, 10.924317, 39.27700, 2103.245, 2043.026, 19.26, 12.970, 1.764, -60.4, 0.27, 1.39, 34, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 2,    0, 2457444.657980, 10.924298, 39.27793, 2103.468, 2043.025,  0.00,  1.000, 1.000,   0.0, 0.27, 0.00,  0, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 3, 3409, 2457444.659923, 10.924271, 39.27887, 2104.491, 2043.034, 19.20, 11.350, 1.373, -57.3, 0.27, 1.38, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 4, 3176, 2457444.661883, 10.924257, 39.27990, 2104.191, 2043.844, 19.01, 10.680, 1.163, -41.5, 0.27, 1.52, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 5, 3241, 2457444.663875, 10.924237, 39.28087, 2104.365, 2043.982, 19.17, 12.940, 1.089, -31.2, 0.27, 1.27, 55, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 6, 3319, 2457444.665812, 10.924220, 39.28172, 2104.357, 2043.175, 18.82, 12.910, 1.254, -37.8, 0.27, 1.38, 69, 1.10, 0.497, 0.2, 9.0, 6.7),],
                                dtype=self.dtypes)

        self.dets_byte_array = self.dets_array.tostring()
        cand_params = { 'block'  : self.test_block,
                        'cand_id' : 1,
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

    def test_basic_byte_array(self):
        # Created with python2.7+numpy1.14 venv, 'b' prefix added for python3
        expected_bytes = b'\x01\x00\x00\x00\x01\xd3\x0c\x00\x00VH\xf9S\xb2\xbfBA\x0fF\xec\x13@\xd9%@\xfa~j\xbct\xa3C@\xecs\x03E\xd5`\xffD{\x14\x9aA\x1f\x85OA\xc1\xca\xe1?\x9a\x99q\xc2q=\x8a>\x85\xeb\xb1?"\x00\x00\x00\xcd\xcc\x8c?\xc9v\xfe>\xcd\xccL>\x00\x00\x10Aff\xd6@\x01\x00\x00\x00\x02\x00\x00\x00\x00K\xb08T\xb2\xbfBA4\x84c\x96=\xd9%@\xe4I\xd25\x93\xa3C@}w\x03E\xcd`\xffD\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x80?\x00\x00\x00\x00q=\x8a>\x00\x00\x00\x00\x00\x00\x00\x00\xcd\xcc\x8c?\xc9v\xfe>\xcd\xccL>\x00\x00\x10Aff\xd6@\x01\x00\x00\x00\x03Q\r\x00\x00[[xT\xb2\xbfBAMHk\x0c:\xd9%@\xf2\xea\x1c\x03\xb2\xa3C@\xdb\x87\x03E\x17a\xffD\x9a\x99\x99A\x9a\x995Aw\xbe\xaf?33e\xc2q=\x8a>\xd7\xa3\xb0?4\x00\x00\x00\xcd\xcc\x8c?\xc9v\xfe>\xcd\xccL>\x00\x00\x10Aff\xd6@\x01\x00\x00\x00\x04h\x0c\x00\x00\x07\x95\xb8T\xb2\xbfBA\xba2\xa868\xd9%@@\x13a\xc3\xd3\xa3C@\x0e\x83\x03E\x02{\xffD{\x14\x98AH\xe1*A/\xdd\x94?\x00\x00&\xc2q=\x8a>\\\x8f\xc2?4\x00\x00\x00\xcd\xcc\x8c?\xc9v\xfe>\xcd\xccL>\x00\x00\x10Aff\xd6@\x01\x00\x00\x00\x05\xa9\x0c\x00\x00#\xdb\xf9T\xb2\xbfBA\x9d\x81\x91\x975\xd9%@\xb96T\x8c\xf3\xa3C@\xd7\x85\x03Em\x7f\xffD)\\\x99A=\nOAZd\x8b?\x9a\x99\xf9\xc1q=\x8a>\\\x8f\xa2?7\x00\x00\x00\xcd\xcc\x8c?\xc9v\xfe>\xcd\xccL>\x00\x00\x10Aff\xd6@\x01\x00\x00\x00\x06\xf7\x0c\x00\x00\xdfS9U\xb2\xbfBAE\x9e$]3\xd9%@\x87P\xa5f\x0f\xa4C@\xb6\x85\x03E\x9ae\xffD\\\x8f\x96A\\\x8fNA\x12\x83\xa0?33\x17\xc2q=\x8a>\xd7\xa3\xb0?E\x00\x00\x00\xcd\xcc\x8c?\xc9v\xfe>\xcd\xccL>\x00\x00\x10Aff\xd6@'

        self.assertEqual(self.dets_byte_array, expected_bytes)

    def test_unpack_memoryview(self):
        new_dets_array = frombuffer(memoryview(self.dets_byte_array), dtype=self.dtypes)

        self.assertEqual(type(self.dets_array), type(new_dets_array))
        for frame in arange(self.dets_array.shape[0]):
            for column in self.dets_array.dtype.names:
                self.assertAlmostEqual(self.dets_array[column][frame], new_dets_array[column][frame], 7)

    def test_unpack_dets_array_memoryview(self):
        self.test_candidate.detections =  memoryview(self.dets_byte_array)
        new_dets_array = self.test_candidate.unpack_dets()

        self.assertEqual(type(self.dets_array), type(new_dets_array))
        for frame in arange(self.dets_array.shape[0]):
            for column in self.dets_array.dtype.names:
                self.assertAlmostEqual(self.dets_array[column][frame], new_dets_array[column][frame], 7)

    def test_unpack_dets_array(self):
        new_dets_array = self.test_candidate.unpack_dets()

        self.assertEqual(type(self.dets_array), type(new_dets_array))
        for frame in arange(self.dets_array.shape[0]):
            for column in self.dets_array.dtype.names:
                self.assertAlmostEqual(self.dets_array[column][frame], new_dets_array[column][frame], 7)
