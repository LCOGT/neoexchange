'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2017-2017 LCOGT

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

from neox.tests.mocks import MockDateTime
from core.models import Body, Proposal, Block, Frame, SourceMeasurement

#Import module to test
from core.mpc_submit import *

class Test_Generate_Message(TestCase):

    def setUp(self):

        # Initialise with a test body, proposal, block, frames and sourcemeasurement
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

        block_params = { 'telclass' : '0m4',
                         'site'     : 'tfn',
                         'body'     : self.body2,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-12-04 00:40:00',
                         'block_end'   : '2015-12-04 08:10:00',
                         'tracking_number' : '0000117782',
                         'num_exposures' : 30,
                         'exp_length' : 120.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'when_observed' : '2015-12-04 07:03:00',
                         'reported' : False
                       }
        self.test_block3 = Block.objects.create(**block_params)

        block_params = { 'telclass' : '2m0',
                         'site'     : 'ogg',
                         'body'     : self.body2,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-12-25 05:40:00',
                         'block_end'   : '2015-12-04 14:10:00',
                         'tracking_number' : '0000117783',
                         'num_exposures' :  5,
                         'exp_length' : 120.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'when_observed' : '2015-12-25 10:03:00',
                         'reported' : False
                       }
        self.test_block4 = Block.objects.create(**block_params)

        frame_params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                    'filename'      : 'cpt1m012-kb75-20150713-0130-e91.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : datetime(2015,07,13,21,9,51),
                    'block'         : self.test_block,
                    'astrometric_catalog' : "UCAC-4"
                 }
        self.test_frame = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'W86',
                    'instrument'    : 'fl03',
                    'filter'        : 'R',
                    'frametype'     : Frame.STACK_FRAMETYPE,
                    'midpoint'      : datetime(2015,12,05,01,10,49,int(0.9*1e6)),
                    'block'         : self.test_block2,
                    'astrometric_catalog' : "2MASS",
                 }
        self.test_frame_stack = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'Z21',
                    'instrument'    : 'kb29',
                    'filter'        : 'w',
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                    'midpoint'      : datetime(2015,12,05,01,10,49,int(0.9*1e6)),
                    'block'         : self.test_block3,
                    'astrometric_catalog' : "2MASS",
                 }
        self.test_frame_point4m = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'F65',
                    'instrument'    : 'fs02',
                    'filter'        : 'solar',
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                    'midpoint'      : datetime(2015,12,05,9,50,49),
                    'block'         : self.test_block4,
                    'astrometric_catalog' : "PPMXL",
                 }
        self.test_frame_twom = Frame.objects.create(**frame_params)

        frame_params = {  'sitecode'      : 'C51',
                    'filter'        : 'R',
                    'frametype'     : Frame.SATELLITE_FRAMETYPE,
                    'midpoint'      : datetime(2016,2,8,21,24,22,int(0.752*1e6)),
                    'block'         : None,
                    'extrainfo'     : '     N999r0q  s2016 02 08.89193 1 - 3471.6659 - 5748.3475 - 1442.3263        C51'
                 }
        self.test_frame_satellite = Frame.objects.create(**frame_params)

        measure_params = {  'body' : self.body,
                            'frame' : self.test_frame,
                            'obs_ra' : 157.5,
                            'obs_dec' : -32.75,
                            'obs_mag' : 21.5,
                         }

        measure = SourceMeasurement.objects.create(**measure_params)

        measure_params['body'] = self.body2
        measure_params['frame'] = self.test_frame_stack
        measure_params['flags'] = 'K'
        measure_params['obs_dec'] = +0.66
        measure = SourceMeasurement.objects.create(**measure_params)

        measure_params = {  'body' : self.body2,
                            'frame' : self.test_frame_point4m,
                            'obs_ra' : 7.6,
                            'obs_dec' : 32.755,
                            'obs_mag' : 20.5,
                         }

        measure = SourceMeasurement.objects.create(**measure_params)

        measure_params = {  'body' : self.body2,
                            'frame' : self.test_frame_twom,
                            'obs_ra' : 7.6,
                            'obs_dec' : 32.755,
                            'obs_mag' : 20.7,
                         }

        measure = SourceMeasurement.objects.create(**measure_params)

        self.maxDiff = None

    def test_K93(self):

        expected_message = (u'COD K93\n'
                            u'CON LCO, 6740 Cortona Drive Suite 102, Goleta, CA 93117\n'
                            u'CON [tlister@lco.global]\n'
                            u'OBS T. Lister, S. Greenstreet, E. Gomez\n'
                            u'MEA T. Lister\n'
                            u'TEL 1.0-m f/8 Ritchey-Chretien + CCD\n'
                            u'ACK N999r0q_K93_kb75\n'
                            u'COM LCO CPT Node 1m0 Dome C at Sutherland, South Africa\n'
                            u'AC2 tlister@lco.global,sgreenstreet@lco.global\n'
                            u'NET UCAC-4\n'
                            u'BND R\n'
                            u'     N999r0q  C2015 07 13.88184010 30 00.00 -32 45 00.0          21.5 w      K93\n')
        message = generate_message(self.test_block.id)

        i = 0
        expected_lines = expected_message.split('\n')
        message_lines = message.split('\n')
        while i < len(expected_lines):
            self.assertEqual(expected_lines[i], message_lines[i])
            i += 1

        self.assertEqual(expected_message, message)

    def test_W86(self):

        expected_message = (u'COD W86\n'
                            u'CON LCO, 6740 Cortona Drive Suite 102, Goleta, CA 93117\n'
                            u'CON [tlister@lco.global]\n'
                            u'OBS T. Lister, S. Greenstreet, E. Gomez\n'
                            u'MEA T. Lister\n'
                            u'TEL 1.0-m f/8 Ritchey-Chretien + CCD\n'
                            u'ACK 2015 XS54_W86_fl03\n'
                            u'COM LCO LSC Node 1m0 Dome B at Cerro Tololo, Chile\n'
                            u'AC2 tlister@lco.global,sgreenstreet@lco.global\n'
                            u'NET UCAC-4\n'
                            u'BND R\n'
                            u'     K15X54S KC2015 12 05.04918910 30 00.00 +00 39 36.0          21.5 R      W86\n')
        message = generate_message(self.test_block2.id)

        i = 0
        expected_lines = expected_message.split('\n')
        message_lines = message.split('\n')
        while i < len(expected_lines):
            self.assertEqual(expected_lines[i], message_lines[i])
            i += 1

        self.assertEqual(expected_message, message)

    def test_Z21(self):

        expected_message = (u'COD Z21\n'
                            u'CON LCO, 6740 Cortona Drive Suite 102, Goleta, CA 93117\n'
                            u'CON [tlister@lco.global]\n'
                            u'OBS T. Lister, S. Greenstreet, E. Gomez\n'
                            u'MEA T. Lister\n'
                            u'TEL 0.4-m f/8 Schmidt-Cassegrain + CCD\n'
                            u'ACK 2015 XS54_Z21_kb29\n'
                            u'COM LCO TFN Node Aqawan A 0m4a at Tenerife, Spain\n'
                            u'AC2 tlister@lco.global,sgreenstreet@lco.global\n'
                            u'NET 2MASS\n'
                            u'BND R\n'
                            u'     K15X54S  C2015 12 05.04918900 30 24.00 +32 45 18.0          20.5 w      Z21\n')
        message = generate_message(self.test_block3.id)

        i = 0
        expected_lines = expected_message.split('\n')
        message_lines = message.split('\n')
        while i < len(expected_lines):
            self.assertEqual(expected_lines[i], message_lines[i])
            i += 1

        self.assertEqual(expected_message, message)

    def test_F65(self):

        expected_message = (u'COD F65\n'
                            u'CON LCO, 6740 Cortona Drive Suite 102, Goleta, CA 93117\n'
                            u'CON [tlister@lco.global]\n'
                            u'OBS T. Lister, S. Greenstreet, E. Gomez\n'
                            u'MEA T. Lister\n'
                            u'TEL 2.0-m f/10 Ritchey-Chretien + CCD\n'
                            u'ACK 2015 XS54_F65_fs02\n'
                            u'COM LCO OGG Node 2m0 FTN at Haleakala, Maui\n'
                            u'AC2 tlister@lco.global,sgreenstreet@lco.global\n'
                            u'NET PPMXL\n'
                            u'BND R\n'
                            u'     K15X54S  C2015 12 05.41028900 30 24.00 +32 45 18.0          20.7 R      F65\n')
        message = generate_message(self.test_block4.id)

        i = 0
        expected_lines = expected_message.split('\n')
        message_lines = message.split('\n')
        while i < len(expected_lines):
            self.assertEqual(expected_lines[i], message_lines[i])
            i += 1

        self.assertEqual(expected_message, message)
