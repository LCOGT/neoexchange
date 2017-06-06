'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2016 LCOGT

sources_subs.py -- Code to retrieve asteroid infomation from various sources.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import logging
import urllib2, os
import imaplib
import json
import email
from urlparse import urljoin
from re import sub
from math import degrees
from datetime import datetime, timedelta
from socket import error
from random import randint
from time import sleep

import requests
import json
from bs4 import BeautifulSoup
import pyslalib.slalib as S

from astrometrics.time_subs import parse_neocp_decimal_date, jd_utc2datetime
from astrometrics.ephem_subs import return_LCOGT_site_codes_mapping
from core.urlsubs import get_telescope_states
from django.conf import settings

logger = logging.getLogger(__name__)

def download_file(url, file_to_save):
    '''Helper routine to download from a URL and save into a file with error trapping'''

    attempts = 0
    while attempts < 3:
        try:
            url_handle = urllib2.urlopen(url)
            file_handle = open(file_to_save, 'wb')
            for line in url_handle:
                file_handle.write(line)
            url_handle.close()
            file_handle.close()
            print "Downloaded:", file_to_save
            break
        except urllib2.HTTPError, e:
            attempts += 1
            if hasattr(e, 'reason'):
                print "HTTP Error %d: %s, retrying" % (e.code, e.reason)
            else:
                print "HTTP Error: %s" % (e.code,)

def random_delay(lower_limit=10, upper_limit=20):
    '''Waits a random number of integer seconds between [lower_limit; default 10]
    and [upper_limit; default 20]. Useful for slowing down web requests to prevent
    overloading remote systems. The executed delay is returned.'''

    try:
        lower_limit = max(int(lower_limit), 0)
    except ValueError:
        lower_limit = 10
    try:
        upper_limit = int(upper_limit)
    except ValueError:
        upper_limit = 20

    delay = randint(lower_limit, upper_limit)
    sleep(delay)

    return delay

def fetchpage_and_make_soup(url, fakeagent=False, dbg=False, parser="html.parser"):
    '''Fetches the specified URL from <url> and parses it using BeautifulSoup.
    If [fakeagent] is set to True, we will pretend to be a Firefox browser on
    Linux rather than as Python-urllib (in case of anti-machine filtering).
    If [parser] is specified, try and use that BeautifulSoup parser (which
    needs to be installed). Defaults to "html.parser" if not specified; may need
    to use "html5lib" to properly parse malformed MPC pages.

    Returns the page as a BeautifulSoup object if all was OK or None if the
    page retrieval failed.'''

    req_headers = {}
    if fakeagent == True:
        req_headers = {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0",
                      }
    req_page = urllib2.Request(url, headers=req_headers)
    opener = urllib2.build_opener() # create an opener object
    try:
        response = opener.open(req_page)
    except urllib2.URLError as e:
        if not hasattr(e, "code"):
            raise
        print "Page retrieval failed:", e
        return None

  # Suck the HTML down
    neo_page = response.read()

# Parse into beautiful soup
    page = BeautifulSoup(neo_page, parser)

    return page

def parse_previous_NEOCP_id(items, dbg=False):
    crossmatch = ['', '', '', '']
    if len(items) == 1:
# Is of the form "<foo> does not exist" or "<foo> was not confirmed". But can
# now apparently include comets...
        chunks = items[0].split()
        none_id = ''
        body = chunks[0]
        if chunks[1].find('does') >= 0:
            none_id = 'doesnotexist'
        elif chunks[1].find('was') >= 0:
            none_id = 'wasnotconfirmed'
        elif chunks[0].find('Comet') >=0:
            body = chunks[4]
            none_id = chunks[1] + ' ' + chunks[2]

        crossmatch = [body, none_id, '', ' '.join(chunks[-3:])]
    elif len(items) == 3:
# Is of the form "<foo> = <bar>(<date> UT)"
        if items[0].find('Comet') != 1:
            newid = str(items[0]).lstrip()+items[1].string.strip()
            provid_date = items[2].split('(')
            provid = provid_date[0].replace(' = ', '')
            date = '('+provid_date[1].strip()
            mpec = ''
        else:
            if dbg: print "Comet found, parsing"
            if dbg: print "Items=",items

            items[0] = sub(r"\s+\(", r"(", items[0])
            # Occasionally we get things of the form " Comet 2015 TQ209 = LM02L2J(Oct. 24.07 UT)"
            # without the leading "C/<year>". The regexp below fixes this by
            # looking for any amount of whitespace at the start of the string,
            # the word 'Comet',any amount of whitespace, and any amount of
            # digits (the '(?=') part looks for but doesn't capture/remove the
            # regexp that follows
            items[0] = sub(r"^\s+Comet\s+(?=\d+)", r"Comet C/", items[0])
            subitems = items[0].lstrip().split()
            if dbg: print "Subitems=", subitems
            newid = subitems[1] + ' ' + subitems[2]
            provid_date = subitems[4].split('(')
            provid = provid_date[0]
            date = '('+provid_date[1] + ' ' + subitems[5] + ' ' + subitems[6]
            mpec = items[1].contents[0].string + items[1].contents[1].string

        crossmatch = [provid, newid, mpec, date]
    elif len(items) == 5:
# Is of the form "<foo> = <bar> (date UT) [see MPEC<x>]"
        newid = str(items[0]).lstrip()+items[1].string.strip()
        provid_date = items[2].split()
        provid = provid_date[1]
        date = ' '.join(provid_date[2:5])
        mpec = items[3].contents[0].string + items[3].contents[1].string
        crossmatch = [provid, newid, mpec, date]
    else:
        logger.warn("Unknown number of fields. items=%s", items)

    return crossmatch

def fetch_previous_NEOCP_desigs(dbg=False):
    '''Fetches the "Previous NEO Confirmation Page Objects" from the MPC, parses
    it and returns a list of lists of object, provisional designation or failure
    reason, date and MPEC.'''

    previous_NEOs_url = 'http://www.minorplanetcenter.net/iau/NEO/ToConfirm_PrevDes.html'

    page = fetchpage_and_make_soup(previous_NEOs_url, parser="html5lib")
    if page == None:
        return None

    divs = page.find_all('div', id="main")

    crossids = []
    for row in divs[0].find_all('li'):
        items = row.contents
        if dbg: print items,len(items)
# Skip the first "Processing" list item
        if items[0].strip() == 'Processing':
            continue
        crossmatch = parse_previous_NEOCP_id(items)
# Append to list
        if crossmatch != ['', '', '', '']:
            crossids.append(crossmatch)

    return crossids

def fetch_NEOCP(dbg=False):

    '''Fetches the NEO Confirmation Page and returns a BeautifulSoup object
    of the page.'''

    NEOCP_url = 'http://www.minorplanetcenter.net/iau/NEO/toconfirm_tabular.html'

    neocp_page = fetchpage_and_make_soup(NEOCP_url)
    return neocp_page

def parse_NEOCP(neocp_page, dbg=False):

    '''Takes a BeautifulSoup object of the NEO Confirmation Page and extracts a
    list of objects, which is returned.'''

    if type(neocp_page) != BeautifulSoup:
        return None

# Find all the input checkboxes with "obj" in the name
    neocp_objects = neocp_page.findAll('input', attrs={"name" : "obj"})
    if len(neocp_objects) == 0:
        return None

    new_objects = []
    for row in neocp_objects:
        new_objects.append(row['value'])

    return new_objects

def parse_NEOCP_extra_params(neocp_page, dbg=False):

    '''Takes a BeautifulSoup object of the NEO Confirmation Page and extracts a
    list of objects along with a dictionary of extra parameters (score,
    discovery date, update date, # obs, arc length (in days) and not seen (in days)
    which are returned.'''

    PCCP_url = 'http://www.minorplanetcenter.net/iau/NEO/pccp_tabular.html'

    if type(neocp_page) != BeautifulSoup:
        return None

# Find the table with the objects
    table = neocp_page.find("table", { "class" : "tablesorter" })
    if table == None:
        return None
    table_body = table.find("tbody")
    if table_body == None:
        return None

    new_objects = []
    object_list = []
    pccp_page = None
    for row in table_body.findAll("tr"):
        cols = row.findAll("td")
        if len(cols) != 0:
            # Turn the HTML non-breaking spaces (&nbsp;) into regular spaces
            cols = [ele.text.replace(u'\xa0', u' ').strip() for ele in cols]
            if dbg: print "Cols=",cols, len(cols)
            pccp = False
            try:
                update_date = cols[6].split()[0]
                if 'Moved' in update_date:
                    pccp = True
                    updated = None
                    update_date = None
                else:
                    updated = None
                    if update_date[0] == 'U':
                        updated = True
                    elif update_date[0] == 'A':
                        updated = False
                    update_jd = update_date[1:]
                    update_date = jd_utc2datetime(update_jd)
            except:
                updated = None
                update_date = None
            if pccp != True:
                try:
                    score = int(cols[1][0:3])
                except:
                    score = None
                neocp_datetime = parse_neocp_decimal_date(cols[2])
                try:
                    nobs = int(cols[8])
                except:
                    nobs = None
                try:
                    arc_length = float(cols[9])
                except:
                    arc_length = None
                try:
                    not_seen = float(cols[11])
                except:
                    not_seen = None

                obj_id = cols[0].split()
                if len(obj_id) == 2:
                    obj_id = obj_id[0]
                else:
                    obj_id = obj_id[0][0:7]

                params = { 'score' : score,
                           'discovery_date' :  neocp_datetime,
                           'update_time' : update_date,
                           'num_obs' : nobs,
                           'arc_length' : arc_length,
                           'not_seen' : not_seen,
                           'updated' : updated
                         }
                if obj_id not in object_list:
                    object_list.append(obj_id)
                    new_object = (obj_id, params)
                    new_objects.append(new_object)
            else:
                if pccp_page == None:
                    pccp_page = fetchpage_and_make_soup(PCCP_url)
                comet_objects = parse_PCCP(pccp_page)
                if dbg: print comet_objects
                for comet in comet_objects:
                    obj_id = comet[0]
                    if dbg: print "obj_id=", obj_id
                    if obj_id not in object_list:
                        object_list.append(obj_id)
                        new_object = (obj_id, comet[1])
                        new_objects.append(new_object)

    return new_objects

def parse_PCCP(pccp_page, dbg=False):

    if type(pccp_page) != BeautifulSoup:
        return None

# Find the table with the objects
    table = pccp_page.find("table", { "class" : "tablesorter" })
    if table == None:
        return None
    table_body = table.find("tbody")
    if table_body == None:
        return None

    new_objects = []
    object_list = []
    pccp_page = None
    for row in table_body.findAll("tr"):
        cols = row.findAll("td")
        if len(cols) != 0:
            # Turn the HTML non-breaking spaces (&nbsp;) into regular spaces
            cols = [ele.text.replace(u'\xa0', u' ').strip() for ele in cols]
            if dbg: print "Cols=",cols, len(cols)
            pccp = False
            try:
                update_date = cols[6].split()[0]
                updated = None
                if update_date[0] == 'U':
                    updated = True
                elif update_date[0] == 'A':
                    updated = False
                update_jd = update_date[1:]
                update_date = jd_utc2datetime(update_jd)
            except:
                updated = None
                update_date = None
            try:
                score = int(cols[1][0:3])
            except:
                score = None
            neocp_datetime = parse_neocp_decimal_date(cols[2])
            try:
                nobs = int(cols[8])
            except:
                nobs = None
            try:
                arc_length = float(cols[9])
            except:
                arc_length = None
            try:
                not_seen = float(cols[11])
            except:
                not_seen = None

            obj_id = cols[0].split()
            if len(obj_id) == 2:
                obj_id = obj_id[0]
            else:
                obj_id = obj_id[0][0:7]

            params = { 'score' : score,
                       'discovery_date' :  neocp_datetime,
                       'update_time' : update_date,
                       'num_obs' : nobs,
                       'arc_length' : arc_length,
                       'not_seen' : not_seen,
                       'updated' : updated
                     }
            if obj_id not in object_list:
                object_list.append(obj_id)
                new_object = (obj_id, params)
                new_objects.append(new_object)

    return new_objects

def fetch_NEOCP_observations(obj_id_or_page):
    '''Query the MPC's showobs service with the specified <obj_id_or_page>. If
    the type of <obj_id_or_page> is not a BeautifulSoup object, it will do a
    fetch of the page of the page from the MPC first. Then the passed or
    downloaded page is turned into a list of unicode strings with blank lines
    removed, which is returned. In the case of the object not existing or having
    being removed from the NEOCP,  None is returned.'''

    if type(obj_id_or_page) != BeautifulSoup:
        obj_id = obj_id_or_page
        NEOCP_obs_url = 'http://cgi.minorplanetcenter.net/cgi-bin/showobsorbs.cgi?Obj='+obj_id+'&obs=y'
        neocp_obs_page = fetchpage_and_make_soup(NEOCP_obs_url)
    else:
        neocp_obs_page = obj_id_or_page


# If the object has left the NEOCP, the HTML will say 'None available at this time.'
# and the length of the list will be 1 (but clean of blank lines first using
# list comprehension)
    obs_page_list = [line for line in neocp_obs_page.text.split('\n') if line.strip() != '']
    obs_lines = None
    if len(obs_page_list) > 1:
        obs_lines = obs_page_list

    return obs_lines

def fetch_mpcobs(asteroid, debug=False):
    '''Performs a search on the MPC Database for <asteroid> and returns the
    resulting observation as a list of text observations.'''

    asteroid = asteroid.strip().replace(' ', '+')
    query_url = 'http://www.minorplanetcenter.net/db_search/show_object?object_id=' + asteroid

    page = fetchpage_and_make_soup(query_url)
    if page == None:
        return None

    if debug: print page
# Find all the '<a foo' tags in the page. This will contain the links we need,
# plus other junk
    refs = page.findAll('a')

# Use a list comprehension to find the 'tmp/<asteroid>.dat' link in among all
# the other links. Turn any pluses (which were spaces) into underscores.
    link = [x.get('href') for x in refs if 'tmp/'+asteroid.replace('+', '_') in x.get('href')]

    if len(link) == 1:
# Replace the '..' part with proper URL

        astfile_link = link[0].replace('../', 'http://www.minorplanetcenter.net/')
        obs_page = fetchpage_and_make_soup(astfile_link)

        if obs_page != None:
            obs_page = obs_page.text.split('\n')
        return obs_page

    return None

def translate_catalog_code(code_or_name):
    '''Mapping between the single character in column 72 of MPC records
    and the astrometric reference catalog used.
    Documentation at: http://www.minorplanetcenter.net/iau/info/CatalogueCodes.html'''

    catalog_codes = {
                  "a" : "USNO-A1",
                  "b" : "USNO-SA1",
                  "c" : "USNO-A2",
                  "d" : "USNO-SA2",
                  "e" : "UCAC-1",
                  "f" : "Tycho-1",
                  "g" : "Tycho-2",
                  "h" : "GSC-1.0",
                  "i" : "GSC-1.1",
                  "j" : "GSC-1.2",
                  "k" : "GSC-2.2",
                  "l" : "ACT",
                  "m" : "GSC-ACT",
                  "n" : "TRC",
                  "o" : "USNO-B1",
                  "p" : "PPM",
                  "q" : "UCAC-4",
                  "r" : "UCAC-2",
                  "s" : "USNO-B2",
                  "t" : "PPMXL",
                  "u" : "UCAC-3",
                  "v" : "NOMAD",
                  "w" : "CMC-14",
                  "x" : "HIP-2",
                  "z" : "GSC-1.x",
                  "A" : "AC",
                  "B" : "SAO 1984",
                  "C" : "SAO",
                  "D" : "AGK 3",
                  "E" : "FK4",
                  "F" : "ACRS",
                  "G" : "Lick Gaspra Catalogue",
                  "H" : "Ida93 Catalogue",
                  "I" : "Perth 70",
                  "J" : "COSMOS/UKST Southern Sky Catalogue",
                  "K" : "Yale",
                  "L" : "2MASS",
                  "M" : "GSC-2.3",
                  "N" : "SDSS-DR7",
                  "O" : "SST-RC1",
                  "P" : "MPOSC3",
                  "Q" : "CMC-15",
                  "R" : "SST-RC4",
                  "S" : "URAT-1",
                  "T" : "URAT-2",
                  "U" : "GAIA-DR1",
                  "V" : "GAIA-DR2",
                  }
    catalog_or_code = ''
    if len(code_or_name) == 1:
        catalog_or_code = catalog_codes.get(code_or_name, '')
    else:
        for code, catalog in catalog_codes.iteritems():
            if code_or_name == catalog:
                catalog_or_code = code

    return catalog_or_code

def parse_mpcobs(line):
    '''Parse a MPC format 80 column observation record line, returning a
    dictionary of values or an empty dictionary if it couldn't be parsed

    Be ware of potential confusion between obs_type of 'S' and 's'. This
    enforced by MPC, see
    http://www.minorplanetcenter.net/iau/info/SatelliteObs.html
    '''

    params = {}
    line = line.rstrip()
    if len(line) != 80 or len(line.strip()) == 0:
        msg = "Bad line %d %d" % (len(line), len(line.strip()))
        logger.debug(msg)
        return params
    number = str(line[0:5])
    prov_or_temp = str(line[5:12])

    if len(number.strip()) != 0 and len(prov_or_temp.strip()) != 0:
        # Number and provisional/temp. desigination
        body = number
    elif len(number.strip()) == 0 or len(prov_or_temp.strip()) != 0:
        # No number but provisional/temp. desigination
        body = prov_or_temp
    else:
        body = number

    obs_type = str(line[14])
    flag_char = str(line[13])

    # Try and convert the condition/ program code into a integer. If it succeeds,
    # then it is a program code and we don't care about it. Otherwise, it's an
    # observation condition code and we do want its value.
    try:
        flag = int(flag_char)
        flag = ' '
    except ValueError:
        flag = flag_char
    filter = str(line[70])
    try:
        obs_mag  = float(line[65:70])
    except ValueError:
        obs_mag = None

    if obs_type == 'C' or obs_type == 'S' or obs_type == 'A':
        # Regular CCD observations, first line of satellite observations or
        # observations that have been rotated from B1950 to J2000 ('A')
#        print "Date=",line[15:32]
        params = {  'body'     : body,
                    'flags'    : flag,
                    'obs_type' : obs_type,
                    'obs_date' : parse_neocp_decimal_date(line[15:32].strip()),
                    'obs_mag'  : obs_mag,
                    'filter'   : filter,
                    'astrometric_catalog' : translate_catalog_code(line[71]),
                    'site_code' : str(line[-3:])
                 }
        ptr = 1
        ra_dec_string = line[32:56]
#        print "RA/Dec=", ra_dec_string
        ptr, ra_radians, status = S.sla_dafin(ra_dec_string, ptr)
        params['obs_ra'] = degrees(ra_radians) * 15.0
        ptr, dec_radians, status = S.sla_dafin(ra_dec_string, ptr)
        params['obs_dec'] = degrees(dec_radians)
    elif obs_type.upper() == 'R':
        # Radar observations, skip
        logger.debug("Found radar observation, skipping")
    elif obs_type == 's':
        # Second line of satellite-based observation, stuff whole line into
        # 'extrainfo' and parse what we can (so we can identify the corresponding
        # 'S' line/frame)
        params = {  'body'     : body,
                    'obs_type' : obs_type,
                    'obs_date' : parse_neocp_decimal_date(line[15:32].strip()),
                    'extrainfo' : line,
                    'site_code' : str(line[-3:])
                 }
    return params

def clean_element(element):
    '''Cleans an element (passed) by converting to ascii and removing any units'''
    key = element[0].encode('ascii', 'ignore')
    value = None
    if len(element) == 2:
        value = element[1].encode('ascii', 'ignore')
    # Match a open parenthesis followed by 0 or more non-whitespace followed by
    # a close parenthesis and replace it with a blank string
    key = sub(r' \(\S*\)','', key)

    return (key, value)

def fetch_mpcdb_page(asteroid, dbg=False):
    '''Performs a search on the MPC Database for <asteroid> and returns a
    BeautifulSoup object of the page (for future use by parse_mpcorbit())'''

    #Strip off any leading or trailing space and replace internal space with a
    # plus sign
    if dbg: print "Asteroid before=", asteroid
    asteroid = asteroid.strip().replace(' ', '+')
    if dbg: print "Asteroid  after=", asteroid
    query_url = 'http://www.minorplanetcenter.net/db_search/show_object?object_id=' + asteroid

    page = fetchpage_and_make_soup(query_url)
    if page == None:
        return None

#    if dbg: print page
    return page

def parse_mpcorbit(page, dbg=False):

    data = []
    # Find the table of elements and then the subtables within it
    elements_table = page.find('table', {'class' : 'nb'})
    if elements_table == None:
        if dbg: logger.debug("No element tables found")
        return {}
    data_tables = elements_table.find_all('table')
    for table in data_tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [elem.text.strip() for elem in cols]
            data.append([elem for elem in cols if elem])

    elements = dict(clean_element(elem) for elem in data)

    name_element = page.find('h3')
    if name_element != None:
        elements['obj_id'] = name_element.text.strip()

    return elements

class PackedError(Exception):
    '''Raised when an invalid pack code is found'''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

def validate_packcode(packcode):
    '''Method to validate that <packcode> is a valid MPC packed designation.
    Format is as described at:
    http://www.minorplanetcenter.org/iau/info/PackedDes.html'''

    valid_cent_codes = {'I' : 18, 'J' : 19, 'K' : 20}
    valid_half_months = 'ABCDEFGHJKLMNOPQRSTUVWXY'

    if len(packcode) != 7:
        raise PackedError("Invalid packcode length")
    if packcode[0] not in valid_cent_codes:
        raise PackedError("Invalid century code")
    if packcode[1:3].isdigit() == False:
        raise PackedError("Invalid year")
    if packcode[3] not in valid_half_months:
        raise PackedError("Invalid half-month character")
    if not packcode[6].isupper() or not packcode[6].isalpha():
        raise PackedError("Invalid half-month order character")
    return True

def packed_to_normal(packcode):
    '''Converts MPC packed provisional designations e.g. K10V01F to unpacked
    normal desigination i.e. 2010 VF1'''

# Convert initial letter to century
    cent_codes = {'I' : 18, 'J' : 19, 'K' : 20}

    if not validate_packcode(packcode):
        raise PackedError("Invalid packcode %s" % packcode)
        return None
    else:
        mpc_cent = cent_codes[packcode[0]]

# Convert next 2 digits to year
    mpc_year = packcode[1:3]
    no_in_halfmonth = packcode[3] + packcode[6]
# Turn the character of the cycle count, which runs 0--9, A--Z, a--z into a
# consecutive integer by converting to ASCII code and skipping the non-alphanumerics
    cycle = ord(packcode[4])
    if cycle >= ord('a'):
        cycle = cycle - 61
    elif cycle >= ord('A') and cycle < ord('Z'):
        cycle = cycle - 55
    else:
        cycle = cycle - ord('0')
    digit = int(packcode[5])
    count = cycle * 10 + digit
# No digits on the end of the unpacked designation if it's the first loop through
    if cycle == 0 and digit == 0:
        count = ''

# Assemble unpacked code
    normal_code = str(mpc_cent) + mpc_year + ' ' + no_in_halfmonth + str(count)

    return normal_code

def parse_goldstone_chunks(chunks, dbg=False):
    '''Tries to parse the Goldstone target line (a split()'ed list of fields)
    to extract the object id. Could also parse the date of radar observation
    and whether astrometry or photometry is needed'''

    if dbg: print chunks
    # Try to convert the 2nd field (counting from 0...) to an integer and if
    # that suceeds, check it's greater than 31. If yes, it's an asteroid number
    # (we assume asteroid #1-31 will never be observed with radar..)
    object_id = ''

    try:
        astnum = int(chunks[2])
    except ValueError:
        if dbg: print "Could not convert", chunks[2], "to asteroid number. Will try different method."
        astnum = -1

    if astnum > 31:
        object_id = str(astnum)
        # Check if the next 2 characters are uppercase in which it's a
        # designation, not a name
        if chunks[3][0].isupper() and chunks[3][1].isupper():
            if dbg: print "In case 1"
            object_id = object_id + ' ' + str(chunks[3])
    else:
        if dbg: print "Specific date of observation"
        # We got an error or a too small number (day of the month)
        if astnum <= 31 and chunks[3].isdigit() and chunks[4].isdigit() and chunks[2][-1].isdigit():
            # We have something of the form [20, 2014, YB35; only need first
            # bit
            if dbg: print "In case 2a"
            object_id = str(chunks[3])
        elif astnum <= 31 and chunks[3].isdigit() and chunks[4].isdigit() and chunks[2][-1].isalnum():
            # We have something that straddles months
            if dbg: print "In case 2b"
            if chunks[5].isdigit() or chunks[5][0:2].isupper() == False:
                # Of the form '2017 May 29-Jun 02 418094 2007 WV4' or number and
                # name e.g.  '2017 May 29-Jun 02 6063 Jason'
                object_id = str(chunks[4])
            else:
                # Of the form '2017 May 29-Jun 02 2017 CS'
                object_id = str(chunks[4]) + ' ' + chunks[5]
        elif astnum <= 31 and (chunks[3].isdigit() or chunks[3][0:2] == 'P/' \
        or chunks[3][0:2] == 'C/') and chunks[4].isalnum():
            # We have a date range e.g. '2016 Mar 17-23'
            # Test if the first 2 characters of chunks[4] are uppercase
            # If yes then we have a desigination e.g. [2014] 'UR' or [2015] 'FW117'
            # If no, then we have a name e.g. [1566] 'Icarus'
            # Hopefully some at Goldstone won't shout the name of the object
            # e.g. '(99942) APOPHIS'! or we're hosed...
            if chunks[4][0:2].isupper():
                if dbg: print "In case 3a"
                object_id = str(chunks[3] + ' ' + chunks[4])
            else:
                if dbg: print "In case 3b"
                object_id = str(chunks[3])
        elif chunks[3].isdigit() and chunks[4].isalpha():
            if dbg: print "In case 4"
            object_id = str(chunks[3] + ' ' + chunks[4])

    return object_id

def fetch_goldstone_targets(dbg=False):
    '''Fetches and parses the Goldstone list of radar targets, returning a list
    of object id's for the current year'''

    goldstone_url = 'http://echo.jpl.nasa.gov/asteroids/goldstone_asteroid_schedule.html'

    page = fetchpage_and_make_soup(goldstone_url)

    if page == None:
        return None

    radar_objects = []
    in_objects = False
    current_year = datetime.now().year
    last_year_seen = current_year
    # The Goldstone target page is just a ...page... of text... with no tags
    # or table or anything much to search for. Do the best we can and look for
    # the "table" header and then start reading and parsing lines until the
    # first 5 characters no longer match our current year
    for line in page.text.split("\n"):
        if len(line.strip()) == 0:
            continue
        if 'Target      Astrometry?  Observations?' in line:
            logger.debug("Found start of table")
            in_objects = True
        else:
            if in_objects == True:
                # Look for malformed comma-separated dates in the first part of
                # the line and convert the first occurence to hyphens before
                # splitting.
                if ', ' in line[0:40]:
                    line = line.replace(', ', '-', 1)
                # Look for malformed space and hyphen-separated dates in the
                # first part of the line and convert the first occurence to
                # hyphens before splitting.
                if '- ' in line[0:40] or ' -' in line[0:40]:
                    line = line.replace('- ', '-', 1).replace(' -', '-', 1)
                chunks = line.lstrip().split()
                #if dbg: print line
                # Check if the start of the stripped line is no longer the
                # current year.
                # <sigh> we also need to check if the year goes backwards due
                # to typos...
                try:
                    year = int(chunks[0])
                except ValueError:
                    year = 9999

                if year < last_year_seen:
                    logger.info("WARN: Error in calendar seen (year=%s). Correcting" % year)
                    year = current_year
                    chunks[0] = year
                if year > last_year_seen:
                    in_objects = False
                    logger.debug("Done with objects")
                else:
                    obj_id = parse_goldstone_chunks(chunks, dbg)
                    if obj_id != '':
                        radar_objects.append(obj_id)
                last_year_seen = year
    return  radar_objects

def fetch_arecibo_page():
    '''Fetches the Arecibo list of radar targets, returning a list
    of object id's for the current year'''

    arecibo_url = 'http://www.naic.edu/~pradar/'

    page = fetchpage_and_make_soup(arecibo_url)

    return page

def fetch_arecibo_targets(page=None):
    '''Parses the Arecibo webpage for upcoming radar targets and returns a list
    of these targets back.
    Takes either a BeautifulSoup page version of the Arecibo target page (from
    a call to fetch_arecibo_page() - to allow  standalone testing) or  calls
    this routine and then parses the resulting page.
    '''

    if type(page) != BeautifulSoup:
        page = fetch_arecibo_page()

    targets = []

    if type(page) == BeautifulSoup:
        # Find the tables, we want the second one
        tables = page.find_all('table')
        if len(tables) != 2 and len(tables) != 3 :
            logger.warn("Unexpected number of tables found in Arecibo page (Found %d)" % len(tables))
        else:
            targets_table = tables[-1]
            rows = targets_table.find_all('tr')
            if len(rows) > 1:
                for row in rows[1:]:
                    items = row.find_all('td')
                    target_object = items[0].text
                    target_object = target_object.strip()
                    # See if it is the form "(12345) 2008 FOO". If so, extract
                    # just the asteroid number
                    if '(' in target_object and ')' in target_object:
                        # See if we have parentheses around the number or around the
                        # temporary desigination.
                        # If the first character in the string is a '(' we have the first
                        # case and should split on the closing ')' and take the 0th chunk
                        # If the first char is not a '(', then we have parentheses around
                        # the temporary desigination and we should split on the '(', take
                        # the 0th chunk and strip whitespace
                        split_char = ')'
                        if target_object[0] != '(':
                            split_char = '('
                        target_object = target_object.split(split_char)[0].replace('(','')
                        target_object = target_object.strip()
                    else:
                        # No parentheses, either just a number or a number and name
                        chunks = target_object.split(' ')
                        if len(chunks) >= 2:
                            if chunks[1].replace('-', '').isalpha() and len(chunks[1]) != 2:
                                target_object = chunks[0]
                            else:
                                target_object = chunks[0] + " " + chunks[1]
                        else:
                            logger.warn("Unable to parse Arecibo target %s" % target_object)
                            target_object = None
                    if target_object:
                        targets.append(target_object)
            else:
                logger.warn("No targets found in Arecibo page")
    return targets

def imap_login(username, password, server='imap.gmail.com'):
    '''Logs into the specified IMAP [server] (Google's gmail is assumed if not
    specified) with the provide username and password.

    An imaplib.IMAP4_SSL connection instance is returned or None if the
    login failed'''

    try:
        mailbox = imaplib.IMAP4_SSL(server)
    except error:
        return None

    try:
        mailbox.login(username, password)
    except imaplib.IMAP4_SSL.error:
        logger.error("Login to %s with username=%s failed" % (server, username))
        mailbox = None

    return mailbox

def fetch_NASA_targets(mailbox, folder='NASA-ARM', date_cutoff=1):
    '''Search through the specified folder/label (defaults to "NASA-ARM" if not
    specified) within the passed IMAP mailbox <mailbox> for emails to the
    small bodies list and returns a list of targets. Emails that are more than
    [date_cutoff] days old (default is 1 day) will not be looked at.'''

    list_address = '"small-bodies-observations@lists.nasa.gov"'
    list_authors  = [ '"paul.a.abell@nasa.gov"',
                      '"paul.w.chodas@jpl.nasa.gov"',
                      '"brent.w.barbee@nasa.gov"']
    list_prefix = '[' + list_address.replace('"','').split('@')[0] +']'
    list_suffix = 'Observations Requested'

    NASA_targets = []

    status, data = mailbox.select(folder)
    if status == "OK":
        msgnums = ['']
        for author in list_authors:
        # Look for messages to the mailing list but without specifying a charset
            status, msgs = mailbox.search(None, 'TO', list_address,\
                                                'FROM', author)

            if status == 'OK' and len(msgs) > 0 and msgs[0] != '':
                msgnums = [msgnums[0] + ' '+ msgs[0],]
        # Messages numbers come back in a space-separated string inside a
        # 1-element list in msgnums
        if status == "OK" and len(msgnums) >0 and msgnums[0] != '':

            for num in msgnums[0].split():
                try:
                    status, data = mailbox.fetch(num, '(RFC822)')
                    if status != 'OK' or len(data) == 0 and msgnums[0] != None:
                        logger.error("ERROR getting message %s", num)
                    else:
                        # Convert message and see if it has the right things
                        msg = email.message_from_string(data[0][1])
                        # Strip off any "Fwd: " parts
                        msg_subject = msg['Subject'].replace('Fwd: ', '')
                        date_tuple = email.utils.parsedate_tz(msg['Date'])
                        msg_utc_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        time_diff = datetime.utcnow() - msg_utc_date
                        # See if the subject has the right prefix and suffix and is
                        # within a day of 'now'
                        if list_prefix in msg_subject and list_suffix in msg_subject and \
                            time_diff <= timedelta(days=date_cutoff):

                            # Define a slice for the fields of the message we will want for
                            # the target.
                            end_slice = 3
                            if list_suffix.split()[0] in msg_subject.split():
                                end_slice = msg_subject.split().index(list_suffix.split()[0])

                            TARGET_DESIGNATION = slice(1, end_slice)

                            target = ' '.join(msg_subject.split()[TARGET_DESIGNATION]).strip()
                            target = target.replace('-', '')
                            target = target.strip()
                            if ',' in target:
                                targets = target.split(',')
                                for target in targets:
                                    target = target.strip()
                                    if target not in NASA_targets:
                                        NASA_targets.append(target)
                            else:
                                if target not in NASA_targets:
                                    NASA_targets.append(target)
                except:
                    logger.error("ERROR getting message %s", num)
                    return NASA_targets
        else:
            logger.warn("No mailing list messages found")
            return []
    else:
        logger.error("Could not open folder/label %s on %s" % (folder, mailbox.host))
        return []
    return NASA_targets

def get_site_status(site_code):
    '''Queries the Valhalla telescope states end point to determine if the
    passed <site_code> is available for scheduling.
    Returns True if the site/telescope is available for scheduling and
    assumed True if the status can't be determined. Otherwise if the
    last event for the telescope can be found and it does not show
    'AVAILABLE', then the good_to_schedule status is set to False.'''

    good_to_schedule = True
    reason = ''

# Get dictionary mapping LCO code (site-enclosure-telescope) to MPC site code
# and reverse it
    site_codes = return_LCOGT_site_codes_mapping()
    lco_codes = {mpc_code:lco_code.lower().replace('-', '.') for lco_code,mpc_code in site_codes.iteritems()}

    response = get_telescope_states()

    if len(response) > 0:
        key = lco_codes.get(site_code, None)
        status = response.get(key, None)
        if status:
            current_status = status[-1]
            logger.debug("State for %s:\n%s" % (site_code, current_status))
            good_to_schedule = 'AVAILABLE' in current_status.get('event_type', '')
            reason = current_status.get('event_reason', '')
        else:
            good_to_schedule = False
            reason = 'Not available for scheduling'

    return (good_to_schedule, reason)

def make_location(params):
    location = {
        'site'            : params['site'].lower(),
        'telescope_class' : params['pondtelescope'][0:3]
    }
    if params['site_code'] == 'W85':
        location['telescope'] = '1m0a'
        location['observatory'] = 'doma'
    return location

def make_target(params):
    '''Make a target dictionary for the request. RA and Dec need to be
    decimal degrees'''

    ra_degs = math.degrees(params['ra_rad'])
    dec_degs = math.degrees(params['dec_rad'])
    target = {
               'name' : params['source_id'],
               'ra'   : ra_degs,
               'dec'  : dec_degs
             }
    return target

def make_moving_target(elements):
    '''Make a target dictionary for the request from an element set'''

#    print elements
    # Generate initial dictionary of things in common
    target = {
                  'name'                : elements['current_name'],
                  'type'                : 'NON_SIDEREAL',
                  'scheme'              : elements['elements_type'],
                  # Moving object param
                  'epochofel'         : elements['epochofel_mjd'],
                  'orbinc'            : elements['orbinc'],
                  'longascnode'       : elements['longascnode'],
                  'argofperih'        : elements['argofperih'],
                  'eccentricity'      : elements['eccentricity'],
            }

    if elements['elements_type'].upper() == 'MPC_COMET':
        target['epochofperih'] = elements['epochofperih_mjd']
        target['perihdist'] = elements['perihdist']
    else:
        target['meandist']  = elements['meandist']
        target['meananom']  = elements['meananom']

    return target

def make_window(params):
    '''Make a window. This is simply set to the start and end time from
    params (i.e. the picked time with the best score plus the block length),
    formatted into a string.
    Hopefully this will prevent rescheduling at a different time as the
    co-ords will be wrong in that case...'''
    window = {
              'start' : params['start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
              'end'   : params['end_time'].strftime('%Y-%m-%dT%H:%M:%S'),
             }

    return window

def make_molecule(params):
    molecule = {
                'type' : params['exp_type'],
                'exposure_count'  : params['exp_count'],
                'exposure_time' : params['exp_time'],
                'bin_x'       : params['binning'],
                'bin_y'       : params['binning'],
                'instrument_name'   : params['instrument'],
                'filter'      : params['filter'],
                'ag_mode'     : 'OPTIONAL', # ON, OFF, or OPTIONAL. Must be uppercase now...
                'ag_name'     : ''

    }
    return molecule

def make_constraints(params):
    constraints = {
#                       'max_airmass' : 2.0,    # 30 deg altitude (The maximum airmass you are willing to accept)
                       'max_airmass' : 1.74,   # 35 deg altitude (The maximum airmass you are willing to accept)
#                       'max_airmass' : 1.55,   # 40 deg altitude (The maximum airmass you are willing to accept)
#                       'max_airmass' : 2.37,   # 25 deg altitude (The maximum airmass you are willing to accept)
                       'min_lunar_distance': 30
                    }
    return constraints

def configure_defaults(params):


    site_list = { 'V37' : 'ELP',
                  'K92' : 'CPT',
                  'K93' : 'CPT',
                  'Q63' : 'COJ',
                  'W85' : 'LSC',
                  'W86' : 'LSC',
                  'W87' : 'LSC',
                  'W89' : 'LSC', # Code for 0m4a
                  'F65' : 'OGG',
                  'E10' : 'COJ',
                  'Z21' : 'TFN',
                  'T04' : 'OGG',
                  'Q58' : 'COJ', # Code for 0m4a
                  'Q59' : 'COJ'} # Code for 0m4b, not currently in use


    params['pondtelescope'] = '1m0a'
    params['observatory'] = ''
    params['site'] = site_list[params['site_code']]
    params['binning'] = 1
    params['instrument'] = '1M0-SCICAM-SINISTRO'
    params['filter'] = 'w'
    params['exp_type'] = 'EXPOSE'

    if params['site_code'] == 'W86' or params['site_code'] == 'W87':
        # Force to Dome B (W86) as W87 is bad
        params['binning'] = 1
        params['observatory'] = 'domb'
        params['instrument'] = '1M0-SCICAM-SINISTRO'
        if params['site_code'] == 'W87':
            params['site_code'] = 'W86'
    elif params['site_code'] == 'W85':
        params['binning'] = 1
        params['observatory'] = 'doma'
        params['instrument'] = '1M0-SCICAM-SINISTRO'
    elif params['site_code'] == 'F65' or params['site_code'] == 'E10':
        params['instrument'] =  '2M0-SCICAM-SPECTRAL'
        params['binning'] = 2
        params['pondtelescope'] = '2m0a'
        params['filter'] = 'solar'
    elif params['site_code'] == 'Z21' or params['site_code'] == 'W89' or params['site_code'] == 'T04' or params['site_code'] == 'Q58' or params['site_code'] == 'Q59':
        params['instrument'] =  '0M4-SCICAM-SBIG'
        params['pondtelescope'] = '0m4'
        params['filter'] = 'w'
        params['binning'] = 2 # 1 is the Right Answer...

    return params

def make_userrequest(elements, params):

    params = configure_defaults(params)
# Create Location (site, observatory etc)
    location = make_location(params)
    logger.debug("Location=%s" % location)
# Create Target (pointing)
    if len(elements) > 0:
        logger.debug("Making a moving object")
        target = make_moving_target(elements)
    else:
        logger.debug("Making a static object")
        target = make_target(params)
    logger.debug("Target=%s" % target)
# Create Window
    window = make_window(params)
    logger.debug("Window=%s" % window)
# Create Molecule
    molecule = make_molecule(params)

    submitter = ''
    submitter_id = params.get('submitter_id', '')
    if submitter_id != '':
        submitter = '(by %s)' % submitter_id
    note = ('Submitted by NEOexchange {}'.format(submitter))
    note = note.rstrip()

    constraints = make_constraints(params)

    request = {
            "location": location,
            "constraints": constraints,
            "target": target,
            "molecules": [molecule],
            "windows": [window],
            "observation_note": note,
        }

# Add the Request to the outer User Request
# If site is ELP, increase IPP value
    ipp_value = 1.00
    if params['site_code'] == 'V37':
        ipp_value = 1.00

    user_request = {
        "submitter": params['user_id'],
        "requests": [request],
        "group_id": params['group_id'],
        "observation_type": "NORMAL",
        "operator": "SINGLE",
        "ipp_value": ipp_value,
        "proposal": params['proposal_id']
    }

# If the ToO mode is set, change the observation_type
    if params['too_mode'] == True:
        request['observation_type'] = 'TARGET_OF_OPPORTUNITY'

    logger.info("User Request=%s" % user_request)

    return user_request


def submit_block_to_scheduler(elements, params):

    user_request = make_userrequest(elements, params)

# Make an endpoint and submit the thing
    try:
        resp = requests.post(
            settings.PORTAL_REQUEST_API,
            json=user_request,
            headers={'Authorization': 'Token {}'.format(settings.PORTAL_TOKEN)},
            timeout=20.0
         )
    except requests.exceptions.Timeout:
        msg = "Observing portal API timed out"
        logger.error(msg)
        params['error_msg'] = msg
        return False, params

    if resp.status_code not in [200,201]:
        msg = "Parsing error"
        logger.error(msg)
        logger.error(resp.json())
        params['error_msg'] = msg
        return False, params

    response = resp.json()
    tracking_number =  response.get('id', '')

    request_items = response.get('requests', '')

    request_numbers =  [_['id'] for _ in request_items]

    if not tracking_number or not request_numbers:
        msg = "No Tracking/Request number received"
        logger.error(msg)
        params['error_msg'] = msg
        return False, params
    request_number = request_numbers[0]
    logger.info("Tracking, Req number=%s, %s" % (tracking_number,request_number))

    return tracking_number, params
