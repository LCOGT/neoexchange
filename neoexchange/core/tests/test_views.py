"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
import shutil
from datetime import datetime, timedelta, date
from unittest import skipIf
import tempfile
from glob import glob
from math import degrees

from django.test import TestCase
from django.forms.models import model_to_dict
from bs4 import BeautifulSoup
from mock import patch
from astropy.io import fits

from neox.tests.mocks import MockDateTime, mock_check_request_status, mock_check_for_images, \
    mock_check_request_status_null, mock_check_request_status_notfound, \
    mock_check_for_images_no_millisecs, \
    mock_check_for_images_bad_date, mock_ingest_frames, mock_archive_frame_header, \
    mock_odin_login, mock_run_sextractor_make_catalog, mock_fetch_filter_list

from astrometrics.ephem_subs import call_compute_ephem, determine_darkness_times
from astrometrics.sources_subs import parse_mpcorbit, parse_mpcobs, \
    fetch_flux_standards, read_solar_standards
from photometrics.catalog_subs import open_fits_catalog, get_catalog_header
from core.frames import block_status, create_frame, frame_params_from_block
from core.models import Body, Proposal, Block, SourceMeasurement, Frame, Candidate,\
    SuperBlock, SpectralInfo, PreviousSpectra, StaticSource
from core.frames import block_status, create_frame, frame_params_from_block
from core.forms import EphemQuery
# Import modules to test
from core.views import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)


class TestClean_NEOCP_Object(TestCase):

    def test_X33656(self):
        obs_page = [u'X33656  23.9  0.15  K1548 330.99052  282.94050   31.81272   13.02458  0.7021329  0.45261672   1.6800247                  3   1    0 days 0.21         NEOCPNomin',
                    u'X33656  23.9  0.15  K1548 250.56430  257.29551   60.34849    2.58054  0.0797769  0.87078998   1.0860765                  3   1    0 days 0.20         NEOCPV0001',
                    u'X33656  23.9  0.15  K1548 256.86580  263.73491   53.18662    3.17001  0.1297341  0.88070404   1.0779106                  3   1    0 days 0.20         NEOCPV0002',
                   ]
        expected_elements = { 'abs_mag'     : 23.9,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 4, 8, 0, 0, 0),
                              'meananom'    : 330.99052,
                              'argofperih'  : 282.94050,
                              'longascnode' :  31.81272,
                              'orbinc'      :  13.02458,
                              'eccentricity':  0.7021329,
                             # 'MDM':   0.45261672,
                              'meandist'    :  1.6800247,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    def test_missing_absmag(self):
        obs_page = ['Object   H     G    Epoch    M         Peri.      Node       Incl.        e           n         a                     NObs NOpp   Arc    r.m.s.       Orbit ID',
                    'N007riz       0.15  K153J 340.52798   59.01148  160.84695   10.51732  0.3080134  0.56802014   1.4439768                  6   1    0 days 0.34         NEOCPNomin',
                    'N007riz       0.15  K153J 293.77087  123.25671  129.78437    3.76739  0.0556350  0.93124537   1.0385481                  6   1    0 days 0.57         NEOCPV0001'
                   ]

        expected_elements = { 'abs_mag'     : 99.99,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 3, 19, 0, 0, 0),
                              'meananom'    : 340.52798,
                              'argofperih'  :  59.01148,
                              'longascnode' : 160.84695,
                              'orbinc'      :  10.51732,
                              'eccentricity':  0.3080134,
                             # 'MDM':   0.56802014,
                              'meandist'    :  1.4439768,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    def test_findorb_without_replace(self):
        obs_page = [u'LSCTLFr 18.04  0.15 K158Q 359.91024    8.53879  335.41846    3.06258  0.1506159  0.29656016   2.2270374    FO 150826     3   1 10.4 min  0.08         Find_Orb   0000 LSCTLFr                     20150826',
                   ]
        expected_elements = {}
        elements = clean_NEOCP_object(obs_page)
        self.assertEqual(expected_elements, elements)

    @patch('core.views.datetime', MockDateTime)
    def test_findorb(self):

        MockDateTime.change_datetime(2015, 8, 27, 12, 0, 0)

        obs_page = [u'LSCTLFr 18.04  0.15 K158Q 359.91024    8.53879  335.41846    3.06258  0.1506159  0.29656016   2.2270374    FO 150826     3   1 10.4 min  0.08         Find_Orb   0000 LSCTLFr                     20150826',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 18.04,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 8, 26, 0, 0, 0),
                              'meananom'    : 359.91024,
                              'argofperih'  : 8.53879,
                              'longascnode' : 335.41846,
                              'orbinc'      :   3.06258,
                              'eccentricity':  0.1506159,
                             # 'MDM':   0.29656016,
                              'meandist'    :  2.2270374,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'L',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 10.4/1440.0,
                              'not_seen'    : 1.5
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_findorb_with_perturbers(self):

        MockDateTime.change_datetime(2015, 9, 27, 6, 00, 00)

        obs_page = [u'CPTTL89 19.03  0.15 K159F 343.17326  209.67924  172.85027   25.18528  0.0920324  0.36954350   1.9232054    FO 150916    30   1    3 days 0.14 M-P 06  Find_Orb   0000 CPTTL89                     20150915',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 19.03,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 9, 15, 0, 0, 0),
                              'meananom'    : 343.17326,
                              'argofperih'  : 209.67924,
                              'longascnode' : 172.85027,
                              'orbinc'      :  25.18528,
                              'eccentricity':  0.0920324,
                             # 'MDM':   0.36954350,
                              'meandist'    :  1.9232054,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'L',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 3.0,
                              'not_seen'    : 12.25
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    def save_N007riz(self):
        obj_id = 'N007riz'
        elements = { 'abs_mag'     : 23.9,
                      'slope'       : 0.15,
                      'epochofel'   : datetime(2015, 3, 19, 0, 0, 0),
                      'meananom'    : 340.52798,
                      'argofperih'  :  59.01148,
                      'longascnode' : 160.84695,
                      'orbinc'      :  10.51732,
                      'eccentricity':  0.3080134,
                      'meandist'    :  1.4439768,
                      'elements_type': 'MPC_MINOR_PLANET',
                      'origin'      : 'M',
                      'source_type' : 'U',
                      'active'      : True
                    }
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
        # We are creating this object
        self.assertEqual(True, created)
        resp = save_and_make_revision(body, elements)
        # We are saving all the detailing elements
        self.assertEqual(True, resp)

    def test_revise_N007riz(self):
        self.save_N007riz()
        obj_id = 'N007riz'
        elements = { 'abs_mag'     : 23.9,
                      'slope'       : 0.15,
                      'epochofel'   : datetime(2015, 4, 19, 0, 0, 0),
                      'meananom'    : 340.52798,
                      'argofperih'  :  59.01148,
                      'longascnode' : 160.84695,
                      'orbinc'      :  10.51732,
                      'eccentricity':  0.4080134,
                      'meandist'    :  1.4439768,
                      'elements_type': 'MPC_MINOR_PLANET',
                      'origin'      : 'M',
                      'source_type' : 'U',
                      'active'      : False
                    }
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
        # Created should now be false
        self.assertEqual(False, created)
        resp = save_and_make_revision(body, elements)
        # Saving the new elements
        self.assertEqual(True,resp)

    def test_update_MPC_duplicate(self):
        self.save_N007riz()
        obj_id = 'N007riz'
        update_MPC_orbit(obj_id)

    def test_create_discovered_object(self):
        obj_id ='LSCTLF8'
        elements = { 'abs_mag'     : 16.2,
                      'slope'       : 0.15,
                      'epochofel'   : datetime(2015, 6, 23, 0, 0, 0),
                      'meananom'    : 333.70614,
                      'argofperih'  :  40.75306,
                      'longascnode' : 287.97838,
                      'orbinc'      :  23.61657,
                      'eccentricity':  0.1186953,
                      'meandist'    :  2.7874893,
                      'elements_type': 'MPC_MINOR_PLANET',
                      'origin'      : 'L',
                      'source_type' : 'D',
                      'active'      : True
                    }
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
        # We are creating this object
        self.assertEqual(True,created)
        resp = save_and_make_revision(body, elements)
        # Need to call full_clean() to validate the fields as this is not
        # done on save() (called by get_or_create() or save_and_make_revision())
        body.full_clean()
        # We are saving all the detailing elements
        self.assertEqual(True, resp)

        # Test it came from LCOGT as a discovery
        self.assertEqual('L', body.origin)
        self.assertEqual('D', body.source_type)

    @patch('core.views.datetime', MockDateTime)
    def test_should_be_comets(self):

        MockDateTime.change_datetime(2016, 8, 1, 23, 00, 00)

        obs_page = [u'P10vY9r 11.8  0.15  K167B 359.98102  162.77868  299.00048  105.84058  0.9976479  0.00002573 1136.349844                 66   1   35 days 0.42         NEOCPNomin',
                   ]

        expected_elements = { 'abs_mag'     : 11.8,
                              'slope'       : 4.0,
                              'epochofel'   : datetime(2016, 7, 11, 0, 0, 0),
                              'argofperih'  : 162.77868,
                              'longascnode' : 299.00048,
                              'orbinc'      : 105.84058,
                              'eccentricity':  0.9976479,
                              'epochofperih': datetime(2018, 7, 18, 16, 0, 8, 802657),
                              'perihdist'   : 1136.349844 * (1.0 - 0.9976479),
                              'meananom'    : None,
                             # 'MDM':   0.36954350,
                              'elements_type': 'MPC_COMET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 35.0,
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])


class TestCheck_for_block(TestCase):

    def setUp(self):
        # Initialise with three test bodies a test proposal and several blocks.
        # The first body has a provisional name (e.g. a NEO candidate), the
        # other 2 do not (e.g. Goldstone targets)
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
        self.body_with_provname, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'N999R0Q'
        self.body_with_uppername = Body.objects.create(**params)

        params['provisional_name'] = 'N999R0q'
        self.body_with_uppername2 = Body.objects.create(**params)

        params['provisional_name'] = ''
        params['name'] = '2014 UR'
        params['origin'] = 'G'
        self.body_no_provname1, created = Body.objects.get_or_create(**params)

        params['name'] = '436724'
        self.body_no_provname2, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        block_params2 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_CPT-20150420',
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

        block_params3 = { 'telclass' : '1m0',
                         'site'     : 'LSC',
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + \
                            '_LSC-20150421',
                         'block_start' : '2015-04-21 23:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '00044',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block3 = Block.objects.create(**block_params3)

        block_params4 = { 'telclass' : '1m0',
                         'site'     : 'LSC',
                         'body'     : self.body_no_provname1,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_no_provname1.current_name() + \
                            '_LSC-20150421',
                         'block_start' : '2015-04-21 23:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '00045',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block4 = Block.objects.create(**block_params4)

        block_params5 = { 'telclass' : '1m0',
                         'site'     : 'ELP',
                         'body'     : self.body_no_provname2,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_no_provname2.current_name() + \
                            '_ELP-20141121_lc',
                         'block_start' : '2014-11-21 03:00:00',
                         'block_end'   : '2014-11-21 13:00:00',
                         'tracking_number' : '00006',
                         'num_exposures' : 77,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block5 = Block.objects.create(**block_params5)

        block_params6 = { 'telclass' : '1m0',
                         'site'     : 'ELP',
                         'body'     : self.body_no_provname2,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_no_provname2.current_name() + \
                            '_ELP-20141121',
                         'block_start' : '2014-11-21 03:00:00',
                         'block_end'   : '2014-11-21 13:00:00',
                         'tracking_number' : '00007',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block6 = Block.objects.create(**block_params6)

        block_params7 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body_with_uppername,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_uppername.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00069',
                         'num_exposures' : 5,
                         'exp_length' : 130.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block2 = Block.objects.create(**block_params2)

    def test_db_storage(self):
        expected_body_count = 5  # Pew, pew, bang, bang...
        expected_block_count = 7
        expected_sblock_count = 7

        body_count = Body.objects.count()
        block_count = Block.objects.count()
        sblock_count = SuperBlock.objects.count()

        self.assertEqual(expected_body_count, body_count)
        self.assertEqual(expected_block_count, block_count)
        self.assertEqual(expected_sblock_count, sblock_count)

    def test_body_with_provname_no_blocks(self):

        new_body = self.body_with_provname
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_with_provname.current_name() + '_CPT-20150422'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_provname_one_block(self):

        new_body = self.body_with_provname
        params = { 'site_code' : 'W86'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_with_provname.current_name() + '_LSC-20150421'
                    }
        expected_state = 1

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_provname_two_blocks(self):

        new_body = self.body_with_provname
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_with_provname.current_name() + '_CPT-20150420'
                    }
        expected_state = 2

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname1_no_blocks(self):

        new_body = self.body_no_provname1
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_no_provname1.current_name() + '_CPT-20150422'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname1_no_blocks_sinistro(self):

        new_body = self.body_no_provname1
        params = { 'site_code' : 'K93'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_no_provname1.current_name() + '_CPT-20150422'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname1_one_block(self):

        new_body = self.body_no_provname1
        params = { 'site_code' : 'W86'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_no_provname1.current_name() + '_LSC-20150421'
                    }
        expected_state = 1

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname2_two_blocks(self):

        new_body = self.body_no_provname2
        params = { 'site_code' : 'V37'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_no_provname2.current_name() + '_ELP-20141121'
                    }
        expected_state = 2

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_uppercase_name(self):
        # This passes but shouldn't as SQlite goes string checks case-insensitively whatever you do
        new_body = self.body_with_uppername2
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_with_uppername2.current_name() + '_CPT-20150420'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    # These mocks via the patch decorator for check_for_archive_images() and
    # lco_api_call() need to patch core.frames even though they are in
    # core.archive_subs otherwise they will be overridden by the
    # 'from core.archive_subs import lco_api_call' in core.frames.

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_active(self):
        resp = block_status(1)
        self.assertTrue(resp)

    @skipIf(True, "Edward needs to fix...")
    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_not_active(self):
        resp = block_status(2)
        self.assertFalse(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.views.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_check_status_change_not_enough_frames(self):
        blockid = self.test_block6.id
        resp = block_status(blockid)
        myblock = Block.objects.get(id=blockid)
        self.assertTrue(myblock.active)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.views.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_check_status_change_enough_frames(self):
        self.test_block6.num_exposures = 3
        self.test_block6.save()
        blockid = self.test_block6.id
        resp = block_status(blockid)
        myblock = Block.objects.get(id=blockid)
        self.assertTrue(myblock.active)

    @patch('core.frames.check_request_status', mock_check_request_status_null)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_check_no_obs(self):
        blockid = self.test_block6.id
        resp = block_status(blockid)
        self.assertFalse(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_check_for_images_no_millisecs)
    def test_block_update_no_millisecs(self):
        blockid = self.test_block5.id
        resp = block_status(blockid)
        self.assertTrue(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_check_for_images_bad_date)
    def test_block_update_bad_datestamp(self):
        blockid = self.test_block5.id
        resp = block_status(blockid)
        self.assertFalse(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_check_for_images_no_millisecs)
    def test_block_update_check_num_observed(self):
        bid = 1
        resp = block_status(block_id=bid)
        blk = Block.objects.get(id=bid)
        self.assertEqual(blk.num_observed,1)

    @patch('core.frames.check_request_status', mock_check_request_status_notfound)
    def test_block_not_found(self):
        bid = 1
        resp = block_status(block_id=bid)
        self.assertEqual(False, resp)


class TestRecordBlock(TestCase):

    def setUp(self):

        self.spectro_tracknum = '606083'
        self.spectro_params = {
                              'binning': 1,
                              'block_duration': 988.0,
                              'calibs': 'both',
                              'end_time': datetime(2018, 3, 16, 18, 50),
                              'exp_count': 1,
                              'exp_time': 180.0,
                              'exp_type': 'SPECTRUM',
                              'group_id': '4_E10-20180316_spectra',
                              'instrument': '2M0-FLOYDS-SCICAM',
                              'instrument_code': 'E10-FLOYDS',
                              'observatory': '',
                              'pondtelescope': '2m0',
                              'proposal_id': 'LCOEngineering',
                              'request_numbers': {1450339: 'NON_SIDEREAL'},
                              'request_windows': [[{'end': '2018-03-16T18:30:00',
                                 'start': '2018-03-16T11:20:00'}]],
                              'site': 'COJ',
                              'site_code': 'E10',
                              'spectra_slit': 'slit_6.0as',
                              'spectroscopy': True,
                              'start_time': datetime(2018, 3, 16, 9, 20),
                              'user_id': 'tlister@lcogt.net'}

        self.spectro_form = { 'start_time' : self.spectro_params['start_time'],
                              'end_time' : self.spectro_params['end_time'],
                              'proposal_code' : self.spectro_params['proposal_id'],
                              'group_id' : self.spectro_params['group_id'],
                              'exp_count' : self.spectro_params['exp_count'],
                              'exp_length' : self.spectro_params['exp_time'],
                            }
        body_params = { 'name' : '4' }
        self.spectro_body = Body.objects.create(**body_params)

        proposal_params = { 'code' : self.spectro_params['proposal_id'], }
        self.proposal = Proposal.objects.create(**proposal_params)

        self.imaging_tracknum = '576013'
        self.imaging_params = {
                              'binning': 1,
                              'block_duration': 1068.0,
                              'end_time': datetime(2018, 3, 16, 3, 50),
                              'exp_count': 12,
                              'exp_time': 42.0,
                              'exp_type': 'EXPOSE',
                              'group_id': 'N999r0q_K91-20180316',
                              'instrument': '1M0-SCICAM-SINISTRO',
                              'observatory': '',
                              'pondtelescope': '1m0',
                              'proposal_id': 'LCOEngineering',
                              'request_numbers': {1440123: 'NON_SIDEREAL'},
                              'request_windows': [[{'end': '2018-03-16T03:30:00',
                                 'start': '2018-03-15T20:20:00'}]],
                              'site': 'CPT',
                              'site_code': 'K91',
                              'start_time': datetime(2018, 3, 15, 18, 20),
                              'user_id': 'tlister@lcogt.net'}

        self.imaging_form = { 'start_time' : self.imaging_params['start_time'],
                              'end_time' : self.imaging_params['end_time'],
                              'proposal_code' : self.imaging_params['proposal_id'],
                              'group_id' : self.imaging_params['group_id'],
                              'exp_count' : self.imaging_params['exp_count'],
                              'exp_length' : self.imaging_params['exp_time'],
                            }
        body_params = {'provisional_name' : 'N999r0q'}
        self.imaging_body = Body.objects.create(**body_params)

        ssource_params = { 'name'   : 'Landolt SA107-684',
                           'ra'     : 234.325,
                           'dec'    : -0.164,
                           'vmag'   : 8.2,
                           'source_type' : StaticSource.SOLAR_STANDARD,
                           'spectral_type' : "G2V"
                         }
        self.solar_analog = StaticSource.objects.create(**ssource_params)

    def test_spectro_block(self):
        block_resp = record_block(self.spectro_tracknum, self.spectro_params, self.spectro_form, self.spectro_body)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_SPECTRA, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.spectro_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.spectro_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 16, 11, 20, 0), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 18, 30, 0), blocks[0].block_end)
        self.assertEqual(self.spectro_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.spectro_tracknum != blocks[0].tracking_number)
        self.assertEqual(self.spectro_params['block_duration'], sblocks[0].timeused)

    def test_imaging_block(self):
        block_resp = record_block(self.imaging_tracknum, self.imaging_params, self.imaging_form, self.imaging_body)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_IMAGING, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.imaging_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.imaging_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 15, 20, 20, 0), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 3, 30, 0), blocks[0].block_end)
        self.assertEqual(self.imaging_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.imaging_tracknum != blocks[0].tracking_number)
        self.assertEqual(self.imaging_params['block_duration'], sblocks[0].timeused)

    def test_spectro_and_solar_block(self):
        new_params =  { 'calibsource' : {  'id': 1,
                                           'name': 'Landolt SA107-684',
                                           'ra_deg': 234.325,
                                           'dec_deg': -0.164,
                                           'pm_ra': 0.0,
                                           'pm_dec': 0.0,
                                           'parallax': 0.0
                                        },
                        'calibsrc_exptime' : 60.0,
                        'dec_deg' : -0.164,
                        'ra_deg'  : 234.325,
                        'solar_analog' : True
                        }
        spectro_params = {**new_params, **self.spectro_params}
        spectro_params['group_id'] = self.spectro_params['group_id'] + '+solstd'
        spectro_params['request_numbers'] = {1450339: 'NON_SIDEREAL', 1450340: 'SIDEREAL'}
        spectro_params['request_windows'] = [[{'end': '2018-03-16T18:30:00', 'start': '2018-03-16T11:20:00'}],
                                            [{'end': '2018-03-16T18:30:00', 'start': '2018-03-16T11:20:00'}]
                                           ]

        block_resp = record_block(self.spectro_tracknum, spectro_params, self.spectro_form, self.spectro_body)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        solar_analogs = StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD)
        self.assertEqual(1, sblocks.count())
        self.assertEqual(2, blocks.count())
        self.assertEqual(Block.OPT_SPECTRA, blocks[0].obstype)
        self.assertEqual(Block.OPT_SPECTRA_CALIB, blocks[1].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.spectro_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.spectro_form['end_time'], sblocks[0].block_end)
        self.assertFalse(sblocks[0].cadence)
        self.assertEqual(self.spectro_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.spectro_tracknum != blocks[0].tracking_number)
        self.assertEqual(self.spectro_params['block_duration'], sblocks[0].timeused)

        self.assertEqual(datetime(2018, 3, 16, 11, 20, 0), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 18, 30, 0), blocks[0].block_end)
        self.assertEqual(self.spectro_body, blocks[0].body)

        self.assertEqual(solar_analogs[0], blocks[1].calibsource)
        self.assertEqual(None, blocks[1].body)
        self.assertEqual(spectro_params['calibsrc_exptime'], blocks[1].exp_length)

    def test_solo_solar_spectro_block(self):
        # adjust parameters for sidereal target
        self.spectro_params['request_numbers'] = {1450339: 'SIDEREAL'}
        self.spectro_params['group_id'] = 'Landolt SA107-684_E10-20180316_spectra'
        self.spectro_form['group_id'] = self.spectro_params['group_id']
        block_resp = record_block(self.spectro_tracknum, self.spectro_params, self.spectro_form, self.solar_analog)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_SPECTRA_CALIB, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.spectro_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.spectro_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 16, 11, 20, 0), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 18, 30, 0), blocks[0].block_end)
        self.assertEqual(self.spectro_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.spectro_tracknum != blocks[0].tracking_number)
        self.assertEqual(self.spectro_params['block_duration'], sblocks[0].timeused)


class TestSchedule_Check(TestCase):

    def setUp(self):
        # Initialise with three test bodies a test proposal and several blocks.
        # The first body has a provisional name (e.g. a NEO candidate), the
        # other 2 are a comet (specified with MPC_COMET elements type) and 1 that
        # should be a comet (high eccentricity but MPC_MINOR_PLANET)
        params = {  'provisional_name' : 'LM059Y5',
                    'name'          : '2009 HA21',
                    'abs_mag'       : 20.7,
                    'slope'         : 0.15,
                    'epochofel'     : '2016-01-13 00:00:00',
                    'meananom'      : 352.95033,
                    'argofperih'    : 219.7865,
                    'longascnode'   : 205.50221,
                    'orbinc'        : 6.41173,
                    'eccentricity'  : 0.728899,
                    'meandist'      : 1.4607441,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body_mp, created = Body.objects.get_or_create(**params)

        params['elements_type'] = 'MPC_MINOR_PLANET'
        params['name'] = '2015 ER61'
        params['eccentricity'] = 0.9996344
        self.body_bad_elemtype, created = Body.objects.get_or_create(**params)

        params['elements_type'] = 'MPC_COMET'
        params['perihdist'] = 1.0540487
        params['epochofperih'] = datetime(2017, 5, 17)
        self.body_good_elemtype, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        src_params = {  'name' : 'SA42-999',
                        'ra'   : 200.0,
                        'dec'  : -15.0,
                        'vmag' : 9.0,
                        'spectral_type' : "G2V",
                        'source_type' : StaticSource.SOLAR_STANDARD
                     }
        self.solar_analog, created = StaticSource.objects.get_or_create(pk=1, **src_params)
        self.maxDiff = None

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_good(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = { 'site_code' : 'Q63',
                 'utc_date' : datetime(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.099441743160916,
                        'speed': 2.9012947050834836,
                        'slot_length': 20,
                        'filter_pattern': 'w',
                        'pattern_iterations': 12.0,
                        'available_filters': 'air, U, B, V, R, I, up, gp, rp, ip, zs, Y, w',
                        'exp_count': 12,
                        'exp_length': 50.0,
                        'schedule_ok': True,
                        'site_code': data['site_code'],
                        'proposal_code': data['proposal_code'],
                        'group_id': self.body_mp.current_name() + '_' + data['site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d'),
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:00:00',
                        'end_time': '2016-04-06T19:10:00',
                        'mid_time': '2016-04-06T14:05:00',
                        'ra_midpoint': 3.312248725288052,
                        'dec_midpoint': -0.1605498546995108,
                        'period' : None,
                        'jitter' : None,
                        'instrument_code' : '',
                        'snr' : None,
                        'too_mode': False,
                        'calibs' : '',
                        'spectroscopy' : False,
                        'calibsource' : {},
                        'calibsource_id' : -1,
                        'solar_analog' : False
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)
        self.assertLessEqual(len(resp['group_id']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_good_spectro(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = { 'instrument_code' : 'E10-FLOYDS',
                 'utc_date' : datetime(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code,
                 'spectroscopy' : True,
                 'calibs' : 'both',
                 'exp_length' : 300.0,
                 'exp_count' : 1
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.09944174338544,
                        'speed': 2.901293748154893,
                        'slot_length': 23,
                        'filter_pattern': 'slit_6.0as',
                        'pattern_iterations': 1.0,
                        'available_filters': 'slit_1.2as, slit_1.6as, slit_2.0as, slit_6.0as',
                        'exp_count': 1,
                        'exp_length': 300.0,
                        'schedule_ok': True,
                        'site_code': data['instrument_code'][0:3],
                        'proposal_code': data['proposal_code'],
                        'group_id': self.body_mp.current_name() + '_' + data['instrument_code'][0:3].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d') + '_spectra',
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:00:00',
                        'end_time': '2016-04-06T19:10:00',
                        'mid_time': '2016-04-06T14:05:00',
                        'ra_midpoint': 3.31224872619019,
                        'dec_midpoint': -0.16054985464643165,
                        'period' : None,
                        'jitter' : None,
                        'instrument_code' : 'E10-FLOYDS',
                        'snr' : 3.2107142545718275,
                        'calibs' : 'both',
                        'spectroscopy' : True,
                        'too_mode': False,
                        'calibsource' : {},
                        'calibsource_id' : -1,
                        'solar_analog' : False
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)
        self.assertLessEqual(len(resp['group_id']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_good_spectro_solar_analog(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = { 'instrument_code' : 'E10-FLOYDS',
                 'utc_date' : datetime(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code,
                 'spectroscopy' : True,
                 'calibs' : 'both',
                 'exp_length' : 300.0,
                 'exp_count' : 1,
                 'solar_analog' : True
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.09944174338544,
                        'speed': 2.901293748154893,
                        'slot_length': 23,
                        'filter_pattern': 'slit_6.0as',
                        'pattern_iterations': 1.0,
                        'available_filters': 'slit_1.2as, slit_1.6as, slit_2.0as, slit_6.0as',
                        'exp_count': 1,
                        'exp_length': 300.0,
                        'schedule_ok': True,
                        'site_code': data['instrument_code'][0:3],
                        'proposal_code': data['proposal_code'],
                        'group_id': self.body_mp.current_name() + '_' + data['instrument_code'][0:3].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d') + '_spectra',
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:00:00',
                        'end_time': '2016-04-06T19:10:00',
                        'mid_time': '2016-04-06T14:05:00',
                        'ra_midpoint': 3.31224872619019,
                        'dec_midpoint': -0.16054985464643165,
                        'period' : None,
                        'jitter' : None,
                        'instrument_code' : 'E10-FLOYDS',
                        'snr' : 3.2107142545718275,
                        'calibs' : 'both',
                        'spectroscopy' : True,
                        'too_mode': False,
                        'calibsource' : {'separation_deg' : 11.551868532224177, **model_to_dict(self.solar_analog)},
                        'calibsource_id' : 1,
                        'solar_analog' : True
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)
        self.assertLessEqual(len(resp['group_id']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_cadence_short_name(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)
        self.body_mp.name = '2009 HA'
        self.body_mp.save()

        data = { 'site_code' : 'Q63',
                 'utc_date' : datetime(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code,
                 'period' : 4.0,
                 'jitter' : 1.0,
                 'start_time' : datetime(2016, 4, 6, 9, 0, 0),
                 'end_time' : datetime(2016, 4, 6, 23, 0, 0),
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.111452844407932,
                        'speed': 2.8743096178906367,
                        'slot_length': 20,
                        'filter_pattern': 'w',
                        'pattern_iterations': 12.0,
                        'available_filters': 'air, U, B, V, R, I, up, gp, rp, ip, zs, Y, w',
                        'exp_count': 12,
                        'exp_length': 50.0,
                        'schedule_ok': True,
                        'site_code': data['site_code'],
                        'proposal_code': data['proposal_code'],
                        'group_id': '2009 HA_Q63-cad-20160406-0406',
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:00:00',
                        'end_time': '2016-04-06T23:00:00',
                        'mid_time': '2016-04-06T16:00:00',
                        'ra_midpoint': 3.3110137022045336,
                        'dec_midpoint': -0.15949643713664577,
                        'period' : 4.0,
                        'jitter' : 1.0,
                        'num_times' : 3,
                        'total_time' : 1.0,
                        'instrument_code' : '',
                        'snr' : None,
                        'too_mode': False,
                        'calibs' : '',
                        'spectroscopy' : False,
                        'calibsource' : {},
                        'calibsource_id' : -1,
                        'solar_analog' : False
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)
        self.assertLessEqual(len(resp['group_id']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_cadence_long_name(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = { 'site_code' : 'Q63',
                 'utc_date' : date(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code,
                 'period' : 4.0,
                 'jitter' : 1.0,
                 'start_time' : datetime(2016, 4, 6, 9, 0, 0),
                 'end_time' : datetime(2016, 4, 6, 23, 0, 0),
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.111452844407932,
                        'speed': 2.8743096178906367,
                        'slot_length': 20,
                        'filter_pattern': 'w',
                        'pattern_iterations': 12.0,
                        'available_filters': 'air, U, B, V, R, I, up, gp, rp, ip, zs, Y, w',
                        'exp_count': 12,
                        'exp_length': 50.0,
                        'schedule_ok': True,
                        'site_code': data['site_code'],
                        'proposal_code': data['proposal_code'],
                        'group_id': '2009 HA21_Q63-cad-20160406-0406',
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:00:00',
                        'end_time': '2016-04-06T23:00:00',
                        'mid_time': '2016-04-06T16:00:00',
                        'ra_midpoint': 3.3110137022045336,
                        'dec_midpoint': -0.15949643713664577,
                        'period' : 4.0,
                        'jitter' : 1.0,
                        'num_times' : 3,
                        'total_time' : 1.0,
                        'instrument_code' : '',
                        'too_mode': False,
                        'snr' : None,
                        'calibs' : '',
                        'spectroscopy' : False,
                        'calibsource' : {},
                        'calibsource_id' : -1,
                        'solar_analog' : False
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)
        self.assertLessEqual(len(resp['group_id']), 50)

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_B_semester(self):
        MockDateTime.change_datetime(2016, 3, 31, 22, 0, 0)

        data = { 'site_code' : 'K92',
                 'utc_date' : date(2016, 4, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2016-03-31T17:40:00',
                        'end_time'   : '2016-03-31T23:59:59',
                        'exp_count'  : 16,
                        'exp_length' : 30.0,
                        'mid_time': '2016-03-31T20:49:59.500000',

                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])
        self.assertEqual(expected_resp['exp_count'], resp['exp_count'])
        self.assertEqual(expected_resp['exp_length'], resp['exp_length'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_start_A_semester(self):
        MockDateTime.change_datetime(2016, 4, 1, 0, 0, 1)

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2016, 4, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2016-04-01T00:00:00',
                        'end_time'   : '2016-04-01T03:40:00',
                        'exp_count'  : 16,
                        'exp_length' : 30.0,
                        'mid_time': '2016-04-01T01:50:00',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])
        self.assertEqual(expected_resp['exp_count'], resp['exp_count'])
        self.assertEqual(expected_resp['exp_length'], resp['exp_length'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_mid_A_semester(self):
        MockDateTime.change_datetime(2016, 4, 20, 23, 0, 0)

        data = { 'site_code' : 'V37',
                 'utc_date' : datetime(2016, 4, 21),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2016-04-21T02:30:00',
                        'end_time'   : '2016-04-21T11:10:00',
                        'exp_count'  : 6,
                        'exp_length' : 165,
                        'mid_time': '2016-04-21T06:50:00',
                        'magnitude' : 20.97
                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])
        self.assertEqual(expected_resp['exp_count'], resp['exp_count'])
        self.assertEqual(expected_resp['exp_length'], resp['exp_length'])
        self.assertAlmostEqual(expected_resp['magnitude'], resp['magnitude'], 2)

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_mid_past_A_semester(self):
        MockDateTime.change_datetime(2015, 4, 20, 23, 1, 0)

        data = { 'site_code' : 'V37',
                 'utc_date' : datetime(2015, 4, 21),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2015-04-21T02:30:00',
                        'end_time'   : '2015-04-21T11:10:00',
                        'exp_count'  : 6,
                        'exp_length' : 165,
                        'mid_time': '2015-04-21T06:50:00',
                        'magnitude' : 20.97
                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_A_semester(self):
        MockDateTime.change_datetime(2016, 9, 30, 23, 0, 0)

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2016, 10, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2016-09-30T17:40:00',
                        'end_time'   : '2016-09-30T23:59:59',
                        'mid_time': '2016-09-30T20:49:59.500000',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_schedule_for_B_at_A_semester_end(self):
        MockDateTime.change_datetime(2017, 3, 31, 23, 0, 0)

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2017,  4, 2),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2017-04-01T17:40:00',
                        'end_time'   : '2017-04-02T03:40:00',
                        'mid_time': '2017-04-01T22:40:00',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_schedule_for_B_at_A_semester_end2(self):

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2017,  4, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        MockDateTime.change_datetime(2017, 3, 31, 23, 0, 0)

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2017-04-01T00:00:00',
                        'end_time'   : '2017-04-01T03:40:00',
                        'mid_time': '2017-04-01T01:50:00',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_start_B_semester(self):
        MockDateTime.change_datetime(2016, 10, 1, 0, 0, 1)

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2016, 10, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2016-10-01T00:00:00',
                        'end_time'   : '2016-10-01T03:00:00',
                        'mid_time': '2016-10-01T01:30:00',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_2017AB_semester(self):
        MockDateTime.change_datetime(2017, 9, 28, 19, 0, 0)

        data = { 'site_code' : 'Z17',
                 'utc_date' : datetime(2017, 10, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2017-09-30T19:50:00',
                        'end_time'   : '2017-10-01T05:50:00',
                        'mid_time': '2017-10-01T00:50:00',

                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_2017AB_semester(self):
        MockDateTime.change_datetime(2017, 11, 30, 19, 0, 0)

        data = { 'site_code' : 'Z17',
                 'utc_date' : datetime(2017, 12, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2017-11-30T19:10:00',
                        'end_time'   : '2017-11-30T23:59:59',
                        'mid_time': '2017-11-30T21:34:59.500000',

                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_start_2018A_semester(self):
        MockDateTime.change_datetime(2017, 12,  1,  1, 0, 0)

        data = { 'site_code' : 'K91',
                 'utc_date' : datetime(2017, 12, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2017-12-01T00:00:00',
                        'end_time'   : '2017-12-01T02:00:00',
                        'mid_time': '2017-12-01T01:00:00',

                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_2018A_semester(self):
        MockDateTime.change_datetime(2018,  5, 31, 23, 0, 0)

        data = { 'site_code' : 'K91',
                 'utc_date' : datetime(2018,  6, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2018-05-31T16:50:00',
                        'end_time'   : '2018-05-31T23:59:59',
                        'mid_time': '2018-05-31T20:24:59.500000',

                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_start_2018B_semester(self):
        MockDateTime.change_datetime(2018,  6,  1,  1, 0, 0)

        data = { 'site_code' : 'K91',
                 'utc_date' : datetime(2018,  6, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2018-06-01T00:00:00',
                        'end_time'   : '2018-06-01T04:10:00',
                        'mid_time': '2018-06-01T02:05:00',

                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_2018B_semester(self):
        MockDateTime.change_datetime(2018, 11, 30, 23, 0, 0)

        data = { 'site_code' : 'K91',
                 'utc_date' : datetime(2018, 12, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2018-11-30T18:40:00',
                        'end_time'   : '2018-11-30T23:59:59',
                        'mid_time': '2018-11-30T21:19:59.500000',

                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])


class TestUpdate_MPC_orbit(TestCase):

    def setUp(self):

        # Read and make soup from a static version of the HTML table/page for
        # an object
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_2014UR.html'), 'r')
        self.test_mpcdb_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.nocheck_keys = ['ingest']   # Involves datetime.utcnow(), hard to check

        self.expected_elements = {u'id' : 1,
                             'name' : u'2014 UR',
                             'provisional_name': None,
                             'provisional_packed': None,
                             'elements_type': u'MPC_MINOR_PLANET',
                             'abs_mag' : 26.6,
                             'argofperih': 222.91160,
                             'longascnode': 24.87559,
                             'eccentricity': 0.0120915,
                             'epochofel': datetime(2016, 1, 13, 0),
                             'meandist': 0.9967710,
                             'orbinc': 8.25708,
                             'meananom': 221.74204,
                             'num_obs': None ,  # '147',
                             'epochofperih': None,
                             'perihdist': None,
                             'slope': 0.15,
                             'origin' : u'M',
                             'active' : True,
                             'arc_length': 357.0,
                             'discovery_date': datetime(2014, 10, 17, 0),
                             'num_obs' : 147,
                             'not_seen' : 5.5,
                             'fast_moving' : False,
                             'score' : None,
                             'source_type' : 'N',
                             'update_time' : datetime(2015, 10, 9, 0),
                             'updated' : True,
                             'urgency' : None
                             }

        self.maxDiff = None

    def test_badresponse(self):

        num_bodies_before = Body.objects.count()
        status = update_MPC_orbit(BeautifulSoup('<html></html>', 'html.parser'), origin='M')
        self.assertEqual(False, status)
        num_bodies_after = Body.objects.count()
        self.assertEqual(num_bodies_before, num_bodies_after)

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_MPC(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(self.expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in self.expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(self.expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Goldstone(self):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'G'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='G')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Arecibo(self):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'A'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Arecibo_better_exists(self):
        params = {'name': '2014 UR',
                  'abs_mag': 21.0,
                  'slope': 0.1,
                  'epochofel': '2017-03-19 00:00:00',
                  'elements_type': u'MPC_MINOR_PLANET',
                  'meananom': 325.2636,
                  'argofperih': 85.19251,
                  'longascnode': 147.81325,
                  'orbinc': 8.34739,
                  'eccentricity': 0.1896865,
                  'meandist': 1.2176312,
                  'source_type': 'U',
                  'num_obs': 1596,
                  'origin': 'M',
                  }

        self.body, created = Body.objects.get_or_create(**params)
        expected_elements = self.expected_elements
        expected_elements['origin'] = 'A'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))

        test_elements = ['epochofel', 'meananom', 'argofperih', 'longascnode', 'orbinc', 'eccentricity']
        for key in test_elements:
            self.assertNotEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Arecibo_older_exists(self):
        params = {'name': '2014 UR',
                  'abs_mag': 26.6,
                  'slope': 0.1,
                  'epochofel': '2013-03-19 00:00:00',
                  'elements_type': u'MPC_MINOR_PLANET',
                  'meananom': 325.2636,
                  'argofperih': 85.19251,
                  'longascnode': 147.81325,
                  'orbinc': 8.34739,
                  'eccentricity': 0.1896865,
                  'meandist': 1.2176312,
                  'source_type': 'U',
                  'num_obs': 15,
                  'origin': 'M',
                  }

        self.body, created = Body.objects.get_or_create(**params)
        expected_elements = self.expected_elements
        expected_elements['origin'] = 'A'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))

        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_goldstone_then_arecibo(self):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'R'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='G')
        self.assertEqual(True, status)

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_arecibo_then_goldstone(self):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'R'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='G')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_arecibo_then_NASA(self):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'N'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='N')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])


class TestUpdate_MPC_obs(TestCase):
    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_WSAE9A6.dat'), 'r')
        self.test_mpcobs_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_13553.dat'), 'r')
        self.test_mpcobs_page2 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_13553_old.dat'), 'r')
        self.test_mpcobs_page3 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_215426.dat'), 'r')
        self.test_mpcobs_page4 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

    @classmethod
    def setUpTestData(cls):
        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        cls.test_body = Body.objects.create(**WSAE9A6_params)

        params_13553 = { 'name' : '13553',
                         'provisional_name' : '1992 JE'
                         }
        cls.test_body2 = Body.objects.create(**params_13553)

        params_215426 = { 'name' : '215426',
                         'provisional_name' : '2002 JF45'
                         }
        cls.test_body3 = Body.objects.create(**params_215426)

    def test1(self):
        expected_num_srcmeas = 6
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 27, 12, int(0.672*1e6)),
                            'obs_ra'    : 325.2828333333333,
                            'obs_dec'   : -10.8525,
                            'obs_mag'   : 21.8,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        measures = update_MPC_obs(self.test_mpcobs_page)

        self.assertEqual(expected_num_srcmeas, len(measures))
        source_measures = SourceMeasurement.objects.filter(body=self.test_body)
        self.assertEqual(expected_num_srcmeas, source_measures.count())
        source_measure = source_measures[len(source_measures) - 1]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test2_multiple_designations(self):
        expected_measures = 23
        measures = update_MPC_obs(self.test_mpcobs_page2)
        self.assertEqual(len(measures), expected_measures)

    def test_repeat_sources(self):
        expected_measures = 11
        total_measures = 23
        expected_frames = 23
        first_date = datetime(1998, 2, 21, 2, 13, 10, 272000)
        last_date = datetime(2018, 7, 10, 3, 35, 44, 448000)

        # Read in old measures
        initial_measures = update_MPC_obs(self.test_mpcobs_page3)
        # update with new ones
        final_measures = update_MPC_obs(self.test_mpcobs_page2)
        self.assertEqual(len(final_measures), expected_measures)

        source_measures = SourceMeasurement.objects.filter(body=self.test_body2)
        sorted_source_measures = sorted(source_measures, key=lambda sm: sm.frame.midpoint)
        self.assertEqual(total_measures, source_measures.count())
        source_measure1 = sorted_source_measures[len(source_measures) - 1]
        source_measure2 = sorted_source_measures[0]
        self.assertEqual(last_date, source_measure1.frame.midpoint)
        self.assertEqual(first_date, source_measure2.frame.midpoint)

        frames = Frame.objects.all()
        self.assertEqual(len(frames), expected_frames)

    def test_packed_name_with_change(self):
        expected_measures = 15

        measures = update_MPC_obs(self.test_mpcobs_page4)
        self.assertEqual(len(measures), expected_measures)


class TestClean_mpcorbit(TestCase):

    def setUp(self):
        # Read and make soup from a static version of the HTML table/page for
        # an object
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_2014UR.html'), 'r')
        test_mpcdb_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.test_elements = parse_mpcorbit(test_mpcdb_page)

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet2016C2.html'), 'r')
        test_mpcdb_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.test_comet_elements = parse_mpcorbit(test_mpcdb_page)

        self.test_hyperbolic_elements = {
                                         'argument of perihelion': '325.96205',
                                         'ascending node': '276.22261',
                                         'eccentricity': '1.0014825',
                                         'epoch': '2018-03-23.0',
                                         'epoch JD': '2458200.5',
                                         'first observation date used': '2017-09-18.0',
                                         'inclination': '142.63838',
                                         'last observation date used': '2018-02-10.0',
                                         'mean anomaly': None,
                                         'mean daily motion': None,
                                         'obj_id': u'A/2017 U7',
                                         'observations used': '87',
                                         'perihelion JD': '2458737.02791',
                                         'perihelion date': '2019-09-10.52791',
                                         'perihelion distance': '6.4186788',
                                         'period': None,
                                         'perturbers coarse indicator': None,
                                         'perturbers precise indicator': '0000',
                                         'radial non-grav. param.': None,
                                         'recip semimajor axis error': None,
                                         'recip semimajor axis future': '-0.00000374',
                                         'recip semimajor axis orig': '0.00011957',
                                         'reference': 'MPEC 2018-E17',
                                         'residual rms': '0.2',
                                         'semimajor axis': None,
                                         'transverse non-grav. param.': None}

        self.expected_params = {
                             'elements_type': 'MPC_MINOR_PLANET',
                             'abs_mag' : '26.6',
                             'argofperih': '222.91160',
                             'longascnode': '24.87559',
                             'eccentricity': '0.0120915',
                             'epochofel': datetime(2016, 1, 13, 0),
                             'meandist': '0.9967710',
                             'orbinc': '8.25708',
                             'meananom': '221.74204',
                             'slope': '0.15',
                             'origin' : 'M',
                             'active' : True,
                             'source_type' : 'N',
                             'discovery_date': datetime(2014, 10, 17, 0),
                             'num_obs': '147',
                             'arc_length': '357',
                             'not_seen' : 5.5,
                             # 'score' : None,
                             'update_time' : datetime(2015, 10, 9, 0),
                             'updated' : True
                             }
        self.expected_comet_params = {
                                        'elements_type': 'MPC_COMET',
                                        'argofperih': '214.01052',
                                        'longascnode' : '24.55858',
                                        'eccentricity' : '1.0000000',
                                        'epochofel': datetime(2016, 4, 19, 0),
                                        'meandist' : None,
                                        'orbinc' : '38.19233',
                                        'meananom': None,
                                        'perihdist' : '1.5671127',
                                        'epochofperih': datetime(2016, 4, 19, 0, 41, 44, int(0.736*1e6)),
                                        'slope': '4.0',
                                        'origin' : 'M',
                                        'active' : True,
                                        'source_type' : 'C',
                                        'discovery_date': datetime(2016, 2, 8, 0),
                                        'num_obs': '89',
                                        'arc_length': '10',
                                        'not_seen' : 6.75,
                                        'update_time' : datetime(2016, 2, 18, 0),
                                        'updated' : True
                                     }
        self.expected_hyperbolic_params = {
                                        'elements_type': 'MPC_COMET',
                                        'argofperih': '325.96205',
                                        'longascnode' : '276.22261',
                                        'eccentricity' : '1.0014825',
                                        'epochofel': datetime(2018, 3, 23, 0),
                                        'meandist' : None,
                                        'orbinc' : '142.63838',
                                        'meananom': None,
                                        'perihdist' : '6.4186788',
                                        'epochofperih': datetime(2019, 9, 10, 12, 40, 11, int(0.424*1e6)),
                                        'slope': '4.0',
                                        'origin' : 'M',
                                        'active' : True,
                                        'source_type' : 'H',
                                        'discovery_date': datetime(2017, 9, 18, 0),
                                        'num_obs': '87',
                                        'arc_length': '145',
                                        'not_seen' : 23.75,
                                        'update_time' : datetime(2018, 2, 10, 0),
                                        'updated' : True
                                     }

        self.maxDiff = None

    @patch('core.views.datetime', MockDateTime)
    def test_clean_2014UR(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        params = clean_mpcorbit(self.test_elements)

        self.assertEqual(self.expected_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_2014UR_no_arclength(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        new_test_elements = self.test_elements
        del new_test_elements['arc length']

        params = clean_mpcorbit(new_test_elements)

        self.assertEqual(self.expected_params, params)

    def test_bad_not_seen(self):

        new_test_elements = self.test_elements
        new_test_elements['last observation date used'] = 'Wibble'
        params = clean_mpcorbit(new_test_elements)

        new_expected_params = self.expected_params
        new_expected_params['not_seen'] = None
        new_expected_params['update_time'] = None
        self.assertEqual(new_expected_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_bad_discovery_date(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        new_test_elements = self.test_elements
        new_test_elements['first observation date used'] = 'Wibble'
        params = clean_mpcorbit(new_test_elements)

        new_expected_params = self.expected_params
        new_expected_params['discovery_date'] = None
        self.assertEqual(new_expected_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_C_2016C2(self):

        MockDateTime.change_datetime(2016, 2, 24, 18, 0, 0)
        params = clean_mpcorbit(self.test_comet_elements)

        self.assertEqual(self.expected_comet_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_A_2017U7(self):

        MockDateTime.change_datetime(2018, 3, 5, 18, 0, 0)
        params = clean_mpcorbit(self.test_hyperbolic_elements)

        self.assertEqual(self.expected_hyperbolic_params, params)


class TestCreate_sourcemeasurement(TestCase):

    def setUp(self):
        # Read in MPC 80 column format observations lines from a static file
        # for testing purposes
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_WSAE9A6.dat'), 'r')
        self.test_obslines = test_fh.readlines()
        test_fh.close()

        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        self.test_body = Body.objects.create(**WSAE9A6_params)

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_N009ags.dat'), 'r')
        self.sat_test_obslines = test_fh.readlines()
        test_fh.close()

        N009ags_params = { 'provisional_name' : 'N009ags',
                         }

        self.sat_test_body = Body.objects.create(**N009ags_params)

        G07212_params = { 'provisional_name' : 'G07212',
                        }

        self.gbot_test_body = Body.objects.create(**G07212_params)

        self.maxDiff = None

    def test_create_nonLCO(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 27, 12, int(0.672*1e6)),
                            'obs_ra'    : 325.2828333333333,
                            'obs_dec'   : -10.8525,
                            'obs_mag'   : 21.8,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        source_measures = create_source_measurement(self.test_obslines[0])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test_create_nonLCO_nocat(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 34,  8, int(0.256*1e6)),
                            'obs_ra'    : 325.28441666666663,
                            'obs_dec'   : -10.857111111111111,
                            'obs_mag'   : 20.9,
                            'filter'    : 'V',
                            'astrometric_catalog' : '',
                            'site_code' : 'G96'
                          }

        source_measures = create_source_measurement(self.test_obslines[1])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test_create_nonLCO_nomag(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 41,  6, int(0.432*1e6)),
                            'obs_ra'    : 325.28599999999994,
                            'obs_dec'   : -10.861583333333332,
                            'obs_mag'   : None,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        source_measures = create_source_measurement(self.test_obslines[2])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test_create_nonLCO_flags(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 9, 54, 16, int(0.416*1e6)),
                            'obs_ra'    : 325.34804166666663,
                            'obs_dec'   : -11.01686111111111,
                            'obs_mag'   : 20.9,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'PPMXL',
                            'site_code' : '474'
                          }

        source_measures = create_source_measurement(self.test_obslines[3])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test_create_blankline(self):

        source_measures = create_source_measurement(self.test_obslines[4])

        self.assertEqual([], source_measures)

    def test_create_LCO_stack(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 23, 24, 46, int(0.4832*1e6)),
                            'obs_ra'    : 325.540625,
                            'obs_dec'   : -11.536666666666667,
                            'obs_mag'   : 21.4,
                            'filter'    : 'R',
                            'astrometric_catalog' : '',
                            'site_code' : 'K93'
                          }

        source_measures = create_source_measurement(self.test_obslines[5])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.STACK_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test_create_LCO_flagI(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : 'I',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 23, 31, 40, int(0.08*1e6)),
                            'obs_ra'    : 325.54225,
                            'obs_dec'   : -11.541111111111112,
                            'obs_mag'   : 21.6,
                            'filter'    : 'R',
                            'astrometric_catalog' : '',
                            'site_code' : 'K93'
                          }

        source_measures = create_source_measurement(self.test_obslines[6])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.SINGLE_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test_create_satellite(self):
        expected_params = { 'body'  : 'N009ags',
                            'flags' : '',
                            'obs_type'  : 'S',
                            'obs_date'  : datetime(2016, 2, 8, 18, 15, 30, int(0.528*1e6)),
                            'obs_ra'    : 228.56833333333333,
                            'obs_dec'   : -9.775,
                            'obs_mag'   : '19',
                            'filter'    : 'R',
                            'astrometric_catalog' : '2MASS',
                            'site_code' : 'C51',
                          }

        expected_extrainfo = '     N009ags  s2016 02 08.76077 1 - 3484.5127 - 5749.6261 - 1405.6769   NEOCPC51'

        source_measures = create_source_measurement(self.sat_test_obslines[0:2])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.SATELLITE_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_extrainfo, source_measure.frame.extrainfo)

    def test_create_non_existant_body(self):

        source_measures = create_source_measurement(self.test_obslines[3].replace('WSAE9A6', 'FOOBAR'))

        self.assertEqual([], source_measures)

    def test_create_whole_file(self):

        source_measures = create_source_measurement(self.test_obslines)
        source_measure = source_measures[0]

        sources = SourceMeasurement.objects.filter(body=self.test_body)
        nonLCO_frames = Frame.objects.filter(frametype=Frame.NONLCO_FRAMETYPE)
        LCO_frames = Frame.objects.filter(frametype__in=[Frame.SINGLE_FRAMETYPE, Frame.STACK_FRAMETYPE])

        self.assertEqual(6, len(sources))
        self.assertEqual(4, len(nonLCO_frames))
        self.assertEqual(2, len(LCO_frames))

    def test_create_duplicates(self):

        source_measures = create_source_measurement(self.test_obslines)
        source_measure = source_measures[0]
        source_measure2 = create_source_measurement(self.test_obslines)

        sources = SourceMeasurement.objects.filter(body=self.test_body)
        nonLCO_frames = Frame.objects.filter(frametype=Frame.NONLCO_FRAMETYPE)
        LCO_frames = Frame.objects.filter(frametype__in=[Frame.SINGLE_FRAMETYPE, Frame.STACK_FRAMETYPE])

        self.assertEqual(6, len(sources))
        self.assertEqual(4, len(nonLCO_frames))
        self.assertEqual(2, len(LCO_frames))

    def test_create_with_trailing_space(self):

        expected_params = { 'body' : 'G07212',
                            'filter' : 'G',
                            'obs_date' : datetime(2017, 11, 2, 4, 10, 16, int(0.32*1e6)),
                            'site_code' : '309',
                            'obs_ra' : 48.408025,
                            'obs_dec'   : 19.463075,
                            'obs_mag'   : 21.4,
                          }

        test_obslines = u"     G07212  'C2017 11 02.17380 03 13 37.926+19 27 47.07         21.4 GUNEOCP309"

        source_measures = create_source_measurement(test_obslines)
        self.assertIsNot(source_measures, False)
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)


class TestFrames(TestCase):
    def setUp(self):
        # Read in MPC 80 column format observations lines from a static file
        # for testing purposes
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_multiframe.dat'), 'r')
        self.test_obslines = test_fh.readlines()
        test_fh.close()

        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        self.test_body = Body.objects.create(**WSAE9A6_params)

        WV2997A_params = { 'provisional_name' : 'WV2997A',
                         }
        self.test_body2 = Body.objects.create(**WV2997A_params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)
        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2015-09-20 13:00:00',
                         'block_end'   : '2015-09-21 03:00:00',
                         'tracking_number' : '00001',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        block_params = { 'telclass' : '0m4',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2017-12-11 13:00:00',
                         'block_end'   : '2017-12-12 03:00:00',
                         'tracking_number' : '522289',
                         'num_exposures' : 5,
                         'exp_length' : 145.0,
                         'active'   : True
                       }
        self.test_block_0m4 = Block.objects.create(**block_params)

        block_params = { 'obstype' : Block.OPT_SPECTRA,
                         'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP_spectra',
                         'block_start' : '2017-12-11 13:00:00',
                         'block_end'   : '2017-12-12 03:00:00',
                         'tracking_number' : '1509481',
                         'num_exposures' : 1,
                         'exp_length' : 1800.0,
                         'active'   : True
                       }
        self.test_spec_block = Block.objects.create(**block_params)

    def test_add_frame(self):
        params = parse_mpcobs(self.test_obslines[-1])
        resp = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K93')
        self.assertEqual(1, frames.count())

    def test_add_frames(self):
        for line in self.test_obslines:
            params = parse_mpcobs(line)
            resp = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K93')
        self.assertEqual(3, frames.count())
        # Did the block get Added
        frames = Frame.objects.filter(sitecode='K93', block__isnull=False)
        # Although there are 4 sources in the file 2 are in the same frame
        self.assertEqual(3, frames.count())

    def test_add_frames_block(self):
        params = {
                    'date_obs': "2015-04-20 21:41:05",
                    'siteid': 'cpt',
                    'encid': 'doma',
                    'telid': '1m0a',
                    'filter_name': 'R',
                    'instrume': "kb70",
                    'origname': "cpt1m010-kb70-20150420-0001-e00.fits",
                    'exptime': '30'
                 }
        frame_params = frame_params_from_block(params, self.test_block)
        frame, frame_created = Frame.objects.get_or_create(**frame_params)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)

    def test_ingest_frames_block(self):
        params = {
                        "DATE_OBS": "2016-06-01T09:43:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00.fits",
                        "EXPTIME" : "30",
                        "GROUPID"   : "TEMP"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME'])/2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, None)

    def test_ingest_frames_block_no_fits_extn(self):
        params = {
                        "DATE_OBS": "2016-06-01T09:43:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00",
                        "EXPTIME" : "30",
                        "GROUPID"   : "TEMP"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME'])/2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].filename, params['ORIGNAME']+'.fits')
        self.assertEqual(frames[0].midpoint, midpoint)

    def test_ingest_frames_block_fwhm(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00.fits",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))

    def test_ingest_frames_banzai_ql(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e11.fits",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 11,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_QL_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].filename, params['ORIGNAME'])

    def test_ingest_frames_banzai_red(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_cpt_0m4_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "cpt",
                        "TELID": "0m4a",
                        "FILTER": "R",
                        "INSTRUME" : "kb96",
                        "ORIGNAME" : "cpt0m407-kb96-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='L09')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'L09')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_elp_0m4_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "elp",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb80",
                        "ORIGNAME" : "elp0m407-kb96-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='V38')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'V38')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_tfn_0m4n1_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "tfn",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb29",
                        "ORIGNAME" : "tfn0m414-kb29-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='Z21')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'Z21')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_tfn_0m4n2_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "tfn",
                        "TELID": "0m4b",
                        "FILTER": "w",
                        "INSTRUME" : "kb88",
                        "ORIGNAME" : "tfn0m410-kb88-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='Z17')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'Z17')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_lsc_0m4n1_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-12T03:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "lsc",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb95",
                        "ORIGNAME" : "lsc0m409-kb95-20171211-0121-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='W89')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'W89')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_lsc_0m4n2_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-12T03:59:28.067",
                        "ENCID": "aqwb",
                        "SITEID": "lsc",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb26",
                        "ORIGNAME" : "lsc0m412-kb26-20171211-0041-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='W79')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'W79')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_spectro_spectrum(self):
        params = {
                    "DATE_OBS": "2018-05-09T13:28:52.383",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "SPECTRUM",
                    "FILTER" : "air     ",
                    "APERTYPE" : "SLIT    ",
                    "APERLEN" : 30.0,
                    "APERWID" : 2.0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0017-e00",
                    "EXPTIME"  : "1800.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1,frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0x2.0AS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e00.fits'))

    def test_ingest_frames_spectro_arc(self):
        params = {
                    "DATE_OBS": "2018-05-09T11:44:33.898",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "ARC",
                    "FILTER" : "air     ",
                    "APERTYPE" : "SLIT    ",
                    "APERLEN" : 30.0,
                    "APERWID" : 2.0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0006-a00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1,frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0x2.0AS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('a00', 'a00.fits'))

    def test_ingest_frames_spectro_lampflat(self):
        params = {
                    "DATE_OBS": "2018-05-09T11:42:18.352",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "LAMPFLAT",
                    "FILTER" : "air",
                    "APERTYPE" : "SLIT",
                    "APERLEN" : 30.0,
                    "APERWID" : 2.0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0005-w00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1,frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0x2.0AS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('w00', 'w00.fits'))

    def test_ingest_frames_spectro_lampflat_badslit(self):
        params = {
                    "DATE_OBS": "2018-05-09T13:28:52.383",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "LAMPFLAT",
                    "FILTER" : "air",
                    "APERTYPE" : "SLIT",
                    "APERLEN" : 30.0,
                    "APERWID" : '',
                    "RLEVEL"  : 0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0017-w00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1,frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0xUNKAS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('w00', 'w00.fits'))

    def test_ingest_frames_spectro_lampflat_badslit2(self):
        params = {
                    "DATE_OBS": "2018-05-09T13:28:52.383",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "LAMPFLAT",
                    "FILTER" : "air",
                    "APERTYPE" : "SLIT",
                    "APERLEN" : 30.0,
                    "APERWID" : 'UNKNOWN',
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0017-w00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1,frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0xUNKAS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('w00', 'w00.fits'))

    def test_add_source_measurements(self):
        # Test we don't get duplicate frames when adding new source measurements
        # if the sources are in the same frame
        for line in self.test_obslines:
            resp = create_source_measurement(line, self.test_block)
        frames = Frame.objects.filter(sitecode='K93', block__isnull=False)
        self.assertEqual(3, frames.count())

    def test_add_source_measurements_twice(self):
        # Test we don't get duplicate frames when adding new source measurements
        # if the sources are in the same frame
        for line in self.test_obslines:
            resp = create_source_measurement(line, self.test_block)
        # And we forgot that we've already done this, so we do it again
        for line in self.test_obslines:
            resp = create_source_measurement(line, self.test_block)
        frames = Frame.objects.filter(sitecode='K93', block__isnull=False)
        # We should get the same number in the previous test,
        # i.e. on the second run the frames are not created
        self.assertEqual(3, frames.count())


@patch('core.views.datetime', MockDateTime)
@patch('astrometrics.time_subs.datetime', MockDateTime)
class TestClean_crossid(TestCase):

    def setUp(self):
        MockDateTime.change_datetime(2015, 11, 5, 18, 0, 0)

    def test_regular_asteroid(self):
        crossid = [u'P10p9py', u'2015 VV1', '', u'(Nov. 5.30 UT)']
        expected_params = { 'active' : False,
                            'name' : '2015 VV1',
                            'source_type' : 'A'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_NEO_recent_confirm(self):
        crossid = [u'WV82468', u'2015 VB2', u'MPEC 2015-V51', u'(Nov. 5.60 UT)']
        expected_params = { 'active' : True,
                            'name' : '2015 VB2',
                            'source_type' : 'N'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_NEO_older_confirm(self):
        crossid = [u'P10o0Ha', u'2015 SE20', u'MPEC 2015-T29', u'(Oct. 8.59 UT)']
        expected_params = { 'active' : False,
                            'name' : '2015 SE20',
                            'source_type' : 'N'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_did_not_exist(self):
        crossid = [u'WTB842B', 'doesnotexist', '', u'(Oct. 9.19 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'X'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_not_confirmed(self):
        crossid = [u'P10oYZI', 'wasnotconfirmed', '', u'(Nov. 4.81 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'U'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_not_interesting(self):
        crossid = [u'P10oYZI', '', '', u'(Nov. 4.81 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'W'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_minor_planet(self):
        crossid = [u'A10422t', 'wasnotminorplanet', '', u'(Sept. 20.89 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'J'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_cbet_recent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'CBET 5432', u'(Nov. 5.49 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_cbet_notrecent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'CBET 5432', u'(Nov. 1.49 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_iauc_recent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'IAUC-', u'(Nov. 5.49 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_iauc_notrecent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'IAUC-', u'(Nov. 1.49 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_asteroid_number(self):
        crossid = [u'LM02L2J', u'C/2015 TQ209', u'IAUC 2015-', u'(Oct. 24.07 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 TQ209',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_mpec_recent(self):
        crossid = [u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Nov. 3.63 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_mpec_notrecent(self):
        crossid = [u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Oct. 18.63 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_hyperbolic_asteroid1(self):
        crossid = [u'ZC82561', u'A/2018 C2', u'MPEC 2018-E18', u'(Nov. 4.95 UT)']
        expected_params = { 'active' : True,
                            'name' : 'A/2018 C2',
                            'source_type' : 'H'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_hyperbolic_asteroid2(self):
        crossid = [u'P10EwQh', u'A/2017 U7', u'MPEC 2018-E17', u'(Nov. 4.94 UT)']
        expected_params = { 'active' : True,
                            'name' : 'A/2017 U7',
                            'source_type' : 'H'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_new_year_switchover(self):
        MockDateTime.change_datetime(2016, 1, 1, 0, 30, 0)
        crossid = [u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Oct. 18.63 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_bad_date(self):
        MockDateTime.change_datetime(2016, 3, 1, 0, 30, 0)
        crossid = [u'P10sKEk', u'2016 CP264', '', u'(Feb. 30.00 UT)']
        expected_params = { 'active' : False,
                            'name' : '2016 CP264',
                            'source_type' : 'A'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_extra_spaces(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)
        crossid = [u'P10tmAL ', u'2013 AM76', '', u'(Mar.  9.97 UT)']
        expected_params = { 'active' : False,
                            'name' : '2013 AM76',
                            'source_type' : 'A'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)


class TestSummarise_Block_Efficiency(TestCase):

    def setUp(self):
        # Initialise with a test body, three test proposals and several blocks.
        # The first proposal has two blocks (one observed, one not), the 2nd one
        # has a block scheduled but not observed and the third has no blocks
        # scheduled.
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

    def test_proposal_with_scheduled_and_obs_blocks(self):
        proposal_params = { 'code'  : 'LCO2015A-009',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal = Proposal.objects.create(**proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'proposal' : proposal,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        block_params2 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'proposal' : proposal,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        test_block2 = Block.objects.create(**block_params2)

        expected_summary = [{ 'Not Observed': 1,
                              'Observed': 1,
                              'proposal': u'LCO2015A-009'}
                           ]

        summary = summarise_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_proposal_with_scheduled_blocks(self):
        proposal_params = { 'code'  : 'LCO2015B-005',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal = Proposal.objects.create(**proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'proposal' : proposal,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        expected_summary = [{ 'Not Observed': 1,
                              'Observed': 0,
                              'proposal': u'LCO2015B-005'}
                           ]

        summary = summarise_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_multiple_proposals_with_scheduled_and_obs_blocks(self):
        proposal_params = { 'code'  : 'LCO2015A-009',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal1 = Proposal.objects.create(**proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'proposal' : proposal1,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        block_params2 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'proposal' : proposal1,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        test_block2 = Block.objects.create(**block_params2)

        proposal_params = { 'code'  : 'LCO2015B-005',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal2 = Proposal.objects.create(**proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'proposal' : proposal2,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        expected_summary = [
                             { 'Not Observed': 1,
                               'Observed': 0,
                               'proposal': u'LCO2015B-005'},
                            { 'Not Observed': 1,
                               'Observed': 1,
                               'proposal': u'LCO2015A-009'}

                           ]

        summary = summarise_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_proposal_with_no_blocks(self):
        proposal_params = { 'code'  : 'LCO2016A-021',
                            'title' : 'LCOGT NEO Follow-up Network (16A)'
                          }
        proposal = Proposal.objects.create(**proposal_params)

        expected_summary = []

        summary = summarise_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_no_proposals(self):
        expected_summary = []

        summary = summarise_block_efficiency()

        self.assertEqual(expected_summary, summary)


class TestCheckCatalogAndRefitNew(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')

#        self.phot_tests_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
#        self.test_catalog = os.path.join(self.phot_tests_dir, 'oracdr_test_catalog.fits')
        self.configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

        self.debug_print = False

        original_test_banzai_fits = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        original_test_cat_bad_wcs = os.path.abspath(os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits'))
        self.test_cat_good_wcs_not_BANZAI = os.path.abspath(os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits'))
        self.test_fits_e10 = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10.fits'))

        self.test_banzai_fits = os.path.abspath(os.path.join(self.temp_dir, 'banzai_test_frame.fits'))
        self.test_cat_bad_wcs = os.path.abspath(os.path.join(self.temp_dir, 'oracdr_test_catalog.fits'))

        shutil.copyfile(original_test_banzai_fits, self.test_banzai_fits)
        shutil.copyfile(original_test_cat_bad_wcs, self.test_cat_bad_wcs)

        body_params = {     'provisional_name': 'P10w5z5',
                            'origin': 'M',
                            'source_type': 'U',
                            'elements_type': 'MPC Minor Planet',
                            'active': False,
                            'epochofel': '2016-07-11 00:00:00',
                            'orbinc': 6.35992,
                            'longascnode': 108.82267,
                            'argofperih': 202.15361,
                            'eccentricity': 0.384586,
                            'meandist': 2.3057577,
                            'meananom': 352.55523,
                            'abs_mag': 21.3,
                            'slope': 0.15,
                        }
        self.test_body, created = Body.objects.get_or_create(**body_params)

        proposal_params = { 'code': 'test',
                            'title': 'test',
                            'pi':'sgreenstreet@lcogt.net',
                            'tag': 'LCOGT',
                            'active': True
                          }
        self.test_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        block_params = {    'telclass': '1m0',
                            'site': 'K92',
                            'body': self.test_body,
                            'proposal': self.test_proposal,
                            'groupid': 'P10w5z5_cpt_20160801',
                            'block_start': datetime(2016, 8, 1, 17),
                            'block_end': datetime(2016, 8, 2, 4),
                            'tracking_number': '0013',
                            'num_exposures': 5,
                            'exp_length': 225.0,
                            'num_observed': 1,
                            'when_observed': datetime(2016, 8, 2, 2, 15, 0),
                            'active': False,
                            'reported': True,
                            'when_reported': datetime(2016, 8, 2, 4, 44, 0)
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)

        frame_params = {    'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'banzai_test_frame.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.390,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.temp_dir)
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print:
                    print("Removed", self.temp_dir)
            except OSError:
                print("Error removing temporary test directory", self.temp_dir)

    def test_check_catalog_and_refit_new_good(self):

        expected_status_and_num_frames = (os.path.abspath(os.path.join(self.temp_dir, 'banzai_test_frame_ldac.fits')), 1)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_bad_astrometric_fit(self):

        expected_status_and_num_frames = (-1, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_cat_bad_wcs)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_cattype_not_BANZAI(self):

        expected_status_and_num_frames = (-99, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_cat_good_wcs_not_BANZAI)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_BANZAI_catalog_found(self):

        expected_status_and_num_frames = (os.path.abspath(os.path.join(self.temp_dir, 'banzai_test_frame.fits'.replace('.fits', '_ldac.fits'))), 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_matching_image_file_found(self):

        expected_fits_file = self.test_banzai_fits.replace('.fits', '.fits[SCI]')

        fits_file = find_matching_image_file(self.test_banzai_fits)

        self.assertEqual(expected_fits_file, fits_file)

    def test_matching_image_file_not_found(self):

        expected_fits_file = None

        fits_file = find_matching_image_file(self.test_banzai_fits.replace('neox', 'neoxs'))

        self.assertEqual(expected_fits_file, fits_file)

        expected_fits_file = None

        fits_file = find_matching_image_file(self.test_banzai_fits.replace('frame.fits', 'frames.fits'))

        self.assertEqual(expected_fits_file, fits_file)

    def test_matching_image_file_not_found_check_catalog_and_refit_new(self):

        expected_status_and_num_frames = (-1, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('neox', 'neoxs'))

        self.assertEqual(expected_status_and_num_frames, status)

        expected_status_and_num_frames = (-1, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('frame.fits', 'frames.fits'))

        self.assertEqual(expected_status_and_num_frames, status)

    def test_run_sextractor_good(self):

        expected_status_and_catalog = (0, os.path.join(self.temp_dir, os.path.basename(self.test_banzai_fits).replace('.fits', '_ldac.fits')))

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        self.assertEqual(expected_status_and_catalog, (status, new_ldac_catalog))

    def test_run_sextractor_bad(self):

        expected_status_and_catalog = (1, -4)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_cat_bad_wcs)

        self.assertEqual(expected_status_and_catalog, (status, new_ldac_catalog))

    @patch('core.views.run_sextractor_make_catalog', mock_run_sextractor_make_catalog)
    def test_cannot_run_sextractor(self):

        expected_num_new_frames_created = 0

        status, num_new_frames_created = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(-4, status)
        self.assertEqual(expected_num_new_frames_created, num_new_frames_created)

    def test_find_block_for_frame_good(self):

        expected_block = self.test_block

        block = find_block_for_frame(self.test_banzai_fits)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_multiple_frames(self):

        frame_params_2 = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'banzai_test_frame.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.380,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame_2, created = Frame.objects.get_or_create(**frame_params_2)

        expected_block = None

        block = find_block_for_frame(self.test_banzai_fits)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_DNE_multiple_frames(self):

        frame_params = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'example-sbig-e00.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.390,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

        frame_params_2 = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'example-sbig-e00.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.380,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame_2, created = Frame.objects.get_or_create(**frame_params_2)

        expected_block = None

        block = find_block_for_frame(self.test_fits_e10)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_DNE(self):

        expected_block = None

        block = find_block_for_frame(self.test_fits_e10)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_check_catalog_and_refit_new(self):

        expected_status_and_num_frames = (-3, 0)

        block = Block.objects.last()
        block.delete()

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_make_new_catalog_entry_good(self):

        expected_num_new_frames = 1

        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        header = get_catalog_header(fits_header, cattype)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

    def test_make_new_catalog_entry_multiple_frames(self):

        frame_params_2 = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'banzai_test_frame_ldac.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.380,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame_2, created = Frame.objects.get_or_create(**frame_params_2)

        expected_num_new_frames = 0

        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        header = get_catalog_header(fits_header, cattype)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        self.assertEqual(expected_num_new_frames, num_new_frames)

    def test_make_new_catalog_entry_not_needed(self):

        expected_num_new_frames = 0

        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        header = get_catalog_header(fits_header, cattype)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        self.assertEqual(expected_num_new_frames, num_new_frames)


class TestUpdate_Crossids(TestCase):

    @classmethod
    def setUpTestData(cls):
        params = {  'provisional_name' : 'LM05OFG',
                    'abs_mag'       : 24.7,
                    'slope'         : 0.15,
                    'epochofel'     : datetime(2016, 7, 31, 00, 0, 0),
                    'meananom'      :   8.5187,
                    'argofperih'    : 227.23234,
                    'longascnode'   :  57.83134,
                    'orbinc'        : 5.40829,
                    'eccentricity'  : 0.6914565,
                    'meandist'      : 2.8126642,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'G',
                    }
        cls.body, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name': 'ZC82561',
                    'provisional_packed': None,
                    'origin': 'M',
                    'source_type': 'U',
                    'elements_type': None,
                    'active': False,
                    'fast_moving': False,
                    'urgency': None,
                    'epochofel': None,
                    'orbinc': None,
                    'longascnode': None,
                    'argofperih': None,
                    'eccentricity': None,
                    'meandist': None,
                    'meananom': None,
                    'perihdist': None,
                    'epochofperih': None,
                    'abs_mag': None,
                    'slope': None,
                    'score': None,
                    'discovery_date': None,
                    'num_obs': None,
                    'arc_length': None,
                    'not_seen': None,
                    'updated': False,
                    'ingest': datetime(2018, 5, 24, 16, 45, 42),
                    'update_time': None
                    }
        cls.blank_body, created = Body.objects.get_or_create(**params)

    def setUp(self):
        self.body.refresh_from_db()

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_goldstone_is_not_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('G', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_arecibo_comet_is_not_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'C/2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.source_type = u'C'
        self.body.origin = u'A'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('C', body.source_type)
        self.assertEqual('A', body.origin)
        self.assertEqual('C/2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_jointradar_neo_is_not_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.origin = u'R'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('R', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_old_mpc_neo_is_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.origin = u'M'
        self.assertEqual(True, self.body.active)
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_new_mpc_neo_is_not_overridden(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 11, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.origin = u'M'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_artsat(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 9, 21, 10, 40, 0)

        crossid_info = [u'A10422t', 'wasnotminorplanet', '', u'(Sept. 20.89 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'A10422t'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('J', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_hyperbolic_ast(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 9, 21, 10, 40, 0)

        crossid_info = [u'ZC99999', u'A/2018 C2', u'MPEC 2018-E18', u'(Mar. 4.95 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'ZC99999'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('H', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('A/2018 C2', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_new_comet_has_epochperih(self):

        # Remove other Body to check we don't create extra
        self.blank_body.delete()

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 1, 20, 10, 40, 0)

        crossid_info = ['P10G50L', 'C/2018 A5', 'MPEC 2018-B20', '(Jan. 17.81 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'P10G50L'
        self.body.epochofel = datetime(2018, 1, 2, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None

        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(1, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('C', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('C/2018 A5', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)
        self.assertIsNot(None, body.perihdist)
        self.assertAlmostEqual(2.6725494646558405, body.perihdist, 7)
        self.assertEqual(datetime(2017, 9, 14, 22, 34, 45, 428836), body.epochofperih)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_hyperbolic_ast_blank_body(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 3,  8, 10, 40, 0)

        crossid_info = [u'ZC82561', u'A/2018 C2', u'MPEC 2018-E18', u'(Mar. 4.95 UT)']

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.blank_body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('H', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('A/2018 C2', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)

class TestStoreDetections(TestCase):

    def setUp(self):

        self.phot_tests_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_mtds = os.path.join(self.phot_tests_dir, 'elp1m008-fl05-20160225-0095-e90.mtds')
        # Initialise with three test bodies a test proposal and several blocks.
        # The first body has a provisional name (e.g. a NEO candidate), the
        # other 2 do not (e.g. Goldstone targets)
        params = {  'provisional_name' : 'P10sSA6',
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
        self.body_with_provname, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015B-005',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        block_params = { 'telclass' : '1m0',
                         'site'     : 'ELP',
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_CPT-20150420',
                         'block_start' : '2016-02-26 03:00:00',
                         'block_end'   : '2016-02-26 13:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        frame_params = { 'block'    : self.test_block,
                         'filename' : 'elp1m008-fl05-20160225-0095-e90.fits',
                         'sitecode' : 'V37',
                         'midpoint' : datetime(2016, 2, 26, 3, 44, 42)
                       }

        self.test_frame = Frame.objects.create(**frame_params)

    def test_store_detections(self):
        expected_num_cands = 23

        store_detections(self.test_mtds)

        cands = Candidate.objects.all()
        self.assertEqual(expected_num_cands, len(cands))


class Test_Generate_New_Candidate_Id_Blank(TestCase):

    def test_no_discoveries(self):
        expected_id = 'LNX0001'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)

    def test_no_discoveries_with_prefix(self):
        expected_id = 'NEOX001'

        new_id = generate_new_candidate_id('NEOX')

        self.assertEqual(expected_id, new_id)

    def test_no_discoveries_other_bodies(self):

        params = {  'provisional_name' : 'LCOTL01',
                    'origin' : 'L'
                 }
        body = Body.objects.create(**params)

        expected_id = 'LNX0001'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)


class Test_Generate_New_Candidate_Id(TestCase):

    def setUp(self):

        params = { 'provisional_name' : 'LNX0001',
                   'origin' : 'L',
                   'ingest' : datetime(2017, 1, 1)
                 }
        body = Body.objects.create(**params)

    def test_one_body(self):
        expected_id = 'LNX0002'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)

    def test_one_body_new_prefix(self):
        expected_id = 'LCOTL01'

        new_id = generate_new_candidate_id('LCOTL')

        self.assertEqual(expected_id, new_id)

    def test_three_body(self):
        params = { 'provisional_name' : 'LNX0002',
                   'origin' : 'L',
                   'ingest' : datetime(2017, 1, 2)
                 }

        body = Body.objects.create(**params)

        params = { 'provisional_name' : 'LNX0003',
                   'origin' : 'L',
                   'ingest' : datetime(2017, 1, 1, 12)
                 }

        body = Body.objects.create(**params)

        expected_id = 'LNX0004'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)
        self.assertEqual(3, Body.objects.count())


class Test_Add_New_Taxonomy_Data(TestCase):

    def setUp(self):

        params = { 'name' : '980',
                   'provisional_name' : 'LNX0003',
                   'origin' : 'L',
                 }
        self.body = Body.objects.create(pk=1, **params)

        tax_params = {'body'          : self.body,
                      'taxonomic_class' : 'S3',
                      'tax_scheme'    :   'Ba',
                      'tax_reference' : 'PDS6',
                      'tax_notes'     : '7I',
                      }
        self.test_spectra = SpectralInfo.objects.create(pk=1, **tax_params)

    def test_one_body(self):
        expected_res = True
        test_obj = ['LNX0003', 'SU', "T", "PDS6", "7G"]
        new_tax = update_taxonomy(test_obj)

        self.assertEqual(expected_res, new_tax)

    def test_new_target(self):
        expected_res = False
        test_obj = ['4702', 'S', "B", "PDS6", "s"]
        new_tax = update_taxonomy(test_obj)

        self.assertEqual(expected_res, new_tax)

    def test_same_data(self):
        expected_res = False
        test_obj = ['980', 'S3', "Ba", "PDS6", "7I"]
        new_tax = update_taxonomy(test_obj)

        self.assertEqual(expected_res, new_tax)

    def test_same_data_twice(self):
        expected_res = False
        test_obj = ['980', 'SU', "T", "PDS6", "7G"]
        new_tax = update_taxonomy(test_obj)
        new_tax = update_taxonomy(test_obj)

        self.assertEqual(expected_res, new_tax)


class Test_Add_External_Spectroscopy_Data(TestCase):

    def setUp(self):

        params = { 'name' : '980',
                   'provisional_name' : 'LNX0003',
                   'origin' : 'L',
                   'active' : True,
                 }
        self.body = Body.objects.create(pk=1, **params)

        spec_params = {'body'          : self.body,
                'spec_wav'      : 'Vis',
                'spec_vis'      : 'spex/sp233/a265962.sp233.txt',
                'spec_ref'      : 'sp[234]',
                'spec_source'   : 'S',
                'spec_date'     : '2017-09-25',
                      }
        self.test_spectra = PreviousSpectra.objects.create(pk=1, **spec_params)

    def test_same_body_different_wavelength(self):
        expected_res = True
        test_obj = ['LNX0003', 'NIR', '', "spex/sp233/a416584.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'S', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_same_body_older(self):
        expected_res = False
        test_obj = ['980', 'Vis', 'spex/sp233/a416584.sp234.txt', "", "sp[24]", datetime.strptime('2015-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'S', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_same_body_newer(self):
        expected_res = True
        test_obj = ['980', 'Vis', 'spex/sp233/a416584.sp234.txt', "", "sp[24]", datetime.strptime('2017-12-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'S', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_same_body_different_source(self):
        expected_res = True
        test_obj = ['980', 'Vis', '2014/09/1999sh10.png', "", "MANOS Site", datetime.strptime('2015-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'M', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_new_body(self):
        expected_res = False
        test_obj = ['9801', 'Vis', '2014/09/1999sh10.png', "", "MANOS Site", datetime.strptime('2015-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'M', dbg=True)

        self.assertEqual(expected_res, new_spec)


class TestCreateStaticSource(TestCase):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.test_flux_standards = fetch_flux_standards(test_flux_page)

        solar_standards_test = os.path.join('astrometrics', 'tests', 'solar_standards_test_list.dat')
        self.test_solar_analogs = read_solar_standards(solar_standards_test)

        self.maxDiff = None
        self.precision = 10

    def test_num_created(self):
        expected_created = 3

        num_created = create_calib_sources(self.test_flux_standards)

        self.assertEqual(expected_created, num_created)
        self.assertEqual(expected_created, StaticSource.objects.count())

    def test_correct_units(self):
        expected_num = 3
        expected_src1_ra = ((((49.42/60.0)+1.0)/60.0)+0)*15.0
        expected_src1_dec = -((((39.0/60.0)+1.0)/60.0)+3.0)
        expected_src3_ra = ((((24.30/60.0)+56.0)/60.0)+5)*15.0
        expected_src3_dec = -((((28.8/60.0)+51.0)/60.0)+27.0)

        num_created = create_calib_sources(self.test_flux_standards)

        cal_sources = StaticSource.objects.filter(source_type=StaticSource.FLUX_STANDARD)
        self.assertEqual(expected_num, cal_sources.count())
        self.assertAlmostEqual(expected_src1_ra, cal_sources[0].ra, self.precision)
        self.assertAlmostEqual(expected_src1_dec, cal_sources[0].dec, self.precision)
        self.assertAlmostEqual(expected_src3_ra, cal_sources[2].ra, self.precision)
        self.assertAlmostEqual(expected_src3_dec, cal_sources[2].dec, self.precision)

    def test_solar_standards(self):
        expected_num = 46
        expected_src1_name = 'Landolt SA93-101'
        expected_src1_ra = ((((18.00/60.0)+53.0)/60.0)+1)*15.0
        expected_src1_dec = ((((25.0/60.0)+22.0)/60.0)+0.0)
        expected_src1_sptype = 'G2V'

        num_created = create_calib_sources(self.test_solar_analogs, cal_type=StaticSource.SOLAR_STANDARD)

        cal_sources = StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD)
        self.assertEqual(expected_num, cal_sources.count())
        self.assertEqual(expected_src1_name, cal_sources[0].name)
        self.assertEqual(expected_src1_sptype, cal_sources[0].spectral_type)
        self.assertAlmostEqual(expected_src1_ra, cal_sources[0].ra, self.precision)
        self.assertAlmostEqual(expected_src1_dec, cal_sources[0].dec, self.precision)


class TestFindBestFluxStandard(TestCase):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.flux_standards = fetch_flux_standards(test_flux_page)
        num_created = create_calib_sources(self.flux_standards)

        self.maxDiff = None
        self.precision = 8

    def test_FTN(self):
        expected_standard = StaticSource.objects.get(name='HR9087')
        expected_params = { 'separation_rad' : 0.9379758789119819}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2017, 11, 15, 1, 10, 0)
        close_standard, close_params = find_best_flux_standard('F65', utc_date)

        self.assertEqual(expected_standard, close_standard)
        for key in expected_params:
            if '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])

    def test_FTS(self):
        expected_standard = StaticSource.objects.get(name='CD-34d241')
        expected_params = { 'separation_rad' : 0.11565764559405214}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2017, 9, 27, 1, 10, 0)
        close_standard, close_params = find_best_flux_standard('E10', utc_date)

        self.assertEqual(expected_standard, close_standard)
        for key in expected_params:
            if '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])


class TestFindBestSolarAnalog(TestCase):

    def setUp(self):

        self.maxDiff = None
        self.precision = 8

    @classmethod
    def setUpTestData(cls):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        cls.flux_standards = fetch_flux_standards(test_flux_page)
        cls.num_flux_created = create_calib_sources(cls.flux_standards)

        test_file = os.path.join('astrometrics', 'tests', 'solar_standards_test_list.dat')
        cls.test_solar_analogs = read_solar_standards(test_file)
        cls.num_solar_created = create_calib_sources(cls.test_solar_analogs, cal_type=StaticSource.SOLAR_STANDARD)
        params = {
                 'name': '1093',
                 'origin': 'M',
                 'source_type': 'A',
                 'elements_type': 'MPC_MINOR_PLANET',
                 'epochofel': datetime(2018, 3, 23, 0, 0),
                 'orbinc': 25.21507,
                 'longascnode': 55.63599,
                 'argofperih': 251.40338,
                 'eccentricity': 0.2712664,
                 'meandist': 3.1289388,
                 'meananom': 211.36057,
                 'abs_mag': 8.83,
                 'slope': 0.15,
                 'num_obs': 2187,
                }
        cls.test_body, created = Body.objects.get_or_create(pk=1, **params)

    def test_ingest(self):
        calib_sources = StaticSource.objects.all()
        flux_standards = calib_sources.filter(source_type=StaticSource.FLUX_STANDARD)
        solar_standards = calib_sources.filter(source_type=StaticSource.SOLAR_STANDARD)

        self.assertEqual(self.num_flux_created+self.num_solar_created, calib_sources.count())
        self.assertEqual(self.num_flux_created, flux_standards.count())
        self.assertEqual(self.num_solar_created, solar_standards.count())

    def test_FTN(self):
        expected_ra = 2.7772337523336565
        expected_dec = 0.6247970652631909
        expected_standard = StaticSource.objects.get(name='35 Leo')
        expected_params = { 'separation_deg' : 13.031726234959416}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2017, 11, 15, 14, 0, 0)
        emp = compute_ephem(utc_date, model_to_dict(self.test_body), 'F65', perturb=False)
        self.assertAlmostEqual(expected_ra, emp[1], self.precision)
        self.assertAlmostEqual(expected_dec, emp[2], self.precision)
        close_standard, close_params = find_best_solar_analog(emp[1], emp[2])

        self.assertEqual(expected_standard, close_standard)
        for key in expected_params:
            if '_deg' in key or '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])

    def test_FTS(self):
        expected_ra = 4.334041503242261
        expected_dec = -0.3877173805762358
        expected_standard = StaticSource.objects.get(name='HD 140990')
        expected_params = { 'separation_deg' : 10.838361371951908}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2014, 4, 20, 13, 30, 0)
        emp = compute_ephem(utc_date, model_to_dict(self.test_body), 'E10', perturb=False)
        self.assertAlmostEqual(expected_ra, emp[1], self.precision)
        self.assertAlmostEqual(expected_dec, emp[2], self.precision)
        close_standard, close_params = find_best_solar_analog(emp[1], emp[2])

        self.assertEqual(expected_standard, close_standard)
        for key in expected_params:
            if '_deg' in key or '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])

    def test_FTS_no_match(self):
        expected_ra = 5.840671145434903
        expected_dec = -0.9524603478856751
        expected_standard = None
        expected_params = {}

        utc_date = datetime(2020, 9, 5, 13, 30, 0)
        emp = compute_ephem(utc_date, model_to_dict(self.test_body), 'E10', perturb=False)
        self.assertAlmostEqual(expected_ra, emp[1], self.precision)
        self.assertAlmostEqual(expected_dec, emp[2], self.precision)
        close_standard, close_params = find_best_solar_analog(emp[1], emp[2], min_sep=5.0)

        self.assertEqual(expected_standard, close_standard)
        self.assertEqual(expected_params, close_params)


class Test_Export_Measurements(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')

        self.debug_print = False
        self.maxDiff = None

    @classmethod
    def setUpTestData(cls):
        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        cls.test_body = Body.objects.create(**WSAE9A6_params)

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_WSAE9A6.dat'), 'r')
        test_obslines = test_fh.readlines()
        test_fh.close()
        source_measures = create_source_measurement(test_obslines)

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print: print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)

    def test1(self):
        expected_num_sources = 6
        sources = SourceMeasurement.objects.all()
        self.assertEqual(expected_num_sources, sources.count())

    def test_export(self):
        expected_filename = os.path.join(self.test_dir, 'WSAE9A6.mpc')
        expected_num_lines = 6

        body = Body.objects.get(provisional_name='WSAE9A6')
        filename, num_lines = export_measurements(body.id, self.test_dir)

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_num_lines, num_lines)
