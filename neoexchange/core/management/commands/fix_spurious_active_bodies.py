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

from core.models import Body

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime
import reversion

class Command(BaseCommand):
    help = 'Find out when all currently active bodies became active and reset them'

    def add_arguments(self, parser):
        parser.add_argument('-r','--reset', action="store_true")

    def handle(self, *args, **options):
        for body in Body.objects.filter(active=True):
            version_list = reversion.get_for_object(body)
            lastversion = None
            for version in version_list:
                version_data = version.field_dict
                if lastversion:
                    revision_datestamp = str(lastversion.revision.date_created)[0:10]
                # We know something funny happened on 1 Jan 2016
                if lastversion and version_data['active'] != lastversion.field_dict['active'] and revision_datestamp=="2016-01-01":
                    self.stdout.write("%s changed between %s and %s" % (body.current_name(), version.revision.date_created, lastversion.revision.date_created))
                    if options['reset']:
                        # Only reset the values if the option asks for a reset
                        body.active = False
                        body.save()
                        self.stdout.write("Reset %s to inactive" % body.current_name())
                        break
                lastversion = version
            lastversion = None

        return
