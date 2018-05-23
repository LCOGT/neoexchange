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
import mock
from socket import error
from datetime import datetime, timedelta
from unittest import skipIf
from math import radians

import astropy.units as u
from bs4 import BeautifulSoup
from django.test import TestCase
from django.forms.models import model_to_dict

from core.models import Body, Proposal, Block
from astrometrics.ephem_subs import determine_darkness_times
from neox.tests.mocks import MockDateTime, mock_expand_cadence
from core.views import record_block, create_calib_sources
# Import module to test
from astrometrics.sources_subs import *


class TestGoldstoneChunkParser(TestCase):
    """Unit tests for the sources_subs.parse_goldstone_chunks() method"""

    def test_specficdate_provis_desig(self):
        expected_objid = '2015 FW117'
        chunks = [u'2015', u'Apr', u'1', u'2015', u'FW117', u'Yes', u'Yes', u'Scheduled']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_specficdate_astnumber(self):
        expected_objid = '285331'
        chunks = [u'2015', u'May', u'16-17', u'285331', u'1999', u'FN53', u'No', u'Yes', u'R']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_unspecificdate_provis_desig(self):
        expected_objid = '2010 NY65'
        chunks = [u'2015', u'Jun', u'2010', u'NY65', u'No', u'Yes', u'R', u'PHA']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_unspecificdate_astnumber(self):
        expected_objid = '385186'
        chunks = [u'2015', u'Jul', u'385186', u'1994', u'AW1', u'No', u'Yes', u'PHA', u'BINARY', u'(not', u'previously', u'observed', u'with', u'radar)']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_specficdate_named_ast(self):
        expected_objid = '1566'  # '(1566) Icarus'
        chunks = [u'2015', u'Jun', u'13-17', u'1566', u'Icarus', u'No', u'Yes', u'R', u'PHA', u'June', u'13/14,', u'14/15,', u'and', u'16/17']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_unspecficdate_named_ast(self):
        expected_objid = '1685'  # '(1685) Toro'
        chunks = ['2016', 'Jan', '1685', 'Toro', 'No', 'No', 'R']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_multimonth_split(self):
        expected_objid = '410777'  # '(410777) 2009 FD'
        chunks = [u'2015', u'Oct', u'25-Nov', u'1', u'410777', u'2009', u'FD', u'No', u'Yes', u'R']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_multimonth_split_provisional(self):
        expected_objid = '2017 CS'  # '2017 CS'
        chunks = [u'2017', u'May', u'22-Jun', u'01', u'2017', u'CS', u'Yes', u'Yes', u'19.4', u'PHA', u'Target-of-opportunity']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_multimonth_split_provisional2(self):
        expected_objid = '2017 CS101'  # '2017 CS01'
        chunks = [u'2017', u'May', u'22-Jun', u'01', u'2017', u'CS101', u'Yes', u'Yes', u'19.4', u'PHA', u'Target-of-opportunity']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_multimonth_split_named(self):
        expected_objid = '6063'  # '606 Jason'
        chunks = [u'2017', u'May', u'22-Jun', u'01', u'6063', u'Jason', u'No', u'Yes', u'15.9', u'R1']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_periodic_comet(self):
        expected_objid = 'P/2016 BA14'
        chunks = [u'2016', u'Mar', u'17-23', u'P/2016', u'BA14', u'Pan-STARRS', u'No', u'Yes', u'Comet', u'DSS-13', u'and', u'Green', u'Bank.', u'Tests', u'at', u'DSS-14.', u'Target-of-opportunity.']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_comma_separated_obsdates(self):
        expected_objid = '2016 BC14'
        line = u'2016 Mar 22, 23          2016 BC14       No         Yes          PHA               NHATS  Tests at DSS-14.  Target-of-opportunity.'
        line = line.replace(', ', '-', 1)
        chunks = line.lstrip().split()
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)


class TestFetchAreciboTargets(TestCase):

    def setUp(self):
        # Read and make soup from the stored version of the Arecibo radar pages
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_arecibo_page.html'), 'r')
        self.test_arecibo_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_arecibo_page_v2.html'), 'r')
        self.test_arecibo_page_v2 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.maxDiff = None

    def test_basics(self):
        expected_length = 17

        targets = fetch_arecibo_targets(self.test_arecibo_page)

        self.assertEqual(expected_length, len(targets))

    def test_targets(self):
        expected_targets = [ u'294739',
                             u'162385',
                             u'337866',
                             u'85990',
                             u'438661',
                             u'2007 BB',
                             u'2015 BN509',
                             u'2014 EK24',
                             u'137805',
                             u'2010 FX9',
                             u'1994 UG',
                             u'406952',
                             u'363599',
                             u'2003 KO2',
                             u'388945',
                             u'2014 US115',
                             u'2009 DL46']

        targets = fetch_arecibo_targets(self.test_arecibo_page)

        self.assertEqual(expected_targets, targets)

    def test_basics_v2(self):
        expected_length = 36

        targets = fetch_arecibo_targets(self.test_arecibo_page_v2)

        self.assertEqual(expected_length, len(targets))

    def test_targets_v2(self):
        expected_targets = [ u'4775',
                             u'357024',
                             u'250458',
                             u'2009 ES',
                             u'2100',
                             u'162117',
                             u'2011 DU',
                             u'2014 UR',
                             u'2012 UA34',
                             u'467963',
                             u'413260',
                             u'164121',
                             u'2004 KB',
                             u'2005 TF',
                             u'326302',
                             u'68950',
                             u'152685',
                             u'162911',
                             u'152391',
                             u'433953',
                             u'2009 TB8',
                             u'369264',
                             u'96590',
                             u'5143',
                             u'2007 VM184',
                             u'2005 WS3',
                             u'326683',
                             u'2006 XD2',
                             u'2008 UL90',
                             u'418849',
                             u'2014 EW24',
                             u'2012 YK',
                             u'4179',
                             u'2102',
                             u'7341',
                             u'226514']

        targets = fetch_arecibo_targets(self.test_arecibo_page_v2)

        self.assertEqual(expected_targets, targets)


class TestFetchGoldstoneTargets(TestCase):

    def setUp(self):
        # Read and make soup from the stored version of the Goldstone radar pages
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_goldstone_page.html'), 'r')
        self.test_goldstone_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.maxDiff = None

    def test_basics(self):
        expected_length = 49

        targets = fetch_goldstone_targets(self.test_goldstone_page)

        self.assertEqual(expected_length, len(targets))

    def test_targets(self):
        expected_targets = [ '3200',
                             '2017 VT14',
                             '2017 WX12',
                             '2017 WZ14',
                             '418849',
                             '2017 QL33',
                             '2007 AG',
                             '438017',
                             '306383',
                             '276055',
                             '2014 SR339',
                             '2015 BN509',
                             '162882',
                             '96950',
                             '3752',
                             '2017 VR12',
                             '2013 RZ73',
                             '1981',
                             '363599',
                             '444193',
                             '194126',
                             '2002 JR100',
                             '242643',
                             '2013 US3',
                             '1999 FN19',
                             '388945',
                             '66391',
                             '68347',
                             '2014 WG365',
                             '469737',
                             '441987',
                             '2015 DP155',
                             '1996 AW1',
                             '13553',
                             '398188',
                             '1998 SD9',
                             '2015 FP118',
                             '144332',
                             '475534',
                             '2013 UG1',
                             '2002 VE68',
                             '4953',
                             '2003 NW1',
#                            'Comet 46P/Wirtanen',
                             '410088',
                             '418849',
                             '2012 MS4',
                             '163899',
                             '2004 XK50',
                             '433']

        targets = fetch_goldstone_targets(self.test_goldstone_page)

        self.assertEqual(expected_targets, targets)

    def test_target_with_ampersand(self):

        html = '''<html><head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"><title>Goldstone Asteroid Schedule</title><style></style></head>
                <body>
                                                                  Needs
                                                        Needs     Physical
                                         Target      Astrometry?  Observations?   H

                2018 Jan 13 &amp; 15  <a href="https://echo.jpl.nasa.gov/asteroids/2003YO3/2003YO3_planning.html">438017 2003 YO3</a>        No         Yes         18.7            
                </body></html>
                '''
        page = BeautifulSoup(html, 'html.parser')

        expected_target = ['438017', ]

        targets = fetch_goldstone_targets(page)

        self.assertEqual(1, len(targets))
        self.assertEqual(expected_target, targets)

    def test_target_with_ampersand2(self):

        html = '''<html><head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"><title>Goldstone Asteroid Schedule</title><style></style></head>
                <body>
                                                                  Needs
                                                        Needs     Physical
                                         Target      Astrometry?  Observations?   H

                2018 Jan 13&amp;15  <a href="https://echo.jpl.nasa.gov/asteroids/2003YO3/2003YO3_planning.html">438017 2003 YO3</a>        No         Yes         18.7            
                </body></html>
                '''
        page = BeautifulSoup(html, 'html.parser')

        expected_target = ['438017', ]

        targets = fetch_goldstone_targets(page)

        self.assertEqual(1, len(targets))
        self.assertEqual(expected_target, targets)

    def test_target_with_ampersand3(self):

        html = '''<html><head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"><title>Goldstone Asteroid Schedule</title><style></style></head>
                <body>
                                                                  Needs
                                                        Needs     Physical
                                         Target      Astrometry?  Observations?   H

                2018 Jan 13&amp; 15  <a href="https://echo.jpl.nasa.gov/asteroids/2003YO3/2003YO3_planning.html">438017 2003 YO3</a>        No         Yes         18.7            
                </body></html>
                '''
        page = BeautifulSoup(html, 'html.parser')

        expected_target = ['438017', ]

        targets = fetch_goldstone_targets(page)

        self.assertEqual(1, len(targets))
        self.assertEqual(expected_target, targets)

    def test_target_with_ampersand4(self):

        html = '''<html><head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"><title>Goldstone Asteroid Schedule</title><style></style></head>
                <body>
                                                                  Needs
                                                        Needs     Physical
                                         Target      Astrometry?  Observations?   H

                2018 Jan 13 &amp;15  <a href="https://echo.jpl.nasa.gov/asteroids/2003YO3/2003YO3_planning.html">438017 2003 YO3</a>        No         Yes         18.7            
                </body></html>
                '''
        page = BeautifulSoup(html, 'html.parser')

        expected_target = ['438017', ]

        targets = fetch_goldstone_targets(page)

        self.assertEqual(1, len(targets))
        self.assertEqual(expected_target, targets)


class TestSubmitBlockToScheduler(TestCase):

    def setUp(self):
        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : datetime(2015, 3, 19, 00, 00, 00),
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

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

    @mock.patch('astrometrics.sources_subs.requests.post')
    def test_submit_body_for_cpt(self, mock_post):
        mock_post.return_value.status_code = 200

        mock_post.return_value.json.return_value = {'id': '999', 'requests' : [{'id': '111', 'duration' : 1820}]}

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'K92'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {  'proposal_id' : 'LCO2015A-009',
                    'exp_count' : 18,
                    'exp_time' : 50.0,
                    'site_code' : site_code,
                    'start_time' : dark_start,
                    'end_time' : dark_end,
                    'filter_pattern' : 'w',
                    'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                    'user_id'  : 'bsimpson'
                 }

        resp, sched_params = submit_block_to_scheduler(body_elements, params)
        self.assertEqual(resp, '999')

        # store block
        data = params
        data['proposal_code'] = 'LCO2015A-009'
        data['exp_length'] = 91
        block_resp = record_block(resp, sched_params, data, self.body)
        self.assertEqual(block_resp, True)

        # Test that block has same start/end as superblock
        blocks = Block.objects.filter(active=True)
        for block in blocks:
            self.assertEqual(block.block_start, block.superblock.block_start)
            self.assertEqual(block.block_end, block.superblock.block_end)

    @mock.patch('astrometrics.sources_subs.expand_cadence', mock_expand_cadence)
    @mock.patch('astrometrics.sources_subs.requests.post')
    def test_submit_cadence(self, mock_post):
        mock_post.return_value.status_code = 200

        mock_post.return_value.json.return_value = {'id': '999', 'requests' : [{'id': '111', 'duration' : 1820},
                                                                               {'id': '222', 'duration' : 1820},
                                                                               {'id': '333', 'duration' : 1820}]}

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'V38'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {  'proposal_id' : 'LCO2015A-009',
                    'exp_count' : 18,
                    'exp_time' : 50.0,
                    'site_code' : site_code,
                    'start_time' : dark_start,
                    'end_time' : dark_end,
                    'filter_pattern' : 'w',
                    'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                    'user_id'  : 'bsimpson',
                    'period'    : 2.0,
                    'jitter'    : 0.25
                 }
        tracking_num, sched_params = submit_block_to_scheduler(body_elements, params)

        # store Blocks
        data = params
        data['proposal_code'] = 'LCO2015A-009'
        data['exp_length'] = 91
        block_resp = record_block(tracking_num, sched_params, data, self.body)
        self.assertEqual(block_resp, True)

        blocks = Block.objects.filter(active=True)

        # test Block dates are indipendent from Superblock dates
        for block in blocks:
            if block != blocks[0]:
                self.assertNotEqual(block.block_start, block.superblock.block_start)
            if block != blocks[2]:
                self.assertNotEqual(block.block_end, block.superblock.block_end)

    def test_make_userrequest(self):
        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'K92'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {  'proposal_id' : 'LCO2015A-009',
                    'exp_count' : 18,
                    'exp_time' : 50.0,
                    'site_code' : site_code,
                    'start_time' : dark_start,
                    'end_time' : dark_end,
                    'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                    'user_id'  : 'bsimpson',
                    'filter_pattern' : 'w'
                 }

        user_request = make_userrequest(body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['windows'][0]['start'], dark_start.strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual(user_request['requests'][0]['location'].get('telescope', None), None)

    def test_1m_sinistro_lsc_doma_userrequest(self):

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'W85'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {  'proposal_id' : 'LCO2015A-009',
                    'exp_count' : 18,
                    'exp_time' : 50.0,
                    'site_code' : site_code,
                    'start_time' : dark_start,
                    'end_time' : dark_end,
                    'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                    'user_id'  : 'bsimpson',
                    'filter_pattern' : 'w'
                 }

        user_request = make_userrequest(body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['location']['telescope'], '1m0a')
        self.assertEqual(user_request['requests'][0]['location']['telescope_class'], '1m0')
        self.assertEqual(user_request['requests'][0]['location']['site'], 'lsc')
        self.assertEqual(user_request['requests'][0]['location']['observatory'], 'doma')

    def test_multi_filter_userrequest(self):

            body_elements = model_to_dict(self.body)
            body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
            body_elements['current_name'] = self.body.current_name()
            site_code = 'W85'
            utc_date = datetime.now()+timedelta(days=1)
            dark_start, dark_end = determine_darkness_times(site_code, utc_date)
            params = {  'proposal_id' : 'LCO2015A-009',
                        'exp_count' : 18,
                        'exp_time' : 50.0,
                        'site_code' : site_code,
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                        'user_id'  : 'bsimpson',
                        'filter_pattern' : 'V,V,R,R,I,I'
                     }

            user_request = make_userrequest(body_elements, params)
            molecules = user_request.get('requests')[0].get('molecules')
            expected_molecule_num = 9
            expected_exp_count = 2
            expected_filter = 'V'

            self.assertEqual(len(molecules), expected_molecule_num)
            self.assertEqual(molecules[3].get('exposure_count'), expected_exp_count)
            self.assertEqual(molecules[3].get('filter'), expected_filter)

    def test_uneven_filter_userrequest(self):

            body_elements = model_to_dict(self.body)
            body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
            body_elements['current_name'] = self.body.current_name()
            site_code = 'W85'
            utc_date = datetime.now()+timedelta(days=1)
            dark_start, dark_end = determine_darkness_times(site_code, utc_date)
            params = {  'proposal_id' : 'LCO2015A-009',
                        'exp_count' : 18,
                        'exp_time' : 50.0,
                        'site_code' : site_code,
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                        'user_id'  : 'bsimpson',
                        'filter_pattern' : 'V,V,R,I'
                     }

            user_request = make_userrequest(body_elements, params)
            molecules = user_request.get('requests')[0].get('molecules')
            expected_molecule_num = 13
            expected_exp_count = 1
            expected_filter = 'I'

            self.assertEqual(len(molecules), expected_molecule_num)
            self.assertEqual(molecules[2].get('exposure_count'), expected_exp_count)
            self.assertEqual(molecules[2].get('filter'), expected_filter)

    def test_single_filter_userrequest(self):

            body_elements = model_to_dict(self.body)
            body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
            body_elements['current_name'] = self.body.current_name()
            site_code = 'W85'
            utc_date = datetime.now()+timedelta(days=1)
            dark_start, dark_end = determine_darkness_times(site_code, utc_date)
            params = {  'proposal_id' : 'LCO2015A-009',
                        'exp_count' : 18,
                        'exp_time' : 50.0,
                        'site_code' : site_code,
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                        'user_id'  : 'bsimpson',
                        'filter_pattern' : 'V'
                     }

            user_request = make_userrequest(body_elements, params)
            molecules = user_request.get('requests')[0].get('molecules')
            expected_molecule_num = 1
            expected_exp_count = 18
            expected_filter = 'V'

            self.assertEqual(len(molecules), expected_molecule_num)
            self.assertEqual(molecules[0].get('exposure_count'), expected_exp_count)
            self.assertEqual(molecules[0].get('filter'), expected_filter)

    def test_overlap_filter_userrequest(self):

            body_elements = model_to_dict(self.body)
            body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
            body_elements['current_name'] = self.body.current_name()
            site_code = 'W85'
            utc_date = datetime.now()+timedelta(days=1)
            dark_start, dark_end = determine_darkness_times(site_code, utc_date)
            params = {  'proposal_id' : 'LCO2015A-009',
                        'exp_count' : 18,
                        'exp_time' : 50.0,
                        'site_code' : site_code,
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                        'user_id'  : 'bsimpson',
                        'filter_pattern' : 'V,V,R,R,I,I,V'
                     }

            user_request = make_userrequest(body_elements, params)
            molecules = user_request.get('requests')[0].get('molecules')
            expected_molecule_num = 8
            expected_exp_count = 3
            expected_filter = 'V'

            self.assertEqual(len(molecules), expected_molecule_num)
            self.assertEqual(molecules[3].get('exposure_count'), expected_exp_count)
            self.assertEqual(molecules[3].get('filter'), expected_filter)

    def test_overlap_nooverlap_filter_userrequest(self):

            body_elements = model_to_dict(self.body)
            body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
            body_elements['current_name'] = self.body.current_name()
            site_code = 'W85'
            utc_date = datetime.now()+timedelta(days=1)
            dark_start, dark_end = determine_darkness_times(site_code, utc_date)
            params = {  'proposal_id' : 'LCO2015A-009',
                        'exp_count' : 15,
                        'exp_time' : 50.0,
                        'site_code' : site_code,
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                        'user_id'  : 'bsimpson',
                        'filter_pattern' : 'V,V,R,I,V'
                     }

            user_request = make_userrequest(body_elements, params)
            molecules = user_request.get('requests')[0].get('molecules')
            expected_molecule_num = 10
            expected_exp_count = 1
            expected_filter = 'V'

            self.assertEqual(len(molecules), expected_molecule_num)
            self.assertEqual(molecules[9].get('exposure_count'), expected_exp_count)
            self.assertEqual(molecules[9].get('filter'), expected_filter)

    def test_partial_filter_userrequest(self):

            body_elements = model_to_dict(self.body)
            body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
            body_elements['current_name'] = self.body.current_name()
            site_code = 'W85'
            utc_date = datetime.now()+timedelta(days=1)
            dark_start, dark_end = determine_darkness_times(site_code, utc_date)
            params = {  'proposal_id' : 'LCO2015A-009',
                        'exp_count' : 15,
                        'exp_time' : 50.0,
                        'site_code' : site_code,
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                        'user_id'  : 'bsimpson',
                        'filter_pattern' : 'V,V,V,V,V,V,R,R,R,R,R,I,I,I,I,I,I'
                     }

            user_request = make_userrequest(body_elements, params)
            molecules = user_request.get('requests')[0].get('molecules')
            expected_molecule_num = 3
            expected_exp_count = 4
            expected_filter = 'I'

            self.assertEqual(len(molecules), expected_molecule_num)
            self.assertEqual(molecules[2].get('exposure_count'), expected_exp_count)
            self.assertEqual(molecules[2].get('filter'), expected_filter)

    def test_partial_overlap_filter_userrequest(self):

            body_elements = model_to_dict(self.body)
            body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
            body_elements['current_name'] = self.body.current_name()
            site_code = 'W85'
            utc_date = datetime.now()+timedelta(days=1)
            dark_start, dark_end = determine_darkness_times(site_code, utc_date)
            params = {  'proposal_id' : 'LCO2015A-009',
                        'exp_count' : 15,
                        'exp_time' : 50.0,
                        'site_code' : site_code,
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                        'user_id'  : 'bsimpson',
                        'filter_pattern' : 'V,V,R,R,I,V'
                     }

            user_request = make_userrequest(body_elements, params)
            molecules = user_request.get('requests')[0].get('molecules')
            expected_molecule_num = 8
            expected_exp_count = 3
            expected_filter = 'V'

            self.assertEqual(len(molecules), expected_molecule_num)
            self.assertEqual(molecules[6].get('exposure_count'), expected_exp_count)
            self.assertEqual(molecules[6].get('filter'), expected_filter)


class TestFetchFilterList(TestCase):
    """Unit test for getting current filters from configdb"""

    def setUp(self):
        # Read stored version of camera mappings file
        self.test_filter_map = os.path.join('astrometrics', 'tests', 'test_camera_mapping.dat')

    def test_1m_cpt(self):
        expected_filter_list = ['air', 'U', 'B', 'V', 'R', 'I', 'up', 'gp', 'rp', 'ip', 'zs', 'Y', 'w']

        filter_list = fetch_filter_list('K91', False, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)

    def test_0m4_ogg(self):
        expected_filter_list = ['air', 'B', 'V', 'up', 'gp', 'rp', 'ip', 'zs', 'w']

        filter_list = fetch_filter_list('T04', False, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)

    def test_2m_ogg(self):
        expected_filter_list = ['air', 'Astrodon-UV', 'B', 'V', 'R', 'I', 'up', 'gp', 'rp', 'ip', 'Skymapper-VS', 'solar', 'zs', 'Y']

        filter_list = fetch_filter_list('F65', False, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)

    def test_1m_lsc_domeb(self):
        expected_filter_list = ['air', 'ND' , 'U', 'B', 'V', 'R', 'I', 'up', 'gp', 'rp', 'ip', 'zs', 'Y', 'w']

        filter_list = fetch_filter_list('W86', False, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)

    def test_unavailable_telescope(self):
        expected_filter_list = []

        filter_list = fetch_filter_list('Z21', False, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)

    def test_lowercase_telescope(self):
        expected_filter_list = ['air', 'B', 'V', 'up', 'gp', 'rp', 'ip', 'zs', 'w']

        filter_list = fetch_filter_list('t04', False, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)

    def test_invalid_telescope(self):
        expected_filter_list = []

        filter_list = fetch_filter_list('BESTtelescope', False, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)

    def test_spectra_telescope(self):
        expected_filter_list = ['slit_1.2as', 'slit_1.6as', 'slit_2.0as', 'slit_6.0as']

        filter_list = fetch_filter_list('F65', True, self.test_filter_map)
        self.assertEqual(expected_filter_list, filter_list)


class TestPreviousNEOCPParser(TestCase):
    """Unit tests for the sources_subs.parse_previous_NEOCP_id() method"""

    def test_was_not_confirmed(self):

        items = [u' P10ngMD was not confirmed (Aug. 19.96 UT)\n']
        expected = [u'P10ngMD', 'wasnotconfirmed', '', u'(Aug. 19.96 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_does_not_exist(self):

        items = [u' N008b6e does not exist (Aug. 14.77 UT)\n']
        expected = [u'N008b6e', 'doesnotexist', '', u'(Aug. 14.77 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_was_not_interesting(self):

        items = [u' OG12993 is not interesting (Jan. 26.10 UT)\n']
        expected = [u'OG12993', '', '', u'(Jan. 26.10 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_was_not_a_minor_planet(self):

        items = [u' A10422t was not a minor planet (Sept. 20.89 UT)\n']
        expected = [u'A10422t', 'wasnotminorplanet', '', u'(Sept. 20.89 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_non_neo(self):

        items = [u' 2015 QF', BeautifulSoup('<sub>   </sub>', "html.parser").sub, u' = WQ39346(Aug. 19.79 UT)\n']
        expected = [u'WQ39346', '2015 QF', '', u'(Aug. 19.79 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_neo(self):

        items = [u' 2015 PK', BeautifulSoup('<sub>229</sub>', "html.parser").sub, u' = P10n00U (Aug. 17.98 UT)  [see ',
                 BeautifulSoup('<a href="/mpec/K15/K15Q10.html"><i>MPEC</i> 2015-Q10</a>', "html.parser").a, u']\n']
        expected = [u'P10n00U', u'2015 PK229', u'MPEC 2015-Q10', u'(Aug. 17.98 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_good_comet(self):

        items = [u' Comet C/2015 Q1 = SW40sQ (Aug. 19.49 UT)  [see ',
            BeautifulSoup('<a href="http://www.cbat.eps.harvard.edu/iauc/20100/2015-.html"><i>IAUC</i> 2015-</a>', "html.parser").a,
            u']\n']
        expected = [u'SW40sQ', u'C/2015 Q1', u'IAUC 2015-', u'(Aug. 19.49 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_good_comet_cbet(self):

        items = [u' Comet C/2015 O1 = P10ms6N(July 21.99 UT)  [see ',
            BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>', "html.parser").a,
            u']\n']

        expected = [u'P10ms6N', u'C/2015 O1', u'CBET 4119', u'(July 21.99 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_bad_comet(self):

        items = [u' Comet C/2015 P3 = MAT01  (Aug. 11.23 UT)  [see ',
            BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004136.txt"><i>CBET</i> 4136</a>', "html.parser").a,
             u']\n']
        expected = [u'MAT01', u'C/2015 P3', u'CBET 4136', u'(Aug. 11.23 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_bad_comet2(self):

        items = [u' Comet 2015 TQ209 = LM02L2J(Oct. 24.07 UT)  [see ',
            BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/iauc/20100/2015-.html"><i>IAUC</i> 2015-</a>', "html.parser").a,
             u']\n']
        expected = [u'LM02L2J', u'C/2015 TQ209', u'IAUC 2015-', u'(Oct. 24.07 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_bad_comet3(self):

        items = [u' Comet C/2015 X8 = NM0015a (Dec. 18.63 UT)  [see ',
            BeautifulSoup(' <a href="/mpec/K15/K15Y20.html"><i>MPEC</i> 2015-Y20</a>', "html.parser").a,
             u']\n']
        expected = [u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Dec. 18.63 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_bad_comet4(self):

        items = [u' Comet C/2016 C1 = P10ABXd (Mar. 30.47 UT)\n']
        expected = [u'P10ABXd', u'C/2016 C1', u'', u'(Mar. 30.47 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_bad_pseudocomet1(self):
        items = [u' A/2018 C2 = ZC82561 (Mar. 4.95 UT)   [see ',
            BeautifulSoup(' <a href="/mpec/K18/K18E18.html"><i>MPEC</i> 2018-E18</a>', "html.parser").a,
            u']\n']
        expected = [u'ZC82561', u'A/2018 C2', u'MPEC 2018-E18', u'(Mar. 4.95 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)


class TestParseNEOCP(TestCase):

    def setUp(self):
        # Read and make soup from the non-tabular and HTML table versions of
        # the NEOCP
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_neocp_page.html'), 'r')
        self.test_neocp_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_neocp_page_table.html'), 'r')
        self.test_neocp_page_table = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        # Set to None to show all differences
        self.maxDiff = None

    def test_parse_neocp(self):
        expected_obj_ids = [
                            u'CAH024',
                            u'P10o56w',
                            u'WS0CB7B',
                            u'WS0D4AD',
                            u'WSB0B67',
                            u'WSB07F4',
                            u'WSB07F2',
                            u'WSB07D3',
                            u'WS0B4C6',
                            u'P10o4Gp',
                            u'P10o4Go',
                            u'P10o4EL',
                            u'P10o41o',
                            u'P10o41l',
                            u'P10o41n',
                            u'P10o3d9',
                            u'P10o3da',
                            u'P10o2VR',
                            u'P10o2ur',
                            u'P10o1Gq',
                            u'P10o1Fl',
                            u'P10o1Fm',
                            u'P10o14r',
                            u'WSF2BB6',
                            u'LM02Ei5',
                            u'P10o10e',
                            u'P10o0Zx',
                            u'WSAF769',
                            u'WSAFE31',
                            u'WSAFCA9',
                            u'WSAF76B',
                            u'P10o0Jv',
                            u'P10o0Jo',
                            u'P10o0Ha',
                            u'P10o0Hc',
                            u'CAH002',
                            u'WSAEABF',
                            u'WSAC540',
                            u'WSAC5DA',
                            u'WS03256',
                            u'WSAD60C',
                            u'WR0159E',
                            u'LM01vOQ',
                            u'P10nI6D',
                            u'P10nw2g',
                            ]

        obj_ids = parse_NEOCP(self.test_neocp_page)

        self.assertEqual(len(expected_obj_ids), len(obj_ids))
        self.assertEqual(expected_obj_ids, obj_ids)

    def test_parse_neocp_table(self):
        expected_obj_ids = [
                            u'CAH024',
                            u'P10o56w',
                            u'WS0CB7B',
                            u'WS0D4AD',
                            u'WSB0B67',
                            u'WSB07F4',
                            u'WSB07F2',
                            u'WSB07D3',
                            u'WS0B4C6',
                            u'P10o4Gp',
                            u'P10o4Go',
                            u'P10o4EL',
                            u'P10o41o',
                            u'P10o41l',
                            u'P10o41n',
                            u'P10o3d9',
                            u'P10o3da',
                            u'P10o2VR',
                            u'P10o2ur',
                            u'P10o1Gq',
                            u'P10o1Fl',
                            u'P10o1Fm',
                            u'P10o14r',
                            u'WSF2BB6',
                            u'LM02Ei5',
                            u'P10o10e',
                            u'P10o0Zx',
                            u'WSAF769',
                            u'WSAFE31',
                            u'WSAFCA9',
                            u'WSAF76B',
                            u'P10o0Jv',
                            u'P10o0Jo',
                            u'P10o0Ha',
                            u'P10o0Hc',
                            u'CAH002',
                            u'WSAEABF',
                            u'WSAC540',
                            u'WSAC5DA',
                            u'WS03256',
                            u'WSAD60C',
                            # u'WR0159E',
                            u'LM01vOQ',
                            u'P10nI6D',
                            u'P10nw2g',
                            ]

        obj_ids = parse_NEOCP(self.test_neocp_page_table)

        self.assertEqual(len(expected_obj_ids), len(obj_ids))
        self.assertEqual(expected_obj_ids, obj_ids)

    def test_parse_neocp_not_soup(self):

        obj_ids = parse_NEOCP(None)

        self.assertEqual(obj_ids, None)

    def test_parse_neocp_no_objects(self):

        obj_ids = parse_NEOCP(BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>', "html.parser"))

        self.assertEqual(obj_ids, None)


class TestParseNEOCPExtraParams(TestCase):

    def setUp(self):
        # Read and make soup from the HTML table versions of the NEOCP
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_neocp_page_table.html'), 'r')
        self.test_neocp_page_table = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.table_header = '''<table class="tablesorter">
          <thead>
            <tr>
              <th>&nbsp;&nbsp;Temp Desig&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Score&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Discovery</th>
              <th>&nbsp;&nbsp;R.A.&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Decl.&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;V&nbsp;&nbsp;</th>
              <th>Updated</th>
              <th>&nbsp;Note&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;NObs&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;Arc&nbsp;&nbsp;</th>
              <th>&nbsp;H&nbsp;&nbsp;</th>
              <th>&nbsp;Not Seen/dys&nbsp;&nbsp;</th>
            </tr>
          </thead>

          <tbody>'''
        self.table_footer = "</tbody>\n</table>"

        # Set to None to show all differences
        self.maxDiff = None

    def test_parse_neocpep_not_soup(self):

        obj_ids = parse_NEOCP_extra_params(None)

        self.assertEqual(obj_ids, None)

    def test_parse_neocpep_no_objects(self):

        obj_ids = parse_NEOCP_extra_params(BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>', "html.parser"))

        self.assertEqual(obj_ids, None)

    def test_parse_neocpep_good_entry(self):
        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">CAH024</span>&nbsp;<input type="checkbox" name="obj" VALUE="CAH024"> CAH024</td>
        <td align="right"><span style="display:none">099</span> 99&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 20.0&nbsp;&nbsp;</td>
        <td><span style="display:none">005.2866</span>&nbsp;&nbsp;12 26.2 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">097.0712</span>&nbsp;&nbsp;+07 04&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none"> 8.4</span>&nbsp;&nbsp;41.6&nbsp;&nbsp;</td>
        <td><span style="display:none">A2457290.449504</span>&nbsp;Added Sept. 24.95 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   6&nbsp;</td>
        <td align="right">&nbsp;  0.06&nbsp;</td>
        <td align="right">&nbsp;31.0&nbsp;</td>
        <td align="right">&nbsp; 4.878&nbsp;</td>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = (u'CAH024', {'score' : 99,
                                        'discovery_date' : datetime(2015, 9, 20),
                                        'num_obs' : 6,
                                        'arc_length' : 0.06,
                                        'not_seen' : 4.878,
                                        'update_time': datetime(2015, 9, 24, 22, 47, 17),
                                        'updated' : False
                                }
        )
        self.assertNotEqual(None, obj_ids)
        self.assertEqual(expected_obj_ids[0], obj_ids[0][0])
        self.assertEqual(expected_obj_ids[1], obj_ids[0][1])

    @skipIf(True, "need to mock URL fetch of PCCP. Tested in TestParsePCCP")
    def test_parse_neocpep_bad_entry(self):
        """Test of 'Moved to the PCCP' entries"""

        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">WR0159E</span><center>WR0159E</center></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td>Moved to the <a href="/iau/NEO/pccp_tabular.html">PCCP</a></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td><td></td></tr>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = (u'WR0159E', {'score' : None,
                                        'discovery_date' : None,
                                        'num_obs' : None,
                                        'arc_length' : None,
                                        'not_seen' : None,
                                        'update_time': None,
                                        'updated' : None
                                       }
        )
        self.assertNotEqual(None, obj_ids)
        self.assertEqual(expected_obj_ids[0], obj_ids[0][0])
        self.assertEqual(expected_obj_ids[1], obj_ids[0][1])

    def test_parse_neocpep_good_entry_updated(self):
        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">P10o4Gp</span>&nbsp;<input type="checkbox" name="obj" VALUE="P10o4Gp"> P10o4Gp</td>
        <td align="right"><span style="display:none">088</span> 88&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 23.4&nbsp;&nbsp;</td>
        <td><span style="display:none">206.8747</span>&nbsp;&nbsp;01 52.5 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">091.0662</span>&nbsp;&nbsp;+01 04&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">29.2</span>&nbsp;&nbsp;20.8&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457290.163043</span>&nbsp;Updated Sept. 24.66 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   7&nbsp;</td>
        <td align="right">&nbsp;  0.86&nbsp;</td>
        <td align="right">&nbsp;20.5&nbsp;</td>
        <td align="right">&nbsp; 0.665&nbsp;</td>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = (u'P10o4Gp', {'score' : 88,
                                        'discovery_date' : datetime(2015, 9, 23, 9, 36),
                                        'num_obs' : 7,
                                        'arc_length' : 0.86,
                                        'not_seen' : 0.665,
                                        'update_time': datetime(2015, 9, 24, 15, 54, 47),
                                        'updated' : True
                                }
        )
        self.assertNotEqual(None, obj_ids)
        self.assertEqual(expected_obj_ids[0], obj_ids[0][0])
        self.assertEqual(expected_obj_ids[1], obj_ids[0][1])

    def test_parse_neocpep_good_entry_updated2(self):
        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">P10nw2g</span>&nbsp;<input type="checkbox" name="obj" VALUE="P10nw2g"> P10nw2g</td>
        <td align="right"><span style="display:none">100</span>100&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 06.3&nbsp;&nbsp;</td>
        <td><span style="display:none">150.4235</span>&nbsp;&nbsp;22 06.7 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">091.1616</span>&nbsp;&nbsp;+01 10&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">27.2</span>&nbsp;&nbsp;22.8&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457281.562894</span>&nbsp;Updated Sept. 16.06 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   6&nbsp;</td>
        <td align="right">&nbsp;  1.16&nbsp;</td>
        <td align="right">&nbsp;24.4&nbsp;</td>
        <td align="right">&nbsp;17.455&nbsp;</td>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = (u'P10nw2g', {'score' : 100,
                                        'discovery_date' : datetime(2015, 9, 6, 7, 12, 00),
                                        'num_obs' : 6,
                                        'arc_length' : 1.16,
                                        'not_seen' : 17.455,
                                        'update_time': datetime(2015, 9, 16, 1, 30, 34),
                                        'updated' : True
                                }
        )
        self.assertNotEqual(None, obj_ids)
        self.assertEqual(expected_obj_ids[0], obj_ids[0][0])
        self.assertEqual(expected_obj_ids[1], obj_ids[0][1])

    def test_parse_neocpep_good_multi_entries(self):
        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">P10nI6D</span>&nbsp;<input type="checkbox" name="obj" VALUE="P10nI6D"> P10nI6D</td>
        <td align="right"><span style="display:none">060</span> 60&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 09.3&nbsp;&nbsp;</td>
        <td><span style="display:none">146.3672</span>&nbsp;&nbsp;21 50.5 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">078.3569</span>&nbsp;&nbsp;-11 39&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">27.3</span>&nbsp;&nbsp;22.7&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457277.142173</span>&nbsp;Updated Sept. 11.64 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   6&nbsp;</td>
        <td align="right">&nbsp;  1.84&nbsp;</td>
        <td align="right">&nbsp;20.1&nbsp;</td>
        <td align="right">&nbsp;13.761&nbsp;</td><tr>
        <tr><td><span style="display:none">P10nw2g</span>&nbsp;<input type="checkbox" name="obj" VALUE="P10nw2g"> P10nw2g</td>
        <td align="right"><span style="display:none">100</span>100&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 06.3&nbsp;&nbsp;</td>
        <td><span style="display:none">150.4235</span>&nbsp;&nbsp;22 06.7 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">091.1616</span>&nbsp;&nbsp;+01 10&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">27.2</span>&nbsp;&nbsp;22.8&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457281.562894</span>&nbsp;Updated Sept. 16.06 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   6&nbsp;</td>
        <td align="right">&nbsp;  1.16&nbsp;</td>
        <td align="right">&nbsp;24.4&nbsp;</td>
        <td align="right">&nbsp;17.455&nbsp;</td><tr>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = [(u'P10nI6D', {'score' : 60,
                                        'discovery_date' : datetime(2015, 9, 9, 7, 12, 00),
                                        'num_obs' : 6,
                                        'arc_length' : 1.84,
                                        'not_seen' : 13.761,
                                        'update_time': datetime(2015, 9, 11, 15, 24, 44),
                                        'updated' : True
                                }),
                           (u'P10nw2g', {'score' : 100,
                                        'discovery_date' : datetime(2015, 9, 6, 7, 12, 00),
                                        'num_obs' : 6,
                                        'arc_length' : 1.16,
                                        'not_seen' : 17.455,
                                        'update_time': datetime(2015, 9, 16, 1, 30, 34),
                                        'updated' : True
                                })
        ]
        self.assertNotEqual(None, obj_ids)
        obj = 0
        while obj < len(expected_obj_ids):
            self.assertEqual(expected_obj_ids[obj][0], obj_ids[obj][0])
            self.assertEqual(expected_obj_ids[obj][1], obj_ids[obj][1])
            obj += 1


class TestParsePCCP(TestCase):

    def setUp(self):
        self.table_header = '''<table class="tablesorter">
          <thead>
            <tr>
              <th>&nbsp;&nbsp;Temp Desig&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Score&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Discovery</th>
              <th>&nbsp;&nbsp;R.A.&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Decl.&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;V&nbsp;&nbsp;</th>
              <th>Updated</th>
              <th>&nbsp;Note&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;NObs&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;Arc&nbsp;&nbsp;</th>
              <th>&nbsp;H&nbsp;&nbsp;</th>
              <th>&nbsp;Not Seen/dys&nbsp;&nbsp;</th>
            </tr>
          </thead>

          <tbody>'''
        self.table_footer = "</tbody>\n</table>"

        # Set to None to show all differences
        self.maxDiff = None

    def test_parse_pccp_not_soup(self):

        obj_ids = parse_PCCP(None)

        self.assertEqual(obj_ids, None)

    def test_parse_pccp_no_objects(self):

        obj_ids = parse_PCCP(BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>', "html.parser"))

        self.assertEqual(obj_ids, None)

    def test_parse_pccp_entry(self):

        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">WR0159E</span>&nbsp;<input type="checkbox" name="obj" VALUE="WR0159E"> WR0159E</td>
        <td align="right"><span style="display:none">010</span> 10&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 13.4&nbsp;&nbsp;</td>
        <td><span style="display:none">190.5617</span>&nbsp;&nbsp;01 01.5 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">089.7649</span>&nbsp;&nbsp;-00 14&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">31.2</span>&nbsp;&nbsp;18.8&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457294.241781</span>&nbsp;Updated Sept. 28.74 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp; 222&nbsp;</td>
        <td align="right">&nbsp; 15.44&nbsp;</td>
        <td align="right">&nbsp;14.4&nbsp;</td>
        <td align="right">&nbsp; 0.726&nbsp;</td>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_PCCP(html)
        expected_obj_ids = [(u'WR0159E', {'score' : 10,
                                        'discovery_date' : datetime(2015, 9, 13, 9, 36),
                                        'num_obs' : 222,
                                        'arc_length' : 15.44,
                                        'not_seen' : 0.726,
                                        'update_time': datetime(2015, 9, 28, 17, 48, 10),
                                        'updated' : True
                                       }
                            ), ]
        self.assertNotEqual(None, obj_ids)
        obj = 0
        while obj < len(expected_obj_ids):
            self.assertEqual(expected_obj_ids[obj][0], obj_ids[obj][0])
            self.assertEqual(expected_obj_ids[obj][1], obj_ids[obj][1])
            obj += 1

    def test_parse_pccp_multientries(self):

        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">WR0159E</span>&nbsp;<input type="checkbox" name="obj" VALUE="WR0159E"> WR0159E</td>
        <td align="right"><span style="display:none">010</span> 10&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 13.4&nbsp;&nbsp;</td>
        <td><span style="display:none">190.5617</span>&nbsp;&nbsp;01 01.5 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">089.7649</span>&nbsp;&nbsp;-00 14&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">31.2</span>&nbsp;&nbsp;18.8&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457294.241781</span>&nbsp;Updated Sept. 28.74 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp; 222&nbsp;</td>
        <td align="right">&nbsp; 15.44&nbsp;</td>
        <td align="right">&nbsp;14.4&nbsp;</td>
        <td align="right">&nbsp; 0.726&nbsp;</td>
        <tr><td><span style="display:none">WR0159X</span>&nbsp;<input type="checkbox" name="obj" VALUE="WR0159E"> WR0159E</td>
        <td align="right"><span style="display:none">007</span>  7&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 13.4&nbsp;&nbsp;</td>
        <td><span style="display:none">190.5617</span>&nbsp;&nbsp;01 01.5 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">089.7649</span>&nbsp;&nbsp;-00 14&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">31.2</span>&nbsp;&nbsp;18.8&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457294.241781</span>&nbsp;Updated Sept. 28.74 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp; 42&nbsp;</td>
        <td align="right">&nbsp; 15.44&nbsp;</td>
        <td align="right">&nbsp;14.4&nbsp;</td>
        <td align="right">&nbsp; 0.726&nbsp;</td>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_PCCP(html)
        expected_obj_ids = [(u'WR0159E', {'score' : 10,
                                        'discovery_date' : datetime(2015, 9, 13, 9, 36),
                                        'num_obs' : 222,
                                        'arc_length' : 15.44,
                                        'not_seen' : 0.726,
                                        'update_time': datetime(2015, 9, 28, 17, 48, 10),
                                        'updated' : True
                                       }
                            ),
                            (u'WR0159X', {'score' : 7,
                                        'discovery_date' : datetime(2015, 9, 13, 9, 36),
                                        'num_obs' : 42,
                                        'arc_length' : 15.44,
                                        'not_seen' : 0.726,
                                        'update_time': datetime(2015, 9, 28, 17, 48, 10),
                                        'updated' : True
                                       }
                            ),
                            ]
        self.assertNotEqual(None, obj_ids)
        obj = 0
        while obj < len(expected_obj_ids):
            self.assertEqual(expected_obj_ids[obj][0], obj_ids[obj][0])
            self.assertEqual(expected_obj_ids[obj][1], obj_ids[obj][1])
            obj += 1


class TestFetchMPCOrbit(TestCase):

    def setUp(self):
        # Read and make soup from a static version of the HTML table/page for
        # an object
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_2014UR.html'), 'r')
        self.test_mpcdb_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        # Set to None to show all differences
        self.maxDiff = None

    def test_fetch_2014UR(self):

        expected_elements = {'P-vector [x]': '-0.38101678',
                             'P-vector [y]': '-0.80462138',
                             'P-vector [z]': '-0.45542359',
                             'Q-vector [x]': '0.92259236',
                             'Q-vector [y]': '-0.29869255',
                             'Q-vector [z]': '-0.24414360',
                             'Tisserand w.r.t. Jupiter': '6.1',
                             'ΔV w.r.t. Earth': '6.0',
                             'absolute magnitude': '26.6',
                             'aphelion distance': '1.009',
                             'arc length': '357',
                             'argument of perihelion': '222.91160',
                             'ascending node': '24.87559',
                             'computer name': 'MPCALB',
                             'eccentricity': '0.0120915',
                             'epoch': '2016-01-13.0',
                             'epoch JD': '2457400.5',
                             'first observation date used': '2014-10-17.0',
                             'first opposition used': '2014',
                             'inclination': '8.25708',
                             'last observation date used': '2015-10-09.0',
                             'last opposition used': '2015',
                             'mean anomaly': '221.74204',
                             'mean daily motion': '0.99040030',
                             'observations used': '147',
                             'obj_id' : u'2014 UR',
                             'oppositions': '2',
                             'perihelion JD': '2457540.09806',
                             'perihelion date': '2016-05-31.59806',
                             'perihelion distance': '0.9847185',
                             'period': '1.0',
                             'perturbers coarse indicator': 'M-v',
                             'perturbers precise indicator': '003Eh',
                             'phase slope': '0.15',
                             'reference': 'MPEC 2015-T44',
                             'residual rms': '0.57',
                             'semimajor axis': '0.9967710',
                             'uncertainty': '1'}

        elements = parse_mpcorbit(self.test_mpcdb_page)
        self.assertEqual(expected_elements, elements)

    def test_badpage(self):

        expected_elements = {}
        elements = parse_mpcorbit(BeautifulSoup('<html></html>', 'html.parser'))
        self.assertEqual(expected_elements, elements)

    def test_badpage_with_empty_table(self):

        expected_elements = {}
        elements = parse_mpcorbit(BeautifulSoup('<html><table class="nb"><table></table></table></html>', 'html.parser'))
        self.assertEqual(expected_elements, elements)


class TestParseMPCObsFormat(TestCase):

    def setUp(self):
        """The "code" for the dictionary keys for the test lines is as follows:
        <char1>_<char2><char3>_<char4> where:
        <char1> is the type of desigination:
            p: provisional designation (e.g. 'K15TE5B'),
            t: temporary desigination (e.g. 'N00809b')
            n: numbered asteroid,
            c: comet
            s: (natural) satellite
        <char2> is the observation code or program code,
        <char3> is the observation type:
            C: CCD observations,
            R/r: radar observation,
            S/s: satellite observation
            x: replaced discovery observation
        <char4> is the precision of the obs:
            l: low precision
            h: high precision
            n: no magnitude
        """
        self.test_lines = { 'p_ C_l' :  u'     K15TE5B  C2015 10 19.36445 04 16 45.66 -02 06 29.9          18.7 RqEU023H45',
                            'p_KC_l' :  u'     K15TE5B KC2015 10 18.42125 04 16 20.07 -02 07 27.5          19.2 VqEU023H21',
                            'p_#C_l' :  u'     K15TE5B 5C2015 10 17.34423 04 15 51.57 -02 07 27.4          18.6 VqEU017W88',
                            'p_ C_h' :  u'     K15TE5B  C2015 10 13.08015704 13 52.281-02 06 45.33         19.51Rt~1YjBY28',
                            'p_ S_l' :  u'     N00809b  S2015 06 22.29960 21 02 46.72 +57 58 39.3          20   RLNEOCPC51',
                            'p_ s_l' :  u'     N00809b  s2015 06 22.29960 1 + 1978.7516 + 1150.7393 + 6468.8442   NEOCPC51',
                            'n_ R_l' :  u'01566         R1968 06 14.229167               +    11541710   2388 252 JPLRS253',
                            'n_ r_l' :  u'01566         r1968 06 14.229167S                        1000       252 JPLRS253',
                            'n_tC_l' :  u'01566        tC2002 07 31.54831 20 30 29.56 -47 49 14.5          18.1 Rcg0322474',
                            'p_ C_n' :  u'     WMAA95B  C2015 06 20.29109 16 40 36.42 -14 23 16.2                qNEOCPG96\n',
                            'p_ C_le' : u'     K13R33T  C2013 09 13.18561323 15 20.53 -10 21 52.6          20.4 V      W86\r\n',
                            'p_ C_f' :  u'     WSAE9A6  C2015 09 20.23688 21 41 08.64 -10 51 41.7               VqNEOCPG96',
                            'p_ x_l' :  u'g0232K10F41B* x2010 03 19.91359 06 26 37.29 +35 47 01.3                L~0FUhC51',
                            'p_quoteC_h': u"     G07212  'C2017 11 02.17380 03 13 37.926+19 27 47.07         21.4 GUNEOCP309",

                          }
        self.maxDiff = None

    def compare_dict(self, expected_params, params, tolerance=7):
        self.assertEqual(len(expected_params), len(params))
        for i in expected_params:
            if 'ra' in i or 'dec' in i:
                self.assertAlmostEqual(expected_params[i], params[i], tolerance)
            else:
                self.assertEqual(expected_params[i], params[i])

    def test_p_spaceC_l(self):
        expected_params = { 'body'  : 'K15TE5B',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 10, 19, 8, 44, 48, int(0.48*1e6)),
                            'obs_ra'    : 64.19025,
                            'obs_dec'   : -2.1083055555555554,
                            'obs_mag'   : 18.7,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'H45'
                          }

        params = parse_mpcobs(self.test_lines['p_ C_l'])

        self.compare_dict(expected_params, params)

    def test_p_KC_l(self):
        expected_params = { 'body'  : 'K15TE5B',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 10, 18, 10, 6, 36, 0),
                            'obs_ra'    : 64.083625,
                            'obs_dec'   : -2.1243055555555554,
                            'obs_mag'   : 19.2,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'H21'
                          }

        params = parse_mpcobs(self.test_lines['p_KC_l'])

        self.compare_dict(expected_params, params)

    def test_p_numC_l(self):
        expected_params = { 'body'  : 'K15TE5B',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 10, 17, 8, 15, 41, int(0.472*1e6)),
                            'obs_ra'    : 63.96487499999999,
                            'obs_dec'   : -2.1242777777777775,
                            'obs_mag'   : 18.6,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'W88'
                          }

        params = parse_mpcobs(self.test_lines['p_#C_l'])

        self.compare_dict(expected_params, params)

    def test_p_spaceC_h(self):
        expected_params = { 'body'  : 'K15TE5B',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 10, 13, 1, 55, 25, int(0.5648*1e6)),
                            'obs_ra'    : 63.4678375,
                            'obs_dec'   : -2.112591666666667,
                            'obs_mag'   : 19.51,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'PPMXL',
                            'site_code' : 'Y28'
                          }

        params = parse_mpcobs(self.test_lines['p_ C_h'])

        self.compare_dict(expected_params, params)

    def test_p_spaceS_l(self):
        expected_params = { 'body'  : 'N00809b',
                            'flags' : ' ',
                            'obs_type'  : 'S',
                            'obs_date'  : datetime(2015, 6, 22, 7, 11, 25, int(0.44*1e6)),
                            'obs_ra'    : 315.69466666666667,
                            'obs_dec'   : 57.977583333333333,
                            'obs_mag'   : 20.0,
                            'filter'    : 'R',
                            'astrometric_catalog' : '2MASS',
                            'site_code' : 'C51'
                            }

        params = parse_mpcobs(self.test_lines['p_ S_l'])

        self.compare_dict(expected_params, params)

    def test_p_spaces_l(self):
        expected_params = { 'body'  : 'N00809b',
                            'extrainfo' : self.test_lines['p_ s_l'],
                            'obs_type'  : 's',
                            'obs_date'  : datetime(2015, 6, 22, 7, 11, 25, int(0.44*1e6)),
                            'site_code' : 'C51'}

        params = parse_mpcobs(self.test_lines['p_ s_l'])

        self.compare_dict(expected_params, params)

    def test_p_spaceR_l(self):
        expected_params = {}

        params = parse_mpcobs(self.test_lines['n_ R_l'])

        self.compare_dict(expected_params, params)

    def test_p_spacer_l(self):
        expected_params = {}

        params = parse_mpcobs(self.test_lines['n_ r_l'])

        self.compare_dict(expected_params, params)

    def test_n_tC_l(self):
        expected_params = { 'body'  : '01566',
                            'flags' : 't',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2002, 7, 31, 13, 9, 33, int(0.984*1e6)),
                            'obs_ra'    : 307.6231666666667,
                            'obs_dec'   : -47.82069444444445,
                            'obs_mag'   : 18.1,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'USNO-A2',
                            'site_code' : '474'
                          }

        params = parse_mpcobs(self.test_lines['n_tC_l'])

        self.compare_dict(expected_params, params)

    def test_p_spaceC_n(self):
        expected_params = { 'body'  : 'WMAA95B',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 6, 20, 6, 59, 10, int(0.176*1e6)),
                            'obs_ra'    : 250.15175,
                            'obs_dec'   : -14.387833333333333,
                            'obs_mag'   : None,
                            'filter'    : ' ',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        params = parse_mpcobs(self.test_lines['p_ C_n'])

        self.compare_dict(expected_params, params)

    def test_p_spacex_l(self):
        """This tests the case of an 'x' observation for a replaced discovery
        observation. From the MPC page
        (http://www.minorplanetcenter.net/iau/info/OpticalObs.html, Note 2):
        "In addition, there are 'X' and 'x' which are used only for already-
        filed observations. 'X' was given originally only to discovery
        observations that were approximate or semi-accurate and that had accurate
        measures corresponding to the time of discovery: this has been extended to
        other replaced discovery observations. Observations marked 'X'/'x' are to be
        suppressed in residual blocks. They are retained so that there exists
        an original record of a discovery. """
        expected_params = { }

        params = parse_mpcobs(self.test_lines['p_ x_l'])

        self.compare_dict(expected_params, params)

    def test_blankline(self):
        expected_params = {}

        params = parse_mpcobs('')

        self.compare_dict(expected_params, params)

    def test_allspacesline(self):
        expected_params = {}

        params = parse_mpcobs(' ' * 80)

        self.compare_dict(expected_params, params)

    def test_p_spaceC_le(self):
        expected_params = { 'body'  : 'K13R33T',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2013, 9, 13, 4, 27, 16, int(0.9632*1e6)),
                            'obs_ra'    : 348.8355416666667,
                            'obs_dec'   : -10.36461111111111,
                            'obs_mag'   : 20.4,
                            'filter'    : 'V',
                            'astrometric_catalog' : '',
                            'site_code' : 'W86'
                          }

        params = parse_mpcobs(self.test_lines['p_ C_le'])

        self.compare_dict(expected_params, params)

    def test_p_spaceC_f(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 41, 6, int(0.432*1e6)),
                            'obs_ra'    : 325.28599999999994,
                            'obs_dec'   : -10.861583333333332,
                            'obs_mag'   : None,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        params = parse_mpcobs(self.test_lines['p_ C_f'])

        self.compare_dict(expected_params, params)

    def test_p_quoteC_h(self):

        expected_params = { 'body'  : 'G07212',
                            'flags' : "'",
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2017, 11, 2, 4, 10, 16, int(0.32*1e6)),
                            'obs_ra'    : 48.408025,
                            'obs_dec'   : 19.463075,
                            'obs_mag'   : 21.4,
                            'filter'    : 'G',
                            'astrometric_catalog' : 'GAIA-DR1',
                            'site_code' : '309'
                          }

        params = parse_mpcobs(self.test_lines['p_quoteC_h'])

        self.compare_dict(expected_params, params)


class TestFetchNEOCPObservations(TestCase):

    def setUp(self):

        self.maxDiff = None

    def test_removed_object(self):
        page = BeautifulSoup('<html><body><pre>\nNone available at this time.\n</pre></body></html>', "html.parser")
        expected = None

        observations = fetch_NEOCP_observations(page)
        self.assertEqual(expected, observations)

    def test_readlines(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_P10pqB2.dat'), 'r')
        obs_data = test_fh.read()
        test_fh.close()
        page = BeautifulSoup(obs_data, "html.parser")

        expected = [u'     P10pqB2  C2015 11 17.40000 03 44 26.153-07 26 22.40         20.8 wLNEOCPF51',
                    u'     P10pqB2  C2015 11 17.41166 03 44 24.591-07 26 51.93         20.9 wLNEOCPF51',
                    u'     P10pqB2  C2015 11 17.43505 03 44 21.461-07 27 51.02         20.9 wLNEOCPF51',
                    u'     P10pqB2 KC2015 11 18.24829 03 42 40.57 -08 02 06.0          20.6 RoNEOCP291',
                    u'     P10pqB2 KC2015 11 18.24999 03 42 40.36 -08 02 10.2          20.6 RoNEOCP291',
                    u'     P10pqB2 KC2015 11 18.25170 03 42 40.13 -08 02 14.4          20.6 RoNEOCP291',
                    u'     P10pqB2 KC2015 11 18.33020 03 42 29.28 -08 05 31.8                oNEOCP711',
                    u'     P10pqB2 KC2015 11 18.33314 03 42 28.87 -08 05 39.2                oNEOCP711',
                    u'     P10pqB2 KC2015 11 18.33622 03 42 28.44 -08 05 46.7                oNEOCP711',
        ]

        observations = fetch_NEOCP_observations(page)
        self.assertEqual(expected, observations)


class TestIMAPLogin(TestCase):

    def setUp(self):
        pass

    @mock.patch('astrometrics.sources_subs.imaplib')
    def test_server_connection(self, mockimaplib):
        mailbox = imap_login('foo@bar.net', 'Wibble', 'localhost')
        mockimaplib.IMAP4_SSL.assert_called_with('localhost')
        self.assertNotEqual(None, mailbox)

    @mock.patch('astrometrics.sources_subs.imaplib')
    def test_badserver(self, mockimaplib):
        mockimaplib.IMAP4_SSL.side_effect = error(111, 'Connection refused')
        mailbox = imap_login('foo@bar.net', 'Wibble', 'localhost')
        self.assertEqual(None, mailbox)

    @mock.patch('astrometrics.sources_subs.imaplib')
    def test_badfolder(self, mockimaplib):
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("NO", ['[NONEXISTENT] Unknown Mailbox: Wibble (Failure)'])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox, folder="Wibble")
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    def test_emptyfolder(self, mockimaplib):
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'0'])
        mailbox.search.return_value = ("OK", [b''])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    def test_foldersearchfailure(self, mockimaplib):
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'0'])
        mailbox.search.return_value = ("NO", [b''])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    def test_cannot_retrieve_msg_high(self, mockimaplib):
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ("OK", [None, ])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    def test_cannot_retrieve_msg_low(self, mockimaplib):
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.side_effect = error("FETCH command error: BAD ['Could not parse command']")
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_msg_correct_match(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 18,  21, 27, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ("OK", [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 CV246 - Observations Requested\r\nDate: Tue, 18 Feb 2016 21:27:04 +000\r\n')])

        expected_targets = ['2016 CV246']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_msg_has_bad_prefix(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 18,  21, 27, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-birds-observations] 2016 CV246 - Observations Requested\r\nDate: Tue, 16 Feb 2018 21:27:04 +000\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_msg_has_bad_suffix(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 18,  21, 27, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 CV246 - Radar Requested\r\nDate: Tue, 18 Feb 2016 21:27:04 +000\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_msg_good_with_tz(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 24,  1, 0, 0)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 22 Feb 2016 20:27:04 -0500\r\n')])

        expected_targets = ['2016 BA14']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_reject_msg_old_with_tz(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 15,  4, 27, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 13 Feb 2016 20:27:04 -0800\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_multiple_msgs(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 24,  1, 0, 0)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'2'])
        mailbox.search.return_value = ("OK", [b'1 2'])
        results = [ ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 22 Feb 2016 20:27:04 -0500\r\n')]),
                    ('OK', [(b'2 (RFC822 {12324}', b'Subject: [small-bodies-observations] 2016 CV123 - Observations Requested\r\nDate: Tue, 22 Feb 2016 22:47:42 -0500\r\n')])
                   ]
        mailbox.fetch.side_effect = results

        expected_targets = ['2016 BA14', '2016 CV123']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_one_msg_multiple_old_msgs(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 24,  1, 0, 0)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'3'])
        mailbox.search.return_value = ("OK", [b'1 2 4'])
        results = [ ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 20516 BA14 - Observations Requested\r\nDate: Tue, 22 Feb 2015 20:27:04 -0500\r\n')]),
                    ('OK', [(b'2 (RFC822 {12324}', b'Subject: [small-bodies-observations] 2015 CV123 - Observations Requested\r\nDate: Tue, 22 Dec 2015 22:47:42 -0500\r\n')]),
                    ('OK', [(b'4 (RFC822 {12324}', b'Subject: [small-bodies-observations] 2016 CV123 - Observations Requested\r\nDate: Tue, 22 Feb 2016 22:47:42 -0500\r\n')])
                    ]
        mailbox.fetch.side_effect = results

        expected_targets = ['2016 CV123']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_fwd_msg_(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 23, 19, 51, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: Fwd: [small-bodies-observations] 2016 DJ - Observations Requested\r\nDate: Tue, 23 Feb 2016 11:25:29 -0800\r\n')])

        expected_targets = ['2016 DJ']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_reject_msg_old_with_tz_and_cutoff(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 16,  4, 27, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 13 Feb 2016 20:27:04 -0800\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox, date_cutoff=2)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_accept_msg_old_with_tz_and_cutoff(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 16,  3, 26, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 13 Feb 2016 20:27:04 -0800\r\n')])

        expected_targets = ['2016 BA14']
        targets = fetch_NASA_targets(mailbox, date_cutoff=2)
        self.assertEqual(expected_targets, targets)

    @mock.patch('astrometrics.sources_subs.imaplib')
    @mock.patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_accept_msg_multiple_targets(self, mockimaplib):
        MockDateTime.change_datetime(2016, 10, 25,  3, 26, 5)
        mailbox = mock.MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value =  ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 TQ11, 2016 SR2, 2016 NP56,\r\n\t2016 ND1- Observations Requested\r\nDate: Mon, 24 Oct 2016 20:20:57 +0000\r\n')])

        expected_targets = ['2016 TQ11', '2016 SR2', '2016 NP56', '2016 ND1']
        targets = fetch_NASA_targets(mailbox, date_cutoff=2)
        self.assertEqual(expected_targets, targets)

class TestSFUFetch(TestCase):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_sfu.html'), 'r')
        self.test_sfu_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.sfu = u.def_unit(['sfu', 'solar flux unit'], 10000.0*u.Jy)
        u.add_enabled_units([self.sfu])

    def test(self):

        expected_result = (datetime(2018,1,15,17,44,10), 70*self.sfu)

        sfu_result = fetch_sfu(self.test_sfu_page)

        self.assertEqual(expected_result[0], sfu_result[0])
        self.assertEqual(expected_result[1].value, sfu_result[1].value)
        self.assertEqual(expected_result[1].unit, sfu_result[1].unit)
        self.assertEqual(expected_result[1].to(u.MJy), sfu_result[1].to(u.MJy))


class TestConfigureDefaults(TestCase):

    def setUp(self):
        pass

    def test_tfn_point4m(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'Z21',
              }

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'site': 'TFN',
                            'exp_type': 'EXPOSE',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_ogg_point4m(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'T04',
              }

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'OGG',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_coj_point4m(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'Q59',
              }

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'COJ',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_cpt_point4m(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'L09',
              }

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'CPT',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_elp_point4m(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'V38',
              }

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': 'aqwa',
                            'exp_type': 'EXPOSE',
                            'site': 'ELP',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_point4m_num1(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'W89',
              }

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'LSC',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_point4m_num2(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'W79',
              }

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'LSC',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_sinistro(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'W86',
              }

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'LSC',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_bad_sinistro(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'W87',
              }

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'LSC',
                            'binning': 1,
                            'site_code': 'W87',
                            'exp_count': 42,
                            'exp_time': 42.0}

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_ftn(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'F65',
              }

        expected_params = { 'instrument':  '2M0-SCICAM-SPECTRAL',
                            'pondtelescope': '2m0',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'OGG',
                            'binning': 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_fts(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'E10',
              }

        expected_params = { 'instrument':  '2M0-SCICAM-SPECTRAL',
                            'pondtelescope': '2m0',
                            'observatory' : '',
                            'exp_type': 'EXPOSE',
                            'site' : 'COJ',
                            'binning' : 2}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_elp_sinistro(self):
        test_params = {
              'exp_count': 42,
              'exp_time': 42.0,
              'site_code': 'V37',
              }

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'site': 'ELP',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_1m_sinistro_cpt(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '1m0',
                            'site': 'CPT',
                            'site_code': 'K92'}

        params = {'site_code': 'K92'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_lsc_doma(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '1m0',
                            'site': 'LSC',
                            'site_code': 'W85'}

        params = {'site_code': 'W85'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_lsc(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '1m0',
                            'site': 'LSC',
                            'site_code': 'W86'}

        params = {'site_code': 'W86'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_elp(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '1m0',
                            'site': 'ELP',
                            'site_code': 'V37'}

        params = {'site_code': 'V37'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_lsc_domec(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '1m0',
                            'site': 'LSC',
                            'site_code': 'W87'}

        params = {'site_code': 'W87'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_cpt_domec(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '1m0',
                            'site': 'CPT',
                            'site_code': 'K93'}

        params = {'site_code': 'K93'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_ogg(self):
        expected_params = { 'binning': 2,
                            'instrument': '2M0-SCICAM-SPECTRAL',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '2m0',
                            'site': 'OGG',
                            'site_code': 'F65'}

        params = {'site_code': 'F65'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_coj(self):
        expected_params = { 'binning': 2,
                            'instrument': '2M0-SCICAM-SPECTRAL',
                            'observatory': '',
                            'exp_type': 'EXPOSE',
                            'pondtelescope': '2m0',
                            'site': 'COJ',
                            'site_code': 'E10'}

        params = {'site_code': 'E10'}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_ogg_floyds(self):
        expected_params = { 'spectroscopy': True,
                            'binning'     : 1,
                            'spectra_slit': 'slit_2.0as',
                            'instrument'  : '2M0-FLOYDS-SCICAM',
                            'observatory' : '',
                            'exp_type'    : 'SPECTRUM',
                            'pondtelescope' : '2m0',
                            'site'        : 'OGG',
                            'site_code'   : 'F65',
                            'instrument_code' : 'F65-FLOYDS'}

        params = { 'site_code' : 'F65', 'instrument_code' : 'F65-FLOYDS', 'spectroscopy' : True}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_coj_floyds(self):
        expected_params = { 'spectroscopy': True,
                            'binning'     : 1,
                            'spectra_slit': 'slit_2.0as',
                            'instrument'  : '2M0-FLOYDS-SCICAM',
                            'observatory' : '',
                            'exp_type'    : 'SPECTRUM',
                            'pondtelescope': '2m0',
                            'site'        : 'COJ',
                            'site_code'   : 'E10',
                            'instrument_code' : 'E10-FLOYDS'}

        params = { 'site_code' : 'E10', 'instrument_code' : 'E10-FLOYDS', 'spectroscopy' : True}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)


class TestMakeMolecule(TestCase):

    def setUp(self):

        self.params_2m0_imaging = configure_defaults({ 'site_code': 'F65',
                                                       'exp_time' : 60.0,
                                                       'exp_count' : 12,
                                                       'filter_pattern' : 'solar'})
        self.filt_2m0_imaging = build_filter_blocks(self.params_2m0_imaging['filter_pattern'],
                                                    self.params_2m0_imaging['exp_count'])[0]

        self.params_1m0_imaging = configure_defaults({ 'site_code': 'K92',
                                                       'exp_time' : 60.0,
                                                       'exp_count' : 12,
                                                       'filter_pattern' : 'w'})
        self.filt_1m0_imaging = build_filter_blocks(self.params_1m0_imaging['filter_pattern'],
                                                    self.params_1m0_imaging['exp_count'])[0]
        self.params_0m4_imaging = configure_defaults({ 'site_code': 'Z21',
                                                       'exp_time' : 90.0,
                                                       'exp_count' : 18,
                                                       'filter_pattern' : 'w'})
        self.filt_0m4_imaging = build_filter_blocks(self.params_0m4_imaging['filter_pattern'],
                                                    self.params_0m4_imaging['exp_count'])[0]

        self.params_2m0_spectroscopy = configure_defaults({ 'site_code': 'F65',
                                                            'instrument_code' : 'F65-FLOYDS',
                                                            'spectroscopy' : True,
                                                            'exp_time' : 180.0,
                                                            'exp_count' : 1})
        self.filt_2m0_spectroscopy = ['slit_2.0as', 1]

    def test_2m_imaging(self):

        expected_molecule = {
                             'type' : 'EXPOSE',
                             'exposure_count' : 12,
                             'exposure_time' : 60.0,
                             'bin_x'       : 2,
                             'bin_y'       : 2,
                             'instrument_name' : '2M0-SCICAM-SPECTRAL',
                             'filter'      : 'solar',
                             'ag_mode'     : 'OPTIONAL',
                             'ag_name'     : ''
                            }

        molecule = make_molecule(self.params_2m0_imaging, self.filt_2m0_imaging)

        self.assertEqual(expected_molecule, molecule)

    def test_1m_imaging(self):

        expected_molecule = {
                             'type' : 'EXPOSE',
                             'exposure_count' : 12,
                             'exposure_time' : 60.0,
                             'bin_x'       : 1,
                             'bin_y'       : 1,
                             'instrument_name' : '1M0-SCICAM-SINISTRO',
                             'filter'      : 'w',
                             'ag_mode'     : 'OPTIONAL',
                             'ag_name'     : ''
                            }

        molecule = make_molecule(self.params_1m0_imaging, self.filt_1m0_imaging)

        self.assertEqual(expected_molecule, molecule)

    def test_0m4_imaging(self):

        expected_molecule = {
                             'type' : 'EXPOSE',
                             'exposure_count' : 18,
                             'exposure_time' : 90.0,
                             'bin_x'       : 2,
                             'bin_y'       : 2,
                             'instrument_name' : '0M4-SCICAM-SBIG',
                             'filter'      : 'w',
                             'ag_mode'     : 'OPTIONAL',
                             'ag_name'     : ''
                            }

        molecule = make_molecule(self.params_0m4_imaging, self.filt_0m4_imaging)

        self.assertEqual(expected_molecule, molecule)

    def test_2m_spectroscopy_spectrum(self):

        expected_molecule = {
                             'type' : 'SPECTRUM',
                             'exposure_count' : 1,
                             'exposure_time' : 180.0,
                             'bin_x'       : 1,
                             'bin_y'       : 1,
                             'instrument_name' : '2M0-FLOYDS-SCICAM',
                             'spectra_slit': 'slit_2.0as',
                             'ag_mode'     : 'ON',
                             'ag_name'     : '',
                             'acquire_mode': 'WCS'
                            }

        molecule = make_molecule(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)

        self.assertEqual(expected_molecule, molecule)

    def test_2m_spectroscopy_arc(self):

        self.params_2m0_spectroscopy['exp_type'] = 'ARC'

        expected_molecule = {
                             'type' : 'ARC',
                             'exposure_count' : 1,
                             'exposure_time' : 60.0,
                             'bin_x'       : 1,
                             'bin_y'       : 1,
                             'instrument_name' : '2M0-FLOYDS-SCICAM',
                             'spectra_slit': 'slit_2.0as',
                             'ag_mode'     : 'OFF',
                             'ag_name'     : '',
                             'acquire_mode': 'WCS'
                            }

        molecule = make_molecule(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)

        self.assertEqual(expected_molecule, molecule)

    def test_2m_spectroscopy_arc_multiple_spectra(self):

        self.params_2m0_spectroscopy['exp_type'] = 'ARC'
        self.params_2m0_spectroscopy['exp_count'] = 2

        expected_molecule = {
                             'type' : 'ARC',
                             'exposure_count' : 1,
                             'exposure_time' : 60.0,
                             'bin_x'       : 1,
                             'bin_y'       : 1,
                             'instrument_name' : '2M0-FLOYDS-SCICAM',
                             'spectra_slit': 'slit_2.0as',
                             'ag_mode'     : 'OFF',
                             'ag_name'     : '',
                             'acquire_mode': 'WCS'
                            }

        molecule = make_molecule(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)

        self.assertEqual(expected_molecule, molecule)

    def test_2m_spectroscopy_lampflat(self):

        self.params_2m0_spectroscopy['exp_type'] = 'LAMP_FLAT'

        expected_molecule = {
                             'type' : 'LAMP_FLAT',
                             'exposure_count' : 1,
                             'exposure_time' : 60.0,
                             'bin_x'       : 1,
                             'bin_y'       : 1,
                             'instrument_name' : '2M0-FLOYDS-SCICAM',
                             'spectra_slit': 'slit_2.0as',
                             'ag_mode'     : 'OFF',
                             'ag_name'     : '',
                             'acquire_mode': 'WCS'
                            }

        molecule = make_molecule(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)

        self.assertEqual(expected_molecule, molecule)

    def test_2m_spectroscopy_lampflat_multiple_spectra(self):

        self.params_2m0_spectroscopy['exp_type'] = 'LAMP_FLAT'
        self.params_2m0_spectroscopy['exp_count'] = 42

        expected_molecule = {
                             'type' : 'LAMP_FLAT',
                             'exposure_count' : 1,
                             'exposure_time' : 60.0,
                             'bin_x'       : 1,
                             'bin_y'       : 1,
                             'instrument_name' : '2M0-FLOYDS-SCICAM',
                             'spectra_slit': 'slit_2.0as',
                             'ag_mode'     : 'OFF',
                             'ag_name'     : '',
                             'acquire_mode': 'WCS'
                            }

        molecule = make_molecule(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)

        self.assertEqual(expected_molecule, molecule)

class TestMakeMolecules(TestCase):

    def setUp(self):

        self.params_2m0_imaging = configure_defaults({ 'site_code': 'F65',
                                                       'exp_time' : 60.0,
                                                       'exp_count' : 12,
                                                       'filter_pattern' : 'solar'})
        self.filt_2m0_imaging = build_filter_blocks(self.params_2m0_imaging['filter_pattern'],
                                                    self.params_2m0_imaging['exp_count'])[0]

        self.params_1m0_imaging = configure_defaults({ 'site_code': 'K92',
                                                       'exp_time' : 60.0,
                                                       'exp_count' : 12,
                                                       'filter_pattern' : 'w'})
        self.filt_1m0_imaging = build_filter_blocks(self.params_1m0_imaging['filter_pattern'],
                                                    self.params_1m0_imaging['exp_count'])[0]
        self.params_0m4_imaging = configure_defaults({ 'site_code': 'Z21',
                                                       'exp_time' : 90.0,
                                                       'exp_count' : 18,
                                                       'filter_pattern' : 'w'})
        self.filt_0m4_imaging = build_filter_blocks(self.params_0m4_imaging['filter_pattern'],
                                                    self.params_0m4_imaging['exp_count'])[0]

        self.params_2m0_spectroscopy = configure_defaults({ 'site_code': 'F65',
                                                            'instrument_code' : 'F65-FLOYDS',
                                                            'spectroscopy' : True,
                                                            'exp_time' : 180.0,
                                                            'exp_count' : 1,
                                                            'filter_pattern' : 'slit_2.0as'})
        self.filt_2m0_spectroscopy = ['slit_2.0as',]

    def test_2m_imaging(self):

        expected_num_molecules = 1
        expected_type = 'EXPOSE'

        molecules = make_molecules(self.params_2m0_imaging)

        self.assertEqual(expected_num_molecules, len(molecules))
        self.assertEqual(expected_type, molecules[0]['type'])

    def test_1m_imaging(self):

        expected_num_molecules = 1
        expected_type = 'EXPOSE'

        molecules = make_molecules(self.params_1m0_imaging)

        self.assertEqual(expected_num_molecules, len(molecules))
        self.assertEqual(expected_type, molecules[0]['type'])

    def test_0m4_imaging(self):

        expected_num_molecules = 1
        expected_type = 'EXPOSE'

        molecules = make_molecules(self.params_0m4_imaging)

        self.assertEqual(expected_num_molecules, len(molecules))
        self.assertEqual(expected_type, molecules[0]['type'])

    def test_2m_spectroscopy_nocalibs(self):

        expected_num_molecules = 1
        expected_type = 'SPECTRUM'

        molecules = make_molecules(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_molecules, len(molecules))
        self.assertEqual(expected_type, molecules[0]['type'])

    def test_2m_spectroscopy_calibs_before(self):

        self.params_2m0_spectroscopy['calibs'] = 'before'
        expected_num_molecules = 3

        molecules = make_molecules(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_molecules, len(molecules))
        self.assertEqual('LAMP_FLAT', molecules[0]['type'])
        self.assertEqual('ARC', molecules[1]['type'])
        self.assertEqual('SPECTRUM', molecules[2]['type'])

    def test_2m_spectroscopy_calibs_after(self):

        self.params_2m0_spectroscopy['calibs'] = 'AFTER'
        expected_num_molecules = 3

        molecules = make_molecules(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_molecules, len(molecules))
        self.assertEqual('LAMP_FLAT', molecules[2]['type'])
        self.assertEqual('ARC', molecules[1]['type'])
        self.assertEqual('SPECTRUM', molecules[0]['type'])

    def test_2m_spectroscopy_calibs_both(self):

        self.params_2m0_spectroscopy['calibs'] = 'BoTh'
        expected_num_molecules = 5

        molecules = make_molecules(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_molecules, len(molecules))
        self.assertEqual('LAMP_FLAT', molecules[0]['type'])
        self.assertEqual('ARC', molecules[1]['type'])
        self.assertEqual('SPECTRUM', molecules[2]['type'])
        self.assertEqual('ARC', molecules[3]['type'])
        self.assertEqual('LAMP_FLAT', molecules[4]['type'])


class TestMakeCadence(TestCase):

    def setUp(self):

        self.elements = {"epochofel_mjd": 58000.0,
                         "current_name" : "3122",
                         "name" : "3122",
                         "meandist": 1.7691326,
                         "longascnode": 336.0952,
                         "orbinc": 22.1508, 
                         "eccentricity": 0.4233003,
                         "meananom": 351.43854,
                         "elements_type": "MPC_MINOR_PLANET",
                         "type": "NON_SIDEREAL",
                         "argofperih": 27.8469}
        self.params = { 'utc_date' : datetime(2017, 8, 20, 0, 0),
                        'start_time' : datetime(2017, 8, 20, 8, 40),
                        'end_time' : datetime(2017, 8, 20, 19, 40),
                        'period' : 2.0,
                        'jitter' : 0.25,
                        'group_id' : "3122_Q59-20170815",
                        'proposal_id' : 'LCOSchedulerTest',
                        'user_id' : 'tlister@lcogt.net',
                        'exp_type' : 'EXPOSE',
                        'exp_count' : 105,
                        'exp_time' : 20.0,
                        'binning' : 2,
                        'instrument' : '0M4-SCICAM-SBIG',
                        'filter' : 'w',
                        'site' : 'COJ',
                        'pondtelescope' : '0m4a',
                        'site_code' : 'Q59'
                        }
        self.ipp_value = 1.0

        self.request = {  'constraints' : {'max_airmass': 2.0, 'min_lunar_distance': 15},
                          'location' : { 'site' : self.params['site'].lower(),
                                         'telescope_class' : self.params['pondtelescope'][0:3]
                                       },
                          'target' : self.elements,
                          'molecules' : [{  'ag_mode': 'OPTIONAL',
                                            'ag_name': '',
                                            'bin_x' : self.params['binning'],
                                            'bin_y' : self.params['binning'],
                                            'exposure_count' : self.params['exp_count'],
                                            'exposure_time' : self.params['exp_time'],
                                            'filter' : self.params['filter'],
                                            'instrument_name' : self.params['instrument'],
                                            'type' : self.params['exp_type']
                                        }],
                          'windows' : [{'start' : datetime.strftime(self.params['start_time'], '%Y-%m-%dT%H:%M:%SZ'),
                                        'end'   : datetime.strftime(self.params['end_time'], '%Y-%m-%dT%H:%M:%SZ')
                                        }]
                        }
        self.request['target']['epochofel'] = self.request['target']['epochofel_mjd']
        self.request['target']['scheme'] = self.request['target']['elements_type']

        self.maxDiff = None

    @mock.patch('astrometrics.sources_subs.expand_cadence', mock_expand_cadence)
    def test_cadence_valhalla(self):
        expected = {
                     u'group_id': u'3122_Q59-20170815',
                     u'ipp_value': 1.0,
                     u'observation_type': u'NORMAL',
                     u'operator': u'MANY',
                     u'proposal': u'LCOSchedulerTest',
                     u'requests': [{u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T06:07:30Z',
                         u'start': u'2017-09-02T06:00:00Z'}]},
                      {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T08:07:30Z',
                         u'start': u'2017-09-02T07:52:30Z'}]},
                      {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T10:07:30Z',
                         u'start': u'2017-09-02T09:52:30Z'}]},
                      {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T12:07:30Z',
                         u'start': u'2017-09-02T11:52:30Z'}]}],
                     u'submitter': u'tlister@lcogt.net'}

        self.request['location']['site'] = 'ogg'
        self.request['molecules'][0]['exposure_count'] = 10
        self.request['molecules'][0]['exposure_time'] = 2.0
        params = self.params
        params['start_time'] = datetime(2017, 9, 2, 6, 0, 0)
        params['end_time'] = datetime(2017, 9, 2, 12, 40, 0)

        ur = make_cadence_valhalla(self.request, params, self.ipp_value)
        for key in ur.keys():
            self.assertEqual(expected[key], ur[key])

    @mock.patch('astrometrics.sources_subs.expand_cadence', mock_expand_cadence)
    def test_cadence_wrapper(self):
        expected = {
                     u'group_id': u'3122_Q59-20170815',
                     u'ipp_value': 1.0,
                     u'observation_type': u'NORMAL',
                     u'operator': u'MANY',
                     u'proposal': u'LCOSchedulerTest',
                     u'requests': [{u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T06:07:30Z',
                         u'start': u'2017-09-02T06:00:00Z'}]},
                      {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T08:07:30Z',
                         u'start': u'2017-09-02T07:52:30Z'}]},
                      {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T10:07:30Z',
                         u'start': u'2017-09-02T09:52:30Z'}]},
                      {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                       u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                       u'molecules': [{u'ag_mode': u'OPTIONAL',
                         u'ag_name': u'',
                         u'bin_x': 2,
                         u'bin_y': 2,
                         u'exposure_count': 10,
                         u'exposure_time': 2.0,
                         u'filter': u'w',
                         u'instrument_name': u'0M4-SCICAM-SBIG',
                         u'priority': 1,
                         u'type': u'EXPOSE'}],
                       u'target': {u'argofperih': 27.8469,
                        u'eccentricity': 0.4233003,
                        u'epochofel': 58000.0,
                        u'longascnode': 336.0952,
                        u'meananom': 351.43854,
                        u'meandist': 1.7691326,
                        u'name': u'3122',
                        u'orbinc': 22.1508,
                        u'scheme': u'MPC_MINOR_PLANET',
                        u'type': u'NON_SIDEREAL'},
                       u'windows': [{u'end': u'2017-09-02T12:07:30Z',
                         u'start': u'2017-09-02T11:52:30Z'}]}],
                     u'submitter': u'tlister@lcogt.net'}

        self.request['location']['site'] = 'ogg'
        self.request['molecules'][0]['exposure_count'] = 10
        self.request['molecules'][0]['exposure_time'] = 2.0
        params = self.params
        params['start_time'] = datetime(2017, 9, 2, 6, 0, 0)
        params['end_time'] = datetime(2017, 9, 2, 12, 40, 0)

        ur = make_cadence(self.elements, params, self.ipp_value, self.request)
        for key in ur.keys():
            self.assertEqual(expected[key], ur[key])


class TestFetchTaxonomyData(TestCase):

    def setUp(self):
        # Read and make soup from the stored, partial version of the PDS Taxonomy Database
        # test_fh = open(os.path.join('astrometrics', 'tests', 'test_taxonomy_page.dat'), 'r')
        # self.test_taxonomy_page = test_fh
        # test_fh.close()
        self.test_taxonomy_page = os.path.join('astrometrics', 'tests', 'test_taxonomy_page.dat')

    def test_basics(self):
        expected_length = 33
        targets = fetch_taxonomy_page(self.test_taxonomy_page)

        self.assertEqual(expected_length, len(targets))

    def test_targets(self):
        expected_targets = [ ['980', 'SU', "T", "PDS6", '7G'],
                             ['980', 'S3', "Ba", "PDS6", '7I'],
                             ['980', 'S', "Td", "PDS6", '2I'],
                             ['980', 'T', "H", "PDS6", '65'],
                             ['980', 'L', "B", "PDS6", 's'],
                             ['4713', 'A', "B", "PDS6", 's'],
                             ['4713', 'A', "3T", "PDS6", ' '],
                             ['4713', 'Sl', "3B", "PDS6", ' '],
                             ['4713', 'Sw', "BD", "PDS6", 'a'],
                            ]
        tax_data = fetch_taxonomy_page(self.test_taxonomy_page)
        for line in expected_targets:
            self.assertIn(line, tax_data)

    def test_tax(self):
        expected_tax = [ 'SU',
                         'S3',
                         'S',
                         'T',
                         'L',
                         'CGTP:',
                         'S',
                         'V',
                         '***',
                         'V',
                         'S',
                         'S',
                         'Sq',
                         'S',
                         'B',
                         'QU',
                         'Q',
                         'S',
                         'K',
                         'Xe',
                         'S',
                         'S',
                         'S',
                         'S',
                         'S',
                         'A',
                         'Sw',
                         'A',
                         'Sl',
                         'Sl',
                         'C',
                         'Xc',
                         'V',
                          ]
        tax_data = fetch_taxonomy_page(self.test_taxonomy_page)
        taxonomy = [row[1] for row in tax_data]
        self.assertEqual(expected_tax, taxonomy)

    def test_tax_site_pull(self):
        expected_line = ['1', 'G', "T", "PDS6", "7G"]
        tax_data = fetch_taxonomy_page()
        self.assertEqual(expected_line, tax_data[0])


class TestFetchTargetsFromList(TestCase):

    def test_commad_line_entry(self):
        test_list = ['588', '2759', '4035', '1930_UB', '1989 AL2']
        out_list = ['588', '2759', '4035', '1930 UB', '1989 AL2']
        self.assertEqual(out_list, fetch_list_targets(test_list))

    def test_text_file_entry(self):
        test_file = [os.path.join('astrometrics', 'tests', 'test_target_list_page.txt')]
        out_list = ['588', '2759', '4035', '1930 UB', '1989 AL2']
        self.assertEqual(out_list, fetch_list_targets(test_file))

    def test_file_and_command_entry(self):
        test_file = [os.path.join('astrometrics', 'tests', 'test_target_list_page.txt'), '4063']
        out_list = ['588', '2759', '4035', '1930 UB', '1989 AL2', '4063']
        self.assertEqual(out_list, fetch_list_targets(test_file))


class TestFetchFluxStandards(TestCase):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        self.test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.maxDiff = None
        self.precision = 10

    def test_badpage(self):
        expected_standards = {}

        standards = fetch_flux_standards('wibble')

        self.assertEqual(expected_standards, standards)

    def test_standards_no_filter(self):
        expected_standards = { 'HR9087'   : { 'ra_rad' : radians(0.030394444444444444*15.0), 'dec_rad' : radians(-3.0275), 'mag' : 5.12, 'spec_type' : 'B7III', 'notes' : None},
                               'CD-34d241': { 'ra_rad' : radians(10.4455), 'dec_rad' : radians(-33.652361111111111), 'mag' : 11.23, 'spec_type' : 'F', 'notes' : None},
                               'BPM16274' : { 'ra_rad' : radians(12.51325), 'dec_rad' : radians(-52.138166666666667), 'mag' : 14.20, 'spec_type' : 'DA2', 'notes' : 'Mod.'},
                               'LTT2415'  : { 'ra_rad' : radians(89.10125), 'dec_rad' : radians(-27.858), 'mag' : 12.21, 'spec_type' : None, 'notes' : None},
                             }

        standards = fetch_flux_standards(self.test_flux_page, filter_optical_model=False)

        self.assertEqual(len(expected_standards), len(standards))
        for fluxstd in expected_standards:
            for key in expected_standards[fluxstd]:
                if '_rad' in key:
                    self.assertAlmostEqual(expected_standards[fluxstd][key], standards[fluxstd][key], places=self.precision)
                else:
                    self.assertEqual(expected_standards[fluxstd][key], standards[fluxstd][key])

    def test_standards_filter_models(self):
        expected_standards = { 'HR9087'   : { 'ra_rad' : radians(0.030394444444444444*15.0), 'dec_rad' : radians(-3.0275), 'mag' : 5.12, 'spec_type' : 'B7III', 'notes' : None},
                               'CD-34d241': { 'ra_rad' : radians(10.4455), 'dec_rad' : radians(-33.652361111111111), 'mag' : 11.23, 'spec_type' : 'F', 'notes' : None},
                               'LTT2415'  : { 'ra_rad' : radians(89.10125), 'dec_rad' : radians(-27.858), 'mag' : 12.21, 'spec_type' : None, 'notes' : None},
                             }

        standards = fetch_flux_standards(self.test_flux_page, filter_optical_model=True)

        self.assertEqual(len(expected_standards), len(standards))
        for fluxstd in expected_standards:
            for key in expected_standards[fluxstd]:
                if '_rad' in key:
                    self.assertAlmostEqual(expected_standards[fluxstd][key], standards[fluxstd][key], places=self.precision)
                else:
                    self.assertEqual(expected_standards[fluxstd][key], standards[fluxstd][key])
