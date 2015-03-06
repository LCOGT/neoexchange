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
from ingest.sources_subs import fetchpage_and_make_soup, packed_to_normal
from ingest.time_subs import extract_mpc_epoch
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
                save_and_make_revision(check_body,kwargs)
                logger.info("Updated %s" % obj_id)
        else:
            save_and_make_revision(body,kwargs)
            logger.info("Added %s" % obj_id)
    else:
        save_and_make_revision(check_body,{'active':False})
        logger.info("Object %s no longer exists on the NEOCP." % obj_id)
    return True

def clean_NEOCP_object(page_list):
    # Parse response from the MPC NEOCP page making sure we only return parameters from the 'NEOCPNomin' (nominal orbit)
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

