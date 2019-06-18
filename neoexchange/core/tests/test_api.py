import json
from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient

from core.models import Proposal, ProposalPermission, SuperBlock, Block, Frame, CatalogSources
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
        self.sblock_params = {
                            'proposal' : self.test_proposal,
                        }
        self.test_sblock = SuperBlock.objects.create(**self.sblock_params)
        self.block_params = { 'superblock' : self.test_sblock,
                              'proposal' :  self.test_proposal,
                              'obstype' : Block.OPT_IMAGING,
                              'num_exposures' : 42,
                            }
        self.test_block = Block.objects.create(**self.block_params)

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


class BlockAPITest(BaseViewTest):
    base_url = '/api/blocks/{}/'
    query_url = '/api/blocks/?tracking_number={}&obstype={}'

    def test_get_returns_json_200(self):
        self.login()
        response = self.client.get(self.base_url.format(self.test_block.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_anonymous_get_returns_json_200(self):
        response = self.client.get(self.base_url.format(self.test_block.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_get_for_LCO_data(self):
        self.login()
        response = self.client.get(self.base_url.format(self.test_block.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            {
                    "active": False,
                    "block_end": None,
                    "block_start": None,
                    "body": None,
                    "calibsource": None,
                    "exp_length" : None,
                    "groupid": None,
                    "id": 1,
                    "num_exposures": 42,
                    "num_observed": None,
                    "obstype": 0,
                    "proposal": self.test_proposal.id,
                    "reported": False,
                    "site": None,
                    "superblock": self.test_sblock.id,
                    "telclass": '1m0',
                    "tracking_number": None,
                    "when_observed": None,
                    "when_reported": None,
            }
        )

    def test_find_blocks_by_superblock(self):
        self.login()
        self.sblock_params['tracking_number'] = '0420'
        test_sblock2 = SuperBlock.objects.create(**self.sblock_params)
        self.block_params['block_start'] = datetime(2019,4,20,16,00,0)
        self.block_params['block_end'] = datetime(2019,4,21, 3,30,0)
        self.block_params['superblock'] = test_sblock2
        test_block2 = Block.objects.create(**self.block_params)

        response = self.client.get(self.query_url.format(test_block2.superblock.tracking_number, ''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        foo = json.loads(response.content.decode('utf8'))
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "active": False,
                    "block_end": "2019-04-21T03:30:00",
                    "block_start": "2019-04-20T16:00:00",
                    "body": None,
                    "calibsource": None,
                    "exp_length" : None,
                    "groupid": None,
                    "id": 2,
                    "num_exposures": 42,
                    "num_observed": None,
                    "obstype": 0,
                    "proposal": self.test_proposal.id,
                    "reported": False,
                    "site": None,
                    "superblock": test_sblock2.id,
                    "telclass": '1m0',
                    "tracking_number": None,
                    "when_observed": None,
                    "when_reported": None,
                }
            ]
        })

    def test_find_block_by_obstype(self):
        self.login()
        self.block_params['obstype'] = Block.OPT_SPECTRA_CALIB
        self.block_params['num_exposures'] = 1
        self.block_params['site'] = 'ogg'
        self.block_params['telclass'] = '2m0'
        test_block2 = Block.objects.create(**self.block_params)

        response = self.client.get(self.query_url.format('', test_block2.obstype))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "active": False,
                    "block_end": None,
                    "block_start": None,
                    "body": None,
                    "calibsource": None,
                    "exp_length" : None,
                    "groupid": None,
                    "id": 2,
                    "num_exposures": 1,
                    "num_observed": None,
                    "obstype": 3,
                    "proposal": self.test_proposal.id,
                    "reported": False,
                    "site": 'ogg',
                    "superblock": self.test_sblock.id,
                    "telclass": '2m0',
                    "tracking_number": None,
                    "when_observed": None,
                    "when_reported": None,
                }
            ]
        })


class SuperBlockAPITest(BaseViewTest):
    base_url = '/api/superblocks/{}/'
    query_url = '/api/superblocks/?tracking_number={}&blockstart_after={}&blockstart_before={}'

    def test_get_returns_json_200(self):
        self.login()
        response = self.client.get(self.base_url.format(self.test_sblock.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_anonymous_get_returns_json_200(self):
        response = self.client.get(self.base_url.format(self.test_sblock.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_get_for_LCO_data(self):
        self.login()
        response = self.client.get(self.base_url.format(self.test_sblock.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            {
                    "active": False,
                    "block_end": None,
                    "block_start": None,
                    "body": None,
                    "cadence": False,
                    "calibsource": None,
                    "groupid": None,
                    "id": 1,
                    "jitter": None,
                    "period": None,
                    "proposal": self.test_proposal.id,
                    "rapid_response": False,
                    "timeused": None,
                    "tracking_number": None,
            }
        )

    def test_find_superblocks_by_trackingnum(self):
        self.login()
        self.sblock_params['tracking_number'] = '0420'
        test_sblock2 = SuperBlock.objects.create(**self.sblock_params)

        response = self.client.get(self.query_url.format(test_sblock2.tracking_number, '', ''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        foo = json.loads(response.content.decode('utf8'))
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "active": False,
                    "block_end": None,
                    "block_start": None,
                    "body": None,
                    "cadence": False,
                    "calibsource": None,
                    "groupid": None,
                    "id": 2,
                    "jitter": None,
                    "period": None,
                    "proposal": self.test_proposal.id,
                    "rapid_response": False,
                    "timeused": None,
                    "tracking_number": "0420",
                }
            ]
        })

    def test_find_superblocks_by_daterange(self):
        self.login()
        self.sblock_params['block_start'] = datetime(2019,4,21,23,0,0)
        self.sblock_params['block_end'] = datetime(2019,4,22,12,0,0)
        self.sblock_params['tracking_number'] = "0421"
        test_sblock2 = SuperBlock.objects.create(**self.sblock_params)
        self.sblock_params['block_start'] = datetime(2019,4,22,16,0,0)
        self.sblock_params['block_end'] = datetime(2019,4,23, 3,30,0)
        self.sblock_params['tracking_number'] = "0422"
        test_sblock3 = SuperBlock.objects.create(**self.sblock_params)

        response = self.client.get(self.query_url.format('', datetime(2019,4,21,22,0,59), datetime(2019,4,22,13,0,0)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "active": False,
                    "block_end": "2019-04-22T12:00:00",
                    "block_start": "2019-04-21T23:00:00",
                    "body": None,
                    "cadence": False,
                    "calibsource": None,
                    "groupid": None,
                    "id": 2,
                    "jitter": None,
                    "period": None,
                    "proposal": self.test_proposal.id,
                    "rapid_response": False,
                    "timeused": None,
                    "tracking_number": "0421",
                }
            ]
        })

    def test_find_superblocks_by_daterange_string(self):
        self.login()
        self.sblock_params['block_start'] = datetime(2019,4,21,23,0,0)
        self.sblock_params['block_end'] = datetime(2019,4,22,12,0,0)
        self.sblock_params['tracking_number'] = "0421"
        test_sblock2 = SuperBlock.objects.create(**self.sblock_params)
        self.sblock_params['block_start'] = datetime(2019,4,22,16,0,0)
        self.sblock_params['block_end'] = datetime(2019,4,23, 3,30,0)
        self.sblock_params['tracking_number'] = "0422"
        test_sblock3 = SuperBlock.objects.create(**self.sblock_params)

        response = self.client.get(self.query_url.format('', "2019-04-21 22:0:59", "2019-04-22 13:00:00"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(
            json.loads(response.content.decode('utf8')),
            { 'count' : 1,
              'next' : None,
              'previous' : None,
              'results' : [
                {
                    "active": False,
                    "block_end": "2019-04-22T12:00:00",
                    "block_start": "2019-04-21T23:00:00",
                    "body": None,
                    "cadence": False,
                    "calibsource": None,
                    "groupid": None,
                    "id": 2,
                    "jitter": None,
                    "period": None,
                    "proposal": self.test_proposal.id,
                    "rapid_response": False,
                    "timeused": None,
                    "tracking_number": "0421",
                }
            ]
        })


class CatalogSourcesAPITest(BaseViewTest):
    base_url = '/api/catsources/{}/'
    query_url = '/api/catsources/?frame_id={}&frame_filename={}&ra_min={}&ra_max={}}&dec_min={}&dec_max={}'

    def setUp(self):
        super(CatalogSourcesAPITest, self).setUp()

        self.frame_params = {
                'block'    : self.test_block,
                'sitecode' : 'K91',
                'filename' : 'cpt1m010-fa16-20190330-0129-e91.fits',
                'midpoint' : datetime(2019,4,20,19,30,0),
                'filter'   : 'w',
                'frametype': Frame.BANZAI_RED_FRAMETYPE
               }
        self.test_frame = Frame.objects.create(**self.frame_params)

        self.catsrc_params = {   'frame' : self.test_frame,
                            'obs_x' : 1024.1,
                            'obs_y' : 511.5,
                            'obs_ra' : 42.0,
                            'obs_dec' : -32.0,
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
        self.test_catsrc1 = CatalogSources.objects.create(**self.catsrc_params)

    def test_get_returns_json_200(self):
        self.login()

        response = self.client.get(self.base_url.format(self.test_catsrc1.id))
        print(self.base_url.format(self.test_catsrc1.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_anonymous_get_returns_json_404(self):
        response = self.client.get(self.base_url.format(self.test_catsrc1.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
