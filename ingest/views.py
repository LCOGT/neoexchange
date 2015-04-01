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

from ingest.models import Body
from ingest.sources_subs import fetchpage_and_make_soup, packed_to_normal, fetch_mpcorbit
from ingest.time_subs import extract_mpc_epoch, parse_neocp_date
from datetime import datetime
import reversion
import logging
logger = logging.getLogger(__name__)


def home(request):
    return

def save_and_make_revision(body,kwargs):
    for k, v in kwargs.items():
        setattr(body, k, v)
        with reversion.create_revision():
            body.save()
    return

def update_NEOCP_orbit(obj_id, dbg=False):
    '''Query the MPC's showobs service with the specified <obj_id> and
    it will write the orbit found into the neox database.
    a) If the object does not have a response it will be marked as active = False
    b) If the object's parameters have changed they will be updated and a revision logged
    c) New objects get marked as active = True automatically 
    '''

    NEOCP_orb_url = 'http://scully.cfa.harvard.edu/cgi-bin/showobsorbs.cgi?Obj='+obj_id+'&orb=y'
    
    neocp_obs_page = fetchpage_and_make_soup(NEOCP_orb_url)
    
    if neocp_obs_page:
        obs_page_list = neocp_obs_page.text.split('\n')
    else:
        return False
    
# If the object has left the NEOCP, the HTML will say 'None available at this time.'
# and the length of the list will be 1
    body, created = Body.objects.get_or_create(provisional_name=obj_id)
    if len(obs_page_list) > 1:
        # Clean up the header and top line of input
        kwargs = clean_NEOCP_object(obs_page_list)
        if not created:
            # Find out if the details have changed, if they have, save a revision
            check_body = Body.objects.filter(provisional_name=obj_id, **kwargs)
            if check_body.count() == 1 and check_body[0] == body:
                save_and_make_revision(check_body[0],kwargs)
                logger.info("Updated %s" % obj_id)
        else:
            save_and_make_revision(body,kwargs)
            logger.info("Added %s" % obj_id)
    else:
        save_and_make_revision(check_body,{'active':False})
        logger.info("Object %s no longer exists on the NEOCP." % obj_id)
    return True

def clean_NEOCP_object(page_list):
    '''Parse response from the MPC NEOCP page making sure we only return 
    parameters from the 'NEOCPNomin' (nominal orbit)'''
    current = False
    if page_list[0] == '':
        page_list.pop(0)
    if page_list[0][:6] == 'Object':
        page_list.pop(0)
    for line in page_list:
        if 'NEOCPNomin' in line:
            current = line.split()
            break
    if current:
        params = {
                'epochofel'     : extract_mpc_epoch(current[3]),
                'meananom'      : current[4],
                'argofperih'    : current[5],
                'longascnode'   : current[6],
                'orbinc'        : current[7],
                'eccentricity'  : current[8],
                'meandist'      : current[10],
                'source_type'   : 'U',
                'elements_type' : 'MPC_MINOR_PLANET',
                'active'        : True,
                'origin'        : 'M',
                }
    else:
        params = []
    return params

def update_crossids(astobj, dbg=False):
    '''Update the passed <astobj> for a new cross-identification.
    <astobj> is expected to be a list of:
    provisional id, final id/failure reason, reference, confirmation date
    normally produced by the fetch_previous_NEOCP_desigs() method.'''

    if len(astobj) != 4:
        return False

    obj_id = astobj[0].rstrip()

    body, created = Body.objects.get_or_create(provisional_name=obj_id)
    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_crossid(astobj, dbg)
    if not created:
        if dbg: print "Did not create new Body"
        # Find out if the details have changed, if they have, save a revision
        check_body = Body.objects.filter(provisional_name=obj_id, **kwargs)
        if check_body.count() == 1 and check_body[0] == body:
            save_and_make_revision(check_body[0],kwargs)
            logger.info("Updated cross identification for %s" % obj_id)
    else:
        # Didn't know about this object before so create but make inactive
        kwargs['active'] = False
        save_and_make_revision(body,kwargs)
        logger.info("Added cross identification for %s" % obj_id)
    return True


def clean_crossid(astobj, dbg=False):

    confirm_date = parse_neocp_date(astobj[3])
    obj_id = astobj[0].rstrip()
    desig = astobj[1]
    reference = astobj[2]

    active = True
    if obj_id != '' and desig == 'wasnotconfirmed':
        # Unconfirmed, no longer interesting so set inactive
        objtype = 'U'
        desig = ''
        active = False
    elif obj_id != '' and desig == 'doesnotexist':
        # Did not exist, no longer interesting so set inactive
        objtype = 'X'
        desig = ''
        active = False
    elif obj_id != '' and desig != '':
        # Confirmed
        if 'CBET' in reference:
            # There is a reference to an CBET so we assume it's "very
            # interesting" i.e. a comet
            objtype = 'C'
        elif 'MPEC' in reference:
            # There is a reference to an MPEC so we assume it's
            # "interesting" i.e. an NEO
            objtype = 'N'
        else:
            objtype = 'A'

    params = { 'source_type'  : objtype,
               'name'         : desig,
               'active'       : active
             }
    if dbg: print "%07s->%s (%s) %s" % ( obj_id, params['name'], params['source_type'], params['active'])

    return params

def clean_mpcorbit(elements, dbg=False, origin='M'):
    '''Takes a list of (proto) element lines from fetch_mpcorbit() and plucks
    out the appropriate bits. origin defaults to 'M'(PC) if not specified'''

    params = {}
    if elements != None:
        params = {
                'epochofel'     : datetime.strptime(elements['epoch'].replace('.0', ''), '%Y-%m-%d'),
                'meananom'      : elements['mean anomaly'],
                'argofperih'    : elements['argument of perihelion'],
                'longascnode'   : elements['ascending node'],
                'orbinc'        : elements['inclination'],
                'eccentricity'  : elements['eccentricity'],
                'meandist'      : elements['semimajor axis'],
                'source_type'   : 'A',
                'elements_type' : 'MPC_MINOR_PLANET',
                'active'        : True,
                'origin'        : origin,
                }
    return params

    
def update_MPC_orbit(obj_id, dbg=False, origin='M'):

    elements = fetch_mpcorbit(obj_id, dbg)

    body, created = Body.objects.get_or_create(name=obj_id)
    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_mpcorbit(elements, dbg, origin)
    if not created:
        if dbg: print "Did not create new Body"
        # Find out if the details have changed, if they have, save a revision
        check_body = Body.objects.filter(name=obj_id, **kwargs)
        if check_body.count() == 1 and check_body[0] == body:
            save_and_make_revision(check_body[0],kwargs)
            logger.info("Updated elements for %s" % obj_id)
    else:
        # Didn't know about this object before so create 
        save_and_make_revision(body,kwargs)
        logger.info("Added new orbit for %s" % obj_id)
    return True
