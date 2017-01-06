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

    def handle(self, *args, **options):
        self.stdout.write("==== Computing scheduling dates %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))
        target_list = fetch_yarkovsky_targets(options['targets'])
        for obj_id in target_list:
            orbelems = model_to_dict(Body.objects.get(name=obj_id))
            visible_dates, emp_visible_dates = monitor_long_term_scheduling(options['site_code'], orbelems)
            self.stdout.write("Reading target %s" % obj_id)
            self.stdout.write("Visible dates:")
            for date in visible_dates:
                print date
            self.stdout.write("Start of night ephemeris entries for %s:" % (options['site_code']))
            for emp in emp_visible_dates:
                print emp

