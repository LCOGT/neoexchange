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

from datetime import datetime
from math import radians, degrees, floor
import os
import tempfile
from glob import glob
import mock
import json

from django.test import SimpleTestCase, TestCase, tag
from django.forms.models import model_to_dict

# Import module to test
from astrometrics.ephem_subs import *
from core.models import Body
from astrometrics.time_subs import datetime2mjd_utc, mjd_utc2mjd_tt
import astrometrics.site_config as cfg


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

    def test_1m_by_site_elp2(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('ELP-DOMB-1m0a')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_code_elp2(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('V39')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_code_lowercase(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('q63')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_tfn1(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('TFN-DOMA-1m0a')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_code_tfn1(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('Z31')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_tfn2(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('TFN-DOMB-1m0a')
        self.compare_limits(pos_limit, neg_limit, alt_limit, '1m')

    def test_1m_by_site_code_tfn2(self):
        (neg_limit, pos_limit, alt_limit) = get_mountlimits('Z24')
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


class TestComputeEphemerides(TestCase):
    """Tests both `compute_ephem()` and the `call_compute_ephem()` wrapper"""

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

        params = {  'provisional_name': 'A10bMLz',
                     'provisional_packed': None,
                     'name': None,
                     'origin': 'M',
                     'source_type': 'U',
                     'elements_type': 'MPC_MINOR_PLANET',
                     'active': True,
                     'fast_moving': False,
                     'urgency': None,
                     'epochofel': datetime(2019, 1, 17, 0, 0),
                     'orbinc': 1.05958,
                     'longascnode': 122.3243,
                     'argofperih': 229.33573,
                     'eccentricity': 0.0627231,
                     'meandist': 0.9472805,
                     'meananom': 118.75832,
                     'perihdist': None,
                     'epochofperih': None,
                     'abs_mag': 29.3,
                     'slope': 0.15,
                     'score': 100,
                     'discovery_date': datetime(2019, 1, 25, 9, 36),
                     'num_obs': 5,
                     'arc_length': 0.02,
                     'not_seen': 0.261,
                     'updated': False,
                     'ingest': datetime(2019, 1, 25, 15, 50, 7),
                     'update_time': datetime(2019, 1, 25, 15, 38, 2)}
        self.body_close, created = Body.objects.get_or_create(**params)

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

        self.length_emp_line = 15
        self.precision = 10

    def test_body_is_correct_class(self):
        tbody = Body.objects.get(provisional_name='N999r0q')
        self.assertIsInstance(tbody, Body)

    def test_save_and_retrieve_bodies(self):
        first_body = Body.objects.get(provisional_name='N999r0q')
        body_dict = model_to_dict(first_body)

        body_dict['provisional_name'] = 'N999z0z'
        body_dict['eccentricity'] = 0.42
        body_dict['ingest'] += timedelta(seconds=1)
        body_dict['id'] += 3
        second_body = Body.objects.create(**body_dict)
        second_body.save()

        saved_items = Body.objects.all()
        self.assertEqual(saved_items.count(), 4)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]
        # Newer should be first due to `-ingest` in the Body Meta ordering
        self.assertEqual(first_saved_item.provisional_name, 'N999z0z')
        self.assertEqual(second_saved_item.provisional_name, 'N999r0q')

    def test_compute_ephem_with_elements(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_ra = 5.28722753669144
        expected_dec = 0.522637696108887
        expected_mag = 20.408525362626005
        expected_motion = 2.4825093417658186
        expected_alt = -58.658929026981895
        expected_spd = 119.94694444444444
        expected_pa = 91.35793788996334
        expected_delta = 0.18138901132373111
        expected_r = 0.9919581686703755
        expected_geocnt_a_pos = [0.08577088074651966, -0.08469640009626787, 0.13553990887734638]
        expected_heliocnt_e_pos = [-0.8586692430417997, -0.5221333567849594, 1.6751755818864368e-06]
        expected_ltt = 90.51398438038252

        emp_line = compute_ephem(d, self.elements, '500', dbg=False, perturb=True, display=False)

        self.assertEqual(self.length_emp_line, len(emp_line))
        self.assertEqual(d, emp_line['date'])
        self.assertAlmostEqual(expected_ra, emp_line['ra'], self.precision)
        self.assertAlmostEqual(expected_dec, emp_line['dec'], self.precision)
        self.assertAlmostEqual(expected_mag, emp_line['mag'], self.precision)
        self.assertAlmostEqual(expected_motion, emp_line['sky_motion'], self.precision)
        self.assertAlmostEqual(expected_alt, emp_line['altitude'], self.precision)
        self.assertAlmostEqual(expected_spd, emp_line['southpole_sep'], self.precision)
        self.assertAlmostEqual(expected_pa,  emp_line['sky_motion_pa'], self.precision)
        self.assertAlmostEqual(expected_delta,  emp_line['earth_obj_dist'], self.precision)
        self.assertAlmostEqual(expected_r,  emp_line['sun_obj_dist'], self.precision)
        self.assertAlmostEqual(expected_ltt,  emp_line['ltt'], self.precision)
        for k, coord in enumerate(expected_geocnt_a_pos):
            self.assertAlmostEqual(coord,  emp_line['geocnt_a_pos'][k], self.precision)
            self.assertAlmostEqual(expected_heliocnt_e_pos[k],  emp_line['heliocnt_e_pos'][k], self.precision)

    def test_compute_ephem_with_body(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_ra = 5.28722753669144
        expected_dec = 0.522637696108887
        expected_mag = 20.408525362626005
        expected_motion = 2.4825093417658186
        expected_alt = -58.658929026981895
        expected_spd = 119.94694444444444
        expected_pa = 91.35793788996334
        expected_delta = 0.18138901132373111
        expected_r = 0.9919581686703755
        expected_geocnt_a_pos = [0.08577088074651966, -0.08469640009626787, 0.13553990887734638]
        expected_heliocnt_e_pos = [-0.8586692430417997, -0.5221333567849594, 1.6751755818864368e-06]
        expected_ltt = 90.51398438038252

        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)

        self.assertEqual(self.length_emp_line, len(emp_line))
        self.assertEqual(d, emp_line['date'])
        self.assertAlmostEqual(expected_ra, emp_line['ra'], self.precision)
        self.assertAlmostEqual(expected_dec, emp_line['dec'], self.precision)
        self.assertAlmostEqual(expected_mag, emp_line['mag'], self.precision)
        self.assertAlmostEqual(expected_motion, emp_line['sky_motion'], self.precision)
        self.assertAlmostEqual(expected_alt, emp_line['altitude'], self.precision)
        self.assertAlmostEqual(expected_spd, emp_line['southpole_sep'], self.precision)
        self.assertAlmostEqual(expected_pa,  emp_line['sky_motion_pa'], self.precision)
        self.assertAlmostEqual(expected_delta,  emp_line['earth_obj_dist'], self.precision)
        self.assertAlmostEqual(expected_r,  emp_line['sun_obj_dist'], self.precision)
        self.assertAlmostEqual(expected_ltt, emp_line['ltt'], self.precision)
        for k, coord in enumerate(expected_geocnt_a_pos):
            self.assertAlmostEqual(coord, emp_line['geocnt_a_pos'][k], self.precision)
            self.assertAlmostEqual(expected_heliocnt_e_pos[k], emp_line['heliocnt_e_pos'][k], self.precision)

    def test_compute_south_polar_distance_with_elements_in_north(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = 0.522637696108887
        expected_spd = 119.94694444444444
        emp_line = compute_ephem(d, self.elements, '500', dbg=False, perturb=True, display=False)
        self.assertAlmostEqual(expected_dec, emp_line['dec'], self.precision)
        self.assertAlmostEqual(expected_spd, emp_line['southpole_sep'], self.precision)
        
    def test_compute_south_polar_distance_with_body_in_north(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = 0.522637696108887
        expected_spd = 119.94694444444444
        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)
        self.assertAlmostEqual(expected_dec, emp_line['dec'], self.precision)
        self.assertAlmostEqual(expected_spd, emp_line['southpole_sep'], self.precision)

    def test_compute_south_polar_distance_with_body_in_south(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_dec = -0.06554641803516298
        expected_spd = 86.242222222222225
        body_elements = model_to_dict(self.body)
        body_elements['meananom'] = 25.2636
        emp_line = compute_ephem(d, body_elements, '500', dbg=False, perturb=True, display=False)
        self.assertAlmostEqual(expected_dec, emp_line['dec'], self.precision)
        self.assertAlmostEqual(expected_spd, emp_line['southpole_sep'], self.precision)

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

    def test_call_compute_ephem_for_close1(self):
        start = datetime(2019, 1, 25, 19, 40)
        end = datetime(2019, 1, 25, 20, 0)
        site_code = 'Z21'
        step_size = 600
        alt_limit = 30
        body_elements = model_to_dict(self.body_close)
        expected_ephem_lines = []

        ephem_lines = call_compute_ephem(body_elements, start, end,
            site_code, step_size, alt_limit)
        line = 0
        self.assertEqual(len(expected_ephem_lines), len(ephem_lines))
        while line < len(expected_ephem_lines):
            self.assertEqual(expected_ephem_lines[line], ephem_lines[line])
            line += 1

    def test_call_compute_comet_missing_q(self):
        body_elements = {
                         'provisional_name': 'C0TUUZ2',
                         'name': None,
                         'origin': 'M',
                         'source_type': 'U',
                         'elements_type': 'MPC_COMET',
                         'epochofel': datetime(2019, 8, 21, 0, 0),
                         'orbit_rms': 0.28,
                         'orbinc': 105.5272,
                         'longascnode': 323.82141,
                         'argofperih': 74.17643,
                         'eccentricity': 1.0,
                         'meandist': 351375868.8,
                         'meananom': None,
                         'perihdist': None,
                         'epochofperih': datetime(2019, 8, 21, 0, 0),
                         'abs_mag': 14.9,
                         'slope': 4.0,
                         'num_obs': 7,
                         'arc_length': 0.2,
                        }
        start = datetime(2019, 8, 21, 15)
        site_code = '500'

        emp_line = compute_ephem(start, body_elements, site_code, perturb=False)

        self.assertEqual({}, emp_line)

    def test_call_compute_comet_missing_qdate(self):
        body_elements = {
                         'provisional_name': 'C0TUUZ2',
                         'name': None,
                         'origin': 'M',
                         'source_type': 'U',
                         'elements_type': 'MPC_COMET',
                         'epochofel': datetime(2019, 8, 21, 0, 0),
                         'orbit_rms': 0.28,
                         'orbinc': 105.5272,
                         'longascnode': 323.82141,
                         'argofperih': 74.17643,
                         'eccentricity': 1.0,
                         'meandist': 351375868.8,
                         'meananom': None,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 14.9,
                         'slope': 4.0,
                         'num_obs': 7,
                         'arc_length': 0.2,
                        }
        start = datetime(2019, 8, 21, 15)
        site_code = '500'

        emp_line = compute_ephem(start, body_elements, site_code, perturb=False)

        self.assertEqual({}, emp_line)

    def test_call_compute_empty_elements(self):
        body_elements = { 'id': 241,
                          'provisional_name': 'WD3FB24',
                          'provisional_packed': None,
                          'name': '2015 DP53',
                          'origin': 'M',
                          'source_type': 'N',
                          'elements_type': None,
                          'active': False,
                          'fast_moving': False,
                          'urgency': None,
                          'epochofel': None,
                          'orbit_rms': 99.0,
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
                          'ingest': datetime(2015, 3, 7, 1, 22, 34),
                          'update_time': None
                        }
        start = datetime(2019, 11, 11, 15)
        site_code = '500'

        emp_line = compute_ephem(start, body_elements, site_code, perturb=False)

        self.assertEqual({}, emp_line)

    def test_numerical_error(self):
        orbelems = {
                     'provisional_name': 'P10Ee5V',
                     'provisional_packed': '',
                     'name': 'C/2017 U1',
                     'origin': 'M',
                     'source_type': 'C',
                     'source_subtype_1': 'H',
                     'source_subtype_2': 'DN',
                     'elements_type': 'MPC_COMET',
                     'active': False,
                     'fast_moving': False,
                     'urgency': None,
                     'epochofel': datetime(2017, 10, 20, 0, 0),
                     'orbit_rms': 99.0,
                     'orbinc': 122.48309,
                     'longascnode': 24.60837,
                     'argofperih': 241.31094,
                     'eccentricity': 1.1938645,
                     'meandist': None,
                     'meananom': 0.0,
                     'perihdist': 0.25316879,
                     'epochofperih': datetime(2017, 9, 9, 10, 45, 27),
                     'abs_mag': 22.2,
                     'slope': 4.0,
                     'score': 5,
                     'discovery_date': datetime(2017, 10, 19, 7, 12),
                     'num_obs': 57,
                     'arc_length': 13.0,
                     'not_seen': 0.908,
                     'updated': True,
                     'ingest': datetime(2017, 10, 19, 14, 20, 8),
                     'update_time': datetime(2017, 10, 27, 17, 5, 51)}

        start = datetime(2020, 11, 2, 9, 30)
        site_code = 'W85'

        try:
            emp_line = compute_ephem(start, orbelems, site_code, perturb=False)
            self.assertEqual({}, emp_line)
        except ValueError:
            self.fail("compute_ephem raised ValueError unexpectedly")


class TestDarkAndObjectUp(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.dark_start = datetime(2019, 1, 25, 19, 40)
        cls.dark_end = datetime(2019, 1, 26, 6, 40)
        cls.site_code = 'Z21'
        cls.slot_length = 10  # minutes
        step_size_secs = 60 * cls.slot_length  # seconds

        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2019-03-19 00:00:00',
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
        cls.body, created = Body.objects.get_or_create(**params)

        ephem_time = cls.dark_start
        cls.full_emp = []
        while ephem_time < cls.dark_end:
            emp_line = compute_ephem(ephem_time, params, cls.site_code, dbg=False, perturb=True, display=False)
            cls.full_emp.append(emp_line)
            ephem_time = ephem_time + timedelta(seconds=step_size_secs)

        cls.precision = 8

    def test1(self):
        expected_first_line = {'date': datetime(2019, 1, 26, 1, 20),
                               'ra': 3.13872732667931,
                               'dec': -0.09499609693219863,
                               'mag': 20.600690640173646,
                               'sky_motion': 1.760842377819953,
                               'altitude': 30.206739359560114,
                               'southpole_sep': 84.55611111111111,
                               'sky_motion_pa': 88.26314748574852
                               }
        expected_last_line = {'date': datetime(2019, 1, 26, 6, 30),
                               'ra': 3.141344602912528,
                               'dec': -0.09490298162746419,
                               'mag': 20.589568103540817,
                               'sky_motion': 1.7374161477538685,
                               'altitude': 47.8232397476396,
                               'southpole_sep': 84.56222222222222,
                               'sky_motion_pa': 87.63684359362396
                               }

        expected_num_lines = 32

        visible_emp = dark_and_object_up(self.full_emp, self.dark_start, self.dark_end, self.slot_length, alt_limit=30.0, debug=False)

        self.assertEqual(expected_num_lines, len(visible_emp))
        for key, value in expected_first_line.items():
            self.assertAlmostEqual(value, visible_emp[0][key], self.precision)
        for key, value in expected_last_line.items():
            self.assertAlmostEqual(value, visible_emp[-1][key], self.precision)

    def test_empty_ephem(self):
        expected_num_lines = 0

        visible_emp = dark_and_object_up([[], [], ], self.dark_start, self.dark_end, self.slot_length, alt_limit=30.0, debug=False)

        self.assertEqual(expected_num_lines, len(visible_emp))

    def test_too_short_ephem(self):
        expected_num_lines = 0
        emp = [{'date': datetime(2019, 1, 25, 19, 40, 0),
                'ra': 1.23,
                'dec': -1.23,
                'mag': 17.0,
                'sky_motion': 4.2,
                'altitude': 42.0},
               [], ]

        visible_emp = dark_and_object_up(emp, self.dark_start, self.dark_end, self.slot_length, alt_limit=30.0, debug=False)

        self.assertEqual(expected_num_lines, len(visible_emp))


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
        self.precision = 10

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
        self.assertAlmostEqual(expected_not_seen, body_elements['not_seen'], self.precision)
        self.assertAlmostEqual(expected_arc_length, body_elements['arc_length'], self.precision)
        self.assertAlmostEqual(expected_score, body_elements['score'], self.precision)
        self.assertAlmostEqual(expected_abs_mag, body_elements['abs_mag'], self.precision)
        self.assertAlmostEqual(expected_FOM, FOM, self.precision)

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

@tag('slow')
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

        expected_dark_and_up_time = 0
        expected_emp_dark_and_up = []

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)
        dark_and_up_time, emp_dark_and_up, set_time = compute_dark_and_up_time(emp)

        self.assertEqual(expected_dark_and_up_time, dark_and_up_time)
        self.assertEqual(expected_emp_dark_and_up, emp_dark_and_up)

    def test_dark_and_up_time_body_above_horizon(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_dark_and_up_time = 5.25
        expected_emp_dark_and_up_first_line = ['2017 01 06 01:20', '02 13 50.14', '+31 54 14.0', '21.0', ' 4.69', '240.8', '+79', '0.52', ' 31', '+62', '+059', '-00:47']

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)
        dark_and_up_time, emp_dark_and_up, set_time = compute_dark_and_up_time(emp)

        self.assertEqual(expected_dark_and_up_time, dark_and_up_time)
        self.assertEqual(expected_emp_dark_and_up_first_line, emp_dark_and_up[0])

    def test_compute_max_altitude(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body)

        expected_max_alt = 88

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)

        max_alt = compute_max_altitude(emp)

        self.assertEqual(expected_max_alt, max_alt)

    def test_compute_max_altitude_not_up_and_dark(self):
        site_code = 'K92'
        body_elements = model_to_dict(self.body)

        expected_max_alt = 0

        dark_start, dark_end = determine_darkness_times(site_code, utc_date=datetime(2017, 1, 6, 0, 0, 00))
        emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, ephem_step_size='5 m', alt_limit=30)

        max_alt = compute_max_altitude(emp)

        self.assertEqual(expected_max_alt, max_alt)

    def test_compute_rise_set(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body)
        expected_max_alt = 88.9
        expected_rise_time = datetime(2017, 1, 6, 1, 20, 00)
        expected_set_time = datetime(2017, 1, 6, 6, 36, 00)

        mid_time = datetime(2017, 1, 6, 3, 30, 00)
        emp_line = compute_ephem(mid_time, body_elements, site_code, dbg=False, perturb=True, display=False)
        app_ra = emp_line['ra']
        app_dec = emp_line['dec']
        min_alt = 30
        rise_time, set_time, max_alt, vis_time = target_rise_set(mid_time, app_ra, app_dec, site_code, min_alt, step_size='1m')

        self.assertAlmostEqual(expected_max_alt, max_alt, 1)
        self.assertEqual(expected_rise_time, rise_time)
        self.assertEqual(expected_set_time, set_time)

    def test_visibility(self):
        site_code = 'V37'
        body_elements = model_to_dict(self.body2)
        expected_max_alt = 41.3
        expected_up_time = 3.8333333333333335
        expected_start_time = datetime(2017, 1, 6, 8, 40)
        expected_stop_time = datetime(2017, 1, 6, 12, 30)

        emp_line = compute_ephem(datetime(2017, 1, 6, 0, 0, 00), body_elements, site_code, dbg=False, perturb=True, display=False)
        app_ra = emp_line['ra']
        app_dec = emp_line['dec']
        min_alt = 30
        up_time, max_alt, start_time, stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '10 m', min_alt, quick_n_dirty=True, body_elements=None)

        self.assertAlmostEqual(expected_max_alt, max_alt, 1)
        self.assertAlmostEqual(expected_up_time, up_time, 1)
        self.assertEqual(expected_start_time, start_time)
        self.assertEqual(expected_stop_time, stop_time)

    def test_visibility_general1m(self):
        site_code = '1M0'
        body_elements = model_to_dict(self.body2)
        expected_start_time = datetime(2017, 1, 5, 19, 0, 00)
        expected_stop_time = datetime(2017, 1, 6, 12, 40, 00)

        emp_line = compute_ephem(datetime(2017, 1, 6, 0, 0, 00), body_elements, site_code, dbg=False, perturb=True, display=False)
        app_ra = emp_line['ra']
        app_dec = emp_line['dec']
        min_alt = 30
        up_time, max_alt, start_time, stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '10 m', min_alt, quick_n_dirty=True, body_elements=body_elements)
        true_up_time, true_max_alt, true_start_time, true_stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '10 m', min_alt, quick_n_dirty=False, body_elements=body_elements)
        self.assertEqual(floor(true_max_alt), floor(max_alt))
        self.assertAlmostEqual(true_up_time, up_time, 1)
        self.assertEqual(expected_start_time, start_time)
        self.assertEqual(expected_stop_time, stop_time)

    def test_visibility_general1m_single_site(self):
        site_code = '1M0'
        body_elements = model_to_dict(self.body)
        expected_max_alt = 89
        expected_up_time = 5

        emp_line = compute_ephem(datetime(2017, 1, 6, 0, 0, 00), body_elements, site_code, dbg=False, perturb=True, display=False)
        app_ra = emp_line['ra']
        app_dec = emp_line['dec']
        min_alt = 30
        up_time, max_alt, start_time, stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '10 m', min_alt, quick_n_dirty=True, body_elements=body_elements)
        true_up_time, true_max_alt, true_start_time, true_stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '10 m', min_alt, quick_n_dirty=False, body_elements=body_elements)
        self.assertEqual(floor(true_max_alt), floor(max_alt))
        self.assertAlmostEqual(true_up_time, up_time, 1)
        self.assertAlmostEqual(expected_max_alt, max_alt, 0)
        self.assertAlmostEqual(expected_up_time, up_time, 0)
        self.assertEqual(start_time, true_start_time)
        self.assertEqual(stop_time, true_stop_time)

    def test_visibility_2m_never_up(self):
        site_code = 'E10'
        body_elements = model_to_dict(self.body4)
        expected_max_alt = 63.5
        expected_up_time = 0
        expected_start_time = None
        expected_stop_time = None

        emp_line = compute_ephem(datetime(2017, 1, 6, 0, 0, 00), body_elements, site_code, dbg=False, perturb=True, display=False)
        app_ra = emp_line['ra']
        app_dec = emp_line['dec']
        min_alt = 80
        up_time, max_alt, start_time, stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '30 m', min_alt, quick_n_dirty=True, body_elements=body_elements)
        true_up_time, true_max_alt, true_start_time, true_stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '30 m', min_alt, quick_n_dirty=False, body_elements=body_elements)
        self.assertEqual(floor(true_max_alt), floor(max_alt))
        self.assertAlmostEqual(true_up_time, up_time, 1)
        self.assertAlmostEqual(expected_max_alt, max_alt, 0)
        self.assertAlmostEqual(expected_up_time, up_time, 0)
        self.assertEqual(expected_start_time, start_time)
        self.assertEqual(expected_stop_time, stop_time)

    def test_visibility_general2m_never_up(self):
        site_code = '2M0'
        body_elements = model_to_dict(self.body4)
        expected_max_alt = 63.5
        expected_up_time = 0
        expected_start_time = datetime(2017, 1, 6, 5, 0, 00)
        expected_stop_time = datetime(2017, 1, 6, 17, 40, 00)

        emp_line = compute_ephem(datetime(2017, 1, 6, 0, 0, 00), body_elements, site_code, dbg=False, perturb=True, display=False)
        app_ra = emp_line['ra']
        app_dec = emp_line['dec']
        min_alt = 80
        up_time, max_alt, start_time, stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '30 m', min_alt, quick_n_dirty=True, body_elements=body_elements)
        true_up_time, true_max_alt, true_start_time, true_stop_time = get_visibility(app_ra, app_dec, datetime(2017, 1, 6, 0, 0, 00), site_code, '30 m', min_alt, quick_n_dirty=False, body_elements=body_elements)
        self.assertEqual(floor(true_max_alt), floor(max_alt))
        self.assertAlmostEqual(true_up_time, up_time, 1)
        self.assertAlmostEqual(expected_max_alt, max_alt, 0)
        self.assertAlmostEqual(expected_up_time, up_time, 0)
        self.assertEqual(expected_start_time, start_time)
        self.assertEqual(expected_stop_time, stop_time)


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
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 15
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 20
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 22.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 30
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 40
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_reallyfaint_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 22.1
        expected_length = 45
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 23.1
        expected_length = 60
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toobright_nonNEOWISE_good1m(self):
        site_code = 'good1m'
        name = 'WH2845B'
        mag = 3.1
        expected_length = 5.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 17.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 22.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 27.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 32.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 35
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_for_coj_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 22.1
        expected_length = 60
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 23.1
        expected_length = 60
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toobright_nonNEOWISE_bad1m(self):
        site_code = 'bad1m'
        name = 'WH2845B'
        mag = 3.1
        expected_length = 6.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_2m_lc(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 10
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_very_bright_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 17.58
        expected_length = 10
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_bright_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 19.9
        expected_length = 20
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_medium_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 20.1
        expected_length = 22.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_mediumfaint_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 20.6
        expected_length = 25
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_faint_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 21.0
        expected_length = 27.5
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_veryfaint_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 21.51
        expected_length = 30
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_reallyfaint_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 23.2
        expected_length = 35
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toofaint_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 23.4
        expected_length = 60
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_toobright_nonNEOWISE_2m(self):
        site_code = '2m'
        name = 'WH2845B'
        mag = 3.1
        expected_length = 6.0
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

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

    def test_slot_length_basic_elp_1m0_2(self):
        site_code = 'V39'
        name = 'A101foo'
        mag = 19.0
        expected_length = 20
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_tfn_1m0_1(self):
        site_code = 'Z31'
        name = 'A101foo'
        mag = 19.0
        expected_length = 20
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)

    def test_slot_length_basic_tfn_1m0_2(self):
        site_code = 'Z24'
        name = 'A101foo'
        mag = 19.0
        expected_length = 20
        slot_length = determine_slot_length(mag, site_code)
        self.assertEqual(expected_length, slot_length)


class TestGetSiteCamParams(TestCase):

    twom_setup_overhead = 180.0
    twom_exp_overhead = 10.0 # for MuSCAT, was 19 for Spectral
    twom_fov = 10.0
    twom_muscat_fov = 9.1
    onem_sbig_fov = 15.5
    onem_setup_overhead = 90.0
    onem_exp_overhead = 15.5
    sinistro_exp_overhead = 28.0
    onem_sinistro_fov = 26.4
    point4m_qhy_fov = 117.9
    point4m_qhy_central_fov = 29.5
    point4m_qhy_exp_overhead = 6
    point4m_qhy_central_exp_overhead = 3
    point4m_setup_overhead = 90.0
    max_exp = 300.0

    def test_bad_site(self):
        site_code = 'wibble'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual('XXX', chk_site_code)
        self.assertEqual(-1, pixel_scale)
        self.assertEqual(-1, max_exp_time)
        self.assertEqual(-1, setup_overhead)
        self.assertEqual(-1, exp_overhead)

    def test_2m_site(self):
        site_code = 'E10'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.27, pixel_scale)
        self.assertEqual(self.twom_muscat_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.twom_setup_overhead, setup_overhead)
        self.assertEqual(self.twom_exp_overhead, exp_overhead)

    def test_muscat_site(self):
        site_code = 'f65'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.27, pixel_scale)
        self.assertEqual(self.twom_muscat_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.twom_setup_overhead, setup_overhead)
        self.assertEqual(self.twom_exp_overhead, exp_overhead)

    def test_2m_sitename(self):
        site_code = 'E10'

        site_string = 'COJ-CLMA-2M0A'
        sitecam = get_sitecam_params(site_string)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code, chk_site_code)
        self.assertEqual(0.27, pixel_scale)
        self.assertEqual(self.twom_muscat_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.twom_setup_overhead, setup_overhead)
        self.assertEqual(self.twom_exp_overhead, exp_overhead)

    def test_2m_floyds(self):
        site_code = 'E10-FLOYDS'

        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual('E10', chk_site_code)
        self.assertEqual(cfg.tel_field['twom_floyds_pixscale'], pixel_scale)
        self.assertEqual(cfg.tel_field['twom_floyds_fov'], ccd_fov)
        self.assertEqual(3600, max_exp_time)
        self.assertEqual(6, len(setup_overhead))
        self.assertEqual(cfg.inst_overhead['floyds_exp_overhead'], exp_overhead)

    def test_1m_site_sinistro_domea(self):
        site_code = 'W85'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)
        self.assertEqual(self.max_exp, max_exp_time)

    def test_1m_lsc_site_sinistro(self):
        site_code = 'W86'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)

    def test_point4m_site(self):
        site_code = 'Z21'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site2(self):
        site_code = 'T04'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site3(self):
        site_code = 'Q59'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site4(self):
        site_code = 'Q58'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site5(self):
        site_code = 'Z17'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site6(self):
        site_code = 'T03'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site7(self):
        site_code = 'W89'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site8(self):
        site_code = 'V38'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site9(self):
        site_code = 'L09'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_point4m_site9_central_fov(self):
        site_code = 'L09'
        sitecam = get_sitecam_params(site_code, 'central30_1x1')
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_central_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_central_exp_overhead, exp_overhead)

    def test_point4m_site10(self):
        site_code = 'W79'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.7386, pixel_scale)
        self.assertEqual(self.point4m_qhy_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.point4m_setup_overhead, setup_overhead)
        self.assertEqual(self.point4m_qhy_exp_overhead, exp_overhead)

    def test_1m_cpt_site_sinistro1(self):
        site_code = 'K92'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)

    def test_1m_cpt_site_sinistro2(self):
        site_code = 'K93'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.max_exp, max_exp_time)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)

    def test_1m_elp_site_sinistro_domeB(self):
        site_code = 'V39'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)
        self.assertEqual(self.max_exp, max_exp_time)

    def test_1m_tfn_site_sinistro_domeA(self):
        site_code = 'Z31'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)
        self.assertEqual(self.max_exp, max_exp_time)

    def test_1m_tfn_site_sinistro_domeB(self):
        site_code = 'Z24'
        sitecam = get_sitecam_params(site_code)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.389, pixel_scale)
        self.assertEqual(self.onem_sinistro_fov, ccd_fov)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.sinistro_exp_overhead, exp_overhead)
        self.assertEqual(self.max_exp, max_exp_time)

    def test_1m_2x2binned(self):
        site_code = 'V39'
        bin_mode = '2k_2x2'
        sitecam = get_sitecam_params(site_code, bin_mode)
        chk_site_code = sitecam['site_code']
        setup_overhead = sitecam['setup_overhead']
        exp_overhead = sitecam['exp_overhead']
        pixel_scale = sitecam['pixel_scale']
        ccd_fov = sitecam['fov']
        max_exp_time = sitecam['max_exp_length']
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(cfg.tel_field['onem_2x2_sin_pixscale'], pixel_scale)
        self.assertEqual(cfg.tel_field['onem_2x2_sinistro_fov'], ccd_fov)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(cfg.inst_overhead['sinistro_2x2_exp_overhead'], exp_overhead)
        self.assertEqual(self.max_exp, max_exp_time)


class TestDetermineExpTimeCount(TestCase):

    def test_slow_1m(self):
        speed = 2.52
        site_code = 'W85'
        slot_len = 22.5
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 45.0
        expected_expcount = 17

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

        expected_exptime = 5.0
        expected_expcount = 33

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_superslow_1m(self):
        speed = 0.235
        site_code = 'W85'
        slot_len = 20
        name = 'WH2845B'
        mag = 21.2

        expected_exptime = 245.0
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
        expected_expcount = 63

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_block_too_short(self):
        speed = 0.18
        site_code = 'F65'
        slot_len = 2
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 0.1
        expected_expcount = 4

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_slow_point4m(self):
        speed = 2.52
        site_code = 'Z21'
        slot_len = 22.5
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 45.0
        expected_expcount = 24

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_fast_point4m(self):
        speed = 23.5
        site_code = 'Z21'
        slot_len = 20
        name = 'WH2845B'
        mag = 17.58

        expected_exptime = 5.0
        expected_expcount = 99

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, 'V')

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)


class TestDetermineSpectroSlotLength(TestCase):

    def test_bright_no_calibs(self):

        exp_time = 180.0
        calibs = 'none'

        expected_slot_length = 552.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_before(self):

        exp_time = 180.0
        calibs = 'before'

        expected_slot_length = 875.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_after(self):

        exp_time = 180.0
        calibs = 'after'

        expected_slot_length = 875.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_both(self):

        exp_time = 180.0
        calibs = 'both'

        expected_slot_length = 1198.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_bright_calibs_both_mixedcase(self):

        exp_time = 180.0
        calibs = 'BoTH'

        expected_slot_length = 1198.0

        slot_length = determine_spectro_slot_length(exp_time, calibs)

        self.assertEqual(expected_slot_length, slot_length)

    def test_multiexp_no_calibs(self):

        exp_time = 30.0
        calibs = 'none'
        num_exp = 10

        expected_slot_length = 901.0

        slot_length = determine_spectro_slot_length(exp_time, calibs, num_exp)

        self.assertEqual(expected_slot_length, slot_length)

    def test_multiexp_calibs_after(self):

        exp_time = 30.0
        calibs = 'after'
        num_exp = 10

        expected_slot_length = 1224.0

        slot_length = determine_spectro_slot_length(exp_time, calibs, num_exp)

        self.assertEqual(expected_slot_length, slot_length)

    def test_multiexp_calibs_both(self):

        exp_time = 30.0
        calibs = 'both'
        num_exp = 10

        expected_slot_length = 1547.0

        slot_length = determine_spectro_slot_length(exp_time, calibs, num_exp)

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

    def test_tenerife_point4m_num2_by_code(self):
        site_code = 'Z17'

        expected_site_name = 'LCO TFN Node 0m4b Aqawan A at Tenerife'

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

    def test_tenerife_point4m_num2_by_name(self):
        site_code = 'TFN-AQWA-0M4B'

        expected_site_name = 'LCO TFN Node 0m4b Aqawan A at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual('LCO TFN Node 0m4a Aqawan A at Tenerife', site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

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

    def test_elp_num1_by_code(self):
        site_code = 'V37'

        expected_site_name = 'LCO ELP Node 1m0 Dome A at McDonald Observatory'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual(site_long, 0.0)
        self.assertNotEqual(site_lat, 0.0)
        self.assertNotEqual(site_hgt, 0.0)

    def test_elp_num1_by_name(self):
        site_code = 'ELP-DOMA'

        expected_site_name = 'LCO ELP Node 1m0 Dome A at McDonald Observatory'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual(site_long, 0.0)
        self.assertNotEqual(site_lat, 0.0)
        self.assertNotEqual(site_hgt, 0.0)

    def test_elp_num2_by_code(self):
        site_code = 'V39'

        expected_site_name = 'LCO ELP Node 1m0 Dome B at McDonald Observatory'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual(site_long, 0.0)
        self.assertNotEqual(site_lat, 0.0)
        self.assertNotEqual(site_hgt, 0.0)

    def test_elp_num2_by_name(self):
        site_code = 'ELP-DOMB'

        expected_site_name = 'LCO ELP Node 1m0 Dome B at McDonald Observatory'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual(site_long, 0.0)
        self.assertNotEqual(site_lat, 0.0)
        self.assertNotEqual(site_hgt, 0.0)

    def test_mtjohn_by_code(self):
        site_code = '474'

        expected_site_name = 'MOA 1.8m at Mount John Observatory'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual(site_long, 0.0)
        self.assertNotEqual(site_lat, 0.0)
        self.assertNotEqual(site_hgt, 0.0)

    def test_mtjohn_by_name(self):
        site_code = 'NZTL-DOMA-1M8A'

        expected_site_name = 'MOA 1.8m at Mount John Observatory'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual(site_long, 0.0)
        self.assertNotEqual(site_lat, 0.0)
        self.assertNotEqual(site_hgt, 0.0)

    def test_tenerife_1m_num1_by_code(self):
        site_code = 'Z31'

        expected_site_name = 'LCO TFN Node 1m0 Dome A at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_tenerife_1m_num2_by_code(self):
        site_code = 'Z24'

        expected_site_name = 'LCO TFN Node 1m0 Dome B at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_tenerife_1m_num1_by_name(self):
        site_code = 'TFN-DOMA-1M0A'

        expected_site_name = 'LCO TFN Node 1m0 Dome A at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)

    def test_tenerife_1m_num2_by_name(self):
        site_code = 'TFN-DOMB-1M0A'

        expected_site_name = 'LCO TFN Node 1m0 Dome B at Tenerife'

        site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)

        self.assertEqual(expected_site_name, site_name)
        self.assertNotEqual('LCO TFN Node 1m0 Dome A at Tenerife', site_name)
        self.assertLess(site_long, 0.0)
        self.assertGreater(site_lat, 0.0)
        self.assertGreater(site_hgt, 0.0)


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
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 10, 'EXPOSE')))

    def test_multiple_individual_filters(self):
        filter_pattern = 'V,R,I'
        expected_overhead = (2. + 5. + 11.)*10.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 10, 'EXPOSE')))

    def test_multiple_repeated_filters(self):
        filter_pattern = 'V,R,I,V,R,I'
        expected_overhead = (2. + 5. + 11.)*10.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 10, 'EXPOSE')))

    def test_multiple_filter_strings(self):
        filter_pattern = 'V,V,V,R,R,R,I,I,I,'
        expected_overhead = (2. + 5. + 11.)*5.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 14, 'EXPOSE')))

    def test_short_block(self):
        filter_pattern = 'V,V,V,R,R,R,I,I,I,V'
        expected_overhead = (2. + 5. + 11.)*2.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 5, 'EXPOSE')))

    def test_repeat_expose(self):
        filter_pattern = 'V,V,R,R,V,V'
        expected_overhead = (2. + 5. + 11.)*3.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 19, 'REPEAT_EXPOSE')))

    def test_start_end_loop(self):
        filter_pattern = 'V,V,R,R,V,V'
        expected_overhead = (2. + 5. + 11.)*4.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 9, 'EXPOSE')))

    def test_exact_loop(self):
        filter_pattern = 'V,V,R,R,I,I'
        expected_overhead = (2. + 5. + 11.)*9.
        self.assertEqual(expected_overhead, molecule_overhead(build_filter_blocks(filter_pattern, 18, 'EXPOSE')))


class TestDetermineExpTimeCount_WithFilters(TestCase):

    def test_1m_alternating(self):
        speed = 2.52
        site_code = 'W85'
        slot_len = 22.5
        name = 'WH2845B'
        mag = 17.58
        filter_pattern = 'V,I'

        expected_exptime = 45.0
        expected_expcount = 13

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

        expected_exptime = 45.0
        expected_expcount = 16

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

        expected_exptime = 45.0
        expected_expcount = 15

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

        expected_exptime = 5.0
        expected_expcount = 38

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

        expected_exptime = 5.0
        expected_expcount = 79

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

        expected_exptime = 5.0
        expected_expcount = 55

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len, mag, filter_pattern)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)


class Test_perturb_elements(TestCase):
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

    def test_no_perturb(self):
        try:
            epochofel = datetime.strptime(self.body_elements['epochofel'], '%Y-%m-%d %H:%M:%S')
        except TypeError:
            epochofel = self.body_elements['epochofel']
        epoch_mjd = datetime2mjd_utc(epochofel)
        expected_inc = self.body_elements['orbinc']
        expected_a = self.body_elements['meandist']
        expected_e = self.body_elements['eccentricity']
        expected_epoch_mjd = epoch_mjd
        expected_j = 0

        test_time = datetime(2015, 4, 20, 1, 30, 0)
        mjd_utc = datetime2mjd_utc(test_time)
        mjd_tt = mjd_utc2mjd_tt(mjd_utc)

        p_orbelems, p_epoch_mjd, j = perturb_elements(self.body_elements, epoch_mjd, mjd_tt, False, False)

        self.assertEqual(expected_j, j)
        self.assertEqual(expected_epoch_mjd, p_epoch_mjd)
        self.assertAlmostEqual(expected_inc, degrees(p_orbelems['Inc']), self.precision)
        self.assertAlmostEqual(expected_a, p_orbelems['SemiAxisOrQ'], self.precision)
        self.assertAlmostEqual(expected_e, p_orbelems['Ecc'], self.precision)

    def test_yes_perturb(self):
        try:
            epochofel = datetime.strptime(self.body_elements['epochofel'], '%Y-%m-%d %H:%M:%S')
        except TypeError:
            epochofel = self.body_elements['epochofel']
        epoch_mjd = datetime2mjd_utc(epochofel)

        expected_inc = 8.34565
        expected_a = 1.21746
        expected_e = 0.189599

        expected_j = 0

        test_time = datetime(2015, 4, 20, 12, 00, 0)
        mjd_utc = datetime2mjd_utc(test_time)
        expected_epoch_mjd = mjd_utc
        mjd_tt = mjd_utc2mjd_tt(mjd_utc)

        p_orbelems, p_epoch_mjd, j = perturb_elements(self.body_elements, epoch_mjd, mjd_tt, False, True)

        self.assertEqual(expected_j, j)
        self.assertAlmostEqual(expected_epoch_mjd, p_epoch_mjd, 2)
        self.assertAlmostEqual(expected_inc, degrees(p_orbelems['Inc']), self.precision)
        self.assertAlmostEqual(expected_a, p_orbelems['SemiAxisOrQ'], self.precision)
        self.assertAlmostEqual(expected_e, p_orbelems['Ecc'], self.precision)

    def test_close_perturb(self):
        try:
            epochofel = datetime.strptime(self.close_elements['epochofel'], '%Y-%m-%d %H:%M:%S')
        except TypeError:
            epochofel = self.close_elements['epochofel']
        epoch_mjd = datetime2mjd_utc(epochofel)

        expected_inc = 12.919617  # 12.91839
        expected_a = 2.024077  # 2.0242057
        expected_e = 0.5071387  # 0.5991733

        expected_j = 0

        test_time = datetime(2015, 4, 20, 12, 00, 0)
        mjd_utc = datetime2mjd_utc(test_time)
        expected_epoch_mjd = mjd_utc
        mjd_tt = mjd_utc2mjd_tt(mjd_utc)

        p_orbelems, p_epoch_mjd, j = perturb_elements(self.close_elements, epoch_mjd, mjd_tt, False, True)

        self.assertEqual(expected_j, j)
        self.assertAlmostEqual(expected_epoch_mjd, p_epoch_mjd, 2)
        self.assertAlmostEqual(expected_inc, degrees(p_orbelems['Inc']), self.precision)
        self.assertAlmostEqual(expected_a, p_orbelems['SemiAxisOrQ'], self.precision)
        self.assertAlmostEqual(expected_e, p_orbelems['Ecc'], self.precision)

    def test_perturb_perturb(self):
        try:
            epochofel = datetime.strptime(self.perturb_elements['epochofel'], '%Y-%m-%d %H:%M:%S')
        except TypeError:
            epochofel = self.perturb_elements['epochofel']
        epoch_mjd = datetime2mjd_utc(epochofel)

        expected_inc = 8.13529  # 8.13617
        expected_a = 1.548882  # 1.5492508
        expected_e = 0.599262  # 0.5991733

        expected_j = 0

        test_time = datetime(2015, 9, 20, 12, 00, 0)
        mjd_utc = datetime2mjd_utc(test_time)
        expected_epoch_mjd = mjd_utc
        mjd_tt = mjd_utc2mjd_tt(mjd_utc)

        p_orbelems, p_epoch_mjd, j = perturb_elements(self.perturb_elements, epoch_mjd, mjd_tt, False, True)

        self.assertEqual(expected_j, j)
        self.assertAlmostEqual(expected_epoch_mjd, p_epoch_mjd, 2)
        self.assertAlmostEqual(expected_inc, degrees(p_orbelems['Inc']), self.precision)
        self.assertAlmostEqual(expected_a, p_orbelems['SemiAxisOrQ'], self.precision)
        self.assertAlmostEqual(expected_e, p_orbelems['Ecc'], self.precision)


class TestReadFindorbEphem(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.debug_print = False
        self.maxDiff = None

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
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)

    def create_empfile(self, lines):
        outfile = os.path.join(self.test_dir, 'new.ephem')
        outfile_fh = open(outfile, 'w')
        for line in lines:
            print(line, file=outfile_fh)
        outfile_fh.close()
        return outfile

    def compare_ephemeris(self, expected, given):
        expected_empinfo = expected[0]
        expected_emp = expected[1]

        empinfo = given[0]
        emp = given[1]

        self.assertEqual(expected_empinfo, empinfo)
        self.assertEqual(len(expected_emp), len(emp))
        expected_line = expected_emp[0]
        emp_line = emp[0]
        self.assertEqual(expected_line[0], emp_line[0])
        self.assertAlmostEqual(expected_line[1], emp_line[1], 10)
        self.assertAlmostEqual(expected_line[2], emp_line[2], 10)
        self.assertAlmostEqual(expected_line[3], emp_line[3], 2)
        self.assertAlmostEqual(expected_line[4], emp_line[4], 2)
        self.assertAlmostEqual(expected_line[5], emp_line[5], 2)

    def test_unnumbered_ast(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'F65',
                             'emp_timesys': '(UTC)',
                             'obj_id': '2017 YE5'}

        expected_emp = [(datetime(2018, 6, 30, 6, 10), 5.52141962907, -0.213430981276, 15.8, 7.26, 0.05)]

        lines = [ '#(F65) Haleakala-Faulkes Telescope North: 2017 YE5',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 06 30 06:10  21 05 24.970   -12 13 43.30  .08487 1.0854 142.8 15.8   7.26 215.5   .05  27'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_numbered_ast(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'F65',
                             'emp_timesys': '(UTC)',
                             'obj_id': '398188'}
        expected_emp = [(datetime(2018, 7, 19, 21, 48), 5.31473475745, 0.460169195739, 16.4, 3.50, 0.039)]

        lines = [ '#(F65) Haleakala-Faulkes Telescope North: (398188) = 2010 LE15',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 07 19 21:48  20 18 02.849   +26 21 56.71  .10109 1.0871 132.6 16.4   3.50 233.1  .039 172',
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_E10_numbered_ast(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'E10',
                             'emp_timesys': '(UTC)',
                             'obj_id': '1627'}
        expected_emp = [(datetime(2018, 7, 19, 22, 11), 3.95651109779, -0.00864485819197, 12.8, 2.04, 22.2)]

        lines = [ '#(E10) Siding Spring-Faulkes Telescope South: (1627) = 1929 SH',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 07 19 22:11  15 06 45.933   -00 29 43.13  .30297 1.1408 106.7 12.8   2.04 136.9  22.2  90'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_E10_numbered_ast_nocrossid(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'E10',
                             'emp_timesys': '(UTC)',
                             'obj_id': '1627'}
        expected_emp = [(datetime(2018, 7, 19, 22, 11), 3.95651109779, -0.00864485819197, 12.8, 2.04, 22.2)]

        lines = [ '#(E10) Siding Spring-Faulkes Telescope South: (1627)',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 07 19 22:11  15 06 45.933   -00 29 43.13  .30297 1.1408 106.7 12.8   2.04 136.9  22.2  90'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_F65_numbered_ast_nocrossid(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'F65',
                             'emp_timesys': '(UTC)',
                             'obj_id': '1627'}
        expected_emp = [(datetime(2018, 7, 19, 22, 11), 3.95651109779, -0.00864485819197, 12.8, 2.04, 22.2)]

        lines = [ '#(F65) Faulkes Telescope North: (1627)',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 07 19 22:11  15 06 45.933   -00 29 43.13  .30297 1.1408 106.7 12.8   2.04 136.9  22.2  90'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_F65_numbered_ast_high_uncertainty(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'F65',
                             'emp_timesys': '(UTC)',
                             'obj_id': '1627'}
        expected_emp = [(datetime(2018, 7, 19, 22, 11), 3.95651109779, -0.00864485819197, 12.8, 2.04, .0022)]

        lines = [ '#(F65) Faulkes Telescope North: (1627)',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 07 19 22:11  15 06 45.933   -00 29 43.13  .30297 1.1408 106.7 12.8   2.04 136.9  2.2m  90'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_Q63_candidate_veryhigh_uncertainty(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'Q63',
                             'emp_timesys': '(UTC)',
                             'obj_id': 'ZTF01Ym'}
        expected_emp = [(datetime(2018, 10, 1, 17, 00), 0.405840538302, -0.581830086206, 20.5, 5.08, 72000.0)]

        lines = [ '#(Q63) Siding Spring-LCO A: ZTF01Ym',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 10 01 17:00  01 33 00.708   -33 20 11.07  .00873 1.0079 140.5 20.5   5.08 121.6   20d  11'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_F65_candidate(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'F65',
                             'emp_timesys': '(UTC)',
                             'obj_id': 'ZR9CB15'}
        expected_emp = [(datetime(2018, 7, 19, 22, 11), 3.95651109779, -0.00864485819197, 12.8, 2.04, .0022)]

        lines = [ '#(F65) Faulkes Telescope North: ZR9CB15',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 07 19 22:11  15 06 45.933   -00 29 43.13  .30297 1.1408 106.7 12.8   2.04 136.9  2.2m  90'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))

    def test_F65_comet(self):
        expected_empinfo = { 'emp_rateunits': "'/hr",
                             'emp_sitecode': 'F65',
                             'emp_timesys': '(UTC)',
                             'obj_id': 'P/60'}
        expected_emp = [(datetime(2018, 7, 19, 22, 11), 3.95651109779, -0.00864485819197, 12.8, 2.04, .0022)]

        lines = [ '#(F65) Faulkes Telescope North: P/60',
                  'Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  \'/hr    PA   " sig PA',
                  '---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---',
                  '2018 07 19 22:11  15 06 45.933   -00 29 43.13  .30297 1.1408 106.7 12.8   2.04 136.9  2.2m  90'
                ]
        outfile = self.create_empfile(lines)

        empinfo, emp = read_findorb_ephem(outfile)

        self.compare_ephemeris((expected_empinfo, expected_emp), (empinfo, emp))


class TestDetermineHorizonsId(SimpleTestCase):

    def test_289P(self):
        expected_id = 90001196
        lines = ['Ambiguous target name; provide unique id:',
                 '    Record #  Epoch-yr  >MATCH DESIG<  Primary Desig  Name  ',
                 '    --------  --------  -------------  -------------  -------------------------',
                 '    90001195    2005    289P           289P            Blanpain',
                 '    90001196    2018    289P           289P            Blanpain',
                 '']
        obj_name = '289P'

        horizons_id = determine_horizons_id(lines, obj_name)

        self.assertEqual(expected_id, horizons_id)

    def test_46P(self):
        expected_id = 90000544
        lines = ['Ambiguous target name; provide unique id:',
                 '    Record #  Epoch-yr  >MATCH DESIG<  Primary Desig  Name  ',
                 '    --------  --------  -------------  -------------  -------------------------',
                 '    90000532    1947    46P            46P             Wirtanen',
                 '    90000533    1954    46P            46P             Wirtanen',
                 '    90000534    1961    46P            46P             Wirtanen',
                 '    90000535    1967    46P            46P             Wirtanen',
                 '    90000536    1974    46P            46P             Wirtanen',
                 '    90000537    1986    46P            46P             Wirtanen',
                 '    90000538    1991    46P            46P             Wirtanen',
                 '    90000539    1997    46P            46P             Wirtanen',
                 '    90000540    1999    46P            46P             Wirtanen',
                 '    90000541    2006    46P            46P             Wirtanen',
                 '    90000542    2007    46P            46P             Wirtanen',
                 '    90000543    2018    46P            46P             Wirtanen',
                 '    90000544    2018    46P            46P             Wirtanen',
                 '']
        obj_name = '46P'

        horizons_id = determine_horizons_id(lines, obj_name)

        self.assertEqual(expected_id, horizons_id)

    def test_46P_prior_apparition(self):
        expected_id = 90000542
        lines = ['Ambiguous target name; provide unique id:',
                 '    Record #  Epoch-yr  >MATCH DESIG<  Primary Desig  Name  ',
                 '    --------  --------  -------------  -------------  -------------------------',
                 '    90000532    1947    46P            46P             Wirtanen',
                 '    90000533    1954    46P            46P             Wirtanen',
                 '    90000534    1961    46P            46P             Wirtanen',
                 '    90000535    1967    46P            46P             Wirtanen',
                 '    90000536    1974    46P            46P             Wirtanen',
                 '    90000537    1986    46P            46P             Wirtanen',
                 '    90000538    1991    46P            46P             Wirtanen',
                 '    90000539    1997    46P            46P             Wirtanen',
                 '    90000540    1999    46P            46P             Wirtanen',
                 '    90000541    2006    46P            46P             Wirtanen',
                 '    90000542    2007    46P            46P             Wirtanen',
                 '    90000543    2018    46P            46P             Wirtanen',
                 '    90000544    2018    46P            46P             Wirtanen',
                 '']
        now = datetime(2008, 5, 11, 17, 20, 42)
        obj_name = '46P'

        horizons_id = determine_horizons_id(lines, obj_name, now)

        self.assertEqual(expected_id, horizons_id)

    def test_29P(self):
        expected_id = 90000393
        lines = ['Ambiguous target name; provide unique id:',
                 '    Record #  Epoch-yr  >MATCH DESIG<  Primary Desig  Name  ',
                 '    --------  --------  -------------  -------------  -------------------------',
                 '    90000387    1908    29P            29P             Schwassmann-Wachmann 1',
                 '    90000388    1925    29P            29P             Schwassmann-Wachmann 1',
                 '    90000389    1941    29P            29P             Schwassmann-Wachmann 1',
                 '    90000390    1957    29P            29P             Schwassmann-Wachmann 1',
                 '    90000391    1974    29P            29P             Schwassmann-Wachmann 1',
                 '    90000392    2007    29P            29P             Schwassmann-Wachmann 1',
                 '    90000393    2011    29P            29P             Schwassmann-Wachmann 1',
                 '']
        now = datetime(2020, 5, 11, 17, 20, 42)
        obj_name = '29P'

        horizons_id = determine_horizons_id(lines, obj_name, now)

        self.assertEqual(expected_id, horizons_id)

    def test_29P_prior_apparition(self):
        expected_id = 90000392
        lines = ['Ambiguous target name; provide unique id:',
                 '    Record #  Epoch-yr  >MATCH DESIG<  Primary Desig  Name  ',
                 '    --------  --------  -------------  -------------  -------------------------',
                 '    90000387    1908    29P            29P             Schwassmann-Wachmann 1',
                 '    90000388    1925    29P            29P             Schwassmann-Wachmann 1',
                 '    90000389    1941    29P            29P             Schwassmann-Wachmann 1',
                 '    90000390    1957    29P            29P             Schwassmann-Wachmann 1',
                 '    90000391    1974    29P            29P             Schwassmann-Wachmann 1',
                 '    90000392    2007    29P            29P             Schwassmann-Wachmann 1',
                 '    90000393    2011    29P            29P             Schwassmann-Wachmann 1',
                 '']
        now = datetime(2008, 5, 11, 17, 20, 42)
        obj_name = '29P'

        horizons_id = determine_horizons_id(lines, obj_name, now)

        self.assertEqual(expected_id, horizons_id)

    def test_10P_prior_apparition(self):
        expected_id = 90000207
        lines = ['Ambiguous target name; provide unique id:',
                 '    Record #  Epoch-yr  >MATCH DESIG<  Primary Desig  Name  ',
                 '    --------  --------  -------------  -------------  -------------------------',
                 '    90000192    1873    10P            10P             Tempel 2',
                 '    90000193    1878    10P            10P             Tempel 2',
                 '    90000194    1894    10P            10P             Tempel 2',
                 '    90000195    1899    10P            10P             Tempel 2',
                 '    90000196    1904    10P            10P             Tempel 2',
                 '    90000197    1915    10P            10P             Tempel 2',
                 '    90000198    1920    10P            10P             Tempel 2',
                 '    90000199    1925    10P            10P             Tempel 2',
                 '    90000200    1930    10P            10P             Tempel 2',
                 '    90000201    1946    10P            10P             Tempel 2',
                 '    90000202    1951    10P            10P             Tempel 2',
                 '    90000203    1957    10P            10P             Tempel 2',
                 '    90000204    1962    10P            10P             Tempel 2',
                 '    90000205    1967    10P            10P             Tempel 2',
                 '    90000206    1972    10P            10P             Tempel 2',
                 '    90000207    1978    10P            10P             Tempel 2',
                 '    90000208    1983    10P            10P             Tempel 2',
                 '    90000209    1988    10P            10P             Tempel 2',
                 '    90000210    1994    10P            10P             Tempel 2',
                 '    90000211    1999    10P            10P             Tempel 2',
                 '    90000212    2008    10P            10P             Tempel 2',
                 '    90000213    2011    10P            10P             Tempel 2',
                 '']
        now = datetime(1975, 5, 11, 17, 20, 42)
        obj_name = '10P'

        horizons_id = determine_horizons_id(lines, obj_name, now)

        self.assertEqual(expected_id, horizons_id)

    def test_73P(self):
        expected_id = 90000732
        lines = ['Ambiguous target name; provide unique id:',
             'Record #  Epoch-yr  >MATCH DESIG<  Primary Desig  Name  ',
             '--------  --------  -------------  -------------  -------------------------',
             '90000726    1930    73P            73P             Schwassmann-Wachmann 3',
             '90000727    1979    73P            73P             Schwassmann-Wachmann 3',
             '90000728    1995    73P            73P             Schwassmann-Wachmann 3',
             '90000729    1996    73P            73P             Schwassmann-Wachmann 3',
             '90000730    2005    73P            73P             Schwassmann-Wachmann 3',
             '90000731    2017    73P            73P             Schwassmann-Wachmann 3',
             '90000732    2017    73P            73P             Schwassmann-Wachmann 3',
             '90000733    1995    73P-A          73P-A           Schwassmann-Wachmann 3',
             '90000734    1995    73P-B          73P-B           Schwassmann-Wachmann 3',
             '90000735    2001    73P-B          73P-B           Schwassmann-Wachmann 3',
             '90000736    2006    73P-B          73P-B           Schwassmann-Wachmann 3',
             '90000737    1995    73P-C          73P-C           Schwassmann-Wachmann 3',
             '90000738    2001    73P-C          73P-C           Schwassmann-Wachmann 3',
             '90000739    2012    73P-C          73P-C           Schwassmann-Wachmann 3',
             '90000740    2001    73P-E          73P-E           Schwassmann-Wachmann 3',
             '90000741    2006    73P-G          73P-G           Schwassmann-Wachmann 3',
             '90000742    2006    73P-H          73P-H           Schwassmann-Wachmann 3',
             '90000743    2006    73P-J          73P-J           Schwassmann-Wachmann 3',
             '90000744    2006    73P-K          73P-K           Schwassmann-Wachmann 3',
             '90000745    2006    73P-L          73P-L           Schwassmann-Wachmann 3',
             '90000746    2006    73P-M          73P-M           Schwassmann-Wachmann 3',
             '90000747    2006    73P-N          73P-N           Schwassmann-Wachmann 3',
             '90000748    2006    73P-P          73P-P           Schwassmann-Wachmann 3',
             '90000749    2006    73P-Q          73P-Q           Schwassmann-Wachmann 3',
             '90000750    2006    73P-R          73P-R           Schwassmann-Wachmann 3',
             '90000751    2006    73P-S          73P-S           Schwassmann-Wachmann 3',
             '90000752    2006    73P-T          73P-T           Schwassmann-Wachmann 3',
             '90000753    2006    73P-U          73P-U           Schwassmann-Wachmann 3',
             '90000754    2006    73P-V          73P-V           Schwassmann-Wachmann 3',
             '90000755    2006    73P-W          73P-W           Schwassmann-Wachmann 3',
             '90000756    2006    73P-X          73P-X           Schwassmann-Wachmann 3',
             '90000757    2006    73P-Y          73P-Y           Schwassmann-Wachmann 3',
             '90000758    2006    73P-Z          73P-Z           Schwassmann-Wachmann 3',
             '90000759    2006    73P-AA         73P-AA          Schwassmann-Wachmann 3',
             '90000760    2006    73P-AB         73P-AB          Schwassmann-Wachmann 3',
             '90000761    2006    73P-AC         73P-AC          Schwassmann-Wachmann 3',
             '90000762    2006    73P-AD         73P-AD          Schwassmann-Wachmann 3',
             '90000763    2006    73P-AE         73P-AE          Schwassmann-Wachmann 3',
             '90000764    2006    73P-AF         73P-AF          Schwassmann-Wachmann 3',
             '90000765    2006    73P-AG         73P-AG          Schwassmann-Wachmann 3',
             '90000766    2006    73P-AH         73P-AH          Schwassmann-Wachmann 3',
             '90000767    2006    73P-AI         73P-AI          Schwassmann-Wachmann 3',
             '90000768    2006    73P-AJ         73P-AJ          Schwassmann-Wachmann 3',
             '90000769    2006    73P-AK         73P-AK          Schwassmann-Wachmann 3',
             '90000770    2006    73P-AL         73P-AL          Schwassmann-Wachmann 3',
             '90000771    2006    73P-AM         73P-AM          Schwassmann-Wachmann 3',
             '90000772    2006    73P-AN         73P-AN          Schwassmann-Wachmann 3',
             '90000773    2006    73P-AO         73P-AO          Schwassmann-Wachmann 3',
             '90000774    2006    73P-AP         73P-AP          Schwassmann-Wachmann 3',
             '90000775    2006    73P-AQ         73P-AQ          Schwassmann-Wachmann 3',
             '90000776    2006    73P-AR         73P-AR          Schwassmann-Wachmann 3',
             '90000777    2006    73P-AS         73P-AS          Schwassmann-Wachmann 3',
             '90000778    2006    73P-AT         73P-AT          Schwassmann-Wachmann 3',
             '90000779    2006    73P-AU         73P-AU          Schwassmann-Wachmann 3',
             '90000780    2006    73P-AV         73P-AV          Schwassmann-Wachmann 3',
             '90000781    2006    73P-AW         73P-AW          Schwassmann-Wachmann 3',
             '90000782    2006    73P-AX         73P-AX          Schwassmann-Wachmann 3',
             '90000783    2006    73P-AY         73P-AY          Schwassmann-Wachmann 3',
             '90000784    2006    73P-AZ         73P-AZ          Schwassmann-Wachmann 3',
             '90000785    2006    73P-BA         73P-BA          Schwassmann-Wachmann 3',
             '90000786    2006    73P-BB         73P-BB          Schwassmann-Wachmann 3',
             '90000787    2006    73P-BC         73P-BC          Schwassmann-Wachmann 3',
             '90000788    2006    73P-BD         73P-BD          Schwassmann-Wachmann 3',
             '90000789    2006    73P-BE         73P-BE          Schwassmann-Wachmann 3',
             '90000790    2006    73P-BF         73P-BF          Schwassmann-Wachmann 3',
             '90000791    2006    73P-BG         73P-BG          Schwassmann-Wachmann 3',
             '90000792    2006    73P-BH         73P-BH          Schwassmann-Wachmann 3',
             '90000793    2006    73P-BI         73P-BI          Schwassmann-Wachmann 3',
             '90000794    2006    73P-BJ         73P-BJ          Schwassmann-Wachmann 3',
             '90000795    2006    73P-BK         73P-BK          Schwassmann-Wachmann 3',
             '90000796    2006    73P-BL         73P-BL          Schwassmann-Wachmann 3',
             '90000797    2006    73P-BM         73P-BM          Schwassmann-Wachmann 3',
             '90000798    2006    73P-BN         73P-BN          Schwassmann-Wachmann 3',
             '90000799    2006    73P-BO         73P-BO          Schwassmann-Wachmann 3',
             '90000800    2006    73P-BP         73P-BP          Schwassmann-Wachmann 3',
             '90000801    2006    73P-BQ         73P-BQ          Schwassmann-Wachmann 3',
             '90000802    2006    73P-BR         73P-BR          Schwassmann-Wachmann 3',
             '90000803    2006    73P-BS         73P-BS          Schwassmann-Wachmann 3',
             '90000804    2017    73P-BT         73P-BT          Schwassmann-Wachmann 3',
             '90000805    2022    73P-BU         73P-BU          Schwassmann-Wachmann 3',
             '90000806    2022    73P-BV         73P-BV          Schwassmann-Wachmann 3',
             '']
        now = datetime(2022, 8, 19, 17, 20, 42)
        obj_name = '73P'

        horizons_id = determine_horizons_id(lines, obj_name, now)

        self.assertEqual(expected_id, horizons_id)

    def test_bad_object(self):
        expected_id = None
        lines = ['Unknown target (20000P). Maybe try different id_type?']
        obj_name = '20000P'

        horizons_id = determine_horizons_id(lines, obj_name)

        self.assertEqual(expected_id, horizons_id)

    def test_bad_object2(self):
        expected_id = None
        lines = []
        obj_name = ''

        horizons_id = determine_horizons_id(lines, obj_name)

        self.assertEqual(expected_id, horizons_id)


class TestLCOGT_tels_to_sitecode(SimpleTestCase):

# 2.0m's
    def test_ogg_clma_2m0a(self):

        expected_sitecode = 'F65'
        sitecode = LCOGT_telserial_to_site_codes('2m0-01')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_clma_2m0a(self):

        expected_sitecode = 'E10'
        sitecode = LCOGT_telserial_to_site_codes('2m0-02')

        self.assertEqual(expected_sitecode, sitecode)

# 1.0m's

    def test_coj_doma_1m0a(self):

        expected_sitecode = 'Q63'
        sitecode = LCOGT_telserial_to_site_codes('1m0-11')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_domb_1m0a(self):

        expected_sitecode = 'Q64'
        sitecode = LCOGT_telserial_to_site_codes('1m0-03')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_doma_1m0a(self):

        expected_sitecode = 'K91'
        sitecode = LCOGT_telserial_to_site_codes('1m0-10')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_domb_1m0a(self):

        expected_sitecode = 'K92'
        sitecode = LCOGT_telserial_to_site_codes('1m0-13')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_domc_1m0a(self):

        expected_sitecode = 'K93'
        sitecode = LCOGT_telserial_to_site_codes('1m0-12')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_doma_1m0a(self):

        expected_sitecode = 'W85'
        sitecode = LCOGT_telserial_to_site_codes('1m0-05')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_domb_1m0a(self):

        expected_sitecode = 'W86'
        sitecode = LCOGT_telserial_to_site_codes('1m0-09')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_domc_1m0a(self):

        expected_sitecode = 'W87'
        sitecode = LCOGT_telserial_to_site_codes('1m0-04')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_doma_1m0a(self):

        expected_sitecode = 'V37'
        sitecode = LCOGT_telserial_to_site_codes('1m0-08')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_domb_1m0a(self):

        expected_sitecode = 'V39'
        sitecode = LCOGT_telserial_to_site_codes('1m0-06')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_doma_1m0a(self):

        expected_sitecode = 'Z31'
        sitecode = LCOGT_telserial_to_site_codes('1m0-14')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_domb_1m0a(self):

        expected_sitecode = 'Z24'
        sitecode = LCOGT_telserial_to_site_codes('1m0-01')

        self.assertEqual(expected_sitecode, sitecode)

# 0.4m's
    def test_coj_clma_0m4a(self):

        expected_sitecode = 'Q58'
        sitecode = LCOGT_telserial_to_site_codes('0m4-03')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_clma_0m4b(self):

        expected_sitecode = 'Q59'
        sitecode = LCOGT_telserial_to_site_codes('0m4-05')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_clma_0m4c(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m4-20')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_aqwa_0m4a(self):

        expected_sitecode = 'L09'
        sitecode = LCOGT_telserial_to_site_codes('0m4-07')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_aqwa_0m4a(self):

        expected_sitecode = 'V38'
        sitecode = LCOGT_telserial_to_site_codes('0m4-11')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_aqwa_0m4b(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m4-19')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwa_0m4a(self):

        expected_sitecode = 'W89'
        sitecode = LCOGT_telserial_to_site_codes('0m4-09')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwa_0m4b(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m4-17')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwb_0m4a(self):

        expected_sitecode = 'W79'
        sitecode = LCOGT_telserial_to_site_codes('0m4-12')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwb_0m4b(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m4-18')

        self.assertEqual(expected_sitecode, sitecode)

    def test_ogg_clma_0m4a(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m4-08')

        self.assertEqual(expected_sitecode, sitecode)

    def test_ogg_clma_0m4b(self):

        expected_sitecode = 'T04'
        sitecode = LCOGT_telserial_to_site_codes('0m4-06')

        self.assertEqual(expected_sitecode, sitecode)

    def test_ogg_clma_0m4c(self):

        expected_sitecode = 'T03'
        sitecode = LCOGT_telserial_to_site_codes('0m4-04')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_aqwa_0m4a(self):

        expected_sitecode = 'Z21'
        sitecode = LCOGT_telserial_to_site_codes('0m4-14')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_aqwa_0m4b(self):

        expected_sitecode = 'Z17'
        sitecode = LCOGT_telserial_to_site_codes('0m4-10')

        self.assertEqual(expected_sitecode, sitecode)

# Without dashes
# 2.0m's
    def test_ogg_clma_2m0a_nodash(self):

        expected_sitecode = 'F65'
        sitecode = LCOGT_telserial_to_site_codes('2m001')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_clma_2m0a_nodash(self):

        expected_sitecode = 'E10'
        sitecode = LCOGT_telserial_to_site_codes('2m002')

        self.assertEqual(expected_sitecode, sitecode)

# 1.0m's

    def test_coj_doma_1m0a_nodash(self):

        expected_sitecode = 'Q63'
        sitecode = LCOGT_telserial_to_site_codes('1m011')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_domb_1m0a_nodash(self):

        expected_sitecode = 'Q64'
        sitecode = LCOGT_telserial_to_site_codes('1m003')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_doma_1m0a_nodash(self):

        expected_sitecode = 'K91'
        sitecode = LCOGT_telserial_to_site_codes('1m010')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_domb_1m0a_nodash(self):

        expected_sitecode = 'K92'
        sitecode = LCOGT_telserial_to_site_codes('1m013')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_domc_1m0a_nodash(self):

        expected_sitecode = 'K93'
        sitecode = LCOGT_telserial_to_site_codes('1m012')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_doma_1m0a_nodash(self):

        expected_sitecode = 'W85'
        sitecode = LCOGT_telserial_to_site_codes('1m005')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_domb_1m0a_nodash(self):

        expected_sitecode = 'W86'
        sitecode = LCOGT_telserial_to_site_codes('1m009')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_domc_1m0a_nodash(self):

        expected_sitecode = 'W87'
        sitecode = LCOGT_telserial_to_site_codes('1m004')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_doma_1m0a_nodash(self):

        expected_sitecode = 'V37'
        sitecode = LCOGT_telserial_to_site_codes('1m008')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_domb_1m0a_nodash(self):

        expected_sitecode = 'V39'
        sitecode = LCOGT_telserial_to_site_codes('1m006')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_doma_1m0a_nodash(self):

        expected_sitecode = 'Z31'
        sitecode = LCOGT_telserial_to_site_codes('1m014')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_domb_1m0a_nodash(self):

        expected_sitecode = 'Z24'
        sitecode = LCOGT_telserial_to_site_codes('1m001')

        self.assertEqual(expected_sitecode, sitecode)

# 0.4m's
    def test_coj_clma_0m4a_nodash(self):

        expected_sitecode = 'Q58'
        sitecode = LCOGT_telserial_to_site_codes('0m403')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_clma_0m4b_nodash(self):

        expected_sitecode = 'Q59'
        sitecode = LCOGT_telserial_to_site_codes('0m405')

        self.assertEqual(expected_sitecode, sitecode)

    def test_coj_clma_0m4c_nodash(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m420')

        self.assertEqual(expected_sitecode, sitecode)

    def test_cpt_aqwa_0m4a_nodash(self):

        expected_sitecode = 'L09'
        sitecode = LCOGT_telserial_to_site_codes('0m407')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_aqwa_0m4a_nodash(self):

        expected_sitecode = 'V38'
        sitecode = LCOGT_telserial_to_site_codes('0m411')

        self.assertEqual(expected_sitecode, sitecode)

    def test_elp_aqwa_0m4b_nodash(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m419')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwa_0m4a_nodash(self):

        expected_sitecode = 'W89'
        sitecode = LCOGT_telserial_to_site_codes('0m409')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwa_0m4b_nodash(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m417')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwb_0m4a_nodash(self):

        expected_sitecode = 'W79'
        sitecode = LCOGT_telserial_to_site_codes('0m412')

        self.assertEqual(expected_sitecode, sitecode)

    def test_lsc_aqwb_0m4b_nodash(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m418')

        self.assertEqual(expected_sitecode, sitecode)

    def test_ogg_clma_0m4a_nodash(self):

        expected_sitecode = 'XXX'
        sitecode = LCOGT_telserial_to_site_codes('0m408')

        self.assertEqual(expected_sitecode, sitecode)

    def test_ogg_clma_0m4b_nodash(self):

        expected_sitecode = 'T04'
        sitecode = LCOGT_telserial_to_site_codes('0m406')

        self.assertEqual(expected_sitecode, sitecode)

    def test_ogg_clma_0m4c_nodash(self):

        expected_sitecode = 'T03'
        sitecode = LCOGT_telserial_to_site_codes('0m404')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_aqwa_0m4a_nodash(self):

        expected_sitecode = 'Z21'
        sitecode = LCOGT_telserial_to_site_codes('0m414')

        self.assertEqual(expected_sitecode, sitecode)

    def test_tfn_aqwa_0m4b_nodash(self):

        expected_sitecode = 'Z17'
        sitecode = LCOGT_telserial_to_site_codes('0m410')

        self.assertEqual(expected_sitecode, sitecode)


class TestConvertFOElements(SimpleTestCase):

    def setUp(self):
        with open(os.path.join('astrometrics', 'tests', 'test_fo_elements.json'), 'r') as fp:
            self.test_json = json.load(fp)
            self.test_obs = self.test_json['objects'][self.test_json['ids'][0]]['observations']
        with open(os.path.join('astrometrics', 'tests', 'test_fo_elements_comet.json'), 'r') as fp:
            self.test_comet_json = json.load(fp)
            self.test_comet_obs = self.test_comet_json['objects'][self.test_comet_json['ids'][0]]['observations']

        self.maxDiff = None
        self.tolerance = 5
        self.now = datetime(2024, 8, 20, 20, 30)

    def test_65803_keys(self):
        expected_keys = ['name', 'origin', 'elements_type', 'epochofel',
                         'epochofperih', 'arc_length', 'not_seen',
                         'num_obs', 'meananom', 'meandist',  'eccentricity',
                         'perihdist', 'orbinc', 'argofperih', 'longascnode',
                         'abs_mag', 'slope', 'orbit_rms', 'updated']
        expected_types = [str, str, str, datetime, None, float, float, int,
            float, float, float, None, float, float, float, float, float, float]
        expected_values = { 'elements_type' : 'MPC_MINOR_PLANET',
                            'epochofel' : datetime(2022, 9, 25),
                            'epochofperih' : None,
                            'perihdist' : None,
                            'arc_length': self.test_obs["latest_used"] - self.test_obs["earliest_used"],
                            'num_obs' : 5278,
                            'not_seen' : 567.4291782407407
                          }

        new_elements = convert_findorb_elements(self.test_json, now=self.now)

        self.assertEqual(expected_keys, list(new_elements.keys()))
        for expected_type, key in zip(expected_types, list(new_elements.keys())):
            if expected_type is None:
                self.assertTrue(new_elements[key] is None, msg="Failure on " + key)
            else:
                self.assertEqual(expected_type, type(new_elements[key]), msg="Failure on " + key)
        for key, expected_value in expected_values.items():
            if type(expected_value) == float:
                self.assertAlmostEqual(expected_value, new_elements[key], self.tolerance)
            else:
                self.assertEqual(expected_value, new_elements[key])

    def test_comet_keys(self):
        expected_keys = ['name', 'origin', 'elements_type', 'epochofel',
                         'epochofperih', 'arc_length', 'not_seen',
                         'num_obs', 'meandist', 'eccentricity', 'perihdist',
                         'orbinc', 'argofperih', 'longascnode', 'abs_mag',
                         'slope', 'orbit_rms', 'meananom', 'updated']
        expected_types = [str, str, str, datetime, datetime, float, float, int,
            None, float, float, float, float, float, float, float, float, None]
        expected_values = { 'elements_type' : 'MPC_COMET',
                            'epochofel' : datetime(2024, 8, 2),
                            'epochofperih' : datetime(2024, 9, 27, 17, 52, 23, int(1e6 * 0.34)),
                            'meandist' : None,
                            'meananom' : None,
                            'perihdist' : 0.3914363976578,
                            'arc_length': self.test_comet_obs["latest_used"] - self.test_comet_obs["earliest_used"],
                            'num_obs' : 4760,
                            'not_seen' : 18.1219866
                          }

        new_elements = convert_findorb_elements(self.test_comet_json, now=self.now)

        self.assertEqual(expected_keys, list(new_elements.keys()))
        for expected_type, key in zip(expected_types, list(new_elements.keys())):
            if expected_type is None:
                self.assertTrue(new_elements[key] is None, msg="Failure on " + key)
            else:
                self.assertEqual(expected_type, type(new_elements[key]), msg="Failure on " + key)
        for key, expected_value in expected_values.items():
            if type(expected_value) == float:
                self.assertAlmostEqual(expected_value, new_elements[key], self.tolerance)
            else:
                self.assertEqual(expected_value, new_elements[key])
