import os
from datetime import datetime, timedelta
from sources_subs import fetch_previous_NEOCP_desigs
from time_subs import parse_neocp_date

# Need to set this so Django can find its settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'neosite.settings'
from neosite.neositeapp.models import ObsBlock, Crossident, check_object_exists

# Fetch Previous NEOCP webpage and parse

object_list = fetch_previous_NEOCP_desigs()

for astobj in object_list:
    
    confirm_date = parse_neocp_date(astobj[3])

    objname = astobj[0].rstrip()
    desig = astobj[1]
    reference = astobj[2]
    print objname, desig
    obj_found = check_object_exists(objname)

    if obj_found !=0:
# We (tried to) observed the object...
    	print "Object found"
    	print str(astobj) + ' ' + str(confirm_date)
	if objname != '' and desig == 'wasnotconfirmed':
# Unconfirmed
    	    objtype = 'UNCONFIRMED'
	    desig = ''
	elif objname != '' and desig == 'doesnotexist':
	    objtype = 'DID NOT EXIST'
	    desig = ''
	elif objname != '' and desig != '':
# Confirmed
	    if 'CBET' in reference:
# There is a reference to an CBET so we assume it's "very interesting" i.e. a comet
    	    	objtype = 'COMET'
	    elif 'MPEC' in reference:
# There is a reference to an MPEC so we assume it's "interesting" i.e. an NEO
    	    	objtype = 'NEO'
	    else:
	    	objtype = 'non NEO'	    
      	print objtype
    	try:
    	    crossid = Crossident.objects.get(original_desig__contains=objname)  
	except Crossident.MultipleObjectsReturned:
	    print "Multiple cross-ids found, shouldn't happen..."
	except Crossident.DoesNotExist:
# Insert new cross-identification into DB
	    new_crossid = Crossident(original_desig = objname,
	    	    	    	     final_desig = desig,
				     objtype = objtype,
				     reference = reference,
				     confirm_date = confirm_date)
	    new_crossid.save()
	else:
	    print "Already cross-identified"
    else:
    	print "Object not found"
