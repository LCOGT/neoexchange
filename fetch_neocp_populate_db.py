'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

fetch_neocp_populate_db.py -- Fetch the MPC NEO Confirmation Page and populate 
DB.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import os
from ingest.sources_subs import fetch_NEOCP, fetch_NEOCP_orbit
from datetime import datetime, tzinfo
from pytz import timezone
# Need to set this so Django can find its settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
from ingest.models import Body
from rise_set.moving_objects import read_neocp_orbit

dbg = True
savedir = os.path.join('/tmp', 'neoexchange')

def insert_new_object(elements):
    '''Creates new Body entries in the DB from the passed element dictionary if
    the object doesn't exist already'''

    status = -1
    try:
        Body.objects.get(provisional_name__exact=elements['name'])
    except Body.MultipleObjectsReturned:
        print "Multiple objects found, shouldn't happen..."
    except Body.DoesNotExist:
# Insert new body into DB

        new_object = Body(provisional_name = elements['name'],
                          origin           = elements['origin'],
                          source_type      = elements['source_type'],
                          elements_type    = elements['type'],
                          active           = False, # Actively following?
                          fast_moving      = False, # Is this object fast?
                          urgency          = 1,     # how urgent is this?
                          epochofel        = elements['epoch'],
                          orbinc           = elements['inclination'].in_degrees(),
                          longascnode      = elements['long_node'].in_degrees(),
                          argofperih       = elements['arg_perihelion'].in_degrees(),
                          eccentricity     = elements['eccentricity'],
                          meandist         = elements['semi_axis'],
                          meananom         = elements['mean_anomaly'].in_degrees(),
                          ingest           = datetime.utcnow().replace(tzinfo=timezone('UTC'))
                    )      
        new_object.save()
        status = 0

    return status
    
# Fetch down a list of objects from the MPC's NEO Confirmation Page
object_list = fetch_NEOCP()

if dbg: print object_list
# Loop over objects, fetch the orbit from the MPC's NEO Confirmation Page links 
# and insert into DB
for astobj in object_list:
# Fetch the orbit file for the candidate, which returns 0 if no lines of orbit 
# data were read (object is no longer on the NEOCP)
    num_read = fetch_NEOCP_orbit(astobj, savedir, delete=True)
    
    if num_read != 0:
        neocp_orbit_file = os.path.join(savedir, astobj+ '.neocp')
# Read the orbit file from disk (should bypass and read direct) and get back
# an element dictionary
        elements = read_neocp_orbit(neocp_orbit_file)
# Set the source type to be 'U'nknown (NEO candidate) and the origin to be 'M'PC
        elements['source_type'] = 'U' # NEO candidate
        elements['origin'] = 'M' # MPC
        if dbg: print elements
        insert_status = insert_new_object(elements)
