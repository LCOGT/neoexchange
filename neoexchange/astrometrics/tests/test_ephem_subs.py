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

from datetime import datetime
from django.test import TestCase
from django.forms.models import model_to_dict
from rise_set.angle import Angle
from math import radians

#Import module to test
from astrometrics.ephem_subs import *
from core.models import Body


class TestGetMountLimits(TestCase):

    def compare_limits(self, pos_limit, neg_limit, alt_limit, tel_class):
        if tel_class.lower() == '2m':
            ha_pos_limit = 12.0 * 15.0
            ha_neg_limit = -12.0 * 15.0
            altitude_limit = 25.0
        elif tel_class.lower() == '1m':
            ha_pos_limit = 4.5 * 15.0
            ha_neg_limit = -4.5 * 15.0
            altitude_limit = 30.0
        elif tel_class.lower() == '0.4m':
            ha_pos_limit = 4.46 * 15.0
            ha_neg_limit = -4.5 * 15.0
            altitude_limit = 15.0
        else:
            self.Fail("Unknown telescope class:", tel_class)
        self.assertEqual(ha_pos_limit, pos_limit)
        self.assertEqual(ha_neg_limit, neg_limit)
        self.assertEqual(altitude_limit, alt_limit)

    def test_2m_by_site(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('OGG-CLMA-2M0A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '2m')

    def test_2m_by_site_code(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('F65')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '2m')

    def test_2m_by_site_code_lowercase(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('f65')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '2m')

    def test_1m_by_site(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('ELP-DOMA-1m0A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_code(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('K91')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_code_lowercase(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('q63')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_point4m_by_site(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('TFN-AQWA-0m4B')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site2(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('OGG-CLMA-0M4A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site3(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('OGG-CLMA-0M4B')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site4(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('COJ-CLMA-0M4A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site5(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('COJ-CLMA-0M4A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('Z21')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code2(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('Q59')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code3(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('T04')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code_lowercase(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('z21')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

class TestComputeEphem(TestCase):

    def setUp(self):
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

        comet_params = { 'abs_mag': 11.1,
                         'active': False,
                         'arc_length': None,
                         'argofperih': 12.796,
                         'discovery_date': None,
                         'eccentricity': 0.640872,
                         'elements_type': u'MPC_COMET',
                         'epochofel': datetime(2015, 8, 6, 0, 0),
                         'epochofperih': datetime(2015, 8, 13, 2, 1, 19),
                         'fast_moving': False,
                         'ingest': datetime(2015, 10, 30, 20, 17, 53),
                         'longascnode': 50.1355,
                         'meananom': None,
                         'meandist': 3.461895,
                         'name': u'67P',
                         'not_seen': None,
                         'num_obs': None,
                         'orbinc': 7.0402,
                         'origin': u'M',
                         'perihdist': 1.2432627,
                         'provisional_name': u'',
                         'provisional_packed': u'',
                         'score': None,
                         'slope': 4.8,
                         'source_type': u'C',
                         'update_time': None,
                         'updated': False,
                         'urgency': None}
        self.comet, created = Body.objects.get_or_create(**comet_params)


        self.elements = {'G': 0.15,
                         'H': 21.0,
                         'MDM': Angle(degrees=0.74394528),
                         'arg_perihelion': Angle(degrees=85.19251),
                         'eccentricity': 0.1896865,
                         'epoch': 57100.0,
                         'inclination': Angle(degrees=8.34739),
                         'long_node': Angle(degrees=147.81325),
                         'mean_anomaly': Angle(degrees=325.2636),
                         'n_nights': 3,
                         'n_obs': 17,
                         'n_oppos': 1,
                         'name': 'N007r0q',
                         'reference': '',
                         'residual': 0.53,
                         'semi_axis': 1.2176312,
                         'type': 'MPC_MINOR_PLANET',
                         'uncertainty': 'U'}

    def test_body_is_correct_class(self):
        tbody = Body.objects.get(provisional_name='N999r0q')
        self.assertIsInstance(tbody, Body)

    def test_save_and_retrieve_bodies(self):
        first_body = Body.objects.get(provisional_name='N999r0q')
        body_dict = model_to_dict(first_body)

        body_dict['provisional_name'] = 'N999z0z'
        body_dict['eccentricity'] = 0.42
        body_dict['id'] += 2
        second_body = Body.objects.create(**body_dict)
        second_body.save()

        saved_items = Body.objects.all()
        self.assertEqual(saved_items.count(), 3)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]
        self.assertEqual(first_saved_item.provisional_name, 'N999r0q')
        self.assertEqual(second_saved_item.provisional_name, 'N999z0z')

    def test_compute_ephem_with_elements(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_ra  = 5.28722753669144
        expected_dec = 0.522637696108887
        expected_mag = 20.408525362626005
        expected_motion = 2.4825093417658186
        expected_alt =  -58.658929026981895
        emp_line = compute_ephem(d, self.elements, '?', dbg=False, perturb=True, display=False)
        self.assertEqual(d, emp_line[0])
        precision = 11
        self.assertAlmostEqual(expected_ra, emp_line[1], precision)
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_mag, emp_line[3], precision)
        self.assertAlmostEqual(expected_motion, emp_line[4], precision)
        self.assertAlmostEqual(expected_alt, emp_line[5], precision)

    def test_compute_ephem_with_body(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_ra  = 5.28722753669144
        expected_dec = 0.522637696108887
        expected_mag = 20.408525362626005
        expected_motion = 2.4825093417658186
        expected_alt =  -58.658929026981895
        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)
        self.assertEqual(d, emp_line[0])
        precision = 11
        self.assertAlmostEqual(expected_ra, emp_line[1], precision)
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_mag, emp_line[3], precision)
        self.assertAlmostEqual(expected_motion, emp_line[4], precision)
        self.assertAlmostEqual(expected_alt, emp_line[5], precision)
        
    def test_compute_south_polar_distance_with_elements_in_north(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = 0.522637696108887
        expected_spd = 119.94694444444444
        emp_line = compute_ephem(d, self.elements, '?', dbg=False, perturb=True, display=False)
        precision = 11
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)
        
    def test_compute_south_polar_distance_with_body_in_north(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = 0.522637696108887
        expected_spd = 119.94694444444444
        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)
        precision = 11
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)

    def test_compute_south_polar_distance_with_body_in_south(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = -0.06554641803516298
        expected_spd = 86.242222222222225
        body_elements = model_to_dict(self.body)
        body_elements['meananom'] = 25.2636
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)
        precision = 11
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)

    def test_call_compute_ephem_with_body(self):
        start = datetime(2015, 4, 21, 8, 45, 00)
        end = datetime(2015, 4, 21,  8, 51, 00)
        site_code = 'V37'
        step_size = 300
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 04 21 08:45', '20 10 05.99', '+29 56 57.5', '20.4', ' 2.43', '+33', '0.09', '107', '-42', '+047', '-04:25'],
                                ['2015 04 21 08:50', '20 10 06.92', '+29 56 57.7', '20.4', ' 2.42', '+34', '0.09', '107', '-42', '+048', '-04:20']]
        ephem_lines = call_compute_ephem(body_elements, start, end, site_code, step_size)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_with_body_F65(self):
        start = datetime(2015, 4, 21, 11, 30, 00)
        end = datetime(2015, 4, 21, 11, 35, 01)
        site_code = 'F65'
        step_size = 300
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 04 21 11:30', '20 10 38.15', '+29 56 52.1', '20.4', ' 2.45', '+20', '0.09', '108', '-47', '-999', '-05:09'],
                                ['2015 04 21 11:35', '20 10 39.09', '+29 56 52.4', '20.4', ' 2.45', '+21', '0.09', '108', '-48', '-999', '-05:04']]

        ephem_lines = call_compute_ephem(body_elements, start, end, site_code, step_size)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_with_date(self):
        start = datetime(2015, 4, 28, 10, 20, 00)
        end = datetime(2015, 4, 28, 10, 25, 01)
        site_code = 'V37'
        step_size = 300
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 04 28 10:20', '20 40 36.53', '+29 36 33.1', '20.6', ' 2.08', '+52', '0.72', '136', '-15', '+058', '-02:53'],
                                ['2015 04 28 10:25', '20 40 37.32', '+29 36 32.5', '20.6', ' 2.08', '+54', '0.72', '136', '-16', '+059', '-02:48']]

        ephem_lines = call_compute_ephem(body_elements, start, end, site_code, step_size)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_with_altlimit(self):
        start = datetime(2015, 9, 1, 17, 20, 00)
        end = datetime(2015, 9, 1, 19, 50, 01)
        site_code = 'K91'
        step_size = 300
        alt_limit = 30.0
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 09 01 19:45', '23 56 43.16', '-11 31 02.4', '19.3', ' 1.91', '+30', '0.86', ' 29', '+01', '+029', '-04:06'],
                                ['2015 09 01 19:50', '23 56 42.81', '-11 31 10.5', '19.3', ' 1.91', '+31', '0.86', ' 29', '+02', '+030', '-04:01']]

        ephem_lines = call_compute_ephem(body_elements, start, end,
            site_code, step_size, alt_limit)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_for_geocenter(self):
        start = datetime(2015, 7, 5, 7, 20, 00)
        end = datetime(2015, 7, 5, 7, 20, 59)
        site_code = '500'
        step_size = 60
        alt_limit = 0
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 07 05 07:20', '23 50 01.78', '+19 03 49.3', '20.7', ' 1.20', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],]

        ephem_lines = call_compute_ephem(body_elements, start, end,
            site_code, step_size, alt_limit)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_for_comets(self):
        start = datetime(2015, 10, 30, 12, 20, 00)
        end = datetime(2015, 10, 30, 12, 29, 59)
        site_code = 'F65'
        step_size = 600
        alt_limit = 0
        body_elements = model_to_dict(self.comet)
        expected_ephem_lines = [['2015 10 30 12:20', '10 44 56.44', '+14 13 30.6', '14.7', ' 1.44', '+1', '0.87', ' 79', '+79', '-999', '-06:16'],]

        ephem_lines = call_compute_ephem(body_elements, start, end,
            site_code, step_size, alt_limit)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_for_comets_no_HG(self):
        start = datetime(2015, 10, 30, 12, 20, 00)
        end = datetime(2015, 10, 30, 12, 29, 59)
        site_code = 'F65'
        step_size = 600
        alt_limit = 0
        body_elements = model_to_dict(self.comet)
        body_elements['abs_mag'] = None
        body_elements['slope'] = None
        expected_ephem_lines = [['2015 10 30 12:20', '10 44 56.44', '+14 13 30.6', '-99.0', ' 1.44', '+1', '0.87', ' 79', '+79', '-999', '-06:16'],]

        ephem_lines = call_compute_ephem(body_elements, start, end,
            site_code, step_size, alt_limit)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

class TestComputeFOM(TestCase):

    def setUp(self):
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
                    'not_seen'      : 2.3942,
                    'arc_length'    : 0.4859,
                    'score'         : 83,
                    'abs_mag'       : 19.8
                    }
        self.body, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : 'EUHT950',
                    'slope'         : 0.15,
                    'epochofel'     : '2015-10-25 00:00:00',
                    'meananom'      : 345.87056,
                    'argofperih'    : 47.03212,
                    'longascnode'   : 7.8065,
                    'orbinc'        : 8.98042,
                    'eccentricity'  : 0.5367056,
                    'meandist'      : 1.9442854,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    'not_seen'      : 0.866,
                    'arc_length'    : 0.0,
                    'score'         : 100,
                    'abs_mag'       : 19.5
                    }
        self.body2, created = Body.objects.get_or_create(**params)

    def test_compute_FOM_with_body(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_FOM = 137.1187602774659
        expected_not_seen = 2.3942
        expected_arc_length = 0.4859
        expected_score = 83
        expected_abs_mag = 19.8
        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)
        FOM = comp_FOM(body_elements, emp_line)
        precision = 11
        self.assertAlmostEqual(expected_not_seen, body_elements['not_seen'], precision)
        self.assertAlmostEqual(expected_arc_length, body_elements['arc_length'], precision)
        self.assertAlmostEqual(expected_score, body_elements['score'], precision)
        self.assertAlmostEqual(expected_abs_mag, body_elements['abs_mag'], precision)
        self.assertAlmostEqual(expected_FOM, FOM, precision)

    def test_FOM_with_BadBody(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_FOM = None
        body_elements = model_to_dict(self.body)
        body_elements['not_seen'] = None
        body_elements['arc_length'] = None
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)

        FOM = comp_FOM(body_elements, emp_line)

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_NoScore(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_FOM = None
        body_elements = model_to_dict(self.body)
        body_elements['score'] = None
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)

        FOM = comp_FOM(body_elements, emp_line)

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_wrong_source_type(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_FOM = None
        body_elements = model_to_dict(self.body)
        body_elements['source_type'] = 'N'
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)

        FOM = comp_FOM(body_elements, emp_line)

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_zero_arclength(self):
        d = datetime(2015, 11, 2, 19, 46, 9)
        expected_FOM = 1.658839108423487e+75
        body_elements = model_to_dict(self.body2)
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)

        FOM = comp_FOM(body_elements, emp_line)

        self.assertEqual(expected_FOM, FOM)

class TestLongTermScheduling(TestCase):

    def setUp(self):
        params = {  'provisional_name' : '2001 SQ263',
                    'slope'         : 0.15,
                    'epochofel'     : '2017-02-16 00:00:00',
                    'meananom'      : 324.47087,
                    'argofperih'    : 262.49786,
                    'longascnode'   : 327.13827,
                    'orbinc'        : 3.94116,
                    'eccentricity'  : 0.4914435,
                    'meandist'      : 0.9474511,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'Y',
                    'not_seen'      : 45.02,
                    'arc_length'    : 5538.0,
                    'score'         : None,
                    'abs_mag'       : 22.4
                    }
        self.body, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : '192559',
                    'slope'         : 0.15,
                    'epochofel'     : '2016-07-31 00:00:00',
                    'meananom'      : 48.13538,
                    'argofperih'    : 75.95569,
                    'longascnode'   : 228.17879,
                    'orbinc'        : 10.06115,
                    'eccentricity'  : 0.2265235,
                    'meandist'      : 1.0745542,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'Y',
                    'not_seen'      : 2981.02,
                    'arc_length'    : 3650.0,
                    'score'         : None,
                    'abs_mag'       : 20.4
                    }
        self.body2, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : '265482',
                    'slope'         : 0.15,
                    'epochofel'     : '2016-07-31 00:00:00',
                    'meananom'      : 269.50759,
                    'argofperih'    : 284.82825,
                    'longascnode'   : 110.84583,
                    'orbinc'        : 6.17463,
                    'eccentricity'  : 0.32794,
                    'meandist'      : 1.12956,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'Y',
                    'not_seen'      : 2159.72,
                    'arc_length'    : 2461.0,
                    'score'         : None,
                    'abs_mag'       : 21.3
                    }
        self.body3, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : '2011 EP51',
                    'slope'         : 0.15,
                    'epochofel'     : '2016-07-31 00:00:00',
                    'meananom'      : 270.23275,
                    'argofperih'    : 169.66452,
                    'longascnode'   : 160.11304,
                    'orbinc'        : 3.40805,
                    'eccentricity'  : 0.3075497,
                    'meandist'      : 0.8282785,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'Y',
                    'not_seen'      : 1037.72,
                    'arc_length'    : 1090.0,
                    'score'         : None,
                    'abs_mag'       : 24.7
                    }
        self.body4, created = Body.objects.get_or_create(**params)

        params = {  'provisional_name' : '469219',
                    'slope'         : 0.15,
                    'epochofel'     : '2016-07-31 00:00:00',
                    'meananom'      : 297.53221,
                    'argofperih'    : 307.22764,
                    'longascnode'   : 66.51321,
                    'orbinc'        : 7.77144,
                    'eccentricity'  : 0.1041435,
                    'meandist'      : 1.00123,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'Y',
                    'not_seen'      : 210.72,
                    'arc_length'    : 4468.0,
                    'score'         : None,
                    'abs_mag'       : 24.2
                    }
        self.body5, created = Body.objects.get_or_create(**params)

    def test_LongTermScheduling_with_body(self):
        #Body is only up for a few days starting at the
        #beginning of the search.
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_returned_params = (['2017 01 06', '2017 01 07', '2017 01 08', '2017 01 09'], [['2017 01 06 01:20', '02 13 50.14', '+31 54 14.0', '21.0', ' 4.69', '+79', '0.52', ' 31', '+62', '+059', '-00:47'], ['2017 01 07 01:20', '02 06 33.78', '+30 58 16.2', '21.0', ' 4.64', '+82', '0.64', ' 22', '+65', '-999', '-00:36'], ['2017 01 08 01:20', '01 59 32.36', '+30 01 16.6', '21.1', ' 4.58', '+84', '0.75', ' 23', '+61', '-999', '-00:25'], ['2017 01 09 01:20', '01 52 45.62', '+29 03 29.1', '21.2', ' 4.51', '+86', '0.84', ' 33', '+53', '+069', '-00:14']], [5.25, 5.0, 4.833333333333333, 4.666666666666667], [88, 89, 89, 88])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=26)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body_no_dark_and_up_emp(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_returned_params = ([], [], [], [])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=26)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body_no_emp(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_returned_params = ([], [], [], [])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 2, 27, 0, 0, 00), date_range=26)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body2(self):
        #Body is up for a couple days when gets faint enough,
        #but then moon gets full. Body becomes observable again
        #after moon "fades" until no longer up for at least 3 hrs.
        site_code = 'V37'
        body_elements = model_to_dict(self.body2)

        expected_returned_params = (['2017 01 09', '2017 01 16', '2017 01 17', '2017 01 18', '2017 01 19', '2017 01 20', '2017 01 21', '2017 01 22', '2017 01 23', '2017 01 24'], [['2017 01 09 08:30', '11 07 53.60', '-19 20 19.8', '21.5', ' 1.03', '+30', '0.86', '106', '+26', '+021', '-02:18'], ['2017 01 16 08:25', '11 11 11.23', '-22 01 59.9', '21.3', ' 0.97', '+30', '0.82', ' 28', '+53', '+012', '-01:59'], ['2017 01 17 08:25', '11 11 28.60', '-22 24 52.3', '21.3', ' 0.97', '+30', '0.74', ' 27', '+42', '+016', '-01:55'], ['2017 01 18 08:25', '11 11 43.01', '-22 47 39.7', '21.2', ' 0.96', '+30', '0.64', ' 31', '+31', '+020', '-01:51'], ['2017 01 19 08:25', '11 11 54.34', '-23 10 21.4', '21.2', ' 0.96', '+30', '0.55', ' 38', '+20', '+023', '-01:48'], ['2017 01 20 08:25', '11 12 02.53', '-23 32 56.7', '21.2', ' 0.95', '+30', '0.45', ' 47', '+09', '+027', '-01:44'], ['2017 01 21 08:25', '11 12 07.47', '-23 55 24.9', '21.1', ' 0.95', '+30', '0.36', ' 56', '-01', '+030', '-01:40'], ['2017 01 22 08:25', '11 12 09.07', '-24 17 45.2', '21.1', ' 0.94', '+30', '0.27', ' 66', '-11', '+034', '-01:36'], ['2017 01 23 08:20', '11 12 07.27', '-24 39 52.1', '21.1', ' 0.94', '+30', '0.19', ' 76', '-22', '+037', '-01:37'], ['2017 01 24 08:20', '11 12 01.93', '-25 01 54.1', '21.0', ' 0.93', '+30', '0.12', ' 86', '-33', '+041', '-01:33']], [4.083333333333333, 3.9166666666666665, 3.8333333333333335, 3.6666666666666665, 3.5833333333333335, 3.4166666666666665, 3.3333333333333335, 3.1666666666666665, 3.1666666666666665, 3.0], [39, 37, 36, 36, 36, 35, 35, 34, 34, 34])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=26)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body3(self):
        #Body is not observable (because not up for >3 hrs) until
        #sometime after start of search and then until the end of
        #the date range.
        site_code = 'V37'
        body_elements = model_to_dict(self.body3)

        expected_returned_params = (['2017 01 18', '2017 01 19', '2017 01 20', '2017 01 21', '2017 01 22', '2017 01 23', '2017 01 24', '2017 01 25', '2017 01 26', '2017 01 27', '2017 01 28', '2017 01 29', '2017 01 30', '2017 01 31', '2017 02 01'], [['2017 01 18 09:15', '14 03 19.11', '+06 01 50.1', '18.4', ' 9.73', '+30', '0.64', ' 20', '+40', '-999', '-03:53'], ['2017 01 19 08:55', '13 52 25.69', '+08 33 39.1', '18.3', ' 9.46', '+30', '0.55', ' 15', '+25', '-999', '-03:58'], ['2017 01 20 08:35', '13 41 43.96', '+10 59 30.8', '18.2', ' 9.15', '+30', '0.45', ' 22', '+11', '-999', '-04:03'], ['2017 01 21 08:15', '13 31 15.01', '+13 18 31.1', '18.2', ' 8.80', '+30', '0.36', ' 35', '-03', '+031', '-04:09'], ['2017 01 22 07:55', '13 20 59.76', '+15 30 00.5', '18.1', ' 8.43', '+30', '0.27', ' 48', '-17', '+036', '-04:15'], ['2017 01 23 07:40', '13 10 56.80', '+17 33 59.8', '18.1', ' 8.04', '+30', '0.20', ' 62', '-31', '+041', '-04:16'], ['2017 01 24 07:20', '13 01 11.14', '+19 29 22.9', '18.0', ' 7.65', '+30', '0.13', ' 76', '-45', '+045', '-04:22'], ['2017 01 25 07:05', '12 51 39.02', '+21 16 57.8', '18.0', ' 7.25', '+30', '0.07', ' 89', '-58', '+050', '-04:24'], ['2017 01 26 06:50', '12 42 22.99', '+22 56 25.1', '18.0', ' 6.87', '+31', '0.03', '103', '-70', '+054', '-04:26'], ['2017 01 27 06:35', '12 33 23.36', '+24 27 57.9', '18.0', ' 6.49', '+31', '0.01', '116', '-76', '+056', '-04:28'], ['2017 01 28 06:25', '12 24 38.51', '+25 52 11.8', '18.0', ' 6.13', '+32', '0.00', '129', '-70', '+055', '-04:25'], ['2017 01 29 06:10', '12 16 12.37', '+27 08 51.3', '18.0', ' 5.78', '+32', '0.02', '141', '-57', '+051', '-04:28'], ['2017 01 30 06:00', '12 08 01.37', '+28 18 53.6', '18.0', ' 5.46', '+33', '0.05', '151', '-44', '+047', '-04:26'], ['2017 01 31 05:45', '12 00 09.11', '+29 22 12.6', '18.0', ' 5.14', '+32', '0.11', '154', '-29', '+042', '-04:29'], ['2017 02 01 05:35', '11 52 32.14', '+30 19 41.3', '18.1', ' 4.84', '+33', '0.19', '150', '-15', '+038', '-04:28']], [3.3333333333333335, 3.6666666666666665, 4.0, 4.333333333333333, 4.666666666666667, 4.916666666666667, 5.25, 5.5, 5.75, 6.0, 6.166666666666667, 6.416666666666667, 6.583333333333333, 6.666666666666667, 6.833333333333333], [64, 67, 70, 73, 75, 77, 79, 80, 82, 84, 85, 86, 87, 88, 89])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=26)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body4(self):
        #Body is not observable (because too faint) until
        #sometime after start of search and then until the end of
        #the date range.
        site_code = 'V37'
        body_elements = model_to_dict(self.body4)

        expected_returned_params = (['2017 01 26', '2017 01 27', '2017 01 28', '2017 01 29', '2017 01 30', '2017 01 31', '2017 02 01'], [['2017 01 26 06:40', '10 53 54.75', '-13 15 07.5', '21.5', ' 4.76', '+30', '0.03', '116', '-72', '+054', '-02:47'], ['2017 01 27 06:25', '10 47 10.72', '-12 24 58.0', '21.4', ' 4.96', '+30', '0.01', '129', '-76', '+055', '-02:52'], ['2017 01 28 06:10', '10 40 12.85', '-11 31 37.6', '21.3', ' 5.15', '+30', '0.00', '141', '-68', '+052', '-02:56'], ['2017 01 29 05:55', '10 33 01.97', '-10 35 07.5', '21.2', ' 5.34', '+30', '0.02', '153', '-55', '+048', '-03:00'], ['2017 01 30 05:40', '10 25 39.12', '-09 35 32.1', '21.1', ' 5.52', '+30', '0.05', '160', '-40', '+043', '-03:03'], ['2017 01 31 05:25', '10 18 05.61', '-08 32 59.2', '21.0', ' 5.68', '+30', '0.11', '158', '-25', '+038', '-03:07'], ['2017 02 01 05:10', '10 10 22.93', '-07 27 40.7', '20.9', ' 5.82', '+30', '0.18', '147', '-10', '+033', '-03:10']], [5.583333333333333, 5.666666666666667, 5.833333333333333, 5.916666666666667, 6.083333333333333, 6.166666666666667, 6.333333333333333], [46, 47, 47, 48, 49, 50, 52])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=26)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body5(self):
        #Body is not observable (because too faint) at
        #any time in the date range.
        site_code = 'V37'
        body_elements = model_to_dict(self.body5)

        expected_returned_params = ([], [], [], [])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=26)

        self.assertEqual(expected_returned_params, returned_params)

    def test_dark_and_up_time_body_never_above_horizon(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_dark_and_up_time = None
        expected_emp_dark_and_up = []

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size = '5 m')
        dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)

        self.assertEqual(expected_dark_and_up_time, dark_and_up_time)
        self.assertEqual(expected_emp_dark_and_up, emp_dark_and_up)

    def test_dark_and_up_time_body_above_horizon(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_dark_and_up_time = 5.25
        expected_emp_dark_and_up_first_line = ['2017 01 06 01:20', '02 13 50.14', '+31 54 14.0', '21.0', ' 4.69', '+79', '0.52', ' 31', '+62', '+059', '-00:47']

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size = '5 m')
        dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)

        self.assertEqual(expected_dark_and_up_time, dark_and_up_time)
        self.assertEqual(expected_emp_dark_and_up_first_line, emp_dark_and_up[0])

    def test_compute_max_altitude(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_max_alt = 88

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size = '5 m')
        dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)

        max_alt = compute_max_altitude(emp_dark_and_up)

        self.assertEqual(expected_max_alt, max_alt)

    def test_compute_max_altitude_not_up_and_dark(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_max_alt = 0

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size = '5 m')
        dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)

        max_alt = compute_max_altitude(emp_dark_and_up)

        self.assertEqual(expected_max_alt, max_alt)


class TestDetermineSlotLength(TestCase):

    def test_bad_site_code(self):
        site_code = 'foo'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 0
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_good1m_lc(self):
        site_code = 'k91'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_good1m(self):
        site_code = 'K91'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_good1m(self):
        site_code = 'K92'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 20
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_good1m(self):
        site_code = 'K93'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 22.5
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_good1m(self):
        site_code = 'V37'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 25
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_good1m(self):
        site_code = 'W85'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 30
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_good1m(self):
        site_code = 'W86'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 40
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_reallyfaint_nonNEOWISE_good1m(self):
        site_code = 'W87'
        name = 'WH2845B'
        mag = 22.1
        expected_length = 45
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_nonNEOWISE_good1m(self):
        site_code = 'W87'
        name = 'WH2845B'
        mag = 23.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(name, mag, site_code)

    def test_slot_length_toobright_nonNEOWISE_good1m(self):
        site_code = 'W87'
        name = 'WH2845B'
        mag = 3.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(name, mag, site_code)

    def test_slot_length_very_bright_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 17.5
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 22.5
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 25
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 27.5
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 32.5
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 35
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_for_coj_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 22.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(name, mag, site_code)

    def test_slot_length_toofaint_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 23.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(name, mag, site_code)

    def test_slot_length_toobright_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 3.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(name, mag, site_code)

    def test_slot_length_very_bright_nonNEOWISE_2m_lc(self):
        site_code = 'f65'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_2m(self):
        site_code = 'E10'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_2m(self):
        site_code = 'E10'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 20
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_2m(self):
        site_code = 'E10'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 22.5
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 25
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 27.5
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 30
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_reallyfaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 23.2
        expected_length = 35
        slot_length = determine_slot_length(name, mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 23.4
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(name, mag, site_code)

    def test_slot_length_toobright_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 3.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(name, mag, site_code)

class TestGetSiteCamParams(TestCase):

    twom_setup_overhead = 180.0
    twom_exp_overhead = 22.5
    twom_fov = radians(10.0/60.0)
    onem_sbig_fov = radians(15.5/60.0)
    onem_setup_overhead = 120.0
    onem_exp_overhead = 15.5
    sinistro_exp_overhead = 48.0
    onem_sinistro_fov = radians(26.4/60.0)
    point4m_fov = radians(29.1/60.0)
    point4m_exp_overhead = 13.0
    point4m_setup_overhead = 120.0
    max_exp = 300.0

    def test_bad_site(self):
        site_code = 'wibble'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual('XXX', chk_site_code)
        self.assertEqual(-1, pixel_scale)
        self.assertEqual(-1, max_exp_time)
        self.assertEqual(-1, setup_overhead)
        self.assertEqual(-1, exp_overhead)

    def test_2m_site(self):
        site_code = 'f65'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.304, pixel_scale)
        self.assertEqual(self.twom_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.twom_setup_overhead, setup_overhead)
        self.assertEqual(self.twom_exp_overhead, exp_overhead)

    def test_2m_sitename(self):
        site_code = 'F65'

        site_string = 'OGG-CLMA-2M0A'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_string)
        self.assertEqual(site_code, chk_site_code)
        self.assertEqual(0.304, pixel_scale)
        self.assertEqual(self.twom_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.twom_setup_overhead, setup_overhead)
        self.assertEqual(self.twom_exp_overhead, exp_overhead)

    def test_1m_site_sinistro_domea(self):
        site_code = 'W85'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)
        self.assertEqual(self.max_exp, max_exp_time)

    def test_1m_lsc_site_sinistro(self):
        site_code = 'W86'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)

    def test_point4m_site(self):
        site_code = 'Z21'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(1.139, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site2(self):
        site_code = 'T04'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(1.139, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site3(self):
        site_code = 'Q59'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(1.139, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_1m_cpt_site_sinistro1(self):
        site_code = 'K92'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)

    def test_1m_cpt_site_sinistro2(self):
        site_code = 'K93'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)

class TestDetermineExpTimeCount(TestCase):

    def test_slow_1m(self):
        speed = 2.52
        site_code = 'W85'
        slot_len = 22.5

        expected_exptime = 60.0
        expected_expcount = 11

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_fast_1m(self):
        speed = 23.5
        site_code = 'K91'
        slot_len = 20

        expected_exptime = 6.5
        expected_expcount = 19

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_superslow_1m(self):
        speed = 0.235
        site_code = 'W85'
        slot_len = 20

        expected_exptime = 222.0
        expected_expcount = 4

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_superfast_2m(self):
        speed = 1800.0
        site_code = 'E10'
        slot_len = 15

        expected_exptime = 1.0
        expected_expcount = 30

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_block_too_short(self):
        speed = 0.18
        site_code = 'F65'
        slot_len = 2

        expected_exptime = None
        expected_expcount = None

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_slow_point4m(self):
        speed = 2.52
        site_code = 'Z21'
        slot_len = 22.5

        expected_exptime = 20.0
        expected_expcount = 37

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_fast_point4m(self):
        speed = 23.5
        site_code = 'Z21'
        slot_len = 20

        expected_exptime = 2.0
        expected_expcount = 72

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

class TestGetSitePos(TestCase):

    def test_tenerife_point4m_num1_by_code(self):
        site_code = 'Z21'

        expected_site_name = 'LCOGT TFN Node 0m4a Aqawan A at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_tenerife_point4m_num1_by_name(self):
        site_code = 'TFN-AQWA-0M4A'

        expected_site_name = 'LCOGT TFN Node 0m4a Aqawan A at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_tenerife_unknown_point4m_num2_by_name(self):
        site_code = 'TFN-AQWA-0M4B'

        expected_site_name = '?'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual('LCOGT TFN Node 0m4a Aqawan A at Tenerife', site_name)
        self.assertNotEqual('LCOGT TFN Node 0m4b Aqawan A at Tenerife', site_name)
        self.assertEqual(0.0, site_long)
        self.assertEqual(0.0, site_lat)
        self.assertEqual(0.0, site_hgt)

    def test_maui_point4m_num2_by_code(self):
        site_code = 'T04'

        expected_site_name = 'LCOGT OGG Node 0m4b at Maui'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_maui_point4m_num2_by_name(self):
        site_code = 'OGG-CLMA-0M4B'

        expected_site_name = 'LCOGT OGG Node 0m4b at Maui'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual('Haleakala-Faulkes Telescope North (FTN)', site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_aust_point4m_num2_by_code(self):
        site_code = 'Q59'

        expected_site_name = 'LCOGT COJ Node 0m4b at Siding Spring'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertGreater(site_long, 0.0)
        self.assertLess(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_aust_point4m_num2_by_name(self):
        site_code = 'COJ-CLMA-0M4B'

        expected_site_name = 'LCOGT COJ Node 0m4b at Siding Spring'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertGreater(site_long, 0.0)
        self.assertLess(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)
