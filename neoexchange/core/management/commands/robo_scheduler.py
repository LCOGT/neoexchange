"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2021 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime, timedelta
from math import degrees

from django.core.management.base import BaseCommand, CommandError

from core.models import Body, Block
from core.views import schedule_check, schedule_submit, record_block
from astrometrics.ephem_subs import format_emp_line, determine_sites_to_schedule, get_sitepos,\
    moon_ra_dec
from astrometrics.sources_subs import get_site_status
from pyslalib.slalib import sla_dsep

def compute_moon_sep(date, object_ra, object_dec, site='500'):
    '''Compute the separation between an object at <object_ra>, <object_dec> and the Moon
    at time <date> from the specified [site] (defaults to geocenter if not specified.
    The separation is returned in degrees.'''

    site_name, site_long, site_lat, site_hgt = get_sitepos(site)
    moon_ra, moon_dec, diam = moon_ra_dec(date, site_long, site_lat, site_hgt)
    moon_obj_sep = sla_dsep(object_ra, object_dec, moon_ra, moon_dec)
    moon_obj_sep = degrees(moon_obj_sep)

    return moon_obj_sep

def filter_bodies(bodies, obs_date = datetime.utcnow(), bright_limit = 19.0, faint_limit = 22.0, spd_south_cut=95.0, speed_cutoff=5.0, moon_sep_cutoff=30.0, too=False):
    north_1m0_list = []
    north_0m4_list = []
    south_1m0_list = []
    south_0m4_list = []
    point4m_mag_cut = 20.5

    run_datetime = datetime.utcnow()

    print(" Object     RA           Dec       Mag.   Speed  Moon Sep.")
    print("----------------------------------------------------------")

    for body in bodies:
        body_line = body.compute_position()
        vmag = body_line[2]
        spd = body_line[3]
        sky_motion = body_line[-2]
        sky_motion_pa = body_line[-1]
        if not body_line:
            continue
        moon_sep = compute_moon_sep(obs_date, body_line[0], body_line[1], '500')
        prefix = ' '
        suffix = ' '
        if moon_sep < moon_sep_cutoff:
            prefix = '('
            suffix = ')'
        moon_sep_str = "%s%.1f%s" % ( prefix, moon_sep, suffix)
        emp_line = { 'date' : obs_date,
                     'ra' : body_line[0],
                     'dec' : body_line[1],
                     'mag' : vmag,
                     'sky_motion' : sky_motion,
                     'sky_motion_pa' : sky_motion_pa,
                     'altitude' : -99,
                     'southpole_sep' : spd
                   }
        line_bits = format_emp_line(emp_line, '500')
        schedule = True
        status = 'OK'

        if vmag > faint_limit or vmag < bright_limit:
            status = "Outside mag. range"
            schedule = False
        if sky_motion > speed_cutoff:
            status = "Too fast"
            schedule = False
        if moon_sep < moon_sep_cutoff:
            status = "Too close to the Moon"
            schedule = False
        # Find number of active and inactive but unreported Blocks
        if too == False:
            num_active = Block.objects.filter(body=body, active=True, block_end__gte=run_datetime-timedelta(seconds=35*60)).count()
            num_not_found = Block.objects.filter(body=body, active=False, num_observed__gte=1, reported=False).count()
            if num_active >= 1:
                status = "Already active"
                schedule = False
            if num_not_found >= 2:
                status = "Tried twice already and not found"
                schedule = False
        else:
            schedule = True

        print("%7s %s %s  V=%s  %s   %6.6s  %s" % ( body.current_name(), line_bits[1], line_bits[2], line_bits[3], line_bits[4], moon_sep_str, status))
        if schedule == False:
            continue

        if spd > spd_south_cut:
            if vmag < point4m_mag_cut:
                north_0m4_list.append(body)
            else:
                north_1m0_list.append(body)
        else:
            if vmag < point4m_mag_cut:
                south_0m4_list.append(body)
            else:
                south_1m0_list.append(body)
    north_list = { '0m4' : north_0m4_list, '1m0' : north_1m0_list }
    south_list = { '0m4' : south_0m4_list, '1m0' : south_1m0_list }

    return north_list, south_list

def schedule_target_list(bodies_list, form_details, username):
    num_scheduled = 0
    objects_scheduled = []
    if bodies_list:
        for target in bodies_list:
            data = schedule_check(form_details, target)
            if datetime.strptime(data['end_time'], '%Y-%m-%dT%H:%M:%S') <= datetime.utcnow():
                form_details['utc_date'] += timedelta(days=1)
                data = schedule_check(form_details, target)

            data['start_time'] = datetime.strptime(data['start_time'],'%Y-%m-%dT%H:%M:%S')
            data['end_time'] = datetime.strptime(data['end_time'],'%Y-%m-%dT%H:%M:%S')

            print("%s@%s for %s->%s" % (target.current_name(), data['site_code'], data['start_time'], data['end_time']))
            tracking_num, sched_params = schedule_submit(data, target, username)
            block_resp = record_block(tracking_num, sched_params, data, target)

            if block_resp:
                num_scheduled += 1
                objects_scheduled.append(str(target.current_name()))
    return num_scheduled, objects_scheduled


class Command(BaseCommand):
    help = 'Determine what to schedule robotically for the given time'

    def add_arguments(self, parser):
        bright_default = 19.0
        faint_default = 22.0
        spd_default = 95.0
        not_seen_default = 2.5
        proposal_default = 'LCO2021B-002'
        speed_limit_default = 5.0
        parser.add_argument('--date', default=datetime.utcnow(), help='Date to schedule for (YYYYMMDD-HH)')
        parser.add_argument('--user', default='tlister@lcogt.net', help="Username to schedule as e.g. 'tlister@lcogt.net'")
        parser.add_argument('--proposal', default=proposal_default, help='Proposal code to use ('+proposal_default+')')
        parser.add_argument('--run', action="store_true", help="Whether to execute the scheduling")
        parser.add_argument('--bright_limit', default=bright_default, type=float, help="Bright magnitude limit ("+str(bright_default)+")")
        parser.add_argument('--faint_limit', default=faint_default, type=float, help="Faint magnitude limit ("+str(faint_default)+")")
        spd_help = "South Polar Distance cutoff for S. Hemisphere (%.1f=%+.1f Dec)" % (spd_default, spd_default-90.0)
        parser.add_argument('--spd_cutoff', default=spd_default, type=float, help=spd_help)
        parser.add_argument('--speed_limit', default=speed_limit_default, type=float, help="Rate of motion limit ("+str(speed_limit_default)+")")
        parser.add_argument('--not_seen', default=not_seen_default, type=float, help="Cutoff since object was seen ("+str(not_seen_default)+" days)")
        parser.add_argument('--too', action="store_true", help="Whether to execute as disruptive ToO")
        parser.add_argument('--object', default=None, type=str, help="Specific object to schedule")
        parser.add_argument('--skip_north', action="store_true", help="Whether to skip scheduling in the North")
        parser.add_argument('--skip_south', action="store_true", help="Whether to skip scheduling in the South")

    def handle(self, *args, **options):
        usage = "Incorrect usage. Usage: %s --date [YYYYMMDD[-HH]] --user [tlister@lcogt.net] --run"
        if type(options['date']) != datetime:
            try:
                scheduling_date = datetime.strptime(options['date'], '%Y%m%d-%H')
            except ValueError:
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
        self.stdout.write('==== Cutoffs: Bright= %.1f, Faint = %.1f, SPD= %.1f(=%+.1f Dec), Motion= %.1f "/min, Not Seen= %.1f days' % \
            (options['bright_limit'], options['faint_limit'], \
             options['spd_cutoff'], options['spd_cutoff'] - 90.0, options['speed_limit'], options['not_seen']))

        if options['object'] is not None:
            bodies = Body.objects.filter(provisional_name=options['object'])
            if bodies.count() == 0:
                raise CommandError("Did not find body %s" % options['object'])
            elif bodies.count() > 1:
                raise CommandError("Found multiple bodies")
            newest = bodies
            # Reset limits to prevent filtering
            options['bright_limit'] = min(options['bright_limit'], 8)
            options['faint_limit'] = max(options['faint_limit'], 22)
            options['speed_limit'] = max(options['speed_limit'], 999)
        else:
            latest = Body.objects.filter(active=True).latest('ingest')
            max_dt = latest.ingest
            min_dt = max_dt - timedelta(days=5)
            newest = Body.objects.filter(ingest__range=(min_dt, max_dt), active=True)
            bodies = newest.filter(not_seen__lte=options['not_seen'], source_type='U', updated=False)
        self.stdout.write("Found %d newest bodies, %d available for scheduling" % (newest.count(), bodies.count()))

        north_list, south_list = filter_bodies(bodies, scheduling_date, options['bright_limit'], options['faint_limit'], \
             options['spd_cutoff'], options['speed_limit'],too=options['too'])

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
            self.stdout.write("No 0.4m telescopes available in the North, transferring targets to 1m0 telescopes")
            north_list['1m0'] = north_list['1m0'] + north_list['0m4']
        if len(sites['south']['0m4']) == 0 and len(sites['south']['1m0']) > 0:
            self.stdout.write("No 0.4m telescopes available in the South, transferring targets to 1m0 telescopes")
            south_list['1m0'] = south_list['1m0'] + south_list['0m4']

        self.stdout.write("\nSite Available?\n===============")
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
                if options['skip_north'] is False:
                    do_north = False
                    if len(sites['north'][tel_class]) > 0:
                        for site in sites['north'][tel_class]:
                            if site_status[site][0] is True:
                                do_north = True
                                north_form = {'site_code': sites['north'][tel_class][0],
                                              'utc_date' : scheduling_date.date(),
                                              'proposal_code': options['proposal'],
                                              'too_mode' : options['too']}
                else:
                    do_north = False

                if options['skip_south'] is False:
                    do_south = False
                    if len(sites['south'][tel_class]) > 0:
                        for site in sites['south'][tel_class]:
                            if site_status[site][0] is True:
                                do_south = True
                                south_form = {'site_code': sites['south'][tel_class][0],
                                              'utc_date' : scheduling_date.date(),
                                              'proposal_code': options['proposal'],
                                              'too_mode' : options['too']}
                else:
                    do_south = False
                # Schedule telescopes
                if do_north:
                    num_scheduled, objects_scheduled = schedule_target_list(north_list[tel_class], north_form, username)
                    self.stdout.write("Scheduled %d (%s) in the North at %s" % (num_scheduled, objects_scheduled, north_form['site_code']))
                else:
                    if options['skip_north']:
                        self.stdout.write("Skipping {} scheduling in the North".format(tel_class))
                    else:
                        self.stdout.write("No %s sites in the North available for scheduling" % tel_class)
                if do_south:
                    num_scheduled, objects_scheduled = schedule_target_list(south_list[tel_class], south_form, username)
                    self.stdout.write("Scheduled %d (%s) in the South at %s" % (num_scheduled,  objects_scheduled, south_form['site_code']))
                else:
                    if options['skip_south']:
                        self.stdout.write("Skipping {} scheduling in the South".format(tel_class))
                    else:
                        self.stdout.write("No %s sites in the South available for scheduling" % tel_class)
        else:
            self.stdout.write("Simulating scheduling at %s and %s" % (sites['north'], sites['south']) )
