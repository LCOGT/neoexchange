'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import os
from datetime import datetime
from unittest import skipIf
import tempfile
from glob import glob

from django.test import TestCase
from django.forms.models import model_to_dict
from bs4 import BeautifulSoup
from mock import patch
from astropy.io import fits

from neox.tests.mocks import MockDateTime, mock_check_request_status, mock_check_for_images, \
    mock_check_request_status_null, mock_check_for_2_images, mock_check_for_images_millisecs, \
    mock_check_for_images_bad_date, mock_ingest_frames

#Import module to test
from astrometrics.ephem_subs import call_compute_ephem, determine_darkness_times
from astrometrics.sources_subs import parse_mpcorbit, parse_mpcobs
from core.views import home, clean_NEOCP_object, save_and_make_revision, \
    update_MPC_orbit, check_for_block, clean_mpcorbit, \
    create_source_measurement, block_status, clean_crossid, create_frame, \
    frame_params_from_block, schedule_check, summarise_block_efficiency, \
    check_catalog_and_refit
from core.models import Body, Proposal, Block, SourceMeasurement, Frame
from core.forms import EphemQuery



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
        obj_id ='N007riz'
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
        self.assertEqual(True,created)
        resp = save_and_make_revision(body,elements)
        # We are saving all the detailing elements
        self.assertEqual(True,resp)

    def test_revise_N007riz(self):
        self.save_N007riz()
        obj_id ='N007riz'
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
        resp = save_and_make_revision(body,elements)
        # Saving the new elements
        self.assertEqual(True,resp)

    def test_update_MPC_duplicate(self):
        self.save_N007riz()
        obj_id ='N007riz'
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
        resp = save_and_make_revision(body,elements)
        # Need to call full_clean() to validate the fields as this is not
        # done on save() (called by get_or_create() or save_and_make_revision())
        body.full_clean()
        # We are saving all the detailing elements
        self.assertEqual(True,resp)

        # Test it came from LCOGT as a discovery
        self.assertEqual('L', body.origin)
        self.assertEqual('D', body.source_type)


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

    def test_body_does_not_exist(self):

        new_body = self.body_no_provname2
        new_body.provisional_name = 'Wibble'
        params = { 'site_code' : 'V37'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_id' : self.body_no_provname1.current_name() + '_ELP-20141121'
                    }
        expected_state = 3

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    @patch('core.views.check_request_status', mock_check_request_status)
    @patch('core.views.check_for_images', mock_check_for_images)
    def test_block_update_active(self):
        resp = block_status(1)
        self.assertTrue(resp)

    @patch('core.views.check_request_status', mock_check_request_status)
    @patch('core.views.check_for_images', mock_check_for_2_images)
    def test_block_update_active(self):
        resp = block_status(1)
        self.assertFalse(resp)

    @skipIf(True, "Edward needs to fix...")
    @patch('core.views.check_request_status', mock_check_request_status)
    @patch('core.views.check_for_images', mock_check_for_images)
    def test_block_update_not_active(self):
        resp = block_status(2)
        self.assertFalse(resp)

    @patch('core.views.check_request_status', mock_check_request_status)
    @patch('core.views.check_for_images', mock_check_for_images)
    @patch('core.views.ingest_frames', mock_ingest_frames)
    def test_block_update_check_status_change(self):
        blockid = self.test_block6.id
        resp = block_status(blockid)
        myblock = Block.objects.get(id=blockid)
        self.assertFalse(myblock.active)

    @patch('core.views.check_request_status', mock_check_request_status_null)
    @patch('core.views.check_for_images', mock_check_for_images)
    def test_block_update_check_no_obs(self):
        blockid = self.test_block6.id
        resp = block_status(blockid)
        self.assertFalse(resp)

    @patch('core.views.check_request_status', mock_check_request_status)
    @patch('core.views.check_for_images', mock_check_for_images_millisecs)
    @patch('core.views.ingest_frames', mock_ingest_frames)
    def test_block_update_millisecs(self):
        blockid = self.test_block5.id
        resp = block_status(blockid)
        self.assertTrue(resp)

    @patch('core.views.check_request_status', mock_check_request_status)
    @patch('core.views.check_for_images', mock_check_for_images_bad_date)
    def test_block_update_bad_datestamp(self):
        blockid = self.test_block5.id
        resp = block_status(blockid)
        self.assertFalse(resp)

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
        params['epochofperih']  = datetime(2017, 5, 17)
        self.body_good_elemtype, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        self.maxDiff = None

    def test_mp_good(self):

        data = { 'site_code' : 'Q63',
                 'utc_date' : datetime(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.099556975068584,
                        'speed': 2.901241169520825,
                        'slot_length': 20,
                        'exp_count': 19,
                        'exp_length': 40.0,
                        'schedule_ok': True,
                        'site_code': data['site_code'],
                        'proposal_code': data['proposal_code'],
                        'group_id': self.body_mp.current_name() + '_' + data['site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d'),
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:00:00',
                        'end_time': '2016-04-06T19:10:00',
                        'mid_time': '2016-04-06T14:05:00',
                        'ra_midpoint': 3.3121839503195525,
                        'dec_midpoint': -0.16049303559750142,
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)

    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_B_semester(self):
        MockDateTime.change_datetime(2016, 3, 31, 22, 0, 0)

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2016, 4, 1),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time' : '2016-03-31T17:40:00',
                        'end_time'   : '2016-03-31T23:59:59',
                        'exp_count'  : 26,
                        'exp_length' : 25.0,
                        'mid_time': '2016-03-31T20:49:59.500000',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

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
                        'exp_count'  : 26,
                        'exp_length' : 25.0,
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
        self.assertAlmostEqual(expected_resp['magnitude'], resp['magnitude'],2)

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
                             'epochofel': datetime(2016,01,13,0),
                             'meandist': 0.9967710,
                             'orbinc': 8.25708,
                             'meananom': 221.74204,
                             'num_obs': None , # '147',
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

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_MPC(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(self.expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in self.expected_elements:
            if key not in self.nocheck_keys and key !='id':
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
            if key not in self.nocheck_keys and key !='id':
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
            if key not in self.nocheck_keys and key !='id':
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
            if key not in self.nocheck_keys and key !='id':
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
            if key not in self.nocheck_keys and key !='id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_arecibo_then_ARM(self):

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
            if key not in self.nocheck_keys and key !='id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

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

        self.expected_params = {
                             'elements_type': 'MPC_MINOR_PLANET',
                             'abs_mag' : '26.6',
                             'argofperih': '222.91160',
                             'longascnode': '24.87559',
                             'eccentricity': '0.0120915',
                             'epochofel': datetime(2016,01,13,0),
                             'meandist': '0.9967710',
                             'orbinc': '8.25708',
                             'meananom': '221.74204',
                             'slope': '0.15',
                             'origin' : 'M',
                             'active' : True,
                             'source_type' : 'N',
                             'discovery_date': datetime(2014,10,17,0),
                             'num_obs': '147',
                             'arc_length': '357',
                             'not_seen' : 5.5,
#                             'score' : None,
                             'update_time' : datetime(2015,10,9,0),
                             'updated' : True
                             }
        self.expected_comet_params = {
                                        'elements_type': 'MPC_COMET',
                                        'argofperih': '214.01052',
                                        'longascnode' : '24.55858',
                                        'eccentricity' : '1.0000000',
                                        'epochofel': datetime(2016, 04, 19, 0),
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
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra,7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec,7)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.astrometric_catalog)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.photometric_catalog)

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
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra,7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec,7)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.astrometric_catalog)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.photometric_catalog)

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
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra,7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec,7)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.astrometric_catalog)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.photometric_catalog)

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
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra,7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec,7)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.astrometric_catalog)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.photometric_catalog)

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
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra,7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec,7)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.astrometric_catalog)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.photometric_catalog)

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
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra,7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec,7)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.astrometric_catalog)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.photometric_catalog)

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
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra,7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec,7)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.astrometric_catalog)
        self.assertEqual(expected_params['astrometric_catalog'], source_measure.photometric_catalog)
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


    def test_add_frame(self):
        params = parse_mpcobs(self.test_obslines[-1])
        resp = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K93')
        self.assertEqual(1,frames.count())

    def test_add_frames(self):
        for line in self.test_obslines:
            params = parse_mpcobs(line)
            resp = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K93')
        self.assertEqual(3,frames.count())
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
        self.assertEqual(1,frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)

    def test_ingest_frames_block(self):
        params = {
                    'date_obs': "2015-04-20 21:41:05",
                    'siteid': 'cpt',
                    'encid': 'doma',
                    'telid': '1m0a',
                    'filter_name': 'R',
                    'instrume': "kb70",
                    'origname': "cpt1m010-kb70-20150420-0001-e00.fits",
                    'exptime': '30',
                    'groupid': 'tmp'
                 }
        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1,frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)

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
class TestClean_crossid(TestCase):

    def setUp(self):
        MockDateTime.change_datetime(2015, 11, 5, 18, 0, 0)

    def test_regular_asteroid(self):
        crossid = u'P10p9py', u'2015 VV1', '', u'(Nov. 5.30 UT)'
        expected_params = { 'active' : False,
                            'name' : '2015 VV1',
                            'source_type' : 'A'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_NEO_recent_confirm(self):
        crossid = u'WV82468', u'2015 VB2', u'MPEC 2015-V51', u'(Nov. 5.60 UT)'
        expected_params = { 'active' : True,
                            'name' : '2015 VB2',
                            'source_type' : 'N'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_NEO_older_confirm(self):
        crossid = u'P10o0Ha', u'2015 SE20', u'MPEC 2015-T29', u'(Oct. 8.59 UT)'
        expected_params = { 'active' : False,
                            'name' : '2015 SE20',
                            'source_type' : 'N'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_did_not_exist(self):
        crossid =  u'WTB842B', 'doesnotexist', '', u'(Oct. 9.19 UT)'
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'X'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_not_confirmed(self):
        crossid =  u'P10oYZI', 'wasnotconfirmed', '', u'(Nov. 4.81 UT)'
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'U'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_not_interesting(self):
        crossid =  u'P10oYZI', '', '', u'(Nov. 4.81 UT)'
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'W'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_cbet_recent(self):
        crossid =  u'WV2B5A8', u'C/2015 V2', u'CBET 5432', u'(Nov. 5.49 UT)'
        expected_params = { 'active' : True,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_cbet_notrecent(self):
        crossid =  u'WV2B5A8', u'C/2015 V2', u'CBET 5432', u'(Nov. 1.49 UT)'
        expected_params = { 'active' : False,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_iauc_recent(self):
        crossid =  u'WV2B5A8', u'C/2015 V2', u'IAUC-', u'(Nov. 5.49 UT)'
        expected_params = { 'active' : True,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_iauc_notrecent(self):
        crossid =  u'WV2B5A8', u'C/2015 V2', u'IAUC-', u'(Nov. 1.49 UT)'
        expected_params = { 'active' : False,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_asteroid_number(self):
        crossid =  u'LM02L2J', u'C/2015 TQ209', u'IAUC 2015-', u'(Oct. 24.07 UT)'
        expected_params = { 'active' : False,
                            'name' : 'C/2015 TQ209',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_mpec_recent(self):
        crossid =  u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Nov. 18.63 UT)'
        expected_params = { 'active' : True,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_mpec_notrecent(self):
        crossid =  u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Oct. 18.63 UT)'
        expected_params = { 'active' : False,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_new_year_switchover(self):
        MockDateTime.change_datetime(2016, 1, 1, 0, 30, 0)
        crossid =  u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Oct. 18.63 UT)'
        expected_params = { 'active' : False,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_bad_date(self):
        MockDateTime.change_datetime(2016, 3, 1, 0, 30, 0)
        crossid = u'P10sKEk', u'2016 CP264', '', u'(Feb. 30.00 UT)'
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

        expected_summary = [ { 'Not Observed': 1,
                               'Observed': 1,
                               'proposal': u'LCO2015A-009'},
                             { 'Not Observed': 1,
                               'Observed': 0,
                               'proposal': u'LCO2015B-005'}
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

class TestCheckCatalogAndRefit(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix = 'tmp_neox_')

        self.phot_tests_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_image = os.path.join(self.phot_tests_dir, 'example-sbig-e10.fits')
        self.test_catalog = os.path.join(self.phot_tests_dir, 'oracdr_test_catalog.fits')
        self.test_ldac_catalog = os.path.join(self.phot_tests_dir, 'ldac_test_catalog.fits')
        self.configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

        # Create a version of the test catalog with a good WCS in the temp dir
        hdulist = fits.open(self.test_catalog, mode='denywrite')
        prihdr = hdulist[0].header
        wcserr = prihdr.get('WCSERR', None)
        if wcserr:
            prihdr['WCSERR'] = (0, 'Reset to 0 for testing')
        self.test_catalog_good_wcs = os.path.join(self.temp_dir, 'oracdr_test_catalog_good_wcs.fits')
        hdulist.writeto(self.test_catalog_good_wcs)
        hdulist.close()

        self.debug_print = False

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print "Error removing files in temporary test directory", self.temp_dir
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print: print "Removed", self.temp_dir
            except OSError:
                print "Error removing temporary test directory", self.temp_dir

    def test_good_catalog_nofit_needed(self):

        expected_status = 0

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_catalog_good_wcs)

        self.assertEqual(expected_status, status)

    def test_bad_catalog_name(self):

        expected_status = -1

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_catalog)

        self.assertEqual(expected_status, status)

    def test_no_matching_image(self):

        expected_status = -1

        # Symlink catalog to temp dir with valid name
        temp_test_catalog = os.path.join(self.temp_dir, 'oracdr_test_e08_cat.fits')
        os.symlink(self.test_catalog, temp_test_catalog)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, temp_test_catalog)

        self.assertEqual(expected_status, status)

    def test_good_catalog_refit(self):

        expected_file = os.path.join(self.temp_dir, 'oracdr_test_e09_ldac.fits')

        # Symlink catalog and image to temp dir with valid name
        temp_test_catalog = os.path.join(self.temp_dir, 'oracdr_test_e08_cat.fits')
        os.symlink(self.test_catalog, temp_test_catalog)
        temp_test_image = os.path.join(self.temp_dir, 'oracdr_test_e08.fits')
        os.symlink(self.test_image, temp_test_image)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, temp_test_catalog)

        self.assertEqual(expected_file, status)
        self.assertTrue(os.path.exists(expected_file))
