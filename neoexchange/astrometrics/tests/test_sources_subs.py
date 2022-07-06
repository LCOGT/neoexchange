"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

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
from mock import patch, MagicMock
from freezegun import freeze_time
from socket import error, timeout
from errno import ETIMEDOUT
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from unittest import skipIf
from math import radians, ceil
from copy import deepcopy

import astropy.units as u
from bs4 import BeautifulSoup
from django.test import TestCase, SimpleTestCase
from django.forms.models import model_to_dict

from core.models import Body, Proposal, Block, StaticSource, PhysicalParameters, Designations, ColorValues
from astrometrics.ephem_subs import determine_darkness_times
from astrometrics.time_subs import datetime2mjd_utc
from neox.tests.mocks import MockDateTime, mock_expand_cadence, mock_expand_cadence_novis, \
    mock_fetchpage_and_make_soup, mock_fetchpage_and_make_soup_pccp
from core.views import record_block, create_calib_sources, compute_vmag_pa
# Import module to test
from astrometrics.sources_subs import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)


class TestPackedToNormal(TestCase):

    def test_too_short_6(self):

        self.assertRaises(PackedError, packed_to_normal, 'K19E00')

    def test_too_long_8(self):

        self.assertRaises(PackedError, packed_to_normal, 'K19E0042')

    def test_bad_halfmonth_lc(self):

        self.assertRaises(PackedError, packed_to_normal, 'J99a01A')

    def test_bad_halfmonth_I(self):

        self.assertRaises(PackedError, packed_to_normal, 'J99I01I')

    def test_bad_halfmonth_Z(self):

        self.assertRaises(PackedError, packed_to_normal, 'J99Z01Z')

    def test_bad_halfmonth_order_lc(self):

        self.assertRaises(PackedError, packed_to_normal, 'J99A01a')

    def test_bad_halfmonth_order_space(self):

        self.assertRaises(PackedError, packed_to_normal, 'J99A01 ')

    def test_bad_halfmonth_Zorder_dash(self):

        self.assertRaises(PackedError, packed_to_normal, 'J99A01-')

    def test_bad_year(self):

        self.assertRaises(PackedError, packed_to_normal, 'JabA01A')

    def test_bad_chars(self):

        self.assertRaises(PackedError, packed_to_normal, 'abcde')

    def test_ast_00001(self):
        expected = '1'

        result = packed_to_normal('00001')

        self.assertEqual(expected, result)

    def test_ast_00433(self):
        expected = '433'

        result = packed_to_normal('00433')

        self.assertEqual(expected, result)

    def test_ast_06478(self):
        expected = '6478'

        result = packed_to_normal('06478')

        self.assertEqual(expected, result)

    def test_ast_99942(self):
        expected = '99942'

        result = packed_to_normal('99942')

        self.assertEqual(expected, result)

    def test_ast_A0001(self):
        expected = '100001'

        result = packed_to_normal('A0001')

        self.assertEqual(expected, result)

    def test_ast_Z4030(self):
        expected = '354030'

        result = packed_to_normal('Z4030')

        self.assertEqual(expected, result)

    def test_ast_a0001(self):
        expected = '360001'

        result = packed_to_normal('a0001')

        self.assertEqual(expected, result)

    def test_ast_I99A01A(self):
        expected = '1899 AA1'

        result = packed_to_normal('I99A01A')

        self.assertEqual(expected, result)

    def test_ast_J23P00F(self):
        expected = '1923 PF'

        result = packed_to_normal('J23P00F')

        self.assertEqual(expected, result)

    def test_ast_K03P00F(self):
        expected = '2003 PF'

        result = packed_to_normal('K03P00F')

        self.assertEqual(expected, result)

    def test_com_PK05Y020(self):
        expected = 'P/2005 Y2'

        result = packed_to_normal('PK05Y020')

        self.assertEqual(expected, result)

    def test_com_PK16B14A(self):
        expected = 'P/2016 BA14'

        result = packed_to_normal('PK16B14A')

        self.assertEqual(expected, result)

    def test_com_PK11WB3G(self):
        expected = 'P/2011 WG113'

        result = packed_to_normal('PK11WB3G')

        self.assertEqual(expected, result)

    def test_com_CJ83J010(self):
        expected = 'C/1983 J1'

        result = packed_to_normal('CJ83J010')

        self.assertEqual(expected, result)

    def test_com_PK13R03b(self):
        expected = 'P/2013 R3-B'

        result = packed_to_normal('PK13R03b')

        self.assertEqual(expected, result)


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

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_arecibo_page_v3.html'), 'r')
        self.test_arecibo_page_v3 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_arecibo_page_v4.html'), 'r')
        self.test_arecibo_page_v4 = BeautifulSoup(test_fh, "html.parser")
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

    def test_targets_v3(self):
        expected_targets = [ u'2016 AZ8',
                             u'433',
                             u'2013 CW32',
                             u'455176',
                             u'2015 EG',
                             u'88254',
                             u'2019 AV2',
                             u'2019 AP11',
                             u'2019 BJ1',
                             u'2019 BW1',
                             u'2019 BH1',
                             u'2019 BF1',
                             u'2018 VX8']

        targets = fetch_arecibo_targets(self.test_arecibo_page_v3)

        self.assertEqual(expected_targets, targets)

    def test_targets_v4(self):
        # Includes Comet target [Issue #387]
        expected_targets = [ u'289P',
                             u'137924',
                             u'250577',
                             u'163379',
                             u'35107',
                             u'2017 BM123',
                             u'2015 BK509',
                             u'4581',
                             u'2013 BA74',
                             u'2003 OC3',
                             u'2019 UO9']

        targets = fetch_arecibo_targets(self.test_arecibo_page_v4)

        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_page_down(self):
        expected_targets = []
        targets = fetch_arecibo_targets()
        self.assertEqual(expected_targets, targets)


class TestFetchGoldstoneCSV(SimpleTestCase):

    def setUp(self):
        self.test_file = os.path.join('astrometrics', 'tests', 'test_goldstone_page.csv')

    def test_basic(self):
        expected_length = 9
        expected_columns = ['number', 'name', 'start (UT)', 'end (UT)', 'OCC', 'Updated 2021 Dec 17']

        table = fetch_goldstone_csv(self.test_file)

        self.assertEqual(expected_length, len(table))
        self.assertEqual(expected_columns, table.colnames)

    def test_missing_file(self):
        expected_length = None

        table = fetch_goldstone_csv('/foo/bar')

        self.assertEqual(expected_length, table)

    def test_missing_url(self):
        expected_length = None

        table = fetch_goldstone_csv('https://foo.bar.com/nothere.csv')

        self.assertEqual(expected_length, table)


class TestFetchGoldstoneTargets(SimpleTestCase):

    def setUp(self):
        # Read and make soup from the stored version of the Goldstone radar pages
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_goldstone_page.html'), 'r')
        self.test_goldstone_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_goldstone_page_v2.html'), 'r')
        self.test_goldstone_page_v2 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.test_csv_file = os.path.join('astrometrics', 'tests', 'test_goldstone_page.csv')

        self.maxDiff = None

    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_basics(self):
        MockDateTime.change_datetime(2018, 4, 6, 2, 0, 0)
        expected_length = 49

        targets = fetch_goldstone_targets(self.test_goldstone_page)

        self.assertEqual(expected_length, len(targets))

    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_targets(self):
        MockDateTime.change_datetime(2018, 4, 6, 2, 0, 0)
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

    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_targets_with_extra(self):
        MockDateTime.change_datetime(2019, 4, 8, 2, 0, 0)
        expected_targets = [ '163081',
                             '522684',
                             '2008 HS3',
                             '2018 VX8',
                             '68950',
                             '66391',
                             '2011 HP',
                             '441987',
                             '494999',
                             '10145',
                             '293054',
                             '2010 PK9',
                             '2005 CL7',
                             '454094',
                             '153814',
                             '141593',
                             '66146',
                             '1620',
                             '237805',
                             '467317',
                             '2100',
                             '297418',
                             '2010 CO1',
                             '1998 FF14',
                             '162082',
                             '2015 JD1',
                             '2010 JG',
                             '481394',
                             '2011 YS62',
                             '2011 WN15',
                             '264357',
                             '216258']

        targets = fetch_goldstone_targets(self.test_goldstone_page_v2)

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

    @freeze_time(datetime(2021, 12, 7, 2, 0, 0))
    def test_csv_file_2021(self):

        expected_targets = ['163899', '4660', '2021 XK6']

        targets = fetch_goldstone_targets(self.test_csv_file)

        self.assertEqual(3, len(targets))
        self.assertEqual(expected_targets, targets)

    @freeze_time(datetime(2022, 1, 7, 2, 0, 0))
    def test_csv_file_2022(self):

        expected_targets = ['7842', '153591', '2016 QJ44', '2018 CW2', '2010 XC15']

        targets = fetch_goldstone_targets(self.test_csv_file)

        self.assertEqual(5, len(targets))
        self.assertEqual(expected_targets, targets)

    @freeze_time(datetime(2021, 12, 7, 2, 0, 0))
    def test_csv_file_calformat_2021(self):

        expected_targets = ['163899', '4660', '2021 XK6']

        expected_targets = [{ 'target': '163899',
                              'windows': [{'start': '2021-11-22T00:00:00', 'end': '2021-12-31T23:59:59'}]},
                             {'target': '4660',
                              'windows': [{'start': '2021-12-05T00:00:00', 'end': '2021-12-31T23:59:59'}]},
                             {'target': '2021 XK6',
                              'windows': [{'start': '2021-12-17T00:00:00', 'end': '2021-12-17T23:59:59'}]},
                              ]


        targets = fetch_goldstone_targets(self.test_csv_file, calendar_format=True)

        self.assertEqual(3, len(targets))
        self.assertEqual(expected_targets, targets)

    @freeze_time(datetime(2022, 1, 7, 2, 0, 0))
    def test_csv_file_calformat_2022(self):

        expected_targets = ['7842', '153591', '2016 QJ44', '2018 CW2', '2010 XC15']

        expected_targets = [
                             {'target': '7842',
                              'windows': [{'start': '2022-01-18T00:00:00', 'end': '2022-01-25T23:59:59'}]},
                             {'target': '153591',
                              'windows': [{'start': '2022-02-18T00:00:00', 'end': '2022-03-08T23:59:59'}]},
                             {'target': '2016 QJ44',
                              'windows': [{'start': '2022-02-18T00:00:00', 'end': '2022-02-25T23:59:59'}]},
                             {'target': '2018 CW2',
                              'windows': [{'start': '2022-02-16T00:00:00', 'end': '2022-02-21T23:59:59'}]},
                             {'target': '2010 XC15',
                              'windows': [{'start': '2022-12-24T00:00:00', 'end': '2023-01-06T23:59:59'}]},
                              ]


        targets = fetch_goldstone_targets(self.test_csv_file, calendar_format=True)

        self.assertEqual(len(expected_targets), len(targets))
        self.assertEqual(expected_targets, targets)


class TestFetchYarkovskyTargets(SimpleTestCase):

    def setUp(self):
        self.test_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_yarkovsky_targets.txt'))

    def test_read_from_file(self):
        expected_targets = [ '1999 NW2',
                             '2015 BG4',
                             '2009 SY',
                             '455184',
                             '1998 VS',
                             '2002 JW15']

        targets = [  '1999 NW2\n',
                     '2015 BG4\n',
                     '2009 SY\n',
                     '455184\n',
                     '1998 VS\n',
                     '2002 JW15\n']

        target_list = fetch_yarkovsky_targets(targets)

        self.assertEqual(expected_targets, target_list)

    def test_read_from_commandline(self):
        expected_targets = [ '433',
                             '1999 NW2',
                             '2015 BG4',
                             '455184',
                             '2002 JW15']

        targets = [  '433',
                     '1999_NW2',
                     '2015_BG4',
                     '455184',
                     '2002_JW15']

        target_list = fetch_yarkovsky_targets(targets)

        self.assertEqual(expected_targets, target_list)

    def test_fetch_from_ftp(self):
        expected_targets = [ '433',
                             '467352',
                             '2002 TS69',
                             '401856',
                             '2011 JY1',
                             '1998 WB2',
                             '2015 KJ19',
                             '2003 MK4',
                             '2003 GQ22']


        targets = fetch_yarkovsky_targets(self.test_file)

        self.assertEqual(expected_targets, targets)


class TestFetchYarkovskyTargetsFTP(SimpleTestCase):

    def setUp(self):
        self.test_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_yarkovsky_targets.txt'))

    def test_fetch_latest(self):
        expected_targets = [ '433',
                             '467352',
                             '2002 TS69',
                             '401856',
                             '2011 JY1',
                             '1998 WB2',
                             '2015 KJ19',
                             '2003 MK4',
                             '2003 GQ22']


        targets = fetch_yarkovsky_targets_ftp(self.test_file)

        self.assertEqual(expected_targets, targets)


class TestSubmitBlockToScheduler(TestCase):
    """Also tests make_requestgroup()"""

    def setUp(self):
        b_params = {'provisional_name' : 'N999r0q',
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
        self.body, created = Body.objects.get_or_create(**b_params)
        self.body_elements = model_to_dict(self.body)
        self.body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        self.body_elements['current_name'] = self.body.current_name()
        self.body_elements['v_mag'] = 16.6777676

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        ssource_params = {  'name' : 'SA107-684',
                            'ra' : 234.3,
                            'dec' : -0.16,
                            'vmag' : 7.0,
                            'source_type' : StaticSource.SOLAR_STANDARD
                        }
        self.ssource = StaticSource.objects.create(**ssource_params)

        site_code = 'K92'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        self.obs_params = {'proposal_id': 'LCO2015A-009',
                           'exp_count': 18,
                           'exp_time': 50.0,
                           'slot_length': 30 * 60,
                           'site_code': site_code,
                           'start_time': dark_start,
                           'end_time': dark_end,
                           'filter_pattern': 'w',
                           'group_name': self.body_elements['current_name'] + '_' + 'CPT' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                           'user_id': 'bsimpson',
                           'dither_distance': 10,
                           'add_dither': False,
                           'fractional_rate': 0.5,
                           'speed': 20,
                           }

        self.maxDiff = None

    @patch('astrometrics.sources_subs.requests.post')
    def test_submit_body_for_cpt(self, mock_post):
        mock_post.return_value.status_code = 200

        mock_post.return_value.json.return_value = {'id': '999', 'requests': [{'id': '111', 'target': {'type': 'NON-SIDEREAL'}, 'duration': 1820}]}

        params = self.obs_params

        resp, sched_params = submit_block_to_scheduler(self.body_elements, params)
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

    @patch('astrometrics.sources_subs.requests.post')
    def test_submit_body_for_cpt_V3(self, mock_post):
        mock_post.return_value.status_code = 200

        mock_post.return_value.json.return_value = {'id': 999,
                                                    'requests': [
                                                        {'id': 111,
                                                         'configurations': [{'id': 222,
                                                                             'target': {'type': 'ORBITAL-ELEMENTS'}
                                                                             }],
                                                         'duration': 1820}
                                                    ]}

        params = self.obs_params

        resp, sched_params = submit_block_to_scheduler(self.body_elements, params)
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
            self.assertEqual(block.request_number, '111')
            self.assertEqual(block.obstype, Block.OPT_IMAGING)
            self.assertEqual(block.num_exposures, params['exp_count'])
            self.assertEqual(block.exp_length, params['exp_time'])

    @patch('astrometrics.sources_subs.expand_cadence', mock_expand_cadence)
    @patch('astrometrics.sources_subs.requests.post')
    def test_submit_cadence(self, mock_post):
        mock_post.return_value.status_code = 200

        mock_post.return_value.json.return_value = {'id': '999', 'requests': [{'id': '111', 'target': {'type': 'NON-SIDEREAL'}, 'duration': 1820},
                                                                              {'id': '222', 'target': {'type': 'NON-SIDEREAL'}, 'duration': 1820},
                                                                              {'id': '333', 'target': {'type': 'NON-SIDEREAL'}, 'duration': 1820}]}

        site_code = 'V38'
        utc_date = datetime(2015, 3, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['period'] = 2.0
        params['jitter'] = 0.25

        tracking_num, sched_params = submit_block_to_scheduler(self.body_elements, params)

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

    @patch('astrometrics.sources_subs.expand_cadence', mock_expand_cadence_novis)
    @patch('astrometrics.sources_subs.requests.post')
    def test_submit_cadence_novis(self, mock_post):
        """Test for issue of 2021-01-26 where jitter=12hr i.e. +/-6hr, start of
        the period was at 2021-01-27 00:00 and visibility started at 08:00 so no
        valid windows were available"""

        mock_post.return_value.status_code = 400

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        params = self.obs_params
        params['start_time'] = datetime(2021,1,27,0,0,0)
        params['end_time'] = datetime(2021,1,31,23,59,59)
        params['period'] = 24.0
        params['jitter'] = 12.0

        resp, sched_params = submit_block_to_scheduler(body_elements, params)
        self.assertEqual(resp, False)
        self.assertEqual(sched_params['error_msg'], 'No visible requests within cadence window parameters')

    @patch('astrometrics.sources_subs.requests.post')
    def test_submit_spectra_for_ogg(self, mock_post):
        mock_post.return_value.status_code = 200

        mock_post.return_value.json.return_value = {'id': '999', 'requests': [{'id': '111', 'duration': 1820, 'target': {'type': 'ORBITAL_ELEMENTS'}}]}

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'F65'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {'proposal_id': 'LCO2015A-009',
                  'exp_count': 18,
                  'exp_time': 50.0,
                  'slot_length': 30,
                  'site_code': site_code,
                  'start_time': dark_start,
                  'end_time': dark_end,
                  'filter_pattern': 'slit_6.0as',
                  'group_name': body_elements['current_name'] + '_' + 'ogg' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                  'user_id': 'bsimpson',
                  'spectroscopy': True,
                  'spectra_slit': 'slit_6.0as',
                  'fractional_rate': 1
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

    @patch('astrometrics.sources_subs.requests.post')
    def test_submit_spectra_for_ogg_V3(self, mock_post):
        mock_post.return_value.status_code = 201

        mock_post.return_value.json.return_value = {'id': 999, 'requests': [
            {'id': 111, 'duration': 2485,
             'configurations': [
                 {'id': 2635701,
                  'constraints': {'max_airmass': 1.74},
                  'instrument_configs': [{'optical_elements': {'slit': 'slit_6.0as'}, 'rotator_mode': 'VFLOAT'}],
                  'target': {'type': 'ORBITAL_ELEMENTS', 'name': '11500'},
                  'type': 'SPECTRUM'},
                 {'id': 2635704,
                  'constraints': {'max_airmass': 1.74},
                  'instrument_configs': [{'optical_elements': {'slit': 'slit_6.0as'}, 'rotator_mode': 'VFLOAT'}],
                  'target': {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3, 'dec': -0.16},
                  'type': 'SPECTRUM'}]
             }, ]}

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'F65'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {'proposal_id': 'LCO2015A-009',
                  'exp_count': 1,
                  'exp_time': 150.0,
                  'slot_length': 30,
                  'site_code': site_code,
                  'start_time': dark_start,
                  'end_time': dark_end,
                  'filter_pattern': 'slit_6.0as',
                  'group_name': body_elements['current_name'] + '_' + 'ogg' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                  'user_id': 'bsimpson',
                  'solar_analog': True,
                  'calibsource': {'id': 1, 'name': 'SA107-684', 'ra_deg': 234.3, 'dec_deg': -0.16, 'calib_exptime': 60},
                  'calibsrc_exptime': 60,
                  'spectroscopy': True,
                  'spectra_slit': 'slit_6.0as',
                  'fractional_rate': 1
                  }

        resp, sched_params = submit_block_to_scheduler(body_elements, params)
        self.assertEqual(resp, '999')

        # store block
        data = params
        data['proposal_code'] = 'LCO2015A-009'
        data['exp_length'] = params['exp_time']
        block_resp = record_block(resp, sched_params, data, self.body)
        self.assertEqual(block_resp, True)

        # Test that block has same start/end as superblock
        blocks = Block.objects.filter(active=True)
        self.assertEqual(2, blocks.count())
        for block in blocks:
            self.assertEqual(block.block_start, block.superblock.block_start)
            self.assertEqual(block.block_end, block.superblock.block_end)
        self.assertEqual(blocks[0].obstype, Block.OPT_SPECTRA)
        self.assertEqual(blocks[0].exp_length, params['exp_time'])
        self.assertEqual(blocks[0].calibsource, None)
        self.assertNotEqual(blocks[0].body, None)
        self.assertEqual(blocks[1].obstype, Block.OPT_SPECTRA_CALIB)
        self.assertEqual(blocks[1].exp_length, params['calibsrc_exptime'])
        self.assertEqual(blocks[1].body, None)
        self.assertNotEqual(blocks[1].calibsource, None)
        self.assertEqual(blocks[1].calibsource.name, params['calibsource']['name'])

    def test_make_requestgroup(self):

        site_code = 'K92'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end

        user_request = make_requestgroup(self.body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['windows'][0]['start'], dark_start.strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual(user_request['requests'][0]['location'].get('telescope', None), None)

    def test_make_generic_requestgroup(self):

        site_code = '2M0'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code

        user_request = make_requestgroup(self.body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['windows'][0]['start'], dark_start.strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual(user_request['requests'][0]['windows'][0]['end'], dark_end.strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual(dark_start + timedelta(days=1), dark_end)
        self.assertEqual(user_request['requests'][0]['location'].get('telescope', None), None)
        self.assertEqual(user_request['requests'][0]['location'].get('site', None), None)
        self.assertEqual(user_request['requests'][0]['location']['telescope_class'], '2m0')

    def test_make_spectra_requestgroup(self):
        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'F65'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {'proposal_id': 'LCO2015A-009',
                  'exp_count': 18,
                  'exp_time': 50.0,
                  'site_code': site_code,
                  'start_time': dark_start,
                  'end_time': dark_end,
                  'filter_pattern': 'slit_6.0as',
                  'group_name': body_elements['current_name'] + '_' + 'OGG' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                  'user_id': 'bsimpson',
                  'spectroscopy': True,
                  'spectra_slit': 'slit_6.0as',
                  'para_angle': False
                  }

        body_elements = compute_vmag_pa(body_elements, params)
        user_request = make_requestgroup(body_elements, params)
        self.assertAlmostEqual(user_request['requests'][0]['configurations'][0]['target']['extra_params']['v_magnitude'], 20.88, 2)
        self.assertAlmostEqual(user_request['requests'][0]['configurations'][0]['instrument_configs'][0]['extra_params']['rotator_angle'], 107.53, 1)
        self.assertEqual(user_request['requests'][0]['configurations'][0]['instrument_configs'][0]['rotator_mode'], 'SKY')

    def test_make_spectra_requestgroup_with_wrong_rate(self):
        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'F65'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = {'proposal_id': 'LCO2015A-009',
                  'exp_count': 18,
                  'exp_time': 50.0,
                  'site_code': site_code,
                  'start_time': dark_start,
                  'end_time': dark_end,
                  'filter_pattern': 'slit_6.0as',
                  'group_name': body_elements['current_name'] + '_' + 'OGG' + '-' + datetime.strftime(utc_date, '%Y%m%d'),
                  'user_id': 'bsimpson',
                  'spectroscopy': True,
                  'spectra_slit': 'slit_6.0as',
                  'para_angle': False,
                  'fractional_rate': 0.5
                  }

        body_elements = compute_vmag_pa(body_elements, params)
        user_request = make_requestgroup(body_elements, params)
        self.assertAlmostEqual(user_request['requests'][0]['configurations'][0]['target']['extra_params']['v_magnitude'], 20.88, 2)
        self.assertAlmostEqual(user_request['requests'][0]['configurations'][0]['instrument_configs'][0]['extra_params']['rotator_angle'], 107.53, 1)
        self.assertEqual(user_request['requests'][0]['configurations'][0]['instrument_configs'][0]['rotator_mode'], 'SKY')
        self.assertEqual(user_request['requests'][0]['configurations'][0]['target']['extra_params']['fractional_ephemeris_rate'], 1)

    def test_1m_sinistro_lsc_doma_requestgroup(self):

        site_code = 'W85'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code

        user_request = make_requestgroup(self.body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['location']['telescope'], '1m0a')
        self.assertEqual(user_request['requests'][0]['location']['telescope_class'], '1m0')
        self.assertEqual(user_request['requests'][0]['location']['site'], 'lsc')

    def test_1m_sinistro_elp_domb_requestgroup(self):

        site_code = 'V39'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code

        user_request = make_requestgroup(self.body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['location']['telescope'], '1m0a')
        self.assertEqual(user_request['requests'][0]['location']['enclosure'], 'domb')
        self.assertEqual(user_request['requests'][0]['location']['telescope_class'], '1m0')
        self.assertEqual(user_request['requests'][0]['location']['site'], 'elp')

    def test_1m_sinistro_tfn_doma_requestgroup(self):

        site_code = 'Z31'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code

        user_request = make_requestgroup(self.body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['location']['telescope'], '1m0a')
        self.assertEqual(user_request['requests'][0]['location']['enclosure'], 'doma')
        self.assertEqual(user_request['requests'][0]['location']['telescope_class'], '1m0')
        self.assertEqual(user_request['requests'][0]['location']['site'], 'tfn')

    def test_1m_sinistro_tfn_generic_requestgroup(self):

        site_code = 'Z24'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code

        user_request = make_requestgroup(self.body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertTrue('telescope' not in user_request['requests'][0]['location'])
        self.assertTrue('enclosure' not in user_request['requests'][0]['location'])
        self.assertEqual(user_request['requests'][0]['location']['telescope_class'], '1m0')
        self.assertEqual(user_request['requests'][0]['location']['site'], 'tfn')

    def test_make_too_requestgroup(self):
        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        site_code = 'Q63'
        utc_date = datetime.now()+timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code
        params['too_mode'] = True

        user_request = make_requestgroup(body_elements, params)

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(user_request['requests'][0]['windows'][0]['start'], dark_start.strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual(user_request['requests'][0]['location'].get('telescope', None), None)
        self.assertEqual(user_request['requests'][0].get('observation_type', None), None)
        self.assertEqual(user_request['observation_type'], 'TIME_CRITICAL')

    def test_1m_binning_requestgroup(self):

        site_code = '1M0'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code
        params['bin_mode'] = '2k_2x2'

        user_request = make_requestgroup(self.body_elements, params)

        instrument_configs = user_request['requests'][0]['configurations'][0]['instrument_configs'][0]

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(instrument_configs['mode'], 'central_2k_2x2')
        self.assertEqual(user_request['requests'][0]['location'].get('telescope', None), None)

    def test_ELP_1m_binning_requestgroup(self):

        params = self.obs_params
        params['bin_mode'] = '2k_2x2'

        user_request = make_requestgroup(self.body_elements, params)

        instrument_configs = user_request['requests'][0]['configurations'][0]['instrument_configs'][0]

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertEqual(instrument_configs['mode'], 'central_2k_2x2')

    def test_1m_no_binning_requestgroup(self):

        params = self.obs_params
        params['bin_mode'] = 'full_chip'

        user_request = make_requestgroup(self.body_elements, params)

        instrument_configs = user_request['requests'][0]['configurations'][0]['instrument_configs'][0]

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertNotIn('mode', instrument_configs.keys())

    def test_2m_no_binning_requestgroup(self):

        site_code = '2M0'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code
        params['bin_mode'] = '2k_2x2'

        user_request = make_requestgroup(self.body_elements, params)

        instrument_configs = user_request['requests'][0]['configurations'][0]['instrument_configs'][0]

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertNotIn('mode', instrument_configs.keys())

    def test_0m4_no_binning_requestgroup(self):

        site_code = 'L09'
        utc_date = datetime(2015, 6, 19, 00, 00, 00) + timedelta(days=1)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        params = self.obs_params
        params['start_time'] = dark_start
        params['end_time'] = dark_end
        params['site_code'] = site_code
        params['bin_mode'] = '2k_2x2'

        user_request = make_requestgroup(self.body_elements, params)

        instrument_configs = user_request['requests'][0]['configurations'][0]['instrument_configs'][0]

        self.assertEqual(user_request['submitter'], 'bsimpson')
        self.assertNotIn('mode', instrument_configs.keys())

    def test_multi_filter_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V,V,R,R,I,I'
        params['exp_count'] = 75

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        inst_configs = configurations[0].get('instrument_configs')

        expected_configuration_num = 3
        expected_inst_config_num = 3
        expected_exp_count = 2
        expected_filter0 = 'I'
        expected_filter1 = 'V'
        expected_filter2 = 'R'

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(len(inst_configs), expected_inst_config_num)
        self.assertEqual(inst_configs[2]['exposure_count'], expected_exp_count)
        self.assertEqual(inst_configs[2]['optical_elements']['filter'], expected_filter0)
        self.assertEqual(configurations[1]['instrument_configs'][2]['optical_elements']['filter'], expected_filter1)
        self.assertEqual(configurations[2]['instrument_configs'][2]['optical_elements']['filter'], expected_filter2)

    def test_uneven_filter_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V,V,R,I'
        params['exp_count'] = 40

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        inst_configs = configurations[0].get('instrument_configs')

        expected_configuration_num = 2
        expected_inst_config_num = 3
        expected_exp_count = 1
        expected_filter = 'I'

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(len(inst_configs), expected_inst_config_num)
        self.assertEqual(inst_configs[0]['exposure_count'], 2)
        self.assertEqual(inst_configs[0]['optical_elements']['filter'], 'V')
        self.assertEqual(inst_configs[2]['exposure_count'], expected_exp_count)
        self.assertEqual(inst_configs[2]['optical_elements']['filter'], expected_filter)

    def test_single_filter_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V'

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        expected_configuration_num = 1
        expected_exp_count = 1
        expected_filter = 'V'

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(configurations[0]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(configurations[0]['instrument_configs'][0]['optical_elements']['filter'], expected_filter)

    def test_overlap_filter_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V,V,R,I,V'
        params['exp_count'] = 9

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        inst_configs = configurations[0].get('instrument_configs')

        expected_configuration_num = 1
        expected_inst_config_num = 6
        expected_exp_count = 3
        expected_filter = 'V'

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(len(inst_configs), expected_inst_config_num)
        self.assertEqual(inst_configs[3]['exposure_count'], expected_exp_count)
        self.assertEqual(inst_configs[3]['optical_elements']['filter'], expected_filter)

    def test_overlap_nooverlap_filter_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V,V,R,I,V'
        params['exp_count'] = 10

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        inst_configs = configurations[0].get('instrument_configs')

        expected_inst_config_num = 7
        expected_configuration_num = 1
        expected_exp_count = 1
        expected_filter = 'V'

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(len(inst_configs), expected_inst_config_num)
        self.assertEqual(inst_configs[6]['exposure_count'], expected_exp_count)
        self.assertEqual(inst_configs[6]['optical_elements']['filter'], expected_filter)

    def test_partial_filter_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V,V,V,V,V,V,R,R,R,R,R,I,I,I,I,I,I,B,B,B,B,B,B,B'
        params['exp_count'] = 15

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        inst_configs = configurations[0].get('instrument_configs')

        expected_inst_config_num = 3
        expected_configuration_num = 1
        expected_exp_count = 4
        expected_filter = 'I'

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(len(inst_configs), expected_inst_config_num)
        self.assertEqual(inst_configs[2]['exposure_count'], expected_exp_count)
        self.assertEqual(inst_configs[2]['optical_elements']['filter'], expected_filter)

    def test_partial_overlap_filter_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V,V,R,R,I,V'
        params['exp_count'] = 10

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        inst_configs = configurations[0].get('instrument_configs')

        expected_inst_config_num = 5
        expected_configuration_num = 1
        expected_exp_count = 3
        expected_filter = 'V'

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(len(inst_configs), expected_inst_config_num)
        self.assertEqual(inst_configs[3]['exposure_count'], expected_exp_count)
        self.assertEqual(inst_configs[3]['optical_elements']['filter'], expected_filter)

    def test_long_filterlist_largecount_requestgroup(self):

        params = self.obs_params
        params['filter_pattern'] = 'V,V,V,R,R,R,I,I,I'
        params['exp_count'] = 91

        user_request = make_requestgroup(self.body_elements, params)
        configurations = user_request.get('requests')[0].get('configurations')
        inst_configs = configurations[0].get('instrument_configs')

        expected_inst_config_num = 3
        expected_configuration_num = 3
        expected_exp_count = 3
        expected_filter0 = 'V'
        expected_filter1 = 'I'
        expected_filter2 = 'V'
        expected_repeat_duration = 577

        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(len(inst_configs), expected_inst_config_num)
        self.assertEqual(inst_configs[0]['exposure_count'], expected_exp_count)
        self.assertEqual(configurations[0]['instrument_configs'][0]['optical_elements']['filter'], expected_filter0)
        self.assertEqual(configurations[1]['instrument_configs'][0]['optical_elements']['filter'], expected_filter1)
        self.assertEqual(configurations[2]['instrument_configs'][0]['optical_elements']['filter'], expected_filter2)
        self.assertEqual(configurations[0]['repeat_duration'], expected_repeat_duration)

    @patch('astrometrics.sources_subs.expand_cadence', mock_expand_cadence_novis)
    @patch('astrometrics.sources_subs.requests.post')
    def test_semester_crossing(self, mock_post):
        """Test for issue of 2021-01-25 where cadence crossed semester boundary
        so no valid windows were available"""

        mock_post.return_value.status_code = 400

        body_elements = model_to_dict(self.body)
        body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        body_elements['current_name'] = self.body.current_name()
        params = self.obs_params
        params['start_time'] = datetime(2021, 1, 27, 0, 0, 0)
        params['end_time'] = datetime(2021, 2, 27, 23, 59, 59)
        params['period'] = 72.0
        params['jitter'] = 24.0

        resp, sched_params = submit_block_to_scheduler(body_elements, params)
        self.assertEqual(resp, False)
        expected_msg = {'windows': [{'non_field_errors': ['The observation window does not fit within any defined semester.']}]}
        self.assertEqual(sched_params['error_msg'], expected_msg)

    def test_spectro_with_solar_analog(self):

        utc_date = datetime(2018, 5, 11, 0)
        params = {'proposal_id': 'LCOEngineering',
                  'user_id': 'bsimpson',
                  'spectroscopy': True,
                  'calibs': 'before',
                  'exp_count': 1,
                  'exp_time': 300.0,
                  'instrument_code': 'F65-FLOYDS',
                  'site_code': 'F65',
                  'filter_pattern': 'slit_6.0as',
                  'group_name': self.body_elements['current_name'] + '_' + 'F65' + '-' + datetime.strftime(utc_date, '%Y%m%d') + "_spectra",
                  'start_time':  utc_date + timedelta(hours=5),
                  'end_time':  utc_date + timedelta(hours=15),
                  'solar_analog': True,
                  'calibsource': {'name': 'SA107-684', 'ra_deg': 234.3254167, 'dec_deg': -0.163889, 'calib_exptime': 60},
                  }
        expected_num_requests = 1
        expected_operator = 'SINGLE'
        expected_configuration_num = 6
        expected_exp_count = 1
        expected_ast_exptime = 300.0
        expected_cal_exptime = 60.0
        expected_filter = 'slit_6.0as'
        expected_groupid = params['group_name'] + '+solstd'
        expected_ast_target = {'name': 'N999r0q', 'type': 'ORBITAL_ELEMENTS', 'scheme': 'MPC_MINOR_PLANET',
                               'epochofel': 57100.0, 'orbinc': 8.34739, 'longascnode': 147.81325,
                               'argofperih': 85.19251, 'eccentricity': 0.1896865, 'extra_params': {'v_magnitude': 16.68, 'fractional_ephemeris_rate': 1},
                               'meandist': 1.2176312, 'meananom': 325.2636}
        expected_cal_target = {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3254167, 'dec': -0.163889, 'extra_params': {}}

        user_request = make_requestgroup(self.body_elements, params)
        requests = user_request['requests']
        self.assertEqual(expected_num_requests, len(requests))
        self.assertEqual(expected_operator, user_request['operator'])
        self.assertEqual(expected_groupid, user_request['name'])

        configurations = user_request['requests'][0]['configurations']
        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(configurations[2]['target'], expected_ast_target)
        self.assertEqual(configurations[2]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(configurations[2]['instrument_configs'][0]['exposure_time'], expected_ast_exptime)
        self.assertEqual(configurations[2]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)

        self.assertEqual(configurations[5]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(configurations[5]['target'], expected_cal_target)
        self.assertEqual(configurations[5]['instrument_configs'][0]['exposure_time'], expected_cal_exptime)
        self.assertEqual(configurations[5]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)

    def test_multiframe_spectro_with_solar_analog(self):

        utc_date = datetime(2018, 5, 11, 0)
        params = {'proposal_id': 'LCOEngineering',
                  'user_id': 'bsimpson',
                  'spectroscopy': True,
                  'calibs': 'before',
                  'exp_count': 10,
                  'exp_time': 30.0,
                  'instrument_code': 'F65-FLOYDS',
                  'site_code': 'F65',
                  'filter_pattern': 'slit_2.0as',
                  'group_name': self.body_elements['current_name'] + '_' + 'F65' + '-' + datetime.strftime(utc_date, '%Y%m%d') + "_spectra",
                  'start_time':  utc_date + timedelta(hours=5),
                  'end_time':  utc_date + timedelta(hours=15),
                  'solar_analog': True,
                  'calibsource': {'name': 'SA107-684', 'ra_deg': 234.3254167, 'dec_deg': -0.163889, 'calib_exptime': 60},
                  }
        expected_num_requests = 1
        expected_operator = 'SINGLE'
        expected_configuration_num = 6
        expected_exp_count = 10
        expected_ast_exptime = 30.0
        expected_cal_exptime = 60.0
        expected_cal_exp_count = 1
        expected_filter = 'slit_2.0as'
        expected_groupid = params['group_name'] + '+solstd'
        expected_ast_target = {'name': 'N999r0q', 'type': 'ORBITAL_ELEMENTS', 'scheme': 'MPC_MINOR_PLANET',
                               'epochofel': 57100.0, 'orbinc': 8.34739, 'longascnode': 147.81325,
                               'argofperih': 85.19251, 'eccentricity': 0.1896865, 'extra_params': {'v_magnitude': 16.68, 'fractional_ephemeris_rate': 1},
                               'meandist': 1.2176312, 'meananom': 325.2636}
        expected_cal_target = {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3254167, 'dec': -0.163889, 'extra_params': {}}

        user_request = make_requestgroup(self.body_elements, params)
        requests = user_request['requests']
        self.assertEqual(expected_num_requests, len(requests))
        self.assertEqual(expected_operator, user_request['operator'])
        self.assertEqual(expected_groupid, user_request['name'])

        configurations = user_request['requests'][0]['configurations']
        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(configurations[2]['target'], expected_ast_target)
        self.assertEqual(configurations[2]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(configurations[2]['instrument_configs'][0]['exposure_time'], expected_ast_exptime)
        self.assertEqual(configurations[2]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)

        self.assertEqual(configurations[5]['instrument_configs'][0]['exposure_count'], expected_cal_exp_count)
        self.assertEqual(configurations[5]['target'], expected_cal_target)
        self.assertEqual(configurations[5]['instrument_configs'][0]['exposure_time'], expected_cal_exptime)
        self.assertEqual(configurations[5]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)

    def test_solo_solar_spectrum(self):

        utc_date = datetime(2018, 5, 11, 0)
        params = {  'proposal_id' : 'LCOEngineering',
                    'user_id'  : 'bsimpson',
                    'spectroscopy' : True,
                    'calibs'     : 'before',
                    'exp_count'  : 1,
                    'exp_time'   : 300.0,
                    'instrument_code' : 'F65-FLOYDS',
                    'site_code' : 'F65',
                    'filter_pattern' : 'slit_6.0as',
                    'group_name' : 'SA107-684' + '_' + 'F65' + '-' + datetime.strftime(utc_date, '%Y%m%d') + "_spectra",
                    'start_time' :  utc_date + timedelta(hours=5),
                    'end_time'   :  utc_date + timedelta(hours=15),
                    'solar_analog' : False,
                    'ra_deg' : 234.3254167,
                    'dec_deg' : -0.163889,
                    'vmag' : 12.4,
                    'source_id' : 'SA107-684',
                    'source_type' : 4
                  }
        expected_num_requests = 1
        expected_operator = 'SINGLE'
        expected_configuration_num = 3
        expected_exp_count = 1
        expected_exptime = 300.0
        expected_filter = 'slit_6.0as'
        expected_groupid = params['group_name']
        expected_target = {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3254167, 'dec': -0.163889,
                                'extra_params': { 'v_magnitude' : 12.4} }

        user_request = make_requestgroup({}, params)
        requests = user_request['requests']
        self.assertEqual(expected_num_requests, len(requests))
        self.assertEqual(expected_operator, user_request['operator'])
        self.assertEqual(expected_groupid, user_request['name'])

        sol_configurations = user_request['requests'][0]['configurations']
        self.assertEqual(len(sol_configurations), expected_configuration_num)
        self.assertEqual(sol_configurations[2]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(sol_configurations[2]['instrument_configs'][0]['exposure_time'], expected_exptime)
        self.assertEqual(sol_configurations[2]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)
        self.assertEqual(sol_configurations[2]['target'], expected_target)

    def test_spectro_with_solar_analog_pm(self):

        utc_date = datetime(2018, 5, 11, 0)
        params = {'proposal_id': 'LCOEngineering',
                  'user_id': 'bsimpson',
                  'spectroscopy': True,
                  'calibs': 'before',
                  'exp_count': 1,
                  'exp_time': 300.0,
                  'instrument_code': 'F65-FLOYDS',
                  'site_code': 'F65',
                  'filter_pattern': 'slit_6.0as',
                  'group_name': self.body_elements['current_name'] + '_' + 'F65' + '-' + datetime.strftime(utc_date, '%Y%m%d') + "_spectra",
                  'start_time':  utc_date + timedelta(hours=5),
                  'end_time':  utc_date + timedelta(hours=15),
                  'solar_analog': True,
                  'calibsource': {'name': 'SA107-684',
                                  'ra_deg': 234.3254167,
                                  'dec_deg': -0.163889,
                                  'pm_ra': 60.313,
                                  'pm_dec': -35.584,
                                  'parallax': 10.5664,
                                  'calib_exptime': 60},
                  }
        expected_num_requests = 1
        expected_operator = 'SINGLE'
        expected_configuration_num = 6
        expected_exp_count = 1
        expected_ast_exptime = 300.0
        expected_cal_exptime = 60.0
        expected_filter = 'slit_6.0as'
        expected_groupid = params['group_name'] + '+solstd'
        expected_ast_target = {'name': 'N999r0q', 'type': 'ORBITAL_ELEMENTS', 'scheme': 'MPC_MINOR_PLANET',
                               'epochofel': 57100.0, 'orbinc': 8.34739, 'longascnode': 147.81325,
                               'argofperih': 85.19251, 'eccentricity': 0.1896865,
                               'extra_params': {'v_magnitude': 16.68, 'fractional_ephemeris_rate': 1}, 'meandist': 1.2176312, 'meananom': 325.2636}
        expected_cal_target = {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3254167, 'dec': -0.163889,
                               'proper_motion_ra': 60.313, 'proper_motion_dec': -35.584, 'extra_params': {}}

        user_request = make_requestgroup(self.body_elements, params)
        requests = user_request['requests']
        self.assertEqual(expected_num_requests, len(requests))
        self.assertEqual(expected_operator, user_request['operator'])
        self.assertEqual(expected_groupid, user_request['name'])

        configurations = user_request['requests'][0]['configurations']
        self.assertEqual(len(configurations), expected_configuration_num)
        self.assertEqual(configurations[2]['target'], expected_ast_target)
        self.assertEqual(configurations[2]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(configurations[2]['instrument_configs'][0]['exposure_time'], expected_ast_exptime)
        self.assertEqual(configurations[2]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)

        self.assertEqual(configurations[5]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(configurations[5]['target'], expected_cal_target)
        self.assertEqual(configurations[5]['instrument_configs'][0]['exposure_time'], expected_cal_exptime)
        self.assertEqual(configurations[5]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)

    def test_solo_solar_spectrum_pm(self):

        utc_date = datetime(2018, 5, 11, 0)
        params = {  'proposal_id' : 'LCOEngineering',
                    'user_id'  : 'bsimpson',
                    'spectroscopy' : True,
                    'calibs'     : 'before',
                    'exp_count'  : 1,
                    'exp_time'   : 300.0,
                    'instrument_code' : 'F65-FLOYDS',
                    'site_code' : 'F65',
                    'filter_pattern' : 'slit_6.0as',
                    'group_name' : 'SA107-684' + '_' + 'F65' + '-' + datetime.strftime(utc_date, '%Y%m%d') + "_spectra",
                    'start_time' :  utc_date + timedelta(hours=5),
                    'end_time'   :  utc_date + timedelta(hours=15),
                    'solar_analog' : False,
                    'ra_deg' : 234.3254167,
                    'dec_deg' : -0.163889,
                    'pm_ra' : 60.313,
                    'pm_dec' : -35.584,
                    'parallax' : 10.5664,
                    'vmag' : 12.4,
                    'source_type' : 4,
                    'source_id' : 'SA107-684',
                  }
        expected_num_requests = 1
        expected_operator = 'SINGLE'
        expected_configuration_num = 3
        expected_exp_count = 1
        expected_exptime = 300.0
        expected_filter = 'slit_6.0as'
        expected_groupid = params['group_name']
        expected_target = {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3254167, 'dec': -0.163889,
                                'proper_motion_ra' : 60.313, 'proper_motion_dec' : -35.584, 'parallax' : 10.5664,
                                'extra_params': { 'v_magnitude' : 12.4} }

        user_request = make_requestgroup({}, params)
        requests = user_request['requests']
        self.assertEqual(expected_num_requests, len(requests))
        self.assertEqual(expected_operator, user_request['operator'])
        self.assertEqual(expected_groupid, user_request['name'])

        sol_configurations = user_request['requests'][0]['configurations']
        self.assertEqual(len(sol_configurations), expected_configuration_num)
        self.assertEqual(sol_configurations[2]['instrument_configs'][0]['exposure_count'], expected_exp_count)
        self.assertEqual(sol_configurations[2]['instrument_configs'][0]['exposure_time'], expected_exptime)
        self.assertEqual(sol_configurations[2]['instrument_configs'][0]['optical_elements']['slit'], expected_filter)
        self.assertEqual(sol_configurations[2]['target'], expected_target)


class TestFetchFilterList(TestCase):
    """Unit test for getting current filters from configdb"""

    def setUp(self):
        self.coj_1m_rsp = {
            '1M0-SCICAM-SINISTRO': {
                'type': 'IMAGE',
                'class': '1m0',
                'name': '1.0 meter Sinistro',
                'optical_elements':
                    {'filters': [
                        {'name': 'Bessell-I', 'code': 'I', 'schedulable': True, 'default': False},
                        {'name': 'Bessell-R', 'code': 'R', 'schedulable': True, 'default': False},
                        {'name': 'Bessell-U', 'code': 'U', 'schedulable': True, 'default': False},
                        {'name': 'PanSTARRS-w', 'code': 'w', 'schedulable': True, 'default': False},
                        {'name': 'PanSTARRS-Y', 'code': 'Y', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-up', 'code': 'up', 'schedulable': True, 'default': False},
                        {'name': 'Clear', 'code': 'air', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-rp', 'code': 'rp', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-ip', 'code': 'ip', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-gp', 'code': 'gp', 'schedulable': True, 'default': False},
                        {'name': 'PanSTARRS-Z', 'code': 'zs', 'schedulable': True, 'default': False},
                        {'name': 'Bessell-V', 'code': 'V', 'schedulable': True, 'default': False},
                        {'name': 'Bessell-B', 'code': 'B', 'schedulable': True, 'default': False},
                        {'name': '400um Pinhole', 'code': '400um-Pinhole', 'schedulable': False, 'default': False},
                        {'name': '150um Pinhole', 'code': '150um-Pinhole', 'schedulable': False, 'default': False},
                        {'name': 'ND', 'code': 'ND', 'schedulable': True, 'default': False},
                        {'name': 'B*ND', 'code': 'B*ND', 'schedulable': False, 'default': False},
                        {'name': 'V*ND', 'code': 'V*ND', 'schedulable': False, 'default': False},
                        {'name': 'R*ND', 'code': 'R*ND', 'schedulable': False, 'default': False},
                        {'name': 'I*ND', 'code': 'I*ND', 'schedulable': False, 'default': False},
                        {'name': 'rp*Diffuser', 'code': 'rp*Diffuser', 'schedulable': False, 'default': False},
                        {'name': 'Diffuser_PennState', 'code': 'Diffuser', 'schedulable': False, 'default': False},
                        {'name': 'gp*Diffuser', 'code': 'gp*Diffuser', 'schedulable': False, 'default': False}]}}}

        self.all_1m_rsp = {
            '1M0-SCICAM-SINISTRO': {
                'type': 'IMAGE',
                'class': '1m0',
                'name': '1.0 meter Sinistro',
                'optical_elements':
                    {'filters': [
                        {'name': 'Bessell-I', 'code': 'I', 'schedulable': True, 'default': False},
                        {'name': 'Bessell-R', 'code': 'R', 'schedulable': True, 'default': False},
                        {'name': 'Bessell-U', 'code': 'U', 'schedulable': True, 'default': False},
                        {'name': 'PanSTARRS-w', 'code': 'w', 'schedulable': True, 'default': False},
                        {'name': 'PanSTARRS-Y', 'code': 'Y', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-up', 'code': 'up', 'schedulable': True, 'default': False},
                        {'name': 'Clear', 'code': 'air', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-rp', 'code': 'rp', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-ip', 'code': 'ip', 'schedulable': True, 'default': False},
                        {'name': 'SDSS-gp', 'code': 'gp', 'schedulable': True, 'default': False},
                        {'name': 'PanSTARRS-Z', 'code': 'zs', 'schedulable': True, 'default': False},
                        {'name': 'Bessell-B', 'code': 'B', 'schedulable': True, 'default': False},
                        {'name': '400um Pinhole', 'code': '400um-Pinhole', 'schedulable': False, 'default': False},
                        {'name': '150um Pinhole', 'code': '150um-Pinhole', 'schedulable': False, 'default': False},
                        {'name': 'ND', 'code': 'ND', 'schedulable': True, 'default': False},
                        {'name': 'B*ND', 'code': 'B*ND', 'schedulable': False, 'default': False},
                        {'name': 'V*ND', 'code': 'V*ND', 'schedulable': False, 'default': False},
                        {'name': 'R*ND', 'code': 'R*ND', 'schedulable': False, 'default': False},
                        {'name': 'I*ND', 'code': 'I*ND', 'schedulable': False, 'default': False},
                        {'name': 'rp*Diffuser', 'code': 'rp*Diffuser', 'schedulable': False, 'default': False},
                        {'name': 'Diffuser_PennState', 'code': 'Diffuser', 'schedulable': False, 'default': False},
                        {'name': 'gp*Diffuser', 'code': 'gp*Diffuser', 'schedulable': False, 'default': False}]}}}

        self.all_2m_rsp = {"2M0-SCICAM-SPECTRAL": {
            "type": "IMAGE",
            "class": "2m0",
            "name": "2.0 meter Spectral",
            "optical_elements": {'filters': [
                 {'name': 'D51', 'code': 'D51', 'schedulable': True, 'default': False},
                 {'name': 'H Beta', 'code': 'H-Beta', 'schedulable': True, 'default': False},
                 {'name': 'OIII', 'code': 'OIII', 'schedulable': True, 'default': False},
                 {'name': 'H Alpha', 'code': 'H-Alpha', 'schedulable': True, 'default': False},
                 {'name': 'Skymapper CaV', 'code': 'Skymapper-VS', 'schedulable': True, 'default': False},
                 {'name': 'Solar (V+R)', 'code': 'solar', 'schedulable': True, 'default': False},
                 {'name': 'Astrodon UV', 'code': 'Astrodon-UV', 'schedulable': True, 'default': False},
                 {'name': 'Bessell-I', 'code': 'I', 'schedulable': True, 'default': False},
                 {'name': 'Bessell-R', 'code': 'R', 'schedulable': True, 'default': False},
                 {'name': 'PanSTARRS-Y', 'code': 'Y', 'schedulable': True, 'default': False},
                 {'name': 'SDSS-up', 'code': 'up', 'schedulable': True, 'default': False},
                 {'name': 'Clear', 'code': 'air', 'schedulable': True, 'default': False},
                 {'name': 'SDSS-rp', 'code': 'rp', 'schedulable': True, 'default': False},
                 {'name': 'SDSS-ip', 'code': 'ip', 'schedulable': True, 'default': False},
                 {'name': 'SDSS-gp', 'code': 'gp', 'schedulable': True, 'default': False},
                 {'name': 'PanSTARRS-Z', 'code': 'zs', 'schedulable': True, 'default': False},
                 {'name': 'Bessell-V', 'code': 'V', 'schedulable': True, 'default': False},
                 {'name': 'Bessell-B', 'code': 'B', 'schedulable': True, 'default': False},
                 {'name': '200um Pinhole', 'code': '200um-Pinhole', 'schedulable': False, 'default': False}]}}}

        self.spec_2m_rsp = {'2M0-FLOYDS-SCICAM': {
            'type': 'SPECTRA',
            'class': '2m0',
            'name': '2.0 meter FLOYDS',
            'optical_elements':
                {'slits': [
                    {'name': '6.0 arcsec slit', 'code': 'slit_6.0as', 'schedulable': True, 'default': False},
                    {'name': '1.6 arcsec slit', 'code': 'slit_1.6as', 'schedulable': True, 'default': False},
                    {'name': '2.0 arcsec slit', 'code': 'slit_2.0as', 'schedulable': True, 'default': False},
                    {'name': '1.2 arcsec slit', 'code': 'slit_1.2as', 'schedulable': True, 'default': False}],
                 }}}

        self.empty = {}

    def test_1m_coj(self):
        expected_filter_list = ['air', 'ND', 'U', 'B', 'V', 'R', 'I', 'up', 'gp', 'rp', 'ip', 'zs', 'Y', 'w']

        filter_list = parse_filter_file(self.coj_1m_rsp, False)
        self.assertCountEqual(expected_filter_list, filter_list)

    def test_1m_all(self):
        expected_filter_list = ['air', 'ND', 'U', 'B', 'R', 'I', 'up', 'gp', 'rp', 'ip', 'zs', 'Y', 'w']

        filter_list = parse_filter_file(self.all_1m_rsp, False)
        self.assertCountEqual(expected_filter_list, filter_list)

    def test_2m_spectral(self):
        expected_filter_list = ['air', 'Astrodon-UV', 'B', 'V', 'R', 'I', 'up', 'gp', 'rp', 'ip', 'Skymapper-VS', 'solar', 'zs', 'Y']

        filter_list = parse_filter_file(self.all_2m_rsp, False)
        self.assertCountEqual(expected_filter_list, filter_list)

    def test_unavailable_telescope(self):
        expected_filter_list = []

        filter_list = parse_filter_file(self.empty, False)
        self.assertCountEqual(expected_filter_list, filter_list)

    def test_spectra_telescope(self):
        expected_filter_list = ['slit_1.2as', 'slit_1.6as', 'slit_2.0as', 'slit_6.0as']

        filter_list = parse_filter_file(self.spec_2m_rsp, True)
        self.assertCountEqual(expected_filter_list, filter_list)


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

    def test_probably_not_real_object(self):
        items = [' SWAN was probably not a real object (Dec. 9.68 UT)\n']
        expected = ['SWAN', 'doesnotexist' , '', '(Dec. 9.68 UT)']

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

    def test_new_with_mpec(self):
        items = [' 2006 GC = P10MSkj (Apr. 7.98 UT)   [see ',
            BeautifulSoup('<a href="/mpec/K19/K19G75.html"><i>MPEC</i> 2019-G75</a>', "html.parser").a,
            ']\n']
        expected = [u'P10MSkj', u'2006 GC', u'MPEC 2019-G75', u'(Apr. 7.98 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_new_crossmatch(self):
        items = ['ZTF02tx = C075WX1 (Apr. 8.66 UT)\n']
        expected = [u'C075WX1', 'ZTF02tx', '', '(Apr. 8.66 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_new_crossmatch2(self):
        items = [' 2019 GR',  BeautifulSoup('<sub>3</sub>', "html.parser").sub, ' = P10Mrzv (Apr. 8.96 UT)\n']
        expected = [u'P10Mrzv', '2019 GR3', '', '(Apr. 8.96 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_new_crossmatch3(self):
        items = [' 2017 QE = P10MWVQ (Apr. 7.90 UT)\n']
        expected = [u'P10MWVQ', '2017 QE', '', '(Apr. 7.90 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_remove_parentheses(self):
        items = [' (455176) = A10c9Hv (Feb. 15.79 UT)\n']
        expected = [u'A10c9Hv', '455176', '', '(Feb. 15.79 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_was_not_confirmed_with_MPEC(self):
        items = [' P10QYyp was not confirmed (Sept. 4.34 UT)   [see ',
            BeautifulSoup('<a href="/mpec/K19/K19R24.html"><i>MPEC</i> 2019-R24</a>', "html.parser").a,
            ']\n']
        expected = [u'P10QYyp', 'wasnotconfirmed', '', u'(Sept. 4.34 UT)']

        crossmatch = parse_previous_NEOCP_id(items)
        self.assertEqual(expected, crossmatch)

    def test_suspected_artificial(self):
        """Test for Issue #548 from 2021/6/11 where artificial satellites
        were reported in a new format"""
        items = [' ZTF0LBs was suspected artificial (June 6.81 UT)\n']
        expected = [u'ZTF0LBs' , 'wasnotminorplanet', '', u'(June 6.81 UT)']

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

    def test_parse_neocpep_new_dates_good_multi_entries(self):
        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">P10OkU8</span>&nbsp;<input type="checkbox" name="obj" VALUE="P10OkU8"> P10OkU8</td>
        <td align="right"><span style="display:none">100</span>100&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2019 05 30.3&nbsp;&nbsp;</td>
        <td><span style="display:none">135.5475</span>&nbsp;&nbsp;13 33.0&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">052.7566</span>&nbsp;&nbsp;-37 14&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">29.5</span>&nbsp;&nbsp;20.5&nbsp;&nbsp;</td>
        <td><span style="display:none">J2458634.158700</span>&nbsp;Added May 30.66 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   4&nbsp;</td>
        <td align="right">&nbsp;  0.03&nbsp;</td>
        <td align="right">&nbsp;20.8&nbsp;</td>
        <td align="right">&nbsp; 0.595&nbsp;</td><tr>
        <tr><td><span style="display:none">A10dYck</span>&nbsp;<input type="checkbox" name="obj" VALUE="A10dYck"> A10dYck</td>
        <td align="right"><span style="display:none">100</span>100&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2019 05 30.4&nbsp;&nbsp;</td>
        <td><span style="display:none">156.4714</span>&nbsp;&nbsp;14 56.7&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">054.0014</span>&nbsp;&nbsp;-35 59&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">31.4</span>&nbsp;&nbsp;18.6&nbsp;&nbsp;</td>
        <td><span style="display:none">J2458634.129509</span>&nbsp;Updated May 30.63 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   7&nbsp;</td>
        <td align="right">&nbsp;  0.23&nbsp;</td>
        <td align="right">&nbsp;21.6&nbsp;</td>
        <td align="right">&nbsp; 0.281&nbsp;</td><tr>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_NEOCP_extra_params(html)
        expected_obj_ids = [(u'P10OkU8', {'score' : 100,
                                        'discovery_date' : datetime(2019, 5, 30, 7, 12, 00),
                                        'num_obs' : 4,
                                        'arc_length' : 0.03,
                                        'not_seen' :  0.595,
                                        'update_time': datetime(2019, 5, 30, 15, 48, 32),
                                        'updated' : False
                                }),
                           (u'A10dYck', {'score' : 100,
                                        'discovery_date' : datetime(2019, 5, 30, 9, 36, 00),
                                        'num_obs' : 7,
                                        'arc_length' : 0.23,
                                        'not_seen' :  0.281,
                                        'update_time': datetime(2019, 5, 30, 15, 6, 30),
                                        'updated' : True
                                })
        ]
        self.assertNotEqual(None, obj_ids)
        obj = 0
        while obj < len(expected_obj_ids):
            self.assertEqual(expected_obj_ids[obj][0], obj_ids[obj][0])
            self.assertEqual(expected_obj_ids[obj][1], obj_ids[obj][1])
            obj += 1

    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_parse_neocpep_pccp_page_down(self):
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
        expected_obj_ids = []
        self.assertEqual(expected_obj_ids, obj_ids)

    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup_pccp)
    def test_parse_neocpep_whole_page(self):
        expected_obj_ids = [ ('CAH024', {'arc_length' : 0.06,
                                          'discovery_date' : datetime(2015,9,20),
                                          'not_seen' : 4.878,
                                          'num_obs' : 6,
                                          'score' : 99,
                                          'update_time' : datetime(2015,9,24,22,47,17),
                                          'updated' : False}),
                             ('WR0159E', {'arc_length' : 15.44,
                                          'discovery_date' : datetime(2015,9,13,9,36),
                                          'not_seen' : 0.726,
                                          'num_obs' : 222,
                                          'score' : 10,
                                          'update_time' : datetime(2015,9,28,17,48,10),
                                          'updated' : True}),
                             ('P10nw2g', {'arc_length' : 1.16,
                                          'discovery_date' : datetime(2015,9,6,7,12),
                                          'not_seen' : 17.455,
                                          'num_obs' : 6,
                                          'score' : 100,
                                          'update_time' : datetime(2015,9,16,1,30,34),
                                          'updated' : True
                                          }),
                            ]
        expected_length = 45

        obj_ids = parse_NEOCP_extra_params(self.test_neocp_page_table)

        self.assertEqual(expected_length, len(obj_ids))
        self.assertEqual(expected_obj_ids[0], obj_ids[0])
        self.assertEqual(expected_obj_ids[-1], obj_ids[-1])
        self.assertEqual(expected_obj_ids[-2], obj_ids[-4])

    def test_parse_neocpep_new_dates_bad1(self):
        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">N00gkyc</span>&nbsp;<input type="checkbox" name="obj" VALUE="N00gkyc"> N00gkyc</td>
        <td align="right"><span style="display:none">100</span>100&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2020 05 32.0&nbsp;&nbsp;</td>
        <td><span style="display:none">328.6061</span>&nbsp;&nbsp;21 54.4&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">098.4370</span>&nbsp;&nbsp;+08 26&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">30.7</span>&nbsp;&nbsp;19.3&nbsp;&nbsp;</td>
        <td><span style="display:none">J2459010.192346</span>&nbsp;Updated June 9.69 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;   5&nbsp;</td>
        <td align="right">&nbsp;  0.46&nbsp;</td>
        <td align="right">&nbsp;18.8&nbsp;</td>
        <td align="right">&nbsp; 8.394&nbsp;</td><tr>
        ''' + self.table_footer, "html.parser")

        expected_obj_ids = [('N00gkyc', {'arc_length': 0.46,
                                         'discovery_date': None,
                                         'not_seen': 8.394,
                                         'num_obs': 5,
                                         'score': 100,
                                         'update_time': datetime(2020, 6, 9, 16, 36, 59),
                                         'updated': True})
                                                ]
        expected_length = 1

        obj_ids = parse_NEOCP_extra_params(html)
        self.assertEqual(expected_length, len(obj_ids))
        self.assertEqual(expected_obj_ids[0], obj_ids[0])


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

    def test_parse_pccp_newdates_multientries(self):

        html = BeautifulSoup(self.table_header +
                             '''
        <tr><td><span style="display:none">A10dRr5</span>&nbsp;<input type="checkbox" name="obj" VALUE="A10dRr5"> A10dRr5</td>
        <td align="right"><span style="display:none">086</span> 86&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2019 05 27.6&nbsp;&nbsp;</td>
        <td><span style="display:none">226.1313</span>&nbsp;&nbsp;19 35.4&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">154.5926</span>&nbsp;&nbsp;+64 35&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">30.7</span>&nbsp;&nbsp;19.3&nbsp;&nbsp;</td>
        <td><span style="display:none">J2458634.240898</span>&nbsp;Updated May 30.74 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;  60&nbsp;</td>
        <td align="right">&nbsp;  2.76&nbsp;</td>
        <td align="right">&nbsp;13.4&nbsp;</td>
        <td align="right">&nbsp; 0.568&nbsp;</td><tr>
        <tr><td><span style="display:none">C0P3XJ2</span>&nbsp;<input type="checkbox" name="obj" VALUE="C0P3XJ2"> C0P3XJ2</td>
        <td align="right"><span style="display:none">035</span> 35&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2019 05 26.4&nbsp;&nbsp;</td>
        <td><span style="display:none">180.6551</span>&nbsp;&nbsp;16 33.5&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">085.3800</span>&nbsp;&nbsp;-04 37&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">29.6</span>&nbsp;&nbsp;20.4&nbsp;&nbsp;</td>
        <td><span style="display:none">J2458633.792922</span>&nbsp;Updated May 30.29 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;  51&nbsp;</td>
        <td align="right">&nbsp;  3.91&nbsp;</td>
        <td align="right">&nbsp;14.9&nbsp;</td>
        <td align="right">&nbsp; 0.611&nbsp;</td><tr>
        <tr><td><span style="display:none">A10dQbl</span>&nbsp;<input type="checkbox" name="obj" VALUE="A10dQbl"> A10dQbl</td>
        <td align="right"><span style="display:none">035</span> 35&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2019 05 25.6&nbsp;&nbsp;</td>
        <td><span style="display:none">297.7413</span>&nbsp;&nbsp;00 21.8&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">096.3491</span>&nbsp;&nbsp;+06 20&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">32.7</span>&nbsp;&nbsp;17.3&nbsp;&nbsp;</td>
        <td><span style="display:none">J2458633.646664</span>&nbsp;Added May 30.15 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp;  51&nbsp;</td>
        <td align="right">&nbsp;  4.33&nbsp;</td>
        <td align="right">&nbsp;13.0&nbsp;</td>
        <td align="right">&nbsp; 0.970&nbsp;</td><tr>
        ''' + self.table_footer, "html.parser")

        obj_ids = parse_PCCP(html)
        expected_obj_ids = [(u'A10dRr5', {'score' : 86,
                                        'discovery_date' : datetime(2019, 5, 27, 14, 24),
                                        'num_obs' : 60,
                                        'arc_length' :  2.76,
                                        'not_seen' : 0.568,
                                        'update_time': datetime(2019, 5, 30, 17, 46, 54),
                                        'updated' : True
                                       }
                            ),
                            (u'C0P3XJ2', {'score' : 35,
                                        'discovery_date' : datetime(2019, 5, 26, 9, 36, 0),
                                        'num_obs' : 51,
                                        'arc_length' :  3.91,
                                        'not_seen' : 0.611,
                                        'update_time': datetime(2019, 5, 30, 7, 1, 48),
                                        'updated' : True
                                       }
                            ),
                            (u'A10dQbl', {'score' : 35,
                                        'discovery_date' : datetime(2019, 5, 25, 14, 24),
                                        'num_obs' : 51,
                                        'arc_length' :  4.33,
                                        'not_seen' : 0.970,
                                        'update_time': datetime(2019, 5, 30,  3, 31, 12),
                                        'updated' : False
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

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet243P.html'), 'r')
        self.test_multiple_epochs_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet2020H3.html'), 'r')
        self.test_missing_data_page = BeautifulSoup(test_fh, "html.parser")
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

    def test_fetch_243P_post2018Aug_epoch(self):

        epoch = datetime(2018, 9, 5, 18, 0, 0)

        expected_elements = {'epoch': '2018-08-30.0',
                             'epoch JD': '2458360.5',
                             'perihelion date': '2018-08-26.00689',
                             'perihelion JD': '2458356.50689',
                             'argument of perihelion': '283.55482',
                             'ascending node': '87.65877',
                             'inclination': '7.64145',
                             'eccentricity': '0.3593001',
                             'perihelion distance': '2.4544438',
                             'radial non-grav. param.': None,
                             'transverse non-grav. param.': None,
                             'semimajor axis': '3.8308789',
                             'mean anomaly': '0.52489',
                             'mean daily motion': '0.13144867',
                             'aphelion distance': '5.207',
                             'period': '7.5',
                             'P-vector [x]': '0.97228322',
                             'P-vector [y]': '0.23016404',
                             'P-vector [z]': '-0.04110774',
                             'Q-vector [x]': '-0.19238738',
                             'Q-vector [y]': '0.88749145',
                             'Q-vector [z]': '0.41874339',
                             'recip semimajor axis orig': None,
                             'recip semimajor axis future': None,
                             'recip semimajor axis error': None,
                             'reference': 'MPC 111774',
                             'observations used': '334',
                             'residual rms': '0.60',
                             'perturbers coarse indicator': 'M-v',
                             'perturbers precise indicator': '0038h',
                             'first observation date used': '2003-08-01.0',
                             'last observation date used': '2018-09-19.0',
                             'computer name': 'MPCW',
                             'orbit quality code': None,
                             'obj_id': '243P/NEAT'}

        elements = parse_mpcorbit(self.test_multiple_epochs_page, epoch)
        self.assertEqual(expected_elements, elements)

    def test_fetch_243P_pre2018Aug_epoch(self):

        # Set epoch to 1 second after the 160/2=80 days between the 2018-03-23
        # and 2018-08-30 elements sets
        epoch = datetime(2018, 6, 11, 0, 0, 1)

        expected_elements = {'epoch': '2018-08-30.0',
                             'epoch JD': '2458360.5',
                             'perihelion date': '2018-08-26.00689',
                             'perihelion JD': '2458356.50689',
                             'argument of perihelion': '283.55482',
                             'ascending node': '87.65877',
                             'inclination': '7.64145',
                             'eccentricity': '0.3593001',
                             'perihelion distance': '2.4544438',
                             'radial non-grav. param.': None,
                             'transverse non-grav. param.': None,
                             'semimajor axis': '3.8308789',
                             'mean anomaly': '0.52489',
                             'mean daily motion': '0.13144867',
                             'aphelion distance': '5.207',
                             'period': '7.5',
                             'P-vector [x]': '0.97228322',
                             'P-vector [y]': '0.23016404',
                             'P-vector [z]': '-0.04110774',
                             'Q-vector [x]': '-0.19238738',
                             'Q-vector [y]': '0.88749145',
                             'Q-vector [z]': '0.41874339',
                             'recip semimajor axis orig': None,
                             'recip semimajor axis future': None,
                             'recip semimajor axis error': None,
                             'reference': 'MPC 111774',
                             'observations used': '334',
                             'residual rms': '0.60',
                             'perturbers coarse indicator': 'M-v',
                             'perturbers precise indicator': '0038h',
                             'first observation date used': '2003-08-01.0',
                             'last observation date used': '2018-09-19.0',
                             'computer name': 'MPCW',
                             'orbit quality code': None,
                             'obj_id': '243P/NEAT'}

        elements = parse_mpcorbit(self.test_multiple_epochs_page, epoch)
        self.assertEqual(expected_elements, elements)

    def test_fetch_243P_post2018Mar_epoch(self):

        # Set epoch to 1 second before the 160/2=80 days between the 2018-03-23
        # and 2018-08-30 elements sets
        epoch = datetime(2018, 6, 10, 23, 59, 59)

        expected_elements = {'epoch': '2018-03-23.0',
                             'epoch JD': '2458200.5',
                             'perihelion date': '2018-08-26.04162',
                             'perihelion JD': '2458356.54162',
                             'argument of perihelion': '283.56217',
                             'ascending node': '87.66076',
                             'inclination': '7.64150',
                             'eccentricity': '0.3591386',
                             'perihelion distance': '2.4544160',
                             'radial non-grav. param.': None,
                             'transverse non-grav. param.': None,
                             'semimajor axis': '3.8298701',
                             'mean anomaly': '339.48043',
                             'mean daily motion': '0.13150061',
                             'aphelion distance': '5.205',
                             'period': '7.5',
                             'P-vector [x]': '0.97225165',
                             'P-vector [y]': '0.23030922',
                             'P-vector [z]': '-0.04104137',
                             'Q-vector [x]': '-0.19254615',
                             'Q-vector [y]': '0.88745569',
                             'Q-vector [z]': '0.4187462',
                             'recip semimajor axis orig': None,
                             'recip semimajor axis future': None,
                             'recip semimajor axis error': None,
                             'reference': 'MPEC 2018-S50',
                             'observations used': '334',
                             'residual rms': '0.60',
                             'perturbers coarse indicator': 'M-v',
                             'perturbers precise indicator': '0038h',
                             'first observation date used': '2003-08-01.0',
                             'last observation date used': '2018-09-19.0',
                             'computer name': 'MPCW',
                             'orbit quality code': None,
                             'obj_id': '243P/NEAT'}

        elements = parse_mpcorbit(self.test_multiple_epochs_page, epoch)
        self.assertEqual(expected_elements, elements)

    def test_fetch_243P_pre2018Mar_epoch(self):

        epoch = datetime(2018, 2, 14,  1,  2,  3)

        expected_elements = {'epoch': '2018-03-23.0',
                             'epoch JD': '2458200.5',
                             'perihelion date': '2018-08-26.04162',
                             'perihelion JD': '2458356.54162',
                             'argument of perihelion': '283.56217',
                             'ascending node': '87.66076',
                             'inclination': '7.64150',
                             'eccentricity': '0.3591386',
                             'perihelion distance': '2.4544160',
                             'radial non-grav. param.': None,
                             'transverse non-grav. param.': None,
                             'semimajor axis': '3.8298701',
                             'mean anomaly': '339.48043',
                             'mean daily motion': '0.13150061',
                             'aphelion distance': '5.205',
                             'period': '7.5',
                             'P-vector [x]': '0.97225165',
                             'P-vector [y]': '0.23030922',
                             'P-vector [z]': '-0.04104137',
                             'Q-vector [x]': '-0.19254615',
                             'Q-vector [y]': '0.88745569',
                             'Q-vector [z]': '0.4187462',
                             'recip semimajor axis orig': None,
                             'recip semimajor axis future': None,
                             'recip semimajor axis error': None,
                             'reference': 'MPEC 2018-S50',
                             'observations used': '334',
                             'residual rms': '0.60',
                             'perturbers coarse indicator': 'M-v',
                             'perturbers precise indicator': '0038h',
                             'first observation date used': '2003-08-01.0',
                             'last observation date used': '2018-09-19.0',
                             'computer name': 'MPCW',
                             'orbit quality code': None,
                             'obj_id': '243P/NEAT'}

        elements = parse_mpcorbit(self.test_multiple_epochs_page, epoch)
        self.assertEqual(expected_elements, elements)

    def test_fetch_C2020H3(self):

        epoch = datetime(2020, 5, 1, 12, 0, 0)

        expected_elements = {}

        elements = parse_mpcorbit(self.test_missing_data_page, epoch)

        self.assertEqual(expected_elements, elements)

    def test_badpage(self):

        expected_elements = {}
        elements = parse_mpcorbit(BeautifulSoup('<html></html>', 'html.parser'))
        self.assertEqual(expected_elements, elements)

    def test_badpage_with_empty_table(self):

        expected_elements = {}
        elements = parse_mpcorbit(BeautifulSoup('<html><table class="nb"><table></table></table></html>', 'html.parser'))
        self.assertEqual(expected_elements, elements)


class TestReadMPCOrbitFile(TestCase):

    def setUp(self):
        self.orbit_file = os.path.join('astrometrics', 'tests', 'test_mpcorbit_2019EN.neocp')

        self.maxDiff = None

    def test1(self):

        expected_orblines = ['K19E00N 21.17  0.15 K1939 343.19351   46.63108  192.93185    9.77594  0.6187870  0.30650105   2.1786196    FO 190311   190   1   59 days 0.21 M-P 06  NEOCPNomin 0000 2019 EN                     20190309']

        orblines = read_mpcorbit_file(self.orbit_file)

        self.assertEqual(len(expected_orblines), len(orblines))
        for i, expected_line in enumerate(expected_orblines):
            self.assertEqual(expected_line, orblines[i])


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
                            'p_* S_l':  u'     N00809b* S2015 06 22.29960 21 02 46.72 +57 58 39.3          20   RLNEOCPC51',
                            'p_ s_l' :  u'     N00809b  s2015 06 22.29960 1 + 1978.7516 + 1150.7393 + 6468.8442   NEOCPC51',
                            'n_ R_l' :  u'01566         R1968 06 14.229167               +    11541710   2388 252 JPLRS253',
                            'n_ r_l' :  u'01566         r1968 06 14.229167S                        1000       252 JPLRS253',
                            'n_tC_l' :  u'01566        tC2002 07 31.54831 20 30 29.56 -47 49 14.5          18.1 Rcg0322474',
                            'p_ C_n' :  u'     WMAA95B  C2015 06 20.29109 16 40 36.42 -14 23 16.2                qNEOCPG96\n',
                            'p_ C_le' : u'     K13R33T  C2013 09 13.18561323 15 20.53 -10 21 52.6          20.4 V      W86\r\n',
                            'p_ C_f' :  u'     WSAE9A6  C2015 09 20.23688 21 41 08.64 -10 51 41.7               VqNEOCPG96',
                            'p_ x_l' :  u'g0232K10F41B* x2010 03 19.91359 06 26 37.29 +35 47 01.3                L~0FUhC51',
                            'p_quoteC_h': u"     G07212  'C2017 11 02.17380 03 13 37.926+19 27 47.07         21.4 GUNEOCP309",
                            'n_pC_l' :  u'01566K15TE5B  C1968 10 13.08015704 13 52.281-02 06 45.33         19.51Rt~1YjBY28',
                            'cp_!C_h':  u'0315PK13V060 !C2013 11 06.14604623 28 19.756-24 20 45.77         21.6 Tt90966705',
                            'cp_C_h':   u'    PK05Y020  C2006 12 25.86945 01 38 12.14 -09 52 27.0          18.9 Nr58738130',
                            'np_4A_l' : u'24554PLS2608 4A1960 09 28.39725 00 39 02.51 +00 49 57.8                Kb6053675',
                            'np_4X_l' : u'24554PLS2608*4X1960 09 24.46184 00 42 27.17 +00 55 44.5          18.1  Kb6053675',
                            'p_* C_l' : u'     K15TE5B* C2015 10 19.36445 04 16 45.66 -02 06 29.9          18.7 RqEU023H45',
                            'p_*KC_l' : u'     K15TE5B*KC2015 10 18.42125 04 16 20.07 -02 07 27.5          19.2 Vq     Q63',
                            't_* C_l' : u'     LSCTLZZ* C2018 10 19.36445 04 16 45.66 -02 06 29.9          18.7 Rq     W85',
                            't_*KC_l' : u'     LSCTLZZ*KC2018 10 18.42125 04 16 20.07 -02 07 27.5          19.2 Vq     W86',
                            't_*IC_l' : u'     CPTTLAZ*IC2018 10 18.92125 04 16 20.07 -02 07 27.5          19.2 rV     L09',
                            'cp_ A_l' : u'0289PI19W010  A1819 12 14.22911 12 47 12.8  +06 18 32                   BJ824007',
                            'cp_ C_l' : u'0289PK03W25Y  C2003 10 25.16974 00 25 15.12 -19 59 45.5          18.8 Toj1989699',
                            'c_ C_l'  : u'0289P         C2015 05 18.19229 13 15 46.04 -02 26 41.9          17.3 Nu94436G30',
                            'c_ M_l2P': u'0002P         M1881 08 26.07540 04 02 14.37 +33 31 38.5                pAN114522',
                            'c_ A_l2P': u'0002P         A1957 07 28.40075 03 42 44.76 +28 38 23.3          19.3 N AJ070689',
                            'c_KC_l2P': u'0002P        KC2019 10 04.62400 23 25 58.25 +04 03 54.3          18.2 Tq~01Y1Q11',
                            'c_ A_l46P':u'0046PJ54R020  A1954 10 28.53048 09 53 23.37 +18 44 42.1                 AJ060662',
                            'c_ C_l73P':u'0073P         C1995 12 22.36597 22 02 32.30 -21 36 12.0                 26211897',
                            'c_aC_l73P':u'0073P      a  C1995 12 23.12177 22 04 58.78 -21 21 19.8                 26444693',
                           'c_btC_l73P':u'0073P     bt  C2017 09 27.20655 03 00 10.55 +05 17 00.6          17.0 Tq@6559J22',
                            'cp_bKC_l': u'    CK15E61b KC2017 12 17.94440 02 44 22.10 +15 55 27.3          18.5 Nq@7755160',
                            'cp_cKC_l': u'0332PK10V01c KC2016 02 19.06978 08 49 10.77 +34 23 21.4          18.1 Nq97706I81',
                            'cZ_ C_lX': u'    CK22E030 ZC2021 10 25.17101318 59 23.09 -05 07 29.4          20.5 gXEM021I41',
                            'cZ_ C_lW': u'    CK22E030 ZC2021 10 25.17101318 59 23.09 -05 07 29.4          20.5 gWEM021I41',
                            'cK_ C_lZ': u'    CK22E030 KC2022 05 19.41238 20 05 55.31 +18 29 26.0          15.2 rZEK019G80',
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
                            'site_code' : 'H45',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : 'H21',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : 'W88',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : 'Y28',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : 'C51',
                            'discovery' : False,
                            'lco_discovery' : False
                            }

        params = parse_mpcobs(self.test_lines['p_ S_l'])

        self.compare_dict(expected_params, params)

    def test_p_discovery_spaceS_l(self):
        expected_params = { 'body'  : 'N00809b',
                            'flags' : '*',
                            'obs_type'  : 'S',
                            'obs_date'  : datetime(2015, 6, 22, 7, 11, 25, int(0.44*1e6)),
                            'obs_ra'    : 315.69466666666667,
                            'obs_dec'   : 57.977583333333333,
                            'obs_mag'   : 20.0,
                            'filter'    : 'R',
                            'astrometric_catalog' : '2MASS',
                            'site_code' : 'C51',
                            'discovery' : True,
                            'lco_discovery' : False
                            }

        params = parse_mpcobs(self.test_lines['p_* S_l'])

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
                            'site_code' : '474',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : 'G96',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : 'W86',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : 'G96',
                            'discovery' : False,
                            'lco_discovery' : False
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
                            'site_code' : '309',
                            'discovery' : False,
                            'lco_discovery' : False
                          }

        params = parse_mpcobs(self.test_lines['p_quoteC_h'])

        self.compare_dict(expected_params, params)

    def test_cp_plingC_h(self):
        expected_params = { 'body'  : '315P',
                            'flags' : '!',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2013, 11,  6, 3, 30, 18, int(0.3744*1e6)),
                            'obs_ra'    : 352.08231666666667,
                            'obs_dec'   : -24.346047222222222,
                            'obs_mag'   : 21.6,
                            'filter'    : 'T',
                            'astrometric_catalog' : 'PPMXL',
                            'site_code' : '705',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cp_!C_h'])

        self.compare_dict(expected_params, params)

    def test_cp_C_h(self):
        """Test for comet with no number, only provisional designation"""
        expected_params = { 'body'  : 'PK05Y020',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2006, 12,  25, 20, 52, 0, int(0.4800*1e6)),
                            'obs_ra'    : 24.5505833333333,
                            'obs_dec'   : -9.87416666666,
                            'obs_mag'   : 18.9,
                            'filter'    : 'N',
                            'astrometric_catalog' : 'UCAC-2',
                            'site_code' : '130',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cp_C_h'])

        self.compare_dict(expected_params, params)

    def test_cp_A_l(self):
        """Test for comet with number and provisional designation, old-style A-observation"""
        expected_params = { 'body'  : '289P',
                            'flags' : ' ',
                            'obs_type'  : 'A',
                            'obs_date'  : datetime(1819, 12, 14,  5, 29, 55, int(0.1040*1e6)),
                            'obs_ra'    : 191.803333333,
                            'obs_dec'   : 6.30888888889,
                            'obs_mag'   : None,
                            'filter'    : ' ',
                            'astrometric_catalog' : '',
                            'site_code' : '007',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cp_ A_l'])

        self.compare_dict(expected_params, params)

    def test_cp_C_l(self):
        """Test for comet with number and provisional designation, new-style (C)CD observation"""
        expected_params = { 'body'  : '289P',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2003, 10, 25,  4,  4, 25, int(0.536*1e6)),
                            'obs_ra'    : 6.313,
                            'obs_dec'   : -19.9959722222,
                            'obs_mag'   : 18.8,
                            'filter'    : 'T',
                            'astrometric_catalog' : 'USNO-B1',
                            'site_code' : '699',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cp_ C_l'])

        self.compare_dict(expected_params, params)

    def test_c_C_l(self):
        """Test for comet with number only, new-style (C)CD observation"""
        expected_params = { 'body'  : '289P',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015,  5, 18,  4, 36, 53, int(0.856*1e6)),
                            'obs_ra'    : 198.941833333,
                            'obs_dec'   : -2.44497222222,
                            'obs_mag'   : 17.3,
                            'filter'    : 'N',
                            'astrometric_catalog' : 'UCAC-3',
                            'site_code' : 'G30',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['c_ C_l'])

        self.compare_dict(expected_params, params)

    def test_c_M_l_2P(self):
        """Test for comet 2P with number only, really old-style (M)icrometer observation (to be ignored)"""
        expected_params = {}
        params = parse_mpcobs(self.test_lines['c_ M_l2P'])

        self.compare_dict(expected_params, params)

    def test_c_A_l_2P(self):
        """Test for comet 2P with number only, old-style A-observation"""
        expected_params = { 'body'  : '2P',
                            'flags' : ' ',
                            'obs_type'  : 'A',
                            'obs_date'  : datetime(1957,  7, 28,  9, 37,  4, int(0.8*1e6)),
                            'obs_ra'    : 55.6865,
                            'obs_dec'   : 28.6398055556,
                            'obs_mag'   : 19.3,
                            'filter'    : 'N',
                            'astrometric_catalog' : '',
                            'site_code' : '689',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['c_ A_l2P'])

        self.compare_dict(expected_params, params)

    def test_c_KC_l_2P(self):
        """Test for comet 2P with number only, new-style (C)CD observation"""
        expected_params = { 'body'  : '2P',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2019, 10,  4, 14, 58, 33, int(0.6*1e6)),
                            'obs_ra'    : 351.492708333,
                            'obs_dec'   : 4.06508333333,
                            'obs_mag'   : 18.2,
                            'filter'    : 'T',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'Q11',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['c_KC_l2P'])

        self.compare_dict(expected_params, params)

    def test_c_A_l_46P(self):
        """Test for comet 46P with number and provisional desigination, old-style A-observation"""
        expected_params = { 'body'  : '46P',
                            'flags' : ' ',
                            'obs_type'  : 'A',
                            'obs_date'  : datetime(1954, 10, 28, 12, 43, 53, int(0.472*1e6)),
                            'obs_ra'    : 148.347375,
                            'obs_dec'   : 18.7450277778,
                            'obs_mag'   : None,
                            'filter'    : ' ',
                            'astrometric_catalog' : '',
                            'site_code' : '662',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['c_ A_l46P'])

        self.compare_dict(expected_params, params)

    def test_c_C_l_73P(self):
        """Test for comet 73P (whole comet) with number only, new-style (C)CD observation"""
        expected_params = { 'body'  : '73P',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(1995, 12, 22,  8, 46, 59, int(0.808*1e6)),
                            'obs_ra'    : 330.634583333,
                            'obs_dec'   : -21.6033333333,
                            'obs_mag'   : None,
                            'filter'    : ' ',
                            'astrometric_catalog' : '',
                            'site_code' : '897',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['c_ C_l73P'])

        self.compare_dict(expected_params, params)

    def test_c_aC_l_73P(self):
        """Test for comet 73P ('a' fragment) with number only, new-style (C)CD observation"""
        expected_params = { 'body'  : '73P-A',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(1995, 12, 23,  2, 55, 20, int(0.928*1e6)),
                            'obs_ra'    : 331.244916667,
                            'obs_dec'   : -21.3555,
                            'obs_mag'   : None,
                            'filter'    : ' ',
                            'astrometric_catalog' : '',
                            'site_code' : '693',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['c_aC_l73P'])

        self.compare_dict(expected_params, params)

    def test_c_btC_l_73P(self):
        """Test for comet 73P ('bt' fragment) with number only, new-style (C)CD observation"""
        expected_params = { 'body'  : '73P-BT',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2017,  9, 27,  4, 57, 25, int(0.92*1e6)),
                            'obs_ra'    : 45.0439583333,
                            'obs_dec'   : 5.2835,
                            'obs_mag'   : 17.0,
                            'filter'    : 'T',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'J22',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['c_btC_l73P'])

        self.compare_dict(expected_params, params)

    def test_cp_bKC_l(self):
        """Test for comet C/2015-E61-B ('b' fragment) with provisional desigination only, new-style (C)CD observation"""
        expected_params = { 'body'  : 'CK15E61b',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2017, 12, 17, 22, 39, 56, int(0.16*1e6)),
                            'obs_ra'    : 41.0920833333,
                            'obs_dec'   : 15.92425,
                            'obs_mag'   : 18.5,
                            'filter'    : 'N',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : '160',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cp_bKC_l'])

        self.compare_dict(expected_params, params)

    def test_cp_cKC_l(self):
        """Test for comet 332P-C = P/2010 V1-C (332P 'c' fragment) with number and provisional desigination only, new-style (C)CD observation"""
        expected_params = { 'body'  : '332P-C',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2016,  2, 19,  1, 40, 28, int(0.992*1e6)),
                            'obs_ra'    : 132.294875,
                            'obs_dec'   : 34.3892777778,
                            'obs_mag'   : 18.1,
                            'filter'    : 'N',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'I81',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cp_cKC_l'])

        self.compare_dict(expected_params, params)

    def test_cZ_C_lX(self):
        """Test for comet C/2022 E3 with provisional desigination, new-style (C)CD observation, Gaia-EDR3 catalog code"""
        expected_params = { 'body'  : 'CK22E030',
                            'flags' : 'Z',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2021, 10, 25,  4,  6, 15, int(0.5232*1e6)),
                            'obs_ra'    : 284.8462083333334,
                            'obs_dec'   : -5.124833333333334,
                            'obs_mag'   : 20.5,
                            'filter'    : 'g',
                            'astrometric_catalog' : 'GAIA-EDR3',
                            'site_code' : 'I41',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cZ_ C_lX'])

        self.compare_dict(expected_params, params)

    def test_cZ_C_lW(self):
        """Test for comet C/2022 E3 with provisional desigination, new-style (C)CD observation, GAIA-DR3 catalog code"""
        expected_params = { 'body'  : 'CK22E030',
                            'flags' : 'Z',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2021, 10, 25,  4,  6, 15, int(0.5232*1e6)),
                            'obs_ra'    : 284.8462083333334,
                            'obs_dec'   : -5.124833333333334,
                            'obs_mag'   : 20.5,
                            'filter'    : 'g',
                            'astrometric_catalog' : 'GAIA-DR3',
                            'site_code' : 'I41',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cZ_ C_lW'])

        self.compare_dict(expected_params, params)

    def test_cK_C_lZ(self):
        """Test for comet C/2022 E3 with provisional desigination, new-style (C)CD stac(K)ed observation, ATLAS-2 catalog code"""
        expected_params = { 'body'  : 'CK22E030',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2022,  5, 19,  9, 53, 49, int(0.632*1e6)),
                            'obs_ra'    : 301.4804583333334,
                            'obs_dec'   : 18.490555555555556,
                            'obs_mag'   : 15.2,
                            'filter'    : 'r',
                            'astrometric_catalog' : 'ATLAS-2',
                            'site_code' : 'G80',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['cK_ C_lZ'])

        self.compare_dict(expected_params, params)

    def test_np_fourA_l(self):
        expected_params = { 'body'  : '24554',
                            'flags' : ' ',
                            'obs_type'  : 'A',
                            'obs_date'  : datetime(1960,  9, 28, 9, 32,  2, int(0.4*1e6)),
                            'obs_ra'    :   9.7604583333333333,
                            'obs_dec'   :  0.83272222222222222,
                            'obs_mag'   : None,
                            'filter'    : ' ',
                            'astrometric_catalog' : 'Yale',
                            'site_code' : '675',
                            'discovery' : False,
                            'lco_discovery' : False
                          }
        params = parse_mpcobs(self.test_lines['np_4A_l'])

        self.compare_dict(expected_params, params)

    def test_np_fourX_l(self):
        expected_params = { }
        params = parse_mpcobs(self.test_lines['np_4X_l'])

        self.compare_dict(expected_params, params)

    def test_n_pC_l(self):
        """Tests the case for both a number and a provisional designation"""

        expected_params = { 'body'  : '01566',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(1968, 10, 13, 1, 55, 25, int(0.5648*1e6)),
                            'obs_ra'    : 63.4678375,
                            'obs_dec'   : -2.112591666666667,
                            'obs_mag'   : 19.51,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'PPMXL',
                            'site_code' : 'Y28',
                            'discovery' : False,
                            'lco_discovery' : False
                          }

        params = parse_mpcobs(self.test_lines['n_pC_l'])

        self.compare_dict(expected_params, params)

    def test_p_discovery_spaceC_l(self):
        expected_params = { 'body'  : 'K15TE5B',
                            'flags' : '*',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 10, 19, 8, 44, 48, int(0.48*1e6)),
                            'obs_ra'    : 64.19025,
                            'obs_dec'   : -2.1083055555555554,
                            'obs_mag'   : 18.7,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'H45',
                            'discovery' : True,
                            'lco_discovery' : False
                          }

        params = parse_mpcobs(self.test_lines['p_* C_l'])

        self.compare_dict(expected_params, params)

    def test_p_discovery_KC_l(self):
        expected_params = { 'body'  : 'K15TE5B',
                            'flags' : '*,K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 10, 18, 10, 6, 36, 0),
                            'obs_ra'    : 64.083625,
                            'obs_dec'   : -2.1243055555555554,
                            'obs_mag'   : 19.2,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'Q63',
                            'discovery' : True,
                            'lco_discovery' : True
                          }

        params = parse_mpcobs(self.test_lines['p_*KC_l'])

        self.compare_dict(expected_params, params)

    def test_t_discovery_spaceC_l(self):
        expected_params = { 'body'  : 'LSCTLZZ',
                            'flags' : '*',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2018, 10, 19, 8, 44, 48, int(0.48*1e6)),
                            'obs_ra'    : 64.19025,
                            'obs_dec'   : -2.1083055555555554,
                            'obs_mag'   : 18.7,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'W85',
                            'discovery' : True,
                            'lco_discovery' : True
                          }

        params = parse_mpcobs(self.test_lines['t_* C_l'])

        self.compare_dict(expected_params, params)

    def test_t_discovery_KC_l(self):
        expected_params = { 'body'  : 'LSCTLZZ',
                            'flags' : '*,K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2018, 10, 18, 10, 6, 36, 0),
                            'obs_ra'    : 64.083625,
                            'obs_dec'   : -2.1243055555555554,
                            'obs_mag'   : 19.2,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'W86',
                            'discovery' : True,
                            'lco_discovery' : True
                          }

        params = parse_mpcobs(self.test_lines['t_*KC_l'])

        self.compare_dict(expected_params, params)

    def test_t_discovery_IC_l(self):
        expected_params = { 'body'  : 'CPTTLAZ',
                            'flags' : '*,I',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2018, 10, 18, 22, 6, 36, 0),
                            'obs_ra'    : 64.083625,
                            'obs_dec'   : -2.1243055555555554,
                            'obs_mag'   : 19.2,
                            'filter'    : 'r',
                            'astrometric_catalog' : 'GAIA-DR2',
                            'site_code' : 'L09',
                            'discovery' : True,
                            'lco_discovery' : True
                          }

        params = parse_mpcobs(self.test_lines['t_*IC_l'])

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

    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_page_down(self):
        observations = fetch_NEOCP_observations("test_body")
        expected = None
        self.assertEqual(expected, observations)


class TestIMAPLogin(TestCase):

    def setUp(self):
        pass

    @patch('astrometrics.sources_subs.imaplib')
    def test_server_connection(self, mockimaplib):
        mailbox = imap_login('foo@bar.net', 'Wibble', 'localhost')
        mockimaplib.IMAP4_SSL.assert_called_with('localhost')
        self.assertNotEqual(None, mailbox)

    @patch('astrometrics.sources_subs.imaplib')
    def test_badserver(self, mockimaplib):
        mockimaplib.IMAP4_SSL.side_effect = error(111, 'Connection refused')
        mailbox = imap_login('foo@bar.net', 'Wibble', 'localhost')
        self.assertEqual(None, mailbox)

    @patch('astrometrics.sources_subs.imaplib')
    def test_badfolder(self, mockimaplib):
        mailbox = MagicMock()
        mailbox.select.return_value = ("NO", ['[NONEXISTENT] Unknown Mailbox: Wibble (Failure)'])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox, folder="Wibble")
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    def test_emptyfolder(self, mockimaplib):
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'0'])
        mailbox.search.return_value = ("OK", [b''])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    def test_foldersearchfailure(self, mockimaplib):
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'0'])
        mailbox.search.return_value = ("NO", [b''])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    def test_cannot_retrieve_msg_high(self, mockimaplib):
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ("OK", [None, ])
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    def test_cannot_retrieve_msg_low(self, mockimaplib):
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.side_effect = error("FETCH command error: BAD ['Could not parse command']")
        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_msg_correct_match(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 18,  21, 27, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ("OK", [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 CV246 - Observations Requested\r\nDate: Tue, 18 Feb 2016 21:27:04 +000\r\n')])

        expected_targets = ['2016 CV246']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_msg_has_bad_prefix(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 18,  21, 27, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-birds-observations] 2016 CV246 - Observations Requested\r\nDate: Tue, 16 Feb 2018 21:27:04 +000\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_msg_has_bad_suffix(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 18,  21, 27, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 CV246 - Radar Requested\r\nDate: Tue, 18 Feb 2016 21:27:04 +000\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_msg_good_with_tz(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 24,  1, 0, 0)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 22 Feb 2016 20:27:04 -0500\r\n')])

        expected_targets = ['2016 BA14']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_reject_msg_old_with_tz(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 15,  4, 27, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 13 Feb 2016 20:27:04 -0800\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_multiple_msgs(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 24,  1, 0, 0)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'2'])
        mailbox.search.return_value = ("OK", [b'1 2'])
        results = [ ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 22 Feb 2016 20:27:04 -0500\r\n')]),
                    ('OK', [(b'2 (RFC822 {12324}', b'Subject: [small-bodies-observations] 2016 CV123 - Observations Requested\r\nDate: Tue, 22 Feb 2016 22:47:42 -0500\r\n')])
                   ]
        mailbox.fetch.side_effect = results

        expected_targets = ['2016 BA14', '2016 CV123']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_one_msg_multiple_old_msgs(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 24,  1, 0, 0)
        mailbox = MagicMock()
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

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_find_fwd_msg_(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 23, 19, 51, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: Fwd: [small-bodies-observations] 2016 DJ - Observations Requested\r\nDate: Tue, 23 Feb 2016 11:25:29 -0800\r\n')])

        expected_targets = ['2016 DJ']
        targets = fetch_NASA_targets(mailbox)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_reject_msg_old_with_tz_and_cutoff(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 16,  4, 27, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 13 Feb 2016 20:27:04 -0800\r\n')])

        expected_targets = []
        targets = fetch_NASA_targets(mailbox, date_cutoff=2)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_accept_msg_old_with_tz_and_cutoff(self, mockimaplib):
        MockDateTime.change_datetime(2016, 2, 16,  3, 26, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 BA14 - Observations Requested\r\nDate: Tue, 13 Feb 2016 20:27:04 -0800\r\n')])

        expected_targets = ['2016 BA14']
        targets = fetch_NASA_targets(mailbox, date_cutoff=2)
        self.assertEqual(expected_targets, targets)

    @patch('astrometrics.sources_subs.imaplib')
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_accept_msg_multiple_targets(self, mockimaplib):
        MockDateTime.change_datetime(2016, 10, 25,  3, 26, 5)
        mailbox = MagicMock()
        mailbox.select.return_value = ("OK", [b'1'])
        mailbox.search.return_value = ("OK", [b'1'])
        mailbox.fetch.return_value = ('OK', [(b'1 (RFC822 {12326}', b'Subject: [small-bodies-observations] 2016 TQ11, 2016 SR2, 2016 NP56,\r\n\t2016 ND1- Observations Requested\r\nDate: Mon, 24 Oct 2016 20:20:57 +0000\r\n')])

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

        expected_result = (datetime(2018, 1, 15, 17, 44, 10), 70*self.sfu)

        sfu_result = fetch_sfu(self.test_sfu_page)

        self.assertEqual(expected_result[0], sfu_result[0])
        self.assertEqual(expected_result[1].value, sfu_result[1].value)
        self.assertEqual(expected_result[1].unit, sfu_result[1].unit)
        self.assertEqual(expected_result[1].to(u.MJy), sfu_result[1].to(u.MJy))

    def test_notable(self):

        html = '''<html><head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"><title>Foo</title><style></style></head>
                <body>
                </body></html>
                '''
        page = BeautifulSoup(html, 'html.parser')
        expected_result = (None, None)

        sfu_result = fetch_sfu(page)

        self.assertEqual(expected_result[0], sfu_result[0])
        self.assertEqual(expected_result[1], sfu_result[1])

    def test_bad_JD(self):

        html = '''<html><head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"><title>Foo</title><style></style></head>
                <body>
                <table>
                <tr><th>Julian Day Number</th><td>Wibble</td></tr>
                </table>
                </body></html>
                '''
        page = BeautifulSoup(html, 'html.parser')
        expected_result = (None, None)

        sfu_result = fetch_sfu(page)

        self.assertEqual(expected_result[0], sfu_result[0])
        self.assertEqual(expected_result[1], sfu_result[1])

    def test_bad_fluxvalue(self):

        html = '''<html><head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"><title>Foo</title><style></style></head>
                <body>
                <table>
                <tr><th>Julian Day Number</th><td>2458134.239</td></tr>
                <tr><th>Observed Flux Density</th><td>Wibble</td></tr>
                </table>
                </body></html>
                '''
        page = BeautifulSoup(html, 'html.parser')
        expected_result = (datetime(2018, 1, 15, 17, 44, 10), None)

        sfu_result = fetch_sfu(page)

        self.assertEqual(expected_result[0], sfu_result[0])
        self.assertEqual(expected_result[1], sfu_result[1])

    # Uncomment and remove catch of `timeout` in fetchpage_and_make_soup() to
    # test the mock is working.

    # @patch('astrometrics.sources_subs.urllib.request.OpenerDirector.open')
    # def test_fetch_socket_timeout_assert_raises(self, mock_open):
        # mock_open.side_effect = timeout(ETIMEDOUT, '(fake) timed out')

        # with self.assertRaises(timeout) as sock_e:
            # sfu_result = fetchpage_and_make_soup('http://www.spaceweather.gc.ca/solarflux/sx-4-en.php')
        # self.assertEqual(sock_e.exception.errno, ETIMEDOUT)
        # self.assertEqual(sock_e.exception.strerror, '(fake) timed out')

    @patch('astrometrics.sources_subs.urllib.request.OpenerDirector.open')
    def test_fetch_socket_timeout_handled(self, mock_open):
        mock_open.side_effect = timeout(ETIMEDOUT, '(fake) timed out')

        sfu_result = fetch_sfu()

        self.assertEqual((None, None), sfu_result)


class TestConfigureDefaults(TestCase):

    def setUp(self):
        self.obs_params = {'exp_count': 10,
                           'exp_time': 42.0
                           }

    def test_tfn_point4m(self):

        test_params = self.obs_params
        test_params['site_code'] = 'Z21'

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'site': 'TFN',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_ogg_point4m(self):
        test_params = self.obs_params
        test_params['site_code'] = 'T04'

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'site': 'OGG',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_coj_point4m(self):
        test_params = self.obs_params
        test_params['site_code'] = 'Q59'

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'site': 'COJ',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_cpt_point4m(self):
        test_params = self.obs_params
        test_params['site_code'] = 'L09'

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'site': 'CPT',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_elp_point4m(self):
        test_params = self.obs_params
        test_params['site_code'] = 'V38'

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': 'aqwa',
                            'site': 'ELP',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_point4m_num1(self):
        test_params = self.obs_params
        test_params['site_code'] = 'W89'

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'site': 'LSC',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_point4m_num2(self):
        test_params = self.obs_params
        test_params['site_code'] = 'W79'

        expected_params = { 'instrument':  '0M4-SCICAM-SBIG',
                            'pondtelescope': '0m4',
                            'observatory': '',
                            'site': 'LSC',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_sinistro(self):
        test_params = self.obs_params
        test_params['site_code'] = 'W86'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'site': 'LSC',
                            'binning': 1}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_lsc_bad_sinistro(self):
        test_params = self.obs_params
        test_params['site_code'] = 'W87'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'site': 'LSC',
                            'binning': 1,
                            'site_code': 'W87',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_ftn(self):
        test_params = self.obs_params
        test_params['site_code'] = 'F65'

        expected_params = {'instrument':  '2M0-SCICAM-MUSCAT',
                           'pondtelescope': '2m0',
                           'observatory': '',
                           'site': 'OGG',
                           'binning': 1,
                           'exp_count': 10,
                           'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_fts(self):
        test_params = self.obs_params
        test_params['site_code'] = 'E10'

        expected_params = { 'instrument':  '2M0-SCICAM-SPECTRAL',
                            'pondtelescope': '2m0',
                            'observatory': '',
                            'site': 'COJ',
                            'binning': 2,
                            'exp_count': 10,
                            'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_elp_sinistro(self):
        test_params = self.obs_params
        test_params['site_code'] = 'V37'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'site': 'ELP',
                            'binning': 1,
                            'exp_count': 10,
                            'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_elp_num2_sinistro(self):
        test_params = self.obs_params
        test_params['site_code'] = 'V39'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'site': 'ELP',
                            'binning': 1,
                            'exp_count': 10,
                            'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_tfn_sinistro(self):
        test_params = self.obs_params
        test_params['site_code'] = 'Z31'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'site': 'TFN',
                            'binning': 1,
                            'exp_count': 10,
                            'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_tfn_num2_sinistro(self):
        test_params = self.obs_params
        test_params['site_code'] = 'Z24'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'site': 'TFN',
                            'binning': 1,
                            'exp_count': 10,
                            'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_sinistro_many(self):
        test_params = self.obs_params
        test_params['site_code'] = '1M0'
        test_params['exp_count'] = 45
        test_params['filter_pattern'] = 'w'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'binning': 1,
                            'exp_count': 45,
                            'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_sinistro_many_plus_filters(self):
        test_params = self.obs_params
        test_params['site_code'] = '1M0'
        test_params['exp_count'] = 15
        test_params['filter_pattern'] = 'B,B,B,V,V,V,R,R,R,R,I,I,I'

        expected_params = { 'instrument':  '1M0-SCICAM-SINISTRO',
                            'pondtelescope': '1m0',
                            'observatory': '',
                            'binning': 1,
                            'exp_count': 15,
                            'exp_time': 42.0}
        expected_params.update(test_params)

        params = configure_defaults(test_params)

        self.assertEqual(expected_params, params)

    def test_1m_sinistro_cpt(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'pondtelescope': '1m0',
                            'site': 'CPT',
                            'site_code': 'K92',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'K92'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_lsc_doma(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'pondtelescope': '1m0',
                            'site': 'LSC',
                            'site_code': 'W85',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'W85'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_lsc(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'pondtelescope': '1m0',
                            'site': 'LSC',
                            'site_code': 'W86',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'W86'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_elp(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'pondtelescope': '1m0',
                            'site': 'ELP',
                            'site_code': 'V37',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'V37'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_lsc_domec(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'pondtelescope': '1m0',
                            'site': 'LSC',
                            'site_code': 'W87',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'W87'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_1m_sinistro_cpt_domec(self):
        expected_params = { 'binning': 1,
                            'instrument': '1M0-SCICAM-SINISTRO',
                            'observatory': '',
                            'pondtelescope': '1m0',
                            'site': 'CPT',
                            'site_code': 'K93',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'K93'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_ogg(self):
        expected_params = {'binning': 1,
                           'instrument': '2M0-SCICAM-MUSCAT',
                           'observatory': '',
                           'pondtelescope': '2m0',
                           'site': 'OGG',
                           'site_code': 'F65',
                           'exp_count': 10,
                           'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'F65'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_coj(self):
        expected_params = { 'binning': 2,
                            'instrument': '2M0-SCICAM-SPECTRAL',
                            'observatory': '',
                            'pondtelescope': '2m0',
                            'site': 'COJ',
                            'site_code': 'E10',
                            'exp_count': 10,
                            'exp_time': 42.0}

        params = self.obs_params
        params['site_code'] = 'E10'

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_ogg_floyds(self):
        expected_params = { 'spectroscopy': True,
                            'binning'     : 1,
                            'spectra_slit': 'slit_6.0as',
                            'instrument'  : '2M0-FLOYDS-SCICAM',
                            'observatory' : '',
                            'exp_type'    : 'SPECTRUM',
                            'pondtelescope' : '2m0',
                            'site'        : 'OGG',
                            'exp_count': 1,
                            'site_code'   : 'F65',
                            'instrument_code' : 'F65-FLOYDS'}

        params = {'site_code': 'F65',
                  'instrument_code': 'F65-FLOYDS',
                  'spectroscopy': True,
                  'exp_count': 1}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_coj_floyds(self):
        expected_params = { 'spectroscopy': True,
                            'binning'     : 1,
                            'spectra_slit': 'slit_6.0as',
                            'instrument'  : '2M0-FLOYDS-SCICAM',
                            'observatory' : '',
                            'exp_type'    : 'SPECTRUM',
                            'exp_count': 1,
                            'pondtelescope': '2m0',
                            'site'        : 'COJ',
                            'site_code'   : 'E10',
                            'instrument_code' : 'E10-FLOYDS'}

        params = { 'site_code' : 'E10', 'instrument_code' : 'E10-FLOYDS', 'spectroscopy' : True,
                   'exp_count': 1}

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_ogg_floyds_solar_analog(self):
        expected_params = { 'spectroscopy': True,
                            'binning'     : 1,
                            'spectra_slit': 'slit_6.0as',
                            'instrument'  : '2M0-FLOYDS-SCICAM',
                            'observatory' : '',
                            'exp_type'    : 'SPECTRUM',
                            'exp_count'   : 1,
                            'pondtelescope' : '2m0',
                            'site'        : 'OGG',
                            'site_code'   : 'F65',
                            'instrument_code' : 'F65-FLOYDS',
                            'solar_analog' : False,
                            'calibsource' : {'name' : 'SA107-684'}
                            }

        params = { 'site_code': 'F65',
                   'instrument_code': 'F65-FLOYDS',
                   'spectroscopy': True,
                   'solar_analog': False,
                   'calibsource': {'name': 'SA107-684'},
                   'exp_count': 1
                   }

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)

    def test_2m_ogg_floyds_unmatched_solar_analog(self):
        expected_params = { 'spectroscopy': True,
                            'binning'     : 1,
                            'spectra_slit': 'slit_6.0as',
                            'instrument'  : '2M0-FLOYDS-SCICAM',
                            'observatory' : '',
                            'exp_type'    : 'SPECTRUM',
                            'exp_count': 1,
                            'pondtelescope' : '2m0',
                            'site'        : 'OGG',
                            'site_code'   : 'F65',
                            'instrument_code' : 'F65-FLOYDS',
                            'solar_analog' : False,
                            'calibsource' : {}
                            }

        params = { 'site_code' : 'F65',
                   'instrument_code' : 'F65-FLOYDS',
                   'spectroscopy' : True,
                   'solar_analog' : False,
                   'calibsource' : {},
                   'exp_count': 1
                   }

        params = configure_defaults(params)

        self.assertEqual(params, expected_params)


class TestMakeconfiguration(TestCase):

    def setUp(self):

        self.target = {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3, 'dec': -0.16}

        self.params_2m0_imaging = configure_defaults({'site_code': 'F65',
                                                      'exp_time': 60.0,
                                                      'exp_count': 12,
                                                      'slot_length': 750,
                                                      'filter_pattern': 'solar',
                                                      'muscat_exp_times':  {'gp_explength': 60,
                                                                            'rp_explength': 30,
                                                                            'ip_explength': 30,
                                                                            'zp_explength': 60,
                                                                            },
                                                      'muscat_sync': True,
                                                      'target': self.target,
                                                      'add_dither': False,
                                                      'constraints': {
                                                          'max_airmass': 2.0,
                                                          'min_lunar_distance': 30.0
                                                       }})
        self.params_2m0_imaging['exp_type'] = 'REPEAT_EXPOSE'
        self.filt_2m0_imaging = build_filter_blocks(self.params_2m0_imaging['filter_pattern'],
                                                    self.params_2m0_imaging['exp_count'],
                                                    self.params_2m0_imaging['exp_type'])

        self.params_1m0_imaging = configure_defaults({'site_code': 'K92',
                                                      'exp_time': 60.0,
                                                      'exp_count': 10,
                                                      'filter_pattern': 'w',
                                                      'target': self.target,
                                                      'add_dither': False,
                                                      'constraints': {
                                                          'max_airmass': 2.0,
                                                          'min_lunar_distance': 30.0
                                                      }})
        self.params_1m0_imaging['exp_type'] = 'EXPOSE'
        self.filt_1m0_imaging = build_filter_blocks(self.params_1m0_imaging['filter_pattern'],
                                                    self.params_1m0_imaging['exp_count'],
                                                    self.params_1m0_imaging['exp_type'])

        self.params_0m4_imaging = configure_defaults({'site_code': 'Z21',
                                                      'exp_time': 90.0,
                                                      'exp_count': 10,
                                                      'filter_pattern': 'w',
                                                      'target': self.target,
                                                      'add_dither': False,
                                                      'constraints': {
                                                          'max_airmass': 2.0,
                                                          'min_lunar_distance': 30.0
                                                      }})
        self.params_0m4_imaging['exp_type'] = 'EXPOSE'
        self.filt_0m4_imaging = build_filter_blocks(self.params_0m4_imaging['filter_pattern'],
                                                    self.params_0m4_imaging['exp_count'],
                                                    self.params_0m4_imaging['exp_type'])

        self.params_2m0_spectroscopy = configure_defaults({'site_code': 'F65',
                                                           'instrument_code': 'F65-FLOYDS',
                                                           'spectroscopy': True,
                                                           'exp_time': 180.0,
                                                           'exp_count': 1,
                                                           'target': self.target,
                                                           'constraints': {
                                                               'max_airmass': 2.0,
                                                               'min_lunar_distance': 30.0
                                                           }})
        self.filt_2m0_spectroscopy = ['slit_6.0as', 1]
        self.maxDiff = None

    def test_2m_imaging(self):

        expected_configuration = {
                          'type': 'REPEAT_EXPOSE',
                          'repeat_duration': 551,
                          'instrument_type': '2M0-SCICAM-MUSCAT',
                          'target': {
                            'type': 'ICRS',
                            'name': 'SA107-684',
                            'ra': 234.3,
                            'dec': -0.16
                          },
                          'constraints': {
                            'max_airmass': 2.0,
                            'min_lunar_distance': 30.0
                          },
                          'acquisition_config': {},
                          'guiding_config': {},
                          'instrument_configs': [{
                              'optical_elements': {'diffuser_g_position': 'out',
                                                   'diffuser_r_position': 'out',
                                                   'diffuser_i_position': 'out',
                                                   'diffuser_z_position': 'out'},
                              'exposure_count': 1,
                              'exposure_time': 60.0,
                              'extra_params': {
                                  'exposure_time_g': 60,
                                  'exposure_time_r': 30,
                                  'exposure_time_i': 30,
                                  'exposure_time_z': 60,
                                  'exposure_mode': 'SYNCHRONOUS'
                              }
                          }]
                        }

        configuration = make_config(self.params_2m0_imaging, self.filt_2m0_imaging)
        self.assertEqual(expected_configuration, configuration)

    def test_1m_imaging(self):

        expected_configuration = {
                              'type': 'EXPOSE',
                              'instrument_type': '1M0-SCICAM-SINISTRO',
                              'target': {
                                'type': 'ICRS',
                                'name': 'SA107-684',
                                'ra': 234.3,
                                'dec': -0.16
                              },
                              'constraints': {
                                'max_airmass': 2.0,
                                'min_lunar_distance': 30.0
                              },
                              'acquisition_config': {},
                              'guiding_config': {},
                              'instrument_configs': [{
                                'exposure_count': 10,
                                'exposure_time': 60.0,
                                'extra_params': {},
                                'optical_elements': {
                                  'filter': 'w'
                                }
                              }]
                            }

        configuration = make_config(self.params_1m0_imaging, self.filt_1m0_imaging)
        self.assertEqual(expected_configuration, configuration)

    def test_0m4_imaging(self):

        expected_configuration = {
                              'type': 'EXPOSE',
                              'instrument_type': '0M4-SCICAM-SBIG',
                              'target': {
                                'type': 'ICRS',
                                'name': 'SA107-684',
                                'ra': 234.3,
                                'dec': -0.16
                              },
                              'constraints': {
                                'max_airmass': 2.0,
                                'min_lunar_distance': 30.0
                              },
                              'acquisition_config': {},
                              'guiding_config': {},
                              'instrument_configs': [{
                                'exposure_count': 10,
                                'exposure_time': 90.0,
                                'extra_params': {},
                                'optical_elements': {
                                  'filter': 'w'
                                }
                              }]
                            }

        configuration = make_config(self.params_0m4_imaging, self.filt_0m4_imaging)

        self.assertEqual(expected_configuration, configuration)

    def test_2m_spectroscopy_spectrum(self):

        expected_configuration = {
                              'type': 'SPECTRUM',
                              'instrument_type': '2M0-FLOYDS-SCICAM',
                              'constraints': {
                                'max_airmass': 2.0,
                                'min_lunar_distance': 30.0
                              },
                              'target': {
                                'type': 'ICRS',
                                'name': 'SA107-684',
                                'ra': 234.3,
                                'dec': -0.16
                              },
                              'acquisition_config': {
                                'mode': 'BRIGHTEST',
                                'exposure_time': 10,
                                'extra_params': {
                                  'acquire_radius': 5.0
                                }
                              },
                              'guiding_config': {
                                'mode': 'ON',
                                'optional': False,
                                'exposure_time': 10
                              },
                              'instrument_configs': [{
                                'exposure_time': 180.0,
                                'exposure_count': 1,
                                'rotator_mode': 'VFLOAT',
                                'optical_elements': {
                                  'slit': 'slit_6.0as'
                                },
                                'extra_params': {}
                              }]
                            }

        configuration = make_spect_config(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)
        self.assertEqual(expected_configuration, configuration)

    def test_2m_spectroscopy_arc(self):

        self.params_2m0_spectroscopy['exp_type'] = 'ARC'

        expected_configuration = {
                          'type': 'ARC',
                          'instrument_type': '2M0-FLOYDS-SCICAM',
                          'constraints': {
                            'max_airmass': 2.0,
                            'min_lunar_distance': 30.0
                          },
                          'target': {
                            'type': 'ICRS',
                            'name': 'SA107-684',
                            'ra': 234.3,
                            'dec': -0.16
                          },
                          'acquisition_config': {
                            'mode': 'BRIGHTEST',
                            'exposure_time': 10,
                            'extra_params': {
                              'acquire_radius': 5.0
                            }
                          },
                          'guiding_config': {
                            'mode': 'ON',
                            'optional': False,
                            'exposure_time': 10
                          },
                          'instrument_configs': [{
                            'exposure_time': 60.0,
                            'exposure_count': 1,
                            'rotator_mode': 'VFLOAT',
                            'optical_elements': {
                              'slit': 'slit_6.0as'
                            },
                            'extra_params': {}
                          }]
                        }

        configuration = make_spect_config(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)
        self.assertEqual(expected_configuration, configuration)

    def test_2m_spectroscopy_arc_multiple_spectra(self):

        self.params_2m0_spectroscopy['exp_type'] = 'ARC'
        self.params_2m0_spectroscopy['exp_count'] = 2

        expected_configuration = {
                          'type': 'ARC',
                          'instrument_type': '2M0-FLOYDS-SCICAM',
                          'constraints': {
                            'max_airmass': 2.0,
                            'min_lunar_distance': 30.0
                          },
                          'target': {
                            'type': 'ICRS',
                            'name': 'SA107-684',
                            'ra': 234.3,
                            'dec': -0.16
                          },
                          'acquisition_config': {
                            'mode': 'BRIGHTEST',
                            'exposure_time': 10,
                            'extra_params': {
                              'acquire_radius': 5.0
                            }
                          },
                          'guiding_config': {
                            'mode': 'ON',
                            'optional': False,
                            'exposure_time': 10
                          },
                          'instrument_configs': [{
                            'exposure_time': 60.0,
                            'exposure_count': 1,
                            'rotator_mode': 'VFLOAT',
                            'optical_elements': {
                              'slit': 'slit_6.0as'
                            },
                            'extra_params': {}
                          }]
                        }

        configuration = make_spect_config(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)
        self.assertEqual(expected_configuration, configuration)

    def test_2m_spectroscopy_lampflat(self):

        self.params_2m0_spectroscopy['exp_type'] = 'LAMP_FLAT'

        expected_configuration = {
                          'type': 'LAMP_FLAT',
                          'instrument_type': '2M0-FLOYDS-SCICAM',
                          'constraints': {
                            'max_airmass': 2.0,
                            'min_lunar_distance': 30.0
                          },
                          'target': {
                            'type': 'ICRS',
                            'name': 'SA107-684',
                            'ra': 234.3,
                            'dec': -0.16
                          },
                          'acquisition_config': {
                            'mode': 'BRIGHTEST',
                            'exposure_time': 10,
                            'extra_params': {
                              'acquire_radius': 5.0
                            }
                          },
                          'guiding_config': {
                            'mode': 'ON',
                            'optional': False,
                            'exposure_time': 10
                          },
                          'instrument_configs': [{
                            'exposure_time': 20.0,
                            'exposure_count': 1,
                            'rotator_mode': 'VFLOAT',
                            'optical_elements': {
                              'slit': 'slit_6.0as'
                            },
                            'extra_params': {}
                          }]
                        }

        configuration = make_spect_config(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)
        self.assertEqual(expected_configuration, configuration)

    def test_2m_spectroscopy_lampflat_multiple_spectra(self):

        self.params_2m0_spectroscopy['exp_type'] = 'LAMP_FLAT'
        self.params_2m0_spectroscopy['exp_count'] = 42

        expected_configuration = {
                                  'type': 'LAMP_FLAT',
                                  'instrument_type': '2M0-FLOYDS-SCICAM',
                                  'constraints': {
                                    'max_airmass': 2.0,
                                    'min_lunar_distance': 30.0
                                  },
                                  'target': {
                                    'type': 'ICRS',
                                    'name': 'SA107-684',
                                    'ra': 234.3,
                                    'dec': -0.16
                                  },
                                  'acquisition_config': {
                                    'mode': 'BRIGHTEST',
                                    'exposure_time': 10,
                                    'extra_params': {
                                      'acquire_radius': 5.0
                                    }
                                  },
                                  'guiding_config': {
                                    'mode': 'ON',
                                    'optional': False,
                                    'exposure_time': 10
                                  },
                                  'instrument_configs': [{
                                    'exposure_time': 20.0,
                                    'exposure_count': 1,
                                    'rotator_mode': 'VFLOAT',
                                    'optical_elements': {
                                      'slit': 'slit_6.0as'
                                    },
                                'extra_params': {}
                                  }]
                                }

        configuration = make_spect_config(self.params_2m0_spectroscopy, self.filt_2m0_spectroscopy)

        self.assertEqual(expected_configuration, configuration)

    def test_2m_spectroscopy_spectrum_different_slit(self):

        expected_configuration = {
                                  'type': 'SPECTRUM',
                                  'instrument_type': '2M0-FLOYDS-SCICAM',
                                  'constraints': {
                                    'max_airmass': 2.0,
                                    'min_lunar_distance': 30.0
                                  },
                                  'target': {
                                    'type': 'ICRS',
                                    'name': 'SA107-684',
                                    'ra': 234.3,
                                    'dec': -0.16
                                  },
                                  'acquisition_config': {
                                    'mode': 'BRIGHTEST',
                                    'exposure_time': 10,
                                    'extra_params': {
                                      'acquire_radius': 5.0
                                    }
                                  },
                                  'guiding_config': {
                                    'mode': 'ON',
                                    'optional': False,
                                    'exposure_time': 10
                                  },
                                  'instrument_configs': [{
                                    'exposure_time': 180.0,
                                    'exposure_count': 1,
                                    'rotator_mode': 'VFLOAT',
                                    'optical_elements': {
                                      'slit': 'slit_2.0as'
                                    },
                                    'extra_params': {}
                                  }]
                                }

        configuration = make_spect_config(self.params_2m0_spectroscopy, ['slit_2.0as', 1])

        self.assertEqual(expected_configuration, configuration)


class TestGetExposureBins(TestCase):

    def setUp(self):
        b_params = {'provisional_name': 'N999r0q',
                    'abs_mag': 21.0,
                    'slope': 0.15,
                    'epochofel': datetime(2015, 3, 19, 00, 00, 00),
                    'meananom': 325.2636,
                    'argofperih': 85.19251,
                    'longascnode': 147.81325,
                    'orbinc': 8.34739,
                    'eccentricity': 0.1896865,
                    'meandist': 1.2176312,
                    'source_type': 'U',
                    'elements_type': 'MPC_MINOR_PLANET',
                    'active': True,
                    'origin': 'M',
                    }
        self.body, created = Body.objects.get_or_create(**b_params)
        self.body_elements = model_to_dict(self.body)
        self.body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        self.body_elements['current_name'] = self.body.current_name()
        self.body_elements['v_mag'] = 16.6777676

        self.params_1m0_imaging = configure_defaults({ 'site_code': 'K92',
                                                       'exp_time': 60.0,
                                                       'exp_count': 10,
                                                       'slot_length': 16,
                                                       'filter_pattern': 'w',
                                                       'target': make_moving_target(self.body_elements, 0.5),
                                                       'add_dither': False,
                                                       'speed': 10,
                                                       'constraints': {
                                                         'max_airmass': 2.0,
                                                         'min_lunar_distance': 30.0
                                                       }})

        self.params_2m0_imaging = configure_defaults({'site_code': 'F65',
                                                      'exp_time': 60.0,
                                                      'exp_count': 10,
                                                      'filter_pattern': 'solar',
                                                      'target': make_moving_target(self.body_elements, 0.5),
                                                      'muscat_exp_times': {'gp_explength': 60,
                                                                           'rp_explength': 30,
                                                                           'ip_explength': 30,
                                                                           'zp_explength': 60,
                                                                           },
                                                      'muscat_sync': True,
                                                      'add_dither': False,
                                                      'constraints': {
                                                        'max_airmass': 2.0,
                                                        'min_lunar_distance': 30.0
                                                      }})

    def test_exposure_bins_long_block(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 145
        params['speed'] = 25

        expected_exp_list = [21, 21, 21, 21, 21, 20, 20]
        self.assertEqual(sum(expected_exp_list), 145)

        exp_count_list = get_exposure_bins(params)

        self.assertEqual(expected_exp_list, exp_count_list)

    def test_exposure_bins_binned(self):
        params = self.params_1m0_imaging
        params['exp_time'] = 15
        params['exp_count'] = 55
        params['speed'] = 18.43
        params['bin_mode'] = '2k_2x2'

        expected_exp_list = [28, 27]
        self.assertEqual(sum(expected_exp_list), 55)

        exp_count_list = get_exposure_bins(params)

        self.assertEqual(expected_exp_list, exp_count_list)

    def test_exposure_bins_short_block(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 10
        params['speed'] = 25

        expected_exp_list = [10]

        exp_count_list = get_exposure_bins(params)

        self.assertEqual(expected_exp_list, exp_count_list)

    def test_exposure_bin_slow_block(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 100
        params['speed'] = 2

        expected_exp_list = [100]

        exp_count_list = get_exposure_bins(params)

        self.assertEqual(expected_exp_list, exp_count_list)

    def test_exposure_bin_full_tracking(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 100
        params['slot_length'] = 147
        params['fractional_rate'] = 1
        params['speed'] = 24

        expected_exp_list = None

        exp_count_list = get_exposure_bins(params)

        self.assertEqual(expected_exp_list, exp_count_list)

    def test_exposure_bin_2m0(self):
        params = self.params_2m0_imaging
        params['exp_count'] = 25
        params['speed'] = 25

        expected_exp_list = [9, 8, 8]

        exp_count_list = get_exposure_bins(params)

        self.assertEqual(expected_exp_list, exp_count_list)


class TestSplitInstConfigs(TestCase):

    def setUp(self):
        self.inst_config = {'exposure_count': 1,
                            'exposure_time': 60.0,
                            'optical_elements': {'filter': 'w'},
                            'extra_params': {}
                            }

    def test_split_high_exposure_count(self):
        exp_bins = [21, 21, 21, 21, 21, 20, 20]
        inst_configs = [self.inst_config]
        inst_configs[0]['exposure_count'] = 145

        inst_list = split_inst_configs(exp_bins, inst_configs)

        self.assertEqual(len(inst_list), len(exp_bins))
        for inst in inst_list:
            self.assertEqual(len(inst), 1)

    def test_split_filters(self):
        exp_bins = [22, 22, 21, 21]
        inst_configs = []
        ic = self.inst_config
        filter_list = ['V', 'B', 'R', 'I']
        for f in filter_list:
            ic['optical_elements']['filter'] = f
            inst_configs.append(deepcopy(ic))

        inst_list = split_inst_configs(exp_bins, inst_configs)

        expected_first_filter = ['V', 'R', 'V', 'B']

        self.assertEqual(len(inst_list), len(exp_bins))
        for k, inst in enumerate(inst_list):
            self.assertEqual(len(inst), 4)
            self.assertEqual(inst[0]['optical_elements']['filter'], expected_first_filter[k])

    def test_split_doublefilters(self):
        exp_bins = [22, 22, 21, 21]
        inst_configs = []
        ic = self.inst_config
        ic['exposure_count'] = 2
        filter_list = ['V', 'B', 'R', 'I']
        for f in filter_list:
            ic['optical_elements']['filter'] = f
            inst_configs.append(deepcopy(ic))

        inst_list = split_inst_configs(exp_bins, inst_configs)

        expected_first_filter = ['V', 'I', 'R', 'B']

        self.assertEqual(len(inst_list), len(exp_bins))
        for k, inst in enumerate(inst_list):
            self.assertEqual(len(inst), 4)
            self.assertEqual(inst[0]['optical_elements']['filter'], expected_first_filter[k])

    def test_split_longfilters(self):
        exp_bins = [22, 22, 21, 21, 21]
        inst_configs = []
        ic = self.inst_config
        ic['exposure_count'] = 25
        filter_list = ['V', 'B', 'R', 'I']
        for f in filter_list:
            ic['optical_elements']['filter'] = f
            inst_configs.append(deepcopy(ic))

        inst_list = split_inst_configs(exp_bins, inst_configs)

        expected_first_filter = ['V', 'B', 'R', 'I', 'V']

        self.assertEqual(len(inst_list), len(exp_bins))
        for k, inst in enumerate(inst_list):
            self.assertEqual(len(inst), 1)
            self.assertEqual(inst[0]['optical_elements']['filter'], expected_first_filter[k])


class TestSplitConfigs(TestCase):

    def setUp(self):
        b_params = {'provisional_name': 'N999r0q',
                    'abs_mag': 21.0,
                    'slope': 0.15,
                    'epochofel': datetime(2015, 3, 19, 00, 00, 00),
                    'meananom': 325.2636,
                    'argofperih': 85.19251,
                    'longascnode': 147.81325,
                    'orbinc': 8.34739,
                    'eccentricity': 0.1896865,
                    'meandist': 1.2176312,
                    'source_type': 'U',
                    'elements_type': 'MPC_MINOR_PLANET',
                    'active': True,
                    'origin': 'M',
                    }
        self.body, created = Body.objects.get_or_create(**b_params)
        self.body_elements = model_to_dict(self.body)
        self.body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        self.body_elements['current_name'] = self.body.current_name()
        self.body_elements['v_mag'] = 16.6777676

        self.params_1m0_imaging = configure_defaults({ 'site_code': 'K92',
                                                       'exp_time': 60.0,
                                                       'exp_count': 20,
                                                       'slot_length': 26*60,
                                                       'filter_pattern': 'w',
                                                       'target': make_moving_target(self.body_elements, 0.5),
                                                       'add_dither': False,
                                                       'speed': 25,
                                                       'bin_mode': '2k_2x2',
                                                       'constraints': {
                                                         'max_airmass': 2.0,
                                                         'min_lunar_distance': 30.0
                                                       }})

        self.params_2m0_imaging = configure_defaults({'site_code': 'F65',
                                                      'exp_time': 60.0,
                                                      'exp_count': 10,
                                                      'filter_pattern': 'solar',
                                                      'target': make_moving_target(self.body_elements, 0.5),
                                                      'muscat_exp_times': {'gp_explength': 60,
                                                                           'rp_explength': 30,
                                                                           'ip_explength': 30,
                                                                           'zp_explength': 60,
                                                                           },
                                                      'muscat_sync': True,
                                                      'add_dither': False,
                                                      'speed': 25,
                                                      'constraints': {
                                                        'max_airmass': 2.0,
                                                        'min_lunar_distance': 30.0
                                                      }})

        self.configs_1m_repeatexpose = [{'type': 'REPEAT_EXPOSE',
                                         'instrument_type': '1M0-SCICAM-SINISTRO',
                                         'target': {'name': 'N999r0q',
                                                    'type': 'ORBITAL_ELEMENTS',
                                                    'scheme': 'MPC_MINOR_PLANET',
                                                    'epochofel': 57100.0,
                                                    'orbinc': 8.34739,
                                                    'longascnode': 147.81325,
                                                    'argofperih': 85.19251,
                                                    'eccentricity': 0.1896865,
                                                    'extra_params': {'v_magnitude': 16.68,
                                                                     'fractional_ephemeris_rate': 0.5},
                                                    'meandist': 1.2176312,
                                                    'meananom': 325.2636},
                                         'constraints': {'max_airmass': 2.0,
                                                         'min_lunar_distance': 30.0},
                                         'acquisition_config': {},
                                         'guiding_config': {},
                                         'instrument_configs': [{'exposure_count': 1,
                                                                 'exposure_time': 60.0,
                                                                 'optical_elements': {'filter': 'w'},
                                                                 'mode': 'central_2k_2x2',
                                                                 'extra_params': {}}],
                                         'repeat_duration': 7091.0}
                                        ]

        self.configs_2m_muscat = [{'type': 'EXPOSE',
                                   'instrument_type': '2M0-SCICAM-MUSCAT',
                                   'target': {'name': 'N999r0q',
                                              'type': 'ORBITAL_ELEMENTS',
                                              'scheme': 'MPC_MINOR_PLANET',
                                              'epochofel': 57100.0,
                                              'orbinc': 8.34739,
                                              'longascnode': 147.81325,
                                              'argofperih': 85.19251,
                                              'eccentricity': 0.1896865,
                                              'extra_params': {'v_magnitude': 16.68,
                                                               'fractional_ephemeris_rate': 0.5},
                                              'meandist': 1.2176312,
                                              'meananom': 325.2636},
                                   'constraints': {'max_airmass': 2.0,
                                                   'min_lunar_distance': 30.0},
                                   'acquisition_config': {},
                                   'guiding_config': {},
                                   'instrument_configs': [{'exposure_count': 10,
                                                           'exposure_time': 60.0,
                                                           'optical_elements': {'diffuser_g_position': 'out',
                                                                                'diffuser_r_position': 'out',
                                                                                'diffuser_i_position': 'out',
                                                                                'diffuser_z_position': 'out'},
                                                           'extra_params': {'exposure_time_g': 60,
                                                                            'exposure_time_r': 35,
                                                                            'exposure_time_i': 35,
                                                                            'exposure_time_z': 60,
                                                                            'exposure_mode': 'ASYNCHRONOUS'}
                                                           }]
                                   }]

    def test_split_single_config(self):
        params = self.params_1m0_imaging
        params['speed'] = 5

        new_configs = split_configs(self.configs_1m_repeatexpose, params)

        self.assertEqual(new_configs, self.configs_1m_repeatexpose)

    def test_split_long_config(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 67

        expected_num_configs = 5

        new_configs = split_configs(self.configs_1m_repeatexpose, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        self.assertEqual(new_configs[0]['instrument_configs'], self.configs_1m_repeatexpose[0]['instrument_configs'])
        self.assertEqual(new_configs[0]['repeat_duration'], 1482)
        self.assertEqual(new_configs[4]['repeat_duration'], 1376)

    def test_split_veryfast_config(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 12
        params['speed'] = 350

        expected_num_configs = 12

        new_configs = split_configs(self.configs_1m_repeatexpose, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        self.assertEqual(new_configs[0]['instrument_configs'], self.configs_1m_repeatexpose[0]['instrument_configs'])
        self.assertEqual(new_configs[0]['repeat_duration'], ceil(self.configs_1m_repeatexpose[0]['repeat_duration'] / 12))
        self.assertEqual(new_configs[4]['repeat_duration'], ceil(self.configs_1m_repeatexpose[0]['repeat_duration'] / 12))

    def test_split_short_config(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 7
        params['speed'] = 54

        configs = self.configs_1m_repeatexpose
        configs[0]['type'] = 'EXPOSE'
        del configs[0]['repeat_duration']
        configs[0]['instrument_configs'][0]['exposure_count'] = params['exp_count']

        expected_num_configs = 2

        new_configs = split_configs(configs, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        for key in new_configs[0]['instrument_configs'][0]:
            if key != 'exposure_count':
                self.assertEqual(new_configs[0]['instrument_configs'][0][key], configs[0]['instrument_configs'][0][key])
            else:
                self.assertNotEqual(new_configs[0]['instrument_configs'][0][key],
                                    configs[0]['instrument_configs'][0][key])
        self.assertNotEqual(new_configs[0]['instrument_configs'][0]['exposure_count'],
                            new_configs[1]['instrument_configs'][0]['exposure_count'])

    def test_split_multifilter_config(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 62
        params['speed'] = 25

        configs = self.configs_1m_repeatexpose
        inst_config = configs[0]['instrument_configs'][0]
        filter_list = ['V', 'R', 'I']
        configs[0]['instrument_configs'] = []
        for filt in filter_list:
            inst_config['optical_elements']['filter'] = filt
            configs[0]['instrument_configs'].append(deepcopy(inst_config))

        expected_num_configs = 5

        new_configs = split_configs(configs, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        self.assertEqual(new_configs[0]['instrument_configs'], configs[0]['instrument_configs'])
        # filter cycles and aren't repeated in this case.
        self.assertNotEqual(new_configs[2]['instrument_configs'], configs[0]['instrument_configs'])
        self.assertEqual(new_configs[0]['repeat_duration'], 1487)
        self.assertEqual(new_configs[4]['repeat_duration'], 1373)

    def test_split_longfilter_config(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 45
        params['speed'] = 25

        configs = self.configs_1m_repeatexpose
        inst_config = configs[0]['instrument_configs'][0]
        filter_list = ['V', 'R', 'I']
        configs[0]['instrument_configs'] = []
        for filt in filter_list:
            inst_config['optical_elements']['filter'] = filt
            inst_config['exposure_count'] = 15
            configs[0]['instrument_configs'].append(deepcopy(inst_config))

        expected_num_configs = 4

        new_configs = split_configs(configs, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        self.assertEqual(new_configs[0]['instrument_configs'][0], configs[0]['instrument_configs'][0])
        self.assertEqual(new_configs[0]['repeat_duration'], 1891)
        self.assertEqual(new_configs[3]['repeat_duration'], 1734)

    def test_split_exposefilter_config(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 9
        params['speed'] = 150

        configs = self.configs_1m_repeatexpose
        configs[0]['type'] = 'EXPOSE'
        del configs[0]['repeat_duration']
        inst_config = configs[0]['instrument_configs'][0]
        filter_list = ['V', 'R', 'I']
        configs[0]['instrument_configs'] = []
        for filt in filter_list:
            inst_config['optical_elements']['filter'] = filt
            inst_config['exposure_count'] = 3
            configs[0]['instrument_configs'].append(deepcopy(inst_config))

        expected_num_configs = 4

        new_configs = split_configs(configs, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        self.assertEqual(new_configs[0]['instrument_configs'][0], configs[0]['instrument_configs'][0])
        self.assertNotEqual(new_configs[2]['instrument_configs'][0], configs[0]['instrument_configs'][2])
        self.assertEqual(new_configs[2]['instrument_configs'][0]['exposure_count'], 2)
        self.assertEqual(new_configs[3]['instrument_configs'][0]['optical_elements']['filter'], 'V')

    def test_split_muscat_config(self):
        params = self.params_2m0_imaging

        configs = self.configs_2m_muscat

        expected_num_configs = 2

        new_configs = split_configs(configs, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        self.assertEqual(new_configs[0]['instrument_configs'][0]['exposure_count'], 5)

    def test_split_longmuscat_config(self):
        params = self.params_2m0_imaging
        params['exp_count'] = 65

        configs = self.configs_2m_muscat
        configs[0]['type'] = 'REPEAT_EXPOSE'
        configs[0]['repeat_duration'] = 65 * 80
        configs[0]['instrument_configs'][0]['exposure_count'] = 1

        expected_num_configs = 7

        new_configs = split_configs(configs, params)

        self.assertEqual(len(new_configs), expected_num_configs)
        for cfg in new_configs:
            self.assertEqual(cfg['instrument_configs'][0], configs[0]['instrument_configs'][0])
            self.assertLess(cfg['repeat_duration'], configs[0]['repeat_duration'])


class TestMakeconfigurations(TestCase):

    def setUp(self):
        self.target = {'type': 'ICRS', 'name': 'SA107-684', 'ra': 234.3, 'dec': -0.16}

        b_params = {'provisional_name': 'N999r0q',
                    'abs_mag': 21.0,
                    'slope': 0.15,
                    'epochofel': datetime(2015, 3, 19, 00, 00, 00),
                    'meananom': 325.2636,
                    'argofperih': 85.19251,
                    'longascnode': 147.81325,
                    'orbinc': 8.34739,
                    'eccentricity': 0.1896865,
                    'meandist': 1.2176312,
                    'source_type': 'U',
                    'elements_type': 'MPC_MINOR_PLANET',
                    'active': True,
                    'origin': 'M',
                    }
        self.body, created = Body.objects.get_or_create(**b_params)
        self.body_elements = model_to_dict(self.body)
        self.body_elements['epochofel_mjd'] = self.body.epochofel_mjd()
        self.body_elements['current_name'] = self.body.current_name()
        self.body_elements['v_mag'] = 16.6777676

        self.params_2m0_imaging = configure_defaults({'site_code': 'F65',
                                                      'exp_time': 60.0,
                                                      'exp_count': 10,
                                                      'filter_pattern': 'solar',
                                                      'target': self.target,
                                                      'muscat_exp_times': {'gp_explength': 60,
                                                                           'rp_explength': 30,
                                                                           'ip_explength': 30,
                                                                           'zp_explength': 60,
                                                                           },
                                                      'muscat_sync': True,
                                                      'add_dither': False,
                                                      'constraints': {
                                                        'max_airmass': 2.0,
                                                        'min_lunar_distance': 30.0
                                                      }})

        self.params_1m0_imaging = configure_defaults({ 'site_code': 'K92',
                                                       'exp_time': 60.0,
                                                       'exp_count': 10,
                                                       'filter_pattern': 'w',
                                                       'target': self.target,
                                                       'add_dither': False,
                                                       'constraints': {
                                                         'max_airmass': 2.0,
                                                         'min_lunar_distance': 30.0
                                                       }})

        self.params_0m4_imaging = configure_defaults({ 'site_code': 'Z21',
                                                       'exp_time': 90.0,
                                                       'exp_count': 18,
                                                       'slot_length': 220,
                                                       'filter_pattern': 'w',
                                                       'target': self.target,
                                                       'add_dither': False,
                                                       'constraints': {
                                                         'max_airmass': 2.0,
                                                         'min_lunar_distance': 30.0
                                                       }})

        self.params_2m0_spectroscopy = configure_defaults({ 'site_code': 'F65',
                                                            'instrument_code' : 'F65-FLOYDS',
                                                            'spectroscopy' : True,
                                                            'exp_time' : 180.0,
                                                            'exp_count' : 1,
                                                            'filter_pattern' : 'slit_6.0as',
                                                            'target' : self.target,
                                                            'constraints': {
                                                              'max_airmass': 2.0,
                                                              'min_lunar_distance': 30.0
                                                            }})
        self.filt_2m0_spectroscopy = ['slit_6.0as', ]

    def test_2m_imaging(self):

        expected_num_configurations = 1
        expected_type = 'EXPOSE'

        configurations = make_configs(self.params_2m0_imaging)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

    def test_1m_imaging(self):

        expected_num_configurations = 1
        expected_type = 'EXPOSE'

        configurations = make_configs(self.params_1m0_imaging)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

    def test_1m_longblock_imaging(self):
        params = self.params_1m0_imaging
        params['exp_count'] = 65
        params['slot_length'] = 120*60
        params['speed'] = 25
        params['target'] = make_moving_target(self.body_elements, 0.5)

        expected_num_configurations = 4
        expected_type = 'REPEAT_EXPOSE'

        configurations = make_configs(params)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

    def test_1m_dithering(self):

        expected_num_configurations = 1
        expected_type = 'EXPOSE'
        expected_num_inst_configurations = 10
        expected_exp_num = 1
        params = self.params_1m0_imaging
        params['dither_distance'] = 10
        params['add_dither'] = True

        configurations = make_configs(params)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

        inst_configs = configurations[0]['instrument_configs']
        self.assertEqual(expected_num_inst_configurations, len(inst_configs))
        self.assertEqual(inst_configs[0]['exposure_count'], expected_exp_num)
        self.assertEqual(inst_configs[0]['extra_params'], {'offset_ra': 0.0, 'offset_dec': 0.0})
        self.assertEqual(inst_configs[6]['extra_params'], {'offset_ra': -10.0, 'offset_dec': -10.0})

    def test_multifilter_dithering(self):

        expected_num_configurations = 1
        expected_type = 'EXPOSE'
        expected_num_inst_configurations = 10
        expected_exp_num = 1
        params = self.params_1m0_imaging
        params['dither_distance'] = 10
        params['add_dither'] = True
        params['filter_pattern'] = 'w,r'
        params['exp_count'] = 10

        configurations = make_configs(params)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

        inst_configs = configurations[0]['instrument_configs']
        self.assertEqual(expected_num_inst_configurations, len(inst_configs))
        self.assertEqual(inst_configs[0]['exposure_count'], expected_exp_num)
        self.assertEqual(inst_configs[0]['extra_params'], {'offset_ra': 0.0, 'offset_dec': 0.0})
        self.assertEqual(inst_configs[6]['extra_params'], {'offset_ra': -10.0, 'offset_dec': -10.0})
        self.assertEqual(inst_configs[0]['optical_elements']['filter'], 'w')
        self.assertEqual(inst_configs[1]['optical_elements']['filter'], 'r')
        self.assertEqual(inst_configs[2]['optical_elements']['filter'], 'w')

    def test_longblock_dithering(self):

        expected_num_configurations = 5
        expected_type = 'EXPOSE'
        expected_num_inst_configurations = 20
        expected_exp_num = 1
        params = self.params_1m0_imaging
        params['dither_distance'] = 20
        params['add_dither'] = True
        params['exp_count'] = 100
        params['target'] = make_moving_target(self.body_elements, 0.5)
        params['speed'] = 25

        configurations = make_configs(params)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

        inst_configs0 = configurations[0]['instrument_configs']
        inst_configs1 = configurations[1]['instrument_configs']
        inst_configs4 = configurations[4]['instrument_configs']

        self.assertEqual(expected_num_inst_configurations, len(inst_configs0))
        self.assertEqual(inst_configs0[0]['exposure_count'], expected_exp_num)
        self.assertEqual(inst_configs0[0]['extra_params'], {'offset_ra': 0.0, 'offset_dec': 0.0})
        self.assertEqual(inst_configs0[6]['extra_params'], {'offset_ra': -20.0, 'offset_dec': -20.0})
        self.assertEqual(inst_configs1[10]['extra_params'], {'offset_ra': 60.0, 'offset_dec': 60.0})
        self.assertEqual(inst_configs4[11]['extra_params'], {'offset_ra': 20.0, 'offset_dec': 0.0})

    def test_muscat_dithering(self):

        expected_num_configurations = 1
        expected_type = 'EXPOSE'
        expected_num_inst_configurations = 10
        expected_exp_num = 1
        params = self.params_2m0_imaging
        params['dither_distance'] = 10
        params['add_dither'] = True
        params['exp_count'] = 10

        configurations = make_configs(params)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

        inst_configs = configurations[0]['instrument_configs']
        self.assertEqual(expected_num_inst_configurations, len(inst_configs))
        self.assertEqual(inst_configs[0]['exposure_count'], expected_exp_num)
        self.assertEqual(inst_configs[0]['extra_params']['offset_ra'], 0.0)
        self.assertEqual(inst_configs[0]['extra_params']['offset_dec'], 0.0)
        self.assertEqual(inst_configs[0]['extra_params']['exposure_mode'], 'SYNCHRONOUS')
        self.assertEqual(inst_configs[0]['extra_params']['exposure_time_g'], 60)
        self.assertEqual(inst_configs[6]['extra_params']['offset_ra'], -10.0)
        self.assertEqual(inst_configs[6]['extra_params']['offset_dec'], -10.0)

    def test_0m4_imaging(self):

        expected_num_configurations = 1
        expected_type = 'REPEAT_EXPOSE'

        configurations = make_configs(self.params_0m4_imaging)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

    def test_2m_spectroscopy_nocalibs(self):

        expected_num_configurations = 1
        expected_type = 'SPECTRUM'

        configurations = make_configs(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])

    def test_2m_spectroscopy_calibs_before(self):

        self.params_2m0_spectroscopy['calibs'] = 'before'
        expected_num_configurations = 3

        configurations = make_configs(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual('LAMP_FLAT', configurations[0]['type'])
        self.assertEqual('ARC', configurations[1]['type'])
        self.assertEqual('SPECTRUM', configurations[2]['type'])

    def test_2m_spectroscopy_calibs_after(self):

        self.params_2m0_spectroscopy['calibs'] = 'AFTER'
        expected_num_configurations = 3

        configurations = make_configs(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual('LAMP_FLAT', configurations[2]['type'])
        self.assertEqual('ARC', configurations[1]['type'])
        self.assertEqual('SPECTRUM', configurations[0]['type'])

    def test_2m_spectroscopy_calibs_both(self):

        self.params_2m0_spectroscopy['calibs'] = 'BoTh'
        expected_num_configurations = 5

        configurations = make_configs(self.params_2m0_spectroscopy)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual('LAMP_FLAT', configurations[0]['type'])
        self.assertEqual('ARC', configurations[1]['type'])
        self.assertEqual('SPECTRUM', configurations[2]['type'])
        self.assertEqual('ARC', configurations[3]['type'])
        self.assertEqual('LAMP_FLAT', configurations[4]['type'])

    def test_2m_spectroscopy_nocalibs_6as_slit(self):

        expected_num_configurations = 1
        expected_type = 'SPECTRUM'
        expected_slit = 'slit_6.0as'

        params_2m0_spectroscopy = self.params_2m0_spectroscopy
        params_2m0_spectroscopy['filter_pattern'] = 'slit_6.0as'
        configurations = make_configs(params_2m0_spectroscopy)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])
        self.assertEqual(expected_slit, configurations[0]['instrument_configs'][0]['optical_elements']['slit'])

    def test_2m_spectroscopy_nocalibs_1p6as_slit(self):

        expected_num_configurations = 1
        expected_type = 'SPECTRUM'
        expected_slit = 'slit_1.6as'

        params_2m0_spectroscopy = self.params_2m0_spectroscopy
        params_2m0_spectroscopy['filter_pattern'] = 'slit_1.6as'
        configurations = make_configs(params_2m0_spectroscopy)

        self.assertEqual(expected_num_configurations, len(configurations))
        self.assertEqual(expected_type, configurations[0]['type'])
        self.assertEqual(expected_slit, configurations[0]['instrument_configs'][0]['optical_elements']['slit'])


class TestMakeCadence(TestCase):

    def setUp(self):

        self.elements = {
                  'name': '481394',
                  'type': 'ORBITAL_ELEMENTS',
                  'scheme': 'MPC_MINOR_PLANET',
                  'epochofel': 58772.0,
                  'orbinc': 5.86644,
                  'longascnode': 228.05483,
                  'argofperih': 305.65602,
                  'meandist': 0.9493097,
                  'eccentricity': 0.2805184,
                  'meananom': 236.20921
                }
        self.params = { 'utc_date' : datetime(2017, 8, 20, 0, 0),
                        'start_time' : datetime(2017, 8, 20, 8, 40),
                        'end_time' : datetime(2017, 8, 20, 19, 40),
                        'period' : 2.0,
                        'jitter' : 0.25,
                        'group_name' : "3122_Q59-20170815",
                        'proposal_id' : 'LCOSchedulerTest',
                        'user_id' : 'tlister@lcogt.net',
                        'exp_type' : 'EXPOSE',
                        'exp_count' : 105,
                        'exp_time' : 20.0,
                        'binning' : 2,
                        'instrument' : '0M4-SCICAM-SBIG',
                        'filter_pattern' : 'w',
                        'site' : 'COJ',
                        'pondtelescope' : '0m4a',
                        'site_code' : 'Q59',
                        'target' : self.elements,
                        'add_dither': False,
                        'constraints' : {'max_airmass': 2.0, 'min_lunar_distance': 15}
                        }
        self.ipp_value = 1.0

        configurations = make_configs(self.params)
        self.request = {  'location' : { 'site' : self.params['site'].lower(),
                                         'telescope_class' : self.params['pondtelescope'][0:3]
                                       },
                          'configurations' : configurations,
                          'windows' : [{'start' : datetime.strftime(self.params['start_time'], '%Y-%m-%dT%H:%M:%SZ'),
                                        'end'   : datetime.strftime(self.params['end_time'], '%Y-%m-%dT%H:%M:%SZ')
                                        }]
                        }

        self.maxDiff = None

    @patch('astrometrics.sources_subs.expand_cadence', mock_expand_cadence)
    def test_cadence_wrapper(self):
        inst_confs = [{u'bin_x': 1,
                       u'bin_y': 1,
                       u'exposure_count': 10,
                       u'exposure_time': 2.0,
                       'optical_elements': {'filter': 'w'}
                       }]
        configs = [{u'instrument_type': u'0M4-SCICAM-SBIG',
                    u'priority': 1,
                    u'type': u'EXPOSE',
                    u'target': self.elements,
                    u'constraints': {u'max_airmass': 2.0,
                                     'min_lunar_distance': 30.0},
                    'instrument_configs' : inst_confs
                    }]

        windows = [{'start': '2019-11-01T00:00:00Z',
                    'end': '2019-11-01T00:30:00Z'},
                   {'start': '2019-11-01T01:30:00Z',
                    'end': '2019-11-01T02:30:00Z'},
                   {'start': '2019-11-01T03:30:00Z',
                    'end': '2019-11-01T04:30:00Z'}]
        requests = []
        for window in windows:
            requests.append({
                    'location': {'site': 'ogg', 'telescope_class': '0m4'},
                    'configurations': configs,
                    'windows': [window],
                })
        expected = {
                     u'name': u'3122_Q59-20170815',
                     u'ipp_value': 1.0,
                     u'observation_type': u'NORMAL',
                     u'operator': u'MANY',
                     u'proposal': u'LCOSchedulerTest',
                     u'requests': requests,
                }

        self.request['location']['site'] = 'ogg'
        self.request['configurations'][0]['exposure_count'] = 10
        self.request['configurations'][0]['exposure_time'] = 2.0
        self.request['configurations'][0]['max_airmass'] = 2.0

        params = self.params
        params['start_time'] = datetime(2019, 11, 1, 0, 0, 0)
        params['end_time'] = datetime(2019, 11, 2, 0, 0, 0)
        params['jitter'] = 1.0
        params['period'] = 2
        ur = make_cadence(self.request, params, self.ipp_value)
        for key in expected.keys():
            if key == 'requests':
                for i, exrequest in enumerate(expected['requests']):
                    self.assertEqual(exrequest, ur['requests'][i])
            else:
                self.assertEqual(expected[key], ur[key])


class TestMakeTarget(TestCase):

    def setUp(self):
        self.params = { 'utc_date' : datetime(2017, 8, 20, 0, 0),
                        'start_time' : datetime(2017, 8, 20, 8, 40),
                        'end_time' : datetime(2017, 8, 20, 19, 40),
                        'period' : 2.0,
                        'jitter' : 0.25,
                        'group_name' : "3122_Q59-20170815" + "+solstd",
                        'proposal_id' : 'LCOSchedulerTest',
                        'user_id' : 'tlister@lcogt.net',
                        'exp_type' : 'EXPOSE',
                        'exp_count' : 105,
                        'exp_time' : 20.0,
                        'binning' : 2,
                        'instrument' : '0M4-SCICAM-SBIG',
                        'filter_pattern' : 'w',
                        'site' : 'COJ',
                        'pondtelescope' : '0m4a',
                        'site_code' : 'Q59',
                        'source_id' : 'LTT9999',
                        'ra_deg'  : 359.07507666666663,
                        'dec_deg' : 4.626489444444445,
                        'constraints' : {'max_airmass': 2.0, 'min_lunar_distance': 15}
                        }
        self.ipp_value = 1.0

    def test_nopm(self):
        expected_target = { 'type' : 'ICRS',
                            'name' : 'LTT9999',
                            'ra'   : self.params['ra_deg'],
                            'dec'  : self.params['dec_deg'],
                            'extra_params' : {}
                          }
        target = make_target(self.params)

        self.assertEqual(expected_target, target)

    def test_pm_no_parallax(self):
        expected_target = { 'type' : 'ICRS',
                            'name' : 'LTT9999',
                            'ra'   : self.params['ra_deg'],
                            'dec'  : self.params['dec_deg'],
                            'proper_motion_ra': 10.0,
                            'proper_motion_dec': -10.0,
                            'extra_params' : {}
                          }

        params_pm = deepcopy(self.params)
        params_pm['pm_ra'] = 10.0
        params_pm['pm_dec'] = -10.0

        target = make_target(params_pm)

        self.assertEqual(expected_target, target)

    def test_pm_parallax_vmag(self):
        expected_target = { 'type' : 'ICRS',
                            'name' : 'LTT9999',
                            'ra'   : self.params['ra_deg'],
                            'dec'  : self.params['dec_deg'],
                            'proper_motion_ra': 10.0,
                            'proper_motion_dec': -10.0,
                            'parallax' : 7.9985,
                            'extra_params' : { 'v_magnitude' : 9.08}
                          }

        params_pm = deepcopy(self.params)
        params_pm['pm_ra'] = 10.0
        params_pm['pm_dec'] = -10.0
        params_pm['parallax'] = 7.9985
        params_pm['vmag'] = 9.08

        target = make_target(params_pm)

        self.assertEqual(expected_target, target)


class TestFetchTaxonomyData(TestCase):

    def setUp(self):
        # Read and make soup from the stored, partial version of the PDS Taxonomy Database
        self.test_taxonomy_page = os.path.join('astrometrics', 'tests', 'test_taxonomy_page.dat')

        # Read and make soup from the stored, partial version of the SDSS Taxonomy Database
        self.test_sdss_page = os.path.join('astrometrics', 'tests', 'test_sdss_tax_page.dat')

    def test_basics(self):
        expected_length = 33
        targets = fetch_taxonomy_page(self.test_taxonomy_page)

        self.assertEqual(expected_length, len(targets))

    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_page_down(self):
        expected_tax = []
        targets = fetch_taxonomy_page(None)
        self.assertEqual(expected_tax, targets)

    def test_basics_sdss(self):
        expected_length = 25
        targets = fetch_taxonomy_page(self.test_sdss_page)

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

    def test_targets_sdss(self):
        expected_targets = [ ['166', 'C', "Sd", "SDSS", '78|1|-'],
                             ['183', 'S', "Sd", "SDSS", '00|1|-'],
                             ['251', 'L', "Sd", "SDSS", '96|2|LS'],
                             ['1067', 'LS', "Sd", "SDSS", '65|1|-'],
                             ['60707', 'DL', "Sd", "SDSS", '8|1|-'],
                             ['2000 QO192', 'C', "Sd", "SDSS", '10|1|-'],
                             ['962', 'S', "Sd", "SDSS", '96|4|CLSQ'],
                            ]
        tax_data = fetch_taxonomy_page(self.test_sdss_page)
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
                         'A',
                         'Sw',
                         'Sl',
                         'Sl',
                         'C',
                         'Xc',
                         'V',
                          ]
        tax_data = fetch_taxonomy_page(self.test_taxonomy_page)
        taxonomy = [row[1] for row in tax_data]
        self.assertEqual(expected_tax, taxonomy)

    def test_tax_sdss(self):
        expected_tax = [ 'C',
                         'S',
                         'S',
                         'X',
                         'C',
                         'CX',
                         'L',
                         'S',
                         'C',
                         'L',
                         'S',
                         'LS',
                         'C',
                         'V',
                         'S',
                         'S',
                         'DL',
                         'C',
                         'D',
                         'S',
                         'C',
                         'LS',
                         'XL',
                         'D',
                         'C',
                          ]
        tax_data = fetch_taxonomy_page(self.test_sdss_page)
        taxonomy = [row[1] for row in tax_data]
        self.assertEqual(expected_tax, taxonomy)


class TestFetchPreviousSpectra(TestCase):

    def setUp(self):
        # Read and make soup from the stored, partial version of the PDS Taxonomy Database
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_smass_page.html'), 'r')
        self.test_smass_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        test_fh2 = open(os.path.join('astrometrics', 'tests', 'test_manos_page.html'), 'r')
        self.test_manos_page = BeautifulSoup(test_fh2, "html.parser")
        test_fh2.close()

    def test_smass_basics(self):
        expected_length = 12
        page = self.test_smass_page
        targets = fetch_smass_targets(page, None)

        self.assertEqual(expected_length, len(targets))

    def test_smass_abreviated(self):
        cut_off = datetime(2017, 10, 25, 3, 26, 5).date() - relativedelta(months=6)
        expected_length = 10
        page = self.test_smass_page
        targets = fetch_smass_targets(page, cut_off)

        self.assertEqual(expected_length, len(targets))

    def test_manos_basics(self):
        expected_length = 11
        page = self.test_manos_page
        targets = fetch_manos_targets(page, None)
        self.assertEqual(expected_length, len(targets))

    def test_manos_abreviated(self):
        cut_off = datetime(2017, 10, 25, 3, 26, 5).date() - relativedelta(months=6)
        expected_length = 10
        page = self.test_manos_page
        targets = fetch_manos_targets(page, cut_off)
        self.assertEqual(expected_length, len(targets))

    def test_smass_targets(self):
        expected_targets = [ ['302'   , 'NIR', '', "http://smass.mit.edu/data/spex/sp233/a000302.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()],
                             ['6053'  , 'NIR', '', "http://smass.mit.edu/data/spex/sp233/a006053.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()],
                             ['96631' , 'NIR', '', "http://smass.mit.edu/data/spex/sp233/a096631.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()],
                             ['96631' , 'Vis', "http://smass.mit.edu/data/spex/sp234/a096631.sp234.txt", '', "sp[234]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()],
                             ['265962', 'Vis+NIR', "http://smass.mit.edu/data/spex/sp233/a265962.sp233.txt", "http://smass.mit.edu/data/spex/sp233/a265962.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()],
                             ['416584', 'NIR', '', "http://smass.mit.edu/data/spex/sp233/a416584.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()],
                             ['422699', 'NIR', '', "http://smass.mit.edu/data/spex/sp233/a422699.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()],
                             ['2006 UY64', 'NIR', '', "http://smass.mit.edu/data/spex/sp209/au2010pr66.sp209.txt", "sp[209]", datetime.strptime('2017-12-02', '%Y-%m-%d').date()],
                             ['416584', 'Vis', "http://smass.mit.edu/data/spex/sp210/au2005lw7.sp210.txt", '', "sp[210]", datetime.strptime('2015-12-02', '%Y-%m-%d').date()],
                            ]
        smass_data = fetch_smass_targets(self.test_smass_page, None)
        for line in expected_targets:
            self.assertIn(line, smass_data)

    def test_manos_targets(self):
        expected_targets = [ ['2018 KW1'  , 'NIR'    , '', '', 'MANOS Site', datetime.strptime('2018-05-23', '%Y-%m-%d').date()],
                             ['2011 SC191', 'NA'     , '', '', 'MANOS Site', datetime.strptime('2018-04-25', '%Y-%m-%d').date()],
                             ['3552'      , 'NA'     , '', '', 'MANOS Site', datetime.strptime('2018-04-25', '%Y-%m-%d').date()],
                             ['2018 FW1'  , 'Vis'    , '', '', 'MANOS Site', datetime.strptime('2018-03-26', '%Y-%m-%d').date()],
                             ['2018 CB'   , 'Vis+NIR', '', '', 'MANOS Site', datetime.strptime('2018-02-08', '%Y-%m-%d').date()],
                             ['2015 CQ13' , 'Vis'    , 'http://manos.lowell.edu/static/data/manosResults/2015CQ13/2015CQ13_150217_GN_spec.jpg', '', 'MANOS Site', datetime.strptime('2015-02-17', '%Y-%m-%d').date()],
                            ]
        manos_data = fetch_manos_targets(self.test_manos_page, None)
        for line in expected_targets:
            self.assertIn(line, manos_data)


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
        expected_standards = { 'HR9087'   : { 'ra_rad' : radians(0.030394444444444444*15.0), 'dec_rad' : radians(-3.0275), 'mag' : 5.12, 'spectral_type' : 'B7III', 'notes' : ''},
                               'CD-34d241': { 'ra_rad' : radians(10.4455), 'dec_rad' : radians(-33.652361111111111), 'mag' : 11.23, 'spectral_type' : 'F', 'notes' : ''},
                               'BPM16274' : { 'ra_rad' : radians(12.51325), 'dec_rad' : radians(-52.138166666666667), 'mag' : 14.20, 'spectral_type' : 'DA2', 'notes' : 'Mod.'},
                               'LTT2415'  : { 'ra_rad' : radians(89.10125), 'dec_rad' : radians(-27.858), 'mag' : 12.21, 'spectral_type' : '', 'notes' : ''},
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
        expected_standards = { 'HR9087'   : { 'ra_rad' : radians(0.030394444444444444*15.0), 'dec_rad' : radians(-3.0275), 'mag' : 5.12, 'spectral_type' : 'B7III', 'notes' : ''},
                               'CD-34d241': { 'ra_rad' : radians(10.4455), 'dec_rad' : radians(-33.652361111111111), 'mag' : 11.23, 'spectral_type' : 'F', 'notes' : ''},
                               'LTT2415'  : { 'ra_rad' : radians(89.10125), 'dec_rad' : radians(-27.858), 'mag' : 12.21, 'spectral_type' : '', 'notes' : ''},
                             }

        standards = fetch_flux_standards(self.test_flux_page, filter_optical_model=True)

        self.assertEqual(len(expected_standards), len(standards))
        for fluxstd in expected_standards:
            for key in expected_standards[fluxstd]:
                if '_rad' in key:
                    self.assertAlmostEqual(expected_standards[fluxstd][key], standards[fluxstd][key], places=self.precision)
                else:
                    self.assertEqual(expected_standards[fluxstd][key], standards[fluxstd][key])

    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_standards_page_down(self):
        expected_standards = None
        standards = fetch_flux_standards(None, filter_optical_model=True)
        self.assertEqual(expected_standards, standards)


class TestReadSolarStandards(TestCase):

    def setUp(self):
        self.test_file = os.path.join('photometrics', 'data', 'Solar_Standards')

        self.maxDiff = None
        self.precision = 10

    def test1(self):

        expected_num_sources = 46
        expected_standards = { 'Landolt SA93-101' : { 'ra_rad' : radians(28.325), 'dec_rad' : radians(0.373611111111111), 'mag' : 9.7, 'spectral_type' : 'G2V'},
                               'Hyades 64'        : { 'ra_rad' : 1.1635601068681027, 'dec_rad' : 0.2922893202041282, 'mag' : 8.1, 'spectral_type' : 'G2V'},
                               'Landolt SA98-978' : { 'ra_rad' : radians(102.8916666666666), 'dec_rad' : radians(-0.1925), 'mag' : 10.5, 'spectral_type' : 'G2V'},
                               'Landolt SA107-684' : { 'ra_rad' : radians(234.3254166666666), 'dec_rad' : radians(-0.163888888888), 'mag' : 8.4, 'spectral_type' : 'G2V'},
                               'Landolt SA107-998' : { 'ra_rad' : radians(234.5683333333333), 'dec_rad' : radians(0.2563888888888), 'mag' : 10.4, 'spectral_type' : 'G2V'},
                             }

        standards = read_solar_standards(self.test_file)

        self.assertEqual(expected_num_sources, len(standards))
        for solstd in expected_standards:
            for key in expected_standards[solstd]:
                if '_rad' in key:
                    self.assertAlmostEqual(expected_standards[solstd][key], standards[solstd][key], places=self.precision, msg="Mismatch for {} on {}".format(solstd, key))
                else:
                    self.assertEqual(expected_standards[solstd][key], standards[solstd][key])


class TestFetchJPLPhysParams(TestCase):
    """Tests the sources_subs.py Fetch JPL PhysParams functions."""
    def setUp(self):
        params = {  'name' : '2555',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : datetime(2015, 3, 19, 00, 00, 00),
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'A',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body, created = Body.objects.get_or_create(**params)

        self.resp = {'phys_par': [{'ref': 'MPO347540',
                   'value': '11.9',
                   'name': 'H',
                   'desc': 'absolute magnitude (magnitude at 1 au from Sun and observer)',
                   'notes': None,
                   'sigma': None,
                   'title': 'absolute magnitude',
                   'units': None},
                  {'ref': 'urn:nasa:pds:neowise_diameters_albedos::2.0[mainbelt] (http://adsabs.harvard.edu/abs/2012ApJ...759L...8M)',
                   'value': '10.256',
                   'name': 'diameter',
                   'desc': 'effective body diameter',
                   'notes': None,
                   'sigma': '1.605',
                   'title': 'diameter',
                   'units': 'km'},
                  {'ref': 'urn:nasa:pds:neowise_diameters_albedos::2.0[mainbelt] (http://adsabs.harvard.edu/abs/2012ApJ...759L...8M)',
                   'value': '0.320',
                   'name': 'albedo',
                   'desc': 'geometric albedo',
                   'notes': None,
                   'sigma': '0.152',
                   'title': 'geometric albedo',
                   'units': None}],
                 'object': {'shortname': '2555 Thomas',
                  'neo': False,
                  'des_alt': [{'pri': '1980 OC'},
                   {'des': '1976 YQ'},
                   {'des': '1971 UZ2'},
                   {'des': '1961 US'}],
                  'orbit_class': {'name': 'Main-belt Asteroid', 'code': 'MBA'},
                  'pha': False,
                  'spkid': '2002555',
                  'kind': 'an',
                  'orbit_id': '30',
                  'fullname': '2555 Thomas (1980 OC)',
                  'des': '2555',
                  'prefix': None},
                 'signature': {'source': 'NASA/JPL Small-Body Database (SBDB) API',
                  'version': '1.1'}}

    def test_store_stuff_physparams(self):
        """Test the storage of physical parameter types, values, and errors."""
        bodies = Body.objects.all()
        body = bodies[0]

        phys_params = PhysicalParameters.objects.filter(body=body)

        store_jpl_physparams(self.resp['phys_par'], body)

        expected_values = [11.9, 10.256, 0.320]
        expected_ptypes = ['H', 'D', 'ab']
        expected_sigmas = [None, 1.605, 0.152]
        expected = list(zip(expected_values, expected_ptypes, expected_sigmas))
        for p in phys_params:
            test_list = (p.value, p.parameter_type, p.error)
            self.assertIn(test_list, expected)
            expected.remove(test_list)

        self.assertEqual(expected, [])

    def test_pole_orient(self):
        """Test the splitting of the value and error numbers.
         Also to test the storage of these values."""
        bodies = Body.objects.all()
        body = bodies[0]

        pole_test = [{"value":"291.421/66.758",
                    "name":"pole",
                    "sigma":"0.007/0.002",
                    "units":None}]

        phys_params = PhysicalParameters.objects.filter(body=body)
        dbpole_param = phys_params.filter(parameter_type='O')
        store_jpl_physparams(pole_test, body)

        self.assertEqual(dbpole_param[0].value, 291.421)
        self.assertEqual(dbpole_param[0].value2, 66.758)
        self.assertEqual(dbpole_param[0].error, 0.007)
        self.assertEqual(dbpole_param[0].error2, 0.002)

    def test_color(self):
        """Test the storage of color bands, values, and errors."""
        bodies = Body.objects.all()
        body = bodies[0]

        color_test = [{"value": "0.426",
                       "name" : "UB",
                       "desc" : "color index U-B magnitude difference",
                       "sigma": "0.026",
                       "title": "U-B",
                       "units": None}]

        color_param = ColorValues.objects.filter(body=body)
        store_jpl_physparams(color_test, body)

        self.assertEqual(color_param[0].value, 0.426)
        self.assertEqual(color_param[0].color_band, 'U-B')
        self.assertEqual(color_param[0].error, 0.026)

    def test_store_stuff_desigs(self):
        """Test the storage of designations without any duplicate designations.
           Also to test the storage of preferred designations."""
        bodies = Body.objects.all()
        body = bodies[0]

        expected_desigs = ['Thomas', '2555', '1980 OC', '1976 YQ', '1971 UZ2', '1961 US']
        expected_dtypes = ['N', '#', 'P', 'P', 'P', 'P']
        expected = list(zip(expected_desigs, expected_dtypes))
        # expected = [[x,expected_dtypes[i]] for i,x in enumerate(expected_desigs)]
        desigs = Designations.objects.filter(body=body)
        store_jpl_desigs(self.resp['object'], body)

        # running second time to test we're only storing values once
        store_jpl_desigs(self.resp['object'], body)
        for d in desigs:
            test_list = (d.value, d.desig_type)
            self.assertIn(test_list, expected)
            expected.remove(test_list)

        self.assertEqual(expected, [])

        # testing for preferred designations
        prov_desig = desigs.filter(desig_type='P').filter(preferred=True)
        self.assertEqual(len(prov_desig), 1)
        self.assertEqual('1980 OC', prov_desig[0].value)

    def test_store_stuff_desigs_noprovdes(self):
        """Test for when there are no alternate designations."""
        bodies = Body.objects.all()
        body = bodies[0]

        pallas = {"neo": False,
                   "des_alt": [],
                   "orbit_class":
                       {"name": "Main-belt Asteroid",
                        "code": "MBA"},
                   "pha": False,
                   "spkid": "2000002",
                   "kind": "an",
                   "orbit_id": "35",
                   "fullname": "2 Pallas",
                   "des": "2",
                   "prefix": None}

        desigs = Designations.objects.filter(body=body)
        store_jpl_desigs(pallas, body)

        self.assertEqual(desigs[0].value, '2')
        self.assertEqual(desigs[0].desig_type, '#')
        self.assertEqual(desigs[1].value, 'Pallas')
        self.assertEqual(desigs[1].desig_type, 'N')
        self.assertEqual(len(desigs), 2)

    def test_store_stuff_desigs_comet(self):
        """Test the storage of comet designations."""
        bodies = Body.objects.all()
        body = bodies[0]

        westphal = {"object":
                        {"neo": True,
                         "des_alt":
                             [{"yl": "1913d",
                               "rn": "1913 VI",
                               "des": "20D/1913 S1"},
                              {"rn": "1852 IV",
                               "des": "20D/1852 O1"},
                              {"yl": "1813d",
                               "rn": "1813 VI"}],
                         "orbit_class":
                             {"name": "Halley-type Comet*",
                              "code": "HTC"},
                         "pha": False,
                         "spkid": "1000212",
                         "kind": "cn",
                         "orbit_id": "19",
                        "fullname": "20D/Westphal",
                         "des": "20D",
                         "prefix": "D"},
                    "signature":
                        {"source": "NASA/JPL Small-Body Database (SBDB) API",
                         "version": "1.1"}
                    }

        comet_des = Designations.objects.filter(body=body)
        store_jpl_desigs(westphal['object'], body)

        self.assertEqual(comet_des[0].value, '20D')
        self.assertEqual(comet_des[0].desig_type, '#')
        self.assertEqual(comet_des[1].value, 'Westphal')
        self.assertEqual(comet_des[1].desig_type, 'N')

    def test_store_stuff_desigs_noname(self):
        """Test the storage of an object's designations when there is no name."""
        bodies = Body.objects.all()
        body = bodies[0]

        ex_obj = {"neo": False,
                  "des_alt":
                      [{"pri": "2005 RT33"}],
                  "orbit_class":
                      {"name": "Main-belt Asteroid",
                       "code": "MBA"},
                  "pha": False,
                  "spkid": "2254857",
                  "kind": "an",
                  "orbit_id": "12",
                  "fullname": "254857  (2005 RT33)",
                  "des": "254857",
                  "prefix": None}

        obj_ex = Designations.objects.filter(body=body)
        store_jpl_desigs(ex_obj, body)

        self.assertEqual(obj_ex[0].value, '254857')
        self.assertEqual(obj_ex[0].desig_type, '#')
        self.assertEqual(obj_ex[1].value, '2005 RT33')
        self.assertEqual(obj_ex[1].desig_type, 'P')

    def test_store_stuff_desigs_nonamenum(self):
        """Test the storage of an object's designations when there is no name and number
           (only a provisional designation)."""
        bodies = Body.objects.all()
        body = bodies[0]

        ex_obj = {"neo": False,
                  "des_alt": [],
                  "orbit_class":
                      {"name": "Inner Main-belt Asteroid",
                       "code": "IMB"},
                  "pha": False,
                  "spkid": "3841574",
                  "kind": "au",
                  "orbit_id": "3",
                  "fullname": "(2019 HG2)",
                  "des": "2019 HG2",
                  "prefix": None}

        obj_ex = Designations.objects.filter(body=body)
        store_jpl_desigs(ex_obj, body)

        self.assertEqual(obj_ex[0].value, '2019 HG2')
        self.assertEqual(obj_ex[0].desig_type, 'P')

    def test_parse_jpl_comet_names(self):
        comet_list = [{'fullname': 'C/2019 Q4 (Borisov)', 'des': '2019 Q4', 'prefix': 'C'},
                      {'fullname': 'P/2019 B2 (Groeller)', 'des': '2019 B2', 'prefix': 'P'},
                      {'fullname': '289P/Blanpain', 'des': '289P', 'prefix': 'P'},
                      {'fullname': '329P/LINEAR-Catalina', 'des': '329P', 'prefix': 'P'},
                      {'fullname': '393P/Spacewatch-Hill', 'des': '393P', 'prefix': 'P'},
                      {'fullname': '389P/Siding Spring', 'des': '389P', 'prefix': 'P'},
                      {'fullname': "'Oumuamua (A/2017 U1)", 'des': '2017 U1', 'prefix': 'A'}]

        comet_expected_dict = [[{'value': None, 'desig_type': '#'}, {'value': 'Borisov', 'desig_type': 'N'}, {'value': 'C/2019 Q4', 'desig_type': 'P'}],
                               [{'value': None, 'desig_type': '#'}, {'value': 'Groeller', 'desig_type': 'N'}, {'value': 'P/2019 B2', 'desig_type': 'P'}],
                               [{'value': '289P', 'desig_type': '#'}, {'value': 'Blanpain', 'desig_type': 'N'}, {'value': None, 'desig_type': 'P'}],
                               [{'value': '329P', 'desig_type': '#'}, {'value': 'LINEAR-Catalina', 'desig_type': 'N'}, {'value': None, 'desig_type': 'P'}],
                               [{'value': '393P', 'desig_type': '#'}, {'value': 'Spacewatch-Hill', 'desig_type': 'N'}, {'value': None, 'desig_type': 'P'}],
                               [{'value': '389P', 'desig_type': '#'}, {'value': 'Siding Spring', 'desig_type': 'N'}, {'value': None, 'desig_type': 'P'}],
                               [{'value': None, 'desig_type': '#'}, {'value': "'Oumuamua", 'desig_type': 'N'}, {'value': 'A/2017 U1', 'desig_type': 'P'}]
                               ]
        for i, comet in enumerate(comet_list):
            out_dicts = parse_jpl_fullname(comet)
            for designation in comet_expected_dict[i]:
                designation['preferred'] = True
            self.assertEqual(out_dicts, comet_expected_dict[i])

    def test_store_stuff_sourcetypes(self):
        """Test the storage of sourcetypes."""
        bodies = Body.objects.all()
        body = bodies[0]
        objcode = 'TJN'
        store_jpl_sourcetypes(objcode, self.resp['object'], body)

        self.assertEqual(body.source_type, 'T')
        self.assertEqual(body.source_subtype_1, 'P5')
        self.assertEqual(body.source_subtype_2, None)

    def test_store_stuff_neo_pha_1(self):
        """Test the storage of source subtypes when the object is labeled as an NEO
           but not as a PHA."""
        bodies = Body.objects.all()
        body = bodies[0]
        objcode = self.resp['object']
        objcode['orbit_class']['code'] = 'APO'
        body.source_type = None
        body.save()
        objcode['neo'] = True
        objcode['pha'] = False
        store_jpl_sourcetypes(objcode['orbit_class']['code'], objcode, body)

        self.assertEqual(body.source_type, 'N')
        self.assertEqual(body.source_subtype_1, 'N3')
        self.assertEqual(body.source_subtype_2, None)

    def test_store_stuff_neo_pha_2(self):
        """Test the storage of source subtypes when the object is labeled as both an NEO
           and as a PHA."""
        bodies = Body.objects.all()
        body = bodies[0]
        objcode = self.resp['object']
        objcode['orbit_class']['code'] = 'APO'
        body.source_type = 'N'
        body.save()
        objcode['neo'] = True
        objcode['pha'] = True
        store_jpl_sourcetypes(objcode['orbit_class']['code'], objcode, body)

        self.assertEqual(body.source_type, 'N')
        self.assertEqual(body.source_subtype_1, 'N3')
        self.assertEqual(body.source_subtype_2, 'PH')

    def test_store_stuff_neo_pha_3(self):
        """Test the storage of source subtypes when the object is labeled as a PHA
           but not as an NEO (This situation is rare)."""
        bodies = Body.objects.all()
        body = bodies[0]
        objcode = self.resp['object']
        objcode['orbit_class']['code'] = 'APO'
        body.source_type = None
        body.save()
        objcode['neo'] = False
        objcode['pha'] = True
        store_jpl_sourcetypes(objcode['orbit_class']['code'], objcode, body)

        self.assertEqual(body.source_type, None)
        self.assertEqual(body.source_subtype_1, 'N3')
        self.assertEqual(body.source_subtype_2, None)

    def test_store_stuff_neo_pha_4(self):
        """Test the storage of source subtypes when the object is a comet
           (instead of an asteroid) and is labeled as both an NEO and as a PHA."""
        bodies = Body.objects.all()
        body = bodies[0]
        objcode = self.resp['object']
        objcode['orbit_class']['code'] = 'JFC'
        body.source_type = 'C'
        body.save()
        objcode['neo'] = True
        objcode['pha'] = True
        store_jpl_sourcetypes(objcode['orbit_class']['code'], objcode, body)

        self.assertEqual(body.source_type, 'C')
        self.assertEqual(body.source_subtype_1, 'JF')
        self.assertEqual(body.source_subtype_2, 'PH')

    def test_store_stuff_comet_longperiod(self):
        """Test the storage of source subtypes when the object is a comet
           (instead of an asteroid) and is labeled as both an NEO and as a PHA."""

        bodies = Body.objects.all()
        body = bodies[0]
        objcode = self.resp['object']
        objcode['orbit_class']['code'] = 'COM'
        body.source_type = 'C'
        body.save()

        store_jpl_sourcetypes(objcode['orbit_class']['code'], objcode, body)

        self.assertEqual(body.source_type, 'C')
        self.assertLessEqual(len(body.source_subtype_1), 2)
        self.assertEqual(body.source_subtype_1, 'LP')


class TestBoxSpiral(TestCase):

    def test_run_generator(self):
        """Test Box Spiral generator"""

        b = box_spiral_generator(1, 3)
        self.assertEqual((0, 0), next(b))
        self.assertEqual((1, 0), next(b))
        self.assertEqual((1, 1), next(b))
        self.assertEqual((0, 1), next(b))
        self.assertEqual((-1, 1), next(b))
        self.assertEqual((-1, 0), next(b))
        for k, b_next in enumerate(b):
            if k == 23:
                self.assertEqual((3, 2), b_next)
            if k == 24:
                self.assertEqual((0, 0), b_next)
            if k == 25:
                self.assertEqual((1, 0), b_next)
                break
