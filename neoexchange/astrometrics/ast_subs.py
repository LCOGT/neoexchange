'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

ast_subs.py -- Asteroid desigination related routines.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import re
from math import degrees, sqrt
from datetime import timedelta

class PackedError(Exception):
    '''Raised when an invalid pack code is found'''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value
    
class MutantError(Exception):
    '''Raised when an invalid mutant hex code is found'''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value
    

def mutant_hex_char_to_int(c):
    '''"Mutant hex" is frequently used by MPC.  It uses the usual hex digits
    0123456789ABCDEF for numbers 0 to 15,  followed by G...Z for 16...35
    and a...z for 36...61.
    This routine turns a mutant hex char into an integer'''
   
# Test for something other than a single char
    if len(c) != 1:
    	return -1
    
# Decode char to integer       
    if c >= '0' and c <= '9':
    	return ord(c) - ord('0')
    elif c >= 'A' and c <= 'Z':
    	return (ord(c)-ord('A') +10)
    elif c >= 'a' and c <= 'z':
    	return (ord(c)-ord('a') + 36)
    else:
    	return -1

def int_to_mutant_hex_char(number):
    '''"Mutant hex" is frequently used by MPC.  It uses the usual hex digits
    0123456789ABCDEF for numbers 0 to 15,  followed by G...Z for 16...35
    and a...z for 36...61.
    This routine turns an integer into a mutant hex char.'''

    if type(number) != int:
        raise MutantError("Not an integer")
    if number < 0 or number > 61:
        raise MutantError("Number out of range 0...61")
    
    if number < 10:
        rval = ord('0')
    elif number < 36:
        rval = ord('A') - 10
    else:
        rval = ord('a')  - 36 

    return chr(rval + number)

def normal_to_packed(obj_name, dbg=False):
    '''Routine to convert normal names for a comet/asteroid into packed 
    desiginations. It should handle all normal asteroid and comet desiginations 
    but does not handle natural satellites. The code has been converted (badly)
    from Bill Gray's find_orb C routine.'''
    
    rval = 0
    comet = False
    
    # Check for comet-style designations such as 'P/1995 O1' 
    # and such.  Leading character can be P, C, X, D, or A.
    if obj_name[0] in 'PCXDA' and obj_name[1] == "/":
        comet = True
        comet_type = obj_name[0]
        obj_name = obj_name[2:]
    
    buff = obj_name.replace(" ", "")
    if dbg: print("len(buff)=", len(buff))
    
    # If the name starts with four digits followed by an uppercase letter, it's
    # a provisional (un-numbered) designation e.g. '1984 DA' or '2015 BM510'
    if len(buff) >= 4 and buff[0:4].isdigit() and buff[4].isupper():
        year = int(buff[0:4])

        if comet == False:
            comet_type = " "
        pack11 = '0'
        i=5
        if len(buff) > 5 and buff[5].isupper():
            pack11 = buff[5]
            i = i+1
        
        sub_designator_str = re.sub('(\d*)([a-zA-Z]*)$', r'\1', buff[i:])
        if dbg: print('sub_designator_str=', sub_designator_str,len(sub_designator_str))
        sub_designator = 0
        if sub_designator_str != '':
            sub_designator = int(sub_designator_str)
        pack10 = chr(ord('0')  + sub_designator % 10)
        if sub_designator < 100:
            pack9 = chr(ord('0')  + sub_designator // 10)
        elif sub_designator < 360:
            pack9 = chr(ord('A')  + sub_designator // 10 - 10)
        else:
            pack9 = chr(ord('a')  + sub_designator // 10 - 36)
        packed_desig = "    %c%c%02d%c%c%c%c" % ( comet_type, 
            ord('A') - 10 + year // 100, year % 100,
            str(buff[4]).upper(), pack9, pack10, pack11)
    elif buff.isdigit():
        # Simple numbered asteroid or comet
        number = int(buff)

        if comet:
            packed_desig = "%04d%c       " % ( number, comet_type)
        else:
            packed_desig = "%c%04d       " % ( int_to_mutant_hex_char( number // 10000), number % 10000);
    else:
        # Bad id
        packed_desig = ' ' * 12
        rval = -1
    return ( packed_desig, rval)

def determine_asteroid_type(perihdist, eccentricity):
    '''Determines the object class from the perihelion distance <perihdist> and
    the eccentricity <eccentricity> and returns it as a single character code
    as defined in core/models.py.

    Currently the checked types are:
    1) NEO (perihelion < 1.3 AU)
    2) Centaur (perihelion > 5.5 AU (orbit of Jupiter) & semi-major axis < 30.1 AU
        (orbit of Neptune)
    3) KBO (perihelion > 30.1 AU (orbit of Neptune)'''

    jupiter_semidist = 5.5
    neptune_semidist = 30.1
    juptrojan_lowlimit = 5.05
    juptrojan_hilimit = 5.35

    obj_type = 'A'
    if perihdist <= 1.3 and eccentricity < 0.999:
        obj_type = 'N'  # NEO
    else:
        # Test for eccentricity close to or greater than 1.0
        if abs(eccentricity-1.0) >=  1e-3 and eccentricity < 1.0:
            semi_axis = perihdist / (1.0 - eccentricity )
            if perihdist >= jupiter_semidist and semi_axis >= jupiter_semidist \
                and semi_axis <= neptune_semidist:
                obj_type = 'E' # Centaur
            elif perihdist > neptune_semidist:
                obj_type = 'K'
            elif semi_axis >= juptrojan_lowlimit and semi_axis <= juptrojan_hilimit:
                obj_type = 'T'
        else:
            obj_type = 'C'  # Comet
    return obj_type

def determine_time_of_perih(meandist, meananom, epochofel):
    '''Calculate time of perihelion passage from passed semimajor axis (<meandist>:in AU),
    mean anomaly (<meananom>:in degrees), and the epoch of the elements 
    (<epochofel>:as a datetime).
    Returns the epoch of perihelion as a datetime.'''

    gauss_k = degrees(0.01720209895) # Gaussian gravitional constant

    # Compute 'n', the mean daily motion
    n = gauss_k / (meandist * sqrt( meandist ))

    if meananom > 180.0 and meananom < 360.0:
        days_from_perihelion = (360.0 - meananom) / n
    else:
        days_from_perihelion = -( meananom / n )
    epochofperih = epochofel + timedelta(days=days_from_perihelion)
#    print n, days_from_perihelion, epochofperih

    return epochofperih
