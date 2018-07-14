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

from datetime import datetime
from math import radians
import mock

from django.test import TestCase
from django.forms.models import model_to_dict
from math import radians

# Import module to test
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
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('COJ-CLMA-0M4B')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site6(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('TFN-AQWA-0M4A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site7(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('LSC-AQWB-0M4A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site9(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('ELP-AQWA-0M4A')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site8(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('CPT-AQWA-0M4A')
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

    def test_point4m_by_site_code4(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('Q58')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code5(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('T03')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code6(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('Z17')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code7(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('W89')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code8(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('V38')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code9(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('L09')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '0.4m')

    def test_point4m_by_site_code10(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('W79')
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

        self.elements = {'slope': 0.15,
                         'abs_mag': 21.0,
                         'MDM': 0.74394528,
                         'argofperih': 85.19251,
                         'eccentricity': 0.1896865,
                         'epochofel': datetime(2015, 3, 19, 0, 0, 0),
                         'orbinc': 8.34739,
                         'longascnode': 147.81325,
                         'meananom': 325.2636,
                         'n_nights': 3,
                         'n_obs': 17,
                         'n_oppos': 1,
                         'name': 'N007r0q',
                         'reference': '',
                         'residual': 0.53,
                         'meandist': 1.2176312,
                         'type': 'MPC_MINOR_PLANET',
                         'uncertainty': 'U'}

        self.length_emp_line = 8

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
        expected_spd = 119.94694444444444
        expected_pa = 91.35793788996334

        emp_line = compute_ephem(d, self.elements, '500', dbg=False, perturb=True, display=False)

        self.assertEqual(self.length_emp_line, len(emp_line))
        self.assertEqual(d, emp_line[0])
        precision = 11
        self.assertAlmostEqual(expected_ra, emp_line[1], precision)
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_mag, emp_line[3], precision)
        self.assertAlmostEqual(expected_motion, emp_line[4], precision)
        self.assertAlmostEqual(expected_alt, emp_line[5], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)
        self.assertAlmostEqual(expected_pa,  emp_line[7], precision)

    def test_compute_ephem_with_body(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_ra  = 5.28722753669144
        expected_dec = 0.522637696108887
        expected_mag = 20.408525362626005
        expected_motion = 2.4825093417658186
        expected_alt =  -58.658929026981895
        expected_spd = 119.94694444444444
        expected_pa  = 91.35793788996334

        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)

        self.assertEqual(self.length_emp_line, len(emp_line))
        self.assertEqual(d, emp_line[0])
        precision = 11
        self.assertAlmostEqual(expected_ra, emp_line[1], precision)
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_mag, emp_line[3], precision)
        self.assertAlmostEqual(expected_motion, emp_line[4], precision)
        self.assertAlmostEqual(expected_alt, emp_line[5], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)
        self.assertAlmostEqual(expected_pa,  emp_line[7], precision)
        
    def test_compute_south_polar_distance_with_elements_in_north(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = 0.522637696108887
        expected_spd = 119.94694444444444
        emp_line = compute_ephem(d, self.elements, '500', dbg=False, perturb=True, display=False)
        precision = 11
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)
        
    def test_compute_south_polar_distance_with_body_in_north(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = 0.522637696108887
        expected_spd = 119.94694444444444
        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)
        precision = 11
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)

    def test_compute_south_polar_distance_with_body_in_south(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = -0.06554641803516298
        expected_spd = 86.242222222222225
        body_elements = model_to_dict(self.body)
        body_elements['meananom'] = 25.2636
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)
        precision = 11
        self.assertAlmostEqual(expected_dec, emp_line[2], precision)
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)

    def test_call_compute_ephem_with_body(self):
        start = datetime(2015, 4, 21, 8, 45, 00)
        end = datetime(2015, 4, 21,  8, 51, 00)
        site_code = 'V37'
        step_size = 300
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 04 21 08:45', '20 10 05.99', '+29 56 57.5', '20.4', ' 2.43', ' 89.2', '+33', '0.09', '107', '-42', '+047', '-04:25'],
                                ['2015 04 21 08:50', '20 10 06.92', '+29 56 57.7', '20.4', ' 2.42', ' 89.2', '+34', '0.09', '107', '-42', '+048', '-04:20']]
        ephem_lines = call_compute_ephem(body_elements, start, end, site_code, step_size)

        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_with_body_F65(self):
        start = datetime(2015, 4, 21, 11, 30, 00)
        end = datetime(2015, 4, 21, 11, 35, 1)
        site_code = 'F65'
        step_size = 300
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 04 21 11:30', '20 10 38.15', '+29 56 52.1', '20.4', ' 2.45', ' 89.0', '+20', '0.09', '108', '-47', '-999', '-05:09'],
                                ['2015 04 21 11:35', '20 10 39.09', '+29 56 52.4', '20.4', ' 2.45', ' 89.0', '+21', '0.09', '108', '-48', '-999', '-05:04']]

        ephem_lines = call_compute_ephem(body_elements, start, end, site_code, step_size)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_with_date(self):
        start = datetime(2015, 4, 28, 10, 20, 00)
        end = datetime(2015, 4, 28, 10, 25, 1)
        site_code = 'V37'
        step_size = 300
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 04 28 10:20', '20 40 36.53', '+29 36 33.1', '20.6', ' 2.08', ' 93.4', '+52', '0.72', '136', '-15', '+058', '-02:53'],
                                ['2015 04 28 10:25', '20 40 37.32', '+29 36 32.5', '20.6', ' 2.08', ' 93.4', '+54', '0.72', '136', '-16', '+059', '-02:48']]

        ephem_lines = call_compute_ephem(body_elements, start, end, site_code, step_size)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_ephem_with_altlimit(self):
        start = datetime(2015, 9, 1, 17, 20, 00)
        end = datetime(2015, 9, 1, 19, 50, 1)
        site_code = 'K91'
        step_size = 300
        alt_limit = 30.0
        body_elements = model_to_dict(self.body)
        expected_ephem_lines = [['2015 09 01 19:45', '23 56 43.16', '-11 31 02.4', '19.3', ' 1.91', '212.2', '+30', '0.86', ' 29', '+01', '+029', '-04:06'],
                                ['2015 09 01 19:50', '23 56 42.81', '-11 31 10.5', '19.3', ' 1.91', '212.2', '+31', '0.86', ' 29', '+02', '+030', '-04:01']]

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
        expected_ephem_lines = [['2015 07 05 07:20', '23 49 59.84', '+19 04 06.3', '20.7', ' 1.23',  '122.4', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'], ]

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
        expected_ephem_lines = [['2015 10 30 12:20', '10 44 56.44', '+14 13 30.6', '14.7', ' 1.44', '107.6', '+1', '0.87', ' 79', '+79', '-999', '-06:16'], ]

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
        expected_ephem_lines = [['2015 10 30 12:20', '10 44 56.44', '+14 13 30.6', '-99.0', ' 1.44', '107.6', '+1', '0.87', ' 79', '+79', '-999', '-06:16'], ]

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
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)
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
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)

        FOM = comp_FOM(body_elements, emp_line)

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_NoScore(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_FOM = None
        body_elements = model_to_dict(self.body)
        body_elements['score'] = None
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)

        FOM = comp_FOM(body_elements, emp_line)

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_wrong_source_type(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_FOM = None
        body_elements = model_to_dict(self.body)
        body_elements['source_type'] = 'N'
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)

        FOM = comp_FOM(body_elements, emp_line)

        self.assertEqual(expected_FOM, FOM)

    def test_FOM_with_zero_arclength(self):
        d = datetime(2015, 11, 2, 19, 46, 9)
        expected_FOM = 1.658839108423487e+75
        body_elements = model_to_dict(self.body2)
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)

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
        # Body is only up for a few days starting at the
        # beginning of the search.
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_returned_params = (['2017 01 06', '2017 01 09'], [['2017 01 06 01:20', '02 13 50.14', '+31 54 14.0', '21.0', ' 4.69', '240.8', '+79', '0.52', ' 31', '+62', '+059', '-00:47'], ['2017 01 09 01:20', '01 52 45.62', '+29 03 29.1', '21.2', ' 4.51', '237.6', '+86', '0.84', ' 33', '+53', '+069', '-00:14']], [5.25, 4.666666666666667], [88, 88])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=5)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body_no_dark_and_up_emp(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_returned_params = ([], [], [], [])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=5)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body_no_emp(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_returned_params = ([], [], [], [])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 2, 27, 0, 0, 00), date_range=3)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body2(self):
        # Body is up for a couple days when gets faint enough,
        # but then moon gets full. Body becomes observable again
        # after moon "fades" until no longer up for at least 3 hrs.
        site_code = 'V37'
        body_elements = model_to_dict(self.body2)

        expected_returned_params = (['2017 01 09', '2017 01 16', '2017 01 17', '2017 01 18', '2017 01 19', '2017 01 20', '2017 01 21', '2017 01 22', '2017 01 23', '2017 01 24'], [['2017 01 09 08:30', '11 07 53.60', '-19 20 19.8', '21.5', ' 1.03', '162.0', '+30', '0.86', '106', '+26', '+021', '-02:18'], ['2017 01 16 08:25', '11 11 11.23', '-22 01 59.9', '21.3', ' 0.97', '172.4', '+30', '0.82', ' 28', '+53', '+012', '-01:59'], ['2017 01 17 08:25', '11 11 28.60', '-22 24 52.3', '21.3', ' 0.97', '174.1', '+30', '0.74', ' 27', '+42', '+016', '-01:55'], ['2017 01 18 08:25', '11 11 43.01', '-22 47 39.7', '21.2', ' 0.96', '175.9', '+30', '0.64', ' 31', '+31', '+020', '-01:51'], ['2017 01 19 08:25', '11 11 54.34', '-23 10 21.4', '21.2', ' 0.96', '177.8', '+30', '0.55', ' 38', '+20', '+023', '-01:48'], ['2017 01 20 08:25', '11 12 02.53', '-23 32 56.7', '21.2', ' 0.95', '179.7', '+30', '0.45', ' 47', '+09', '+027', '-01:44'], ['2017 01 21 08:25', '11 12 07.47', '-23 55 24.9', '21.1', ' 0.95', '181.7', '+30', '0.36', ' 56', '-01', '+030', '-01:40'], ['2017 01 22 08:25', '11 12 09.07', '-24 17 45.2', '21.1', ' 0.94', '183.7', '+30', '0.27', ' 66', '-11', '+034', '-01:36'], ['2017 01 23 08:20', '11 12 07.27', '-24 39 52.1', '21.1', ' 0.94', '185.8', '+30', '0.19', ' 76', '-22', '+037', '-01:37'], ['2017 01 24 08:20', '11 12 01.93', '-25 01 54.1', '21.0', ' 0.93', '188.0', '+30', '0.12', ' 86', '-33', '+041', '-01:33']], [4.083333333333333, 3.9166666666666665, 3.8333333333333335, 3.6666666666666665, 3.5833333333333335, 3.4166666666666665, 3.3333333333333335, 3.1666666666666665, 3.1666666666666665, 3.0], [39, 37, 36, 36, 36, 35, 35, 34, 34, 34])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 8, 0, 0, 00), date_range=18)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body2_shorter_time_limit(self):
        # Body is up for a couple days when gets faint enough,
        # but then moon gets full. Body becomes observable again
        # after moon "fades" until no longer up for at least 3 hrs.
        site_code = 'V37'
        body_elements = model_to_dict(self.body2)

        expected_returned_params = (['2017 01 09', '2017 01 16', '2017 01 17', '2017 01 18', '2017 01 19', '2017 01 20', '2017 01 21', '2017 01 22', '2017 01 23', '2017 01 24', '2017 01 25', '2017 01 26', '2017 01 27', '2017 01 28'], [['2017 01 09 08:30', '11 07 53.60', '-19 20 19.8', '21.5', ' 1.03', '162.0', '+30', '0.86', '106', '+26', '+021', '-02:18'], ['2017 01 16 08:25', '11 11 11.23', '-22 01 59.9', '21.3', ' 0.97', '172.4', '+30', '0.82', ' 28', '+53', '+012', '-01:59'], ['2017 01 17 08:25', '11 11 28.60', '-22 24 52.3', '21.3', ' 0.97', '174.1', '+30', '0.74', ' 27', '+42', '+016', '-01:55'], ['2017 01 18 08:25', '11 11 43.01', '-22 47 39.7', '21.2', ' 0.96', '175.9', '+30', '0.64', ' 31', '+31', '+020', '-01:51'], ['2017 01 19 08:25', '11 11 54.34', '-23 10 21.4', '21.2', ' 0.96', '177.8', '+30', '0.55', ' 38', '+20', '+023', '-01:48'], ['2017 01 20 08:25', '11 12 02.53', '-23 32 56.7', '21.2', ' 0.95', '179.7', '+30', '0.45', ' 47', '+09', '+027', '-01:44'], ['2017 01 21 08:25', '11 12 07.47', '-23 55 24.9', '21.1', ' 0.95', '181.7', '+30', '0.36', ' 56', '-01', '+030', '-01:40'], ['2017 01 22 08:25', '11 12 09.07', '-24 17 45.2', '21.1', ' 0.94', '183.7', '+30', '0.27', ' 66', '-11', '+034', '-01:36'], ['2017 01 23 08:20', '11 12 07.27', '-24 39 52.1', '21.1', ' 0.94', '185.8', '+30', '0.19', ' 76', '-22', '+037', '-01:37'], ['2017 01 24 08:20', '11 12 01.93', '-25 01 54.1', '21.0', ' 0.93', '188.0', '+30', '0.12', ' 86', '-33', '+041', '-01:33'], ['2017 01 25 08:20', '11 11 52.97', '-25 23 45.5', '21.0', ' 0.93', '190.2', '+30', '0.07', ' 96', '-43', '+044', '-01:29'], ['2017 01 26 08:20', '11 11 40.31', '-25 45 25.4', '21.0', ' 0.93', '192.5', '+30', '0.03', '107', '-53', '+047', '-01:25'], ['2017 01 27 08:20', '11 11 23.85', '-26 06 52.7', '20.9', ' 0.93', '194.8', '+30', '0.00', '117', '-62', '+050', '-01:21'], ['2017 01 28 08:20', '11 11 03.50', '-26 28 06.2', '20.9', ' 0.93', '197.2', '+30', '0.00', '127', '-70', '+053', '-01:16']], [4.083333333333333, 3.9166666666666665, 3.8333333333333335, 3.6666666666666665, 3.5833333333333335, 3.4166666666666665, 3.3333333333333335, 3.1666666666666665, 3.1666666666666665, 3.0, 2.9166666666666665, 2.75, 2.6666666666666665, 2.5], [39, 37, 36, 36, 36, 35, 35, 34, 34, 34, 33, 33, 33, 32])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 8, 0, 0, 00), date_range=20, dark_and_up_time_limit=2.5)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body3(self):
        # Body is not observable (because not up for >3 hrs) until
        # sometime after start of search and then until the end of
        # the date range.
        site_code = 'V37'
        body_elements = model_to_dict(self.body3)

        expected_returned_params = (['2017 01 21', '2017 01 22', '2017 01 23', '2017 01 24', '2017 01 25', '2017 01 26'], [['2017 01 21 08:15', '13 31 15.01', '+13 18 31.1', '18.2', ' 8.80', '311.3', '+30', '0.36', ' 35', '-03', '+031', '-04:09'], ['2017 01 22 07:55', '13 20 59.76', '+15 30 00.5', '18.1', ' 8.43', '310.7', '+30', '0.27', ' 48', '-17', '+036', '-04:15'], ['2017 01 23 07:40', '13 10 56.80', '+17 33 59.8', '18.1', ' 8.04', '310.0', '+30', '0.20', ' 62', '-31', '+041', '-04:16'], ['2017 01 24 07:20', '13 01 11.14', '+19 29 22.9', '18.0', ' 7.65', '309.2', '+30', '0.13', ' 76', '-45', '+045', '-04:22'], ['2017 01 25 07:05', '12 51 39.02', '+21 16 57.8', '18.0', ' 7.25', '308.2', '+30', '0.07', ' 89', '-58', '+050', '-04:24'], ['2017 01 26 06:50', '12 42 22.99', '+22 56 25.1', '18.0', ' 6.87', '307.3', '+31', '0.03', '103', '-70', '+054', '-04:26']], [4.333333333333333, 4.666666666666667, 4.916666666666667, 5.25, 5.5, 5.75], [73, 75, 77, 79, 80, 82])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 19, 0, 0, 00), date_range=7)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body4(self):
        # Body is not observable (because too faint) until
        # sometime after start of search and then until the end of
        # the date range.
        site_code = 'V37'
        body_elements = model_to_dict(self.body4)

        expected_returned_params = (['2017 01 26', '2017 01 27', '2017 01 28', '2017 01 29', '2017 01 30'], [['2017 01 26 06:40', '10 53 54.75', '-13 15 07.5', '21.5', ' 4.76', '294.8', '+30', '0.03', '116', '-72', '+054', '-02:47'], ['2017 01 27 06:25', '10 47 10.72', '-12 24 58.0', '21.4', ' 4.96', '295.4', '+30', '0.01', '129', '-76', '+055', '-02:52'], ['2017 01 28 06:10', '10 40 12.85', '-11 31 37.6', '21.3', ' 5.15', '296.1', '+30', '0.00', '141', '-68', '+052', '-02:56'], ['2017 01 29 05:55', '10 33 01.97', '-10 35 07.5', '21.2', ' 5.34', '296.7', '+30', '0.02', '153', '-55', '+048', '-03:00'], ['2017 01 30 05:40', '10 25 39.12', '-09 35 32.1', '21.1', ' 5.52', '297.3', '+30', '0.05', '160', '-40', '+043', '-03:03']], [5.583333333333333, 5.666666666666667, 5.833333333333333, 5.916666666666667, 6.083333333333333], [46, 47, 47, 48, 49])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 25, 0, 0, 00), date_range=5)

        self.assertEqual(expected_returned_params, returned_params)

    def test_LongTermScheduling_with_body5(self):
        # Body is not observable (because too faint) at
        # any time in the date range.
        site_code = 'V37'
        body_elements = model_to_dict(self.body5)

        expected_returned_params = ([], [], [], [])

        returned_params = monitor_long_term_scheduling(site_code, body_elements, utc_date=datetime(2017, 1, 6, 0, 0, 00), date_range=7)

        self.assertEqual(expected_returned_params, returned_params)

    def test_dark_and_up_time_body_never_above_horizon(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_dark_and_up_time = None
        expected_emp_dark_and_up = []

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)
        dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)

        self.assertEqual(expected_dark_and_up_time, dark_and_up_time)
        self.assertEqual(expected_emp_dark_and_up, emp_dark_and_up)

    def test_dark_and_up_time_body_above_horizon(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_dark_and_up_time = 5.25
        expected_emp_dark_and_up_first_line = ['2017 01 06 01:20', '02 13 50.14', '+31 54 14.0', '21.0', ' 4.69', '240.8', '+79', '0.52', ' 31', '+62', '+059', '-00:47']

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)
        dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)

        self.assertEqual(expected_dark_and_up_time, dark_and_up_time)
        self.assertEqual(expected_emp_dark_and_up_first_line, emp_dark_and_up[0])

    def test_compute_max_altitude(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_max_alt = 88

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)
        dark_and_up_time = compute_dark_and_up_time(emp)

        max_alt = compute_max_altitude(emp)

        self.assertEqual(expected_max_alt, max_alt)

    def test_compute_max_altitude_not_up_and_dark(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_max_alt = 0

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)
        dark_and_up_time = compute_dark_and_up_time(emp)

        max_alt = compute_max_altitude(emp)

        self.assertEqual(expected_max_alt, max_alt)


class TestDetermineRatesAndPA(TestCase):

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
        self.body_elements = model_to_dict(self.body)

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
        self.comet_elements = model_to_dict(self.comet)

        close_params = { 'abs_mag': 25.8,
                         'active': True,
                         'arc_length': 0.03,
                         'argofperih': 11.00531,
                         'discovery_date': datetime(2017, 1, 24, 4, 48),
                         'eccentricity': 0.5070757,
                         'elements_type': u'MPC_MINOR_PLANET',
                         'epochofel': datetime(2017, 1, 7, 0, 0),
                         'epochofperih': None,
                         'longascnode': 126.11232,
                         'meananom': 349.70053,
                         'meandist': 2.0242057,
                         'orbinc': 12.91839,
                         'origin': u'M',
                         'perihdist': None,
                         'provisional_name': u'P10yMB1',
                         'slope': 0.15,
                         'source_type': u'U',
                         'updated': True,
                         'urgency': None}
        self.close, created = Body.objects.get_or_create(**close_params)
        self.close_elements = model_to_dict(self.close)

        yark_params = {  'abs_mag': 24.7,
                         'active': True,
                         'arc_length': 2148.0,
                         'argofperih': 169.66953,
                         'discovery_date': datetime(2011, 3, 12, 0, 0),
                         'eccentricity': 0.3077038,
                         'elements_type': u'MPC_MINOR_PLANET',
                         'epochofel': datetime(2017, 2, 16, 0, 0),
                         'epochofperih': None,
                         'fast_moving': False,
                         'ingest': datetime(2017, 1, 31, 22, 52, 33, 38551),
                         'longascnode': 160.05822,
                         'meananom': 171.81857,
                         'meandist': 0.8280978,
                         'name': u'2011 EP51',
                         'not_seen': 4.95316023288194,
                         'num_obs': 34,
                         'orbinc': 3.4119,
                         'origin': u'M',
                         'perihdist': None,
                         'provisional_name': None,
                         'provisional_packed': None,
                         'score': None,
                         'slope': 0.15,
                         'source_type': u'N',
                         'update_time': datetime(2017, 1, 27, 0, 0),
                         'updated': True,
                         'urgency': None}
        self.yark_target, created = Body.objects.get_or_create(**yark_params)
        self.yark_elements = model_to_dict(self.yark_target)

        perturb_params = { 'abs_mag': 30.1,
                        'active': False,
                        'arc_length': 0.04,
                        'argofperih': 88.46163,
                        'discovery_date': datetime(2018, 5, 8, 9, 36),
                        'eccentricity': 0.5991733,
                        'elements_type': 'MPC_MINOR_PLANET',
                        'epochofel': datetime(2018, 5, 2, 0, 0),
                        'epochofperih': None,
                        'fast_moving': False,
                        'ingest': datetime(2018, 5, 8, 18, 20, 12),
                        'longascnode': 47.25654,
                        'meananom': 23.36326,
                        'meandist': 1.5492508,
                        'name': '',
                        'not_seen': 0.378,
                        'num_obs': 5,
                        'orbinc': 8.13617,
                        'origin': 'M',
                        'perihdist': None,
                        'provisional_name': 'A106MHy',
                        'provisional_packed': None,
                        'score': 100,
                        'slope': 0.15,
                        'source_type': 'X',
                        'update_time': datetime(2018, 5, 8, 18, 9, 43),
                        'updated': False,
                        'urgency': None}
        self.perturb_target, created = Body.objects.get_or_create(**perturb_params)
        self.perturb_elements = model_to_dict(self.perturb_target)

        self.precision = 4

    def test_neo_Q64(self):
        expected_minrate = 2.531733441262908 - (0.01*2.531733441262908)
        expected_maxrate = 2.5546060130918056 + (0.01*2.5546060130918056)
        expected_pa = (92.46770128867529+92.49478201324034)/2.0
        expected_deltapa = 10.0

        start_time = datetime(2015, 4, 20, 1, 30, 0)
        end_time = datetime(2015, 4, 20, 2, 00, 0)
        site_code = 'Q64'
        minrate, maxrate, pa, deltapa = determine_rates_pa(start_time, end_time, self.body_elements, site_code)

        self.assertAlmostEqual(expected_minrate, minrate, self.precision)
        self.assertAlmostEqual(expected_maxrate, maxrate, self.precision)
        self.assertAlmostEqual(expected_pa, pa, self.precision)
        self.assertAlmostEqual(expected_deltapa, deltapa, self.precision)

    def test_close_neo_W86(self):
        expected_minrate = 11.168352251337911 - (0.01*11.168352251337911)
        expected_maxrate = 11.235951320053525 + (0.01*11.235951320053525)
        expected_pa = (359.4874655767052+(0.26203084523351095+360.0))/2.0
        expected_deltapa = 10.0

        start_time = datetime(2017, 1, 25, 7, 00, 0)
        end_time = datetime(2017, 1, 25, 7, 50, 0)
        site_code = 'W86'
        minrate, maxrate, pa, deltapa = determine_rates_pa(start_time, end_time, self.close_elements, site_code)

        self.assertAlmostEqual(expected_minrate, minrate, self.precision)
        self.assertAlmostEqual(expected_maxrate, maxrate, self.precision)
        self.assertAlmostEqual(expected_pa, pa, self.precision)
        self.assertAlmostEqual(expected_deltapa, deltapa, self.precision)

    def test_yark_target_bad_pa(self):
        expected_minrate = 5.048257569072863 - (0.01*5.048257569072863)
        expected_maxrate = 5.072223332592448 + (0.01*5.072223332592448)
        expected_pa = (295.5850631246814+295.56445469665186)/2.0
        expected_deltapa = 10.0

        start_time = datetime(2017, 1, 27, 13, 57, 0)
        end_time =   datetime(2017, 1, 27, 14, 21, 0)
        site_code = 'Q63'
        minrate, maxrate, pa, deltapa = determine_rates_pa(start_time, end_time, self.yark_elements, site_code)

        self.assertAlmostEqual(expected_minrate, minrate, self.precision)
        self.assertAlmostEqual(expected_maxrate, maxrate, self.precision)
        self.assertAlmostEqual(expected_pa, pa, self.precision)
        self.assertAlmostEqual(expected_deltapa, deltapa, self.precision)

    def test_perturb_error(self):
        expected_minrate = 1.2072179264460565 - (0.01*1.2072179264460565)
        expected_maxrate = 1.3456142840902674 + (0.01*1.3456142840902674)
        expected_pa = (309.8080216233171+320.9860119849485)/2.0
        expected_deltapa = 11.17799036163143

        start_time = datetime(2018, 5, 9, 7, 11, 12, 181000)
        end_time =   datetime(2018, 5, 9, 7, 38, 14, 888000)
        site_code = 'W87'
        minrate, maxrate, pa, deltapa = determine_rates_pa(start_time, end_time, self.perturb_elements, site_code)

        self.assertAlmostEqual(expected_minrate, minrate, self.precision)
        self.assertAlmostEqual(expected_maxrate, maxrate, self.precision)
        self.assertAlmostEqual(expected_pa, pa, self.precision)
        self.assertAlmostEqual(expected_deltapa, deltapa, self.precision)

class TestDetermineSlotLength(TestCase):

    def test_bad_site_code(self):
        site_code = 'foo'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 0
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_good1m_lc(self):
        site_code = 'k91'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_good1m(self):
        site_code = 'K91'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_good1m(self):
        site_code = 'K92'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 20
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_good1m(self):
        site_code = 'K93'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 22.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_good1m(self):
        site_code = 'V37'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_good1m(self):
        site_code = 'W85'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 30
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_good1m(self):
        site_code = 'W86'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 40
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_reallyfaint_nonNEOWISE_good1m(self):
        site_code = 'W87'
        name = 'WH2845B'
        mag = 22.1
        expected_length = 45
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_nonNEOWISE_good1m(self):
        site_code = 'W87'
        name = 'WH2845B'
        mag = 23.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(mag, site_code)

    def test_slot_length_toobright_nonNEOWISE_good1m(self):
        site_code = 'W87'
        name = 'WH2845B'
        mag = 3.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(mag, site_code)

    def test_slot_length_very_bright_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 17.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 22.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 27.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_bad1m(self):
        site_code = 'Q63'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 32.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 35
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_for_coj_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 22.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(mag, site_code)

    def test_slot_length_toofaint_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 23.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(mag, site_code)

    def test_slot_length_toobright_nonNEOWISE_bad1m(self):
        site_code = 'Q64'
        name = 'WH2845B'
        mag = 3.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(mag, site_code)

    def test_slot_length_very_bright_nonNEOWISE_2m_lc(self):
        site_code = 'f65'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 10
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_2m(self):
        site_code = 'E10'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 10
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_2m(self):
        site_code = 'E10'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 20
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_2m(self):
        site_code = 'E10'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 22.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 27.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 30
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_reallyfaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 23.2
        expected_length = 35
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 23.4
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(mag, site_code)

    def test_slot_length_toobright_nonNEOWISE_2m(self):
        site_code = 'F65'
        name = 'WH2845B'
        mag = 3.1
        with self.assertRaises(MagRangeError):
            slot_length = determine_slot_length(mag, site_code)

    def test_slot_length_basic_tfn_0m4_num1(self):
        site_code = 'Z21'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_tfn_0m4_num2(self):
        site_code = 'Z17'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_ogg_0m4_num1(self):
        site_code = 'T04'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_ogg_0m4_num2(self):
        site_code = 'T03'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_lsc_0m4_num1(self):
        site_code = 'W89'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_lsc_0m4_num2(self):
        site_code = 'W79'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_elp_0m4(self):
        site_code = 'V38'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_cpt_0m4(self):
        site_code = 'L09'
        name = 'A101foo'
        mag = 19.0

        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)


class TestGetSiteCamParams(TestCase):

    twom_setup_overhead = 240.0
    twom_exp_overhead = 19.0
    twom_fov = radians(10.0/60.0)
    onem_sbig_fov = radians(15.5/60.0)
    onem_setup_overhead = 90.0
    onem_exp_overhead = 15.5
    sinistro_exp_overhead = 38.0
    onem_sinistro_fov = radians(26.4/60.0)
    point4m_fov = radians(29.1/60.0)
    point4m_exp_overhead = 14.0
    point4m_setup_overhead = 90.0
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
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site2(self):
        site_code = 'T04'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site3(self):
        site_code = 'Q59'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site4(self):
        site_code = 'Q58'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site5(self):
        site_code = 'Z17'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site6(self):
        site_code = 'T03'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site7(self):
        site_code = 'W89'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site8(self):
        site_code = 'V38'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site9(self):
        site_code = 'L09'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
        self.assertEqual(self.point4m_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_exp_overhead, exp_overhead)

    def test_point4m_site10(self):
        site_code = 'W79'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.571, pixel_scale)
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
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 60.0
        expected_expcount = 12

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_bright_1m(self):
        speed = 0.52
        site_code = 'W85'
        slot_len = 10.0
        name = 'WH2845B'
        mag = 12.58

        expected_exptime = 85.0
        expected_expcount = 4

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_fast_1m(self):
        speed = 23.5
        site_code = 'K91'
        slot_len = 20
        name = 'WH2845B'
        mag = 16.58

        expected_exptime = 6.5
        expected_expcount = 24

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_superslow_1m(self):
        speed = 0.235
        site_code = 'W85'
        slot_len = 20
        name = 'WH2845B'
        mag = 21.2

        expected_exptime = 235.0
        expected_expcount = 4

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_superfast_2m(self):
        speed = 1800.0
        site_code = 'E10'
        slot_len = 15
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 1.0
        expected_expcount = 32

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_block_too_short(self):
        speed = 0.18
        site_code = 'F65'
        slot_len = 2
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = None
        expected_expcount = None

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_slow_point4m(self):
        speed = 2.52
        site_code = 'Z21'
        slot_len = 22.5
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 40.0
        expected_expcount = 23

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_fast_point4m(self):
        speed = 23.5
        site_code = 'Z21'
        slot_len = 20
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 4.0
        expected_expcount = 60

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)


class TestDetermineSpectroSlotLength(TestCase):

    def test_bright_no_calibs(self):

        exp_time = 180.0
        calibs = 'none'

        expected_slot_length = 612.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_before(self):

        exp_time = 180.0
        calibs = 'before'

        expected_slot_length = 935.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_after(self):

        exp_time = 180.0
        calibs = 'after'

        expected_slot_length = 935.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_both(self):

        exp_time = 180.0
        calibs = 'both'

        expected_slot_length = 1258.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_both_mixedcase(self):

        exp_time = 180.0
        calibs = 'BoTH'

        expected_slot_length = 1258.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)


class TestGetSitePos(TestCase):

    def test_tenerife_point4m_num1_by_code(self):
        site_code = 'Z21'

        expected_site_name = 'LCO TFN Node 0m4a Aqawan A at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_tenerife_point4m_num1_by_name(self):
        site_code = 'TFN-AQWA-0M4A'

        expected_site_name = 'LCO TFN Node 0m4a Aqawan A at Tenerife'

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
        self.assertNotEqual('LCO TFN Node 0m4a Aqawan A at Tenerife', site_name)
        self.assertNotEqual('LCO TFN Node 0m4b Aqawan A at Tenerife', site_name)
        self.assertEqual(0.0, site_long)
        self.assertEqual(0.0, site_lat)
        self.assertEqual(0.0, site_hgt)

    def test_maui_point4m_num2_by_code(self):
        site_code = 'T04'

        expected_site_name = 'LCO OGG Node 0m4b at Maui'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_maui_point4m_num2_by_name(self):
        site_code = 'OGG-CLMA-0M4B'

        expected_site_name = 'LCO OGG Node 0m4b at Maui'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual('Haleakala-Faulkes Telescope North (FTN)', site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_maui_point4m_num3_by_code(self):
        site_code = 'T03'

        expected_site_name = 'LCO OGG Node 0m4c at Maui'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_maui_point4m_num3_by_name(self):
        site_code = 'OGG-CLMA-0M4C'

        expected_site_name = 'LCO OGG Node 0m4c at Maui'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual('Haleakala-Faulkes Telescope North (FTN)', site_name)
        self.assertNotEqual('LCO OGG Node 0m4b at Maui', site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_aust_point4m_num1_by_code(self):
        site_code = 'Q58'

        expected_site_name = 'LCO COJ Node 0m4a at Siding Spring'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertGreater(site_long, 0.0)
        self.assertLess(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_aust_point4m_num1_by_name(self):
        site_code = 'COJ-CLMA-0M4A'

        expected_site_name = 'LCO COJ Node 0m4a at Siding Spring'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertGreater(site_long, 0.0)
        self.assertLess(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_aust_point4m_num2_by_code(self):
        site_code = 'Q59'

        expected_site_name = 'LCO COJ Node 0m4b at Siding Spring'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertGreater(site_long, 0.0)
        self.assertLess(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_aust_point4m_num2_by_name(self):
        site_code = 'COJ-CLMA-0M4B'

        expected_site_name = 'LCO COJ Node 0m4b at Siding Spring'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertGreater(site_long, 0.0)
        self.assertLess(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_geocenter(self):
        site_code = '500'

        expected_site_name = 'Geocenter'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertEqual(site_long, 0.0)
        self.assertEqual(site_lat, 0.0)
        self.assertEqual(site_hgt, 0.0)

    def test_bpl(self):
        site_code = 'BPL'

        expected_site_name = 'LCO Back Parking Lot Node (BPL)'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual(site_long, 0.0)
        self.assertNotEqual(site_lat, 0.0)
        self.assertNotEqual(site_hgt, 0.0)


class TestDetermineSitesToSchedule(TestCase):

    def test_CA_morning(self):
        '''Morning in CA so CPT and TFN should be open, ELP should be
        schedulable for Northern targets'''
        d = datetime(2017, 3,  9,  19, 27, 5)

        expected_sites = { 'north' : { '0m4' : ['Z21','Z17'], '1m0' : ['V37',] },
                           'south' : { '0m4' : ['L09', ]    , '1m0' : ['K93', 'K92', 'K91'] }
                         }

        sites = determine_sites_to_schedule(d)

        self.assertEqual(expected_sites, sites)

    def test_CA_afternoon1(self):
        '''Afternoon in CA (pre UTC date roll) so LSC should be opening, ELP
        should be schedulable for Northern targets, OGG for bright targets'''
        d = datetime(2017, 3,  9,  23, 27, 5)

        expected_sites = { 'north' : { '0m4' : ['T04', 'T03', 'V38'], '1m0' : ['V37',] },
                           'south' : { '0m4' : ['W89', 'W79'], '1m0' : ['W87', 'W85'] }
                         }

        sites = determine_sites_to_schedule(d)

        self.assertEqual(expected_sites, sites)

    def test_CA_afternoon2(self):
        '''Afternoon in CA (post UTC date roll) so LSC should be opening, ELP
        should be schedulable for Northern targets, OGG for bright targets'''

        d = datetime(2017, 3, 10,  00, 2, 5)

        expected_sites = { 'north' : { '0m4' : ['T04', 'T03', 'V38'], '1m0' : ['V37',] },
                           'south' : { '0m4' : ['W89', 'W79']       , '1m0' : ['W87', 'W85'] }
                         }

        sites = determine_sites_to_schedule(d)

        self.assertEqual(expected_sites, sites)

    def test_UK_morning(self):
        '''Morning in UK so COJ is open and a little bit of OGG 0.4m is available'''
        d = datetime(2017, 3,  10,  8, 27, 5)

        expected_sites = { 'north' : { '0m4' : ['T04', 'T03'], '1m0' : [ ] },
                           'south' : { '0m4' : ['Q58',], '1m0' : ['Q63', 'Q64'] }
                         }

        sites = determine_sites_to_schedule(d)

        self.assertEqual(expected_sites, sites)

    def test_UK_late_morning(self):
        '''Late morning in UK so only COJ is open; not enough time at the
        OGG 0.4m is available'''
        d = datetime(2017, 3,  10, 12,  0, 1)

        expected_sites = { 'north' : { '0m4' : [ ],         '1m0' : [ ] },
                           'south' : { '0m4' : [ 'Q58', ] , '1m0' : ['Q63', 'Q64'] }
                         }

        sites = determine_sites_to_schedule(d)

        self.assertEqual(expected_sites, sites)


class TestLCOGT_domes_to_site_codes(TestCase):

    def test_point4m_tfn_1(self):
        expected_code = 'Z21'

        code = LCOGT_domes_to_site_codes('tfn', 'aqwa', '0m4a')

        self.assertEqual(expected_code, code)

    def test_point4m_tfn_2(self):
        expected_code = 'Z17'

        code = LCOGT_domes_to_site_codes('tfn', 'aqwa', '0m4b')

        self.assertEqual(expected_code, code)

    def test_point4m_coj_1(self):
        expected_code = 'Q58'

        code = LCOGT_domes_to_site_codes('coj', 'clma', '0m4a')

        self.assertEqual(expected_code, code)

    def test_point4m_coj_2(self):
        expected_code = 'Q59'

        code = LCOGT_domes_to_site_codes('coj', 'clma', '0m4b')

        self.assertEqual(expected_code, code)

    def test_point4m_ogg_1(self):
        expected_code = 'T04'

        code = LCOGT_domes_to_site_codes('ogg', 'clma', '0m4b')

        self.assertEqual(expected_code, code)

    def test_point4m_ogg_2(self):
        expected_code = 'T03'

        code = LCOGT_domes_to_site_codes('ogg', 'clma', '0m4c')

        self.assertEqual(expected_code, code)


class TestMPC_site_codes_to_domes(TestCase):

    def test_point4m_tfn_1(self):
        e_siteid, e_encid, e_telid = 'tfn', 'aqwa', '0m4a'

        siteid, encid, telid = MPC_site_code_to_domes('Z21')

        self.assertEqual(e_siteid, siteid)
        self.assertEqual(e_encid, encid)
        self.assertEqual(e_telid, telid)

    def test_point4m_tfn_2(self):
        e_siteid, e_encid, e_telid = 'tfn', 'aqwa', '0m4b'

        siteid, encid, telid = MPC_site_code_to_domes('Z17')

        self.assertEqual(e_siteid, siteid)
        self.assertEqual(e_encid, encid)
        self.assertEqual(e_telid, telid)

    def test_1m_cpt_1(self):
        e_siteid, e_encid, e_telid = 'cpt', 'doma', '1m0a'

        siteid, encid, telid = MPC_site_code_to_domes('K91')

        self.assertEqual(e_siteid, siteid)
        self.assertEqual(e_encid, encid)
        self.assertEqual(e_telid, telid)

    def test_point4m_elp_1(self):
        e_siteid, e_encid, e_telid = 'elp', 'aqwa', '0m4a'

        siteid, encid, telid = MPC_site_code_to_domes('V38')

        self.assertEqual(e_siteid, siteid)
        self.assertEqual(e_encid, encid)
        self.assertEqual(e_telid, telid)

    def test_point4m_ogg_2(self):
        e_siteid, e_encid, e_telid = 'ogg', 'clma', '0m4b'

        siteid, encid, telid = MPC_site_code_to_domes('T04')

        self.assertEqual(e_siteid, siteid)
        self.assertEqual(e_encid, encid)
        self.assertEqual(e_telid, telid)


class Testmolecule_overhead(TestCase):

    def test_single_filter(self):
        filter_pattern = 'V'
        expected_overhead = (2. + 5. + 11.)*1
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 10)))

    def test_multiple_individual_filters(self):
        filter_pattern = 'V,R,I'
        expected_overhead = (2. + 5. + 11.)*10.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 10)))

    def test_multiple_repeated_filters(self):
        filter_pattern = 'V,R,I,V,R,I'
        expected_overhead = (2. + 5. + 11.)*10.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 10)))

    def test_multiple_filter_strings(self):
        filter_pattern = 'V,V,V,R,R,R,I,I,I,'
        expected_overhead = (2. + 5. + 11.)*5.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 14)))

    def test_short_block(self):
        filter_pattern = 'V,V,V,R,R,R,I,I,I,V'
        expected_overhead = (2. + 5. + 11.)*2.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 5)))

    def test_start_end_loop(self):
        filter_pattern = 'V,V,R,R,V,V'
        expected_overhead = (2. + 5. + 11.)*7.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 19)))

    def test_exact_loop(self):
        filter_pattern = 'V,V,R,R,I,I'
        expected_overhead = (2. + 5. + 11.)*9.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 18)))


class TestDetermineExpTimeCount_WithFilters(TestCase):

    def test_1m_alternating(self):
        speed = 2.52
        site_code = 'W85'
        slot_len = 22.5
        name = 'WH2845B'
        mag = 17.58
        filter_pattern = 'V,I'

        expected_exptime = 60.0
        expected_expcount = 10

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, filter_pattern)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_1m_long_pattern(self):
        speed = 2.52
        site_code = 'W85'
        slot_len = 22.5
        name = 'WH2845B'
        mag = 17.58
        filter_pattern = 'V,V,V,R,R,R,I,I,I,V'

        expected_exptime = 60.0
        expected_expcount = 12

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, filter_pattern)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_1m_short_pattern(self):
        speed = 2.52
        site_code = 'W85'
        slot_len = 22.5
        name = 'WH2845B'
        mag = 17.58
        filter_pattern = 'V,V,I,I'

        expected_exptime = 60.0
        expected_expcount = 11

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, filter_pattern)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_0m4_alternating_pattern(self):
        speed = 23.5
        site_code = 'Z21'
        slot_len = 20
        name = 'WH2845B'
        mag = 17.58
        filter_pattern = 'V,I,V,I'

        expected_exptime = 4.0
        expected_expcount = 30

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, filter_pattern)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_0m4_long_pattern(self):
        speed = 23.5
        site_code = 'Z21'
        slot_len = 20
        name = 'WH2845B'
        mag = 17.58
        filter_pattern = 'V,V,V,V,V,V,R,R,R,R,R,R,I,I,I,I,I,I,I'

        expected_exptime = 4.0
        expected_expcount = 52

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, filter_pattern)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_0m4_short_pattern(self):
        speed = 23.5
        site_code = 'Z21'
        slot_len = 20
        name = 'WH2845B'
        mag = 17.58
        filter_pattern = 'V,V,I,I'

        expected_exptime = 4.0
        expected_expcount = 40

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, filter_pattern)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

