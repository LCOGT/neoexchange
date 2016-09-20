'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import os
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
from django.http import Http404, HttpResponse
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
from astrometrics.time_subs import extract_mpc_epoch, parse_neocp_date, \
    parse_neocp_decimal_date, get_semester_dates, jd_utc2datetime
from photometrics.external_codes import run_sextractor, run_scamp, updateFITSWCS,\
    read_mtds_file
from photometrics.catalog_subs import open_fits_catalog, get_catalog_header, \
    determine_filenames, increment_red_level, update_ldac_catalog_wcs
from astrometrics.ast_subs import determine_asteroid_type, determine_time_of_perih
from core.frames import create_frame, fetch_observations, ingest_frames
import logging
import reversion
import json
import requests
from urlparse import urljoin
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)


class LoginRequiredMixin(object):

    #login_url = reverse('auth_login')

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)

def user_proposals(user):
    '''
    Returns active proposals the given user has permissions for
    '''
    if type(user) != User:
        try:
            user = User.objects.get(username=user)
        except ObjectDoesNotExist:
            raise ValidationError

    proposals = Proposal.objects.filter(proposalpermission__user=user, active=True)

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


class BlockTimeSummary(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        block_summary = summarise_block_efficiency()
        return render(request, 'core/block_time_summary.html', {'summary':json.dumps(block_summary)})

def summarise_block_efficiency():
    summary = []
    proposals = Proposal.objects.all()
    for proposal in proposals:
        blocks = Block.objects.filter(proposal=proposal)
        observed = blocks.filter(num_observed__isnull=False)
        if len(blocks) > 0:
            proposal_summary = {
                                 'proposal':proposal.code,
                                 'Observed' : observed.count(),
                                 'Not Observed' : blocks.count() - observed.count()
                               }
            summary.append(proposal_summary)
    return summary


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
        name = self.request.GET.get("q","")
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
        context['images'] = [{'img': img} for img in fetch_observations(context['block'].tracking_number)]
        return context


class BlockListView(ListView):
    model = Block
    template_name = 'core/block_list.html'
    queryset=Block.objects.order_by('-block_start')
    context_object_name="block_list"
    paginate_by = 20


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

class CandidatesViewBlock(LoginRequiredMixin, View):
    template = 'core/candidates.html'
    def get(self, request, *args, **kwargs):
       block = Block.objects.get(pk=kwargs['pk'])
       candidates = Candidate.objects.filter(block=block).order_by('score')
       return render(request, self.template, {'body':block.body,'candidates':candidates,'slot':block})

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
    # Determine the semester boundaries for the current time and truncate the dark time and
    # therefore the windows appropriately.
    semester_start, semester_end = get_semester_dates(datetime.utcnow())
    dark_start = max(dark_start, semester_start)
    dark_end = min(dark_end, semester_end)

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
        site_list = { 'V37' : 'ELP' , 'K92' : 'CPT' , 'K93' : 'CPT', 'Q63' : 'COJ', 'W85' : 'LSC', 'W86' : 'LSC', 'F65' : 'OGG', 'E10' : 'COJ' }

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
                'update_time' : datetime.utcnow(),
                'arc_length' : None,
                'not_seen' : None
            }
            arc_length = None
            arc_units = current[14]
            if arc_units == 'days':
                arc_length = float(current[13])
            elif arc_units == 'hrs':
                arc_length = float(current[13]) / 24.0
            elif arc_units == 'min':
                arc_length = float(current[13]) / 1440.0
            if arc_length:
                params['arc_length'] = arc_length

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
        if params != {}:
            # Check for objects that should be treated as comets (e>0.9)
            if params['eccentricity'] > 0.9:

                if params['slope'] == 0.15:
                    params['slope'] = 4.0
                params['elements_type'] = 'MPC_COMET'
                params['perihdist'] = params['meandist'] * (1.0 - params['eccentricity'])
                params['epochofperih'] = determine_time_of_perih(params['meandist'], params['meananom'], params['epochofel'])
                params['meananom'] = None
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
        # But first check if it is a comet or NEO and came from somewhere other
        # than the MPC. In this case, leave it active.
        if body.source_type in ['N', 'C'] and body.origin != 'M':
            kwargs['active'] = True
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

    obj_id = None
    if type(obj_id_or_page) != BeautifulSoup:
        obj_id = obj_id_or_page
        page = fetch_mpcdb_page(obj_id, dbg)

        if page == None:
            logger.warn("Could not find elements for %s" % obj_id)
            return False
    else:
        page = obj_id_or_page

    elements = parse_mpcorbit(page, dbg)
    if elements == {}:
        logger.warn("Could not parse elements from page for %s" % obj_id)
        return False

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
                        if prior_frame.extrainfo != params['extrainfo']:
                            prior_frame.extrainfo = params['extrainfo']
                            prior_frame.save()
                        if len(measures) > 0:
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

def determine_original_name(fits_file):
    '''Determines the ORIGNAME for the FITS file <fits_file>.
    This is pretty disgusting and a sign we are probably doing something wrong
    and should store the true filename but at least it's contained to one place
    now...'''
    fits_file_orig = fits_file
    if 'e90.fits' in os.path.basename(fits_file):
        fits_file_orig = os.path.basename(fits_file.replace('e90.fits', 'e00.fits'))
    elif 'e10.fits' in os.path.basename(fits_file):
        fits_file_orig = os.path.basename(fits_file.replace('e10.fits', 'e00.fits'))
    elif 'e91.fits' in os.path.basename(fits_file):
        fits_file_orig = os.path.basename(fits_file.replace('e91.fits', 'e00.fits'))
    elif 'e11.fits' in os.path.basename(fits_file):
        fits_file_orig = os.path.basename(fits_file.replace('e11.fits', 'e00.fits'))
    return fits_file_orig

def check_catalog_and_refit(configs_dir, dest_dir, catfile, dbg=False):
    '''Checks the astrometric fit status of <catfile> and performs a source
    extraction and refit if it is bad. The name of the newly created FITS LDAC
    catalog from this process is returned or an integer status code if no
    fit was needed or could not be performed.'''

    num_new_frames_created = 0

    # Open catalog, get header and check fit status
    fits_header, junk_table, cattype = open_fits_catalog(catfile, header_only=True)
    header = get_catalog_header(fits_header, cattype)
    if header != {}:
        logger.debug("astrometric fit status=%d" %  header['astrometric_fit_status'])
        fits_file = determine_filenames(catfile)
        if header['astrometric_fit_status'] != 0:
            if fits_file == None:
                logger.error("Could not determine matching image for %s" % catfile)
                return -1, num_new_frames_created
            fits_file = os.path.join(os.path.dirname(catfile), fits_file)
            if os.path.exists(fits_file) == False or os.path.isfile(fits_file) == False:
                logger.error("Could not open matching image %s for catalog %s" % ( fits_file, catfile))
                return -1, num_new_frames_created
            logger.debug("Running SExtractor on: %s" % fits_file)
            sext_status = run_sextractor(configs_dir, dest_dir, fits_file, catalog_type='FITS_LDAC')
            if sext_status == 0:
                fits_ldac_catalog ='test_ldac.fits'
                logger.debug("Running SCAMP")
                scamp_status = run_scamp(configs_dir, dest_dir, fits_ldac_catalog, dbg)

                if scamp_status == 0:
                    scamp_file = os.path.basename(fits_ldac_catalog).replace('.fits', '.head' )
                    scamp_file = os.path.join(dest_dir, scamp_file)
                    scamp_xml_file = os.path.join(dest_dir, 'scamp.xml')

                    # Update WCS in image file
                    # Get new output filename
                    fits_file_output = increment_red_level(fits_file)
                    fits_file_output = os.path.join(dest_dir, fits_file_output)
                    logger.debug("Updating bad WCS in image file: %s" % fits_file_output)
                    status = updateFITSWCS(fits_file, scamp_file, scamp_xml_file, fits_file_output)

                    #if a Frame does not exist for the fits file with a non-null block
                    #create one with the fits filename
                    if len(Frame.objects.filter(filename=os.path.basename(fits_file_output), block__isnull=False)) < 1:
                        fits_file_orig = determine_original_name(fits_file)
                        try:
                            frame = Frame.objects.get(filename=fits_file_orig, block__isnull=False)
                        except Frame.MultipleObjectsReturned:
                            logger.error("Found multiple versions of fits frame %s pointing at multiple blocks %s" %(fits_file_output, frames_with_blocks))
                            return -3, num_new_frames_created
                        except Frame.DoesNotExist:
                            logger.error("Frame entry for fits file %s does not exist" % fits_file_output)
                            return -3, num_new_frames_created

                        #Create a new Frame entry for new fits_file_output name
                        frame_params = {    'sitecode':header['site_code'],
                                            'instrument':header['instrument'],
                                            'filter':header['filter'],
                                            'filename':os.path.basename(fits_file_output),
                                            'exptime':header['exptime'],
                                            'midpoint':header['obs_midpoint'],
                                            'block':frame.block,
                                            'zeropoint':header.get('zeropoint', -99),
                                            'zeropoint_err':header.get('zeropoint_err', -99),
                                            'fwhm':header['fwhm'],
                                            'frametype':Frame.SINGLE_FRAMETYPE,
                                            'rms_of_fit':header['astrometric_fit_rms'],
                                            'nstars_in_fit':header['astrometric_fit_nstars'],
                                        }

                        frame, created = Frame.objects.get_or_create(**frame_params)
                        if created == True:
                            num_new_frames_created += 1

                    # Update RA, Dec columns in LDAC catalog file
                    logger.debug("Updating RA, Dec in LDAC catalog file: %s" % fits_ldac_catalog )
                    fits_ldac_catalog_path = os.path.join(dest_dir, fits_ldac_catalog)
                    update_ldac_catalog_wcs(fits_file_output, fits_ldac_catalog_path, overwrite=True)

                    # Rename catalog to permanent name
                    new_ldac_catalog = os.path.join(dest_dir, fits_file_output.replace('.fits', '_ldac.fits'))
                    logger.debug("Renaming %s to %s" % (fits_ldac_catalog_path, new_ldac_catalog ))
                    os.rename(fits_ldac_catalog_path, new_ldac_catalog)
                else:
                    logger.error("Execution of SCAMP failed")
                    return -4, 0
            else:
                logger.error("Execution of SExtractor failed")
                return -4, 0
        else:
            # Astrometric fit was good
            if cattype == 'BANZAI':
                # Need to re-extract catalog
                fits_file = os.path.join(os.path.dirname(catfile), fits_file)
                if os.path.exists(fits_file) == False or os.path.isfile(fits_file) == False:
                    logger.error("Could not open matching image %s for catalog %s" % ( fits_file, catfile))
                    return -1, num_new_frames_created
                fits_file_for_sext = fits_file + "[SCI]"
                logger.debug("Running SExtractor on BANZAI file: %s" % fits_file_for_sext)
                sext_status = run_sextractor(configs_dir, dest_dir, fits_file_for_sext, catalog_type='FITS_LDAC')
                if sext_status == 0:
                    fits_ldac_catalog ='test_ldac.fits'
                    fits_ldac_catalog_path = os.path.join(dest_dir, fits_ldac_catalog)
                    fits_file_output = os.path.basename(fits_file)
                    fits_file_output = os.path.join(dest_dir, fits_file_output)

                    # Rename catalog to permanent name
                    new_ldac_catalog = os.path.join(dest_dir, fits_file_output.replace('.fits', '_ldac.fits'))
                    logger.debug("Renaming %s to %s" % (fits_ldac_catalog_path, new_ldac_catalog ))
                    os.rename(fits_ldac_catalog_path, new_ldac_catalog)

                else:
                    logger.error("Execution of SExtractor failed")
                    return -4, 0
            else:
                logger.info("Catalog %s already has good WCS fit status" % catfile)
                return 0, num_new_frames_created

            #if a Frame does not exist for the fits file with a non-null block
            #create one with the fits filename
            if len(Frame.objects.filter(filename=os.path.basename(fits_file), block__isnull=False)) < 1:
                #create a new Frame even if WCS fit is good in order to have the real fits filename in the Frame
                fits_file_orig = determine_original_name(fits_file)
                try:
                    frame = Frame.objects.get(filename=fits_file_orig, block__isnull=False)
                except Frame.MultipleObjectsReturned:
                    logger.error("Found multiple versions of fits frame %s pointing at multiple blocks %s" % (fits_file_orig, frames_with_blocks))
                    return -3, num_new_frames_created
                except Frame.DoesNotExist:
                    logger.error("Frame entry for fits file %s does not exist" % fits_file_orig)
                    return -3, num_new_frames_created

                #Create a new Frame entry for new fits_file_output name
                frame_params = {    'sitecode':header['site_code'],
                                    'instrument':header['instrument'],
                                    'filter':header['filter'],
                                    'filename':os.path.basename(fits_file),
                                    'exptime':header['exptime'],
                                    'midpoint':header['obs_midpoint'],
                                    'block':frame.block,
                                    'zeropoint':header['zeropoint'],
                                    'zeropoint_err':header['zeropoint_err'],
                                    'fwhm':header['fwhm'],
                                    'frametype':Frame.SINGLE_FRAMETYPE,
                                    'rms_of_fit':header['astrometric_fit_rms'],
                                    'nstars_in_fit':header['astrometric_fit_nstars'],
                                }

                frame, created = Frame.objects.get_or_create(**frame_params)
                if created == True:
                    num_new_frames_created += 1
    else:
        logger.error("Could not check catalog %s" % catfile)
        return -2, num_new_frames_created

    return new_ldac_catalog, num_new_frames_created

def store_detections(mtdsfile, dbg=False):

    moving_objects = read_mtds_file(mtdsfile)
    if moving_objects != {} and len(moving_objects.get('detections', [])) > 0:
        det_frame = moving_objects['frames'][0]
        try:
            frame = Frame.objects.get(filename=det_frame[0], block__isnull=False)
        except Frame.MultipleObjectsReturned:
            logger.error("Frame %s exists multiple times" % det_frame[0])
            return None
        except Frame.DoesNotExist:
            logger.error("Frame %s does not exist" % det_frame[0])
            return None
        jds = np.array([x[1] for x in moving_objects['frames']], dtype=np.float64)
        mean_jd = jds.mean(dtype=np.float64)
        mean_dt = jd_utc2datetime(mean_jd)
        for candidate in moving_objects['detections']:
            # These parameters are the same for all frames and do not need
            # averaging
            score = candidate[0]['score']
            speed = candidate[0]['velocity']
            sky_position_angle = candidate[0]['sky_pos_angle']
            # These need averaging across the frames. Accumulate means as doubles
            # (float64) to avoid loss of precision.
            mean_ra = candidate['ra'].mean(dtype=np.float64) * 15.0
            mean_dec = candidate['dec'].mean(dtype=np.float64)
            mean_x = candidate['x'].mean(dtype=np.float64)
            mean_y = candidate['y'].mean(dtype=np.float64)
            # Need to construct a masked array for the magnitude to avoid
            # problems with 0.00 values
            mag = np.ma.masked_array(candidate['mag'], mask=candidate['mag'] <= 0.0)
            mean_mag = mag.mean(dtype=np.float64)

            try:
                cand = Candidate.objects.get(block=frame.block, cand_id=candidate['det_number'][0], avg_midpoint=mean_dt, score=score,\
                        avg_x=mean_x, avg_y=mean_y,avg_ra=mean_ra, avg_dec=mean_dec, avg_mag=mean_mag, speed=speed,\
                        sky_motion_pa=sky_position_angle)
                if cand.detections!=candidate.tostring():
                    cand.detections=candidate.tostring()
                    cand.save()
            except Candidate.MultipleObjectsReturned:
                pass
            except Candidate.DoesNotExist:
                # Store candidate moving object
                params = {  'block' : frame.block,
                            'cand_id' : candidate['det_number'][0],
                            'avg_midpoint' : mean_dt,
                            'score' : score,
                            'avg_x' : mean_x,
                            'avg_y' : mean_y,
                            'avg_ra' : mean_ra,
                            'avg_dec' : mean_dec,
                            'avg_mag' : mean_mag,
                            'speed' : speed,
                            'sky_motion_pa' : sky_position_angle,
                            'detections' : candidate.tostring()
                        }
                if dbg: print params
                cand, created = Candidate.objects.get_or_create(**params)
                if dbg: print cand, created

    return

def make_plot(request):

    import matplotlib
    matplotlib.use('Agg')
    import aplpy
    import io

    fits_file = 'cpt1m010-kb70-20160428-0148-e91.fits'
    fits_filepath = os.path.join('/tmp', 'tmp_neox_9nahRl', fits_file)

    sources = CatalogSources.objects.filter(frame__filename__contains=fits_file[0:28]).values_list('obs_ra', 'obs_dec')

    fig = aplpy.FITSFigure(fits_filepath)
    fig.show_grayscale(pmin=0.25, pmax=98.0)
    ra = [X[0] for X in sources]
    dec = [X[1] for X in sources]

    fig.show_markers(ra, dec, edgecolor='green', facecolor='none', marker='o', s=15, alpha=0.5)

    buffer = io.BytesIO()
    fig.save(buffer, format='png')
    fig.save(fits_filepath.replace('.fits', '.png'), format='png')

    return HttpResponse(buffer.getvalue(), content_type="Image/png")

def plotframe(request):

    return render(request, 'core/frame_plot.html')
