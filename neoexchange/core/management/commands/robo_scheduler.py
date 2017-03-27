from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from core.models import Body, Block
from core.views import schedule_check, schedule_submit, record_block
from astrometrics.ephem_subs import format_emp_line, determine_sites_to_schedule
from astrometrics.sources_subs import get_site_status

def filter_bodies(bodies, obs_date = datetime.utcnow(), bright_limit = 19.0, faint_limit = 22.0, spd_south_cut=95.0, speed_cutoff=5.0):
    north_1m0_list = []
    north_0m4_list = []
    south_1m0_list = []
    south_0m4_list = []

    run_datetime = datetime.utcnow()

    print(" Object     RA           Dec       Mag.   Speed")
    print("------------------------------------------------")

    for body in bodies:
        emp_line = body.compute_position()
        vmag = emp_line[2]
        spd = emp_line[3]
        sky_motion = emp_line[-1]
        if not emp_line:
            continue
        line_bits = format_emp_line((obs_date, emp_line[0], emp_line[1], vmag, sky_motion, spd), '500')
        print("%7s %s %s  V=%s  %s" % ( body.current_name(), line_bits[1], line_bits[2], line_bits[3], line_bits[4]))
        if vmag > faint_limit or vmag < bright_limit:
            continue
        if sky_motion > speed_cutoff:
            continue
        # Find number of active and inactive but unreported Blocks
        num_active = Block.objects.filter(body=body, active=True, block_end__gte=run_datetime-timedelta(seconds=35*60)).count()
        num_not_found = Block.objects.filter(body=body, active=False, num_observed__gte=1, reported=False).count()
        if num_active >= 1:
            print "Already active"
            continue
        if num_not_found >= 2:
            print "Tried twice already and not found"
            continue
        if spd > spd_south_cut:
            if vmag < 20.5:
                north_0m4_list.append(body)
            else:
                north_1m0_list.append(body)
        else:
            south_1m0_list.append(body)
    north_list = { '0m4' : north_0m4_list, '1m0' : north_1m0_list }
    south_list = { '0m4' : south_0m4_list, '1m0' : south_1m0_list }

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
    help = 'Determine what to schedule robotically for the given time'

    def add_arguments(self, parser):
        bright_default = 19.0
        faint_default = 22.0
        spd_default = 95.0
        not_seen_default = 2.5
        proposal_default = 'LCO2016B-011'
        speed_limit_default = 5.0
        parser.add_argument('--date', default=datetime.utcnow(), help='Date to schedule for (YYYYMMDD)')
        parser.add_argument('--user', default='tlister@lcogt.net', help="Username to schedule as e.g. 'tlister@lcogt.net'")
        parser.add_argument('--proposal', default=proposal_default, help='Proposal code to use ('+proposal_default+')')
        parser.add_argument('--run', action="store_true", help="Whether to execute the scheduling")
        parser.add_argument('--bright_limit', default=bright_default, type=float, help="Bright magnitude limit ("+str(bright_default)+")")
        parser.add_argument('--faint_limit', default=faint_default, type=float, help="Faint magnitude limit ("+str(faint_default)+")")
        spd_help = "South Polar Distance cutoff for S. Hemisphere (%.1f=%+.1f Dec)" % (spd_default, spd_default-90.0)
        parser.add_argument('--spd_cutoff', default=spd_default, type=float, help=spd_help)
        parser.add_argument('--speed_limit', default=speed_limit_default, type=float, help="Rate of motion limit ("+str(speed_limit_default)+")")
        parser.add_argument('--not_seen', default=not_seen_default, help="Cutoff since object was seen ("+str(not_seen_default)+" days)")
        parser.add_argument('--too', action="store_true", help="Whether to execute as disruptive ToO")

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s --date [YYYYMMDD] --user [tlister@lcogt.net] --run"
        if type(options['date']) != datetime:
            try:
                scheduling_date = datetime.strptime(options['date'], '%Y%m%d')
            except ValueError:
                raise CommandError(usage)
        else:
            scheduling_date = options['date']
            if scheduling_date.hour > 17:
                scheduling_date += timedelta(days=1)

        if options['spd_cutoff'] < 0.0 or options['spd_cutoff'] >= 180.0:
            raise CommandError("South Polar Distance cutoff must be in the range 0..180")

        username = options['user']
        self.stdout.write("==== Runnning for date %s , submitting as %s" % (scheduling_date.date(), username))
        self.stdout.write('==== Cutoffs: Bright= %.1f, Faint = %.1f, SPD= %.1f(=%+.1f Dec), Motion= %.1f "/min' % \
            (options['bright_limit'], options['faint_limit'], \
             options['spd_cutoff'], options['spd_cutoff'] - 90.0, options['speed_limit']))

        latest = Body.objects.filter(active=True).latest('ingest')
        max_dt = latest.ingest
        min_dt = max_dt - timedelta(days=5)
        newest = Body.objects.filter(ingest__range=(min_dt, max_dt), active=True)
        bodies = newest.filter(not_seen__lte=options['not_seen'], source_type='U', updated=False)
        self.stdout.write("Found %d newest bodies, %d available for scheduling" % (newest.count(), bodies.count()))

        north_list, south_list = filter_bodies(bodies, scheduling_date, options['bright_limit'], options['faint_limit'], \
             options['spd_cutoff'], options['speed_limit'])

        # Dictionary *and* list comprehensions, super swank...
        north_targets = {tel_class : [str(x.current_name()) for x in north_list[tel_class]] for tel_class in north_list.keys()}
        south_targets = {tel_class : [str(x.current_name()) for x in south_list[tel_class]] for tel_class in south_list.keys()}

        self.stdout.write("\nTargets for scheduling:\nNorth: %s\nSouth: %s\n" % (north_targets, south_targets))
        num_north_targets = len(north_list['0m4']) + len(north_list['1m0'])
        num_south_targets = len(south_list['0m4']) + len(south_list['1m0'])
        self.stdout.write("Found %d for the North, %d for the South" % (num_north_targets, num_south_targets))

        sites = determine_sites_to_schedule(scheduling_date)

        self.stdout.write("\nSites for scheduling:\nNorth: %s\nSouth: %s\n\n" % (sites['north'], sites['south']))

# If no 0.4m's are available, transfer targets to 1m list
        if len(sites['north']['0m4']) == 0 and len(sites['north']['1m0']) > 0:
            self.stdout.warn("No 0.4m telescopes available, transferring targets to 1m0 telescopes")
            north_list['1m0'] = north_list['1m0'].append(north_list['0m4'])

        self.stdout.write("Site Available?\n===============")
        site_statuses = []
        for hemisphere in sites.keys():
            for tel_class in north_list.keys():
                for site in sites[hemisphere][tel_class]:
                    site_available, reason = get_site_status(site)
                    site_statuses.append((site, (site_available, reason)))
                    self.stdout.write("%4s %5s (%s)" % (site, site_available, reason))

        site_status = dict(site_statuses)

        if options['run']:

            for tel_class in north_list.keys():
                do_north = False
                if len(sites['north'][tel_class]) > 0:
                    for site in sites['north'][tel_class]:
                        if site_status[site][0] == True:
                            do_north = True
                            north_form = {'site_code': sites['north'][tel_class][0],
                                          'utc_date' : scheduling_date.date(),
                                          'proposal_code': options['proposal'],
                                          'too_mode' : options['too']}
                            break
                do_south = False
                if len(sites['south'][tel_class]) > 0:
                    for site in sites['south'][tel_class]:
                        if site_status[site][0] == True:
                            do_south = True
                            south_form = {'site_code': sites['south'][tel_class][0],
                                          'utc_date' : scheduling_date.date(),
                                          'proposal_code': options['proposal'],
                                          'too_mode' : options['too']}
                            break

                if do_north:
                    num_scheduled = schedule_target_list(north_list[tel_class], north_form, username)
                    self.stdout.write("Scheduled %d in the North at %s" % (num_scheduled, north_form['site_code']))
                else:
                    self.stdout.write("No sites in the North available for scheduling")
                if do_south:
                    num_scheduled = schedule_target_list(south_list[tel_class], south_form, username)
                    self.stdout.write("Scheduled %d in the South at %s" % (num_scheduled, south_form['site_code']))
                else:
                    self.stdout.write("No sites in the South available for scheduling")
        else:
            self.stdout.write("Simulating scheduling at %s and %s" % (sites['north'], sites['south']) )
