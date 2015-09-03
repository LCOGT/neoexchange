import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'neox.settings'
from sys import argv

from core.models import Body
from core.views import clean_NEOCP_object, save_and_make_revision
import logging

logger = logging.getLogger(__name__)

if len(argv) == 2:
    new_rock = argv[1]
else:
    print "Wrong usage"
    exit(-1)


if not os.path.isfile(new_rock):
    print "File",new_rock,"not found"
    exit(-2)

orbfile_fh = open(new_rock, 'r')
orblines = orbfile_fh.readlines()

orblines[0] = orblines[0].replace('Find_Orb  ', 'NEOCPNomin')
print orblines
kwargs = clean_NEOCP_object(orblines)
print kwargs
if kwargs != {}:
    obj_id = kwargs['provisional_name']
    body, created = Body.objects.get_or_create(provisional_name=obj_id)
    print   body, created  
    if not created:
        # Find out if the details have changed, if they have, save a
        # revision
        check_body = Body.objects.filter(**kwargs)
        if check_body.count() == 0:
            if save_and_make_revision(body, kwargs):
                msg = "Updated %s" % obj_id
            else:
                msg = "No changes saved for %s" % obj_id
        else:
            msg = "No changes needed for %s" % obj_id
    else:
        save_and_make_revision(body, kwargs)
        msg = "Added %s" % obj_id

    print msg
