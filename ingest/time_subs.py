'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

time_subs.py -- Various routines to handle times.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from datetime import datetime,timedelta

def parse_neocp_date(neocp_datestr, dbg=False):
    '''Parse dates from the NEOCP (e.g. '(Nov. 16.81 UT)' ) into a datetime 
    object and return this. No sanity checking of the input is done'''
    month_map = { 'Jan' : 1,
    	    	  'Feb' : 2,
		  'Mar' : 3,
		  'Apr' : 4,
		  'May' : 5,
		  'Jun' : 6,
		  'Jul' : 7,
		  'Aug' : 8,
		  'Sep' : 9,
		  'Oct' : 10,
		  'Nov' : 11,
		  'Dec' : 12 } 
		  
    chunks = neocp_datestr.split(' ')
    if dbg: print chunks
    if len(chunks) != 3: return None
    month_str = chunks[0].replace('(', '').replace('.', '')
    day_chunks = chunks[1].split('.') 
    if dbg: print day_chunks
    neocp_datetime = datetime(year=datetime.utcnow().year, month=month_map[month_str[0:3]],
    	day=int(day_chunks[0]))
	
    decimal_day = float('0.' + day_chunks[1].split()[0])
    neocp_datetime = neocp_datetime + timedelta(days=decimal_day)
    
    return neocp_datetime
    
def round_datetime(date_to_round, round_mins=10, round_up=False):
    '''Rounds the passed datetime object, <date_to_round>, to the 
    'floor' (default) or the 'ceiling' (if [roundup=True]) of
    the nearest passed amount (which defaults to 10min)'''
    
    correct_mins = 0
    if round_up:
        correct_mins = round_mins
    date_to_round = date_to_round - timedelta(minutes=(date_to_round.minute % round_mins)-correct_mins,
                	seconds=date_to_round.second,
                	microseconds=date_to_round.microsecond)

    return date_to_round

def extract_mpc_epoch(epochstring):
    '''Convert packed MPC epoch format (e.g. 'J974L') from NEOCP orbit files
    into a datetime.datetime epoch (e.g. '1997 4 21'). Returns -1 if invalid
    length (no other sanity checking is done)'''


    
    if len(epochstring) != 5: return -1
    year = 100 * (ord(epochstring[0]) - ord('A') + 10) + \
        10 * (ord(epochstring[1]) - ord('0')) + \
    (ord(epochstring[2]) - ord('0'))

    month = extract_packed_date(epochstring[3])
    day = extract_packed_date(epochstring[4])

    return datetime(year, month, day, 0)

def extract_packed_date(value):
    lookup = {  'A'     : 10,
            'B'     : 11,
            'C'     : 12,
            'D'     : 13,
            'E'     : 14,
            'F'     : 15,
            'G'     : 16,
            'H'     : 17,
            'I'     : 18,
            'J'     : 19,
            'K'     : 20,
            'L'     : 21,
            'M'     : 22,
            'N'     : 23,
            'O'     : 24,
            'P'     : 25,
            'Q'     : 26,
            'R'     : 27,
            'S'     : 28,
            'T'     : 29,
            'U'     : 30,
            'V'     : 31}
    try:
        return int(value) 
    except ValueError:
        return lookup[value]
