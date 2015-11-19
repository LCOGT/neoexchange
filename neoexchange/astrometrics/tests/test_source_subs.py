'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from django.test import TestCase
from django.forms.models import model_to_dict
from core.models import Body
from datetime import datetime, timedelta
from unittest import skipIf
from bs4 import BeautifulSoup
import os

from astrometrics.ephem_subs import determine_darkness_times
#Import module to test
from astrometrics.sources_subs import parse_goldstone_chunks, \
    submit_block_to_scheduler, parse_previous_NEOCP_id, parse_NEOCP, \
    parse_NEOCP_extra_params, parse_PCCP, parse_mpcorbit, parse_mpcobs, \
    fetch_NEOCP_observations


class TestGoldstoneChunkParser(TestCase):
    '''Unit tests for the sources_subs.parse_goldstone_chunks() method'''

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
        expected_objid = '1566' # '(1566) Icarus'
        chunks = [u'2015', u'Jun', u'13-17', u'1566', u'Icarus', u'No', u'Yes', u'R', u'PHA', u'June', u'13/14,', u'14/15,', u'and', u'16/17']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_unspecficdate_named_ast(self):
        expected_objid = '1685' # '(1685) Toro'
        chunks = ['2016', 'Jan', '1685', 'Toro', 'No', 'No', 'R']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

    def test_multimonth_split(self):
        expected_objid = '410777' # '(410777) 2009 FD'
        chunks = [u'2015', u'Oct', u'25-Nov', u'1', u'410777', u'2009', u'FD', u'No', u'Yes', u'R']
        obj_id = parse_goldstone_chunks(chunks)
        self.assertEqual(expected_objid, obj_id)

class TestSubmitBlockToScheduler(TestCase):

    def setUp(self):
        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : datetime(2015,03,19,00,00,00),
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

    @skipIf(True, "needs mocking, submits to real scheduler")
    def test_submit_body_for_cpt(self):

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'K92'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {  'proposal_code' : 'LCO2015A-009',
                    'exp_count' : 18,
                    'exp_time' : 50.0,
                    'site_code' : site_code,
                    'start_time' : dark_start,
                    'end_time' : dark_end,
                    'group_id' : body_elements['current_name'] + '_' + 'CPT' + '-'  + datetime.strftime(utc_date, '%Y%m%d')

                 }

        request_number = submit_block_to_scheduler(body_elements, params)

class TestPreviousNEOCPParser(TestCase):
    '''Unit tests for the sources_subs.parse_previous_NEOCP_id() method'''

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

    def test_non_neo(self):

        items = [u' 2015 QF', BeautifulSoup('<sub>   </sub>').sub, u' = WQ39346(Aug. 19.79 UT)\n']
        expected = [u'WQ39346', '2015 QF', '', u'(Aug. 19.79 UT)']
        
        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)
        

    def test_neo(self):

        items = [u' 2015 PK', BeautifulSoup('<sub>229</sub>').sub, u' = P10n00U (Aug. 17.98 UT)  [see ', BeautifulSoup('<a href="/mpec/K15/K15Q10.html"><i>MPEC</i> 2015-Q10</a>').a, u']\n']
        expected = [u'P10n00U', u'2015 PK229', u'MPEC 2015-Q10', u'(Aug. 17.98 UT)']
        
        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_good_comet(self):

        items = [u' Comet C/2015 Q1 = SW40sQ (Aug. 19.49 UT)  [see ',
            BeautifulSoup('<a href="http://www.cbat.eps.harvard.edu/iauc/20100/2015-.html"><i>IAUC</i> 2015-</a>').a,
            u']\n']
        expected = [u'SW40sQ', u'C/2015 Q1', u'IAUC 2015-', u'(Aug. 19.49 UT)']
        
        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_good_comet_cbet(self):

        items = [u' Comet C/2015 O1 = P10ms6N(July 21.99 UT)  [see ',
            BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>').a,
            u']\n']

        expected = [u'P10ms6N', u'C/2015 O1', u'CBET 4119', u'(July 21.99 UT)']
        
        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_bad_comet(self):

        items = [u' Comet C/2015 P3 = MAT01  (Aug. 11.23 UT)  [see ',
            BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004136.txt"><i>CBET</i> 4136</a>').a,
             u']\n']
        expected = [u'MAT01', u'C/2015 P3', u'CBET 4136', u'(Aug. 11.23 UT)']
        
        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_bad_comet2(self):

        items = [u' Comet 2015 TQ209 = LM02L2J(Oct. 24.07 UT)  [see ', 
            BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/iauc/20100/2015-.html"><i>IAUC</i> 2015-</a>').a,
             u']\n']
        expected = [u'LM02L2J', u'C/2015 TQ209', u'IAUC 2015-', u'(Oct. 24.07 UT)']
        
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
#                            u'WR0159E',
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

        obj_ids = parse_NEOCP(BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>'))

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

        obj_ids = parse_NEOCP_extra_params(BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>'))

        self.assertEqual(obj_ids, None)

    def test_parse_neocpep_good_entry(self):
        html = BeautifulSoup(self.table_header + \
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
        ''' + self.table_footer)

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = (u'CAH024', {'score' : 99,
                                        'discovery_date' : datetime(2015,9,20),
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
        '''Test of 'Moved to the PCCP' entries'''

        html = BeautifulSoup(self.table_header + \
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
        ''' + self.table_footer)

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
        html = BeautifulSoup(self.table_header + \
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
        ''' + self.table_footer)

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = (u'P10o4Gp', {'score' : 88,
                                        'discovery_date' : datetime(2015,9,23,9,36),
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
        html = BeautifulSoup(self.table_header + \
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
        ''' + self.table_footer)

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = (u'P10nw2g', {'score' : 100,
                                        'discovery_date' : datetime(2015,9,6,7,12,00),
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
        html = BeautifulSoup(self.table_header + \
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
        ''' + self.table_footer)

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = [(u'P10nI6D', {'score' : 60,
                                        'discovery_date' : datetime(2015,9,9,7,12,00),
                                        'num_obs' : 6,
                                        'arc_length' : 1.84,
                                        'not_seen' : 13.761,
                                        'update_time': datetime(2015, 9, 11, 15, 24, 44),
                                        'updated' : True
                                }),
                           (u'P10nw2g', {'score' : 100,
                                        'discovery_date' : datetime(2015,9,6,7,12,00),
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
            obj+=1

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

        obj_ids = parse_PCCP(BeautifulSoup(' <a href="http://www.cbat.eps.harvard.edu/cbet/004100/CBET004119.txt"><i>CBET</i> 4119</a>'))

        self.assertEqual(obj_ids, None)

    def test_parse_pccp_entry(self):

        html = BeautifulSoup(self.table_header + \
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
        ''' + self.table_footer)

        obj_ids = parse_PCCP(html)
        expected_obj_ids = [(u'WR0159E', {'score' : 10,
                                        'discovery_date' : datetime(2015, 9, 13, 9, 36),
                                        'num_obs' : 222,
                                        'arc_length' : 15.44,
                                        'not_seen' : 0.726,
                                        'update_time': datetime(2015, 9, 28, 17, 48, 10),
                                        'updated' : True
                                       }
                            ),]
        self.assertNotEqual(None, obj_ids)
        obj = 0
        while obj < len(expected_obj_ids):
            self.assertEqual(expected_obj_ids[obj][0], obj_ids[obj][0])
            self.assertEqual(expected_obj_ids[obj][1], obj_ids[obj][1])
            obj+=1

    def test_parse_pccp_multientries(self):

        html = BeautifulSoup(self.table_header + \
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
        ''' + self.table_footer)

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
            obj+=1

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
                             'V w.r.t. Earth': '6.0',
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
        
class TestParseMPCObsFormat(TestCase):

    def setUp(self):
        '''The "code" for the dictionary keys for the test lines is as follows:
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
        <char4> is the precision of the obs:
            l: low precision
            h: high precision
            n: no magnitude
        '''
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
                            'astrometric_catalog' : 'UCAC2-beta',
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
                            'astrometric_catalog' : 'UCAC2-beta',
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
                            'astrometric_catalog' : 'UCAC2-beta',
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
        expected_params = {}

        params = parse_mpcobs(self.test_lines['p_ S_l'])

        self.compare_dict(expected_params, params)
        
    def test_p_spaces_l(self):
        expected_params = {}

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
                            'obs_date'  : datetime(2002, 07, 31, 13, 9, 33, int(0.984*1e6)),
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
                            'astrometric_catalog' : 'UCAC2-beta',
                            'site_code' : 'G96'
                          }

        params = parse_mpcobs(self.test_lines['p_ C_n'])

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
                            'astrometric_catalog' : 'UCAC2-beta',
                            'site_code' : 'G96'
                          }

        params = parse_mpcobs(self.test_lines['p_ C_f'])

        self.compare_dict(expected_params, params)

class TestFetchNEOCPObservations(TestCase):

    def setUp(self):

        self.maxDiff = None

    def test_removed_object(self):
        page = BeautifulSoup('<html><body><pre>\nNone available at this time.\n</pre></body></html>')
        expected = None

        observations = fetch_NEOCP_observations(page)
        self.assertEqual(expected, observations)

    def test_readlines(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_P10pqB2.dat'), 'r')
        obs_data = test_fh.read()
        test_fh.close()
        page = BeautifulSoup(obs_data)

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
      
