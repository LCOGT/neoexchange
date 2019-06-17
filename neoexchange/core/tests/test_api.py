import json

from django.test import TestCase

from core.models import Proposal

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
