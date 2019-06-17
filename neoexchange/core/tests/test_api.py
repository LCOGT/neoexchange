import json
from datetime import datetime

from django.test import TestCase

from core.models import Proposal, Frame

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
            [
                {'code' : 'LCO2015A-009',
                 'title' : 'LCOGT NEO Follow-up Network',
                 'pi' : "",
                 'tag' : 'LCOGT',
                 'active' : True,
                 'time_critical' : False,
                 'download' : True
                 }
            ]
        )

class FrameAPITest(TestCase):
    base_url = '/api/frames/{}/'

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
