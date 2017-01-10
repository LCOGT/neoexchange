from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.forms.models import model_to_dict

from astrometrics.sources_subs import fetch_yarkovsky_targets
from astrometrics.ephem_subs import monitor_long_term_scheduling
from core.models import Body


class Command(BaseCommand):
    help = 'Compute dates when Yarkovsky & radar/ARM targets are observable for the next 30 days'

    def add_arguments(self, parser):
        parser.add_argument('site_code', help='MPC site code')
        parser.add_argument('targets', nargs='+', help='Targets to schedule')
        parser.add_argument('--start_date', default=datetime.utcnow().strftime('%Y-%m-%d'), help='Date to start ephemeris search in %Y-%m-%d format')
        parser.add_argument('--date_range', type=int, default=30, help='Date range ephemeris search in days')

    def handle(self, *args, **options):
        self.stdout.write("==== Computing scheduling dates %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.stdout.write("========================")
        target_list = fetch_yarkovsky_targets(options['targets'])
        for obj_id in target_list:
            orbelems = model_to_dict(Body.objects.get(name=obj_id))
            visible_dates, emp_visible_dates, dark_and_up_time_all, max_alt_all = monitor_long_term_scheduling(options['site_code'], orbelems, datetime.strptime(options['start_date'], '%Y-%m-%d'), options['date_range'])
            self.stdout.write("Reading target %s" % obj_id)
            self.stdout.write("Visible dates:")
            for date in visible_dates:
                print date
            self.stdout.write("Start of night ephemeris entries for %s:" % options['site_code'])
            for emp in emp_visible_dates:
                print emp
            self.stdout.write("Maximum altitudes:")
            x = 0
            for alt in max_alt_all:
                print emp_visible_dates[x][0][0:10], ":", alt
                x += 1
            self.stdout.write("Number of hours target is up and sky is dark:")
            x = 0
            for time in dark_and_up_time_all:
                print emp_visible_dates[x][0][0:10], ":", round(time, 2)
                x += 1
            self.stdout.write("========================")

