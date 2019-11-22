"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2019-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from datetime import datetime, timedelta
from core.models import Body
from core.views import update_jpl_phys_params, get_characterization_targets()
import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update Observations and elements. Use no arguments to update all Characterization Targets'

    def add_arguments(self, parser):
        parser.add_argument('target', type=str, nargs='?', default=None, help='Target to update (enter Provisional Designations w/ an underscore, i.e. 2002_DF3)')

    def handle(self, *args, **options):

        if options['target']:
            obj_id = str(options['target']).replace('_', ' ')
            bodies = Body.objects.filter(Q(name=obj_id) | Q(provisional_name=obj_id))
        else:
            bodies = get_characterization_targets()

        i = 0
        for body in bodies:
            self.stdout.write("{} ==== Updating {} ==== ({} of {}) ".format(datetime.now().strftime('%Y-%m-%d %H:%M'), body.current_name(), i+1, len(bodies)))
            update_jpl_phys_params(body)
            i += 1
