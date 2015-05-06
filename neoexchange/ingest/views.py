'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime
from django.db.models import Q
from django.forms.models import model_to_dict
from django.shortcuts import render
from django.views.generic import DetailView, ListView, FormView, TemplateView
from django.core.urlresolvers import reverse
from ingest.ephem_subs import call_compute_ephem, compute_ephem, \
    determine_darkness_times, determine_slot_length, determine_exp_time_count
from ingest.forms import EphemQuery, ScheduleForm
from ingest.models import *
from ingest.sources_subs import fetchpage_and_make_soup, packed_to_normal, \
    fetch_mpcorbit, submit_block_to_scheduler
from ingest.time_subs import extract_mpc_epoch, parse_neocp_date
import logging
import reversion

logger = logging.getLogger(__name__)


def home(request):
    latest = Body.objects.latest('ingest')
    newest = Body.objects.filter(ingest=latest.ingest)
    params = {
            'targets'   : Body.objects.filter(active=True).count(),
            'blocks'    : Block.objects.filter(active=True).count(),
            'latest'    : latest,
            'newest'    : newest,
            'form'      : EphemQuery()
    }
    return render(request,'ingest/home.html',params)

class BodyDetailView(DetailView):
    context_object_name = "body"
    model = Body

    def get_context_data(self, **kwargs):
        context = super(BodyDetailView, self).get_context_data(**kwargs)
        context['form'] = EphemQuery()
        return context


class BodySearchView(ListView):
    template_name = 'ingest/body_list.html'
    model = Body

    def get_queryset(self):
        try:
            name = self.request.REQUEST.get("q")
        except:
            name = ''
        if (name != ''):
            object_list = self.model.objects.filter(Q(provisional_name__icontains = name )|Q(provisional_packed__icontains = name)|Q(name__icontains = name))
        else:
            object_list = self.model.objects.all()
        return object_list

def ephemeris(request):

    form = EphemQuery(request.GET)
    ephem_lines = []
    if form.is_valid():
        data = form.cleaned_data
        body_elements = model_to_dict(data['target'])
        dark_start, dark_end = determine_darkness_times(data['site_code'], data['utc_date'])
        ephem_lines = call_compute_ephem(body_elements, dark_start, dark_end, data['site_code'], 300, data['alt_limit'] )
    else:
        return render(request, 'ingest/home.html', {'form' : form})
    return render(request, 'ingest/ephem.html',
        {'target'  : data['target'],
         'ephem_lines'      : ephem_lines, 
         'site_code'        : form['site_code'].value(),
        }
    )

class ScheduleTarget(FormView):
    template_name = 'ingest/schedule.html'
    form_class = ScheduleForm
    success_url = reverse('schedule-success')

    def form_valid(self, form):
        data = schedule(form)
        logger.debug(data)
        self.request.session['results'] = data
        return super(ScheduleTarget, self).form_valid(form)

def schedule(data):
    body_elements = model_to_dict(data['body_id'])
    # Check for valid proposal
    # validate_proposal_time(data['proposal_code'])

    # Determine magnitude
    dark_start, dark_end = determine_darkness_times(data['site_code'], data['utc_date'])
    dark_midpoint = dark_start + (dark_end-dark_start)/2
    emp = compute_ephem(dark_midpoint, body_elements, data['site_code'], False, False, False)
    magnitude = emp[3]
    speed = emp[4]

    # Determine slot length
    try:
        slot_length = determine_slot_length(body_elements['provisional_name'], magnitude, data['site_code'])
    except MagRangeError:
        ok_to_schedule = False
    # Determine exposure length and count
    exp_length, exp_count = determine_exp_time_count(speed, data['site_code'], slot_length)
    if exp_length == None or exp_count == None:
        ok_to_schedule = False

    if data['ok_to_schedule'] == True:
        logger.info(body_elements)
        # Assemble request
        body_elements['epochofel_mjd'] = body.epochofel_mjd()
        body_elements['current_name'] = body.current_name()
        params = {  'proposal_code' : data['proposal_code'],
                    'exp_count' : exp_count,
                    'exp_time' : exp_length,
                    'site_code' : data['site_code'],
                    'start_time' : dark_start,
                    'end_time' : dark_end,
                    'group_id' : body_elements['current_name'] + '_' + data['site_code'].upper() + '-'  + datetime.strftime(data['utc_date'], '%Y%m%d')
                 }
        # Record block and submit to scheduler
#    if check_block_exists == 0:
        request_number = submit_block_to_scheduler(body_elements, params)
    resp =   {
             'target_name' : body.current_name(),
             'magnitude' : magnitude,
             'speed' : speed,
             'slot_length' : slot_length,
             'exp_count' : exp_count,
             'exp_length' : exp_length,
             'schedule_ok' : ok_to_schedule,
             'request_number' : request_number
             }
    return resp


def schedule_old(request):

    body_id = request.GET.get('body_id', 1)
    ok_to_schedule = request.GET.get('ok_to_schedule', False)
    logger.info("top of form", ok_to_schedule, body_id)
    form = ScheduleForm()
    if form.is_valid():
        data = form.cleaned_data
        logger.info(data)
        body_elements = model_to_dict(data['body_id'])
        # Check for valid proposal
        # validate_proposal_time(data['proposal_code'])

        # Determine magnitude
        dark_start, dark_end = determine_darkness_times(data['site_code'], data['utc_date'])
        dark_midpoint = dark_start + (dark_end-dark_start)/2
        emp = compute_ephem(dark_midpoint, body_elements, data['site_code'], False, False, False)
        magnitude = emp[3]
        speed = emp[4]

        # Determine slot length
        try:
            slot_length = determine_slot_length(body_elements['provisional_name'], magnitude, data['site_code'])
        except MagRangeError:
            ok_to_schedule = False
        # Determine exposure length and count
        exp_length, exp_count = determine_exp_time_count(speed, data['site_code'], slot_length)
        if exp_length == None or exp_count == None:
            ok_to_schedule = False

        if data['ok_to_schedule'] == True:
            logger.info(body_elements)
            # Assemble request
            body_elements['epochofel_mjd'] = body.epochofel_mjd()
            body_elements['current_name'] = body.current_name()
            params = {  'proposal_code' : data['proposal_code'],
                        'exp_count' : exp_count,
                        'exp_time' : exp_length,
                        'site_code' : data['site_code'],
                        'start_time' : dark_start,
                        'end_time' : dark_end,
                        'group_id' : body_elements['current_name'] + '_' + data['site_code'].upper() + '-'  + datetime.strftime(data['utc_date'], '%Y%m%d')
                     }
            # Record block and submit to scheduler
#    if check_block_exists == 0:
            request_number = submit_block_to_scheduler(body_elements, params)
#        record_block()
        return render(request, 'ingest/schedule.html',
            {'form' : form,
             'target_name' : body.current_name(),
             'magnitude' : magnitude,
             'speed' : speed,
             'slot_length' : slot_length,
             'exp_count' : exp_count,
             'exp_length' : exp_length,
             'schedule_ok' : ok_to_schedule,
             'request_number' : request_number}
        )
    else:
        logger.debug(form)
        body = Body.objects.get(id=body_id)
        return render(request, 'ingest/schedule.html', {'form' : form, 'target_name' : body.current_name()})

    return render(request, 'ingest/schedule.html',
        {'target_name' : body.current_name()}
    )

def save_and_make_revision(body,kwargs):
    ''' Make a revision if any of the parameters have changed, but only do it once per ingest not for each parameter
    '''
    update = False
    body_dict = model_to_dict(body)
    for k, v in kwargs.items():
        param = body_dict[k]
        if type(body_dict[k]) == type(float()):
            v = float(body_dict[k])
        if v != param:
            setattr(body, k, v)
            update = True
    if update:
        with reversion.create_revision():
            body.save()
    return update

def update_NEOCP_orbit(obj_id, dbg=False):
    '''Query the MPC's showobs service with the specified <obj_id> and
    it will write the orbit found into the neox database.
    a) If the object does not have a response it will be marked as active = False
    b) If the object's parameters have changed they will be updated and a revision logged
    c) New objects get marked as active = True automatically 
    '''

    NEOCP_orb_url = 'http://scully.cfa.harvard.edu/cgi-bin/showobsorbs.cgi?Obj='+obj_id+'&orb=y'
    
    neocp_obs_page = fetchpage_and_make_soup(NEOCP_orb_url)
    
    if neocp_obs_page:
        obs_page_list = neocp_obs_page.text.split('\n')
    else:
        return False
    
# If the object has left the NEOCP, the HTML will say 'None available at this time.'
# and the length of the list will be 1
    body, created = Body.objects.get_or_create(provisional_name=obj_id)
    if len(obs_page_list) > 1:
        # Clean up the header and top line of input
        kwargs = clean_NEOCP_object(obs_page_list)
        if not created:
            # Find out if the details have changed, if they have, save a revision
            check_body = Body.objects.filter(provisional_name=obj_id, **kwargs)
            if check_body.count() == 0:
                if save_and_make_revision(body,kwargs):
                    logger.info("Updated %s" % obj_id)
        else:
            save_and_make_revision(body,kwargs)
            logger.info("Added %s" % obj_id)
    else:
        save_and_make_revision(check_body,{'active':False})
        logger.info("Object %s no longer exists on the NEOCP." % obj_id)
    return True

def clean_NEOCP_object(page_list):
    '''Parse response from the MPC NEOCP page making sure we only return 
    parameters from the 'NEOCPNomin' (nominal orbit)'''
    current = False
    if page_list[0] == '':
        page_list.pop(0)
    if page_list[0][:6] == 'Object':
        page_list.pop(0)
    for line in page_list:
        if 'NEOCPNomin' in line:
            current = line.strip().split()
            break
    if current:
        if len(current) == 16:
            # Missing H parameter, probably...
            try:
                slope = float(current[2])
            except ValueError:
                # Insert a high magnitude for the missing H
                current.insert(1,99.99)
                logger.warn("Missing H magnitude for %s; assuming 99.99", current[0])
            except:
                logger.error("Missing field in NEOCP orbit for %s which wasn't correctable", current[0])

        if len(current) == 17:
            params = {
                    'abs_mag'       : float(current[1]),
                    'slope'         : float(current[2]),
                    'epochofel'     : extract_mpc_epoch(current[3]),
                    'meananom'      : float(current[4]),
                    'argofperih'    : float(current[5]),
                    'longascnode'   : float(current[6]),
                    'orbinc'        : float(current[7]),
                    'eccentricity'  : float(current[8]),
                    'meandist'      : float(current[10]),
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        else:
            logger.warn("Did not get right number of parameters for %s. Values %s", current[0], current)
            params = {}
    else:
        params = {}
    return params

def update_crossids(astobj, dbg=False):
    '''Update the passed <astobj> for a new cross-identification.
    <astobj> is expected to be a list of:
    provisional id, final id/failure reason, reference, confirmation date
    normally produced by the fetch_previous_NEOCP_desigs() method.'''

    if len(astobj) != 4:
        return False

    obj_id = astobj[0].rstrip()

    body, created = Body.objects.get_or_create(provisional_name=obj_id)
    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_crossid(astobj, dbg)
    if not created:
        if dbg: print "Did not create new Body"
        # Find out if the details have changed, if they have, save a revision
        check_body = Body.objects.filter(provisional_name=obj_id, **kwargs)
        if check_body.count() == 0:
            save_and_make_revision(body,kwargs)
            logger.info("Updated cross identification for %s" % obj_id)
    else:
        # Didn't know about this object before so create but make inactive
        kwargs['active'] = False
        save_and_make_revision(body,kwargs)
        logger.info("Added cross identification for %s" % obj_id)
    return True


def clean_crossid(astobj, dbg=False):
    '''Takes an <astobj> (a list of new designation, provisional designation,
    reference and confirm date produced from the MPC's Previous NEOCP Objects
    page) and determines the type and whether it should still be followed.

    Objects that were not confirmed, did not exist or "were not interesting
    (normally a satellite) are set inactive immediately. For NEOs and comets,
    we set it to inactive if more than 3 days have passed since the
    confirmation date'''

    interesting_cutoff = 3 * 86400  # 3 days in seconds

    confirm_date = parse_neocp_date(astobj[3])
    obj_id = astobj[0].rstrip()
    desig = astobj[1]
    reference = astobj[2]

    time_from_confirm = datetime.utcnow() - confirm_date
    time_from_confirm = time_from_confirm.total_seconds()

    active = True
    if obj_id != '' and desig == 'wasnotconfirmed':
        # Unconfirmed, no longer interesting so set inactive
        objtype = 'U'
        desig = ''
        active = False
    elif obj_id != '' and desig == 'doesnotexist':
        # Did not exist, no longer interesting so set inactive
        objtype = 'X'
        desig = ''
        active = False
    elif obj_id != '' and desig == '' and reference == '':
        # "Was not interesting" (normally a satellite), no longer interesting 
        # so set inactive
        objtype = 'W'
        desig = ''
        active = False
    elif obj_id != '' and desig != '':
        # Confirmed
        if 'CBET' in reference:
            # There is a reference to an CBET so we assume it's "very
            # interesting" i.e. a comet
            objtype = 'C'
            if time_from_confirm > interesting_cutoff:
                active = False
        elif 'MPEC' in reference:
            # There is a reference to an MPEC so we assume it's
            # "interesting" i.e. an NEO
            objtype = 'N'
            if time_from_confirm > interesting_cutoff:
                active = False
        else:
            objtype = 'A'
            active = False

    params = { 'source_type'  : objtype,
               'name'         : desig,
               'active'       : active
             }
    if dbg: print "%07s->%s (%s) %s" % ( obj_id, params['name'], params['source_type'], params['active'])

    return params

def clean_mpcorbit(elements, dbg=False, origin='M'):
    '''Takes a list of (proto) element lines from fetch_mpcorbit() and plucks
    out the appropriate bits. origin defaults to 'M'(PC) if not specified'''

    params = {}
    if elements != None:
        params = {
                'epochofel'     : datetime.strptime(elements['epoch'].replace('.0', ''), '%Y-%m-%d'),
                'meananom'      : elements['mean anomaly'],
                'argofperih'    : elements['argument of perihelion'],
                'longascnode'   : elements['ascending node'],
                'orbinc'        : elements['inclination'],
                'eccentricity'  : elements['eccentricity'],
                'meandist'      : elements['semimajor axis'],
                'source_type'   : 'A',
                'elements_type' : 'MPC_MINOR_PLANET',
                'active'        : True,
                'origin'        : origin,
                }
    return params

    
def update_MPC_orbit(obj_id, dbg=False, origin='M'):

    elements = fetch_mpcorbit(obj_id, dbg)

    body, created = Body.objects.get_or_create(name=obj_id)
    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_mpcorbit(elements, dbg, origin)
    if not created:
        # Find out if the details have changed, if they have, save a revision
        check_body = Body.objects.filter(name=obj_id, **kwargs)
        if check_body.count() == 1 and check_body[0] == body:
            if save_and_make_revision(check_body[0],kwargs):
                logger.info("Updated elements for %s" % obj_id)
    else:
        # Didn't know about this object before so create 
        save_and_make_revision(body,kwargs)
        logger.info("Added new orbit for %s" % obj_id)
    return True
