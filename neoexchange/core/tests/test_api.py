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
