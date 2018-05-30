"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
from datetime import datetime, timedelta, date
from math import floor, ceil
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
from django.http import Http404, HttpResponse, HttpResponseRedirect
from http.client import HTTPSConnection
from bs4 import BeautifulSoup
import urllib
from astrometrics.ephem_subs import call_compute_ephem, compute_ephem, \
    determine_darkness_times, determine_slot_length, determine_exp_time_count, \
    MagRangeError,  LCOGT_site_codes, LCOGT_domes_to_site_codes, \
    determine_spectro_slot_length
from .forms import EphemQuery, ScheduleForm, ScheduleCadenceForm, ScheduleBlockForm, \
    ScheduleSpectraForm, MPCReportForm, SpectroFeasibilityForm
from .models import *
from astrometrics.sources_subs import fetchpage_and_make_soup, packed_to_normal, \
    fetch_mpcdb_page, parse_mpcorbit, submit_block_to_scheduler, parse_mpcobs,\
    fetch_NEOCP_observations, PackedError, fetch_filter_list
from astrometrics.time_subs import extract_mpc_epoch, parse_neocp_date, \
    parse_neocp_decimal_date, get_semester_dates, jd_utc2datetime
from photometrics.external_codes import run_sextractor, run_scamp, updateFITSWCS,\
    read_mtds_file
from photometrics.catalog_subs import open_fits_catalog, get_catalog_header, \
    determine_filenames, increment_red_level, update_ldac_catalog_wcs, FITSHdrException
from photometrics.photometry_subs import calc_asteroid_snr, calc_sky_brightness
from astrometrics.ast_subs import determine_asteroid_type, determine_time_of_perih, \
    convert_ast_to_comet
from core.frames import create_frame, ingest_frames, measurements_from_block
from core.mpc_submit import email_report_to_mpc
import logging
import reversion
import json
import requests
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)


class LoginRequiredMixin(object):

    # login_url = reverse('auth_login')

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)


def user_proposals(user):
    """
    Returns active proposals the given user has permissions for
    """
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
        block_summary = summarise_block_efficiency(block_filter=10)
        return render(request, 'core/block_time_summary.html', {'summary': json.dumps(block_summary)})


def summarise_block_efficiency(block_filter=0):
    summary = []
    proposals = Proposal.objects.all()
    for proposal in proposals:
        blocks = Block.objects.filter(proposal=proposal)
        observed = blocks.filter(num_observed__isnull=False)
        if len(blocks) > block_filter:
            proposal_summary = {
                                 'proposal': proposal.code,
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
        context['taxonomies'] = SpectralInfo.objects.filter(body=self.object)
        context['spectra'] = sort_previous_spectra(self)
        return context


def sort_previous_spectra(self, **kwargs):
    spectra_of_interest = PreviousSpectra.objects.filter(body=self.object)
    spectra_out = []
    vis_count = 0
    nir_count = 0
    for s in spectra_of_interest:
        if s.spec_source == 'M':
            spectra_out.append(s)
        elif s.spec_source == 'S':
            if spectra_of_interest.filter(spec_wav='Vis+NIR').count() > 0:
                if s.spec_wav == 'Vis+NIR':
                    spectra_out.append(s)
            else:
                if vis_count == 0 and s.spec_wav == 'Vis':
                    vis_count = 1
                    spectra_out.append(s)
                if nir_count == 0 and s.spec_wav == 'NIR':
                    nir_count = 1
                    s.spec_vis = s.spec_ir
                    spectra_out.append(s)
    return spectra_out


class BodySearchView(ListView):
    template_name = 'core/body_list.html'
    model = Body

    def get_queryset(self):
        name = self.request.GET.get("q", "")
        if name != '':
            if name.isdigit():
                object_list = self.model.objects.filter(name=name)
            else:
                object_list = self.model.objects.filter(Q(provisional_name__icontains=name) | Q(provisional_packed__icontains=name) | Q(name__icontains=name))
        else:
            object_list = self.model.objects.all()
        return object_list


class BlockDetailView(DetailView):
    template_name = 'core/block_detail.html'
    model = Block


class SuperBlockDetailView(DetailView):
    template_name = 'core/block_detail.html'
    model = SuperBlock


class BlockListView(ListView):
    model = Block
    template_name = 'core/block_list.html'
    queryset = Block.objects.order_by('-block_start')
    context_object_name = "block_list"
    paginate_by = 20


class SuperBlockListView(ListView):
    model = SuperBlock
    template_name = 'core/block_list.html'
    queryset = SuperBlock.objects.order_by('-block_start')
    context_object_name = "block_list"
    paginate_by = 20


class BlockReport(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        if block.when_observed:
            block.active = False
            block.reported = True
            block.when_reported = datetime.utcnow()
            block.save()
            return redirect(reverse('blocklist'))
        else:
            messages.error(request, 'Block does not have any observations')
            return HttpResponseRedirect(reverse('block-view', kwargs={'pk': block.superblock.id}))


class BlockReportMPC(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        if block.reported is True:
            messages.error(request, 'Block has already been reported')
            return HttpResponseRedirect(reverse('block-report-mpc', kwargs={'pk': kwargs['pk']}))
        if request.user.is_authenticated:
            email = request.user.email
        else:
            email = None
        mpc_resp = email_report_to_mpc(blockid=kwargs['pk'], bodyid=kwargs.get('source', None), email_sender=email)
        if mpc_resp:
            block.active = False
            block.reported = True
            block.when_reported = datetime.utcnow()
            block.save()
            return redirect(reverse('blocklist'))
        else:
            messages.error(request, 'It was not possible to email report to MPC')
            return HttpResponseRedirect(reverse('block-report-mpc', kwargs={'pk': kwargs['pk']}))


class UploadReport(LoginRequiredMixin, FormView):
    template_name = 'core/uploadreport.html'
    success_url = reverse_lazy('blocklist')
    form_class = MPCReportForm

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        form = MPCReportForm(initial={'block_id': block.id})
        return render(request, 'core/uploadreport.html', {'form': form, 'slot': block})

    def form_invalid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        slot = Block.objects.get(pk=form['block_id'].value())
        return render(context['view'].request, 'core/uploadreport.html', {'form': form, 'slot': slot})

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
        data = measurements_from_block(blockid=kwargs['pk'])
        return render(request, self.template, data)


class MeasurementViewBody(View):
    template = 'core/measurements.html'

    def get(self, request, *args, **kwargs):
        body = Body.objects.get(pk=kwargs['pk'])
        measures = SourceMeasurement.objects.filter(body=body).order_by('frame__midpoint')
        return render(request, self.template, {'body': body, 'measures' : measures})


class CandidatesViewBlock(LoginRequiredMixin, View):
    template = 'core/candidates.html'

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        candidates = Candidate.objects.filter(block=block).order_by('score')
        return render(request, self.template, {'body': block.body, 'candidates': candidates, 'slot': block})


def generate_new_candidate_id(prefix='LNX'):

    new_id = None
    qs = Body.objects.filter(origin='L', provisional_name__contains=prefix).order_by('provisional_name')

    if qs.count() == 0:
        # No discoveries so far, sad face
        num_zeros = 7 - len(prefix)
        new_id = "%s%0.*d" % (prefix, num_zeros, 1)
    else:
        last_body_id = qs.last().provisional_name
        try:
            last_body_num = int(last_body_id.replace(prefix, ''))
            new_id_num = last_body_num + 1
            num_zeros = 7 - len(prefix)
            new_id = "%s%0.*d" % (prefix, num_zeros, new_id_num)
        except ValueError:
            logger.warning("Unable to decode last discoveries' id (id=%s)" % last_body_id)
    return new_id


def generate_new_candidate(cand_frame_data, prefix='LNX'):

    new_body = None
    new_id = generate_new_candidate_id(prefix)
    first_frame = cand_frame_data.order_by('midpoint')[0]
    last_frame = cand_frame_data.latest('midpoint')
    if new_id:
        try:
            time_span = last_frame.midpoint - first_frame.midpoint
            arc_length = time_span.total_seconds() / 86400.0
        except:
            arc_length = None

        params = {  'provisional_name' : new_id,
                    'origin' : 'L',
                    'source_type' : 'U',
                    'discovery_date' : first_frame.midpoint,
                    'num_obs' : cand_frame_data.count(),
                    'arc_length' : arc_length
                 }
        new_body, created = Body.objects.get_or_create(**params)
        if created:
            not_seen = datetime.utcnow() - last_frame.midpoint
            not_seen_days = not_seen.total_seconds() / 86400.0
            new_body.not_seen = not_seen_days
            new_body.save()
    else:
        logger.warning("Could not determine a new id for the new object")

    return new_body


def ephemeris(request):

    form = EphemQuery(request.GET)
    ephem_lines = []
    if form.is_valid():
        data = form.cleaned_data
        body_elements = model_to_dict(data['target'])
        dark_start, dark_end = determine_darkness_times(
            data['site_code'], data['utc_date'])
        ephem_lines = call_compute_ephem(
            body_elements, dark_start, dark_end, data['site_code'], 900, data['alt_limit'])
    else:
        return render(request, 'core/home.html', {'form': form})
    return render(request, 'core/ephem.html',
                  {'target': data['target'],
                   'ephem_lines': ephem_lines,
                   'site_code': form['site_code'].value(),
                   }
                  )


class LookUpBodyMixin(object):
    """
    A Mixin for finding a Body from a pk and if it exists, return the Body instance.
    """
    def dispatch(self, request, *args, **kwargs):
        try:
            body = Body.objects.get(pk=kwargs['pk'])
            self.body = body
            return super(LookUpBodyMixin, self).dispatch(request, *args, **kwargs)
        except Body.DoesNotExist:
            raise Http404("Body does not exist")


class ScheduleParameters(LoginRequiredMixin, LookUpBodyMixin, FormView):
    """
    Creates a suggested observation request, including time window and molecules
    """
    template_name = 'core/schedule.html'
    form_class = ScheduleForm
    ok_to_schedule = False

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        cadence_form = ScheduleCadenceForm()
        return self.render_to_response(self.get_context_data(form=form, cad_form=cadence_form, body=self.body))

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
        """
        Only show proposals the current user is a member of
        """
        proposals = user_proposals(self.request.user)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        kwargs['form'].fields['proposal_code'].choices = proposal_choices
        if kwargs['cad_form']:
            kwargs['cad_form'].fields['proposal_code'].choices = proposal_choices
        return kwargs


class ScheduleParametersCadence(LoginRequiredMixin, LookUpBodyMixin, FormView):
    """
    Creates a suggested cadenced observation request, including time window and molecules
    """
    template_name = 'core/schedule.html'
    form_class = ScheduleCadenceForm
    ok_to_schedule = False

    def post(self, request, *args, **kwargs):
        form = ScheduleCadenceForm(request.POST)
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.render_to_response(self.get_context_data(form=form, body=self.body))

    def form_valid(self, form, request):
        data = schedule_check(form.cleaned_data, self.body, self.ok_to_schedule)
        new_form = ScheduleBlockForm(data)
        return render(request, 'core/schedule_confirm.html', {'form': new_form, 'data': data, 'body': self.body})


class ScheduleParametersSpectra(LoginRequiredMixin, LookUpBodyMixin, FormView):
    """
    Creates a suggested spectroscopic observation request, including time window,
    calibrations and molecules
    """
    template_name = 'core/schedule_spectra.html'
    form_class = ScheduleSpectraForm
    ok_to_schedule = False

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        return self.render_to_response(self.get_context_data(form=form, body=self.body))

    def post(self, request, *args, **kwargs):
        form = ScheduleSpectraForm(request.POST)
        if form.is_valid():
            return self.form_valid(form,request)
        else:
            return self.render_to_response(self.get_context_data(form=form, body=self.body))

    def form_valid(self, form, request):
        data = schedule_check(form.cleaned_data, self.body, self.ok_to_schedule)
        new_form = ScheduleBlockForm(data)
        return render(request, 'core/schedule_confirm.html', {'form': new_form, 'data': data, 'body': self.body})

    def get_context_data(self, **kwargs):
        """
        Only show proposals the current user is a member of
        """
        proposals = user_proposals(self.request.user)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        kwargs['form'].fields['proposal_code'].choices = proposal_choices
        return kwargs


class ScheduleSubmit(LoginRequiredMixin, SingleObjectMixin, FormView):
    """
    Takes the hidden form input from ScheduleParameters, validates them as a double check.
    Then submits to the scheduler. If a tracking number is returned, the object has been scheduled and we record a Block.
    """
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
            # Recalculate the parameters by amending the block length
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
                messages.success(self.request, "Request %s successfully submitted to the scheduler" % tracking_num)
                block_resp = record_block(tracking_num, sched_params, form.cleaned_data, target)
                if block_resp:
                    messages.success(self.request, "Block recorded")
                else:
                    messages.warning(self.request, "Record not created")
            else:
                msg = "It was not possible to submit your request to the scheduler."
                if sched_params.get('error_msg', None):
                    msg += "\nAdditional information:" + sched_params['error_msg']
                messages.warning(self.request, msg)
            return super(ScheduleSubmit, self).form_valid(form)

    def get_success_url(self):
        return reverse('home')


def schedule_check(data, body, ok_to_schedule=True):

    spectroscopy = data.get('spectroscopy', False)
    body_elements = model_to_dict(body)

    if spectroscopy:
        data['site_code'] = data['instrument_code'][0:3]
    else:
        data['instrument_code'] = ''

    # Check if we have a high eccentricity object and it's not of comet type
    if body_elements['eccentricity'] >= 0.9 and body_elements['elements_type'] != 'MPC_COMET':
        logger.warning("Preventing attempt to schedule high eccentricity non-Comet")
        ok_to_schedule = False

    # Check for valid proposal
    # validate_proposal_time(data['proposal_code'])

    # Determine magnitude
    if data.get('start_time') and data.get('end_time'):
        dark_start = data.get('start_time')
        dark_end = data.get('end_time')
        utc_date = data.get('utc_date', dark_start.date())
    else:
        dark_start, dark_end = determine_darkness_times(data['site_code'], data['utc_date'])
        utc_date = data['utc_date']
        if dark_end <= datetime.utcnow():
            dark_start, dark_end = determine_darkness_times(data['site_code'], data['utc_date'] + timedelta(days=1))
            utc_date = data['utc_date'] + timedelta(days=1)
    # Determine the semester boundaries for the current time and truncate the dark time and
    # therefore the windows appropriately.
    semester_date = max(datetime.utcnow(), datetime.combine(utc_date, datetime.min.time()))
    semester_start, semester_end = get_semester_dates(semester_date)
    if dark_start.day != dark_end.day and semester_start < dark_start:
        semester_date = max(datetime.utcnow(), datetime.combine(utc_date, datetime.min.time()) - timedelta(days=1))
        semester_start, semester_end = get_semester_dates(semester_date)
    dark_start = max(dark_start, semester_start)
    dark_end = min(dark_end, semester_end)

    dark_midpoint = dark_start + (dark_end - dark_start) / 2
    emp = compute_ephem(dark_midpoint, body_elements, data['site_code'],
        dbg=False, perturb=False, display=False)
    if emp == []:
        emp = [-99 for x in range(5)]
    magnitude = emp[3]
    speed = emp[4]
    
    # Determine filter pattern
    if data.get('filter_pattern'):
        filter_pattern = data.get('filter_pattern')
    elif data['site_code'] == 'E10' or data['site_code'] == 'F65':
        if spectroscopy:
            filter_pattern = 'slit_6.0as'
        else:
            filter_pattern = 'solar'
    else:
        filter_pattern = 'w'

    # Get string of available filters
    available_filters = ''
    filter_list = fetch_filter_list(data['site_code'], spectroscopy)
    for filt in filter_list:
        available_filters = available_filters + filt + ', '
    available_filters = available_filters[:-2]

    # Determine slot length
    if data.get('slot_length'):
        slot_length = data.get('slot_length')
    else:
        if spectroscopy:
            slot_length = determine_spectro_slot_length(data['exp_length'], data['calibs'])
            slot_length /= 60.0
            slot_length = ceil(slot_length)
        else:
            try:
                slot_length = determine_slot_length(magnitude, data['site_code'])
            except MagRangeError:
                slot_length = 0.
                ok_to_schedule = False
    snr = None
    if spectroscopy:
        new_mag, new_passband, snr = calc_asteroid_snr(magnitude, 'V', data['exp_length'], instrument=data['instrument_code'])
        exp_count = data['exp_count']
        exp_length = data.get('exp_length', 1)
    else:
        # Determine exposure length and count
        exp_length, exp_count = determine_exp_time_count(speed, data['site_code'], slot_length, magnitude, filter_pattern)
        if exp_length is None or exp_count is None:
            ok_to_schedule = False

    # Determine pattern iterations
    if exp_count:
        pattern_iterations = float(exp_count) / float(len(filter_pattern.split(',')))
        pattern_iterations = round(pattern_iterations, 2)
    else:
        pattern_iterations = None

    # Get period and jitter for cadence
    period = data.get('period', None)
    jitter = data.get('jitter', None)

    if period and jitter:
        # Number of times the cadence request will run between start and end date
        cadence_start = data['start_time']
        cadence_end = data['end_time']
        total_run_time = cadence_end - cadence_start
        cadence_period = timedelta(seconds=data['period']*3600.0)
        total_requests = 1 + int(floor(total_run_time.total_seconds() / cadence_period.total_seconds()))
        # Remove the last start if the request would run past the cadence end
        if cadence_start + total_requests * cadence_period + timedelta(seconds=slot_length*60.0) > cadence_end:
            total_requests -= 1

        # Total hours of time used by all cadence requests
        total_time = timedelta(seconds=slot_length*60.0) * total_requests
        total_time = total_time.total_seconds()/3600.0

    suffix = datetime.strftime(utc_date, '%Y%m%d')
    if period and jitter:
        suffix = "cad-%s-%s" % (datetime.strftime(data['start_time'], '%Y%m%d'), datetime.strftime(data['end_time'], '%m%d'))
        if len(body.current_name()) > 7:
            # Name is too long to fit in the groupid field, trim off year part.
            suffix = "cad-%s-%s" % (datetime.strftime(data['start_time'], '%m%d'), datetime.strftime(data['end_time'], '%m%d'))
    elif spectroscopy:
        suffix += "_spectra"
    resp = {
        'target_name': body.current_name(),
        'magnitude': magnitude,
        'speed': speed,
        'slot_length': slot_length,
        'filter_pattern': filter_pattern,
        'pattern_iterations': pattern_iterations,
        'available_filters': available_filters,
        'exp_count': exp_count,
        'exp_length': exp_length,
        'schedule_ok': ok_to_schedule,
        'site_code': data['site_code'],
        'proposal_code': data['proposal_code'],
        'group_id': body.current_name() + '_' + data['site_code'].upper() + '-' + suffix,
        'utc_date': utc_date.isoformat(),
        'start_time': dark_start.isoformat(),
        'end_time': dark_end.isoformat(),
        'mid_time': dark_midpoint.isoformat(),
        'ra_midpoint': emp[1],
        'dec_midpoint': emp[2],
        'period' : period,
        'jitter' : jitter,
        'snr' : snr,
        'spectroscopy' : spectroscopy,
        'calibs' : data.get('calibs', ''),
        'instrument_code' : data['instrument_code']
    }

    if period and jitter:
        resp['num_times'] = total_requests
        resp['total_time'] = total_time

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

              'filter_pattern': data['filter_pattern'],
              'exp_count': data['exp_count'],
              'exp_time': data['exp_length'],
              'site_code': data['site_code'],
              'start_time': data['start_time'],
              'end_time': data['end_time'],
              'group_id': data['group_id'],

              'spectroscopy' : data.get('spectroscopy', False),
              'calibs' : data.get('calibs', ''),
              'instrument_code' : data['instrument_code']
              }
    if data['period'] or data['jitter']:
        params['period'] = data['period']
        params['jitter'] = data['jitter']
    # Check for pre-existing block
    tracking_number = None
    resp_params = None
    if check_for_block(data, params, body) == 1:
        # Append another suffix to allow 2 versions of the block. Must
        # do this to both `data` (so the next Block check works) and to
        # `params` so the correct group_id will go to the Valhalla/scheduler
        data['group_id'] = data['group_id'] + '_2'
        params['group_id'] = data['group_id']
    elif check_for_block(data, params, body) >= 2:
        # Multiple blocks found
        resp_params = {'error_msg' : 'Multiple Blocks for same day and site found'}
    if check_for_block(data, params, body) == 0:
        # Record block and submit to scheduler
        tracking_number, resp_params = submit_block_to_scheduler(body_elements, params)
    return tracking_number, resp_params


class SpectroFeasibility(LookUpBodyMixin, FormView):

    template_name = 'core/feasibility.html'
    form_class = SpectroFeasibilityForm

    def get(self, request, *args, **kwargs):
        form = SpectroFeasibilityForm(body=self.body)
        return self.render_to_response(self.get_context_data(form=form, body=self.body))

    def form_valid(self, form, request):
        data = feasibility_check(form.cleaned_data, self.body)
        new_form = SpectroFeasibilityForm(data, body=self.body)
        return render(request, 'core/feasibility.html', {'form': new_form, 'data': data, 'body': self.body})

    def post(self, request, *args, **kwargs):
        form = SpectroFeasibilityForm(request.POST,body=self.body)
        if form.is_valid():
            return self.form_valid(form,request)
        else:
            return self.render_to_response(self.get_context_data(form=form, body=self.body))


def feasibility_check(data, body):
    """Calculate spectroscopic feasibility
    """

    # We assume asteroid magnitudes will be in V and calculate sky
    # brightness in SDSS-ip as that is where most of the signal will be
    ast_mag_bandpass = data.get('bandpass', 'V')
    sky_mag_bandpass = data.get('sky_mag_bandpass', 'ip')
    data['sky_mag'] = calc_sky_brightness(sky_mag_bandpass, data['moon_phase'])
    snr_params = {
                    'moon_phase' : data['moon_phase'],
                    'airmass'    : data['airmass']
                 }
    data['new_mag'], data['new_passband'], data['snr'] = calc_asteroid_snr(data['magnitude'], ast_mag_bandpass, data['exp_length'], instrument=data['instrument_code'], params=snr_params)
    calibs = data.get('calibs', 'both')
    slot_length = determine_spectro_slot_length(data['exp_length'], calibs)
    slot_length /= 60.0
    data['slot_length'] = slot_length

    return data

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
            body_dict['FOM'] = body.compute_FOM()
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
    except Exception as e:
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


def characterization(request):

    char_filter = request.GET.get("filter", "")
    params = build_characterization_list(char_filter)
    return render(request, 'core/characterization.html', params)


def build_characterization_list(disp=None):
    params = {}
    try:
        # If we don't have any Body instances, return None instead of breaking
        char_targets = Body.objects.filter(active=True).exclude(origin='M')
        unranked = []
#        t_test = datetime.today()
        for body in char_targets:
            spectra = PreviousSpectra.objects.filter(body=body)
            s_wav = s_vis_link = s_nir_link = ''
            m_vis_link = m_nir_link = ''
            m_wav = ""
            if spectra:
                s_date = date.today()-date(1000, 1, 1)
                for spectrum in spectra:
                    if spectrum.spec_source == "S":
                        if s_wav == spectrum.spec_wav or not s_wav:
                            if s_date > date.today()-spectrum.spec_date:
                                s_date = date.today()-spectrum.spec_date
                                s_wav = spectrum.spec_wav
                                s_vis_link = spectrum.spec_vis
                                s_nir_link = spectrum.spec_ir
                        else:
                            s_date = date.today()-spectrum.spec_date
                            s_wav = "Vis+NIR"
                            if spectrum.spec_vis:
                                s_vis_link = spectrum.spec_vis
                            if spectrum.spec_ir:
                                s_nir_link = spectrum.spec_ir
                    elif spectrum.spec_source == "M":
                        m_wav = spectrum.spec_wav
                        m_vis_link = spectrum.spec_vis
                        m_nir_link = spectrum.spec_ir
                        if m_wav == "NA":
                            m_wav = "YES"
            body_dict = model_to_dict(body)
            body_dict['current_name'] = body.current_name()
            body_dict['ingest_date'] = body.ingest
            body_dict['s_wav'] = s_wav
            if s_vis_link:
                body_dict['s_vis_link'] = s_vis_link
            if s_nir_link:
                body_dict['s_nir_link'] = s_nir_link
            if m_vis_link:
                body_dict['m_vis_link'] = m_vis_link
            if m_nir_link:
                body_dict['m_nir_link'] = m_nir_link
            body_dict['m_wav'] = m_wav
            body_dict['origin'] = body.get_origin_display()
            if 'Vis' in s_wav or 'Vis' in m_wav:
                body_dict['obs_needed'] = 'LC'
            else:
                body_dict['obs_needed'] = 'Spec/LC'
            emp_line = body.compute_position()
            if not emp_line:
                continue
            obs_dates = body.compute_obs_window()
            if obs_dates[0]:
                body_dict['obs_sdate'] = obs_dates[0]
                if obs_dates[0] == obs_dates[2]:
                    startdate = 'Now'
                else:
                    startdate = obs_dates[0].strftime('%m/%y')
                if not obs_dates[1]:
                    body_dict['obs_edate'] = obs_dates[2]+timedelta(days=99)
                    enddate = '>'
                else:
                    enddate = obs_dates[1].strftime('%m/%y')
                    body_dict['obs_edate'] = obs_dates[1]
            else:
                body_dict['obs_sdate'] = body_dict['obs_edate'] = obs_dates[2]+timedelta(days=99)
                startdate = '-'
                enddate = '-'
            days_to_start = body_dict['obs_sdate']-obs_dates[2]
            days_to_end = body_dict['obs_edate']-obs_dates[2]
            # Define a sorting Priority:
            # Currently a combination of imminence and window width.
            body_dict['priority'] = days_to_start.days + days_to_end.days
            body_dict['obs_start'] = startdate
            body_dict['obs_end'] = enddate
            body_dict['ra'] = emp_line[0]
            body_dict['dec'] = emp_line[1]
            body_dict['v_mag'] = emp_line[2]
            if disp:
                if disp in body_dict['obs_needed']:
                    unranked.append(body_dict)
            else:
                unranked.append(body_dict)
            # print body_dict['obs_sdate'],body_dict['obs_edate']
            # print datetime.today()-t_test
    except Exception as e:
        unranked = None
        logger.error('Characterization list failed on %s' % e)
    params = {
        'targets': Body.objects.filter(active=True).count(),
        'blocks': Block.objects.filter(active=True).count(),
        'char_targets': unranked,
        'char_filter': disp
    }
    return params


def check_for_block(form_data, params, new_body):
    """Checks if a block with the given name exists in the Django DB.
    Return 0 if no block found, 1 if found, 2 if multiple blocks found"""

    # XXX Code smell, duplicated from sources_subs.configure_defaults()
    site_list = { 'V37' : 'ELP' ,
                  'K92' : 'CPT' ,
                  'K93' : 'CPT',
                  'Q63' : 'COJ',
                  'W85' : 'LSC',
                  'W86' : 'LSC',
                  'W89' : 'LSC',
                  'F65' : 'OGG',
                  'E10' : 'COJ',
                  'Z21' : 'TFN',
                  'Q58' : 'COJ',
                  'Q59' : 'COJ',
                  'T04' : 'OGG',
                  'V99' : 'ELP'
                  }

    try:
        block_id = SuperBlock.objects.get(body=new_body.id,
                                     groupid__contains=form_data['group_id'],
                                     proposal=Proposal.objects.get(code=form_data['proposal_code'])
                                     )
#                                         site=site_list[params['site_code']])
    except SuperBlock.MultipleObjectsReturned:
        logger.debug("Multiple superblocks found")
        return 2
    except SuperBlock.DoesNotExist:
        logger.debug("SuperBlock not found")
        return 0
    else:
        logger.debug("SuperBlock found")
        # XXX Do we want to check for matching site in the Blocks as well?
        return 1


def record_block(tracking_number, params, form_data, body):
    """Records a just-submitted observation as a SuperBlock and Block(s) in the database.
    """

    logger.debug("form data=%s" % form_data)
    logger.debug("   params=%s" % params)
    if tracking_number:
        cadence = False
        if len(params.get('request_numbers', [])) > 1:
            cadence = True
        sblock_kwargs = {
                         'body'     : body,
                         'proposal' : Proposal.objects.get(code=form_data['proposal_code']),
                         'groupid'  : form_data['group_id'],
                         'block_start' : form_data['start_time'],
                         'block_end'   : form_data['end_time'],
                         'tracking_number' : tracking_number,
                         'cadence'  : cadence,
                         'period'   : params.get('period', None),
                         'jitter'   : params.get('jitter', None),
                         'timeused' : params.get('block_duration', None),
                         'active'   : True,
                       }
        sblock_pk = SuperBlock.objects.create(**sblock_kwargs)
        i = 0
        for request in params.get('request_numbers', []):
            # cut off json UTC timezone remnant
            no_timezone_blk_start = params['request_windows'][i][0]['start'][:-1]
            no_timezone_blk_end = params['request_windows'][i][0]['end'][:-1]
            block_kwargs = { 'superblock' : sblock_pk,
                             'telclass' : params['pondtelescope'].lower(),
                             'site'     : params['site'].lower(),
                             'body'     : body,
                             'proposal' : Proposal.objects.get(code=form_data['proposal_code']),
                             'groupid'  : form_data['group_id'],
                             'block_start' : datetime.strptime(no_timezone_blk_start, '%Y-%m-%dT%H:%M:%S'),
                             'block_end'   : datetime.strptime(no_timezone_blk_end, '%Y-%m-%dT%H:%M:%S'),
                             'tracking_number' : request,
                             'num_exposures'   : form_data['exp_count'],
                             'exp_length'      : form_data['exp_length'],
                             'active'   : True
                           }
            pk = Block.objects.create(**block_kwargs)
            i += 1
        return True
    else:
        return False


def return_fields_for_saving():
    """Returns a list of fields that should be checked before saving a revision.
    Split out from save_and_make_revision() so it can be consistently used by the
    remove_bad_revisions management command."""

    fields = ['provisional_name', 'provisional_packed', 'name', 'origin', 'source_type',  'elements_type',
              'epochofel', 'abs_mag', 'slope', 'orbinc', 'longascnode', 'eccentricity', 'argofperih', 'meandist', 'meananom',
              'score', 'discovery_date', 'num_obs', 'arc_length']

    return fields


def save_and_make_revision(body, kwargs):
    """
    Make a revision if any of the parameters have changed, but only do it once
    per ingest not for each parameter.
    Converts current model instance into a dict and compares a subset of elements with
    incoming version. Incoming variables may be generically formatted as strings,
    so use the type of original to convert and then compare.
    """

    fields = return_fields_for_saving()

    update = False

    body_dict = model_to_dict(body)
    for k, v in kwargs.items():
        param = body_dict.get(k, '')
        if isinstance(param, float) and v is not None:
            v = float(v)
        if v != param:
            setattr(body, k, v)
            if k in fields:
                update = True
    if update:
        with reversion.create_revision():
            body.save()
    else:
        body.save()
    return update


def update_NEOCP_orbit(obj_id, extra_params={}):
    """Query the MPC's showobs service with the specified <obj_id> and
    it will write the orbit found into the neox database.
    a) If the object does not have a response it will be marked as active = False
    b) If the object's parameters have changed they will be updated and a revision logged
    c) New objects get marked as active = True automatically
    """
    NEOCP_orb_url = 'http://cgi.minorplanetcenter.net/cgi-bin/showobsorbs.cgi?Obj=%s&orb=y' % obj_id

    neocp_obs_page = fetchpage_and_make_soup(NEOCP_orb_url)

    if neocp_obs_page:
        obs_page_list = neocp_obs_page.text.split('\n')
    else:
        return False

    try:
        body, created = Body.objects.get_or_create(provisional_name__startswith=obj_id, defaults={'provisional_name' : obj_id})
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
            check_body = Body.objects.filter(provisional_name__startswith=obj_id, **kwargs)
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
    """Query the NEOCP for <obj_id> and download the observation lines.
    These are used to create Source Measurements for the body if the
    number of observations in the passed extra_params dictionary is greater than
    the number of Source Measurements for that Body"""

    try:
        body = Body.objects.get(provisional_name__startswith=obj_id)
        num_measures = SourceMeasurement.objects.filter(body=body).count()

# Check if the NEOCP has more measurements than we do
        if body.num_obs > num_measures:
            obs_lines = fetch_NEOCP_observations(obj_id)
            if obs_lines:
                measure = create_source_measurement(obs_lines)
                if measure is False:
                    msg = "Could not create source measurements for object %s (no or multiple Body's exist)" % obj_id
                else:
                    if len(measure) > 0:
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
    """Parse response from the MPC NEOCP page making sure we only return
    parameters from the 'NEOCPNomin' (nominal orbit)"""
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
                    logger.warning(
                        "Missing RMS for %s; assuming 99.99", current[0])
                except:
                    logger.error(
                        "Missing field in NEOCP orbit for %s which wasn't correctable", current[0])
            except ValueError:
                # Insert a high magnitude for the missing H
                current.insert(1, 99.99)
                logger.warning(
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
                params['not_seen'] = not_seen.total_seconds() / 86400.0  # Leap seconds can go to hell...
            except:
                pass
        else:
            logger.warning(
                "Did not get right number of parameters for %s. Values %s", current[0], current)
            params = {}
        if params != {}:
            # Check for objects that should be treated as comets (e>0.9)
            if params['eccentricity'] > 0.9:
                params = convert_ast_to_comet(params, None)
    else:
        params = {}
    return params


def update_crossids(astobj, dbg=False):
    """Update the passed <astobj> for a new cross-identification.
    <astobj> is expected to be a list of:
    provisional id, final id/failure reason, reference, confirmation date
    normally produced by the fetch_previous_NEOCP_desigs() method."""

    if len(astobj) != 4:
        return False

    obj_id = astobj[0].rstrip()

    try:
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
    except:
        logger.warn("Multiple objects found called %s" % obj_id)
        return False
    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_crossid(astobj, dbg)
    if not created:
        if dbg:
            print("Did not create new Body")
        # Find out if the details have changed, if they have, save a revision
        # But first check if it is a comet or NEO and came from somewhere other
        # than the MPC. In this case, leave it active.
        if body.source_type in ['N', 'C', 'H'] and body.origin != 'M':
            kwargs['active'] = True
        if kwargs['source_type'] in ['C', 'H']:
            kwargs = convert_ast_to_comet(kwargs, body)
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
        logger.warning("Could not add cross identification for %s" % obj_id)
        return False
    return True


def clean_crossid(astobj, dbg=False):
    """Takes an <astobj> (a list of new designation, provisional designation,
    reference and confirm date produced from the MPC's Previous NEOCP Objects
    page) and determines the type and whether it should still be followed.

    Objects that were not confirmed, did not exist or "were not interesting
    (normally a satellite) are set inactive immediately. For NEOs and comets,
    we set it to inactive if more than 3 days have passed since the
    confirmation date"""

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
    elif obj_id != '' and desig == 'wasnotminorplanet':
        # "was not a minor planet"; set to satellite and no longer interesting
        objtype = 'J'
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
            if 'A/' in desig:
                # Check if it is an inactive hyperbolic asteroid
                objtype = 'H'
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
            print("%07s->%s (%s) %s" % (obj_id, params['name'], params['source_type'], params['active']))
    else:
        logger.warning("Unparseable cross-identification: %s" % astobj)
        params = {}

    return params


def clean_mpcorbit(elements, dbg=False, origin='M'):
    """Takes a list of (proto) element lines from fetch_mpcorbit() and plucks
    out the appropriate bits. origin defaults to 'M'(PC) if not specified"""

    params = {}
    if elements is not None:

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
            if 'A/2' in elements.get('obj_id', ''):
                params['source_type'] = 'H'
            # The MPC never seems to have H values for comets so we remove it
            # from the dictionary to avoid replacing what was there before.
            if params['abs_mag'] is None:
                del params['abs_mag']
            params['slope'] = elements.get('phase slope', '4.0')
            params['perihdist'] = elements['perihelion distance']
            perihelion_date = elements['perihelion date'].replace('-', ' ')
            params['epochofperih'] = parse_neocp_decimal_date(perihelion_date)

        not_seen = None
        if last_obs is not None:
            time_diff = datetime.utcnow() - last_obs
            not_seen = time_diff.total_seconds() / 86400.0
        params['not_seen'] = not_seen
    return params


def update_MPC_orbit(obj_id_or_page, dbg=False, origin='M'):
    """
    Performs remote look up of orbital elements for object with id obj_id_or_page,
    Gets or creates corresponding Body instance and updates entry.
    Alternatively obj_id_or_page can be a BeautifulSoup object, in which case
    the call to fetch_mpcdb_page() will be skipped and the passed BeautifulSoup
    object will parsed.
    """

    obj_id = None
    if type(obj_id_or_page) != BeautifulSoup:
        obj_id = obj_id_or_page
        page = fetch_mpcdb_page(obj_id, dbg)

        if page is None:
            logger.warning("Could not find elements for %s" % obj_id)
            return False
    else:
        page = obj_id_or_page

    elements = parse_mpcorbit(page, dbg)
    if elements == {}:
        logger.warning("Could not parse elements from page for %s" % obj_id)
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
        obs_lines = [obs_lines, ]

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
                obs_body = Body.objects.get(Q(provisional_name__startswith=params['body']) |
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
                        logger.warning("No blocks for %s" % obs_body)
                if params['obs_type'] == 's':
                    # If we have an obs_type of 's', then we have the second line
                    # of a satellite measurement and we need to find the matching
                    # Frame we created on the previous line read and update its
                    # extrainfo field.
                    try:
                        prior_frame = Frame.objects.get(frametype=Frame.SATELLITE_FRAMETYPE,
                                                        midpoint=params['obs_date'],
                                                        sitecode=params['site_code'])
                        if prior_frame.extrainfo != params['extrainfo']:
                            prior_frame.extrainfo = params['extrainfo']
                            prior_frame.save()
                        if len(measures) > 0:
                            # Replace SourceMeasurement in list to be returned with
                            # updated version
                            measures[-1] = SourceMeasurement.objects.get(pk=measures[-1].pk)
                    except Frame.DoesNotExist:
                        logger.warning("Matching satellite frame for %s from %s on %s does not exist" % (params['body'], params['obs_date'], params['site_code']))
                    except Frame.MultipleObjectsReturned:
                        logger.warning("Multiple matching satellite frames for %s from %s on %s found" % (params['body'], params['obs_date'], params['site_code']))
                else:
                    # Otherwise, make a new Frame and SourceMeasurement
                    frame = create_frame(params, block)
                    measure_params = {  'body'    : obs_body,
                                        'frame'   : frame,
                                        'obs_ra'  : params['obs_ra'],
                                        'obs_dec' : params['obs_dec'],
                                        'obs_mag' : params['obs_mag'],
                                        'flags'   : params['flags']
                                     }
                    measure, measure_created = SourceMeasurement.objects.get_or_create(**measure_params)
                    if measure_created:
                        measures.append(measure)
            except Body.DoesNotExist:
                logger.debug("Body %s does not exist" % params['body'])
                measures = False
            except Body.MultipleObjectsReturned:
                logger.warning("Multiple versions of Body %s exist" % params['body'])
                measures = False

    return measures


def determine_original_name(fits_file):
    """Determines the ORIGNAME for the FITS file <fits_file>.
    This is pretty disgusting and a sign we are probably doing something wrong
    and should store the true filename but at least it's contained to one place
    now..."""
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


def find_matching_image_file(catfile):
    """Find the matching image file for the passed <catfile>. Returns None if it
    can't be found or opened"""

    if os.path.exists(catfile) is False or os.path.isfile(catfile) is False:
        logger.error("Could not open matching image for catalog %s" % catfile)
        return None
    fits_file_for_sext = catfile + "[SCI]"

    return fits_file_for_sext


def run_sextractor_make_catalog(configs_dir, dest_dir, fits_file):
    """Run SExtractor, rename output to new filename which is returned"""

    logger.debug("Running SExtractor on BANZAI file: %s" % fits_file)
    sext_status = run_sextractor(configs_dir, dest_dir, fits_file, catalog_type='FITS_LDAC')
    if sext_status == 0:
        fits_ldac_catalog = 'test_ldac.fits'
        fits_ldac_catalog_path = os.path.join(dest_dir, fits_ldac_catalog)

        # Rename catalog to permanent name
        fits_file_output = os.path.basename(fits_file)
        fits_file_output = fits_file_output.replace('[SCI]', '').replace('.fits', '_ldac.fits')
        new_ldac_catalog = os.path.join(dest_dir, fits_file_output)
        logger.debug("Renaming %s to %s" % (fits_ldac_catalog_path, new_ldac_catalog))
        os.rename(fits_ldac_catalog_path, new_ldac_catalog)

    else:
        logger.error("Execution of SExtractor failed")
        return sext_status, -4

    return sext_status, new_ldac_catalog


def find_block_for_frame(catfile):
    """Try and find a Block for the original passed <catfile> filename (new style with
    filename directly stored in the DB. If that fails, try and determine the filename
    that would have been stored with the ORIGNAME.
    Returns the Block if found, None otherwise."""

    # try and find Frame does for the fits catfile with a non-null block
    try:
        frame = Frame.objects.get(filename=os.path.basename(catfile), block__isnull=False)
    except Frame.MultipleObjectsReturned:
        logger.error("Found multiple versions of fits frame %s pointing at multiple blocks" % os.path.basename(catfile))
        return None
    except Frame.DoesNotExist:
        # Try and find the Frame under the original name (old-style)
        fits_file_orig = determine_original_name(catfile)
        try:
            frame = Frame.objects.get(filename=fits_file_orig, block__isnull=False)
        except Frame.MultipleObjectsReturned:
            logger.error("Found multiple versions of fits frame %s pointing at multiple blocks" % fits_file_orig)
            return None
        except Frame.DoesNotExist:
            logger.error("Frame entry for fits file %s does not exist" % fits_file_orig)
            return None
    return frame.block


def make_new_catalog_entry(new_ldac_catalog, header, block):

    num_new_frames_created = 0

    # if a Frame does not exist for the catalog file with a non-null block
    # create one with the fits filename
    catfilename = os.path.basename(new_ldac_catalog)
    if len(Frame.objects.filter(filename=catfilename, block__isnull=False)) < 1:

        # Create a new Frame entry for new fits_file_output name
        frame_params = {    'sitecode': header['site_code'],
                          'instrument': header['instrument'],
                              'filter': header['filter'],
                            'filename': catfilename,
                             'exptime': header['exptime'],
                            'midpoint': header['obs_midpoint'],
                               'block': block,
                           'zeropoint': header['zeropoint'],
                       'zeropoint_err': header['zeropoint_err'],
                                'fwhm': header['fwhm'],
                           'frametype': Frame.BANZAI_LDAC_CATALOG,
                           'astrometric_catalog' : header.get('astrometric_catalog', None),
                          'rms_of_fit': header['astrometric_fit_rms'],
                       'nstars_in_fit': header['astrometric_fit_nstars'],
                                'wcs' : header.get('wcs', None),
                        }

        frame, created = Frame.objects.get_or_create(**frame_params)
        if created is True:
            logger.debug("Created new Frame id#%d", frame.id)
            num_new_frames_created += 1

    return num_new_frames_created


def check_catalog_and_refit(configs_dir, dest_dir, catfile, dbg=False):
    """New version of check_catalog_and_refit designed for BANZAI data. This
    version of the routine assumes that the astrometric fit status of <catfile>
    is likely to be good and exits if not the case. A new source extraction
    is performed unless we find an existing Frame record for the catalog.
    The name of the newly created FITS LDAC catalog from this process is returned
    or an integer status code if no fit was needed or could not be performed."""

    num_new_frames_created = 0

    # Open catalog, get header and check fit status
    fits_header, junk_table, cattype = open_fits_catalog(catfile, header_only=True)
    try:
        header = get_catalog_header(fits_header, cattype)
    except FITSHdrException as e:
        logger.error("Bad header for %s (%s)" % (catfile, e))
        return -1, num_new_frames_created

    if header.get('astrometric_fit_status', None) != 0:
        logger.error("Bad astrometric fit found")
        return -1, num_new_frames_created

    # Check catalog type
    if cattype != 'BANZAI':
        logger.error("Unable to process non-BANZAI data at this time")
        return -99, num_new_frames_created

    # Check for matching catalog
    catfilename = os.path.basename(catfile).replace('.fits', '_ldac.fits')
    catalog_frames = Frame.objects.filter(filename=catfilename, frametype__in=(Frame.BANZAI_LDAC_CATALOG, Frame.FITS_LDAC_CATALOG))
    if len(catalog_frames) != 0:
        return os.path.abspath(os.path.join(dest_dir, os.path.basename(catfile.replace('.fits', '_ldac.fits')))), 0

    # Find image file for this catalog
    fits_file = find_matching_image_file(catfile)
    if fits_file is None:
        logger.error("Could not open matching image %s for catalog %s" % ( fits_file, catfile))
        return -1, num_new_frames_created

    # Make a new FITS_LDAC catalog from the frame
    status, new_ldac_catalog = run_sextractor_make_catalog(configs_dir, dest_dir, fits_file)
    if status != 0:
        logger.error("Execution of SExtractor failed")
        return -4, 0

    # Find Block for original frame
    block = find_block_for_frame(catfile)
    if block is None:
        logger.error("Could not find block for fits frame %s" % catfile)
        return -3, num_new_frames_created

    # Check if we have a sitecode (none if this is a new instrument/telescope)
    if header.get('site_code', None) is None:
        logger.error("No sitecode found for fits frame %s" % catfile)
        return -5, num_new_frames_created

    # Create a new Frame entry for the new_ldac_catalog
    num_new_frames_created = make_new_catalog_entry(new_ldac_catalog, header, block)

    return new_ldac_catalog, num_new_frames_created


def store_detections(mtdsfile, dbg=False):

    num_candidates = 0
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
                cand = Candidate.objects.get(block=frame.block, cand_id=candidate['det_number'][0], avg_midpoint=mean_dt, score=score,
                        avg_x=mean_x, avg_y=mean_y, avg_ra=mean_ra, avg_dec=mean_dec, avg_mag=mean_mag, speed=speed,
                        sky_motion_pa=sky_position_angle)
                if cand.detections != candidate.tostring():
                    cand.detections = candidate.tostring()
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
                if dbg:
                    print(params)
                cand, created = Candidate.objects.get_or_create(**params)
                if dbg:
                    print(cand, created)
                if created:
                    num_candidates += 1

    return num_candidates


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


def update_taxonomy(taxobj, dbg=False):
    """Update the passed <taxobj> for a new taxonomy update.
    <taxobj> is expected to be a list of:
    designation/provisional designation, taxonomy, taxonomic scheme, reference, notes
    normally produced by the fetch_taxonomy_page() method.
    Will only add (never remove) taxonomy fields that are not already in Taxonomy database and match objects in DB."""

    if len(taxobj) != 5:
        return False

    obj_id = taxobj[0].rstrip()
    body_all = Body.objects.all()
    try:
        body = Body.objects.get(name=obj_id)
    except:
        try:
            body = Body.objects.get(provisional_name=obj_id)
        except:
            if dbg is True:
                print("No such Body as %s" % obj_id)
                print("number of bodies: %i" % body_all.count())
            return False
    # Must be a better way to do this next bit, but I don't know what it is off the top of my head.
    check_tax = SpectralInfo.objects.filter(body=body, taxonomic_class=taxobj[1], tax_scheme=taxobj[2],
                                            tax_reference=taxobj[3], tax_notes=taxobj[4])
    if check_tax.count() != 0:
        if dbg is True:
            print("Data already in DB")
        return False
    params = {  'body'          : body,
                'taxonomic_class' : taxobj[1],
                'tax_scheme'    : taxobj[2],
                'tax_reference' : taxobj[3],
                'tax_notes'     : taxobj[4],
                }
    tax, created = SpectralInfo.objects.get_or_create(**params)
    if not created:
        if dbg is True:
            print("Did not write for some reason.")
        return False
    return True


def update_previous_spectra(specobj, source='U', dbg=False):
    """Update the passed <specobj> for a new external spectroscopy update.
    <specobj> is expected to be a list of:
    designation/provisional designation, wavelength region, data link, reference, date
    normally produced by the fetch_manos_tagets() or fetch_smass_targets() method.
    Will only add (never remove) spectroscopy details that are not already in spectroscopy
    database and match Characterization objects in DB."""

    if len(specobj) != 6:
        return False

    obj_id = specobj[0].rstrip()
    body_char = Body.objects.filter(active=True).exclude(origin='M')
    try:
        body = body_char.get(name=obj_id)
    except:
        try:
            body = body_char.get(provisional_name=obj_id)
        except:
            if dbg is True:
                print("%s is not a Characterization Target" % obj_id)
                print("Number of Characterization Targets: %i" % body_char.count())
            return False
    check_spec = PreviousSpectra.objects.filter(body=body, spec_wav=specobj[1], spec_source=source)
    if check_spec:
        for check in check_spec:
            if check.spec_date >= specobj[5]:
                if dbg is True:
                    print("More recent data already in DB")
                return False
    params = {  'body'          : body,
                'spec_wav'      : specobj[1],
                'spec_vis'      : specobj[2],
                'spec_ir'       : specobj[3],
                'spec_ref'      : specobj[4],
                'spec_source'   : source,
                'spec_date'     : specobj[5],
                }
    spec, created = PreviousSpectra.objects.get_or_create(**params)
    if not created:
        if dbg is True:
            print("Did not write for some reason.")
        return False
    return True



