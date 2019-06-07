"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.forms.models import model_to_dict
from django.contrib.contenttypes.models import ContentType

from core.views import return_fields_for_saving
from core.models import Body
from reversion.models import Version
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update objects for new cross-identifications from the Previous NEO Confirmation Page Objects page'

    def handle(self, *args, **options):
        self.stdout.write("==== Removing Bad Revisions %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        minorbody_ct = ContentType.objects.get(app_label='core', model='body')
        self.stdout.write("==== Found content_type=%d for Body ====" % minorbody_ct.id)
        bodies = Version.objects.filter(content_type=minorbody_ct.id).values('object_id').annotate(sum=Count('id')).order_by('-sum')
        num_d = 0
        num_s = 0
        self.stdout.write("==== Found {} Bodies ====".format(bodies.count()))
        for body in bodies:
            try:
                logger.debug('*** Inspecting Body ID {} ***'.format(body['object_id']))
                versions = Version.objects.filter(object_id=body['object_id']).order_by('revision__date_created')
            except Exception, e:
                logger.error("Problem with body: {}".format(e))
                continue
            if versions.count() <= 2:
                continue
            original = versions.first()
            for version in versions[1:]:
                update = False
                fields = return_fields_for_saving()
                try:
                    vers_dict = version.field_dict
                    orig_dict = original.field_dict
                except Exception, e:
                    logger.error("Problem with body: {}".format(e))
                    continue
                # Check if the values in the original are the same as the revision
                for k in fields:
                    try:
                        if vers_dict[k] != orig_dict[k]:
                            update = True
                    except KeyError, e:
                        logger.debug('Error with {}'.format(e))
                if update:
                    original = version
                    #logger.debug('Saved version {}'.format(version.id))
                    num_s += 1
                else:
                    #logger.debug('Deleted version {}'.format(version.id))
                    version.revision.delete()
                    version.delete()
                    num_d += 1
        logger.debug("Updated: {} bodies".format(bodies.count()))
        logger.debug("Deleted: {} revisions".format(num_d))
        logger.debug("Saved: {} revisions".format(num_s))
