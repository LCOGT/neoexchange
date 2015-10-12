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
        body_dict['id'] += 1
        second_body = Body.objects.create(**body_dict)
        second_body.save()

        saved_items = Body.objects.all()
        self.assertEqual(saved_items.count(), 2)

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
        
    def test_compute_south_polar_distance_with_elements(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_spd = 119.94694444444444
        emp_line = compute_ephem(d, self.elements, '?', dbg=False, perturb=True, display=False)
        precision = 11
        self.assertAlmostEqual(expected_spd, emp_line[6], precision)
        
    def test_compute_south_polar_distance_with_body(self):
        d = datetime(2015, 4, 21, 17, 35, 00)
        expected_spd = 119.94694444444444
        body_elements = model_to_dict(self.body)
        emp_line = compute_ephem(d, body_elements, '?', dbg=False, perturb=True, display=False)
        precision = 11
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

    def test_1m_site_sbig(self):
        site_code = 'V37'
        chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit = get_sitecam_params(site_code)
        self.assertEqual(site_code.upper(), chk_site_code)
        self.assertEqual(0.464, pixel_scale)
        self.assertEqual(self.onem_sbig_fov, ccd_fov)
        self.assertEqual(self.onem_setup_overhead, setup_overhead)
        self.assertEqual(self.onem_exp_overhead, exp_overhead)
        self.assertEqual(self.max_exp, max_exp_time)

    def test_1m_site_sinistro(self):
        site_code = 'W86'
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
        site_code = 'V37'
        slot_len = 22.5

        expected_exptime = 50.0
        expected_expcount = 18

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_fast_1m(self):
        speed = 23.5
        site_code = 'K91'
        slot_len = 20

        expected_exptime = 5.5
        expected_expcount = 51

        exp_time, exp_count = determine_exp_time_count(speed, site_code, slot_len)

        self.assertEqual(expected_exptime, exp_time)
        self.assertEqual(expected_expcount, exp_count)

    def test_superslow_1m(self):
        speed = 0.235
        site_code = 'W85'
        slot_len = 20

        expected_exptime = 254.5
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
