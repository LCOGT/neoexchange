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

from nose.tools import eq_, assert_equal, assert_almost_equal, raises, nottest

#Import module to test
from ast_subs import *
from sources_subs import parse_goldstone_chunks

class TestIntToMutantHexChar(object):
    '''Unit tests for the int_to_mutant_hex_char() method'''
    
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
            expected_msg = ("Number out of range 0...61")
            assert_equal(e.__str__(), expected_msg)

    def test_bad_mutant_too_large(self):
        try:
            int_to_mutant_hex_char(62)
            assert False
        except MutantError as e:
            expected_msg = ("Number out of range 0...61")
            assert_equal(e.__str__(), expected_msg)

    def test_bad_mutant_not_number1(self):
        try:
            int_to_mutant_hex_char('9')
            assert False
        except MutantError as e:
            expected_msg = ("Number out of range 0...61")
            assert_equal(e.__str__(), expected_msg)

    def test_bad_mutant_not_number2(self):
        try:
            int_to_mutant_hex_char('FOO')
            assert False
        except MutantError as e:
            expected_msg = ("Number out of range 0...61")
            assert_equal(e.__str__(), expected_msg)

    def test_num_less_than_ten(self):
        char = int_to_mutant_hex_char(8)
        expected_char = '8'
        assert_equal(char, expected_char)

    def test_num_less_than_thirtysix_t1(self):
        char = int_to_mutant_hex_char(10)
        expected_char = 'A'
        assert_equal(char, expected_char)

    def test_num_less_than_thirtysix_t2(self):
        char = int_to_mutant_hex_char(23)
        expected_char = 'N'
        assert_equal(char, expected_char)

    def test_num_less_than_thirtysix_t3(self):
        char = int_to_mutant_hex_char(34)
        expected_char = 'Y'
        assert_equal(char, expected_char)

    def test_num_less_than_thirtysix_t4(self):
        char = int_to_mutant_hex_char(35)
        expected_char = 'Z'
        assert_equal(char, expected_char)

    def test_num_greater_than_thirtysix_t1(self):
        char = int_to_mutant_hex_char(36)
        expected_char = 'a'
        assert_equal(char, expected_char)

    def test_num_greater_than_thirtysix_t2(self):
        char = int_to_mutant_hex_char(49)
        expected_char = 'n'
        assert_equal(char, expected_char)

    def test_num_greater_than_thirtysix_t3(self):
        char = int_to_mutant_hex_char(60)
        expected_char = 'y'
        assert_equal(char, expected_char)

    def test_num_greater_than_thirtysix_t4(self):
        char = int_to_mutant_hex_char(61)
        expected_char = 'z'
        assert_equal(char, expected_char)


class TestNormalToPacked(object):
    '''Unit tests for normal_to_packed() method'''
    
    def test_number_t0(self):
        expected_desig = '00001       '
        packed_desig, ret_code = normal_to_packed('1')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_number_t1(self):
        expected_desig = '00719       '
        packed_desig, ret_code = normal_to_packed('719')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_number_t2(self):
        expected_desig = 'B7317       '
        packed_desig, ret_code = normal_to_packed('117317')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_number_t3(self):
        expected_desig = 'Z7317       '
        packed_desig, ret_code = normal_to_packed('357317')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_number_t4(self):
        expected_desig = 'a7317       '
        packed_desig, ret_code = normal_to_packed('367317')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_number_t5(self):
        expected_desig = 'g1234       '
        packed_desig, ret_code = normal_to_packed('421234')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_comet_t1(self):
        expected_desig = '    CK13A010'
        packed_desig, ret_code = normal_to_packed('C/2013 A1')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_comet_t2(self):
        expected_desig = '    PK01T000'
        packed_desig, ret_code = normal_to_packed('P/2001 T')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_comet_t3(self):
        expected_desig = '0004P       '
        packed_desig, ret_code = normal_to_packed('P/4')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_comet_t4(self):
        expected_desig = '0314P       '
        packed_desig, ret_code = normal_to_packed('P/314')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_comet_t5(self):
        expected_desig = '    CJ83Z150'
        packed_desig, ret_code = normal_to_packed('C/1983 Z15')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_provdesig_t1(self):
        expected_desig = '     K15D00D'
        packed_desig, ret_code = normal_to_packed('2015   DD')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_provdesig_t2(self):
        expected_desig = '     J99Z01A'
        packed_desig, ret_code = normal_to_packed('1999 ZA1')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_provdesig_t3(self):
        expected_desig = '     J99Z11A'
        packed_desig, ret_code = normal_to_packed('1999 ZA11')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_provdesig_t4(self):
        expected_desig = '     K00LA0W'
        packed_desig, ret_code = normal_to_packed('2000 LW100')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)

    def test_provdesig_t5(self):
        expected_desig = '     K10LZ9W'
        packed_desig, ret_code = normal_to_packed('2010 LW359')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_provdesig_t6(self):
        expected_desig = '     K00La0W'
        packed_desig, ret_code = normal_to_packed('2000 LW360')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_provdesig_t7(self):
        expected_desig = '     K00Az9Z'
        packed_desig, ret_code = normal_to_packed('2000 AZ619')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, 0)
    
    def test_baddesig_t1(self):
        expected_desig = '            '
        packed_desig, ret_code = normal_to_packed('FOO BAR')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, -1)
    
    def test_baddesig_t1(self):
        expected_desig = '            '
        packed_desig, ret_code = normal_to_packed('12345 A')
        assert_equal(packed_desig, expected_desig)
        assert_equal(ret_code, -1)

class TestGoldstoneChunkParser(object):
    '''Unit tests for the sources_subs.parse_goldstone_chunks() method'''
    
    def test_specficdate_provis_desig(self):
        expected_objid = '2015 FW117'
        chunks = [u'2015', u'Apr', u'1', u'2015', u'FW117', u'Yes', u'Yes', u'Scheduled']
        obj_id = parse_goldstone_chunks(chunks)
        assert_equal(expected_objid, obj_id)

    def test_specficdate_astnumber(self):
        expected_objid = '285331'
        chunks = [u'2015', u'May', u'16-17', u'285331', u'1999', u'FN53', u'No', u'Yes', u'R']
        obj_id = parse_goldstone_chunks(chunks)
        assert_equal(expected_objid, obj_id)

    def test_unspecificdate_provis_desig(self):
        expected_objid = '2010 NY65'
        chunks = [u'2015', u'Jun', u'2010', u'NY65', u'No', u'Yes', u'R', u'PHA']
        obj_id = parse_goldstone_chunks(chunks)
        assert_equal(expected_objid, obj_id)

    def test_unspecificdate_astnumber(self):
        expected_objid = '385186'
        chunks = [u'2015', u'Jul', u'385186', u'1994', u'AW1', u'No', u'Yes', u'PHA', u'BINARY', u'(not', u'previously', u'observed', u'with', u'radar)']
        obj_id = parse_goldstone_chunks(chunks)
        assert_equal(expected_objid, obj_id)
    
    def test_specficdate_named_ast(self):
        expected_objid = '1566' # '(1566) Icarus'
        chunks = [u'2015', u'Jun', u'13-17', u'1566', u'Icarus', u'No', u'Yes', u'R', u'PHA', u'June', u'13/14,', u'14/15,', u'and', u'16/17']
        obj_id = parse_goldstone_chunks(chunks)
        assert_equal(expected_objid, obj_id)

    def test_unspecficdate_named_ast(self):
        expected_objid = '1685' # '(1685) Toro'
        chunks = ['2016', 'Jan', '1685', 'Toro', 'No', 'No', 'R']
        obj_id = parse_goldstone_chunks(chunks)
        assert_equal(expected_objid, obj_id)
