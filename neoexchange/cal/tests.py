from django.test import TestCase
from mock import patch

from core.models import Body, SuperBlock, Proposal, Block
from neox.tests.mocks import mock_fetch_arecibo_calendar_targets

class CalNeoxApiTest(TestCase):

    def setUp(self):
        params = {  'name' : 'N999r0q',
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
                    'origin'        : 'G',
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
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

    def test_neox_blocks(self):
        response = self.client.get('/api/neox/?start=2015-04-18T13:00:00&end=2015-04-22T13:00:00')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            [{
            'title': "N999r0q",
            'start': '2015-04-20T13:00:00',
            'end': '2015-04-21T03:00:00',
            'url': "/block/1/"
            }]
        )

    def test_neox_blocks_noblock(self):
        response = self.client.get('/api/neox/')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            []
        )


class CalAreciboApiTest(TestCase):

    def setUp(self):
        self.maxDiff = None

    @patch('cal.views.fetch_arecibo_calendar_targets', mock_fetch_arecibo_calendar_targets)
    def test_low_uncertainty(self):
        response = self.client.get('/api/arecibo/')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
             [ {"title": "2020 RY",
                 "start": "2020-09-03T01:17:00",
                 "end": "2020-09-03T03:06:00",
                 "borderColor": "red"
                },
                {"title": "2020 RK",
                 "start": "2020-09-03T01:29:00",
                 "end": "2020-09-03T03:56:00"
                }
              ]
        )
