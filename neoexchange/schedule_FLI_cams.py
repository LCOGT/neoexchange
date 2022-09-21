import os
import json
from sys import argv, exit
from datetime import datetime, timedelta
import warnings
import argparse
import requests
from copy import deepcopy
from math import degrees, radians

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neox.settings")
from django.conf import settings
import django
django.setup()
from django.forms import model_to_dict

from astrometrics.sources_subs import make_target, make_moving_target
from astrometrics.ephem_subs import LCOGT_domes_to_site_codes, determine_darkness_times, call_compute_ephem, target_rise_set
from core.models import Body, Block, SuperBlock, StaticSource, SITE_CHOICES
from core.views import record_block

SUBMIT_URL = 'https://observe.lco.global'

def parse_args(args):
    prop_choices = ['LCOEngineering', 'LCO2022B-006']
    site_choices = [x[0] for x in SITE_CHOICES[:-3]]
    parser = argparse.ArgumentParser(description='Schedule FLI cameras',
                                     usage='%(prog)s [--filters] [--proposal] [--fracrate] [--date] <target> <block_length>')
    parser.add_argument('target', default='65803', help='Target to schedule for')
    parser.add_argument('block_length', type=float, help='Block length in hours')
    parser.add_argument('--date', action="store", type=datetime.fromisoformat, default=datetime.utcnow()+timedelta(minutes=10), help='Date to schedule for (default: %(default)s))')
    parser.add_argument('--filters', nargs='+', default=['gp', 'ip', 'clear'], help='Filters to schedule (default: %(default)s)')
    parser.add_argument('--proposal', choices=prop_choices, default=prop_choices[0], help='Proposal to use (default: %(default)s)')
    parser.add_argument('--site', choices=site_choices, default='cpt', help='Site to schedule (default: %(default)s)')
    parser.add_argument('--fracrate', type=float, default=0.5, help='Target tracking fractional rate (default: %(default)s)')
    parser.add_argument('--run', action="store_true", help="Whether to execute the scheduling")

    options = parser.parse_args(args)
    options_dict = vars(options)
    return options_dict

def get_cam_params(site, obs):
    if obs == 'doma' and site == 'cpt':
        sinistro_cam_name = 'fa16'
        cam_name = 'ef02'
    #    overhead = 3.64
        overhead = 1.455
    elif  obs == 'domb' and site == 'cpt':
        sinistro_cam_name = 'fa01'
        cam_name = 'ef03'
        overhead = 1.455
    elif  obs == 'domc' and site == 'cpt':
        sinistro_cam_name = 'fa06'
        cam_name = 'ef04'
        overhead = 1.455
    elif obs == 'doma' and site == 'lsc':
        sinistro_cam_name = 'fa15'
        cam_name = 'ef07'
    #    overhead = 1.404
        overhead = 1.5
    elif  obs == 'domb' and site == 'lsc':
        sinistro_cam_name = 'fa04'
        cam_name = 'ef05'
        overhead = 1.5
    elif  obs == 'domc' and site == 'lsc':
        sinistro_cam_name = 'fa03'
        cam_name = 'ef01'
        overhead = 1.5
    elif obs == 'doma' and site == 'elp':
        cam_name = 'ef08'
    #    overhead = 2.5
        overhead = 1.5
        sinistro_cam_name = 'fa05'
    elif obs == 'domb' and site == 'elp':
        cam_name = 'ef15'
        overhead = 1.5
        sinistro_cam_name = 'fa07'
    elif obs == 'doma' and site == 'coj':
        cam_name = 'ef09'
        overhead = 1.5
    elif  obs == 'domb' and site == 'coj':
        cam_name = 'ef10'
        overhead = 1.5
    elif obs == 'clma' and site == 'ogg':
        cam_name = 'kb42'
        overhead = 2.5
    elif obs == 'clma' and site == 'coj':
        cam_name = 'kb38'
        overhead = 2.5
    elif obs == 'doma' and site == 'tfn':
        cam_name = 'ef11'
        overhead = 1.5
        sinistro_cam_name = 'fa20'
    elif obs == 'domb' and site == 'tfn':
        cam_name = 'ef13'
        overhead = 1.5
        sinistro_cam_name = 'fa11'
    else:
        raise Exception("Camera '{}' not found".format(obs))

    return cam_name, overhead, sinistro_cam_name


if __name__ == "__main__":
    dstr = "%Y-%m-%dT%H:%M"
    options = parse_args(argv[1:])
    domes = ['doma', 'domb', ]# 'domc']
    exp_counts = [2, 2, 2]
    exp_times = [2.0, 10.0, 30.0]

    front_overhead = 90.0+25
    min_alt = 30

    site = options['site']
    frac_rate = options['fracrate']

    try:
        body_or_src = Body.objects.get(name=options['target'])
        body_elements = model_to_dict(body_or_src)
        body_elements['epochofel_mjd'] = body_or_src.epochofel_mjd()
        body_elements['epochofperih_mjd'] = body_or_src.epochofperih_mjd()
        body_elements['current_name'] = body_or_src.current_name()
        target_params = make_moving_target(body_elements)
    except Body.DoesNotExist:
        try:
            body_or_src = StaticSource.objects.get(name__icontains=options['target'])
            staticsrc_params = { 'ra_deg' : body_or_src.ra,
                                 'dec_deg' : body_or_src.dec, 
                                 'source_id' : body_or_src.current_name()
                               }
            target_params = make_target(staticsrc_params)
            body_elements = {'ra' : body_or_src.ra, 'dec' : body_or_src.dec, 'vmag' : body_or_src.vmag }
            frac_rate = 0.0
        except StaticSource.DoesNotExist:
            print("No StaticSource with that name found either")
            exit(-1)
        except StaticSource.MultipleObjectsReturned:
            print("Multiple StaticSources found:")
            srcs = StaticSource.objects.filter(name__icontains=options['target']).values_list('name', flat=True)
            print(srcs)
            exit(-2)
    block_start = options['date']
    block_length = timedelta(hours=abs(options['block_length']))
    block_end = block_start + block_length
    
    # Compute dark times and check/truncate if gone beyond
    site_code = LCOGT_domes_to_site_codes(site, 'doma', '1m0a')
    dark_start, dark_end = determine_darkness_times(site_code, block_start, sun_zd=102)
    if dark_start < datetime.utcnow():
        print("computing dark times for next day")
        dark_start, dark_end = determine_darkness_times(site_code, block_start+timedelta(days=1), sun_zd=102)
    print(f"Dark time: {dark_start.strftime(dstr)} -> {dark_end.strftime(dstr)}")
    end_suffix = ''
    if block_end > dark_end:
        block_end = dark_end
        end_suffix = '(truncated)'
    print(f"Scheduling for: {body_or_src.current_name()} from {block_start.strftime(dstr)} -> {block_end.strftime(dstr)}{end_suffix} using {options['filters']} using {options['proposal']}")

    emp = call_compute_ephem(body_elements, block_start, block_end, site_code, ephem_step_size='5m', alt_limit=min_alt, perturb=False)
    if len(emp) == 0:
        print(f"No visibility during {block_start.strftime(dstr)} ->  {block_end.strftime(dstr)}")
        if 'ra' in body_elements and 'dec' in body_elements:
            rise_time, set_time, max_alt, vis_time_hours = target_rise_set(block_start, radians(body_elements['ra']), radians(body_elements['dec']), site_code, min_alt, step_size='5m', sun=True)
            print(f"Visibility: {rise_time.strftime(dstr)} ->  {set_time.strftime(dstr)}")
        exit(-3)

    initial_inst_config = {
                    'exposure_time' : None,
                    'exposure_count' : None,
                    'mode': "autoguider_2",
                    'optical_elements' : {
                        'filter' : 'air'
                    }
                }

    for obs, cam_filter in zip(domes, options['filters']):

        cam_name, overhead, _ = get_cam_params(site, obs)
        telescope = '1m0a'
        site_code = LCOGT_domes_to_site_codes(site, obs.lower(), telescope)
        reqgroup_params = {
                            'telescope' : telescope,
                            'enclosure' : obs.lower(),
                            'site' : site.lower(),
                            'start' : block_start.strftime("%Y-%m-%dT%H:%M:%S") ,
                            'end' :  block_end.strftime("%Y-%m-%dT%H:%M:%S"),
                            'proposal'  : options['proposal'],
                            'name' : f"{body_or_src.current_name()}_{site_code.upper()}-{block_start.strftime('%Y%m%d')}", 
                            'priority' : 3, # This one is optional.  Default is 500.
                            'observation_type' : 'DIRECT',
                            'request' : {}
                          }

        reqgroup =  deepcopy(reqgroup_params)
        # Create base Expose configuration
        expose_params = {
            # Required expose params
            'target'     : target_params,
            'type'       : 'REPEAT_EXPOSE',
            'instrument_name'  : cam_name,    #instrument/CCD
            'instrument_type' : 'AUTOGUIDER',
            'guide_camera_name'    : cam_name,
            'constraints' : {
                # Block observing constraints.  Required (maybe only a blank dictionary?)
                'max_airmass' : 4.0,
                'min_transparency' : 1.0,
                'max_seeing' : 2.0,
                'min_lunar_dist' : 15,
                'min_lunar_phase' : 1.00
            },
            'instrument_configs' : [],
            "acquisition_config": {
                "mode": "OFF"
            },
            "guiding_config": {
                "mode": "OFF"
            },
            "extra_params": {
                "observation_note" : "DART impact test"
            }
        }
        configs = []
        config = deepcopy(expose_params)
        rep_duration = block_length-timedelta(seconds=front_overhead)
        config['repeat_duration'] = rep_duration.total_seconds()

        inst_configs = []
        visit_duration = 0.0
        for expcount, exptime in zip(exp_counts, exp_times):
            print(expcount, exptime)
            visit_duration += expcount * (exptime+overhead)
            inst_config = deepcopy(initial_inst_config)
            inst_config['optical_elements']['filter'] = cam_filter # Set the filter
            inst_config['exposure_time'] = exptime # Set exposure time
            inst_config['exposure_count'] = expcount
            inst_configs.append(inst_config)
        config['instrument_configs'] = inst_configs
        configs.append(config)
        # Make a cleanup config to go at the end
        cleanup = deepcopy(expose_params)
        cleanup['type'] = 'EXPOSE'
        cleanup['instrument_configs'] = [deepcopy(initial_inst_config), ]
        cleanup['instrument_configs'][0]['optical_elements']['filter'] = 'clear'
        cleanup['instrument_configs'][0]['exposure_time'] = 0.15
        cleanup['instrument_configs'][0]['exposure_count'] = 1
        cleanup['instrument_configs'][0]['mode'] = 'autoguider_1'
        cleanup['extra_params']['observation_note'] = 'AG camera reset'
        configs.append(cleanup)
        # Add into RequestGroup
        reqgroup['request']['configurations'] = configs
        print()
        print(json.dumps(reqgroup, indent=4))

        print("For: %s->%s->%s on %s" % (reqgroup['site'], reqgroup['enclosure'], reqgroup['telescope'], cam_name))
        exp_list = []
        for config in configs:
            for inst in config['instrument_configs']:
                exp = f"{inst['exposure_count']}x{inst['exposure_time']}s"
                exp_list.append(exp)
        exp_string = ",".join(exp_list)
        print(reqgroup['start'], reqgroup['end'], exp_string,  reqgroup['name'])
        # Save the block
        if options['run']:
            token = os.getenv('VALHALLA_TOKEN')
            if token is None:
                print("VALHALLA_TOKEN must be set in environment")
                exit(-2)
            resp = requests.post(SUBMIT_URL + '/api/schedule/',
                        headers={'Authorization': 'Token {}'.format(token)},
                        json=reqgroup)
            try:
                resp.raise_for_status()
                response = resp.json()
                tracking_number = response['request_group_id']
                print('Submitted block with id: {0}. Check it at {1}/blocks/{0}'.format(response['id'], SUBMIT_URL))
                print("Now create downtime blocks at http://downtime.lco.gtn/admin/schedule/downtime/add/")
                request_items = [response.get('request', ''), ]
                request_numbers = [r['id'] for r in request_items]
                request_types = {}
                if len(request_items) > 0:
                    if 'configurations' in request_items[0]:
                        request_types = dict([(str(r['id']), r['configurations'][0]['target']['type']) for r in request_items])
                    else:
                        request_types = dict([(r['id'], r['target']['type']) for r in request_items])
                request_windows = [[{'start' : response['start'], 'end' : response['end']}]]
                length_obs = config.get('repeat_duration', block_length-timedelta(seconds=front_overhead))
                num_visits = length_obs.total_seconds() / visit_duration
                num_exposures = int(num_visits * sum(exp_counts))
                params = {
                            'block_duration' : sum([float(r['duration']) for r in request_items]),
                            'request_windows' : request_windows,
                            'request_numbers' : request_types,
                            'exp_count' : num_exposures,
                            'exp_time' : max(exp_times),
                            'site' : site,
                            'pondtelescope' : reqgroup['telescope'][0:3],
                            'fractional_rate' : frac_rate
                         }
                form_data = {
                             'proposal_code' : response['proposal'],
                             'group_name' : response['name'],
                             'start_time': block_start,
                             'end_time': block_end,
                            }
                record_block(tracking_number, params, form_data, body_or_src)
            except requests.HTTPError:
                print('Failed to submit block: error code {}: {}'.format(resp.status_code, resp.json()))
