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
import BeautifulSoup as bs

def fetchpage_and_make_soup(url, fakeagent=False, dbg=False):
    '''Fetches the specified URL from <url> and parses it using BeautifulSoup.
    If <fakeagent> is set to True, we will pretend to be a Firefox browser on
    Linux rather than as Python-urllib (in case of anti-machine filtering)
    
    Returns the page as a BeautifulSoup object if all was OK or None if the 
    page retrieval failed.'''

    req_headers = {}
    if fakeagent == True:
        req_headers = { 'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0",
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
    page  = bs.BeautifulSoup(neo_page)

    return page

    
def fetch_previous_NEOCP_desigs(dbg=False):
    '''Fetches the "Previous NEO Confirmation Page Objects" from the MPC, parses
    it and returns a list of lists of object, provisional designation or failure
    reason, date and MPEC.'''
    
    previous_NEOs_url='http://www.minorplanetcenter.net/iau/NEO/ToConfirm_PrevDes.html'
    
    page = fetchpage_and_make_soup(previous_NEOs_url)
    if page == None:
        return None

    divs = page.findAll('div', id="main")
    
    crossids = []
    for row in divs[0].findAll('li'):
        items = row.contents
        if dbg: print items,len(items)
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
                provid = provid_date[0].replace(' = ','')
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
        if crossmatch !=  ['', '', '', '']:
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
    neocp_objects = neocp_page.findAll('input', attrs = {"name" : "obj"})

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
                obs_page_line = "%80s" % ( line )
                print >> neo_cand_fh, obs_page_line
            neo_cand_fh.close()
            lines_written =  len(obs_page_list)
            print "Wrote",lines_written,"MPC lines to",neocand_filename
        else:
            print "File",neocand_filename,"already exists, not overwriting."
            
    else:
        print "Object",obj_id,"no longer exists on the NEOCP."

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

        print "Will save files in", savedir
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
            print "Wrote",orbit_lines_written,"orbit lines to",neocand_filename
        else:
            print "File",neocand_filename,"already exists, not overwriting."
            
    else:
        print "Object",obj_id,"no longer exists on the NEOCP."

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
