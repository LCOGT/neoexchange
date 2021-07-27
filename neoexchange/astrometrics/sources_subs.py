"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

sources_subs.py -- Code to retrieve asteroid infomation from various sources.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import logging
import os
import urllib.request
import urllib.error
from urllib.parse import urljoin
import imaplib
import email
from re import sub, compile
from math import degrees
from time import sleep
from datetime import date, datetime, timedelta
from socket import error
from random import randint
import requests
import shutil
import tempfile
from contextlib import closing

from bs4 import BeautifulSoup
import astropy.units as u
try:
    import pyslalib.slalib as S
except ModuleNotFoundError:
    pass
from django.conf import settings
from astropy.io import ascii

import astrometrics.site_config as cfg
from astrometrics.time_subs import parse_neocp_decimal_date, jd_utc2datetime, datetime2mjd_utc, mjd_utc2mjd_tt, mjd_utc2datetime
from astrometrics.ephem_subs import build_filter_blocks, MPC_site_code_to_domes, compute_ephem, perturb_elements, LCOGT_site_codes
from core.urlsubs import get_telescope_states

logger = logging.getLogger(__name__)


def download_file(url, file_to_save):
    """Helper routine to download from a URL and save into a file with error trapping"""

    attempts = 0
    while attempts < 3:
        try:
            url_handle = urllib.request.urlopen(url)
            file_handle = open(file_to_save, 'wb')
            for line in url_handle:
                file_handle.write(line)
            url_handle.close()
            file_handle.close()
            print("Downloaded:", file_to_save)
            break
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            attempts += 1
            if hasattr(e, 'code'):
                print("HTTP Error %d: %s, retrying" % (e.code, e.reason))
            else:
                print("HTTP Error: %s" % (e.reason,))


def random_delay(lower_limit=10, upper_limit=20):
    """Waits a random number of integer seconds between [lower_limit; default 10]
    and [upper_limit; default 20]. Useful for slowing down web requests to prevent
    overloading remote systems. The executed delay is returned."""

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
    """Fetches the specified URL from <url> and parses it using BeautifulSoup.
    If [fakeagent] is set to True, we will pretend to be a Firefox browser on
    Linux rather than as Python-urllib (in case of anti-machine filtering).
    If [parser] is specified, try and use that BeautifulSoup parser (which
    needs to be installed). Defaults to "html.parser" if not specified; may need
    to use "html5lib" to properly parse malformed MPC pages.

    Returns the page as a BeautifulSoup object if all was OK or None if the
    page retrieval failed."""

    req_headers = {}
    if fakeagent is True:
        req_headers = {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0",
                      }
    req_page = urllib.request.Request(url, headers=req_headers)
    opener = urllib.request.build_opener()  # create an opener object
    try:
        response = opener.open(req_page, timeout=20)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        if hasattr(e, 'code'):
            logger.warning("Page retrieval failed with HTTP Error %d: %s, retrying" % (e.code, e.reason))
        else:
            logger.warning("Page retrieval failed with HTTP Error: %s" % (e.reason,))
        return None
    except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError) as sock_e:
        logger.warning("Page retrieval failed with socket Error %d: %s" % (sock_e.errno, sock_e.strerror))
        return None

    # Suck the HTML down
    neo_page = response.read()

# Parse into beautiful soup
    page = BeautifulSoup(neo_page, parser)

    return page


def parse_previous_NEOCP_id(items, dbg=False):
    crossmatch = ['', '', '', '']

    ast = compile('^\s+A/\d{4}')
    if len(items) == 1:
        if dbg: print("1 item found")
        # Is of the form "<foo> does not exist" or "<foo> was not confirmed". But can
        # now apparently include comets...
        chunks = items[0].split()
        none_id = ''
        body = chunks[0]
        if chunks[1].find('does') >= 0 or ('not' in chunks and 'real' in chunks):
            none_id = 'doesnotexist'
        elif chunks[0].find('Comet') >= 0:
            body = chunks[4]
            none_id = chunks[1] + ' ' + chunks[2]
        elif len(chunks) >= 5:
            if chunks[2].lower() == 'not' and chunks[3].lower() == 'confirmed':
                none_id = 'wasnotconfirmed'
            elif (chunks[2].lower() == 'not' and chunks[4].lower() == 'minor') or (chunks[2].lower() == 'suspected' and chunks[3].lower() == 'artificial'):
                none_id = 'wasnotminorplanet'
            elif chunks[2].lower() == 'not' and chunks[3].lower() == 'interesting':
                none_id = ''
            else:
                if dbg: print(chunks)
                middle = chunks.index('=')
                body = chunks[middle+1].rstrip()
                none_id = ' '.join(chunks[:middle]).rstrip()
        none_id = none_id.replace('(', '').replace(')', '')
        crossmatch = [body, none_id, '', ' '.join(chunks[-3:])]
    elif len(items) == 3:
        if dbg: print("3 items found")
        if items[0].lower().find('was not confirmed') != -1:
            # Is an odd case of not confirmed but with an MPEC...
            chunks = items[0].split()
            newid = 'wasnotconfirmed'
            provid = chunks[0]
            mpec = ''
            date = ' '.join(chunks[-4:-1])
        elif items[0].find('Comet') != 1 and len(ast.findall(items[0])) != 1:
            # Is of the form "<foo> = <bar>(<date> UT)"
            if items[1].string is not None:
                newid = str(items[0]).lstrip()+items[1].string.strip()
                provid_date = items[2].split('(')
                provid = provid_date[0].replace(' = ', '').rstrip()
                date = '('+provid_date[1].strip()
                mpec = ''
            else:
                chunks = items[0].split('=')
                newid = chunks[0].strip()
                provid_date = chunks[1].split('(')
                provid = provid_date[0].strip()
                provid_date = provid_date[1].split(')')
                date = '('+provid_date[0].strip()+')'
                mpec = ''
                if items[1].contents[0].string is not None:
                    if items[1].contents[0].string == 'MPEC':
                        mpec = items[1].contents[0].string + items[1].contents[1].string
        else:
            # Now matches comets and 'A/<YYYY>' type objects
            if dbg:
                print("Comet found, parsing")
            if dbg:
                print("Items=", items)

            items[0] = sub(r"\s+\(", r"(", items[0])
            # Occasionally we get things of the form " Comet 2015 TQ209 = LM02L2J(Oct. 24.07 UT)"
            # without the leading "C/<year>". The regexp below fixes this by
            # looking for any amount of whitespace at the start of the string,
            # the word 'Comet',any amount of whitespace, and any amount of
            # digits (the '(?=') part looks for but doesn't capture/remove the
            # regexp that follows
            items[0] = sub(r"^\s+Comet\s+(?=\d+)", r"Comet C/", items[0])
            subitems = items[0].lstrip().split()
            if dbg:
                print("Subitems=", subitems)
            if len(subitems) == 7:
                # Of the form 'A/2017 U2 = ZC82561 etc"
                newid = subitems[0] + ' ' + subitems[1]
                index = 3
            else:
                # Comet form
                newid = subitems[1] + ' ' + subitems[2]
                index = 4
            provid_date = subitems[index].split('(')
            provid = provid_date[0]
            date = '('+provid_date[1] + ' ' + subitems[index+1] + ' ' + subitems[index+2]
            mpec = items[1].contents[0].string + items[1].contents[1].string

        crossmatch = [provid, newid, mpec, date]
    elif len(items) == 5:
        # Is of the form "<foo> = <bar> (date UT) [see MPEC<x>]"
        if dbg: print("5 items found")
        newid = str(items[0]).lstrip()+items[1].string.strip()
        provid_date = items[2].split()
        provid = provid_date[1]
        date = ' '.join(provid_date[2:5])
        mpec = items[3].contents[0].string + items[3].contents[1].string
        crossmatch = [provid, newid, mpec, date]
    else:
        logger.warning("Unknown number of fields. items=%s", items)

    return crossmatch


def fetch_previous_NEOCP_desigs(dbg=False):
    """Fetches the "Previous NEO Confirmation Page Objects" from the MPC, parses
    it and returns a list of lists of object, provisional designation or failure
    reason, date and MPEC."""

    previous_NEOs_url = 'https://www.minorplanetcenter.net/iau/NEO/ToConfirm_PrevDes.html'

    page = fetchpage_and_make_soup(previous_NEOs_url, parser="html5lib")
    if page is None:
        return None

    divs = page.find_all('div', id="main")

    crossids = []
    for row in divs[0].find_all('li'):
        items = row.contents
        if dbg:
            print(items, len(items))
# Skip the first "Processing" list item
        if items[0].strip() == 'Processing':
            continue
        crossmatch = parse_previous_NEOCP_id(items)
# Append to list
        if crossmatch != ['', '', '', '']:
            crossids.append(crossmatch)

    return crossids


def fetch_NEOCP(dbg=False):
    """Fetches the NEO Confirmation Page and returns a BeautifulSoup object
    of the page."""

    NEOCP_url = 'https://www.minorplanetcenter.net/iau/NEO/toconfirm_tabular.html'

    neocp_page = fetchpage_and_make_soup(NEOCP_url, parser='html5lib')
    return neocp_page


def parse_NEOCP(neocp_page, dbg=False):
    """Takes a BeautifulSoup object of the NEO Confirmation Page and extracts a
    list of objects, which is returned."""

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
    """Takes a BeautifulSoup object of the NEO Confirmation Page and extracts a
    list of objects along with a dictionary of extra parameters (score,
    discovery date, update date, # obs, arc length (in days) and not seen (in days)
    which are returned."""

    PCCP_url = 'https://www.minorplanetcenter.net/iau/NEO/pccp_tabular.html'

    if type(neocp_page) != BeautifulSoup:
        return None

# Find the table with the objects
    table = neocp_page.find("table", { "class" : "tablesorter"})
    if table is None:
        return None
    table_body = table.find("tbody")
    if table_body is None:
        return None

    new_objects = []
    object_list = []
    pccp_page = None
    for row in table_body.findAll("tr"):
        cols = row.findAll("td")
        if len(cols) != 0:
            # Turn the HTML non-breaking spaces (&nbsp;) into regular spaces
            cols = [ele.text.replace(u'\xa0', u' ').strip() for ele in cols]
            if dbg:
                print(len(new_objects), len(cols))
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
                    elif update_date[0] == 'J':
                        # At some point the MPC decided to changed their scheme
                        # for the JD update time and now they all start with 'J'...
                        update_type = cols[6].split()[1]
                        if 'added' in update_type.lower():
                            updated = False
                        elif 'updated' in update_type.lower():
                            updated = True
                    update_jd = update_date[1:]
                    update_date = jd_utc2datetime(update_jd)
            except:
                updated = None
                update_date = None
            if pccp is not True:
                try:
                    score = int(cols[1][0:3])
                except:
                    score = None
                try:
                    neocp_datetime = parse_neocp_decimal_date(cols[2])
                except ValueError:
                    neocp_datetime = None
                    logger.warning("Date Parsing error:" + cols[2])
                    logger.warning(cols)
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
                if pccp_page is None:
                    pccp_page = fetchpage_and_make_soup(PCCP_url)
                comet_objects = parse_PCCP(pccp_page)
                if dbg:
                    print(comet_objects)
                if comet_objects:
                    for comet in comet_objects:
                        obj_id = comet[0]
                        if dbg:
                            print("obj_id=", obj_id)
                        if obj_id not in object_list:
                            object_list.append(obj_id)
                            new_object = (obj_id, comet[1])
                            new_objects.append(new_object)

    return new_objects


def parse_PCCP(pccp_page, dbg=False):

    if type(pccp_page) != BeautifulSoup:
        return None

# Find the table with the objects
    table = pccp_page.find("table", {"class" : "tablesorter"})
    if table is None:
        return None
    table_body = table.find("tbody")
    if table_body is None:
        return None

    new_objects = []
    object_list = []
    pccp_page = None
    for row in table_body.findAll("tr"):
        cols = row.findAll("td")
        if len(cols) != 0:
            # Turn the HTML non-breaking spaces (&nbsp;) into regular spaces
            cols = [ele.text.replace(u'\xa0', u' ').strip() for ele in cols]
            if dbg:
                print("Cols=", cols, len(cols))
            pccp = False
            try:
                update_date = cols[6].split()[0]
                updated = None
                if update_date[0] == 'U':
                    updated = True
                elif update_date[0] == 'A':
                    updated = False
                elif update_date[0] == 'J':
                    # At some point the MPC decided to changed their scheme
                    # for the JD update time and now they all start with 'J'...
                    update_type = cols[6].split()[1]
                    if 'added' in update_type.lower():
                        updated = False
                    elif 'updated' in update_type.lower():
                        updated = True
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
    """Query the MPC's showobs service with the specified <obj_id_or_page>. If
    the type of <obj_id_or_page> is not a BeautifulSoup object, it will do a
    fetch of the page of the page from the MPC first. Then the passed or
    downloaded page is turned into a list of unicode strings with blank lines
    removed, which is returned. In the case of the object not existing or having
    being removed from the NEOCP,  None is returned."""

    if type(obj_id_or_page) != BeautifulSoup:
        obj_id = obj_id_or_page
        NEOCP_obs_url = 'https://cgi.minorplanetcenter.net/cgi-bin/showobsorbs.cgi?Obj='+obj_id+'&obs=y'
        neocp_obs_page = fetchpage_and_make_soup(NEOCP_obs_url)
    else:
        neocp_obs_page = obj_id_or_page

    if neocp_obs_page is None:
        return None


# If the object has left the NEOCP, the HTML will say 'None available at this time.'
# and the length of the list will be 1 (but clean of blank lines first using
# list comprehension)
    obs_page_list = [line for line in neocp_obs_page.text.split('\n') if line.strip() != '']
    obs_lines = None
    if len(obs_page_list) > 1:
        obs_lines = obs_page_list

    return obs_lines


def fetch_mpcobs(asteroid, debug=False):
    """Performs a search on the MPC Database for <asteroid> and returns the
    resulting observation as a list of text observations."""

    asteroid = asteroid.strip().replace(' ', '+')
    html_id = asteroid.replace('/', '%2F')
    query_url = 'https://www.minorplanetcenter.net/db_search/show_object?object_id=' + html_id

    page = fetchpage_and_make_soup(query_url)
    if page is None:
        return None

    if debug:
        print(page)
# Find all the '<a foo' tags in the page. This will contain the links we need,
# plus other junk
    refs = page.findAll('a')

# Use a list comprehension to find the 'tmp/<asteroid>.dat' link in among all
# the other links. Turn any pluses (which were spaces) into underscores.
    link = [x.get('href') for x in refs if 'tmp/'+asteroid.replace('+', '_').replace('/', '_') in x.get('href')]

    if len(link) == 1:
        # Replace the '..' part with proper URL

        astfile_link = link[0].replace('../', 'https://www.minorplanetcenter.net/')
        obs_page = fetchpage_and_make_soup(astfile_link)

        if obs_page is not None:
            obs_page = obs_page.text.split('\n')
        return obs_page

    return None


def translate_catalog_code(code_or_name, ades_code=False):
    """Mapping between the single character in column 72 of MPC records
    and the astrometric reference catalog used.
    Documentation at: https://www.minorplanetcenter.net/iau/info/CatalogueCodes.html"""

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
                  "W" : "UCAC5",
                  }
    # https://www.minorplanetcenter.net/iau/info/ADESFieldValues.html
    catalog_mapping = {'USNO-SA2.0'  : 'USNOSA2',  # Can't test, don't have CDs
                       'USNO-A2.0'   : 'USNOA2',   # Can't test, don't have CDs
                       'USNO-B1.0'   : 'USNOB1',
                       'UCAC-3'      : 'UCAC3',
                       'UCAC-4'      : 'UCAC4',
                       'URAT-1'      : 'URAT1',    # Failed in Astrometrica, couldn't test
                       'NOMAD'       : 'NOMAD',
                       'CMC-14'      : 'CMC14',    # Failed in Astrometrica, couldn't test
                       'CMC-15'      : 'CMC15',
                       'PPMXL'       : 'PPMXL',
                       'GAIA-DR1'    : 'Gaia1',
                       'GAIA-DR2'    : 'Gaia2',
                       '2MASS'       : '2MASS'
                      }
    catalog_or_code = ''
    if len(code_or_name.strip()) == 1:
        catalog_or_code = catalog_codes.get(code_or_name, '')
        if not catalog_or_code:
            logger.warning("{} is not in our accepted list of astrometric catalog codes.".format(code_or_name))
    else:
        if ades_code is True:
            catalog_or_code = catalog_mapping.get(code_or_name.upper(), '')
        else:
            for code, catalog in catalog_codes.items():
                if code_or_name == catalog:
                    catalog_or_code = code

    return catalog_or_code


def parse_mpcobs(line):
    """Parse a MPC format 80 column observation record line, returning a
    dictionary of values or an empty dictionary if it couldn't be parsed

    Be aware of potential confusion between obs_type of 'S' and 's'. This
    is enforced by MPC, see
    https://www.minorplanetcenter.net/iau/info/SatelliteObs.html
    """

    params = {}
    line = line.rstrip()
    if len(line) != 80 or len(line.strip()) == 0:
        msg = "Bad line %d %d" % (len(line), len(line.strip()))
        logger.debug(msg)
        return params
    number = str(line[0:5])
    prov_or_temp = str(line[5:12])
    comet_desig = ['C', 'P', 'D', 'X', 'A']

    fragment = None
    if number.strip() in comet_desig and len(prov_or_temp.strip()) != 0:
        # Comet with no number
        body = number.strip() + prov_or_temp.strip()
    elif len(number.strip()) != 0 and len(prov_or_temp.strip()) != 0:
        # Number and provisional/temp. designation
        body = number
        if prov_or_temp.lstrip(' ').islower():
            # If the last characters of the provisional desigination is a
            # lowercase letter (with spaces to the left) OR
            # the last letter only of the provisional desigination is lowecase,
            # with everything uppercase (or numbers):
            #   it is a comet fragment (probably...)
            fragment = prov_or_temp.lstrip(' ')
        elif (prov_or_temp[-1] != '0' and prov_or_temp[-1].islower() and prov_or_temp[:-1].isupper()):
            fragment = prov_or_temp[-1]
    elif len(number.strip()) == 0 or len(prov_or_temp.strip()) != 0:
        # No number but provisional/temp. designation
        body = prov_or_temp
    else:
        body = number

    body = body.rstrip()
    # Strip leading zeros off comets
    if body[-1] == 'P' and body[:-1].isdigit():
        body = body.lstrip('0')
        if fragment is not None:
            body += '-' + fragment.upper()
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
        obs_mag = float(line[65:70])
    except ValueError:
        obs_mag = None

    site_code = str(line[-3:])

    discovery = False
    lco_discovery = False
    if line[12] == '*':
        discovery = True
        if site_code in LCOGT_site_codes():
            lco_discovery = True
        if flag == ' ':
            flag = '*'
        else:
            flag = '*,' + flag

    if obs_type == 'C' or obs_type == 'S' or obs_type == 'A':
        # Regular CCD observations, first line of satellite observations or
        # observations that have been rotated from B1950 to J2000 ('A')
        # print("Date=",line[15:32])
        params = { 'body'     : body,
                   'flags'    : flag,
                   'obs_type' : obs_type,
                   'obs_date' : parse_neocp_decimal_date(line[15:32].strip()),
                   'obs_mag'  : obs_mag,
                   'filter'   : filter,
                   'astrometric_catalog' : translate_catalog_code(line[71]),
                   'site_code' : site_code,
                   'discovery' : discovery,
                   'lco_discovery' : lco_discovery
                 }
        ptr = 1
        ra_dec_string = line[32:56]
#        print("RA/Dec=", ra_dec_string)
        ptr, ra_radians, status = S.sla_dafin(ra_dec_string, ptr)
        params['obs_ra'] = degrees(ra_radians) * 15.0
        ptr, dec_radians, status = S.sla_dafin(ra_dec_string, ptr)
        params['obs_dec'] = degrees(dec_radians)
    elif obs_type.upper() == 'R':
        # Radar observations, skip
        logger.debug("Found radar observation, skipping")
    elif obs_type.upper() == 'M':
        # Micrometer observations, skip
        logger.debug("Found micrometer observation, skipping")
    elif obs_type == 's':
        # Second line of satellite-based observation, stuff whole line into
        # 'extrainfo' and parse what we can (so we can identify the corresponding
        # 'S' line/frame)
        params = { 'body'     : body,
                   'obs_type' : obs_type,
                   'obs_date' : parse_neocp_decimal_date(line[15:32].strip()),
                   'extrainfo' : line,
                   'site_code' : str(line[-3:])
                 }
    return params


def clean_element(element):
    """Cleans an element (passed) by removing any units"""
    key = element[0]
    value = None
    if len(element) == 2:
        value = element[1]
    # Split the Key at the open parentheses and discard everything that follows
    key = key.split(' (', 1)[0]

    return key, value


def fetch_mpcdb_page(asteroid, dbg=False):
    """Performs a search on the MPC Database for <asteroid> and returns a
    BeautifulSoup object of the page (for future use by parse_mpcorbit())"""

    # Strip off any leading or trailing space and replace internal space with a
    # plus sign
    if dbg:
        print("Asteroid before=", asteroid)
    asteroid = asteroid.strip().replace(' ', '+')
    if dbg:
        print("Asteroid  after=", asteroid)
    query_url = 'https://www.minorplanetcenter.net/db_search/show_object?object_id=' + asteroid

    page = fetchpage_and_make_soup(query_url)
    if page is None:
        return None

#    if dbg: print(page)
    return page


def parse_mpcorbit(page, epoch_now=None, dbg=False):
    """Parses a page of elements tables return from the Minor Planet Center (MPC)
    database search page and returns an element set as a dictionary.
    In the case of multiple element sets (normally comets), the closest in time
    to [epoch_now] is returned."""
    if epoch_now is None:
        epoch_now = datetime.utcnow()

    data = []
    # Find the table of elements and then the subtables within it
    elements_tables = page.find_all('table', {'class' : 'nb'})
    if elements_tables is None or len(elements_tables) == 0:
        logger.warning("No element tables found")
        return {}

    min_elements_dt = timedelta.max
    best_elements = {}
    for elements_table in elements_tables:
        data_tables = elements_table.find_all('table')
        for table in data_tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                cols = [elem.text.strip() for elem in cols]
                data.append([elem for elem in cols if elem])

        elements = dict(clean_element(elem) for elem in data)
        # Look for nearest element set in time
        epoch = elements.get('epoch', None)
        if dbg:
            print(epoch)
        if epoch is not None:
            try:
                epoch_datetime = datetime.strptime(epoch, "%Y-%m-%d.0")
                epoch_dt = epoch_now - epoch_datetime
                if epoch_dt < min_elements_dt:
                    # Closer match found, update best elements and minimum time
                    # separation
                    if dbg:
                        print("Found closer element match", epoch_dt, min_elements_dt, epoch)
                    best_elements = elements
                    min_elements_dt = abs(epoch_dt)
                else:
                    if dbg:
                        print("No closer match found")
            except ValueError:
                msg = "Couldn't parse epoch: " + epoch
                logger.warning(msg)
            name_element = page.find('h3')
            if name_element is not None:
                best_elements['obj_id'] = name_element.text.strip()

    return best_elements


def read_mpcorbit_file(orbit_file):

    try:
        orbfile_fh = open(orbit_file, 'r')
    except IOError:
        logger.warning("File %s not found" % orbit_file)
        return None

    orblines = orbfile_fh.readlines()
    orbfile_fh.close()
    orblines[0] = orblines[0].replace('Find_Orb  ', 'NEOCPNomin').rstrip()

    return orblines


class PackedError(Exception):
    """Raised when an invalid pack code is found"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def validate_packcode(packcode):
    """Method to validate that <packcode> is a valid MPC packed designation.
    Format is as described at:
    https://www.minorplanetcenter.org/iau/info/PackedDes.html"""

    valid_cent_codes = {'I' : 18, 'J' : 19, 'K' : 20}
    valid_half_months = 'ABCDEFGHJKLMNOPQRSTUVWXY'
    comet_desig = ['C', 'P', 'D', 'X', 'A']

    if len(packcode) == 5 and ((packcode[0].isalpha() and packcode[1:].isdigit()) or packcode.isdigit()):
        return True
    if len(packcode) == 8 and packcode[0] in comet_desig and packcode[1] in valid_cent_codes:
        return True
    if len(packcode) != 7:
        raise PackedError("Invalid packcode length")
    if packcode[0] not in valid_cent_codes:
        raise PackedError("Invalid century code")
    if packcode[1:3].isdigit() is False:
        raise PackedError("Invalid year")
    if packcode[3] not in valid_half_months:
        raise PackedError("Invalid half-month character")
    if not packcode[6].isupper() or not packcode[6].isalpha():
        raise PackedError("Invalid half-month order character")
    return True


def validate_text(text_string):
    valid_symbols = '`~!@#$%^&*()_+- ={}|[]\:;<,>.?/"'+"'"
    valid_characters = 'abcdefghijklmnopqrstuvwxyz'
    if text_string is None:
        return ''

    out_string = ''
    for char in text_string:
        if char.isdigit():
            out_string += char
        elif char in valid_characters or char in valid_characters.upper():
            out_string += char
        elif char in valid_symbols:
            out_string += char

    return out_string


def packed_to_normal(packcode):
    """Converts MPC packed provisional designations e.g. K10V01F to unpacked
    normal desigination i.e. 2010 VF1 including packed 5 digit number designations
    i.e. L5426 to 215426"""

# Convert initial letter to century
    cent_codes = {'I' : 18, 'J' : 19, 'K' : 20}
    comet_flag = ''
    frag_tag = ''
    comet_desig = ['C', 'P', 'D', 'X', 'A']

    if not validate_packcode(packcode):
        raise PackedError("Invalid packcode %s" % packcode)
    elif len(packcode) == 5 and packcode.isdigit():
        # Just a number
        return str(int(packcode))
    elif len(packcode) == 5 and packcode[0].isalpha() and packcode[1:].isdigit():
        cycle = cycle_mpc_character_code(packcode[0])
        normal_code = str(cycle) + packcode[1:]
        return normal_code
    elif len(packcode) == 8 and packcode[0] in comet_desig:
        mpc_cent = cent_codes[packcode[1]]
        comet_flag = '{}/'.format(packcode[0])
        packcode = packcode[1:]
    else:
        mpc_cent = cent_codes[packcode[0]]

# Convert next 2 digits to year
    mpc_year = packcode[1:3]
    if not comet_flag or (packcode[-1] != "0" and packcode[-1].upper() == packcode[-1]):
        no_in_halfmonth = packcode[3] + packcode[6]
    else:
        no_in_halfmonth = packcode[3]
        if packcode[-1] != "0":
            # if non-0 lower case code at the end of comet designation, then we are following a fragment
            frag_tag = "-{}".format(packcode[-1].upper())

    # Turn the character of the cycle count, which runs 0--9, A--Z, a--z into a
    # consecutive integer by converting to ASCII code and skipping the non-alphanumerics
    cycle = cycle_mpc_character_code(packcode[4])
    digit = int(packcode[5])
    count = cycle * 10 + digit
    # No digits on the end of the unpacked designation if it's the first loop through
    if cycle == 0 and digit == 0:
        count = ''

# Assemble unpacked code
    normal_code = comet_flag + str(mpc_cent) + mpc_year + ' ' + no_in_halfmonth + str(count) + frag_tag

    return normal_code


def cycle_mpc_character_code(char):
    """Convert MPC character code into a number 0--9, A--Z, a--z and return integer"""
    cycle = ord(char)
    if cycle >= ord('a'):
        cycle -= 61
    elif ord('A') <= cycle <= ord('Z'):
        cycle -= 55
    else:
        cycle -= ord('0')
    return cycle


def psv_padding(s, l, jtype, dpos=0):
    """PSV formatting routine (adapted from ADESMaster.adesutility.applyPaddingAndJustification)

    psv_padding(s, l, jtype, dpos)

    Inputs:
        s: input string
        l: output length (pad with blanks)
            If string is too long it is returned without change
        jtype: justification type
            L: left
            R: right
            C: center
            D: Justify on Decimal
        dpos: decimal point in column <dpos> (for jtype = "D")

    Return Value:
        (padded string, l, dpos)
        l is the achieved width.  It may be longer than l
        dpos is the achieved dpos.  It may be different from dpos

        The width and dpos may be different. These should be used to
        update the headerInfo array if one is trying to achieve alignment
        over multiple lines.
    """

    ll = len(s)
    if jtype.upper() == 'L':  # negative multipliers result in ''
        outs = s + (l - ll)*' '
        return outs, len(outs), dpos
    elif jtype.upper() == 'R':
        outs = (l - ll)*' ' + s
        return outs, len(outs), dpos
    elif jtype.upper() == 'C':
        i = (l-ll)//2
        j = i
        if i*2 != l-ll:
            j += 1
        outs = i*' ' + s + j*' '
        return outs, len(outs), dpos
    elif jtype.upper() == 'D':  # null strings not allowed
        try:
            if dpos < 0:
                raise RuntimeError("Invalid negative value of dpos ({})".format(dpos))
        except TypeError:
            raise RuntimeError("Illegal Decimal position: {} ".format(dpos))

        # pad only with spaces on both sides
        # and do not change s
        #
        # if s has no decimal point don't add one
        # but line up as if it were to the right
        # of s.
        #
        # the result may be too wide.  This is OK
        # we will do a fix-up on width in the caller.
        # Note this means we have to do it twice but
        # we never will get wider as a result of the
        # second pass.
        #
        # Also, we assume s is a decimal for xsd.  If
        # not, validation will fail later.  If there
        # is more than one decimal point, it will fail
        # here.

        sp = s.split('.')
        if len(sp) == 1:  # No decimal point
            sleft = s
            sright = ''
        elif len(sp) == 2:  # has decimal point
            (sleft, sright) = sp
        else:
            raise RuntimeError('Illegal string for decimal justification: {}'.format(s))

        # now re-pack with width
        leftpad = dpos - 1 - len(sleft)

        # figure out dpos extension
        if leftpad < 0:  # <n> needs adjusting
            ndpos = dpos - leftpad
            dpos = ndpos
        rightpad = (l - dpos) - len(sright)
        if (len(s) > 0) and (s[-1] == '.'):  # trailing decimal point adjustment
            sleft = s
            rightpad -= 1

        # works for negative values of leftpad and rightpad
        # adding no characters
        if sright:  # don't add '.' if sright is ''
            retval = leftpad * ' ' + sleft + '.' + sright + rightpad * ' '
        else:
            rightpad += 1
            retval = leftpad * ' ' + sleft + rightpad * ' '
        return retval, len(retval), dpos

    else:
        raise RuntimeError("Illegal justification string: {} ".format(jtype))


def parse_goldstone_chunks(chunks, dbg=False):
    """Tries to parse the Goldstone target line (a split()'ed list of fields)
    to extract the object id. Could also parse the date of radar observation
    and whether astrometry or photometry is needed"""

    if dbg:
        print(chunks)
    # Try to convert the 2nd field (counting from 0...) to an integer and if
    # that suceeds, check it's greater than 31. If yes, it's an asteroid number
    # (we assume asteroid #1-31 will never be observed with radar..)
    object_id = ''

    try:
        astnum = int(chunks[2])
    except ValueError:
        if dbg:
            print("Could not convert", chunks[2], "to asteroid number. Will try different method.")
        astnum = -1

    if astnum > 31:
        object_id = str(astnum)
        # Check if the next 2 characters are uppercase in which it's a
        # designation, not a name
        if chunks[3][0].isupper() and chunks[3][1].isupper():
            if dbg:
                print("In case 1")
            object_id = object_id + ' ' + str(chunks[3])
    else:
        if dbg:
            print("Specific date of observation")
        # We got an error or a too small number (day of the month)
        if astnum <= 31 and chunks[3].isdigit() and chunks[4].isdigit() and chunks[2][-1].isdigit():
            # We have something of the form [20, 2014, YB35; only need first
            # bit
            if dbg:
                print("In case 2a")
            object_id = str(chunks[3])
        elif astnum <= 31 and chunks[3].isdigit() and chunks[4].isdigit() and chunks[2][-1].isalnum():
            # We have something that straddles months
            if dbg:
                print("In case 2b")
            if chunks[5].isdigit() or chunks[5][0:2].isupper() is False:
                # Of the form '2017 May 29-Jun 02 418094 2007 WV4' or number and
                # name e.g.  '2017 May 29-Jun 02 6063 Jason'
                object_id = str(chunks[4])
            else:
                # Of the form '2017 May 29-Jun 02 2017 CS'
                object_id = str(chunks[4]) + ' ' + chunks[5]
        elif astnum <= 31 and (chunks[3].isdigit() or chunks[3][0:2] == 'P/'
                               or chunks[3][0:2] == 'C/') and chunks[4].isalnum():
            # We have a date range e.g. '2016 Mar 17-23'
            # Test if the first 2 characters of chunks[4] are uppercase
            # If yes then we have a desigination e.g. [2014] 'UR' or [2015] 'FW117'
            # If no, then we have a name e.g. [1566] 'Icarus'
            # Hopefully some at Goldstone won't shout the name of the object
            # e.g. '(99942) APOPHIS'! or we're hosed...
            if chunks[4][0:2].isupper():
                if dbg:
                    print("In case 3a")
                object_id = str(chunks[3] + ' ' + chunks[4])
            else:
                if dbg:
                    print("In case 3b")
                object_id = str(chunks[3])
        elif chunks[3].isdigit() and chunks[4].isalpha():
            if dbg:
                print("In case 4")
            object_id = str(chunks[3] + ' ' + chunks[4])

    return object_id


def fetch_goldstone_page():
    """Fetches the Goldstone page of radar targets, returning a BeautifulSoup
    page"""

    goldstone_url = 'http://echo.jpl.nasa.gov/asteroids/goldstone_asteroid_schedule.html'

    page = fetchpage_and_make_soup(goldstone_url)

    return page


def fetch_goldstone_targets(page=None, dbg=False):
    """Fetches and parses the Goldstone list of radar targets, returning a list
    of object id's for the current year.
    Takes either a BeautifulSoup page version of the Goldstone target page (from
    a call to fetch_goldstone_page() - to allow  standalone testing) or  calls
    this routine and then parses the resulting page.
    """

    if type(page) != BeautifulSoup:
        page = fetch_goldstone_page()

    if page is None:
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
            if in_objects is True:
                if line.lstrip()[0:4].isdigit() is False:
                    # Text comments in the table..
                    continue
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
                # Look for ampersands in the line and change to hyphens
                if '&' in line[0:40] or ' &' in line[0:40] or '& ' in line[0:40] or ' & ' in line[0:40]:
                    line = line.replace(' & ', '-', 1).replace('& ', '-', 1).replace(' &', '-', 1)
                chunks = line.lstrip().split()
                # if dbg: print(line)
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
    return radar_objects


def fetch_arecibo_page():
    """Fetches the Arecibo list of radar targets, returning a list
    of object id's for the current year"""

    arecibo_url = 'http://www.naic.edu/~pradar/'

    page = fetchpage_and_make_soup(arecibo_url)

    return page


def fetch_arecibo_targets(page=None):
    """Parses the Arecibo webpage for upcoming radar targets and returns a list
    of these targets back.
    Takes either a BeautifulSoup page version of the Arecibo target page (from
    a call to fetch_arecibo_page() - to allow  standalone testing) or  calls
    this routine and then parses the resulting page.
    """

    if type(page) != BeautifulSoup:
        page = fetch_arecibo_page()

    targets = []

    if type(page) == BeautifulSoup:
        # Find the tables
        tables = page.find_all('table')
        for t, targets_table in enumerate(tables):
            rows = targets_table.find_all('tr')
            header = rows[0].find_all('td')[0].text.upper()
            if len(rows) > 1 and 'OBJECT' in header or 'ASTEROID' in header:
                for row in rows[1:]:
                    items = row.find_all('td')
                    target_object = items[0].text
                    target_object = target_object.strip()
                    # See if it is the form "(12345) 2008 FOO". If so, extract
                    # just the asteroid number
                    if '(' in target_object and ')' in target_object:
                        # See if we have parentheses around the number or around the
                        # temporary designation.
                        # If the first character in the string is a '(' we have the first
                        # case and should split on the closing ')' and take the 0th chunk
                        # If the first char is not a '(', then we have parentheses around
                        # the temporary designation and we should split on the '(', take
                        # the 0th chunk and strip whitespace
                        split_char = ')'
                        if target_object[0] != '(':
                            split_char = '('
                        target_object = target_object.split(split_char)[0].replace('(', '')
                        target_object = target_object.strip()
                    else:
                        # No parentheses, either just a number or a number and name
                        chunks = target_object.split(' ')
                        if len(chunks) >= 2:
                            if chunks[0].isalpha() and chunks[1].isalpha():
                                logger.warning("All text object found: " + target_object)
                                target_object = None
                            else:
                                if chunks[1].replace('-', '').isalpha() and len(chunks[1]) != 2:
                                    target_object = chunks[0]
                                elif 'Comet' in chunks[0] and '/P' in chunks[1].rstrip()[-2:]:
                                    target_object = chunks[1].replace('/', '')
                                else:
                                    target_object = chunks[0] + " " + chunks[1]
                        else:
                            logger.warning("Unable to parse Arecibo target %s" % target_object)
                            target_object = None
                    if target_object:
                        targets.append(target_object)
            else:
                logger.warning("No targets found in Arecibo page table {}.".format(t+1))
    return targets


def imap_login(username, password, server='imap.gmail.com'):
    """Logs into the specified IMAP [server] (Google's gmail is assumed if not
    specified) with the provide username and password.

    An imaplib.IMAP4_SSL connection instance is returned or None if the
    login failed"""

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
    """Search through the specified folder/label (defaults to "NASA-ARM" if not
    specified) within the passed IMAP mailbox <mailbox> for emails to the
    small bodies list and returns a list of targets. Emails that are more than
    [date_cutoff] days old (default is 1 day) will not be looked at."""

    list_address = '"small-bodies-observations@lists.nasa.gov"'
    list_authors = [ '"paul.a.abell@nasa.gov"',
                     '"Abell, Paul A. (JSC-XI111) via small-bodies-observations"',
                     '"paul.w.chodas@jpl.nasa.gov"',
                     '"brent.w.barbee@nasa.gov"',
                     '"Barbee, Brent W. (GSFC-5950) via small-bodies-observations"']

    list_prefix = '[' + list_address.replace('"', '').split('@')[0] + ']'
    list_suffix = 'Observations Requested'

    NASA_targets = []

    status, data = mailbox.select(folder)
    if status == "OK":
        msgnums = ['']
        for author in list_authors:
            # Look for messages to the mailing list but without specifying a charset
            status, msgs = mailbox.search(None, 'TO', list_address,
                                          'FROM', author)
            msgs = [msgs[0].decode('utf-8'), ]
            if status == 'OK' and len(msgs) > 0 and msgs[0] != '':
                msgnums = [msgnums[0] + ' ' + msgs[0], ]
        # Messages numbers come back in a space-separated string inside a
        # 1-element list in msgnums
        if status == "OK" and len(msgnums) > 0 and msgnums[0] != '':

            for num in msgnums[0].split():
                try:
                    status, data = mailbox.fetch(num, '(RFC822)')
                    if status != 'OK' or len(data) == 0 and msgnums[0] is not None:
                        logger.error("Error getting message %s", num)
                    else:
                        # Convert message and see if it has the right things
                        raw_email = data[0][1]
                        raw_email_string = raw_email.decode('utf-8')
                        msg = email.message_from_string(raw_email_string)
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
                except Exception as e:
                    logger.error(e)
                    logger.error("Error decoding message %s", num)
                    return NASA_targets
        else:
            logger.warning("No mailing list messages found")
            return []
    else:
        logger.error("Could not open folder/label %s on %s" % (folder, mailbox.host))
        return []
    return NASA_targets


def get_site_status(site_code):
    """Queries the Valhalla telescope states end point to determine if the
    passed <site_code> is available for scheduling.
    Returns True if the site/telescope is available for scheduling and
    assumed True if the status can't be determined. Otherwise if the
    last event for the telescope can be found and it does not show
    'AVAILABLE', then the good_to_schedule status is set to False."""

    good_to_schedule = True
    reason = ''

# Get dictionary mapping LCO code (site-enclosure-telescope) to MPC site code
# and reverse it
    site_codes = cfg.valid_site_codes
    lco_codes = {mpc_code: lco_code.lower().replace('-', '.') for lco_code, mpc_code in site_codes.items()}

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

    return good_to_schedule, reason


def fetch_yarkovsky_targets(targets_or_file=None):
    """Main wrapper routine for either fetch_yarkovsky_targets_list() or
    fetch_yarkovsky_targets_ftp() to fetch Yarkovsky targets.
    If [targets_or_file] is a `list` of targets, fetch_yarkovsky_targets_list()
    is called; if [targets_or_file] is a filename or None, then
    fetch_yarkovsky_targets_ftp() is called and the target list comes from either
    the FTP site (`targets_or_file=None`) or by reading the file specified by
    `targets_or_file`.

    Returns a list of target names.
    """

    if type(targets_or_file) == list:
        yark_target_list = fetch_yarkovsky_targets_list(targets_or_file)
    else:
        yark_target_list = fetch_yarkovsky_targets_ftp(targets_or_file)

    return yark_target_list


def fetch_yarkovsky_targets_list(yark_targets):
    """Parses a list of lines of Yarkovsky targets (read from a file and which
    may contain comments) and returns a list of targets"""

    yark_target_list = []

    for obj_id in yark_targets:
        obj_id = obj_id.strip()
        comment_loc = obj_id.find('#')
        if comment_loc >= 0:
            obj_id = obj_id[0:comment_loc].strip()
        if '_' in obj_id:
            obj_id = str(obj_id).replace('_', ' ')
        if len(obj_id) > 0:
            yark_target_list.append(obj_id)

    return yark_target_list


def fetch_yarkovsky_targets_ftp(file_or_url=None):
    """Fetches Yarkovsky targets from either the specified file (if [file_or_url]
    is not None) or the current list from the FTP site
    and parses it to return the target and expected A2 Yarkovsky value and
    its error"""
    ftp_url = 'ftp://ssd.jpl.nasa.gov/pub/ssd/yarkovsky/yarko_targets/yarko_latest.txt'

    targets = []
    tempdir = None

    if file_or_url is None or file_or_url.startswith('ftp://'):
        if file_or_url is not None and file_or_url.startswith('ftp://'):
            ftp_url = file_or_url
        tempdir = tempfile.mkdtemp(prefix='tmp_neox_')
        target_file = os.path.join(tempdir, 'yarkovsky_targets.txt')

        with closing(urllib.request.urlopen(ftp_url)) as read_fp:
            with open(target_file, 'wb') as write_fp:
                shutil.copyfileobj(read_fp, write_fp)
    else:
        target_file = file_or_url

    if os.path.exists(target_file):
        table = ascii.read(target_file, format='csv')

        for target in list(table['base']):
            target = target.upper()
            # Look for designations of the for yyyyXY[12] and add space in the middle
            if len(target) >=6 and target[0:4].isdigit() and target[4:6].isalpha():
                target = target[0:4] + ' ' + target[4:]
            targets.append(target)

        if tempdir:
            try:
                os.remove(target_file)
                os.rmdir(tempdir)
            except FileNotFoundError:
                pass

    return targets

def fetch_sfu(page=None):
    """Fetches the solar radio flux from the Solar Radio Monitoring
    Program run by National Research Council and Natural Resources Canada.
    The solar radio flux is a measure of the progress through the solar
    cycle which has been shown to affect the atmospheric airglow - one
    of the major components of the night sky brightness.
    Normally this routine is run without any arguments which will fetch
    the current value in 'solar flux units (sfu)'s' (scaled from
    `astropy.units.Jy` (Janskys) where 1 sfu = 10,000 Jy) and the
    `datetime` when it was measured. For testing, [page] can be a static
    BeautifulSoup version of the page. In the event of parsing problems,
    (None, None) is returned."""

    sfu_url = 'http://www.spaceweather.gc.ca/solarflux/sx-4-en.php'

    flux_datetime = None
    flux_sfu = None
    # Define new 'sfu' (solar flux unit)
    sfu = u.def_unit(['sfu', 'solar flux unit'], 10000.0*u.Jy)

    if page is None:
        page = fetchpage_and_make_soup(sfu_url)

    if type(page) == BeautifulSoup:
        table = page.find_all('td')
        obs_jd = None
        try:
            obs_jd = table[0].text
            flux_datetime = jd_utc2datetime(float(obs_jd))
        except (ValueError, IndexError):
            logger.warning("Could not parse flux observation time (" + str(obs_jd) + ")")
        flux_sfu_text = None
        try:
            flux_sfu_text = table[2].text
            flux_sfu = float(flux_sfu_text)
            # Flux is in 'solar flux units', equal to 10,000 Jy or 0.01 MJy.
            # Add in our custom astropy unit declared above.
            flux_sfu = flux_sfu * sfu
        except (ValueError, IndexError):
            logger.warning("Could not parse flux (" + str(flux_sfu_text) + ")")

    return flux_datetime, flux_sfu


def make_location(params):
    location = {'telescope_class': params['pondtelescope'][0:3]}
    if params.get('site', None):
        location['site'] = params['site'].lower()
    if params['site_code'] == 'W85':
        location['telescope'] = '1m0a'
        location['enclosure'] = 'doma'
    elif params['site_code'] == 'W87':
        location['telescope'] = '1m0a'
        location['enclosure'] = 'domc'
    elif params['site_code'] == 'V39':
        location['telescope'] = '1m0a'
        location['enclosure'] = 'domb'
    elif params['site_code'] == 'Z31':
        location['telescope'] = '1m0a'
        location['enclosure'] = 'doma'
    elif params['site_code'] == 'Z24':
        location['telescope'] = '1m0a'
        location['enclosure'] = 'domb'
    return location


def make_target(params):
    """Make a target dictionary for the request. RA and Dec need to be
    decimal degrees"""

    ra_degs = params['ra_deg']
    dec_degs = params['dec_deg']
    # XXX Todo: Add in proper motion and parallax if present
    target = {
               'type' : 'ICRS',
               'name' : params['source_id'],
               'ra'   : ra_degs,
               'dec'  : dec_degs,
               'extra_params' : {}
             }
    if 'vmag' in params:
        target['extra_params']['v_magnitude'] = params['vmag']
    if 'pm_ra' in params:
        target['proper_motion_ra'] = params['pm_ra']
    if 'pm_dec' in params:
        target['proper_motion_dec'] = params['pm_dec']
    if 'parallax' in params:
        target['parallax'] = params['parallax']
    return target


def make_moving_target(elements):
    """Make a target dictionary for the request from an element set"""

    # Generate initial dictionary of things in common
    target = {
                  'name'                : elements['current_name'],
                  'type'                : 'ORBITAL_ELEMENTS',
                  'scheme'              : elements['elements_type'],
                  # Moving object param
                  'epochofel'         : elements['epochofel_mjd'],
                  'orbinc'            : elements['orbinc'],
                  'longascnode'       : elements['longascnode'],
                  'argofperih'        : elements['argofperih'],
                  'eccentricity'      : elements['eccentricity'],
                  'extra_params'      : {}
            }

    if elements['elements_type'].upper() == 'MPC_COMET':
        target['epochofperih'] = elements['epochofperih_mjd']
        target['perihdist'] = elements['perihdist']
    else:
        target['meandist'] = elements['meandist']
        target['meananom'] = elements['meananom']
    if 'v_mag' in elements:
        target['extra_params']['v_magnitude'] = round(elements['v_mag'], 2)

    return target


def make_window(params):
    """Make a window. This is simply set to the start and end time from
    params (i.e. the picked time with the best score plus the block length),
    formatted into a string.
    Hopefully this will prevent rescheduling at a different time as the
    co-ords will be wrong in that case..."""
    window = {
              'start' : params['start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
              'end'   : params['end_time'].strftime('%Y-%m-%dT%H:%M:%S'),
             }

    return window


def make_config(params, filter_list):
    # Common part of a molecule
    conf = {
        'type': params['exp_type'],
        'instrument_type': params['instrument'],
        'target': params['target'],
        'constraints': params['constraints'],
        'acquisition_config': {},
        'guiding_config': {},
        'instrument_configs': []
    }
    if params['exp_type'] == 'REPEAT_EXPOSE':
        # Remove overhead from slot_length so repeat_exposure matches predicted frames.
        # This will allow a 2 hour slot to fit within a 2 hour window.
        single_mol_overhead = cfg.molecule_overhead['filter_change'] + cfg.molecule_overhead['per_molecule_time']
        if '2M0' in params['instrument']:
            overhead = cfg.tel_overhead['twom_setup_overhead']
        elif '0M4' in params['instrument']:
            overhead = cfg.tel_overhead['point4m_setup_overhead']
        elif '1M0' in params['instrument']:
            overhead = cfg.tel_overhead['onem_setup_overhead']
        else:
            overhead = 0
        conf['repeat_duration'] = params['slot_length'] - overhead - single_mol_overhead - 1
        conf['repeat_duration'] = max(conf['repeat_duration'], 1)
    for filt in filter_list:
        if params['exp_type'] == 'REPEAT_EXPOSE' and len(filter_list) == 1:
            exp_count = 1
        else:
            exp_count = filt[1]

        instrument_config = {'exposure_count': exp_count,
                             'exposure_time': params['exp_time'],
                             'optical_elements': {'filter': filt[0]}
                             }

        if params.get('bin_mode', None) == '2k_2x2' and params['pondtelescope'] == '1m0':
            instrument_config['mode'] = 'central_2k_2x2'

        if params['instrument'] == '2M0-SCICAM-MUSCAT':
            if params.get('muscat_sync', False):
                exposure_mode = 'SYNCHRONOUS'
            else:
                exposure_mode = 'ASYNCHRONOUS'
            extra_params = {'exposure_time_g': params['muscat_exp_times']['gp_explength'],
                            'exposure_time_r': params['muscat_exp_times']['rp_explength'],
                            'exposure_time_i': params['muscat_exp_times']['ip_explength'],
                            'exposure_time_z': params['muscat_exp_times']['zp_explength'],
                            'exposure_mode': exposure_mode}
            instrument_config['optical_elements'] = {'diffuser_g_position': 'out',
                                                     'diffuser_r_position': 'out',
                                                     'diffuser_i_position': 'out',
                                                     'diffuser_z_position': 'out'}

            instrument_config['extra_params'] = extra_params
        conf['instrument_configs'].append(instrument_config)

    return conf


def make_spect_config(params, exp_filter):

    if 'ORBITAL_ELEMENTS' in params['target']['type']:  # then non-sidereal target (use larger window)
        acq_rad = 15.0
    else:
        acq_rad = 5.0

    if params['exp_type'].upper() in ['ARC', 'LAMP_FLAT']:
        ag_mode = 'OFF'
        exp_count = 1
        exp_time = 60.0
        if params['exp_type'].upper() == 'LAMP_FLAT' and 'slit_6.0as' in params['spectra_slit']:
            exp_time = 20.0
    else:
        exp_count = params['exp_count']
        exp_time = params['exp_time']

    if params.get('rot_mode', 'VFLOAT') == 'SKY':
        inst_extra = {'rotator_angle': params.get('rot_angle', 0)}
    else:
        inst_extra = {}

    configurations = {
        'type': params['exp_type'],
        'instrument_type': '2M0-FLOYDS-SCICAM',
        'constraints': params['constraints'],
        'target': params['target'],
        'acquisition_config': {
            'mode': 'BRIGHTEST',
            'exposure_time': params.get('ag_exp_time', 10),
            "extra_params": {
              "acquire_radius": acq_rad,
            }
        },
        'guiding_config': {
            'mode': 'ON',
            'optional': False,
            'exposure_time': params.get('ag_exp_time', 10)
        },
        'instrument_configs': [
            {
                'exposure_time': exp_time,
                'exposure_count': exp_count,
                'rotator_mode': params.get('rot_mode', 'VFLOAT'),
                'optical_elements': {
                    'slit': exp_filter[0]
                },
                'extra_params': inst_extra
            }
        ]
    }
    return configurations


def make_configs(params):
    """Handles creating the potentially multiple molecules. Returns a list of the molecules.
    In imaging mode (`params['spectroscopy'] = False` or not present), this just calls
    the regular make_config().
    In spectroscopy mode, this will produce 1, 3 or 5 molecules depending on whether
    `params['calibs']` is 'none, 'before'/'after' or 'both'."""

    filt_list = build_filter_blocks(params['filter_pattern'], params['exp_count'], params['exp_type'])

    calib_mode = params.get('calibs', 'none').lower()
    if params.get('spectroscopy', False) is True:
        # Spectroscopy mode
        params['spectra_slit'] = params['filter_pattern']
        spectrum_molecule = make_spect_config(params, filt_list[0])
        if calib_mode != 'none':
            old_type = params['exp_type']
            params['exp_type'] = 'ARC'
            arc_molecule = make_spect_config(params, filt_list[0])
            params['exp_type'] = 'LAMP_FLAT'
            flat_molecule = make_spect_config(params, filt_list[0])
            params['exp_type'] = old_type
        if calib_mode == 'before':
            configs = [flat_molecule, arc_molecule, spectrum_molecule]
        elif calib_mode == 'after':
            configs = [spectrum_molecule, arc_molecule, flat_molecule]
        elif calib_mode == 'both':
            configs = [flat_molecule, arc_molecule, spectrum_molecule, arc_molecule, flat_molecule]
        else:
            configs = [spectrum_molecule, ]
    else:
        configs = [make_config(params, filt_list)]

    return configs


def make_constraints(params):
    constraints = {
                    # 'max_airmass' : 2.0,    # 30 deg altitude (The maximum airmass you are willing to accept)
                    # 'max_airmass' : 1.74,   # 35 deg altitude (The maximum airmass you are willing to accept)
                    # 'max_airmass' : 1.55,   # 40 deg altitude (The maximum airmass you are willing to accept)
                    # 'max_airmass' : 2.37,   # 25 deg altitude (The maximum airmass you are willing to accept)
                    # 'min_lunar_distance': 30
                    'max_airmass': params.get('max_airmass', 1.74),
                    'min_lunar_distance': params.get('min_lunar_distance', 30)
                  }
    return constraints


def make_single(params, ipp_value, request):
    """Create a user_request for a single observation"""

    requestgroup = {
                    'submitter' : params['user_id'],
                    'requests'  : [request],
                    'name'  : params['group_name'],
                    'observation_type': "NORMAL",
                    'operator'  : "SINGLE",
                    'ipp_value' : ipp_value,
                    'proposal'  : params['proposal_id']
    }

# If the ToO mode is set, change the observation_type
    if params.get('too_mode', False) is True:
        requestgroup['observation_type'] = 'TIME_CRITICAL'

    return requestgroup


def make_many(params, ipp_value, request, cal_request):
    """Create a request for a MANY observation of the asteroidgroup
    target (<request>) and calibration source (<cal_request>)"""

    requestgroup = {
                    'submitter' : params['user_id'],
                    'requests'  : [request, cal_request],
                    'name'  : params['group_name'],
                    'observation_type': "NORMAL",
                    'operator'  : "MANY",
                    'ipp_value' : ipp_value,
                    'proposal'  : params['proposal_id']
    }

    return requestgroup


def make_proposal(params):
    proposal = {
                 'proposal_id': params['proposal_id'],
                 'user_id': params['user_id']
               }
    return proposal


def expand_cadence(user_request):

    cadence_url = urljoin(settings.PORTAL_REQUEST_API, 'cadence/')

    try:
        resp = requests.post(
            cadence_url,
            json=user_request,
            headers={'Authorization': 'Token {}'.format(settings.PORTAL_TOKEN)},
            timeout=120.0
         )
    except requests.exceptions.Timeout:
        msg = "Observing portal API timed out"
        logger.error(msg)
        return False, msg

    if resp.status_code not in [200, 201]:
        msg = "Cadence generation error"
        logger.error(msg)
        logger.error(resp.json())
        return False, resp.json()

    cadence_user_request = resp.json()

    return True, cadence_user_request


def make_cadence(request, params, ipp_value, debug=False):

    """Create a user_request for a cadence observation"""
    # Add cadence parameters into Request
    cadence = {
                'start' : datetime.strftime(params['start_time'], '%Y-%m-%dT%H:%M:%S'),
                'end'   : datetime.strftime(params['end_time'], '%Y-%m-%dT%H:%M:%S'),
                'period': params['period'],
                'jitter': params['jitter']
             }
    request = [{'cadence': cadence,
                'configurations': request['configurations'],
                'windows': [],
                'location': request['location'],
                }]

    user_request = {
                    'requests' : request,
                    'name' : params['group_name'],
                    'observation_type': "NORMAL",
                    'operator' : "SINGLE",
                    'ipp_value': ipp_value,
                    'proposal' : params['proposal_id']
                   }

# If the ToO mode is set, change the observation_type
    if params.get('too_mode', False) is True:
        user_request['observation_type'] = 'TIME_CRITICAL'

# Submit the UserRequest with the cadence
    status, cadence_user_request = expand_cadence(user_request)

    if debug and status is True:
        print('Cadence generated {} requests'.format(len(cadence_user_request['requests'])))
        i = 1
        for request in cadence_user_request['requests']:
            print('Request {0} window start: {1} window end: {2}'.format(
                i, request['windows'][0]['start'], request['windows'][0]['end']
            ))
            i += 1

    return cadence_user_request


def configure_defaults(params):

    site_list = { 'V37' : 'ELP',
                  'V39' : 'ELP',
                  'K91' : 'CPT',
                  'K92' : 'CPT',
                  'K93' : 'CPT',
                  'Q63' : 'COJ',
                  'Q64' : 'COJ',
                  'W85' : 'LSC',
                  'W86' : 'LSC',
                  'W87' : 'LSC',
                  'W89' : 'LSC',  # Code for aqwa-0m4a
                  'W79' : 'LSC',  # Code for aqwb-0m4a
                  'F65' : 'OGG',
                  'F65-FLOYDS' : 'OGG',
                  'E10' : 'COJ',
                  'E10-FLOYDS' : 'COJ',
                  'Z31' : 'TFN',
                  'Z24' : 'TFN',
                  'Z17' : 'TFN',
                  'Z21' : 'TFN',
                  'T03' : 'OGG',
                  'T04' : 'OGG',
                  'Q58' : 'COJ',  # Code for 0m4a
                  'Q59' : 'COJ',
                  'V38' : 'ELP',
                  'L09' : 'CPT'}  # Code for 0m4a

    params['pondtelescope'] = '1m0'
    params['observatory'] = ''
    try:
        params['site'] = site_list[params['site_code']]
    except KeyError:
        pass
    params['binning'] = 1
    params['instrument'] = '1M0-SCICAM-SINISTRO'

    # Perform Repeated exposures if many exposures compared to number of filter changes.
    if params['exp_count'] <= 10 or params['exp_count'] < 10*len(list(filter(None, params['filter_pattern'].split(',')))):
        params['exp_type'] = 'EXPOSE'
    else:
        params['exp_type'] = 'REPEAT_EXPOSE'

    if params['site_code'] in ['F65', 'E10', '2M0']:
        if 'F65' in params['site_code']:
            params['instrument'] = '2M0-SCICAM-MUSCAT'
        else:
            params['instrument'] = '2M0-SCICAM-SPECTRAL'
            params['binning'] = 2
        params['pondtelescope'] = '2m0'
        if params.get('spectroscopy', False) is True and 'FLOYDS' in params.get('instrument_code', ''):
            params['exp_type'] = 'SPECTRUM'
            params['instrument'] = '2M0-FLOYDS-SCICAM'
            params['binning'] = 1
            # params['ag_exp_time'] = 10
            if params.get('solar_analog', False) and len(params.get('calibsource', {})) > 0:
                params['calibsrc_exptime'] = params['calibsource']['calib_exptime']
            if params.get('filter', None):
                del(params['filter'])
            params['spectra_slit'] = 'slit_6.0as'
    elif params['site_code'] in ['Z17', 'Z21', 'W89', 'W79', 'T03', 'T04', 'Q58', 'Q59', 'V38', 'L09', '0M4']:
        params['instrument'] = '0M4-SCICAM-SBIG'
        params['pondtelescope'] = '0m4'
        params['binning'] = 1
# We are not currently doing Aqawan-specific binding for LSC (or TFN or OGG) but
# the old code is here if needed again
#        if params['site_code'] == 'W89':
#            params['observatory'] = 'aqwa'
#        if params['site_code'] == 'W79':
#            params['observatory'] = 'aqwb'
        if params['site_code'] == 'V38':
            # elp-aqwa-0m4a kb80
            params['observatory'] = 'aqwa'
    elif params.get('bin_mode', None) == '2k_2x2':
        params['binning'] = 2

    return params


def make_requestgroup(elements, params):

    params = configure_defaults(params)

# Create Location (site, observatory etc)
    location = make_location(params)
    logger.debug("Location=%s" % location)
# Create Target (pointing)
    if len(elements) > 0:
        logger.debug("Making a moving object")
        params['target'] = make_moving_target(elements)
        if 'sky_pa' in elements and params['para_angle'] is False:
            params['rot_mode'] = 'SKY'
            params['rot_angle'] = round(elements['sky_pa'], 1)
    else:
        logger.debug("Making a static object")
        params['target'] = make_target(params)
    logger.debug(f"Target={params['target']}")
# Create Window
    window = make_window(params)
    logger.debug("Window=%s" % window)
# Create Molecule(s)
    params['constraints'] = make_constraints(params)
    configurations = make_configs(params)

    submitter = ''
    submitter_id = params.get('submitter_id', '')
    if submitter_id != '':
        submitter = f'(by {submitter_id})'
    note = f'Submitted by NEOexchange {submitter}'
    note = note.rstrip()

    request = {
        'configurations': configurations,
        "acceptability_threshold": params.get('acceptability_threshold', 90),
        'windows': [window],
        'location': location,
        "observation_note": note,
    }

    if params.get('solar_analog', False) and len(params.get('calibsource', {})) > 0:
        # Assemble solar analog request
        params['group_name'] += "+solstd"
        params['source_id'] = params['calibsource']['name']
        params['ra_deg'] = params['calibsource']['ra_deg']
        params['dec_deg'] = params['calibsource']['dec_deg']
        if 'pm_ra' in params['calibsource']:
            params['pm_ra'] = params['calibsource']['pm_ra']
        if 'pm_dec' in params['calibsource']:
            params['pm_dec'] = params['calibsource']['pm_dec']
        params['target'] = make_target(params)
        # save target exposure settings
        exp_time = params['exp_time']
        exp_count = params['exp_count']
        ag_exptime = params.get('ag_exp_time', 10)
        # update exposure settings for analog and create configurations
        params['exp_time'] = params['calibsrc_exptime']
        params['exp_count'] = 1
        params['ag_exp_time'] = 10
        params['rot_mode'] = 'VFLOAT'
        cal_configurations = make_configs(params)
        # reinstate target exposure settings
        params['exp_time'] = exp_time
        params['exp_count'] = exp_count
        params['ag_exp_time'] = ag_exptime

        cal_request = {
                        "location": location,
                        "configurations": cal_configurations,
                        "windows": [window],
                        "observation_note": note,
                    }
    else:
        cal_request = {}

    ipp_value = params.get('ipp_value', 1.0)

# Add the Request to the outer User Request
    if 'period' in params.keys() and 'jitter' in params.keys():
        user_request = make_cadence(request, params, ipp_value)
    elif len(cal_request) > 0:
        user_request = make_many(params, ipp_value, request, cal_request)
    else:
        user_request = make_single(params, ipp_value, request)

    logger.info("User Request=%s" % user_request)

    return user_request


def submit_block_to_scheduler(elements, params):

    user_request = make_requestgroup(elements, params)

    # Errors or mostly blank dict came back from make_requestgroup(), probably cadence-related
    if user_request.get('errors', None):
        msg = user_request['errors']
        logger.error(msg)
        params['error_msg'] = msg
        return False, params
    elif 'name' not in user_request and 'proposal' not in user_request:
        error_msg = {}
        for x in user_request['requests']:
            if x != {}:
                for key, value in x.items():
                    error_msg[key] = value
            params['error_msg'] = error_msg
        return False, params

# Make an endpoint and submit the thing
    try:
        resp = requests.post(
            settings.PORTAL_REQUEST_API,
            json=user_request,
            headers={'Authorization': 'Token {}'.format(settings.PORTAL_TOKEN)},
            timeout=120.0
         )
    except requests.exceptions.Timeout:
        msg = "Observing portal API timed out"
        logger.error(msg)
        params['error_msg'] = msg
        return False, params

    if resp.status_code not in [200, 201]:
        logger.error(resp.json())
        # msg = "Parsing error"
        try:
            msg = resp.json()
        except AttributeError:
            try:
                msg = user_request['errors']
            except KeyError:
                try:
                    msg = user_request['proposal'][0]
                except KeyError:
                    msg = "Unable to decode response from Observing Portal"
        params['error_msg'] = msg
        logger.error(msg)
        return False, params

    response = resp.json()
    tracking_number = str(response.get('id', ''))

    request_items = response.get('requests', '')

    request_numbers = [_['id'] for _ in request_items]

    if not tracking_number or not request_numbers:
        msg = "No Tracking/Request number received"
        logger.error(msg)
        params['error_msg'] = msg
        return False, params

    request_types = {}
    if len(request_items) > 0:
        if 'configurations' in request_items[0]:
            request_types = dict([(str(r['id']), r['configurations'][0]['target']['type']) for r in request_items])
        else:
            request_types = dict([(r['id'], r['target']['type']) for r in request_items])
    request_windows = [r['windows'] for r in user_request['requests']]

    params['block_duration'] = sum([float(_['duration']) for _ in request_items])
    params['request_windows'] = request_windows
    params['request_numbers'] = request_types

    request_number_string = ", ".join([str(x) for x in request_numbers])
    logger.info("Tracking, Req number=%s, %s" % (tracking_number, request_number_string))

    return tracking_number, params


def fetch_filter_list(site, spec):
    """Fetches the filter list from the observation portal instruments endpoint"""

    siteid, encid, telid = MPC_site_code_to_domes(site)
    if '1m0' in telid.lower():
        camid = "1m0-SciCam-Sinistro"
    elif '0m4' in telid.lower():
        camid = "0m4-SciCam-SBIG"
    elif '2m0' in telid.lower():
        if spec:
            camid = "2m0-FLOYDS-SciCam"
        elif "OGG" in siteid.upper():
            camid = "2M0-SCICAM-MUSCAT"
        else:
            camid = "2m0-SciCam-Spectral"
    else:
        camid = ''

    if siteid == 'xxx':
        siteid = encid = telid = ''

    # Disable specific telescope check, use all telescopes of appropriate class at a site.
    encid = telid = ''

    request_url = (
        '{instruments_url}?site={site}&enclosure={enclosure}&telescope={telescope}&instrument_type={instrument_type}'
        '&only_schedulable=true'
    ).format(
        instruments_url=settings.PORTAL_INSTRUMENTS_URL,
        site=siteid.lower(),
        enclosure=encid.lower(),
        telescope=telid.lower(),
        instrument_type=camid
    )
    response = requests.get(request_url, timeout=20, verify=True)

    resp = {}
    if response.status_code in [200, 201]:
        resp = response.json()

    fetch_error = ''
    data_out = []
    if not resp:
        fetch_error = 'The {} at {} is not schedulable.'.format(camid, site)
    elif 'MUSCAT' in camid:
        data_out = ['gp', 'rp', 'ip', 'zp']
    else:
        data_out = parse_filter_file(resp, spec)
        if not data_out:
            fetch_error = 'Could not find any filters for the {} at {}'.format(camid, site)
    if fetch_error:
        logger.error(fetch_error)
    return data_out, fetch_error


def parse_filter_file(resp, spec):
    """Parses the returned json dictionary and pull out the list of approved filters
    """
    if spec is not True:
        filter_list = cfg.phot_filters
    else:
        filter_list = cfg.spec_filters

    site_filters = []
    for instrument_type_config in resp.values():
        try:
            filt_list = []
            for optical_elements in instrument_type_config['optical_elements'].values():
                for optical_element in optical_elements:
                    if optical_element['schedulable'] is True:
                        filt_list.append(optical_element['code'])
        except KeyError:
            filt_list = []
        for filt in filter_list:
            if filt in filt_list and filt not in site_filters:
                site_filters.append(filt)

    return site_filters


def fetch_taxonomy_page(page=None):
    """Fetches Taxonomy data to be compared against database."""

    if page is None:
        taxonomy_url = 'https://sbn.psi.edu/archive/bundles/ast_taxonomy/data/taxonomy10.tab'
        data_file = fetchpage_and_make_soup(taxonomy_url)
        # data_file = urllib.request.urlopen(taxonomy_url)
        data_out = parse_taxonomy_data(data_file)
    else:
        with open(page, 'r') as input_file:
            data_out = parse_taxonomy_data(input_file.read())
    return data_out


def parse_binzel_data(tax_text=None):
    """Parses the Binzel taxonomy database for targets and pulls a list
    of these targets back.
    """
    tax_table = []
    for line in tax_text:
        if line[0] != '#':
            line = line.split('\n')
            chunks = line[0].split(',')
            if chunks[0] == '':
                chunks[0] = chunks[2]
            row = [chunks[0], chunks[4], "B", "BZ04", chunks[10]]
            tax_table.append(row)
    return tax_table


def parse_taxonomy_data(tax_text=None):
    """Parses the online taxonomy database for targets and pulls a list
    of these targets back.
    PDS table has 125 characters/line (chunks = 16 once names/notes removed)
    SDSS table has 117 characters/line (chunks = 6 once names/extra removed)
    """

    tax_text = str(tax_text).replace("\r", '\n').split("\n")
    tax_text = list(filter(None, tax_text))

    tax_scheme = ['T',
                'Ba',
                'Td',
                'H',
                'S',
                'B',
                ['3T', '3B'],
                'BD',
                ]
    tax_table = []
    if len(tax_text[0]) == 117:
            offset = -1
    else:
        offset = 0
    for line in tax_text:
        number = line[:8+offset].strip()
        name = line[8+offset:25+offset].strip()
        prov = line[25+offset:37+offset].strip()
        end = line[103+offset*44:].strip()
        line = line[36+offset:103+offset*44]
        chunks = line.split(' ')
        chunks = list(filter(None, chunks))
        # parse Object ID=Object Number or Provisional designation if no number
        if number != '0':
            obj_id = number
        else:
            obj_id = prov
        # Build Taxonomy reference table.
        if len(chunks) == 6:
            out = '{}|{}|{}'.format(chunks[1], chunks[2], chunks[5])
            row = [obj_id, chunks[0], 'Sd', "SDSS", out]
            tax_table.append(row)
        elif len(chunks) == 16:
            index = range(0, 8)
            index = [2*x for x in index]+[13]
            for i in index:
                out = ' '
                if chunks[i] != '-':
                    if i == 12 or i == 13:
                        scheme = tax_scheme[6][i-12]
                    else:
                        if end[0] != '-':
                            out = chunks[i+1] + "|" + end
                        else:
                            out = chunks[i+1]
                        scheme = tax_scheme[i//2]
                    row = [obj_id, chunks[i], scheme, "PDS6", out]
                    tax_table.append(row)
    return tax_table


def fetch_smass_page():
    """Fetches the smass list of spectral targets"""

    smass_url = 'http://smass.mit.edu/catalog.php?sort=dat&mpcc=off&text=off'

    page = fetchpage_and_make_soup(smass_url)

    return page


def fetch_smass_targets(page=None, cut_off=None):
    """Parses the smass webpage for spectroscopy results and returns a list
    of these targets back along with links to data files.
    Takes either a BeautifulSoup page version of the SMASS target page (from
    a call to fetch_smass_page() - to allow  standalone testing) or  calls
    this routine and then parses the resulting page.
    """

    if type(page) != BeautifulSoup:
        page = fetch_smass_page()

    targets = []
    if type(page) == BeautifulSoup:
        # Find the table, make sure there is only one
        tables = page.find_all('table')
        if len(tables) != 1:
            logger.warning("Unexpected number of tables found on SMASS page (Found %d)" % len(tables))
        else:
            targets_table = tables[0]
            rows = targets_table.find_all('tr')
            if len(rows) > 1:
                for row in rows[2:]:
                    mpnum = row.find_all('td', class_="mpnumber")
                    provdes = row.find_all('td', class_="provdesig")
                    data = row.find_all('td', class_="datalinks")
                    ref = row.find_all('td', class_="refnumber last")
                    items = row.find_all('td')
                    if len(mpnum) > 0:
                        target_name = mpnum[0].text
                        target_name = target_name.strip()
                        if target_name == '':
                            target_name = provdes[0].text
                            target_name = target_name.strip()
                    t_wav = data[0].text
                    t_wav = t_wav.strip()
                    t_link = row.find_all('a')
                    t_link = t_link[0]['href']

                    if t_link.split('.')[-1] != 'txt':
                        if t_link.split('.')[-1] == 'tx':
                            t_link += 't'
                        else:
                            t_link += '.txt'
                    t_link = 'http://smass.mit.edu/' + t_link
                    if 'Vis' in t_wav:
                        v_link = t_link
                    else:
                        v_link = ''
                    if 'NIR' in t_wav:
                        i_link = t_link
                    else:
                        i_link = ''
                    date = items[-1].text
                    date = date.strip()
                    date = datetime.strptime(date, '%Y-%m-%d').date()
                    if cut_off and date < cut_off:
                        return targets
                    ref = ref[0].text
                    ref = ref.strip()
                    target_object = [target_name, t_wav, v_link, i_link, ref, date]
                    same_object = [row for row in targets if target_name == row[0] and t_wav == row[1]]
                    same_object = [item for sublist in same_object for item in sublist]
                    if same_object and date <= same_object[5]:
                        continue
                    elif same_object:
                        targets[targets.index(same_object)] = target_object
                    else:
                        targets.append(target_object)
    return targets


def fetch_manos_page():
    """Fetches the manos list of spectral targets"""
    # new manos site = http://manos.lowell.edu/observations/summary
    manos_url = 'http://manos.lowell.edu/observations/summary/statuses'
    page = fetchpage_and_make_soup(manos_url)

    return page


def fetch_manos_targets(page=None, cut_off=None):
    """Parses the manos webpage for spectroscopy results and returns a list
    of these targets back along with links to data files when present.
    Takes either a BeautifulSoup page version of the MANOS target page (from
    a call to fetch_manos_page() - to allow  standalone testing) or  calls
    this routine and then parses the resulting page.
    """

    if type(page) != BeautifulSoup:
        page = fetch_manos_page()

    targets = []

    if type(page) == BeautifulSoup:
        # Create list of dictionaries of manos data
        manos_data = eval(str(page).replace('true', 'True').replace('false', 'False'))['data']

        for datum in manos_data:
            if datum['ast_number'] != '-':
                target_name = datum['ast_number']
            else:
                target_name = datum['primary_designation']
            # skip if already ingested more recent data for target
            if any([target_name == target[0] for target in targets]):
                continue

            # Has MANOS collected Spectra?
            if datum['vis_spec'] is True and datum['nir_spec'] is True:
                target_wav = 'Vis+NIR'
            elif datum['vis_spec'] is True:
                target_wav = 'Vis'
            elif datum['nir_spec'] is True:
                target_wav = 'NIR'
            else:
                target_wav = "NA"

            # Does MANOS have links?
            if isinstance(datum['vis_spec_image'], str):
                vislink = datum['vis_spec_image'].replace('thumbs', datum['file_asteroid_vis_spec'])
                vislink = 'http://manos.lowell.edu' + vislink + '.jpg'
            else:
                vislink = ''
            if isinstance(datum['nir_spec_image'], str):
                nirlink = datum['nir_spec_image'].replace('thumbs', datum['file_asteroid_nir_spec'])
                nirlink = 'http://manos.lowell.edu' + nirlink + '.jpg'
            else:
                nirlink = ''

            # Date of update
            update = datetime.strptime(datum['last_updated'], '%Y-%m-%d').date()
            # Return new updates only (check current calendar year) unless told otherwise
            if cut_off and update < cut_off:
                return targets

            target_object = [target_name, target_wav, vislink, nirlink, 'MANOS Site', update]
            targets.append(target_object)
    return targets


def fetch_list_targets(list_targets):
    """Fetches targets from command line and/or text file and returns a list of targets"""

    new_target_list = []

    for obj_id in list_targets:
        if os.path.isfile(obj_id):
            with open(obj_id, 'r') as input_file:
                for line in input_file:
                    if '_' in line:
                        line = str(line).replace('_', ' ')
                    if ',' in line:
                        line = str(line).replace(',', '')
                    if '\n' in line:
                        line = str(line).replace('\n', '')
                    new_target_list.append(line)
            continue
        if '_' in obj_id:
            obj_id = str(obj_id).replace('_', ' ')
        new_target_list.append(obj_id)

    return new_target_list


def fetch_flux_standards(page=None, filter_optical_model=True, dbg=False):
    """Parses either the passed [page] or fetches the table of
    spectrophotometric flux standards from ESO's page at:
    https://www.eso.org/sci/observing/tools/standards/spectra/stanlis.html
    The page is parsed and a dictionary of the flux standards is returned with
    the key set to the name of the standard. This will then points to a sub-dictionary
    containing:
    *  ra_rad : J2000 Right Ascension (radians),
    * dec_rad : J2000 Declination (radians),
    *     mag : V magnitude,
    * sp_type : Spectral type,
    *   notes : Notes
    If [filter_optical_model] is True, then entries that have 'Mod' in the Notes,
    indicating that they only modelled (not observed) optical spectra, are removed
    from the results.
    """

    if page is None:
        flux_standards_url = 'https://www.eso.org/sci/observing/tools/standards/spectra/stanlis.html'
        page = fetchpage_and_make_soup(flux_standards_url)
        if not page:
            return None
    flux_standards = {}

    if type(page) == BeautifulSoup:
        tables = page.find_all('div', {"class" : "richtext text parbase section"})
        if len(tables) == 1:
            links = tables[0].find_all('a')
            for link in links:
                name = link.text.strip()
                if dbg:
                    print("Standard=", name)
                if link.next_sibling:
                    string = link.next_sibling.encode('ascii', 'ignore')
                    if dbg:
                        print(string)
                    nstart = 1
                    nstart, ra, status = S.sla_dafin(string, nstart)
                    if status == 0:
                        ra *= 15.0
                    else:
                        ra = None
                    nstart, dec, status = S.sla_dafin(string, nstart)
                    if status != 0:
                        dec = None
                    info = string[nstart-1:].rstrip().split()
                    mag = None
                    if len(info) >= 1:
                        try:
                            mag = float(info[0])
                        except ValueError:
                            mag = None
                    spec_type = ''
                    if len(info) >= 2:
                        spec_type = info[1].decode('utf-8', 'ignore')
                    notes = ''
                    if len(info) == 3:
                        notes = info[2].decode('utf-8', 'ignore')
                    if ra and dec and mag and ((notes != 'Mod.' and filter_optical_model is True) or filter_optical_model is False):
                        flux_standards[name] = { 'ra_rad' : ra, 'dec_rad' : dec,
                            'mag' : mag, 'spectral_type' : spec_type, 'notes' : notes}
        else:
            logger.warning("Unable to find table of flux standards in page")
    else:
        logger.warning("Passed page object was not a BeautifulSoup object")
    return flux_standards


def read_solar_standards(standards_file):

    standards = {}

    data = ascii.read(standards_file, format='fixed_width_no_header', names=('Name', 'RA', 'Dec', 'Vmag'), col_starts=(4, 25, 37, 49))
    for row in data:
        name = row['Name'].replace('Land', 'Landolt').replace('(SA) ', 'SA')
        nstart = 1
        nstart, ra, status = S.sla_dafin(row['RA'].replace(':', ' '), nstart)
        if status == 0:
            ra *= 15.0
        else:
            ra = None
        nstart = 1
        nstart, dec, status = S.sla_dafin(row['Dec'].replace(':', ' '), nstart)
        if status != 0:
            dec = None
        v_mag = row['Vmag']
        standards[name] = { 'ra_rad' : ra, 'dec_rad' : dec, 'mag' : v_mag, 'spectral_type' : 'G2V'}
    return standards


def fetch_jpl_physparams_altdes(body):
    """Function to fetch physical parameters, designations, source types, and subtypes from JPL Horizons (online)"""
    jpl_url_base = 'https://ssd-api.jpl.nasa.gov/sbdb.api'
    request_url = jpl_url_base + '?sstr={}&phys-par=Y&alt-des=Y&no-orbit=Y'.format(body.current_name())
    resp = requests.get(request_url, timeout=20, verify=True).json()

    return resp


def store_jpl_physparams(phys_par, body):
    """Function to store object physical parameters from JPL Horizons"""

    # parsing the JPL physparams dictionary
    for p in phys_par:
        if 'H' == p['name']:  # absolute magnitude
            p_type = 'H'
        elif 'G' == p['name']:  # magnitude (phase) slope
            p_type = 'G'
        elif 'diameter' in p['name']:  # diameter
            p_type = 'D'
        elif 'extent' in p['name']:  # extent
            continue
        elif 'GM' in p['name']:  # GM
            p_type = 'M'
        elif 'density' in p['name']:  # density
            p_type = 'R'
        elif 'rot_per' in p['name']:  # rotation period
            p_type = 'P'
        elif 'pole' in p['name']:  # pole direction
            p_type = 'O'
        elif 'albedo' in p['name']:  # geometric albedo
            p_type = 'ab'
        # Parameters available from JPL, but not explicitly stored by us at the moment.
        # TAL 2020/7/8: Thought about mapping M1,K1->H,G here but decided against
#        elif 'M1' == p['name']: # absolute magnitude of comet and coma (total)
#            p_type = 'H'
#        elif 'K1' == p['name']: # comet total magnitude slope parameter
#            p_type = 'G'
#        elif 'M2' == p['name']: # comet total magnitude parameter
#        elif 'K2' == p['name']: # comet nuclear magnitude slope parameter
#        elif 'PC' == p['name']: # comet nuclear magnitude law - phase coefficient
        elif 'spectral' in p['desc']:
            continue
        else:
            p_type = p['name']

        # Making sure we're storing float, not string
        try:
            jpl_value = float(p['value'])
        except (TypeError, ValueError):
            jpl_value = p['value']
        try:
            jpl_error = float(p['sigma'])
        except (TypeError, ValueError):
            jpl_error = p['sigma']

        # Splitting values that are connected values
        jpl_value2 = jpl_error2 = None

        if isinstance(jpl_value, str) and '/' in jpl_value:
            jpl_value, jpl_value2 = jpl_value.split('/')

        if isinstance(jpl_error, str) and '/' in jpl_error:
            jpl_error, jpl_error2 = jpl_error.split('/')

        # Build physparams dictionary
        phys_params = {'parameter_type': p_type,
                       'value': jpl_value,
                       'error': jpl_error,
                       'units': p.get('units', None),
                       'reference': p.get('ref', None),
                       'notes': p.get('notes', None),
                       'preferred': True
                       }

        # Change dictionary if color
        if 'color' in p.get('desc', ''):
            phys_params['color_band'] = p['title']
            del phys_params['parameter_type']
        else:
            phys_params['value2'] = jpl_value2
            phys_params['error2'] = jpl_error2

        saved = body.save_physical_parameters(phys_params)
        if saved:
            logger.info('New Physical Parameter saved for {}: {}'.format(body.current_name(), p.get('desc', 'unknown')))


def store_jpl_desigs(obj, body):
    """Function to store object name, number, and designations from JPL Horizons"""

    # parsing through JPL designations
    des_dict_list = parse_jpl_fullname(obj)

    des_alt = obj['des_alt']
    preferred = False
    if len(des_alt) >= 1:
        for d in des_alt:
            alt_des = None
            for des in d:
                if des == 'pri':
                    preferred = True
                    alt_des = d[des]
                elif des == 'des':
                    preferred = False
                    alt_des = d[des]
                elif des == 'rn':
                    continue
                elif des == 'yl':
                    continue

            if alt_des:
                prov_des_dict = {'value': alt_des,
                                 'desig_type': 'P',
                                 'preferred': preferred}
                des_dict_list.append(prov_des_dict)

    for D in des_dict_list:
        if D['value']:
            saved = body.save_physical_parameters(D)
            if saved:
                logger.info('New Designation saved for {}: {}'.format(body.current_name(), D['value']))


def parse_jpl_fullname(obj):
    """Given a JPL object, return parsed full name"""
    fullname = obj['fullname']
    number = name = prov_des = None
    if fullname[0] == '(':  # provisional designation only
        prov_des = fullname.strip('()')
    elif '/' in fullname:  # comet
        parts = fullname.split('/')
        if len(parts) == 2:
            part1 = parts[0]
            part2 = parts[1]
            if len(part1) == 1 and part1.isalpha():
                prov_des = fullname
            elif '(' in part1:
                part11, part12 = part1.split('(')
                name = part11.rstrip()
                prov_des = part12 + '/' + part2.strip('()')
            else:
                number = part1
            if '(' in part2:
                part21, part22 = part2.split('(')
                prov_des = part1 + '/' + part21.rstrip()
                name = part22.strip('()')
            elif number:
                name = part2
    elif ' ' in fullname:
        name_parts = list(filter(None, fullname.split(' ')))
        if len(name_parts) == 4:
            number = name_parts[0]
            if name_parts[1][0].isalpha:
                name = name_parts[1]
        elif len(name_parts) == 3:
            part1, part2, part3 = name_parts
            number = part1
        elif len(name_parts) == 2:
            part1, part2 = name_parts
            number = part1
            name = part2

    # designation dictionary
    des_dict_list = [{'value': number, 'desig_type': '#', 'preferred': True},
                     {'value': name, 'desig_type': 'N', 'preferred': True},
                     {'value': prov_des, 'desig_type': 'P', 'preferred': True}]
    return des_dict_list


def store_jpl_sourcetypes(code, obj, body):
    """Function to store object source types and subtypes from JPL Horizons"""

    source_type = source_subtype_1 = source_subtype_2 = None
    if 'CEN' in code:  # Centaur
        source_type = 'E'
    elif 'TJN' in code:  # Jupiter trojan
        source_type = 'T'
        source_subtype_1 = 'P5'
    elif 'TNO' in code:  # Trans-Neptunian Object
        source_type = 'K'
    elif 'IEO' in code:  # Atira
        source_subtype_1 = 'N1'
    elif 'ATE' in code:  # Aten
        source_subtype_1 = 'N2'
    elif 'APO' in code:  # Apollo
        source_subtype_1 = 'N3'
    elif 'AMO' in code:  # Amor
        source_subtype_1 = 'N4'
    elif 'IMB' in code:  # inner main belt
        source_subtype_1 = 'MI'
    elif 'MBA' in code:  # main belt
        source_subtype_1 = 'M'
    elif 'OMB' in code:  # outer main belt
        source_subtype_1 = 'MO'
    # No current way to tell if L4/L5 Trojan from JPL
#    if code is '##': # L4
#        source_subtype_1 = 'T4'
#    if code is '##': # L5
#        source_subtype_1 = 'T5'
    # We do not have category for "Mars Crossing Asteroid"
#    if code is 'MCA': # MCA = mars crossing asteroid
#        source_subtype_1 = 'P4'
    elif 'HYA' in code:  # hyperbolic asteroid
        source_subtype_1 = 'H'
    elif 'HYP' in code:  # hyperbolic comet
        source_subtype_1 = 'H'
    elif 'PAA' in code:  # parabolic asteroid
        source_subtype_1 = 'PA'
    elif 'PAR' in code:  # parabolic comet
        source_subtype_1 = 'PA'
    elif 'JFC' in code:  # Jupiter family comet P<20yrs
        source_subtype_1 = 'JF'
    elif 'JFc' in code:  # Jupiter family comet 2<Tjupiter<3
        source_subtype_1 = 'JF'
    elif 'HTC' in code:  # Halley type comet
        source_subtype_1 = 'HT'
    elif 'COM' in code:  # Long Period comet
        source_subtype_1 = 'LP'
    else:
        source_subtype_1 = None

    if obj['neo'] is True:
        source_type = body.source_type
        if not source_type:
            source_type = 'N'
        if obj['pha'] is True:
            source_subtype_2 = 'PH'
        if source_type != 'N':
            if not source_subtype_1:
                source_subtype_1 = 'N'
            elif not source_subtype_2:
                source_subtype_2 = 'N'

    if source_type:
        body.source_type = source_type
    body.source_subtype_1 = source_subtype_1
    body.source_subtype_2 = source_subtype_2
    body.save()



