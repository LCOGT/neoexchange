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
import urllib2, os
from bs4 import BeautifulSoup
from datetime import datetime
from re import sub
import logging
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
        if dbg: print items, len(items)
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
#                print "Items=",items
                items[0] = items[0].replace(' (', '(')
                subitems = items[0].lstrip().split()
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
            print "Unknown number of fields"
# Append to list
        if crossmatch != ['', '', '', '']:
            crossids.append(crossmatch)

    return crossids

def fetch_NEOCP(dbg=False):

    '''Fetches the NEO Confirmation Page and extracts a list of objects, which
    is returned.'''

    NEOCP_url = 'http://www.minorplanetcenter.net/iau/NEO/ToConfirm.html'

    neocp_page = fetchpage_and_make_soup(NEOCP_url)
    if neocp_page == None:
        return None

# Find all the input checkboxes with "obj" in the name
    neocp_objects = neocp_page.findAll('input', attrs={"name" : "obj"})

    new_objects = []
    for row in neocp_objects:
        new_objects.append(row['value'])

    return new_objects

def fetch_NEOCP_observations(obj_id, savedir, delete=False, dbg=False):
    '''Query the MPC's showobs service with the specified <obj_id> and
    it will write the observations found into <savedir>/<obj_id>.dat
    The file will not be overwritten if it exists unless 'delete=True'
    Returns the number of lines written or None if:
      (a) the object was no longer on the NEOCP or
      (b) the file already exists and [delete] is not True'''

    NEOCP_obs_url = 'http://scully.cfa.harvard.edu/cgi-bin/showobsorbs.cgi?Obj='+obj_id+'&obs=y'

    neocp_obs_page = fetchpage_and_make_soup(NEOCP_obs_url)

    obs_page_list = neocp_obs_page.text.split('\n')

# If the object has left the NEOCP, the HTML will say 'None available at this time.'
# and the length of the list will be 1
    lines_written = None
    if len(obs_page_list) > 1:
    # Create save directory if it doesn't exist
        if not os.path.isdir(savedir): os.mkdir(savedir)

        print "Will save files in", savedir
        neocand_filename = os.path.join(savedir, obj_id + '.dat')
        if delete: os.remove(neocand_filename)
        if os.path.isfile(neocand_filename) == False:
            neo_cand_fh = open(neocand_filename, 'w')
            for line in obs_page_list:
                obs_page_line = "%80s" % (line)
                print >> neo_cand_fh, obs_page_line
            neo_cand_fh.close()
            lines_written = len(obs_page_list)
            print "Wrote", lines_written, "MPC lines to", neocand_filename
        else:
            print "File", neocand_filename, "already exists, not overwriting."

    else:
        print "Object", obj_id, "no longer exists on the NEOCP."

    return lines_written

def fetch_NEOCP_orbit(obj_id, savedir, delete=False, dbg=False):
    '''Query the MPC's showobs service with the specified <obj_id> and
    it will write the orbit found into <savedir>/<obj_id>.neocp
    Only the first of the potential orbits (the 'NEOCPNomin' nominal orbit) is
    returned if there are multiple orbits found.
    The file will not be overwritten if it exists unless 'delete=True'
    Returns the number of lines written or None if:
      (a) the object was no longer on the NEOCP or
      (b) the file already exists and [delete] is not True'''

    NEOCP_orb_url = 'http://scully.cfa.harvard.edu/cgi-bin/showobsorbs.cgi?Obj='+obj_id+'&orb=y'

    neocp_obs_page = fetchpage_and_make_soup(NEOCP_orb_url)

    obs_page_list = neocp_obs_page.text.split('\n')

# If the object has left the NEOCP, the HTML will say 'None available at this time.'
# and the length of the list will be 1
    orbit_lines_written = None
    if len(obs_page_list) > 1:
    # Create save directory if it doesn't exist
        if not os.path.isdir(savedir): os.mkdir(savedir)

        if dbg: print "Will save files in", savedir
        neocand_filename = os.path.join(savedir, obj_id + '.neocp')
        if delete and os.path.isfile(neocand_filename): os.remove(neocand_filename)
        orbit_lines_written = 0
        if os.path.isfile(neocand_filename) == False:
            for line in obs_page_list:
                if 'NEOCPNomin' in line:
                    neo_orbit_fh = open(neocand_filename, 'w')
#                obs_page_line = "%80s" % ( line )
                    print >> neo_orbit_fh, line
                    neo_orbit_fh.close()
                    orbit_lines_written = orbit_lines_written + 1
            if dbg: print "Wrote", orbit_lines_written, "orbit lines to", neocand_filename
        else:
            if dbg: print "File", neocand_filename, "already exists, not overwriting."

    else:
        if dbg: print "Object", obj_id, "no longer exists on the NEOCP."

    return orbit_lines_written

def fetch_mpcobs(asteroid, file_to_save, debug=False):
    '''Performs a search on the MPC Database for <asteroid> and saves the
    resulting observations into <file_to_save>.'''

    query_url = 'http://www.minorplanetcenter.net/db_search/show_object?object_id=' + asteroid

    page = fetchpage_and_make_soup(query_url)
    if page == None:
        return None

    if debug: print page
# Find all the '<a foo' tags in the page. This will contain the links we need,
# plus other junk
    refs = page.findAll('a')

# Use a list comprehension to find the 'tmp/<asteroid>.dat' link in among all
# the other links
    link = [x.get('href') for x in refs if 'tmp/'+asteroid in x.get('href')]

    if len(link) == 1:
# Replace the '..' part with proper URL

        astfile_link = link[0].replace('../', 'http://www.minorplanetcenter.net/')
        download_file(astfile_link, file_to_save)

        return file_to_save

    return None

def clean_element(element):
    'Cleans an element (passed) by converting to ascii and removing any units'''
    key = element[0].encode('ascii', 'ignore')
    value = element[1].encode('ascii', 'ignore')
    # Match a open parenthesis followed by 0 or more non-whitespace followed by
    # a close parenthesis and replace it with a blank string
    key = sub(r' \(\S*\)','', key)

    return (key, value)

def fetch_mpcorbit(asteroid, dbg=False):
    '''Performs a search on the MPC Database for <asteroid> and returns a list
    of the resulting orbital elements.'''

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
    normal desigination i.e. 2010VF1'''

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
    normal_code = str(mpc_cent) + mpc_year + no_in_halfmonth + str(count)

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
        if astnum <= 31 and chunks[3].isdigit() and chunks[4].isdigit():
            # We have something of the form [20, 2014, YB35; only need first
            # bit
            if dbg: print "In case 2"
            object_id = str(chunks[3])
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
