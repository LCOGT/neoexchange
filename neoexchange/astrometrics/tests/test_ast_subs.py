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

from datetime import datetime, timedelta
from django.test import TestCase

from core.models import Body
# Import module to test
from astrometrics.ast_subs import *


class TestIntToMutantHexChar(TestCase):
    """Unit tests for the int_to_mutant_hex_char() method"""

# EricS says to run without the exception handler in place first to check it works as expected
# This is the simple test version where we only care if we get an exception (any exception)
# and are not bothered what the specific message/failure is
# '@raises' is a "decorator"

#    @raises(MutantError)
#    def test_bad_mutantcode_length(self):
#        int_to_mutant_hex_char(-1)

    def test_bad_mutant_too_small(self):
        try:
            int_to_mutant_hex_char(-1)
            assert False
        except MutantError as e:
            expected_msg = "Number out of range 0...61"
            self.assertEqual(e.__str__(), expected_msg)

    def test_bad_mutant_too_large(self):
        try:
            int_to_mutant_hex_char(62)
            assert False
        except MutantError as e:
            expected_msg = "Number out of range 0...61"
            self.assertEqual(e.__str__(), expected_msg)

    def test_bad_mutant_not_number1(self):
        try:
            int_to_mutant_hex_char('9')
            assert False
        except MutantError as e:
            expected_msg = "Not an integer"
            self.assertEqual(e.__str__(), expected_msg)

    def test_bad_mutant_not_number2(self):
        try:
            int_to_mutant_hex_char('FOO')
            assert False
        except MutantError as e:
            expected_msg = "Not an integer"
            self.assertEqual(e.__str__(), expected_msg)

    def test_num_less_than_ten(self):
        char = int_to_mutant_hex_char(8)
        expected_char = '8'
        self.assertEqual(char, expected_char)

    def test_num_less_than_thirtysix_t1(self):
        char = int_to_mutant_hex_char(10)
        expected_char = 'A'
        self.assertEqual(char, expected_char)

    def test_num_less_than_thirtysix_t2(self):
        char = int_to_mutant_hex_char(23)
        expected_char = 'N'
        self.assertEqual(char, expected_char)

    def test_num_less_than_thirtysix_t3(self):
        char = int_to_mutant_hex_char(34)
        expected_char = 'Y'
        self.assertEqual(char, expected_char)

    def test_num_less_than_thirtysix_t4(self):
        char = int_to_mutant_hex_char(35)
        expected_char = 'Z'
        self.assertEqual(char, expected_char)

    def test_num_greater_than_thirtysix_t1(self):
        char = int_to_mutant_hex_char(36)
        expected_char = 'a'
        self.assertEqual(char, expected_char)

    def test_num_greater_than_thirtysix_t2(self):
        char = int_to_mutant_hex_char(49)
        expected_char = 'n'
        self.assertEqual(char, expected_char)

    def test_num_greater_than_thirtysix_t3(self):
        char = int_to_mutant_hex_char(60)
        expected_char = 'y'
        self.assertEqual(char, expected_char)

    def test_num_greater_than_thirtysix_t4(self):
        char = int_to_mutant_hex_char(61)
        expected_char = 'z'
        self.assertEqual(char, expected_char)


class TestNormalToPacked(TestCase):
    """Unit tests for normal_to_packed() method"""

    def test_number_t0(self):
        expected_desig = '00001       '
        packed_desig, ret_code = normal_to_packed('1')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_number_t1(self):
        expected_desig = '00719       '
        packed_desig, ret_code = normal_to_packed('719')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_number_t2(self):
        expected_desig = 'B7317       '
        packed_desig, ret_code = normal_to_packed('117317')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_number_t3(self):
        expected_desig = 'Z7317       '
        packed_desig, ret_code = normal_to_packed('357317')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_number_t4(self):
        expected_desig = 'a7317       '
        packed_desig, ret_code = normal_to_packed('367317')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_number_t5(self):
        expected_desig = 'g1234       '
        packed_desig, ret_code = normal_to_packed('421234')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_comet_t1(self):
        expected_desig = '    CK13A010'
        packed_desig, ret_code = normal_to_packed('C/2013 A1')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_comet_t2(self):
        expected_desig = '    PK01T000'
        packed_desig, ret_code = normal_to_packed('P/2001 T')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_comet_t3(self):
        expected_desig = '0004P       '
        packed_desig, ret_code = normal_to_packed('P/4')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_comet_t4(self):
        expected_desig = '0314P       '
        packed_desig, ret_code = normal_to_packed('P/314')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_comet_t5(self):
        expected_desig = '    CJ83Z150'
        packed_desig, ret_code = normal_to_packed('C/1983 Z15')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_comet_packed1(self):
        expected_desig = '0060P       '
        packed_desig, ret_code = normal_to_packed('0060P  ')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_provdesig_t1(self):
        expected_desig = '     K15D00D'
        packed_desig, ret_code = normal_to_packed('2015   DD')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_provdesig_t2(self):
        expected_desig = '     J99Z01A'
        packed_desig, ret_code = normal_to_packed('1999 ZA1')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_provdesig_t3(self):
        expected_desig = '     J99Z11A'
        packed_desig, ret_code = normal_to_packed('1999 ZA11')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_provdesig_t4(self):
        expected_desig = '     K00LA0W'
        packed_desig, ret_code = normal_to_packed('2000 LW100')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_provdesig_t5(self):
        expected_desig = '     K10LZ9W'
        packed_desig, ret_code = normal_to_packed('2010 LW359')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_provdesig_t6(self):
        expected_desig = '     K00La0W'
        packed_desig, ret_code = normal_to_packed('2000 LW360')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_provdesig_t7(self):
        expected_desig = '     K00Az9Z'
        packed_desig, ret_code = normal_to_packed('2000 AZ619')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_baddesig_t1(self):
        expected_desig = '            '
        packed_desig, ret_code = normal_to_packed('FOO BAR')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, -1)

    def test_baddesig_t2(self):
        expected_desig = '            '
        packed_desig, ret_code = normal_to_packed('12345 A')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, -1)

    def test_shortnumber_t1(self):
        expected_desig = '01627       '
        packed_desig, ret_code = normal_to_packed('1627')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_shortnumber_t2(self):
        expected_desig = '00433       '
        packed_desig, ret_code = normal_to_packed('433')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_shortnumber_t3(self):
        expected_desig = '00016       '
        packed_desig, ret_code = normal_to_packed('16')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)

    def test_shortnumber_t4(self):
        expected_desig = '00004       '
        packed_desig, ret_code = normal_to_packed('4')
        self.assertEqual(packed_desig, expected_desig)
        self.assertEqual(ret_code, 0)


class TestDetermineAsteroidType(TestCase):

    def test_neo1(self):
        expected_type = 'N'
        obj_type = determine_asteroid_type(1.0, 0.1)
        self.assertEqual(obj_type, expected_type)

    def test_neo2(self):
        expected_type = 'N'
        obj_type = determine_asteroid_type(1.299, 0.4)
        self.assertEqual(obj_type, expected_type)

    def test_neo3(self):
        expected_type = 'N'
        obj_type = determine_asteroid_type(1.3, 0.99)
        self.assertEqual(obj_type, expected_type)

    def test_nonneo1(self):
        expected_type = 'A'
        obj_type = determine_asteroid_type(1.301, 0.1)
        self.assertEqual(obj_type, expected_type)

    def test_nonneo2(self):
        expected_type = 'A'
        obj_type = determine_asteroid_type(1.301, 0.9)
        self.assertEqual(obj_type, expected_type)

    def test_comet1(self):
        expected_type = 'C'
        obj_type = determine_asteroid_type(0.301, 0.9991)
        self.assertEqual(obj_type, expected_type)

    def test_comet2(self):
        expected_type = 'C'
        obj_type = determine_asteroid_type(1.301, 1.0000)
        self.assertEqual(obj_type, expected_type)

    def test_comet3(self):
        expected_type = 'C'
        obj_type = determine_asteroid_type(5.51, 1.00001)
        self.assertEqual(obj_type, expected_type)

    def test_centaur1(self):
        expected_type = 'E'
        obj_type = determine_asteroid_type(5.51, 0.1)
        self.assertEqual(obj_type, expected_type)

    def test_centaur2(self):
        expected_type = 'E'
        obj_type = determine_asteroid_type(5.5, 0.817275747508)
        self.assertEqual(obj_type, expected_type)

    def test_centaur3(self):
        expected_type = 'E'
        obj_type = determine_asteroid_type(30.099, 0.0)
        self.assertEqual(obj_type, expected_type)

    def test_centaur4(self):
        expected_type = 'A'
        obj_type = determine_asteroid_type(5.49, 0.82)
        self.assertEqual(obj_type, expected_type)

    def test_kbo1(self):
        expected_type = 'K'
        obj_type = determine_asteroid_type(30.1001, 0.0)
        self.assertEqual(obj_type, expected_type)

    def test_kbo2(self):
        expected_type = 'K'
        obj_type = determine_asteroid_type(42, 0.998)
        self.assertEqual(obj_type, expected_type)

    def test_trojan1(self):
        expected_type = 'T'
        obj_type = determine_asteroid_type(5.05, 0.0)
        self.assertEqual(obj_type, expected_type)

    def test_trojan2(self):
        expected_type = 'T'
        obj_type = determine_asteroid_type(5.05, 0.05607)
        self.assertEqual(obj_type, expected_type)

    def test_trojan3(self):
        expected_type = 'A'
        obj_type = determine_asteroid_type(5.05, 0.0561)
        self.assertEqual(obj_type, expected_type)


class TestDetermineTimeOfPerihelion(TestCase):

    def test_perihelion_in_future(self):
        meandist = 1000.0
        meananom = 359.0
        epochofel = datetime(2016, 7, 11, 0, 0, 0)

        expected_time_of_perih = epochofel + timedelta(days=32084.54804999279)

        time_of_perih = determine_time_of_perih(meandist, meananom, epochofel)

        self.assertEqual(expected_time_of_perih, time_of_perih)

    def test_perihelion_in_past(self):
        meandist = 1000.0
        meananom = 1.0
        epochofel = datetime(2016, 7, 11, 0, 0, 0)

        expected_time_of_perih = epochofel - timedelta(days=32084.54804999279)

        time_of_perih = determine_time_of_perih(meandist, meananom, epochofel)

        self.assertEqual(expected_time_of_perih, time_of_perih)


class TestConvertAstToComet(TestCase):

    def setUp(self):
        self.params = {
                         'provisional_name': 'P10G50L',
                         'provisional_packed': None,
                         'name': 'C/2018 A5',
                         'origin': 'M',
                         'source_type': 'C',
                         'elements_type': 'MPC_COMET',
                         'active': False,
                         'fast_moving': False,
                         'urgency': None,
                         'epochofel': datetime(2018, 1, 2, 0, 0),
                         'orbinc': 23.77111,
                         'longascnode': 88.06834,
                         'argofperih': 356.74589,
                         'eccentricity': 0.5415182,
                         'meandist': 5.8291288,
                         'meananom': 7.63767,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 17.0,
                         'slope': 0.15,
                         'score': 40,
                         'discovery_date': datetime(2018, 1, 13, 9, 36),
                         'num_obs': 18,
                         'arc_length': 3.58,
                         'not_seen': 0.757,
                         'updated': True,
                         'ingest': datetime(2018, 1, 14, 13, 20, 7),
                         'update_time': datetime(2018, 1, 17, 16, 43, 16)
                      }
        self.body = Body.objects.create(**self.params)

    def test_asteroid(self):
        kwargs = {'source_type': 'A', 'name': '2018 AA5', 'active': False, 'source_subtype_1': ''}

        new_kwargs = convert_ast_to_comet(kwargs, self.body)

        self.assertEqual(kwargs, new_kwargs)

    def test_comet(self):
        expected_kwargs = { 'source_type': 'C',
                            'name': 'C/2018 A5',
                            'active': True,
                            'elements_type' : 'MPC_COMET',
                            'perihdist' : 2.6725494646558405,
                            'epochofperih' : datetime(2017, 9, 14, 22, 34, 45, 428836),
                            'meananom' : None,
                            'slope' : 4.0,
                            'eccentricity' : self.body.eccentricity,
                            'epochofel' : self.body.epochofel,
                            'meandist' : self.body.meandist
                          }
        kwargs = {'source_type': 'C', 'name': 'C/2018 A5', 'active': True}

        new_kwargs = convert_ast_to_comet(kwargs, self.body)

        self.assertEqual(expected_kwargs, new_kwargs)

    def test_new_body(self):
        kwargs = {'source_type': 'A', 'name': '2018 ZZ99', 'active': False, 'source_subtype_1': ''}
        expected_kwargs = kwargs

        blank_body, created = Body.objects.get_or_create(provisional_name='Wibble')
        self.assertTrue(created)
        self.assertEqual(None, blank_body.meandist)
        self.assertEqual(None, blank_body.eccentricity)

        new_kwargs = convert_ast_to_comet(kwargs, blank_body)

        self.assertEqual(expected_kwargs, new_kwargs)

    def test_parabolic(self):
        self.body.eccentricity = 1.0
        self.body.save()
        expected_kwargs = { 'source_type': 'C',
                            'name': 'C/2018 A5',
                            'active': True,
                            'elements_type' : 'MPC_COMET',
                            'epochofperih' : datetime(2017, 9, 14, 22, 34, 45, 428836),
                            'meananom' : None,
                            'slope' : 4.0,
                            'eccentricity' : self.body.eccentricity,
                            'epochofel' : self.body.epochofel,
                            'meandist' : self.body.meandist,
                            'source_subtype_1': ''
                          }

        kwargs = {'source_type': 'C', 'name': 'C/2018 A5', 'active': True, 'source_subtype_1': ''}

        new_kwargs = convert_ast_to_comet(kwargs, self.body)

        self.assertEqual(expected_kwargs, new_kwargs)
