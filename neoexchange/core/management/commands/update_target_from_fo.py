"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2024 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from astrometrics.ephem_subs import convert_findorb_elements
from core.views import save_and_make_revision
from core.models import Body


class Command(BaseCommand):
    help = 'Update elements from a manual find_orb fit.'

    def add_arguments(self, parser):
        default_path = os.path.join(os.path.expanduser('~'), '.find_orb', 'elem_short.json')
        parser.add_argument('elements_file', type=str, nargs='?', default=default_path, help='Path to elem_short.json file')
        parser.add_argument('--target', action="store", default='', help='Name for object (overrides that found in elements; enter Provisional Designations w/ an underscore, i.e. 2002_DF3)')

    def handle(self, *args, **options):
        obj_id = None
        if options['target']:
            obj_id = str(options['target']).replace('_', ' ')
            body = Body.objects.get(name=obj_id)

        self.stdout.write(f"Reading elements from: {options['elements_file']}")
        if os.path.exists(options['elements_file']):
            with open(options['elements_file'], 'r') as fp:
                elements_json = json.load(fp)
            new_elements = convert_findorb_elements(elements_json)
            if len(new_elements) > 0:
                if obj_id is None:
                    obj_id = new_elements["name"]
                    body = Body.objects.get(name=obj_id)
                    self.stdout.write(f"Determined name= {obj_id}")
                if body:
                    # Overwrite origin with original or LCO
                    new_elements['origin'] = body.origin or 'L'
                    self.stdout.write(f"Updating Body # {body.id} ({obj_id}/{body.current_name()})")
                    # Show elements that are being changed
                    self.stdout.write("{")
                    for key, new_value in new_elements.items():
                        out_str = f"    {key}: "
                        if getattr(body, key) != new_value:
                            out_str += f"{getattr(body, key)} - > {new_value}"
                        else:
                            out_str += "No change"
                        self.stdout.write(out_str)
                    self.stdout.write("}")
                    updated = save_and_make_revision(body, new_elements)
                    if updated:
                        self.stdout.write("Successfully updated Body")
            else:
                self.stdout.write("Unable to parse elements for updating Body")
        else:
            self.stdout.write("Couldn't open file.")
