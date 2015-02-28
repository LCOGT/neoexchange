'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

update_crossids.py -- Fetch the MPC Previous NEO Confirmation Page and update 
DB entries for their new status.

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
from datetime import datetime, timedelta
from ingest.sources_subs import fetch_previous_NEOCP_desigs
from ingest.time_subs import parse_neocp_date

# Need to set this so Django can find its settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
from ingest.models import Body, check_object_exists

# Fetch Previous NEOCP webpage and parse

object_list = fetch_previous_NEOCP_desigs()

for astobj in object_list:
    
    confirm_date = parse_neocp_date(astobj[3])

    objname = astobj[0].rstrip()
    desig = astobj[1]
    reference = astobj[2]
    print objname, desig, reference
    obj_found = check_object_exists(objname)

    if obj_found !=0:
        # We have the object...
    	print "Object found"
    	print str(astobj) + ' ' + str(confirm_date)
	if objname != '' and desig == 'wasnotconfirmed':
            # Unconfirmed
    	    objtype = 'U'
	    desig = ''
	elif objname != '' and desig == 'doesnotexist':
	    objtype = 'X'
	    desig = ''
	elif objname != '' and desig != '':
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
      	print objtype
    	try:
    	    crossid = Body.objects.get(provisional_name__contains=objname)  
	except Body.MultipleObjectsReturned:
	    print "Multiple cross-ids found, shouldn't happen..."
	except Body.DoesNotExist:
    	    print "Object now not found, shouldn't happen..."
	else:
	    print "Adding cross-identification"
            # Insert new cross-identification into DB
	    crossid.name = desig
            crossid.source_type = objtype

            # XXX We currently have nowhere to store the reference (e.g. MPEC) 
            # or the confirm date but we probably should...
	    ## crossid.reference = reference,
	    ## crossid.confirm_date = confirm_date
	    crossid.save()
    else:
    	print "Object not found"
