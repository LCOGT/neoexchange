import json
from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient

from core.models import Proposal, ProposalPermission, SuperBlock, Block, Frame
from mock import patch
from neox.tests.mocks import mock_lco_authenticate

# Import modules to test
from core.viewsets import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)

class ProposalAPITest(TestCase):
    base_url = '/api/proposals/{}/'

    def test_get_returns_json_200(self):
        test_proposal = Proposal.objects.create()
        response = self.client.get(self.base_url.format(test_proposal.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_returns_correct_proposal(self):
        eng_proposal_params = { 'code'  : 'LCOEngineering',
                                'title' : 'LCOGT Engineering'
                              }
        eng_proposal = Proposal.objects.create(**eng_proposal_params)
        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
        }
        neo_proposal = Proposal.objects.create(**neo_proposal_params)
        response = self.client.get(self.base_url.format(neo_proposal.id))
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
                {'code' : 'LCO2015A-009',
                 'title' : 'LCOGT NEO Follow-up Network',
                 'pi' : "",
                 'tag' : 'LCOGT',
                 'active' : True,
                 'time_critical' : False,
                 'download' : True
                 }
        )

    def test_returns_download_only_proposal(self):
        eng_proposal_params = { 'code'  : 'LCOEngineering',
                                'title' : 'LCOGT Engineering',
                                'download' : False
                              }
        eng_proposal = Proposal.objects.create(**eng_proposal_params)
        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network',
                                'download' : True
        }
        neo_proposal = Proposal.objects.create(**neo_proposal_params)
        response = self.client.get(self.base_url.format(None).replace('None/',''))
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            {
                'count' : 1,
                'next'  : None,
                'previous' : None,
                'results' : [
                    {'code' : 'LCO2015A-009',
                     'title' : 'LCOGT NEO Follow-up Network',
                     'pi' : "",
                     'tag' : 'LCOGT',
                     'active' : True,
                     'time_critical' : False,
                     'download' : True
                     }
                ]
            }
        )

class BaseViewTest(APITestCase):

    def setUp(self):
        self.bart = User.objects.create_user(
            username='bart',
            password='simpson',
            email='bart@simpson.org',
            first_name = 'Bart',
            last_name = 'Simpson',
            is_active = 1
        )
        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        test_proposal_params = { 'code'  : 'LCOEngineering',
                                 'title' : 'Test Proposal'
                               }
        self.test_proposal, created = Proposal.objects.get_or_create(**test_proposal_params)
        pp = ProposalPermission.objects.create(proposal=self.test_proposal, user=self.bart)
        sblock_params = {
                            'proposal' : self.test_proposal,
                        }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        self.test_block = Block.objects.create(superblock=self.test_sblock, proposal=self.test_proposal)

        self.maxDiff = None

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login(self):
        self.assertTrue(self.client.login(username='bart', password='simpson'))


class FrameAPITest(BaseViewTest):
    base_url = '/api/frames/{}/'
    query_url = '/api/frames/?filename={}&frametype={}'

    def test_get_returns_json_200_for_nonLCO(self):
        frame_params = {
                        'sitecode' : 'G96',
                        'midpoint' : datetime(2019,4,20,19,30,0),
                        'filter'   : 'V',
                        'frametype': Frame.NONLCO_FRAMETYPE
                       }
        test_frame = Frame.objects.create(**frame_params)
        response = self.client.get(self.base_url.format(test_frame.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_get_returns_json_404_for_LCO(self):
        frame_params = {
                        'sitecode' : 'K91',
                        'filename' : 'cpt1m010-fa16-20190330-0129-e91.fits',
                        'midpoint' : datetime(2019,4,20,19,30,0),
                        'filter'   : 'w',
                        'frametype': Frame.BANZAI_RED_FRAMETYPE
                       }
        test_frame = Frame.objects.create(**frame_params)
        response = self.client.get(self.base_url.format(test_frame.id))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['content-type'], 'application/json')

    def test_get_returns_details_for_nonLCO(self):
        frame_params = {
                        'sitecode' : 'G96',
                        'midpoint' : datetime(2019, 6, 15, 10, 23, 2),
                        'filter'   : 'G',
                        'frametype': Frame.NONLCO_FRAMETYPE
                       }
        test_frame = Frame.objects.create(**frame_params)
        response = self.client.get(self.base_url.format(test_frame.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            {
                "astrometric_catalog": " ",
                "block": None,
                "exptime": None,
                "extrainfo": None,
                "filename": None,
                "filter": "G",
                "frameid": None,
                "frametype": 2,
                "fwhm": None,
                "id": 1,
                "instrument": None,
                "midpoint": "2019-06-15T10:23:02",
                "nstars_in_fit": None,
                "photometric_catalog": " ",
                "quality": " ",
                "rms_of_fit": None,
                "sitecode": "G96",
                "time_uncertainty": None,
                "zeropoint": None,
                "zeropoint_err": None
            }
        )

    def test_get_for_LCO_data(self):
        self.login()
        frame_params = {
                        'sitecode' : 'K91',
                        'filename' : 'cpt1m010-fa16-20190330-0129-e91.fits',
                        'midpoint' : datetime(2019,4,20,19,30,0),
                        'filter'   : 'w',
                        'frametype': Frame.BANZAI_RED_FRAMETYPE,
                        'block'    : self.test_block
                       }
        test_frame = Frame.objects.create(**frame_params)
        response = self.client.get(self.base_url.format(test_frame.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            {
                "astrometric_catalog": " ",
                "block": 1,
                "exptime": None,
                "extrainfo": None,
                "filename": 'cpt1m010-fa16-20190330-0129-e91.fits',
                "filter": "w",
                "frameid": None,
                "frametype": 91,
                "fwhm": None,
                "id": 1,
                "instrument": None,
                "midpoint": "2019-04-20T19:30:00",
                "nstars_in_fit": None,
                "photometric_catalog": " ",
                "quality": " ",
                "rms_of_fit": None,
                "sitecode": "K91",
                "time_uncertainty": None,
                "zeropoint": None,
                "zeropoint_err": None
            }
        )

    def test_find_frame_by_filename(self):
        self.login()
        frame_params = {
                        'sitecode' : 'K91',
                        'filename' : 'cpt1m010-fa16-20190330-0129-e91.fits',
                        'midpoint' : datetime(2019,4,20,19,30,0),
                        'filter'   : 'w',
                        'frametype': Frame.BANZAI_RED_FRAMETYPE,
                        'block'    : self.test_block
                       }
        test_frame = Frame.objects.create(**frame_params)
        frame_params['filename'] = 'cpt1m010-fa16-20190330-0130-e91.fits'
        frame_params['midpoint'] = datetime(2019,4,20,19,31,0)
        test_frame2 = Frame.objects.create(**frame_params)

        response = self.client.get(self.query_url.format(test_frame2.filename, ''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "astrometric_catalog": " ",
                    "block": 1,
                    "exptime": None,
                    "extrainfo": None,
                    "filename": 'cpt1m010-fa16-20190330-0130-e91.fits',
                    "filter": "w",
                    "frameid": None,
                    "frametype": 91,
                    "fwhm": None,
                    "id": 2,
                    "instrument": None,
                    "midpoint": "2019-04-20T19:31:00",
                    "nstars_in_fit": None,
                    "photometric_catalog": " ",
                    "quality": " ",
                    "rms_of_fit": None,
                    "sitecode": "K91",
                    "time_uncertainty": None,
                    "zeropoint": None,
                    "zeropoint_err": None
                }
            ]
        })

    def test_find_frame_by_frametype(self):
        self.login()
        frame_params = {
                        'sitecode' : 'K91',
                        'filename' : 'cpt1m010-fa16-20190330-0129-e91.fits',
                        'midpoint' : datetime(2019,4,20,19,30,0),
                        'filter'   : 'w',
                        'frametype': Frame.BANZAI_RED_FRAMETYPE,
                        'block'    : self.test_block
                       }
        test_frame = Frame.objects.create(**frame_params)
        frame_params['filename'] = 'cpt1m010-fa16-20190330-0129-e91_ldac.fits'
        frame_params['frametype'] = Frame.BANZAI_LDAC_CATALOG
        test_frame2 = Frame.objects.create(**frame_params)

        response = self.client.get(self.query_url.format('', test_frame2.frametype))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "astrometric_catalog": " ",
                    "block": 1,
                    "exptime": None,
                    "extrainfo": None,
                    "filename": 'cpt1m010-fa16-20190330-0129-e91_ldac.fits',
                    "filter": "w",
                    "frameid": None,
                    "frametype": 6,
                    "fwhm": None,
                    "id": 2,
                    "instrument": None,
                    "midpoint": "2019-04-20T19:30:00",
                    "nstars_in_fit": None,
                    "photometric_catalog": " ",
                    "quality": " ",
                    "rms_of_fit": None,
                    "sitecode": "K91",
                    "time_uncertainty": None,
                    "zeropoint": None,
                    "zeropoint_err": None
                }
            ]
        })

    def test_find_frame_by_filename_and_frametype(self):
        self.login()
        frame_params = {
                        'sitecode' : 'K91',
                        'filename' : 'cpt1m010-fa16-20190330-0129-e91.fits',
                        'midpoint' : datetime(2019,4,20,19,30,0),
                        'filter'   : 'w',
                        'frametype': Frame.BANZAI_RED_FRAMETYPE,
                        'block'    : self.test_block
                       }
        test_frame = Frame.objects.create(**frame_params)
        frame_params['filename'] = 'cpt1m010-fa16-20190330-0130-e91.fits'
        frame_params['midpoint'] = datetime(2019,4,20,19,31,0)
        test_frame3 = Frame.objects.create(**frame_params)
        frame_params['filename'] = 'cpt1m010-fa16-20190330-0130-e91_ldac.fits'
        frame_params['frametype'] = Frame.BANZAI_LDAC_CATALOG
        test_frame3 = Frame.objects.create(**frame_params)

        response = self.client.get(self.query_url.format(test_frame3.filename, test_frame3.frametype))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "astrometric_catalog": " ",
                    "block": 1,
                    "exptime": None,
                    "extrainfo": None,
                    "filename": 'cpt1m010-fa16-20190330-0130-e91_ldac.fits',
                    "filter": "w",
                    "frameid": None,
                    "frametype": 6,
                    "fwhm": None,
                    "id": 3,
                    "instrument": None,
                    "midpoint": "2019-04-20T19:31:00",
                    "nstars_in_fit": None,
                    "photometric_catalog": " ",
                    "quality": " ",
                    "rms_of_fit": None,
                    "sitecode": "K91",
                    "time_uncertainty": None,
                    "zeropoint": None,
                    "zeropoint_err": None
                }
            ]
        })
