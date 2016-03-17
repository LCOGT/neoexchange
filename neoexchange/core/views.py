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

from datetime import datetime, timedelta
from django.db.models import Q
from django.forms.models import model_to_dict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import DetailView, ListView, FormView, TemplateView, View
from django.views.generic.edit import FormView
from django.views.generic.detail import SingleObjectMixin
from django.http import Http404
from httplib import REQUEST_TIMEOUT, HTTPSConnection
from bs4 import BeautifulSoup
import urllib
from astrometrics.ephem_subs import call_compute_ephem, compute_ephem, \
    determine_darkness_times, determine_slot_length, determine_exp_time_count, \
    MagRangeError,  LCOGT_site_codes, LCOGT_domes_to_site_codes
from .forms import EphemQuery, ScheduleForm, ScheduleBlockForm, MPCReportForm
from .models import *
from astrometrics.sources_subs import fetchpage_and_make_soup, packed_to_normal, \
    fetch_mpcdb_page, parse_mpcorbit, submit_block_to_scheduler, parse_mpcobs,\
    fetch_NEOCP_observations, PackedError
from astrometrics.time_subs import extract_mpc_epoch, parse_neocp_date, parse_neocp_decimal_date
from astrometrics.ast_subs import determine_asteroid_type
import logging
import reversion
import json
import requests
from urlparse import urljoin
from django.conf import settings

logger = logging.getLogger(__name__)


class LoginRequiredMixin(object):

    #login_url = reverse('auth_login')

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)

def user_proposals(user):
    if type(user) != User:
        try:
            user = User.objects.get(username=user)
        except ObjectDoesNotExist:
            raise ValidationError

    proposals = Proposal.objects.filter(proposalpermission__user=user)

    return proposals

class MyProposalsMixin(object):

    def get_context_data(self, **kwargs):
        context = super(MyProposalsMixin, self).get_context_data(**kwargs)
        proposals = user_proposals(self.request.user)
        context['proposals'] = [(proposal.code, proposal.title) for proposal in proposals]

        return context


def home(request):
    params = build_unranked_list_params()
    return render(request, 'core/home.html', params)


class BodyDetailView(DetailView):
    model = Body
    context_object_name = "body"

    def get_context_data(self, **kwargs):
        context = super(BodyDetailView, self).get_context_data(**kwargs)
        context['form'] = EphemQuery()
        context['blocks'] = Block.objects.filter(body=self.object).order_by('block_start')
        return context


class BodySearchView(ListView):
    template_name = 'core/body_list.html'
    model = Body

    def get_queryset(self):
        try:
            name = self.request.REQUEST.get("q")
        except:
            name = ''
        if (name != ''):
            object_list = self.model.objects.filter(Q(provisional_name__icontains=name) | Q(provisional_packed__icontains=name) | Q(name__icontains=name))
        else:
            object_list = self.model.objects.all()
        return object_list

class BlockDetailView(DetailView):
    template_name = 'core/block_detail.html'
    model = Block

    def get_context_data(self, **kwargs):
        context = super(BlockDetailView, self).get_context_data(**kwargs)
        context['images'] = fetch_observations(context['block'].tracking_number, context['block'].proposal.code)
        return context


class BlockListView(ListView):
    model = Block
    template_name = 'core/block_list.html'
    queryset=Block.objects.order_by('-block_start')
    context_object_name="block_list"
    paginate_by = 20

def fetch_observations(tracking_num, proposal_code):
    query = "/find?propid=%s&order_by=-date_obs&tracknum=%s" % (proposal_code,tracking_num)
    data = framedb_lookup(query)
    if data:
        imgs = [(d["date_obs"],d["origname"][:-5]) for d in data]
        return imgs
    else:
        return False

def framedb_lookup(query):
    try:
        conn = HTTPSConnection("data.lcogt.net", timeout=20)
        params = urllib.urlencode(
            {'username': settings.NEO_ODIN_USER, 'password': settings.NEO_ODIN_PASSWD})
        #query = "/find?%s" % params
        conn.request("POST", query, params)
        response = conn.getresponse()
        r = response.read()
        data = json.loads(r)
    except:
        return False
    return data


class BlockReport(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        block.active = False
        block.reported = True
        block.when_reported = datetime.utcnow()
        block.save()
        return redirect(reverse('blocklist'))

class UploadReport(LoginRequiredMixin, FormView):
    template_name = 'core/uploadreport.html'
    success_url = reverse_lazy('blocklist')
    form_class = MPCReportForm

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        form = MPCReportForm(initial={'block_id':block.id})
        return render(request, 'core/uploadreport.html', {'form':form,'slot':block})

    def form_invalid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        print context['view'].request
        slot = Block.objects.get(pk=form['block_id'].value())
        return render(context['view'].request, 'core/uploadreport.html', {'form':form,'slot':slot})

    def form_valid(self, form):
        obslines = form.cleaned_data['report'].splitlines()
        measure = create_source_measurement(obslines, form.cleaned_data['block'])
        if measure:
            messages.success(self.request, 'Added source measurements for %s' % form.cleaned_data['block'])
        else:
            messages.warning(self.request, 'Unable to add source measurements for %s' % form.cleaned_data['block'])
        return super(UploadReport, self).form_valid(form)



class MeasurementViewBlock(LoginRequiredMixin, View):
    template = 'core/measurements.html'
    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        frames = Frame.objects.filter(block=block).values_list('id',flat=True)
        measures = SourceMeasurement.objects.filter(frame__in=frames)
        return render(request, self.template, {'body':block.body,'measures':measures,'slot':block})

class MeasurementViewBody(View):
    template = 'core/measurements.html'
    def get(self, request, *args, **kwargs):
        body = Body.objects.get(pk=kwargs['pk'])
        measures = SourceMeasurement.objects.filter(body=body).order_by('frame__midpoint')
        return render(request, self.template, {'body':body, 'measures' : measures})

def ephemeris(request):

    form = EphemQuery(request.GET)
    ephem_lines = []
    if form.is_valid():
        data = form.cleaned_data
        body_elements = model_to_dict(data['target'])
        dark_start, dark_end = determine_darkness_times(
            data['site_code'], data['utc_date'])
        ephem_lines = call_compute_ephem(
            body_elements, dark_start, dark_end, data['site_code'], 300, data['alt_limit'])
    else:
        return render(request, 'core/home.html', {'form': form})
    return render(request, 'core/ephem.html',
                  {'target': data['target'],
                   'ephem_lines': ephem_lines,
                   'site_code': form['site_code'].value(),
                   }
                  )


class LookUpBodyMixin(object):
    '''
    A Mixin for finding a Body from a pk and if it exists, return the Body instance.
    '''
    def dispatch(self, request, *args, **kwargs):
        try:
            body = Body.objects.get(pk=kwargs['pk'])
            self.body = body
            return super(LookUpBodyMixin, self).dispatch(request, *args, **kwargs)
        except Body.DoesNotExist:
            raise Http404("Body does not exist")

class ScheduleParameters(LoginRequiredMixin, LookUpBodyMixin, FormView):
    '''
    Creates a suggested observation request, including time window and molecules
    '''
    template_name = 'core/schedule.html'
    form_class = ScheduleForm
    ok_to_schedule = False

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        return self.render_to_response(self.get_context_data(form=form, body=self.body))

    def form_valid(self, form, request):
        data = schedule_check(form.cleaned_data, self.body, self.ok_to_schedule)
        new_form = ScheduleBlockForm(data)
        return render(request, 'core/schedule_confirm.html', {'form': new_form, 'data': data, 'body': self.body})

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.render_to_response(self.get_context_data(form=form, body=self.body))

    def get_context_data(self, **kwargs):
        '''
        Only show proposals the current user is a member of
        '''
        proposals = user_proposals(self.request.user)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        kwargs['form'].fields['proposal_code'].choices = proposal_choices
        return kwargs



class ScheduleSubmit(LoginRequiredMixin, SingleObjectMixin, FormView):
    '''
    Takes the hidden form input from ScheduleParameters, validates them as a double check.
    Then submits to the scheduler. If a tracking number is returned, the object has been scheduled and we record a Block.
    '''
    template_name = 'core/schedule_confirm.html'
    form_class = ScheduleBlockForm
    model = Body

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.form_invalid(form)

    def form_valid(self, form, request):
        if 'edit' in request.POST:
            # Recalculate the parameters with by amending the block length
            data = schedule_check(form.cleaned_data, self.object)
            new_form = ScheduleBlockForm(data)
            return render(request, 'core/schedule_confirm.html', {'form': new_form, 'data': data, 'body': self.object})
        elif 'submit' in request.POST:
            target = self.get_object()
            username = ''
            if request.user.is_authenticated():
                username = request.user.get_username()
            tracking_num, sched_params = schedule_submit(form.cleaned_data, target, username)
            if tracking_num:
                messages.success(self.request,"Request %s successfully submitted to the scheduler" % tracking_num)
                block_resp = record_block(tracking_num, sched_params, form.cleaned_data, target)
                if block_resp:
                    messages.success(self.request,"Block recorded")
                else:
                    messages.warning(self.request, "Record not created")
            else:
                messages.warning(self.request,"It was not possible to submit your request to the scheduler")
            return super(ScheduleSubmit, self).form_valid(form)

    def get_success_url(self):
        return reverse('home')

def schedule_check(data, body, ok_to_schedule=True):
    body_elements = model_to_dict(body)

    # Check if we have a high eccentricity object and it's not of comet type
    if body_elements['eccentricity'] >= 0.9 and body_elements['elements_type'] != 'MPC_COMET':
        logger.warn("Preventing attempt to schedule high eccentricity non-Comet")
        ok_to_schedule = False

    # Check for valid proposal
    # validate_proposal_time(data['proposal_code'])

    # Determine magnitude
    if data.get('start_time') and data.get('end_time'):
        dark_start = data.get('start_time')
        dark_end = data.get('end_time')
        utc_date = dark_start.date()
    else:
        dark_start, dark_end = determine_darkness_times(data['site_code'], data['utc_date'])
        utc_date = data['utc_date']
    dark_midpoint = dark_start + (dark_end - dark_start) / 2
    emp = compute_ephem(dark_midpoint, body_elements, data['site_code'], \
        dbg=False, perturb=True, display=False)
    if emp == []:
        emp = [-99 for x in range(5)]
    magnitude = emp[3]
    speed = emp[4]

    # Determine slot length
    if data.get('slot_length'):
        slot_length = data.get('slot_length')
    else:
        try:
            slot_length = determine_slot_length(body_elements['provisional_name'], magnitude, data['site_code'])
        except MagRangeError:
            slot_length = 0.
            ok_to_schedule = False
    # Determine exposure length and count
    exp_length, exp_count = determine_exp_time_count(speed, data['site_code'], slot_length)
    if exp_length == None or exp_count == None:
        ok_to_schedule = False

    resp = {
        'target_name': body.current_name(),
        'magnitude': magnitude,
        'speed': speed,
        'slot_length': slot_length,
        'exp_count': exp_count,
        'exp_length': exp_length,
        'schedule_ok': ok_to_schedule,
        'site_code': data['site_code'],
        'proposal_code': data['proposal_code'],
        'group_id': body.current_name() + '_' + data['site_code'].upper() + '-' + datetime.strftime(utc_date, '%Y%m%d'),
        'utc_date': utc_date.isoformat(),
        'start_time': dark_start.isoformat(),
        'end_time': dark_end.isoformat(),
        'mid_time': dark_midpoint.isoformat(),
        'ra_midpoint': emp[1],
        'dec_midpoint': emp[2]
    }
    return resp


def schedule_submit(data, body, username):

    # Assemble request
    # Send to scheduler
    body_elements = model_to_dict(body)
    body_elements['epochofel_mjd'] = body.epochofel_mjd()
    body_elements['epochofperih_mjd'] = body.epochofperih_mjd()
    body_elements['current_name'] = body.current_name()
    # Get proposal details
    proposal = Proposal.objects.get(code=data['proposal_code'])
    my_proposals = user_proposals(username)
    if proposal not in my_proposals:
        resp_params = {'msg' : 'You do not have permission to schedule using proposal %s' % data['proposal_code']}

        return None, resp_params
    params = {'proposal_id': proposal.code,
              'user_id': proposal.pi,
              'tag_id': proposal.tag,
              'priority': data.get('priority', 15),
              'submitter_id': username,

              'exp_count': data['exp_count'],
              'exp_time': data['exp_length'],
              'site_code': data['site_code'],
              'start_time': data['start_time'],
              'end_time': data['end_time'],
              'group_id': data['group_id']
              }
    # Check for pre-existing block
    tracking_number = None
    resp_params = None
    if check_for_block(data, params, body) == 0:
        # Record block and submit to scheduler
        tracking_number, resp_params = submit_block_to_scheduler(body_elements, params)
    return tracking_number, resp_params

def ranking(request):

    params = build_unranked_list_params()

    return render(request, 'core/ranking.html', params)


def build_unranked_list_params():
    params = {}
    try:
        # If we don't have any Body instances, return None instead of breaking
        latest = Body.objects.filter(active=True).latest('ingest')
        max_dt = latest.ingest
        min_dt = max_dt - timedelta(days=5)
        newest = Body.objects.filter(ingest__range=(min_dt, max_dt), active=True)
        unranked = []
        for body in newest:
            body_dict = model_to_dict(body)
            body_dict['FOM'] = body.compute_FOM
            body_dict['current_name'] = body.current_name()
            emp_line = body.compute_position()
            if not emp_line:
                continue
            body_dict['ra'] = emp_line[0]
            body_dict['dec'] = emp_line[1]
            body_dict['v_mag'] = emp_line[2]
            body_dict['spd'] = emp_line[3]
            body_dict['observed'], body_dict['reported'] = body.get_block_info()
            body_dict['type'] = body.get_source_type_display()
            unranked.append(body_dict)
    except Exception, e:
        latest = None
        unranked = None
        logger.error('Ranking failed on %s' % e)
    params = {
        'targets': Body.objects.filter(active=True).count(),
        'blocks': Block.objects.filter(active=True).count(),
        'latest': latest,
        'newest': unranked
    }
    return params

def check_for_block(form_data, params, new_body):
        '''Checks if a block with the given name exists in the Django DB.
        Return 0 if no block found, 1 if found, 2 if multiple blocks found'''

        # XXX Code smell, duplicated from sources_subs.configure_defaults()
        site_list = { 'V37' : 'ELP' , 'K92' : 'CPT', 'Q63' : 'COJ', 'W85' : 'LSC', 'W86' : 'LSC', 'F65' : 'OGG', 'E10' : 'COJ' }

        try:
            body_id = Body.objects.get(provisional_name=new_body.provisional_name)
        except Body.MultipleObjectsReturned:
            body_id = Body.objects.get(name=new_body.name)
        except Body.DoesNotExist:
            logger.warn("Body does not exist")
            return 3

        try:
            block_id = Block.objects.get(body=body_id,
                                         groupid__contains=form_data['group_id'],
                                         proposal=Proposal.objects.get(code=form_data['proposal_code']),
                                         site=site_list[params['site_code']])
        except Block.MultipleObjectsReturned:
            logger.debug("Multiple blocks found")
            return 2
        except Block.DoesNotExist:
            logger.debug("Block not found")
            return 0
        else:
            logger.debug("Block found")
            return 1

def record_block(tracking_number, params, form_data, body):
    '''Records a just-submitted observation as a Block in the database.
    '''

    logger.debug("form data=%s" % form_data)
    logger.debug("   params=%s" % params)
    if tracking_number:
        block_kwargs = { 'telclass' : params['pondtelescope'].lower(),
                         'site'     : params['site'].lower(),
                         'body'     : body,
                         'proposal' : Proposal.objects.get(code=form_data['proposal_code']),
                         'groupid'  : form_data['group_id'],
                         'block_start' : form_data['start_time'],
                         'block_end'   : form_data['end_time'],
                         'tracking_number' : tracking_number,
                         'num_exposures'   : form_data['exp_count'],
                         'exp_length'      : form_data['exp_length'],
                         'active'   : True
                       }
        pk = Block.objects.create(**block_kwargs)
        return True
    else:
        return False

def save_and_make_revision(body, kwargs):
    '''
    Make a revision if any of the parameters have changed, but only do it once
    per ingest not for each parameter.
    Converts current model instance into a dict and compares each element with
    incoming version. Incoming variables may be generically formatted as strings,
    so use the type of original to convert and then compare.
    '''
    update = False
    body_dict = model_to_dict(body)
    for k, v in kwargs.items():
        param = body_dict[k]
        if type(body_dict[k]) == type(float()) and v is not None:
            v = float(v)
        if v != param:
            setattr(body, k, v)
            update = True
    if update:
        with reversion.create_revision():
            body.save()
    return update


def update_NEOCP_orbit(obj_id, extra_params={}):
    '''Query the MPC's showobs service with the specified <obj_id> and
    it will write the orbit found into the neox database.
    a) If the object does not have a response it will be marked as active = False
    b) If the object's parameters have changed they will be updated and a revision logged
    c) New objects get marked as active = True automatically
    '''
    NEOCP_orb_url = 'http://cgi.minorplanetcenter.net/cgi-bin/showobsorbs.cgi?Obj=%s&orb=y' % obj_id

    neocp_obs_page = fetchpage_and_make_soup(NEOCP_orb_url)

    if neocp_obs_page:
        obs_page_list = neocp_obs_page.text.split('\n')
    else:
        return False

    try:
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
    except:
        logger.debug("Multiple objects found called %s" % obj_id)
        return False
# If the object has left the NEOCP, the HTML will say 'None available at this time.'
# and the length of the list will be 1
    if len(obs_page_list) > 1:
        # Clean up the header and top line of input
        first_kwargs = clean_NEOCP_object(obs_page_list)
        kwargs = first_kwargs.copy()
        kwargs.update(extra_params)
        if not created:
            # Find out if the details have changed, if they have, save a
            # revision
            check_body = Body.objects.filter(provisional_name=obj_id, **kwargs)
            if check_body.count() == 0:
                if save_and_make_revision(body, kwargs):
                    msg = "Updated %s" % obj_id
                else:
                    msg = "No changes saved for %s" % obj_id
            else:
                msg = "No changes needed for %s" % obj_id
        else:
            save_and_make_revision(body, kwargs)
            msg = "Added %s" % obj_id
    else:
        save_and_make_revision(body, {'active': False})
        msg = "Object %s no longer exists on the NEOCP." % obj_id
    logger.info(msg)
    return msg

def update_NEOCP_observations(obj_id, extra_params={}):
    '''Query the NEOCP for <obj_id> and download the observation lines.
    These are used to create Source Measurements for the body if the
    number of observations in the passed extra_params dictionary is greater than
    the number of Source Measurements for that Body'''

    try:
        body = Body.objects.get(provisional_name=obj_id)
        num_measures = SourceMeasurement.objects.filter(body=body).count()

# Check if the NEOCP has more measurements than we do
        if body.num_obs > num_measures:
            obs_lines = fetch_NEOCP_observations(obj_id)
            if obs_lines:
                measure = create_source_measurement(obs_lines)
                if measure == False:
                    msg = "Could not create source measurements for object %s (no or multiple Body's exist)" % obj_id
                else:
                    if len(measure) >0:
                        msg = "Created source measurements for object %s" % obj_id
                    elif len(measure) == 0:
                        msg = "Source measurements already exist for object %s" % obj_id
            else:
                msg = "No observations exist for object %s" % obj_id
        else:
            msg = "Object %s has not been updated since %s" % (obj_id, body.update_time)
    except Body.DoesNotExist:
        msg = "Object %s does not exist" % obj_id
    return msg

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
                # ...nope guess again... Could be missing RMS...
                try:
                    rms = float(current[15])
                except ValueError:
                     # Insert a high value for the missing rms
                    current.insert(15, 99.99)
                    logger.warn(
                        "Missing RMS for %s; assuming 99.99", current[0])
                except:
                    logger.error(
                        "Missing field in NEOCP orbit for %s which wasn't correctable", current[0])
            except ValueError:
                # Insert a high magnitude for the missing H
                current.insert(1, 99.99)
                logger.warn(
                    "Missing H magnitude for %s; assuming 99.99", current[0])
            except:
                logger.error(
                    "Missing field in NEOCP orbit for %s which wasn't correctable", current[0])

        if len(current) == 17:
            params = {
                'abs_mag': float(current[1]),
                'slope': float(current[2]),
                'epochofel': extract_mpc_epoch(current[3]),
                'meananom': float(current[4]),
                'argofperih': float(current[5]),
                'longascnode': float(current[6]),
                'orbinc': float(current[7]),
                'eccentricity': float(current[8]),
                'meandist': float(current[10]),
                'source_type': 'U',
                'elements_type': 'MPC_MINOR_PLANET',
                'active': True,
                'origin': 'M',
                'update_time' : datetime.utcnow()
            }
        elif len(current) == 22 or len(current) == 23 or len(current) == 24:
            params = {
                'abs_mag': float(current[1]),
                'slope': float(current[2]),
                'epochofel': extract_mpc_epoch(current[3]),
                'meananom': float(current[4]),
                'argofperih': float(current[5]),
                'longascnode': float(current[6]),
                'orbinc': float(current[7]),
                'eccentricity': float(current[8]),
                'meandist': float(current[10]),
                'source_type': 'U',
                'elements_type': 'MPC_MINOR_PLANET',
                'active': True,
                'origin': 'L',
                'provisional_name' : current[0],
                'num_obs' : int(current[13]),
                'update_time' : datetime.utcnow(),
                'arc_length' : None,
                'not_seen' : None
            }
            # If this is a find_orb produced orbit, try and fill in the
            # 'arc length' and 'not seen' values.
            arc_length = None
            arc_units = current[16]
            if arc_units == 'days':
                arc_length = float(current[15])
            elif arc_units == 'hrs':
                arc_length = float(current[15]) / 24.0
            elif arc_units == 'min':
                arc_length = float(current[15]) / 1440.0
            if arc_length:
                params['arc_length'] = arc_length
            try:
                not_seen = datetime.utcnow() - datetime.strptime(current[-1], '%Y%m%d')
                params['not_seen'] = not_seen.total_seconds() / 86400.0 # Leap seconds can go to hell...
            except:
                pass
        else:
            logger.warn(
                "Did not get right number of parameters for %s. Values %s", current[0], current)
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

    try:
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
    except:
        logger.debug("Multiple objects found called %s" % obj_id)
        return False
    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_crossid(astobj, dbg)
    if not created:
        if dbg:
            print "Did not create new Body"
        # Find out if the details have changed, if they have, save a revision
        check_body = Body.objects.filter(provisional_name=obj_id, **kwargs)
        if check_body.count() == 0:
            save_and_make_revision(body, kwargs)
            logger.info("Updated cross identification for %s" % obj_id)
    elif kwargs != {}:
        # Didn't know about this object before so create but make inactive
        kwargs['active'] = False
        save_and_make_revision(body, kwargs)
        logger.info("Added cross identification for %s" % obj_id)
    else:
        logger.warn("Could not add cross identification for %s" % obj_id)
        return False
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

    obj_id = astobj[0].rstrip()
    desig = astobj[1]
    reference = astobj[2]
    confirm_date = parse_neocp_date(astobj[3])

    time_from_confirm = datetime.utcnow() - confirm_date
    if time_from_confirm < timedelta(0):
        # if this is negative a date in the future has erroneously be assumed
        time_from_confirm = datetime.utcnow() - confirm_date.replace(year=confirm_date.year-1)
    time_from_confirm = time_from_confirm.total_seconds()

    active = True
    objtype = ''
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
        if ('CBET' in reference or 'IAUC' in reference or 'MPEC' in reference) and 'C/' in desig:
            # There is a reference to an CBET or IAUC so we assume it's "very
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

    if objtype != '':
        params = {'source_type': objtype,
                  'name': desig,
                  'active': active
                  }
        if dbg:
            print "%07s->%s (%s) %s" % (obj_id, params['name'], params['source_type'], params['active'])
    else:
        logger.warn("Unparseable cross-identification: %s" % astobj)
        params = {}

    return params


def clean_mpcorbit(elements, dbg=False, origin='M'):
    '''Takes a list of (proto) element lines from fetch_mpcorbit() and plucks
    out the appropriate bits. origin defaults to 'M'(PC) if not specified'''

    params = {}
    if elements != None:

        try:
            last_obs = datetime.strptime(elements['last observation date used'].replace('.0', ''), '%Y-%m-%d')
        except ValueError:
            last_obs = None

        try:
            first_obs = datetime.strptime(elements['first observation date used'].replace('.0', ''), '%Y-%m-%d')
        except ValueError:
            first_obs = None

        if 'arc length' in elements:
            arc_length = elements['arc length']
        else:
            arc_length = last_obs-first_obs
            arc_length = str(arc_length.days)

        # Common parameters
        params = {
            'epochofel': datetime.strptime(elements['epoch'].replace('.0', ''), '%Y-%m-%d'),
            'abs_mag': elements.get('absolute magnitude', None),
            'slope': elements.get('phase slope', 0.15),
            'meananom': elements['mean anomaly'],
            'argofperih': elements['argument of perihelion'],
            'longascnode': elements['ascending node'],
            'orbinc': elements['inclination'],
            'eccentricity': elements['eccentricity'],
            'meandist': elements['semimajor axis'],
            'source_type': determine_asteroid_type(float(elements['perihelion distance']), float(elements['eccentricity'])),
            'elements_type': 'MPC_MINOR_PLANET',
            'active': True,
            'origin': origin,
            'updated' : True,
            'num_obs' : elements['observations used'],
            'arc_length' : arc_length,
            'discovery_date' : first_obs,
            'update_time' : last_obs
        }

        if 'radial non-grav. param.' in elements:
            # Comet, update/overwrite a bunch of things
            params['elements_type'] = 'MPC_COMET'
            params['source_type'] = 'C'
            # The MPC never seems to have H values for comets so we remove it
            # from the dictionary to avoid replacing what was there before.
            if params['abs_mag'] == None:
                del params['abs_mag']
            params['slope'] = elements.get('phase slope', '4.0')
            params['perihdist'] = elements['perihelion distance']
            perihelion_date = elements['perihelion date'].replace('-', ' ')
            params['epochofperih'] = parse_neocp_decimal_date(perihelion_date)

        not_seen = None
        if last_obs != None:
            time_diff = datetime.utcnow() - last_obs
            not_seen = time_diff.total_seconds() / 86400.0
        params['not_seen'] = not_seen
    return params


def update_MPC_orbit(obj_id_or_page, dbg=False, origin='M'):
    '''
    Performs remote look up of orbital elements for object with id obj_id_or_page,
    Gets or creates corresponding Body instance and updates entry.
    Alternatively obj_id_or_page can be a BeautifulSoup object, in which case
    the call to fetch_mpcdb_page() will be skipped and the passed BeautifulSoup
    object will parsed.
    '''

    if type(obj_id_or_page) != BeautifulSoup:
        obj_id = obj_id_or_page
        page = fetch_mpcdb_page(obj_id, dbg)

        if page == None:
            logger.warn("Could not find elements for %s" % obj_id)
            return False
    else:
        page = obj_id_or_page

    elements = parse_mpcorbit(page, dbg)
    if type(obj_id_or_page) == BeautifulSoup:
        obj_id = elements['obj_id']
        del elements['obj_id']

    try:
        body, created = Body.objects.get_or_create(name=obj_id)
    except Body.MultipleObjectsReturned:
        # When the crossid happens we end up with multiple versions of the body.
        # Need to pick the one has been most recently updated
        bodies = Body.objects.filter(
            name=obj_id, provisional_name__isnull=False).order_by('-ingest')
        created = False
        if not bodies:
            bodies = Body.objects.filter(name=obj_id).order_by('-ingest')
        body = bodies[0]
    # If this object is a radar target and the requested origin is for the
    # "other" site (Goldstone ('G') when we have Arecibo ('A') or vice versa),
    # then set the origin to 'R' for joint Radar target.
    if (body.origin == 'G' and origin == 'A') or (body.origin == 'A' and origin == 'G'):
        origin = 'R'
    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_mpcorbit(elements, dbg, origin)
    # Save, make revision, or do not update depending on the what has happened
    # to the object
    save_and_make_revision(body, kwargs)
    if not created:
        logger.info("Updated elements for %s" % obj_id)
    else:
        logger.info("Added new orbit for %s" % obj_id)
    return True

def create_source_measurement(obs_lines, block=None):
    measures = []
    if type(obs_lines) != list:
        obs_lines = [obs_lines,]

    for obs_line in obs_lines:
        logger.debug(obs_line.rstrip())
        params = parse_mpcobs(obs_line)
        if params:
            try:
                # Try to unpack the name first
                try:
                    unpacked_name = packed_to_normal(params['body'])
                except PackedError:
                    unpacked_name = 'ZZZZZZ'
                obs_body = Body.objects.get(Q(provisional_name=params['body']) |
                                            Q(name=params['body']) |
                                            Q(name=unpacked_name)
                                           )
                # Identify block
                if not block:
                    blocks = Block.objects.filter(block_start__lte=params['obs_date'], block_end__gte=params['obs_date'], body=obs_body)
                    if blocks:
                        logger.info("Found %s blocks for %s" % (blocks.count(), obs_body))
                        block = blocks[0]
                    else:
                        logger.warn("No blocks for %s" % (obs_body))
                if params['obs_type'] == 's':
                    # If we have an obs_type of 's', then we have the second line
                    # of a satellite measurement and we need to find the matching
                    # Frame we created on the previous line read and update its
                    # extrainfo field.
                    try:
                        prior_frame = Frame.objects.get(frametype = Frame.SATELLITE_FRAMETYPE,
                                                        midpoint = params['obs_date'],
                                                        sitecode = params['site_code'])
                        prior_frame.extrainfo = params['extrainfo']
                        prior_frame.save()
                        # Replace SourceMeasurement in list to be returned with
                        # updated version
                        measures[-1] = SourceMeasurement.objects.get(pk=measures[-1].pk)
                    except Frame.DoesNotExist:
                        logger.warn("Matching satellite frame for %s from %s on %s does not exist" % params['body'], params['obs_date'],params['site_code'])
                    except Frame.MultipleObjectsReturned:
                        logger.warn("Multiple matching satellite frames for %s from %s on %s found" % params['body'], params['obs_date'],params['site_code'])
                else:
                    # Otherwise, make a new Frame and SourceMeasurement
                    frame = create_frame(params, block)
                    measure_params = {  'body'    : obs_body,
                                        'frame'   : frame,
                                        'obs_ra'  : params['obs_ra'],
                                        'obs_dec' : params['obs_dec'],
                                        'obs_mag' : params['obs_mag'],
                                        'astrometric_catalog' : params['astrometric_catalog'],
                                        'photometric_catalog' : params['astrometric_catalog'],
                                        'flags'   : params['flags']
                                     }
                    measure, measure_created = SourceMeasurement.objects.get_or_create(**measure_params)
                    if measure_created:
                        measures.append(measure)
            except Body.DoesNotExist:
                logger.debug("Body %s does not exist" % params['body'])
                measures = False
            except Body.MultipleObjectsReturned:
                logger.warn("Multiple versions of Body %s exist" % params['body'])
                measures = False

    return measures

def check_request_status(tracking_num=None):
    data = None
    client = requests.session()
    # First have to authenticate
    login_data = dict(username=settings.NEO_ODIN_USER, password=settings.NEO_ODIN_PASSWD)
    # Because we are sending log in details it has to go over SSL
    data_url = urljoin(settings.REQUEST_API_URL, tracking_num)
    try:
        resp = client.post(data_url, data=login_data, timeout=20)
        data = resp.json()
    except ValueError:
        logger.error("Request API did not return JSON")
    except requests.exceptions.Timeout:
        logger.error("Request API timed out")
    return data

def check_for_images(eventid=False):
    images = None
    client = requests.session()
    login_data = dict(username=settings.NEO_ODIN_USER, password=settings.NEO_ODIN_PASSWD)
    data_url = 'https://data.lcogt.net/find?blkuid=%s&order_by=-date_obs&full_header=1' % eventid
    try:
        resp = client.post(data_url, data=login_data, timeout=20)
        images = resp.json()
    except ValueError:
        logger.error("Request API did not return JSON %s" % resp.text)
    except requests.exceptions.Timeout:
        logger.error("Data view timed out")
    return images

def create_frame(params, block=None):
    # Return None if params is just whitespace
    if not params:
        return None
    our_site_codes = LCOGT_site_codes()
    if params.get('groupid', None):
    # In these cases we are parsing the FITS header
        frame_params = frame_params_from_block(params, block)
    else:
        # We are parsing observation logs
        frame_params = frame_params_from_log(params, block)
    frame, frame_created = Frame.objects.get_or_create(**frame_params)
    if frame_created:
        msg = "created"
    else:
        msg = "updated"
    logger.debug("Frame %s %s" % (frame, msg))
    return frame

def frame_params_from_block(params, block):
    # In these cases we are parsing the FITS header
    frame_params = { 'midpoint' : params.get('date_obs', None),
                     'sitecode' : LCOGT_domes_to_site_codes(params.get('siteid', None), params.get('encid', None), params.get('telid', None)),
                     'filter'   : params.get('filter_name', "B"),
                     'frametype': Frame.SINGLE_FRAMETYPE,
                     'block'    : block,
                     'instrument': params.get('instrume', None),
                     'filename'  : params.get('origname', None),
                     'exptime'   : params.get('exptime', None),
                 }
    return frame_params

def frame_params_from_log(params, block):
    our_site_codes = LCOGT_site_codes()
    # We are parsing observation logs
    sitecode = params.get('site_code', None)
    if sitecode in our_site_codes:
        if params.get('flags', None) != 'K':
            frame_type = Frame.SINGLE_FRAMETYPE
        else:
            frame_type = Frame.STACK_FRAMETYPE
    else:
        if params.get('obs_type', None) == 'S':
            frame_type = Frame.SATELLITE_FRAMETYPE
        else:
            frame_type = Frame.NONLCO_FRAMETYPE
    frame_params = { 'midpoint' : params.get('obs_date', None),
                     'sitecode' : sitecode,
                     'block'    : block,
                     'filter'   : params.get('filter', "B"),
                     'frametype' : frame_type
                   }
    return frame_params

def ingest_frames(images, block):
    for image in images:
        frame = create_frame(image, block)
    logger.debug("Ingested %s frames" % len(images))
    return

def block_status(block_id):
    '''
    Check if a block has been observed. If it has, record when the longest run finished
    - RequestDB API is used for block status
    - FrameDB API is used for number and datestamp of images
    - We do not count scheduler blocks which include < 3 exposures
    '''
    status = False
    try:
        block = Block.objects.get(id=block_id)
        tracking_num = block.tracking_number
    except ObjectDoesNotExist:
        logger.error("Block with id %s does not exist" % block_id)
        return False
    data = check_request_status(tracking_num)
    # data is a full LCOGT request dict for this tracking number.
    if not data:
        return False
    # The request dict has a schedule property which indicates the number so times the schedule has/will attempt it.
    # For each of these times find out if any data was taken and if it was close to what we wanted
    num_scheduled = 0 # Number of times the scheduler tried to observe this
    for k,v in data['requests'].items():
        logger.error('Request no. %s' % k)
        if not v['schedule']:
            logger.error('No schedule returned by API')
        for event in v['schedule']:
            images = check_for_images(eventid=event['id'])
            if images:
                num_scheduled += 1
                try:
                    last_image = datetime.strptime(images[0]['date_obs'][:19],'%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.error('Image datetime stamp is badly formatted %s' % images[0]['date_obs'])
                    return False
                if len(images) >= 3:
                    block.num_observed = num_scheduled
                    logger.error('Image %s x %s' % (event['id'], num_scheduled))
                    if (not block.when_observed or last_image > block.when_observed):
                        block.when_observed = last_image
                    if block.block_end < datetime.utcnow():
                        block.active = False
                    block.save()
                    status = True
                    logger.debug("Block %s updated" % block)
                    # Add frames
                    resp = ingest_frames(images, block)
                else:
                    logger.debug("No update to block %s" % block)
    return status
