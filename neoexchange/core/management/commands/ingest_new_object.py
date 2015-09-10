'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2015-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from sys import argv
import os

from core.models import Body
from core.views import clean_NEOCP_object, save_and_make_revision
from astrometrics.sources_subs import packed_to_normal
import logging

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ingest new objects from a local NEOCP 1-line file produced by e.g. find_orb'

    def add_arguments(self, parser):
        parser.add_argument('rockfile', nargs='+', type=str)

    def handle(self, *args, **options):
        new_rock = options['rockfile'][0]
        try:
            orbfile_fh = open(new_rock, 'r')
        except IOError:
            self.stdout.write("File %s not found" % new_rock)
            return

        orblines = orbfile_fh.readlines()

        orblines[0] = orblines[0].replace('Find_Orb  ', 'NEOCPNomin')
        dbg_msg = orblines[0]
        self.stdout.write(dbg_msg)
        kwargs = clean_NEOCP_object(orblines)
        if kwargs != {}:
            obj_file = os.path.basename(new_rock)
            file_chunks = obj_file.split('.')
            if len(file_chunks) == 2:
                obj_id = file_chunks[0].strip()
                if obj_id != kwargs['provisional_name']:
                    msg = "Mismatch between filename (%s) and provisional id (%s).\nAssuming provisional id is a final designation." % (obj_id, kwargs['provisional_name'])
                    self.stdout.write(msg)
                    kwargs['name'] = packed_to_normal(kwargs['provisional_name'])
                    kwargs['provisional_name'] = obj_id
                    kwargs['source_type'] = 'D'
            else:
                obj_id = kwargs['provisional_name']
 
            body, created = Body.objects.get_or_create(provisional_name=obj_id)

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
                msg = "Added new local target %s" % obj_id

            self.stdout.write(msg)
