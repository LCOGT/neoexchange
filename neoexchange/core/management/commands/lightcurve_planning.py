"""
Generates a phased planning plot for future LC Observations
"""

from core.models import Body
from astrometrics.ephem_subs import compute_ephem
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.forms.models import model_to_dict


class Command(BaseCommand):

    help = 'Plan LC Observations for a given object.'

    def add_arguments(self, parser):
        parser.add_argument('body_name', type=str, help='Body name to plan for')

    def break_data(self, dates, phases, site):
        day_list = list(set(dates))
        print(len(day_list))

    def handle(self, *args, **options):
        body_name = options['body_name']
        period = 5.2
        alt_limit = 30
        body = Body.objects.get(name=body_name)
        body_elements = model_to_dict(body)

        site_list = ['V37', 'W85', 'K91', 'Q63']

        # vis_times = dict.fromkeys(site_list, [])
        # vis_dates = dict.fromkeys(site_list, [])

        date_start = datetime.utcnow()

        date_end = date_start + timedelta(days=3)

        for site in site_list:
            emp_time = date_start
            phase_times = []
            vis_day_list = []
            while emp_time <= date_end:
                emp = compute_ephem(emp_time, body_elements, site, dbg=False, perturb=False, display=False)
                altitude = emp[5]
                if altitude > alt_limit:
                    phased_emp_time = (emp_time - date_start) / timedelta(hours=period)
                    phase_times.append(phased_emp_time)
                    vis_day_list.append(emp_time.date)
                emp_time += timedelta(minutes=30)
            # vis_times[site] = phase_times
            # vis_dates[site] = vis_day_list
            # print(site)
            # print(vis_dates[site])
            self.break_data(vis_day_list, phase_times, site)
