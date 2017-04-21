'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from mock import patch
from django.test import TestCase
from django.core.urlresolvers import reverse

from neox.tests.mocks import MockCandidate
#Import module to test
from analyser.views import *
from core.models import Body, Block, SourceMeasurement, Proposal

class Test_Analyser(TestCase):

    def setUp(self):
        neo_proposal_params = { 'code'  : 'LCO2016B-001',
        'title' : 'LCO NEO Follow-up Network'
        }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)
        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2016-03-19 00:00:00',
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
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2017-01-01 13:00:00',
                         'block_end'   : '2017-02-01 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : None,
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'file1.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2017-01-01 21:09:51',
                    'block'         : self.test_block,
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                    'frameid'       : 1
                 }
        self.frame1 = Frame.objects.create(**params)
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'file2.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2017-01-01 21:20:00',
                    'block'         : self.test_block,
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                    'frameid'       : 2
                 }
        self.frame2 = Frame.objects.create(**params)


    @patch('analyser.views.Candidate.objects.get', MockCandidate)
    def test_source_meas_created(self):
        sources1 = SourceMeasurement.objects.filter(frame__block=self.test_block).count()
        self.assertEqual(sources1,0)
        resp = analyser_to_source_measurement(self.test_block, [1,2], 2)
        self.assertTrue(resp)
        sources2 = SourceMeasurement.objects.filter(frame__block=self.test_block).count()
        self.assertEqual(sources2,2)

    @patch('analyser.views.Candidate.objects.get', MockCandidate)
    def test_source_meas_updated(self):
        params1 = {
            'body'   : self.body,
            'frame'  : self.frame1,
            'obs_ra' : 10.1,
            'obs_dec': 10.2,
            'aperture_size' : 1
        }
        sm1 = SourceMeasurement.objects.create(**params1)
        params2 = {
            'body'   : self.body,
            'frame'  : self.frame2,
            'obs_ra' : 10.15,
            'obs_dec': 10.25,
            'aperture_size' : 1
        }
        sm2 = SourceMeasurement.objects.create(**params2)

        sources1 = SourceMeasurement.objects.filter(frame__block=self.test_block)
        self.assertEqual(sources1.count(),2)
        self.assertEqual(sources1[0].obs_ra, 10.1)
        resp = analyser_to_source_measurement(self.test_block, [1,2], 1)
        self.assertTrue(resp)
        sources2 = SourceMeasurement.objects.filter(frame__block=self.test_block)
        self.assertEqual(sources2.count(),2)
        self.assertEqual(sources2[0].obs_ra, 22.753496)

    def test_url_reverses(self):
        submit_url = reverse('block-submit-mpc', kwargs={'pk':self.test_block.pk, 'source':2})
        analyser_url = reverse('block-ast', kwargs={'pk':self.test_block.pk})
        analyser_submit_url = reverse('submit-candidates', kwargs={'pk':self.test_block.pk})
        self.assertEqual(submit_url,'/block/1/source/2/report/submit/')
        self.assertEqual(analyser_url,'/block/1/analyser/')
        self.assertEqual(analyser_submit_url,'/block/1/analyser/submit/')
