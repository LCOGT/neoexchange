"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

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
from core.models import Body
from astrometrics.sources_subs import fetch_jpl_physparams_altdes


class Command(BaseCommand):
    help = 'Update Observations and elements. Use no arguments to update all Characterization Targets'

    def add_arguments(self, parser):
        parser.add_argument('target', type=str, nargs='?', default=None, help='Target to update (enter Provisional Designations w/ an underscore, i.e. 2002_DF3)')

    def handle(self, *args, **options):
        
        if options['target']:
            obj_id = str(options['target']).replace('_', ' ')
            bodies = Body.objects.filter(name=obj_id)
        else:
            bodies = Body.objects.filter(active=True).exclude(origin='M')
        
        body = bodies[0]
           
        fetch_jpl_physparams_altdes(body)
        
        resp = fetch_jpl_physparams_altdes(body)
        
        store_jpl_physparams(resp['phys_par'], body)
        store_jpl_desigs(resp['object'], body)
        store_jpl_sourcetypes(resp['object']['orbit_class']['code'], body)    
        
       
        phys_param_results = body.get_physical_parameters()
        print(phys_param_results)


