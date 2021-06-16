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

from datetime import datetime
from os.path import expanduser

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db import close_old_connections
from django.forms.models import model_to_dict

from astrometrics.sources_subs import fetch_yarkovsky_targets
from astrometrics.ephem_subs import monitor_long_term_scheduling
from core.models import Body


class Command(BaseCommand):
    help = 'Compute dates when Yarkovsky & radar/ARM targets are observable for the next 30 days'

    def add_arguments(self, parser):
        parser.add_argument('site_code', help='MPC site code')
        parser.add_argument('dark_and_up_time_limit', type=float, help='Amount of time sky must be dark and target is above the horizon')
        parser.add_argument('targets', nargs='*', help='Targets to schedule')
        parser.add_argument('--targetlist', action="store", default=None, help="File of targets to read (optional; set to 'FTP' to read from JPL site)")
        parser.add_argument('--start_date', default=datetime.utcnow().strftime('%Y-%m-%d'), help='Date to start ephemeris search in YYYY-MM-DD format')
        parser.add_argument('--date_range', type=int, default=30, help='Date range ephemeris search in days')

    def handle(self, *args, **options):
        self.stdout.write("==== Computing scheduling dates %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.stdout.write("========================")
        targets = []
        target_list = []
        if options['targetlist'] is not None:
            if options['targetlist'] == 'FTP':
                targets = None
            elif options['targetlist'].startswith('ftp://'):
                targets = options['targetlist']
            else:
                with open(expanduser(options['targetlist'])) as f:
                    targets = f.readlines()

            target_list = fetch_yarkovsky_targets(targets)
        target_list += options['targets']
        self.stdout.write("Combined target list")
        self.stdout.write("\n".join(target_list))
        self.stdout.write("========================")
        for obj_id in target_list:
            try:
                target = Body.objects.get(name=obj_id)
            except Body.MultipleObjectsReturned:
                target = Body.objects.get(name=obj_id, active=True)
            orbelems = model_to_dict(target)
            visible_dates, emp_visible_dates, dark_and_up_time_all, max_alt_all = monitor_long_term_scheduling(options['site_code'], orbelems, datetime.strptime(options['start_date'], '%Y-%m-%d'), options['date_range'], options['dark_and_up_time_limit'])
            self.stdout.write("Reading target %s" % obj_id)
            self.stdout.write("Visible dates:")
            for date in visible_dates:
                print(date)
            self.stdout.write("Start of night ephemeris entries for %s:" % options['site_code'])
            if len(emp_visible_dates) > 0:
                self.stdout.write('  Date/Time (UTC)        RA              Dec        Mag     "/min    P.A.    Alt Moon Phase Moon Dist Moon Alt Score  H.A.')
            for emp in emp_visible_dates:
                print(emp)
            self.stdout.write("Maximum altitudes:")
            x = 0
            for alt in max_alt_all:
                print(emp_visible_dates[x][0][0:10], ":", alt)
                x += 1
            self.stdout.write("Number of hours target is up and sky is dark:")
            x = 0
            for time in dark_and_up_time_all:
                print(emp_visible_dates[x][0][0:10], ":", round(time, 2))
                x += 1
            self.stdout.write("========================")
            close_old_connections()
