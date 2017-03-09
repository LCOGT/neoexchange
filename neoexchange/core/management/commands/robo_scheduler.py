from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from core.models import Body, Block
from core.views import schedule_check, schedule_submit, record_block
from astrometrics.ephem_subs import format_emp_line

def filter_bodies(bodies, obs_date = datetime.utcnow(), bright_limit = 19.0, faint_limit = 22.0):
    north_list=[] 
    south_list=[] 

    for body in bodies:
        emp_line = body.compute_position()
        if not emp_line:
            continue
        line_bits = format_emp_line((obs_date, emp_line[0], emp_line[1], emp_line[2], emp_line[3]), '500')
        print body.current_name(), line_bits[1:4]
        if emp_line[2] > faint_limit or emp_line[2] < bright_limit:
            continue
    # Find number of active and inactive but unreported Blocks
        num_active = Block.objects.filter(body=body, active=True).count()
        num_not_found = Block.objects.filter(body=body, active=False, reported=False).count()
        if num_active >= 1:
            print "Already active"
            continue
        if num_not_found >= 2:
            print "Tried twice already and not found"
            continue
        if emp_line[3] > 95:
            north_list.append(body)
        else:
            south_list.append(body)
    return north_list, south_list

def schedule_target_list(bodies_list, form_details, username):
    num_scheduled = 0
    for target in bodies_list:
        data = schedule_check(form_details, target)

        data['start_time'] = datetime.strptime(data['start_time'],'%Y-%m-%dT%H:%M:%S')
        data['end_time'] = datetime.strptime(data['end_time'],'%Y-%m-%dT%H:%M:%S')

        tracking_num, sched_params = schedule_submit(data, target, username)
        block_resp = record_block(tracking_num, sched_params, data, target)

        if block_resp:
            num_scheduled += 1
    return num_scheduled


class Command(BaseCommand):
    help = 'Fetch Goldstone target list for the current year'

    def add_arguments(self, parser):
        parser.add_argument('--date', default=datetime.utcnow(), help='Date to schedule for (YYYYMMDD)')
        parser.add_argument('--user', default='tlister@lcogt.net', help="Username to schedule as e.g. 'tlister@lcogt.net'")
        parser.add_argument('--run', action="store_true", help="Whether to execute the scheduling")

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s --date [YYYYMMDD] --user [tlister@lcogt.net]"
        if type(options['date']) != datetime:
            try:
                scheduling_date = datetime.strptime(options['date'], '%Y%m%d')
            except ValueError:
                raise CommandError(usage)
        else:
            scheduling_date = options['date']

        username = options['user']
        self.stdout.write("==== Runnning for date %s , submitting as %s" % (scheduling_date.date(), username))
        latest = Body.objects.filter(active=True).latest('ingest')
        max_dt = latest.ingest
        min_dt = max_dt - timedelta(days=5)
        newest = Body.objects.filter(ingest__range=(min_dt, max_dt), active=True)
        bodies = newest.filter(not_seen__lte=2.5, source_type='U', updated=False)
        self.stdout.write("Found %d newest bodies, %d available for scheduling" % (newest.count(), bodies.count()))

        north_list, south_list = filter_bodies(bodies, obs_date=scheduling_date)


        self.stdout.write("Found %d for the North, %d for the South" % (len(north_list), len(south_list)))

        north_form = {'site_code': 'V37', 'utc_date' : scheduling_date.date(), 'proposal_code': 'LCO2016B-011'}
        south_form = {'site_code': 'W85', 'utc_date' : scheduling_date.date(), 'proposal_code': 'LCO2016B-011'}

        if options['run']:
            num_scheduled = schedule_target_list(north_list, north_form, username)
            self.stdout.write("Scheduled %d in the North" % num_scheduled)
            num_scheduled = schedule_target_list(south_list, south_form, username)
            self.stdout.write("Scheduled %d in the South" % num_scheduled)
        else:
            self.stdout.write("Simulating scheduling")
