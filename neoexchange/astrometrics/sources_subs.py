'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

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

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from re import sub
from reqdb.client import SchedulerClient
from reqdb.requests import Request, UserRequest
from astrometrics.time_subs import parse_neocp_decimal_date, jd_utc2datetime
from math import degrees
import slalib as S
import logging
import urllib2, os
from urlparse import urljoin


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
# Is of the form "<foo> does not exist" or "<foo> was not confirmed"
        chunks = items[0].split()
        none_id = ''
        if chunks[1].find('does') >= 0:
            none_id = 'doesnotexist'
        elif chunks[1].find('was') >= 0:
            none_id = 'wasnotconfirmed'

        crossmatch = [chunks[0], none_id, '', ' '.join(chunks[-3:])]
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
                  "L" : "2MASS",
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
                  "N" : "SDSS-DR7",
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
    dictionary of values or an empty dictionary if it couldn't be parsed'''

    params = {}
    line = line.rstrip()
    if len(line) != 80 or len(line.strip()) == 0:
        msg = "Bad line %d %d" % (len(line), len(line.strip()))
        logger.debug(msg)
        return params
    number = str(line[0:5])
    prov_or_temp = str(line[5:12])

    if len(number.strip()) == 0 or len(prov_or_temp.strip()) != 0:
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

    if obs_type == 'C':
        # Regular CCD observations
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
    elif obs_type == 'S':
        # Satellite -based observation, do something with it
        logger.warn("Found satellite observation, skipping (for now)")
    return params

def clean_element(element):
    '''Cleans an element (passed) by converting to ascii and removing any units'''
    key = element[0].encode('ascii', 'ignore')
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
        if dbg: "No element tables found"
        return None
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
            object_id = str(chunks[4])
        elif astnum <= 31 and chunks[3].isdigit() and chunks[4].isalnum():
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

def make_location(params):
    location = {
        'telescope_class' : params['pondtelescope'][0:3],
        'site'        : params['site'].lower(),
        'observatory' : params['observatory'],
        'telescope'   : '',
    }

# Check if the 'pondtelescope' is length 4 (1m0a) rather than length 3, and if
# so, update the null string set above with a proper telescope
    if len(params['pondtelescope']) == 4:
        location['telescope'] = params['pondtelescope']

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

    print elements
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
        target['epochofperih'] = elements['epochofperih']
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
                'exposure_count'  : params['exp_count'],
                'exposure_time' : params['exp_time'],
                'bin_x'       : params['binning'],
                'bin_y'       : params['binning'],
                'instrument_name'   : params['instrument'],
                'filter'      : params['filter'],
                'ag_mode'     : 'Optional', # 0=On, 1=Off, 2=Optional.  Default is 2.
                'ag_name'     : ''

    }
    return molecule

def make_proposal(params):
    '''Construct needed proposal info'''

    proposal = {
                 'proposal_id'   : params['proposal_id'],
                 'user_id'       : params['user_id'],
                 'tag_id'        : params['tag_id'],
                 'priority'      : params['priority'],
               }
    return proposal

def make_constraints(params):
    constraints = {
#                      'max_airmass' : 2.0,    # 30 deg altitude (The maximum airmass you are willing to accept)
                       'max_airmass' : 1.74,   # 35 deg altitude (The maximum airmass you are willing to accept)
#                      'max_airmass' : 1.55,   # 40 deg altitude (The maximum airmass you are willing to accept)
#                      'max_airmass' : 2.37,    # 25 deg altitude (The maximum airmass you are willing to accept)
                    }
    return constraints

def configure_defaults(params):

    site_list = { 'V37' : 'ELP' , 'K92' : 'CPT', 'Q63' : 'COJ', 'W85' : 'LSC', 'W86' : 'LSC', 'F65' : 'OGG', 'E10' : 'COJ' }
    params['pondtelescope'] = '1m0'
    params['observatory'] = ''
    params['site'] = site_list[params['site_code']]
    params['binning'] = 2
    params['instrument'] = '1M0-SCICAM-SBIG'
    params['filter'] = 'w'

    if params['site_code'] == 'W86' or params['site_code'] == 'W87':
        params['binning'] = 1
        params['observatory'] = 'domb'
        params['instrument'] = '1M0-SCICAM-SINISTRO'
    elif params['site_code'] == 'V37':
        params['binning'] = 1
        params['instrument'] = '1M0-SCICAM-SINISTRO'
    elif params['site_code'] == 'F65' or params['site_code'] == 'E10':
        params['instrument'] =  '2M0-SCICAM-SPECTRAL'
        params['pondtelescope'] = '2m0'
        params['filter'] = 'solar'

    return params

def submit_block_to_scheduler(elements, params):
    request = Request()

    params = configure_defaults(params)
# Create Location (site, observatory etc) and add to Request
    location = make_location(params)
    logger.debug("Location=%s" % location)
    request.set_location(location)
# Create Target (pointing) and add to Request
    if len(elements) > 0:
        logger.debug("Making a moving object")
        target = make_moving_target(elements)
    else:
        logger.debug("Making a static object")
        target = make_target(params)
    logger.debug("Target=%s" % target)
    request.set_target(target)
# Create Window and add to Request
    window = make_window(params)
    logger.debug("Window=%s" % window)
    request.add_window(window)
# Create Molecule and add to Request
    molecule = make_molecule(params)
    request.add_molecule(molecule) # add exposure to the request
    request.set_note('Submitted by NEOexchange')
    logger.debug("Request=%s" % request)

    constraints = make_constraints(params)
    request.set_constraints(constraints)

# Add the Request to the outer User Request
    user_request =  UserRequest(group_id=params['group_id'])
    user_request.add_request(request)
    user_request.operator = 'single'
    proposal = make_proposal(params)
    user_request.set_proposal(proposal)

# Make an endpoint and submit the thing
    client = SchedulerClient('http://scheduler1.lco.gtn/requestdb/')
    response_data = client.submit(user_request)
    client.print_submit_response()
    request_numbers =  response_data.get('request_numbers', '')
    tracking_number =  response_data.get('tracking_number', '')
#    request_numbers = (-42,)
    if not tracking_number or not request_numbers:
        logger.error("No Tracking/Request number received")
        return False, params
    request_number = request_numbers[0]
    logger.info("Tracking, Req number=%s, %s" % (tracking_number,request_number))

    return tracking_number, params
