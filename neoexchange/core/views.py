"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO
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
from shutil import move
from glob import glob
from datetime import datetime, timedelta, date
from math import floor, ceil, degrees, radians, pi, acos, pow
from astropy import units as u
import json
import urllib
import logging
import tempfile
import bokeh
from django.db.models import Q, Prefetch
from django.forms.models import model_to_dict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import DetailView, ListView, FormView, TemplateView, View
from django.views.generic.edit import FormView
from django.views.generic.detail import SingleObjectMixin
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from http.client import HTTPSConnection
from django.conf import settings
from bs4 import BeautifulSoup
import reversion
import requests
import re
import numpy as np
try:
    import pyslalib.slalib as S
except ImportError:
    pass
import io

from .forms import EphemQuery, ScheduleForm, ScheduleCadenceForm, ScheduleBlockForm, \
    ScheduleSpectraForm, MPCReportForm, SpectroFeasibilityForm
from .models import *
from astrometrics.ast_subs import determine_asteroid_type, determine_time_of_perih, \
    convert_ast_to_comet
import astrometrics.site_config as cfg
from astrometrics.albedo import asteroid_diameter
from astrometrics.ephem_subs import call_compute_ephem, compute_ephem, \
    determine_darkness_times, determine_slot_length, determine_exp_time_count, \
    MagRangeError, determine_spectro_slot_length, get_sitepos, read_findorb_ephem,\
    accurate_astro_darkness, get_visibility, determine_exp_count, determine_star_trails,\
    calc_moon_sep, get_alt_from_airmass
from astrometrics.sources_subs import fetchpage_and_make_soup, packed_to_normal, \
    fetch_mpcdb_page, parse_mpcorbit, submit_block_to_scheduler, parse_mpcobs,\
    fetch_NEOCP_observations, PackedError, fetch_filter_list, fetch_mpcobs, validate_text,\
    read_mpcorbit_file, fetch_jpl_physparams_altdes, store_jpl_sourcetypes, store_jpl_desigs,\
    store_jpl_physparams
from astrometrics.time_subs import extract_mpc_epoch, parse_neocp_date, \
    parse_neocp_decimal_date, get_semester_dates, jd_utc2datetime, datetime2st
from photometrics.external_codes import run_sextractor, run_scamp, updateFITSWCS,\
    read_mtds_file, unpack_tarball, run_findorb
from photometrics.catalog_subs import open_fits_catalog, get_catalog_header, \
    determine_filenames, increment_red_level, update_ldac_catalog_wcs, FITSHdrException, sanitize_object_name
from photometrics.photometry_subs import calc_asteroid_snr, calc_sky_brightness
from photometrics.spectraplot import pull_data_from_spectrum, pull_data_from_text, spectrum_plot
from core.frames import create_frame, ingest_frames, measurements_from_block
from core.mpc_submit import email_report_to_mpc
from core.archive_subs import lco_api_call
from core.utils import search
from photometrics.SA_scatter import readSources, genGalPlane, plotScatter, \
    plotFormat
from core.plots import spec_plot, lin_vis_plot

logger = logging.getLogger(__name__)

BOKEH_URL = "https://cdn.bokeh.org/bokeh/release/bokeh-{}.min."


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


def determine_active_proposals(proposal_code=None, filter_proposals=True):
    """Determine and return the active Proposals or verify the passed [proposal_code]
    exists. If [filter_proposals] is set to True (the default), proposals
    with `proposal.download=False` are excluded from the returned proposal list.

    Returns a list of proposal codes.
    """

    if proposal_code is not None:
        try:
            proposal = Proposal.objects.get(code=proposal_code.upper())
            proposals = [proposal.code, ]
        except Proposal.DoesNotExist:
            logger.warning("Proposal {} does not exist".format(proposal_code))
            proposals = []
    else:
        proposals = Proposal.objects.filter(active=True)
        if filter_proposals is True:
            proposals = proposals.filter(download=True)
        proposals = proposals.order_by('code').values_list('code', flat=True)

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
        blocks = Block.objects.filter(superblock__proposal=proposal)
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
        lin_script, lin_div = lin_vis_plot(self.object)
        context['lin_script'] = lin_script
        context['lin_div'] = lin_div
        base_path = BOKEH_URL.format(bokeh.__version__)
        context['css_path'] = base_path + 'css'
        context['js_path'] = base_path + 'js'
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
        name = name.strip()
        object_list = []
        if name != '':
            if name.isdigit():
                object_list = self.model.objects.filter(designations__value=name).filter(designations__desig_type='#')
            if not object_list:
                object_list = self.model.objects.filter(Q(designations__value__icontains=name) | Q(provisional_name__icontains=name) | Q(provisional_packed__icontains=name) | Q(name__icontains=name))
        else:
            object_list = self.model.objects.all()
        return list(set(object_list))


class BodyVisibilityView(DetailView):
    template_name = 'core/body_visibility.html'
    model = Body


class BlockDetailView(DetailView):
    template_name = 'core/block_detail.html'
    model = Block


class SuperBlockDetailView(DetailView):
    template_name = 'core/block_detail.html'
    model = SuperBlock


class SuperBlockTimeline(DetailView):
    template_name = 'core/block_timeline.html'
    model = SuperBlock

    def get_context_data(self, **kwargs):
        context = super(SuperBlockTimeline, self).get_context_data(**kwargs)
        blks = []
        for blk in self.object.block_set.all():
            if blk.when_observed:
                date = blk.when_observed.isoformat(' ')
            else:
                date = blk.block_start.isoformat(' ')
            data = {
                'date' : date,
                'num'  : blk.num_observed if blk.num_observed else 0,
                'type' : blk.get_obstype_display(),
                'duration' : (blk.block_end - blk.block_start).seconds
                }
            blks.append(data)
        context['blocks'] = json.dumps(blks)
        return context


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

class BlockCancel(View):
    def get(self, request, *args, **kwargs):
        try:
            bk = SuperBlock.objects.get(id=kwargs['pk'])
        except Exception:
            return Http404
        url = f'https://observe.lco.global/api/requestgroups/{bk.tracking_number}/cancel/'
        resp = lco_api_call(url, method='post')
        if 'Not Found' in resp.get('detail',''):
            messages.warning(request, 'SuperBlock not found')
        else:
            if resp['state'] == 'CANCELED':
                bk.active = False
                bk.save()
                # Cancel all sub-Blocks
                num_canceled = Block.objects.filter(superblock=bk, active=True).update(active=False)
                messages.success(request, f'SuperBlock {bk.id} and {num_canceled} Blocks cancelled')
            else:
                messages.warning(request, f'SuperBlock {bk.id} not cancelled')
        return HttpResponseRedirect(reverse('block-view', kwargs={'pk': kwargs['pk']}))

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
    # Set default pagination (number of objects per page)
    paginate_by = 20
    # Set minimum number of orphans (objects allowed on last page)
    orphans = 3

    def get(self, request, *args, **kwargs):
        body = Body.objects.get(pk=kwargs['pk'])
        measurements = SourceMeasurement.objects.filter(body=body).order_by('frame__midpoint')
        measurements = measurements.prefetch_related(Prefetch('frame'), Prefetch('body'))

        # Set up pagination
        page = request.GET.get('page', None)

        # Toggle Pagination
        if page == '0':
            self.paginate_by = len(measurements)
        # add more rows for denser formats
        elif 'mpc' in request.path or 'ades' in request.path:
            self.paginate_by = 30
        paginator = Paginator(measurements, self.paginate_by, orphans=self.orphans)

        if paginator.num_pages > 1:
            is_paginated = True
        else:
            is_paginated = False

        if page is None or int(page) < 1:
            page = 1
        elif int(page) > paginator.num_pages:
            page = paginator.num_pages
        page_obj = paginator.page(page)

        return render(request, self.template, {'body': body, 'measures' : page_obj, 'is_paginated': is_paginated, 'page_obj': page_obj})


def download_measurements_file(template, body, m_format, request):
    measures = SourceMeasurement.objects.filter(body=body.id).order_by('frame__midpoint')
    measures = measures.prefetch_related(Prefetch('frame'), Prefetch('body'))
    data = { 'measures' : measures}
    filename = "{}{}".format(sanitize_object_name(body.current_name()), m_format)

    response = HttpResponse(template.render(data), content_type="text/plain")
    response['Content-Disposition'] = 'attachment; filename=' + filename
    return response


class MeasurementDownloadMPC(View):
    template = get_template('core/mpc_outputfile.txt')

    def get(self, request, *args, **kwargs):
        try:
            body = Body.objects.get(id=kwargs['pk'])
        except Body.DoesNotExist:
            logger.warning("Could not find Body with pk={}".format(kwargs['pk']))
            raise Http404("Body does not exist")

        response = download_measurements_file(self.template, body, '_mpc.dat', request)
        return response


class MeasurementDownloadADESPSV(View):

    template = get_template('core/mpc_ades_psv_outputfile.txt')

    def get(self, request, *args, **kwargs):
        try:
            body = Body.objects.get(id=kwargs['pk'])
        except Body.DoesNotExist:
            logger.warning("Could not find Body with pk={}".format(kwargs['pk']))
            raise Http404("Body does not exist")

        response = download_measurements_file(self.template, body, '.psv', request)
        return response


def export_measurements(body_id, output_path=''):

    t = get_template('core/mpc_outputfile.txt')
    try:
        body = Body.objects.get(id=body_id)
    except Body.DoesNotExist:
        logger.warning("Could not find Body with pk={}".format(body_id))
        return None, -1
    measures = SourceMeasurement.objects.filter(body=body).exclude(frame__frametype=Frame.SATELLITE_FRAMETYPE).exclude(frame__midpoint__lt=datetime(1993, 1, 1, 0, 0, 0, 0)).order_by('frame__midpoint')
    measures = measures.prefetch_related(Prefetch('frame'), Prefetch('body'))
    data = { 'measures' : measures}

    filename = "{}.mpc".format(sanitize_object_name(body.current_name()))
    filename = os.path.join(output_path, filename)

    output_fh = open(filename, 'w')
    output = t.render(data)
    output_fh.writelines(output)
    output_fh.close()

    return filename, output.count('\n')-1


def update_elements_with_findorb(source_dir, dest_dir, filename, site_code, start_time):
    """Handle the refitting of a set of MPC1992 format observations in <filename>
    located in <dest_dir> with original config files in <source_dir>. The ephemeris
    is computed for <site_code> starting at <start_time>

    Either a parsed dictionary of elements or a status code is returned.
    """

    elements_or_status = None

    status = run_findorb(source_dir, dest_dir, filename, site_code, start_time)
    if status != 0:
        logger.error("Error running find_orb on the data")
        elements_or_status = status
    else:
        orbit_file = os.path.join(os.getenv('HOME'), '.find_orb', 'mpc_fmt.txt')
        try:
            orbfile_fh = open(orbit_file, 'r')
        except IOError:
            logger.warning("File %s not found" % orbit_file)
            return None

        orblines = orbfile_fh.readlines()
        orbfile_fh.close()
        orblines[0] = orblines[0].replace('Find_Orb  ', 'NEOCPNomin')
        elements_or_status = clean_NEOCP_object(orblines)
    return elements_or_status


def refit_with_findorb(body_id, site_code, start_time=datetime.utcnow(), dest_dir=None, remove=False):
    """Refit all the SourceMeasurements for a body with find_orb and update the elements.
    Inputs:
    <body_id>: the PK of the Body,
    <site_code>: the MPC site code to generate the ephemeris for,
    [start_time]: where to start the ephemeris,
    [dest_dir]: destination directory (if not specified, a unique directory in the
                form '/tmp/tmp_neox_<stuff>' is created and used),
    [remove]: whether to remove the temporary directory and contents afterwards

    Outputs:
    The ephemeris output (if found), starting at [start_time] is read in and a
    dictionary containing the ephemeris details (object id, time system,
    motion rate units, sitecode) and a list of tuples containing:
    Datetime, RA, Dec, magnitude, rate, uncertainty is returned. In the event of
    an issue, None is returned."""

    source_dir = os.path.abspath(os.path.join(os.getenv('HOME'), '.find_orb'))
    dest_dir = dest_dir or tempfile.mkdtemp(prefix='tmp_neox_')
    new_ephem = (None, None)
    comp_time = start_time + timedelta(days=1)

    filename, num_lines = export_measurements(body_id, dest_dir)

    if filename is not None:
        if num_lines > 0:
            status_or_elements = update_elements_with_findorb(source_dir, dest_dir, filename, site_code, start_time)
            if type(status_or_elements) != dict:
                logger.error("Error running find_orb on the data")
            else:
                new_elements = status_or_elements
                body = Body.objects.get(pk=body_id)
                logger.info("{}: FindOrb found an orbital rms of {} using {} observations.".format(body.current_name(), new_elements['orbit_rms'], new_elements['num_obs']))
                if body.epochofel:
                    time_to_current_epoch = abs(body.epochofel - comp_time)
                else:
                    time_to_current_epoch = abs(datetime.min - comp_time)
                time_to_new_epoch = abs(new_elements['epochofel'] - comp_time)
                if time_to_new_epoch <= time_to_current_epoch and new_elements['orbit_rms'] > 0.0 and new_elements['orbit_rms'] < 1.0:
                    # Reset some fields to avoid overwriting

                    new_elements['provisional_name'] = body.provisional_name
                    new_elements['origin'] = body.origin
                    new_elements['source_type'] = body.source_type
                    updated = save_and_make_revision(body, new_elements)
                    message = "Did not update"
                    if updated is True:
                        message = "Updated"
                else:
                    # Fit was bad or for an old epoch
                    message = ""
                    if new_elements['epochofel'] < start_time:
                        message = "Epoch of elements was too old"
                    if new_elements['orbit_rms'] >= 1.0:
                        message += " and rms was too high"
                    elif new_elements['orbit_rms'] < 0.001:
                        message += " and rms was suspicously low"
                    message += ". Did not update"
                logger.info("%s Body #%d (%s) with FindOrb" % (message, body.pk, body.current_name()))

                # Read in ephemeris file
                ephem_file = os.path.join(dest_dir, 'new.ephem')
                if os.path.exists(ephem_file):
                    emp_info, ephemeris = read_findorb_ephem(ephem_file)
                    new_ephem = (emp_info, ephemeris)
                else:
                    logger.warning("Could not read ephem file %s" % ephem_file)

            # Clean up output directory
            if remove:
                try:
                    files_to_remove = glob(os.path.join(dest_dir, '*'))
                    for file_to_rm in files_to_remove:
                        os.remove(file_to_rm)
                except OSError:
                    logger.warning("Error removing files in temporary test directory", self.test_dir)
                try:
                    os.rmdir(dest_dir)
                    logger.debug("Removed", dest_dir)
                except OSError:
                    logger.warning("Error removing temporary test directory", dest_dir)
        else:
            logger.warning("Unable to export measurements for Body #%s" % body_id)
    else:
        logger.warning("Could not find Body with id #%s" % body_id)

    return new_ephem


class CandidatesViewBlock(LoginRequiredMixin, View):
    template = 'core/candidates.html'

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        candidates = Candidate.objects.filter(block=block).order_by('score')
        return render(request, self.template, {'body': block.body, 'candidates': candidates, 'slot': block})


class StaticSourceView(ListView):
    template_name = 'core/calibsource_list.html'
    model = StaticSource
    queryset = StaticSource.objects.order_by('ra')
    context_object_name = "calibsources"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(StaticSourceView, self).get_context_data(**kwargs)
        sun_ra, sun_dec = accurate_astro_darkness('500', datetime.utcnow(), solar_pos=True)
        night_ra = degrees(sun_ra - pi)
        if night_ra < 0:
            night_ra += 360
        night_ra = degreestohms(night_ra, ':')
        night_dec = degreestodms(degrees(-sun_dec), ':')
        context['night'] = {'ra': night_ra, 'dec': night_dec}
        return context


class BestStandardsView(ListView):
    template_name = 'core/best_calibsource_list.html'
    model = StaticSource
    paginate_by = 20

    def determine_ra_range(self, utc_dt=datetime.utcnow(), HA_hours=3, dbg=False):
        sun_ra, sun_dec = accurate_astro_darkness('500', utc_dt, solar_pos=True)
        night_ra = degrees(sun_ra - pi)
        if night_ra < 0:
            night_ra += 360
        if dbg: print(utc_dt, degreestohms(night_ra, ':'), HA_hours*15)

        min_ra = night_ra - (HA_hours * 15)
        if min_ra < 0:
            min_ra += 360
        max_ra = night_ra + (HA_hours * 15)
        if max_ra > 360:
            max_ra -= 360
        if dbg: print("RA range=", min_ra, max_ra)

        return min_ra, max_ra

    def get_sources(self, utc_date=datetime.utcnow(), dbg=False):

        min_ra, max_ra = self.determine_ra_range(utc_dt=utc_date, dbg=False)
        if min_ra > max_ra:
            # Wrap occurred
            ra_filter = Q(ra__gte=min_ra) | Q(ra__lte=max_ra)
        else:
            ra_filter = Q(ra__gte=min_ra) & Q(ra__lte=max_ra)
        ftn_standards = StaticSource.objects.filter(ra_filter, source_type=StaticSource.FLUX_STANDARD, dec__gte=0).order_by('ra')
        fts_standards = StaticSource.objects.filter(ra_filter, source_type=StaticSource.FLUX_STANDARD, dec__lte=0).order_by('ra')
        if dbg: print(ftn_standards,fts_standards)

        return ftn_standards, fts_standards

    def get_context_data(self, **kwargs):
        context = super(BestStandardsView, self).get_context_data(**kwargs)
        utc_date = datetime.utcnow()
        sun_ra, sun_dec = accurate_astro_darkness('500', utc_date, solar_pos=True)
        night_ra = degrees(sun_ra - pi)
        if night_ra < 0:
            night_ra += 360
        night_ra = degreestohms(night_ra, ':')
        night_dec = degreestodms(degrees(-sun_dec), ':')
        context['night'] = {'ra': night_ra, 'dec': night_dec, 'utc_date' : utc_date.date}
        ftn_standards, fts_standards = self.get_sources(utc_date=utc_date)
        context['ftn_calibsources'] = ftn_standards
        context['fts_calibsources'] = fts_standards
        return context


class StaticSourceDetailView(DetailView):
    template_name = 'core/calibsource_detail.html'
    model = StaticSource

    def get_context_data(self, **kwargs):
        context = super(StaticSourceDetailView, self).get_context_data(**kwargs)
        context['blocks'] = Block.objects.filter(calibsource=self.object).order_by('block_start')
        script, div, p_spec = plot_all_spec(self.object)
        if script and div:
            context['script'] = script
            context['div'] = div["raw_spec"]
        base_path = BOKEH_URL.format(bokeh.__version__)
        context['css_path'] = base_path + 'css'
        context['js_path'] = base_path + 'js'
        return context


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


class LookUpCalibMixin(object):
    """
    A Mixin for finding a StaticSource for a sitecode and if it exists, return the Target instance.
    """
    def dispatch(self, request, *args, **kwargs):
        try:
            calib_id = kwargs['pk']
            if calib_id == '-':
                sitecode = kwargs['instrument_code'][0:3]
                target, target_params = find_best_flux_standard(sitecode)
            else:
                target = StaticSource.objects.get(pk=calib_id)
            self.target = target
            return super(LookUpCalibMixin, self).dispatch(request, *args, **kwargs)
        except StaticSource.DoesNotExist:
            raise Http404("StaticSource does not exist")


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
        cadence_form = ScheduleCadenceForm()
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.render_to_response(self.get_context_data(form=form, cad_form=cadence_form, body=self.body))

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


class ScheduleCalibParameters(LoginRequiredMixin, LookUpCalibMixin, FormView):
    """
    Creates a suggested observation request for a static source, including time window and molecules
    """
    template_name = 'core/schedule.html'
    form_class = ScheduleForm
    ok_to_schedule = False

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        cadence_form = ScheduleCadenceForm()
        return self.render_to_response(self.get_context_data(form=form, cad_form=cadence_form, body=self.target))

    def form_valid(self, form, request):
        data = schedule_check(form.cleaned_data, self.target, self.ok_to_schedule)
        new_form = ScheduleBlockForm(data)
        return render(request, 'core/calib_schedule_confirm.html', {'form': new_form, 'data': data, 'calibrator': self.target})

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        cadence_form = ScheduleCadenceForm()
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.render_to_response(self.get_context_data(form=form, cad_form=cadence_form, body=self.target))

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
        return render(request, 'core/schedule_confirm.html', {'form': new_form, 'data': data, 'body': self.body, 'cadence': True})


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


class ScheduleCalibSpectra(LoginRequiredMixin, LookUpCalibMixin, FormView):
    """
    Creates a suggested spectroscopic calibration observation request, including time
    window, calibrations and molecules
    """
    template_name = 'core/schedule_spectra.html'
    form_class = ScheduleSpectraForm
    ok_to_schedule = False

    def get(self, request, *args, **kwargs):
        # Override default exposure time for brighter calib targets and set the initial
        # instrument code to that which came in via the URL and the kwargs
        form = ScheduleSpectraForm(initial={'exp_length' : 180.0,
                                            'instrument_code' : kwargs.get('instrument_code', '')}
                                  )
        return self.render_to_response(self.get_context_data(form=form, body=self.target))

    def post(self, request, *args, **kwargs):
        form = ScheduleSpectraForm(request.POST)
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.render_to_response(self.get_context_data(form=form, body=self.target))

    def form_valid(self, form, request):
        data = schedule_check(form.cleaned_data, self.target, self.ok_to_schedule)
        new_form = ScheduleBlockForm(data)
        return render(request, 'core/calib_schedule_confirm.html', {'form': new_form, 'data': data, 'calibrator': self.target})

    def get_context_data(self, **kwargs):
        """
        Only show proposals the current user is a member of
        """
        proposals = user_proposals(self.request.user)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        kwargs['form'].fields['proposal_code'].choices = proposal_choices
        return kwargs


class ScheduleCalibSubmit(LoginRequiredMixin, SingleObjectMixin, FormView):
    """
    Takes the hidden form input from ScheduleParameters, validates them as a double check.
    Then submits to the scheduler. If a tracking number is returned, the object has been scheduled and we record a Block.
    """
    template_name = 'core/calib_schedule_confirm.html'
    form_class = ScheduleBlockForm
    model = StaticSource

    def get_context_data(self, **kwargs):
        context = super(ScheduleCalibSubmit, self).get_context_data(**kwargs)
        context['calibrator'] = self.object

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.form_invalid(form, request)

    def form_valid(self, form, request):
        if 'edit' in request.POST:
            # Recalculate the parameters by amending the block length
            data = schedule_check(form.cleaned_data, self.object)
            new_form = ScheduleBlockForm(data)
            return render(request, self.template_name, {'form': new_form, 'data': data, 'calibrator': self.object})
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
            return super(ScheduleCalibSubmit, self).form_valid(form)

    def form_invalid(self, form, request):
        # Recalculate the parameters using new form data
        data = schedule_check(form.cleaned_data, self.object)
        new_form = ScheduleBlockForm(data)
        return render(request, 'core/calib_schedule_confirm.html', {'form': new_form, 'data': data, 'calibrator': self.object})

    def get_success_url(self):
        return reverse('home')


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
            return self.form_invalid(form, request)

    def form_valid(self, form, request):
        # Recalculate the parameters using new form data
        data = schedule_check(form.cleaned_data, self.object)
        new_form = ScheduleBlockForm(data)
        if 'edit' in request.POST:
            return render(request, 'core/schedule_confirm.html', {'form': new_form, 'data': data, 'body': self.object})
        elif 'submit' in request.POST and new_form.is_valid():
            target = self.get_object()
            username = ''
            if request.user.is_authenticated():
                username = request.user.get_username()
            tracking_num, sched_params = schedule_submit(new_form.cleaned_data, target, username)
            if tracking_num:
                messages.success(self.request, "Request %s successfully submitted to the scheduler" % tracking_num)
                block_resp = record_block(tracking_num, sched_params, new_form.cleaned_data, target)
                self.success = True
                if block_resp:
                    messages.success(self.request, "Block recorded")
                else:
                    messages.warning(self.request, "Record not created")
            else:
                self.success = False
                msg = parse_portal_errors(sched_params)
                messages.warning(self.request, msg)
            return super(ScheduleSubmit, self).form_valid(new_form)

    def form_invalid(self, form, request):
        # Recalculate the parameters using new form data
        data = schedule_check(form.cleaned_data, self.object)
        new_form = ScheduleBlockForm(data)
        return render(request, 'core/schedule_confirm.html', {'form': new_form, 'data': data, 'body': self.object})

    def get_success_url(self):
        if self.success:
            return reverse('home')
        else:
            return reverse('target', kwargs={'pk': self.object.id})


def parse_portal_errors(sched_params):
    """Parse a passed <sched_params> response from the LCO Observing Portal via
    schedule_submit() and try to extract an error message
    """

    msg = "It was not possible to submit your request to the scheduler."
    if sched_params.get('error_msg', None):
        msg += "\nAdditional information:"
        error_groups = sched_params['error_msg']
        for error_type in error_groups.keys():
            error_msgs = error_groups[error_type]
            for errors in error_msgs:
                if type(errors) == str:
                    msg += "\n{err_type}: {error}".format(err_type=error_type, error=errors)
                elif type(errors) == dict:
                    for key in errors:
                        msg += "\n".join(errors[key])
    return msg


def schedule_check(data, body, ok_to_schedule=True):

    spectroscopy = data.get('spectroscopy', False)
    solar_analog = data.get('solar_analog', False)
    body_elements = model_to_dict(body)

    # Get period and jitter for cadence
    period = data.get('period', None)
    jitter = data.get('jitter', None)

    if spectroscopy:
        data['site_code'] = data['instrument_code'][0:3]
    else:
        data['instrument_code'] = ''

    # Check if we have a high eccentricity object and it's not of comet type
    if body_elements.get('eccentricity', 0.0) >= 0.9 and body_elements.get('elements_type', None) != 'MPC_COMET':
        logger.warning("Preventing attempt to schedule high eccentricity non-Comet")
        ok_to_schedule = False

    # If ToO mode is set, check for valid proposal
    too_mode = data.get('too_mode', False)
    if too_mode is True:
        proposal = Proposal.objects.get(code=data['proposal_code'])
        if proposal and proposal.time_critical is False:
            logger.warning("ToO/TC observations not possible with this proposal")
            too_mode = False

    # if start/stop times already established, use those
    if data.get('start_time') and data.get('end_time') and (data.get('edit_window', False) or period is not None):
        dark_start = data.get('start_time')
        dark_end = data.get('end_time')
    elif data['site_code'] in ['1M0', '2M0', '0M4']:
        utc_date = data.get('utc_date', datetime.utcnow().date())
        if utc_date == datetime.utcnow().date():
            dark_start = datetime.utcnow().replace(microsecond=0).replace(second=0)
        else:
            dark_start = datetime.combine(utc_date, datetime.min.time())
        dark_end = dark_start + timedelta(hours=24)
    else:
        # Otherwise, calculate night based on site and date.
        dark_start, dark_end = determine_darkness_times(data['site_code'], data.get('utc_date', datetime.utcnow().date()))
        if dark_end <= datetime.utcnow():
            # If night has already ended, use next night instead
            dark_start, dark_end = determine_darkness_times(data['site_code'], data['utc_date'] + timedelta(days=1))
    dark_midpoint = dark_start + (dark_end - dark_start) / 2
    utc_date = data.get('utc_date', dark_midpoint.date())
    # Get semester boundaries for "current" semester
    semester_date = max(datetime.utcnow(), datetime.combine(utc_date, datetime.min.time()))
    semester_start, semester_end = get_semester_dates(semester_date)

    # Get maximum airmass
    max_airmass = data.get('max_airmass', 1.74)
    alt_limit = get_alt_from_airmass(max_airmass)

    # calculate visibility
    # Determine the semester boundaries for the current time and truncate the visibility time and
    # therefore the windows appropriately.
    dark_and_up_time, max_alt, rise_time, set_time = get_visibility(None, None, utc_date, data['site_code'], '2 m', alt_limit, False, body_elements)
    if (data['site_code'] in ['1M0', '2M0', '0M4']) or (period is not None and dark_end - dark_start >= timedelta(days=1)):
        # If using generic telescope or cadence lasting more than 1 day ignore object visibility
        rise_time = dark_start
        set_time = dark_end
    if rise_time and set_time:
        if set_time < dark_start > rise_time:
            # If object sets before it gets dark, use next night instead
            dark_and_up_time, max_alt, rise_time, set_time = get_visibility(None, None, utc_date+timedelta(days=1), data['site_code'], '2 m', alt_limit, False, body_elements)
        if rise_time and set_time:
            if rise_time.day != set_time.day and semester_start < rise_time:
                # if observations cross UT day boundary, check semester boundaries.
                semester_date = max(datetime.utcnow(), datetime.combine(utc_date, datetime.min.time()))
                semester_start, semester_end = get_semester_dates(semester_date)
            rise_time = up_time = max(rise_time, semester_start)
            set_time = down_time = min(set_time, semester_end)
            if rise_time < datetime.utcnow() and period is None:
                # If start time would be in the past, set to now except for cadence.
                rise_time = datetime.utcnow().replace(microsecond=0)
            if down_time > dark_end > up_time:
                # If object sets after morning, truncate to end of night
                set_time = dark_end
            if up_time < dark_start < down_time:
                # if object rises before evening, truncate to start of night
                rise_time = dark_start
            if set_time < rise_time:
                # object sets before it rises somehow, set window to 0.
                set_time = rise_time
            mid_dark_up_time = rise_time + (set_time - rise_time) / 2
        else:
            mid_dark_up_time = rise_time = set_time = up_time = down_time = dark_midpoint
    else:
        mid_dark_up_time = rise_time = set_time = up_time = down_time = dark_midpoint
    if max_alt is not None:
        max_alt_airmass = S.sla_airmas((pi/2.0)-radians(max_alt))
    else:
        max_alt_airmass = 13
        dark_and_up_time = 0
    if abs(mid_dark_up_time.date() - utc_date) > timedelta(days=1) or rise_time.date() > utc_date or set_time.date() < utc_date:
        utc_date = mid_dark_up_time.date()

    solar_analog_id = -1
    solar_analog_params = {}
    solar_analog_exptime = 60
    if type(body) == Body:
        emp = compute_ephem(mid_dark_up_time, body_elements, data['site_code'], dbg=False, perturb=False, display=False)
        if emp == {}:
            emp['date'] = mid_dark_up_time
            emp['ra'] = -99
            emp['dec'] = -99
            emp['mag'] = -99
            emp['sky_motion'] = -99
        ra = emp['ra']
        dec = emp['dec']
        magnitude = emp['mag']
        speed = emp['sky_motion']
        if spectroscopy and solar_analog:
            # Try and find a suitable solar analog "close" to RA, Dec midpoint
            # of block
            close_solarstd, close_solarstd_params = find_best_solar_analog(ra, dec, data['site_code'])
            if close_solarstd is not None:
                solar_analog_id = close_solarstd.id
                solar_analog_params = close_solarstd_params
    else:
        magnitude = body.vmag
        speed = 0.0
        ra = radians(body.ra)
        dec = radians(body.dec)

    # Determine filter pattern
    if data.get('filter_pattern'):
        filter_pattern = data.get('filter_pattern')
    elif data['site_code'] == 'E10' or data['site_code'] == 'F65' or data['site_code'] == '2M0':
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

    # Check for binning
    bin_mode = data.get('bin_mode', None)

    # Get maximum airmass
    max_airmass = data.get('max_airmass', 1.74)
    alt_limit = get_alt_from_airmass(max_airmass)

    # Pull out LCO Site, Telescope Class using site_config.py
    lco_site_code = next(key for key, value in cfg.valid_site_codes.items() if value == data['site_code'])

    # Determine slot length
    if data.get('slot_length', None):
        slot_length = data.get('slot_length')
    else:
        try:
            slot_length = determine_slot_length(magnitude, data['site_code'])
        except MagRangeError:
            slot_length = 60
            ok_to_schedule = False

    # determine lunar position
    moon_alt, moon_obj_sep, moon_phase = calc_moon_sep(mid_dark_up_time, ra, dec, data['site_code'])
    min_lunar_dist = data.get('min_lunar_dist', 30)
    if moon_phase <= .25:
        moon_phase_code = 'D'
    elif moon_phase <= .75:
        moon_phase_code = 'G'
    else:
        moon_phase_code = 'B'

    # Calculate slot length, exposure time, SNR
    snr = None
    saturated = None
    if spectroscopy:
        snr_params = {'airmass': max_alt_airmass,
                      'slit_width': float(filter_pattern[5:8])*u.arcsec,
                      'moon_phase': moon_phase_code
                      }
        new_mag, new_passband, snr, saturated = calc_asteroid_snr(magnitude, 'V', data['exp_length'], instrument=data['instrument_code'], params=snr_params)
        exp_count = data['exp_count']
        exp_length = data.get('exp_length', 1)
        slot_length = determine_spectro_slot_length(data['exp_length'], data['calibs'])
        slot_length /= 60.0
        slot_length = ceil(slot_length)
        # If automatically finding Solar Analog, calculate exposure time.
        # Currently assume bright enough that 180s is the maximum exposure time.
        if solar_analog and solar_analog_params:
            if data.get('calibsource_exptime', None):
                solar_analog_exptime = data.get('calibsource_exptime')
            else:
                solar_analog_exptime = calc_asteroid_snr(solar_analog_params['vmag'], 'V', 180, instrument=data['instrument_code'], params=snr_params, optimize=True)
    else:
        # Determine exposure length and count
        if data.get('exp_length', None):
            exp_length = data.get('exp_length')
            slot_length, exp_count = determine_exp_count(slot_length, exp_length, data['site_code'], filter_pattern, bin_mode=bin_mode)
        else:
            exp_length, exp_count = determine_exp_time_count(speed, data['site_code'], slot_length, magnitude, filter_pattern, bin_mode=bin_mode)
            slot_length, exp_count = determine_exp_count(slot_length, exp_length, data['site_code'], filter_pattern, exp_count, bin_mode=bin_mode)
        if exp_length is None or exp_count is None:
            ok_to_schedule = False

    # determine stellar trailing
    if spectroscopy:
        ag_exp_time = data.get('ag_exp_time', 10)
        trail_len = determine_star_trails(speed, ag_exp_time)
    else:
        ag_exp_time = None
        trail_len = determine_star_trails(speed, exp_length)
    if lco_site_code[-4:-1].upper() == "0M4":
        typical_seeing = 3.0
    else:
        typical_seeing = 2.0

    # get ipp value
    ipp_value = data.get('ipp_value', 1.00)

    # get acceptability threshold
    acceptability_threshold = data.get('acceptability_threshold', 90)

    # Determine pattern iterations
    if exp_count:
        pattern_iterations = float(exp_count) / float(len(filter_pattern.split(',')))
        pattern_iterations = round(pattern_iterations, 2)
    else:
        pattern_iterations = None

    if period is not None and jitter is not None:
        # Increase Jitter if shorter than slot length
        if jitter < slot_length / 60:
            jitter = round(slot_length / 60, 2)+.01
        if period < 0.02:
            period = 0.02

        # Number of times the cadence request will run between start and end date
        cadence_start = rise_time
        cadence_end = set_time
        total_run_time = cadence_end - cadence_start
        cadence_period = timedelta(seconds=data['period']*3600.0)
        total_requests = 1 + int(floor(total_run_time.total_seconds() / cadence_period.total_seconds()))

        # Remove the last start if the request would run past the cadence end
        if cadence_start + total_requests * cadence_period + timedelta(seconds=slot_length*60.0) > cadence_end:
            total_requests -= 1

        # Total hours of time used by all cadence requests
        total_time = timedelta(seconds=slot_length*60.0) * total_requests
        total_time = total_time.total_seconds()/3600.0

    # Create Group ID
    group_name = validate_text(data.get('group_name', None))

    suffix = datetime.strftime(utc_date, '%Y%m%d')
    if period and jitter:
        suffix = "cad-%s-%s" % (datetime.strftime(rise_time, '%Y%m%d'), datetime.strftime(set_time, '%m%d'))
    elif spectroscopy:
        suffix += "_spectra"
    if too_mode is True:
        suffix += '_ToO'
    default_group_name = body.current_name() + '_' + data['site_code'].upper() + '-' + suffix
    if not group_name or (group_name == default_group_name + '_bin2x2' and bin_mode != '2k_2x2'):
        group_name = default_group_name
    if group_name == default_group_name and bin_mode == '2k_2x2':
        group_name += '_bin2x2'

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
        'too_mode': too_mode,
        'site_code': data['site_code'],
        'proposal_code': data['proposal_code'],
        'group_name': group_name,
        'utc_date': utc_date.isoformat(),
        'start_time': rise_time.replace(second=0).isoformat(),
        'end_time': set_time.replace(second=0).isoformat(),
        'mid_time': mid_dark_up_time.replace(second=0).replace(microsecond=0).isoformat(),
        'vis_start': up_time.isoformat(),
        'vis_end': down_time.isoformat(),
        'edit_window': data.get('edit_window', False),
        'ra_midpoint': ra,
        'dec_midpoint': dec,
        'period': period,
        'jitter': jitter,
        'bin_mode': bin_mode,
        'snr': snr,
        'saturated': saturated,
        'spectroscopy': spectroscopy,
        'calibs': data.get('calibs', ''),
        'instrument_code': data['instrument_code'],
        'lco_site': lco_site_code[0:3],
        'lco_tel': lco_site_code[-4:-1],
        'lco_enc': lco_site_code[4:8],
        'max_alt': max_alt,
        'max_alt_airmass': max_alt_airmass,
        'vis_time': dark_and_up_time,
        'moon_alt': moon_alt,
        'moon_sep': moon_obj_sep,
        'moon_phase': moon_phase * 100,
        'min_lunar_dist': min_lunar_dist,
        'max_airmass': max_airmass,
        'ipp_value': ipp_value,
        'ag_exp_time': ag_exp_time,
        'acceptability_threshold': acceptability_threshold,
        'trail_len': trail_len,
        'typical_seeing': typical_seeing,
        'solar_analog': solar_analog,
        'calibsource': solar_analog_params,
        'calibsource_id': solar_analog_id,
        'calibsource_exptime': solar_analog_exptime,
    }

    if period and jitter:
        resp['num_times'] = total_requests
        resp['total_time'] = total_time

    return resp


def compute_vmag_pa(body_elements, data):
    emp_line_base = compute_ephem(data['start_time'], body_elements, data['site_code'], dbg=False, perturb=False, display=False)
    # assign Magnitude and position angle
    if emp_line_base['mag'] and emp_line_base['mag'] > 0:
        body_elements['v_mag'] = emp_line_base['mag']
    body_elements['sky_pa'] = emp_line_base['sky_motion_pa']

    return body_elements


def schedule_submit(data, body, username):
    # Assemble request
    # Send to scheduler
    if type(body) == StaticSource:
        body_elements = {}
    else:
        body_elements = model_to_dict(body)
        body_elements['epochofel_mjd'] = body.epochofel_mjd()
        body_elements['epochofperih_mjd'] = body.epochofperih_mjd()
        body_elements['current_name'] = body.current_name()
    # If we have a solar analog requested, retrieve corresponding StaticSource
    # object and assemble parameters
    calibsource_params = {}
    if data.get('solar_analog', False) and data.get('calibsource_id', -1) > 0:
        try:
            calibsource = StaticSource.objects.get(pk=data['calibsource_id'])
            calibsource_params = {  'id'      : calibsource.pk,
                                    'name'    : calibsource.name,
                                    'ra_deg'  : calibsource.ra,
                                    'dec_deg' : calibsource.dec,
                                    'pm_ra'   : calibsource.pm_ra,
                                    'pm_dec'  : calibsource.pm_dec,
                                    'parallax': calibsource.parallax,
                                    'source_type' : calibsource.source_type,
                                    'vmag' : calibsource.vmag,
                                    'calib_exptime': data.get('calibsource_exptime', 60)
                                 }
        except StaticSource.DoesNotExist:
            logger.error("Was passed a StaticSource id=%d, but it now can't be found" % data['calibsource_id'])

    emp_at_start = None
    if isinstance(body, Body) and data.get('spectroscopy', False) is not False and body.source_type != 'C' and body.elements_type != 'MPC_COMET':

        # Check for recent elements
        if abs(body.epochofel-data['start_time']) >= timedelta(days=2):
            # Update MPC observations assuming too many updates have not been done recently and target is not a comet
            cut_off_time = timedelta(minutes=1)
            now = datetime.utcnow()
            recent_updates = Body.objects.exclude(source_type='U').filter(update_time__gte=now-cut_off_time)
            if len(recent_updates) < 1:
                update_MPC_obs(body.current_name())

            # Invoke find_orb to update Body's elements and return ephemeris
            refit_with_findorb(body.id, data['site_code'], data['start_time'])

            body.refresh_from_db()
            body_elements = model_to_dict(body)
            body_elements['epochofel_mjd'] = body.epochofel_mjd()
            body_elements['epochofperih_mjd'] = body.epochofperih_mjd()
            body_elements['current_name'] = body.current_name()
        else:
            logger.info("Current epoch is <2 days old; not updating")

    if type(body) != StaticSource and data.get('spectroscopy', False) is True:
        body_elements = compute_vmag_pa(body_elements, data)

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
              'bin_mode': data['bin_mode'],
              'filter_pattern': data['filter_pattern'],
              'exp_count': data['exp_count'],
              'exp_time': data['exp_length'],
              'site_code': data['site_code'],
              'start_time': data['start_time'],
              'end_time': data['end_time'],
              'group_name': data['group_name'],
              'too_mode': data.get('too_mode', False),
              'spectroscopy': data.get('spectroscopy', False),
              'calibs': data.get('calibs', ''),
              'instrument_code': data['instrument_code'],
              'solar_analog': data.get('solar_analog', False),
              'calibsource': calibsource_params,
              'max_airmass': data.get('max_airmass', 1.74),
              'ipp_value': data.get('ipp_value', 1),
              'min_lunar_distance': data.get('min_lunar_dist', 30),
              'acceptability_threshold': data.get('acceptability_threshold', 90),
              'ag_exp_time': data.get('ag_exp_time', 10)
              }
    if data['period'] or data['jitter']:
        params['period'] = data['period']
        params['jitter'] = data['jitter']
    # If we have a (static) StaticSource object, fill in details needed by make_target
    if type(body) == StaticSource:
        params['ra_deg'] = body.ra
        params['dec_deg'] = body.dec
        params['source_id'] = body.current_name()
        params['pm_ra'] = body.pm_ra
        params['pm_dec'] = body.pm_dec
        params['parallax'] = body.parallax
        params['source_type'] = body.source_type
        params['vmag'] = body.vmag
    # Check for pre-existing block
    tracking_number = None
    resp_params = None
    if check_for_block(data, params, body) == 1:
        # Append another suffix to allow 2 versions of the block. Must
        # do this to both `data` (so the next Block check works) and to
        # `params` so the correct name will go to the Valhalla/scheduler
        data['group_name'] += '_2'
        params['group_name'] = data['group_name']
    elif check_for_block(data, params, body) >= 2:
        # Multiple blocks found
        resp_params = {'error_msg' : 'Multiple Blocks for same day and site found'}
    if check_for_block(data, params, body) == 0:
        # Submit to scheduler and then record block
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
        form = SpectroFeasibilityForm(request.POST, body=self.body)
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.render_to_response(self.get_context_data(form=form, body=self.body))


class CalibSpectroFeasibility(LookUpCalibMixin, FormView):

    template_name = 'core/feasibility.html'
    form_class = SpectroFeasibilityForm

    def get(self, request, *args, **kwargs):
        form = SpectroFeasibilityForm(body=self.target, initial={'exp_length' : 180.0})
        return self.render_to_response(self.get_context_data(form=form, body=self.target))

    def form_valid(self, form, request):
        data = feasibility_check(form.cleaned_data, self.target)
        new_form = SpectroFeasibilityForm(data, body=self.target)
        return render(request, 'core/feasibility.html', {'form': new_form, 'data': data, 'body': self.target})

    def post(self, request, *args, **kwargs):
        form = SpectroFeasibilityForm(request.POST, body=self.target)
        if form.is_valid():
            return self.form_valid(form, request)
        else:
            return self.render_to_response(self.get_context_data(form=form, body=self.target))


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
    if isinstance(body, Body):
        spectral_type = 'Mean'
    else:
        spectral_type = 'Solar'
    data['new_mag'], data['new_passband'], data['snr'], data['saturated'] = calc_asteroid_snr(data['magnitude'], ast_mag_bandpass, data['exp_length'], instrument=data['instrument_code'], params=snr_params, taxonomy=spectral_type)
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


def get_characterization_targets():
    """Function to return the list of Characterization targets.
    If we change this, also change models.Body.characterization_target"""

    characterization_list = Body.objects.filter(active=True).exclude(origin='M').exclude(source_type='U')
    return characterization_list


def build_characterization_list(disp=None):
    params = {}
    # If we don't have any Body instances, return None instead of breaking
    try:
        # If we change the definition of Characterization Target,
        # also update models.Body.characterization_target()
        char_targets = get_characterization_targets()
        unranked = []
        for body in char_targets:
            try:
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
                                m_wav = "Yes"
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
                    startdate = '[--'
                    enddate = '--]'
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
                body_dict['motion'] = emp_line[4]
                body_dict['radar_target'] = body.radar_target()
                if disp:
                    if disp in body_dict['obs_needed']:
                        unranked.append(body_dict)
                else:
                    unranked.append(body_dict)
            except Exception as e:
                logger.error('Characterization target %s failed on %s' % (body.name, e))
    except Body.DoesNotExist as e:
        unranked = None
        logger.error('Characterization list failed on %s' % e)
    params = {
        'targets': Body.objects.filter(active=True).count(),
        'blocks': Block.objects.filter(active=True).count(),
        'char_targets': unranked,
        'char_filter': disp
    }
    return params


def build_lookproject_list(disp=None):
    params = {}
    # If we don't have any Body instances, return None instead of breaking
    try:
        look_targets = Body.objects.filter(active=True, origin='O')
        unranked = []
        for body in look_targets:
            try:
                body_dict = model_to_dict(body)
                body_dict['current_name'] = body.current_name()
                body_dict['ingest_date'] = body.ingest
                source_types = [x[1] for x in OBJECT_TYPES if x[0] == body.source_type]
                if len(source_types) == 1:
                    body_dict['source_type'] = source_types[0]
                subtype1 = [x[1] for x in OBJECT_SUBTYPES if x[0] == body.source_subtype_1]
                subtype2 = [x[1] for x in OBJECT_SUBTYPES if x[0] == body.source_subtype_2]
                subtypes = subtype1+subtype2
                if len(subtypes) == 1:
                    body_dict['subtypes'] = subtypes[0]
                elif len(subtypes) > 1:
                    body_dict['subtypes'] = ", ".join(subtypes)
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
                    startdate = '[--'
                    enddate = '--]'
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
                body_dict['motion'] = emp_line[4]
                unranked.append(body_dict)
            except Exception as e:
                logger.error('LOOK target %s failed on %s' % (body.name, e))
        latest = Body.objects.filter(source_type='C').latest('ingest')
        max_dt = latest.ingest
        min_dt = max_dt - timedelta(days=30)
        newest_comets = Body.objects.filter(ingest__range=(min_dt, max_dt), source_type='C')
        comets = []
        for body in newest_comets:
            try:
                body_dict = model_to_dict(body)
                body_dict['current_name'] = body.current_name()
                body_dict['ingest_date'] = body.ingest
                subtype1 = [x[1] for x in OBJECT_SUBTYPES if x[0] == body.source_subtype_1]
                subtype2 = [x[1] for x in OBJECT_SUBTYPES if x[0] == body.source_subtype_2]
                subtypes = subtype1+subtype2
                if len(subtypes) == 1:
                    body_dict['subtypes'] = subtypes[0]
                elif len(subtypes) > 1:
                    body_dict['subtypes'] = ", ".join(subtypes)
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
                    startdate = '[--'
                    enddate = '--]'
                days_to_start = body_dict['obs_sdate']-obs_dates[2]
                days_to_end = body_dict['obs_edate']-obs_dates[2]
                # Define a sorting Priority:
                # Currently a combination of imminence and window width.
                body_dict['obs_start'] = startdate
                body_dict['obs_end'] = enddate
                body_dict['ra'] = emp_line[0]
                body_dict['dec'] = emp_line[1]
                body_dict['v_mag'] = emp_line[2]
                body_dict['motion'] = emp_line[4]
                body_dict['period'] = body.period
                body_dict['recip_a'] = body.recip_a
                body_dict['perihdist'] = body.perihdist
                comets.append(body_dict)
            except Exception as e:
                logger.error('LOOK target %s failed on %s' % (body.name, e))
    except Body.DoesNotExist as e:
        unranked = None
        logger.error('LOOK list failed on %s' % e)
    params = {
        'look_targets': unranked,
        'new_comets': comets
    }
    return params


def look_project(request):

    params =  build_lookproject_list()
    return render(request, 'core/lookproject.html', params)

def check_for_block(form_data, params, new_body):
    """Checks if a block with the given name exists in the Django DB.
    Return 0 if no block found, 1 if found, 2 if multiple blocks found"""

    # XXX Code smell, duplicated from sources_subs.configure_defaults()
    site_list = { 'V37' : 'ELP' ,
                  'V39' : 'ELP',
                  'K92' : 'CPT',
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
                  'T04' : 'OGG'
                  }

    try:
        block_id = SuperBlock.objects.get(body=new_body.id,
                                     groupid__contains=form_data['group_name'],
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


def record_block(tracking_number, params, form_data, target):
    """Records a just-submitted observation as a SuperBlock and Block(s) in the database.
    """

    logger.debug("form data=%s" % form_data)
    logger.debug("   params=%s" % params)
    if tracking_number:
        cadence = False
        if len(params.get('request_numbers', [])) > 1 and params.get('period', -1.0) > 0.0 and params.get('jitter', -1.0) > 0.0:
            cadence = True
        proposal = Proposal.objects.get(code=form_data['proposal_code'])
        sblock_kwargs = {
                         'proposal': proposal,
                         'groupid': form_data['group_name'],
                         'block_start': form_data['start_time'],
                         'block_end': form_data['end_time'],
                         'tracking_number': tracking_number,
                         'cadence': cadence,
                         'period': params.get('period', None),
                         'jitter': params.get('jitter', None),
                         'timeused': params.get('block_duration', None),
                         'rapid_response': params.get('too_mode', False),
                         'active': True,
                       }
        if isinstance(target, StaticSource):
            sblock_kwargs['calibsource'] = target
        else:
            sblock_kwargs['body'] = target
        # Check if this went to a rapid response proposal
        if proposal.time_critical is True:
            sblock_kwargs['rapid_response'] = True
        sblock_pk = SuperBlock.objects.create(**sblock_kwargs)
        i = 0
        for request, request_type in params.get('request_numbers', {}).items():
            # cut off json UTC timezone remnant
            no_timezone_blk_start = params['request_windows'][i][0]['start'][:-1]
            no_timezone_blk_end = params['request_windows'][i][0]['end'][:-1]
            try:
                dt_notz_blk_start = datetime.strptime(no_timezone_blk_start, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                dt_notz_blk_start = datetime.strptime(no_timezone_blk_start, '%Y-%m-%dT%H:%M:%S.%f')
            try:
                dt_notz_blk_end = datetime.strptime(no_timezone_blk_end, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                dt_notz_blk_end = datetime.strptime(no_timezone_blk_end, '%Y-%m-%dT%H:%M:%S.%f')
            obstype = Block.OPT_IMAGING
            if params.get('spectroscopy', False):
                obstype = Block.OPT_SPECTRA
                if request_type == 'SIDEREAL' or request_type == 'ICRS':
                    obstype = Block.OPT_SPECTRA_CALIB

            # sort site vs camera
            site = params.get('site', None)
            if site is not None:
                site = site.lower()
            else:
                inst = params.get('instrument', None)
                if inst:
                    chunks = inst.split('-')
                    if chunks[-1] == 'SBIG':
                        site = 'sbg'
                    elif chunks[-1] == 'SPECTRAL':
                        site = 'spc'
                    elif chunks[-1] == 'SINISTRO':
                        site = 'sin'

            block_kwargs = { 'superblock' : sblock_pk,
                             'telclass' : params['pondtelescope'].lower(),
                             'site'     : site,
                             'obstype'  : obstype,
                             'block_start' : dt_notz_blk_start,
                             'block_end'   : dt_notz_blk_end,
                             'request_number'  : request,
                             'num_exposures'   : params['exp_count'],
                             'exp_length'      : params['exp_time'],
                             'active'   : True
                           }
            if (request_type == 'SIDEREAL' or request_type == 'ICRS') and params.get('solar_analog', False) is True and len(params.get('calibsource', {})) > 0:
                try:
                    calib_source = StaticSource.objects.get(pk=params['calibsource']['id'])
                except StaticSource.DoesNotExist:
                    logger.error("Tried to refetch a StaticSource (# %d) which now does not exist" % params['calibsource']['id'])
                    return False
                block_kwargs['body'] = None
                block_kwargs['calibsource'] = calib_source
                block_kwargs['exp_length'] = params['calibsrc_exptime']
            elif request_type == 'SIDEREAL' or request_type == 'ICRS':
                block_kwargs['body'] = None
                block_kwargs['calibsource'] = target
            else:
                block_kwargs['body'] = target
                block_kwargs['calibsource'] = None
            pk = Block.objects.create(**block_kwargs)
            i += 1
        return True
    else:
        return False


def sort_des_type(name, default='T'):
    # Guess name type based on structure
    n = name.strip()
    if not n:
        return ''
    if n.isdigit():
        dtype = '#'
    elif ' ' in n or '_' in n:
        dtype = 'P'
    elif n[-1] in ['P', 'C', 'D'] and n[:-1].isdigit():
        dtype = '#'
    elif bool(re.search('\d', n)) or (not n.isupper() and sum(1 for c in n if c.isupper()) > 1):
        dtype = 'C'
    elif n.replace('-', '').replace("'", "").isalpha() and not n.isupper():
        dtype = 'N'
    else:
        dtype = default
    return dtype


def return_fields_for_saving():
    """Returns a list of fields that should be checked before saving a revision.
    Split out from save_and_make_revision() so it can be consistently used by the
    remove_bad_revisions management command."""

    body_fields = ['provisional_name', 'provisional_packed', 'name', 'origin', 'source_type',  'elements_type',
              'epochofel', 'abs_mag', 'slope', 'orbinc', 'longascnode', 'eccentricity', 'argofperih', 'meandist', 'meananom',
              'score', 'discovery_date', 'num_obs', 'arc_length']

    param_fields = ['abs_mag', 'slope', 'provisional_name', 'name']

    return body_fields, param_fields


def save_and_make_revision(body, kwargs):
    """
    Make a revision if any of the parameters have changed, but only do it once
    per ingest not for each parameter.
    Converts current model instance into a dict and compares a subset of elements with
    incoming version. Incoming variables may be generically formatted as strings,
    so use the type of original to convert and then compare.
    """

    b_fields, p_fields = return_fields_for_saving()

    p_field_to_p_code = {'abs_mag': 'H', 'slope': 'G', 'provisional_name': 'C', 'name': 'P'}

    update = False

    body_dict = model_to_dict(body)
    for k, v in kwargs.items():
        param = body_dict.get(k, '')
        if isinstance(param, float) and v is not None:
            v = float(v)
        if v != param:
            setattr(body, k, v)
            if k in b_fields:
                update = True
        if k in p_fields:
            param_code = p_field_to_p_code[k]
            if 'name' in k:
                if k == 'name':
                    param_code = sort_des_type(str(v))
                p_dict = {'desig_type': param_code,
                              'value': v,
                              'notes': 'MPC Default',
                              'preferred': True,
                              }
            else:
                p_dict = {'value': v,
                          'parameter_type': param_code,
                          'preferred': False,
                          'reference': 'MPC Default'
                          }
            phys_update = body.save_physical_parameters(p_dict)
            if k == 'abs_mag' and phys_update:
                albedo = body.get_physical_parameters(param_type='ab', return_all=False)
                if not albedo:
                    albedo = [{'value': 0.14, 'error': 0.5-0.14, 'error2': 0.14-0.01}]
                albedo_mid = albedo[0]['value']
                if albedo[0]['error']:
                    albedo_high = albedo_mid + albedo[0]['error']
                    if albedo[0]['error2']:
                        albedo_low = albedo_mid - albedo[0]['error2']
                    else:
                        albedo_low = albedo_mid - albedo[0]['error']
                else:
                    albedo_high = albedo_mid + 0.01
                    albedo_low = albedo_mid - 0.01
                diam_dict = {'value': round(asteroid_diameter(albedo_mid, v), 2),
                             'error': round(asteroid_diameter(albedo_low, v) - asteroid_diameter(albedo_mid, v)),
                             'error2': round(asteroid_diameter(albedo_mid, v) - asteroid_diameter(albedo_high, v)),
                             'parameter_type': 'D',
                             'units': 'm',
                             'preferred': True,
                             'reference': 'MPC Default',
                             'notes': 'Initial Diameter Guess using H={} and albedo={} ({} to {})'.format(v, round(albedo_mid, 2), round(albedo_low, 2), round(albedo_high, 2))
                            }
                body.save_physical_parameters(diam_dict)

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
    NEOCP_orb_url = 'https://cgi.minorplanetcenter.net/cgi-bin/showobsorbs.cgi?Obj=%s&orb=y' % obj_id

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
        line = line.strip()
        if 'NEOCPNomin' in line or 'MPC       ' in line:
            current = line.split()
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
                'not_seen' : None,
                'orbit_rms' : float(current[15])
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

        elif 21 <= len(current) <= 25:
            # The first 20 characters can get very messy if there is a temporary
            # and permanent designation as the absolute magnitude and slope gets
            # pushed up and partially overwritten. Sort this mess out and then the
            # rest obeys the documentation on the MPC site:
            # https://www.minorplanetcenter.net/iau/info/MPOrbitFormat.html)

            # First see if the absolute mag. and slope are numbers in the correct place
            try:
                abs_mag = float(line[8:13])
                slope = float(line[14:19])
            except ValueError:
                # Nope, we have a mess and will have to assume a slope
                abs_mag = float(line[12:17])
                slope = 0.15

            # See if there is a "readable desigination" towards the end of the line
            readable_desig = None
            if len(line) > 194:
                readable_desig = line[166:194].strip()
            elements_type = 'MPC_MINOR_PLANET'
            source_type = 'U'
            if readable_desig and readable_desig[0:2] == 'P/':
                elements_type = 'MPC_COMET'
                source_type = 'C'

            # See if this is a local discovery
            provisional_name = line[0:7].rstrip()
            origin = 'M'
            if provisional_name[0:5] in ['CPTTL', 'LSCTL', 'ELPTL', 'COJTL', 'COJAT', 'LSCAT', 'LSCJM', 'LLZ00' ]:
                origin = 'L'
            params = {
                'abs_mag': abs_mag,
                'slope': slope,
                'epochofel': extract_mpc_epoch(line[20:25]),
                'meananom': float(line[26:35]),
                'argofperih': float(line[37:46]),
                'longascnode': float(line[48:57]),
                'orbinc': float(line[59:68]),
                'eccentricity': float(line[70:79]),
                'meandist': float(line[92:103]),
                'source_type': source_type,
                'elements_type': elements_type,
                'active': True,
                'origin': origin,
                'provisional_name' : provisional_name,
                'num_obs' : int(line[117:122]),
                'orbit_rms' : float(line[137:141]),
                'update_time' : datetime.utcnow(),
                'arc_length' : None,
                'not_seen' : None
            }
            # If this is a find_orb produced orbit, try and fill in the
            # 'arc length' and 'not seen' values.
            arc_length = None
            arc_units = line[132:136].rstrip()
            if arc_units == 'days':
                arc_length = float(line[127:131])
            elif arc_units == 'hrs':
                arc_length = float(line[127:131]) / 24.0
            elif arc_units == 'min':
                arc_length = float(line[127:131]) / 1440.0
            elif arc_units.isdigit():
                try:
                    first_obs_year = datetime(int(line[127:131]), 1, 1)
                except:
                    first_obs_year = None
                try:
                    last_obs_year = datetime(int(arc_units)+1, 1, 1)
                except:
                    last_obs_year = None
                if first_obs_year and last_obs_year:
                    td = last_obs_year - first_obs_year
                    arc_length = td.days
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
            if params['eccentricity'] > 0.9 or params['elements_type'] == 'MPC_COMET':
                params = convert_ast_to_comet(params, None)
    else:
        params = {}
    return params


def update_crossids(astobj, dbg=False):
    """Update the passed <astobj> for a new cross-identification.
    <astobj> is expected to be a list of:
    temporary/tracklet id, final id/failure reason, reference, confirmation date
    normally produced by the fetch_previous_NEOCP_desigs() method."""

    if len(astobj) != 4:
        return False

    temp_id = astobj[0].rstrip()
    desig = astobj[1]

    created = False
    # Find Bodies that have the 'provisional name' of <temp_id> OR (final)'name' of <desig>
    # but don't have a blank 'name'
    bodies = Body.objects.filter(Q(provisional_name=temp_id) | Q(name=desig) & ~Q(name=''))
    if dbg:
        print("temp_id={},desig={},bodies={}".format(temp_id, desig, bodies))

    if bodies.count() == 0:
        body = Body.objects.create(provisional_name=temp_id, name=desig)
        created = True
    elif bodies.count() == 1:
        body = bodies[0]
    else:
        logger.warning("Multiple objects (%d) found called %s or %s" % (bodies.count(), temp_id, desig))
        # Sort by ingest time and remove extras (if there are no Block or SuperBlocks)
        sorted_bodies = bodies.order_by('ingest')
        body = sorted_bodies[0]
        logger.info("Taking %s (id=%d) as canonical Body" % (body.current_name(), body.pk))
        for del_body in sorted_bodies[1:]:
            del_names = Designations.objects.filter(body=del_body)
            for name in del_names:
                des_dict = model_to_dict(name)
                del des_dict['id']
                del des_dict['body']
                body.save_physical_parameters(des_dict)
            logger.info("Trying to remove %s (id=%d) duplicate Body" % (del_body.current_name(), del_body.pk))
            num_sblocks = SuperBlock.objects.filter(body=del_body).count()
            num_blocks = Block.objects.filter(body=del_body).count()
            if del_body.origin != 'M':
                if num_sblocks == 0 and num_blocks == 0 and del_body.origin != 'M':
                    logger.info("Removed %s (id=%d) duplicate Body" % (del_body.current_name(), del_body.pk))
                    del_body.delete()
                else:
                    logger.warning("Found %d SuperBlocks and %d Blocks referring to this Body; not deleting" % (num_sblocks, num_blocks))
            else:
                logger.info("Origin of Body is MPC, not removing")
                # Set to inactive to prevent candidates hanging around
                del_body.active = False
                del_body.save()

    # Determine what type of new object it is and whether to keep it active
    kwargs = clean_crossid(astobj, dbg)
    if not created:
        if dbg:
            print("Did not create new Body")
        # Find out if the details have changed, if they have, save a revision
        # But first check if it is a comet or NEO and came from somewhere other
        # than the MPC. In this case, leave it active.
        if (body.source_type in ['N', 'C'] or body.source_subtype_1 == 'H') and body.origin != 'M':
            kwargs['active'] = True
        # Check if we are trying to "downgrade" a NEO or other target type
        # to an asteroid
        if body.source_type != 'A' and body.origin != 'M' and kwargs['source_type'] == 'A':
            logger.warning("Not downgrading type for %s from %s to %s" % (body.current_name(), body.source_type, kwargs['source_type']))
            kwargs['source_type'] = body.source_type
        if kwargs['source_type'] == 'C' or (kwargs['source_type'] == 'A' and kwargs['source_subtype_1'] == 'H'):
            if dbg:
                print("Converting to comet")
            kwargs = convert_ast_to_comet(kwargs, body)
        if dbg:
            print(kwargs)
        check_body = Body.objects.filter(provisional_name=temp_id, **kwargs)
        if check_body.count() == 0:
            save_and_make_revision(body, kwargs)
            body.save_physical_parameters({'value': temp_id, 'desig_type': sort_des_type(temp_id, default='C'), 'notes': 'MPC Default'})
            logger.info("Updated cross identification for %s" % body.current_name())
    elif kwargs != {}:
        # Didn't know about this object before so create but make inactive
        kwargs['active'] = False
        save_and_make_revision(body, kwargs)
        logger.info("Added cross identification for %s" % temp_id)
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
    desig = astobj[1].rstrip()
    reference = astobj[2]
    confirm_date = parse_neocp_date(astobj[3])

    time_from_confirm = datetime.utcnow() - confirm_date
    if time_from_confirm < timedelta(0):
        # if this is negative a date in the future has erroneously be assumed
        time_from_confirm = datetime.utcnow() - confirm_date.replace(year=confirm_date.year-1)
    time_from_confirm = time_from_confirm.total_seconds()

    active = True
    objtype = ''
    sub1 = ''
    if obj_id != '' and desig == 'wasnotconfirmed':
        if dbg:
            print("Case 1")
        # Unconfirmed, no longer interesting so set inactive
        objtype = 'U'
        desig = ''
        active = False
    elif obj_id != '' and desig == 'doesnotexist':
        # Did not exist, no longer interesting so set inactive
        if dbg:
            print("Case 2")
        objtype = 'X'
        desig = ''
        active = False
    elif obj_id != '' and desig == 'wasnotminorplanet':
        # "was not a minor planet"; set to satellite and no longer interesting
        if dbg:
            print("Case 3")
        objtype = 'J'
        desig = ''
        active = False
    elif obj_id != '' and desig == '' and reference == '':
        # "Was not interesting" (normally a satellite), no longer interesting
        # so set inactive
        if dbg:
            print("Case 4")
        objtype = 'W'
        desig = ''
        active = False
    elif obj_id != '' and desig != '':
        # Confirmed
        if 'C/' in desig or 'P/' in desig or bool(re.match('\d{1,4}P' ,desig)): # look for 1..4 digits and then a 'P'
            # There is a reference to a CBET or IAUC so we assume it's "very
            # interesting" i.e. a comet
            if dbg:
                print("Case 5a")
            objtype = 'C'
            # Strip off any leading zeros
            try:
                desig = str(int(desig[0:-1]))
                desig += 'P'
            except ValueError:
                pass
            if time_from_confirm > interesting_cutoff:
                active = False
        elif 'MPEC' in reference:
            # There is a reference to an MPEC so we assume it's
            # "interesting" i.e. an NEO
            if dbg:
                print("Case 5b")
            objtype = 'N'
            if 'A/' in desig:
                # Check if it is an active (Comet-like) asteroid
                objtype = 'A'
                sub1 = 'A'
            if 'I/' in desig:
                # Check if it is an inactive hyperbolic asteroid
                objtype = 'A'
                sub1 = 'H'
            if time_from_confirm > interesting_cutoff:
                active = False
        else:
            chunks = desig.split()
            for i, planet in enumerate(['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']):
                if chunks[0] == planet and ('I' in chunks[1] or 'V' in chunks[1] or 'X' in chunks[1]):
                    if dbg:
                        print("Case 5d")
                    objtype = 'M'
                    sub1 = 'P' + str(i+1)
                    active = False
                    break
            if objtype == '':
                if dbg:
                    print("Case 5z")
                objtype = 'A'
                active = False

    if objtype != '':
        params = {'source_type': objtype,
                  'source_subtype_1': sub1,
                  'name': desig,
                  'active': active
                  }
        if dbg:
            print("%07s->%s (%s/%s) %s" % (obj_id, params['name'], params['source_type'], params['source_subtype_1'], params['active']))
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
            params['meandist'] = None
            params['meananom'] = None

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

    elements = parse_mpcorbit(page, dbg=dbg)
    if elements == {}:
        logger.warning("Could not parse elements from page for %s" % obj_id)
        return False

    if type(obj_id_or_page) == BeautifulSoup:
        chunks = elements['obj_id'].split('\n')
        if len(chunks) > 1:
            obj_id = chunks[0]
        else:
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
    if body.epochofel:
        time_to_current_epoch = abs(body.epochofel - datetime.now())
        time_to_new_epoch = abs(kwargs['epochofel'] - datetime.now())
    if not body.epochofel or time_to_new_epoch <= time_to_current_epoch:
        save_and_make_revision(body, kwargs)
        if not created:
            logger.info("Updated elements for %s from MPC" % obj_id)
        else:
            logger.info("Added new orbit for %s from MPC" % obj_id)
    else:
        body.origin = origin
        body.save()
        logger.info("More recent elements already stored for %s" % obj_id)
    # Update Physical Parameters
    if body.characterization_target() or body.source_type == 'C':
        update_jpl_phys_params(body)
        if body.source_type == 'C':
            # The MPC DB doesn't return any info for comets; update the Body's
            # `abs_mag` and `slope` values here if possible
            new_abs_mag = None
            try:
                new_abs_mag = PhysicalParameters.objects.get(body=body, parameter_type='M1', preferred=True).value
            except (PhysicalParameters.DoesNotExist, PhysicalParameters.MultipleObjectsReturned):
                new_abs_mag = None
            if new_abs_mag:
                msg = "Updated abs_mag for {} from M1={}".format(body.current_name(), new_abs_mag)
                logger.debug(msg)
                body.abs_mag = new_abs_mag

            new_slope = None
            try:
                new_slope = PhysicalParameters.objects.get(body=body, parameter_type='K1', preferred=True).value
            except (PhysicalParameters.DoesNotExist, PhysicalParameters.MultipleObjectsReturned):
                new_slope = None
            if new_slope:
                msg = "Updated slope for {} from K1={}".format(body.current_name(), new_slope)
                logger.debug(msg)
                body.slope = new_slope / 2.5
            body.save()
            # Build physparams dictionary to store reciprocal semi-major axis
            phys_params = {'parameter_type': '/a',
                           'value' : elements.get('recip semimajor axis orig', None),
                           'error' : elements.get('recip semimajor axis error', None),
                           'value2': elements.get('recip semimajor axis future', None),
                           'error2': elements.get('recip semimajor axis error', None),
                           'units': 'au',
                           'reference': elements.get('reference', None),
                           'preferred': True
                           }
            if phys_params['value'] is not None:
                saved = body.save_physical_parameters(phys_params)
                body.refresh_from_db()
                # Test to see if it's a DNC with a 1/a value < 1e-4 (10,000 AU)
                if body.recip_a and body.recip_a < 1e-4 and body.source_subtype_2 is None:
                    body.source_subtype_2 = 'DN'
                    body.save()

    return True


def update_jpl_phys_params(body):
    """Fetch physical parameters, names, and object type from JPL SB database and store in Neoexchange DB"""
    resp = fetch_jpl_physparams_altdes(body)

    try:
        store_jpl_physparams(resp['phys_par'], body)
        store_jpl_desigs(resp['object'], body)
        store_jpl_sourcetypes(resp['object']['orbit_class']['code'], resp['object'], body)
    except KeyError:
        if 'message' in resp.keys():
            logger.warning(resp['message'])
        else:
            logger.warning("Error getting physical parameters from JPL DB")


def ingest_new_object(orbit_file, obs_file=None, dbg=False):
    """Ingests a new object or updates an existing one from the <orbit_file>
    If the observation file, which defaults to <orbit_file> with the '.neocp'
    extension replaced by '.dat' but which can be specified by [obs_file] is
    also found, additional information such as discovery date will be created or
    updated.
    Returns the Body object that was created or retrieved, a boolean for whether
    the Body was created or not, and a message. In the case of errors,
    None, False, and the message are returned.
    """

    orblines = read_mpcorbit_file(orbit_file)

    if orblines is None:
        msg = "Could not read orbit file: " + orbit_file
        return None, False, msg

    if obs_file is None:
        obs_file = orbit_file.replace('neocp', 'dat')

    # If not found, try new-style obs file name
    if os.path.exists(obs_file) is False:
        obs_file = orbit_file.replace('.neocp', '_mpc.dat')

    local_discovery = False
    try:
        obsfile_fh = open(obs_file, 'r')
        obslines = obsfile_fh.readlines()
        obsfile_fh.close()
        for obsline in obslines:
            obs_params = parse_mpcobs(obsline)
            if obs_params.get('discovery', False) is True:
                break
        discovery_date = obs_params.get('obs_date', None)
        local_discovery = obs_params.get('lco_discovery', False)
    except IOError:
        logger.warning("Unable to find matching observation file (%s)" % obs_file)
        discovery_date = None

    dbg_msg = orblines[0]
    logger.debug(dbg_msg)
    kwargs = clean_NEOCP_object(orblines)
    if kwargs != {}:
        obj_file = os.path.basename(orbit_file)
        file_chunks = obj_file.split('.')
        name = None
        if len(file_chunks) == 2:
            obj_id = file_chunks[0].strip()
            if obj_id != kwargs['provisional_name']:
                msg = "Mismatch between filename (%s) and provisional id (%s).\nAssuming provisional id is a final designation." % (obj_id, kwargs['provisional_name'])
                logger.info(msg)
                try:
                    name = packed_to_normal(kwargs['provisional_name'])
                except PackedError:
                    name = None
                kwargs['name'] = name
                kwargs['provisional_packed'] = kwargs['provisional_name']
                if name is not None and obj_id.strip() == name.replace(' ', ''):
                    kwargs['provisional_name'] = None
                    kwargs['origin'] = 'M'
                else:
                    kwargs['provisional_name'] = obj_id
                # Determine perihelion distance and asteroid type
                if kwargs.get('eccentricity', None) is not None and kwargs.get('eccentricity', 2.0) < 1.0\
                        and kwargs.get('meandist', None) is not None:
                    perihdist = kwargs['meandist'] * (1.0 - kwargs['eccentricity'])
                    source_type = determine_asteroid_type(perihdist, kwargs['eccentricity'])
                    if dbg:
                        print("New source type", source_type)
                    kwargs['source_type'] = source_type
                if local_discovery:
                    if dbg:
                        print("Setting to local origin")
                    kwargs['origin'] = 'L'
                    kwargs['source_type'] = 'D'
        else:
            obj_id = kwargs['provisional_name']

        # Add in discovery date from the observation file
        kwargs['discovery_date'] = discovery_date
        # Needs to be __exact (and the correct database collation set on Body)
        # to perform case-sensitive lookup on the provisional name.
        if dbg:
            print("Looking in the DB for ", obj_id)
        query = Q(provisional_name__exact=obj_id)
        if name is not None:
            query |= Q(name__exact=name)
        bodies = Body.objects.filter(query)
        if bodies.count() == 0:
            body, created = Body.objects.get_or_create(provisional_name__exact=obj_id)
        elif bodies.count() == 1:
            body = bodies[0]
            created = False
        else:
            msg = "Multiple bodies found, aborting"
            logger.error(msg)
            return None, False, msg
        if not created:
            # Find out if the details have changed, if they have, save a
            # revision
            check_body = Body.objects.filter(**kwargs)
            if check_body.count() == 0:
                kwargs['updated'] = True
                if save_and_make_revision(body, kwargs):
                    msg = "Updated %s" % obj_id
                else:
                    msg = "No changes saved for %s" % obj_id
            else:
                msg = "No changes needed for %s" % obj_id
        else:
            save_and_make_revision(body, kwargs)
            msg = "Added new local target %s" % obj_id
    else:
        body = None
        created = False
        msg = "Unable to parse orbit line"

    return body, created, msg


def update_MPC_obs(obj_id_or_page):
    """
    Performs remote look up of observations for object with id obj_id_or_page,
    Gets or creates corresponding Body instance and updates or creates
    SourceMeasurements.
    Alternatively obj_id_or_page can be a BeautifulSoup object, in which case
    the call to fetch_mpcdb_page() will be skipped and the passed BeautifulSoup
    object will parsed.
    """
    obj_id = None
    if type(obj_id_or_page) != BeautifulSoup:
        obj_id = obj_id_or_page
        obslines = fetch_mpcobs(obj_id)

        if obslines is None:
            logger.warning("Could not find observations for %s" % obj_id)
            return False
    else:
        page = obj_id_or_page
        obslines = page.text.split('\n')

    if len(obslines) > 0:
        measures = create_source_measurement(obslines, None)
    else:
        measures = []
    return measures


def count_useful_obs(obs_lines):
    """Function to determine max number of obs_lines will be read """
    i = 0
    for obs_line in obs_lines:
        if len(obs_line) > 15 and obs_line[14] in ['C', 'S', 'A']:
            i += 1
    return i


def create_source_measurement(obs_lines, block=None):
    # initialize measures/obs_lines
    measures = []
    if type(obs_lines) != list:
        obs_lines = [obs_lines, ]

    useful_obs = count_useful_obs(obs_lines)

    # find an obs_body for the mpc data
    obs_body = None
    for obs_line in reversed(obs_lines):
        param = parse_mpcobs(obs_line)
        if param:
            # Try to unpack the name first
            try:
                try:
                    unpacked_name = packed_to_normal(param['body'])
                except PackedError:
                    try:
                        unpacked_name = str(int(param['body']))
                    except ValueError:
                        unpacked_name = 'ZZZZZZ'
                obs_body = Body.objects.get(Q(provisional_name__startswith=param['body']) |
                                            Q(name=param['body']) |
                                            Q(name=unpacked_name) |
                                            Q(provisional_name=unpacked_name)
                                           )
            except Body.DoesNotExist:
                logger.debug("Body %s does not exist" % param['body'])
                # if no body is found, remove obsline
                obs_lines.remove(obs_line)
            except Body.MultipleObjectsReturned:
                logger.warning("Multiple versions of Body %s exist" % param['body'])
            # when a body is found, exit loop
            if obs_body is not None:
                break

    if obs_body:
        # initialize DB products
        frame_list = Frame.objects.filter(sourcemeasurement__body=obs_body)
        source_list = SourceMeasurement.objects.filter(body=obs_body).prefetch_related('frame')
        block_list = Block.objects.filter(body=obs_body)
        measure_count = len(source_list)

        for obs_line in reversed(obs_lines):
            # End loop when measurements are in the DB for all MPC lines
            logger.info('Previously recorded {} of {} total MPC obs'.format(measure_count, useful_obs))
            if measure_count >= useful_obs:
                break
            frame = None
            logger.debug(obs_line.rstrip())
            params = parse_mpcobs(obs_line)
            if params:
                # Check name is still the same as obs_body
                try:
                    unpacked_name = packed_to_normal(params['body'])
                except PackedError:
                    try:
                        unpacked_name = str(int(params['body']))
                    except ValueError:
                        unpacked_name = 'ZZZZZZ'
                # if new name, reset obs_body
                if params['body'] != obs_body.name and unpacked_name != obs_body.provisional_name and unpacked_name != obs_body.name and params['body'] != obs_body.provisional_name:
                    try:
                        try:
                            unpacked_name = packed_to_normal(params['body'])
                        except PackedError:
                            try:
                                unpacked_name = str(int(params['body']))
                            except ValueError:
                                unpacked_name = 'ZZZZZZ'
                        obs_body = Body.objects.get(Q(provisional_name__startswith=params['body']) |
                                                    Q(name=params['body']) |
                                                    Q(name=unpacked_name)
                                                   )
                    except Body.DoesNotExist:
                        logger.debug("Body %s does not exist" % params['body'])
                        continue
                    except Body.MultipleObjectsReturned:
                        logger.warning("Multiple versions of Body %s exist" % params['body'])
                        continue
                # Identify block
                if not block:
                    if block_list:
                        blocks = [blk for blk in block_list if blk.block_start <= params['obs_date'] <= blk.block_end]
                        if blocks:
                            logger.info("Found %s blocks for %s" % (len(blocks), obs_body))
                            block = blocks[0]
                        else:
                            logger.debug("No blocks for %s, presumably non-LCO data" % obs_body)
                if params['obs_type'] == 's':
                    # If we have an obs_type of 's', then we have one line
                    # of a satellite measurement and we need to find the matching
                    # Frame we created on the previous line read and update its
                    # extrainfo field.
                    # Otherwise, make a new Frame and SourceMeasurement
                    if frame_list:
                        frame = next((frm for frm in frame_list if frm.sitecode == params['site_code'] and
                                                                    params['obs_date'] == frm.midpoint and
                                                                    frm.frametype == Frame.SATELLITE_FRAMETYPE), None)
                    if not frame_list or not frame:
                        try:
                            prior_frame = Frame.objects.get(frametype=Frame.SATELLITE_FRAMETYPE,
                                                            midpoint=params['obs_date'],
                                                            sitecode=params['site_code'])
                            if prior_frame.extrainfo != params['extrainfo']:
                                prior_frame.extrainfo = params['extrainfo']
                                prior_frame.save()
                        except Frame.DoesNotExist:
                            logger.warning("Matching satellite frame for %s from %s on %s does not exist" % (params['body'], params['obs_date'], params['site_code']))
                            frame = create_frame(params, block)
                            frame.extrainfo = params['extrainfo']
                            frame.save()
                        except Frame.MultipleObjectsReturned:
                            logger.warning("Multiple matching satellite frames for %s from %s on %s found" % (params['body'], params['obs_date'], params['site_code']))
                            continue
                else:
                    if params['obs_type'] == 'S':
                        # If we have an obs_type of 'S', then we have one line
                        # of a satellite measurement and we need to find the matching
                        # Frame we created on the previous line read and update its
                        # filter field.
                        # Otherwise, make a new Frame and SourceMeasurement
                        if frame_list:
                            frame = next((frm for frm in frame_list if frm.sitecode == params['site_code'] and
                                                                        params['obs_date'] == frm.midpoint and
                                                                        frm.frametype == Frame.SATELLITE_FRAMETYPE), None)
                        if not frame_list or not frame:
                            try:
                                frame = Frame.objects.get(frametype=Frame.SATELLITE_FRAMETYPE,
                                                                midpoint=params['obs_date'],
                                                                sitecode=params['site_code'])
                                if frame.filter != params['filter']:
                                    frame.filter = params['filter']
                                    frame.save()
                            except Frame.DoesNotExist:
                                frame = create_frame(params, block)
                            except Frame.MultipleObjectsReturned:
                                logger.warning("Multiple matching satellite frames for %s from %s on %s found" % (params['body'], params['obs_date'], params['site_code']))
                                continue
                    else:
                        # If no satellites, check for existing frames, and create new ones
                        if frame_list:
                            frame = next((frm for frm in frame_list if frm.sitecode == params['site_code'] and params['obs_date'] == frm.midpoint), None)
                            if not frame:
                                frame = create_frame(params, block)
                        else:
                            frame = create_frame(params, block)
                    if frame:
                        measure_params = {  'body'    : obs_body,
                                            'frame'   : frame,
                                            'obs_ra'  : params['obs_ra'],
                                            'obs_dec' : params['obs_dec'],
                                            'obs_mag' : params['obs_mag'],
                                            'flags'   : params['flags'],
                                            'astrometric_catalog': params['astrometric_catalog'],
                                         }
                        if source_list and next((src for src in source_list if src.frame == measure_params['frame']), None):
                            measure_created = False
                            measure = None
                        else:
                            measure, measure_created = SourceMeasurement.objects.get_or_create(**measure_params)
                        if measure_created:
                            measures.append(measure)
                            measure_count += 1

        # Set updated to True for the target with the current datetime
        update_params = { 'updated' : True,
                          'update_time' : datetime.utcnow()
                        }
        updated = save_and_make_revision(obs_body, update_params)
        logger.info("Updated %d MPC Observations for Body #%d (%s)" % (len(measures), obs_body.pk, obs_body.current_name()))

    # Reverse and return measures.
    measures = [m for m in reversed(measures)]
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


def find_spec(pk):
    """find directory of spectra for a certain block
    NOTE: Currently will only pull first spectrum of a superblock
    """
    try:
        block = Block.objects.get(pk=pk)
        url = settings.ARCHIVE_FRAMES_URL+str(Frame.objects.filter(block=block)[0].frameid)+'/headers'
    except IndexError:
        return '', '', '', '', ''
    try:
        data = lco_api_call(url)['data']
    except TypeError:
        return '', '', '', '', ''
    if 'DAY_OBS' in data:
        date_obs = data['DAY_OBS']
    elif 'DAY-OBS' in data:
        date_obs = data['DAY-OBS']
    else:
        date_obs = str(int(block.block_start.strftime('%Y%m%d'))-1)

    obj = sanitize_object_name(data['OBJECT'])

    if 'REQNUM' in data:
        req = data['REQNUM'].lstrip("0")
    else:
        req = block.request_number
    path = os.path.join(date_obs, obj + '_' + req)
    prop = block.superblock.proposal.code

    return date_obs, obj, req, path, prop


def find_analog(date_obs, site):
    """Search for Calib Source blocks taken 10 days before or after a given date at a specific site.
    Return a list of reduced fits files in order of temporal distance from given date."""

    if date_obs is None:
        logger.warning("Attempt to find analogs for unobserved Block")
        return []

    analog_blocks = Block.objects.filter(obstype=Block.OPT_SPECTRA_CALIB, site=site, when_observed__lte=date_obs+timedelta(days=10), when_observed__gte=date_obs-timedelta(days=10))
    star_list = []
    time_diff = []
    for b in analog_blocks:
        d_out, obj, req, path, prop = find_spec(b.id)
        filenames = search(path, matchpattern='.*_2df_ex.fits', latest=False)
        if filenames is False:
            continue
        filenames = [os.path.join(path, f) for f in filenames]
        for fn in filenames:
            star_list.append(fn)
            time_diff.append(abs(date_obs - b.when_observed))

    analog_list = [calib for _, calib in sorted(zip(time_diff, star_list))]

    return analog_list


def plot_all_spec(source):
    """Plot all non-FLOYDS data for given source.
        Currently only checks if source is StaticSource or PreviousSpectra instance.
    """

    data_spec = []
    p_spec = []
    if isinstance(source, StaticSource):
        calibsource = source
        base_dir = os.path.join('cdbs', 'ctiostan')  # new base_dir for method

        obj = sanitize_object_name(calibsource.name.lower())
        spec_file = os.path.join(base_dir, "f{}.dat".format(obj))
        wav, flux, err = pull_data_from_text(spec_file)
        if wav:
            label = calibsource.name
            new_spec = {'label': label,
                        'spec': flux,
                        'wav': wav,
                        'err': err,
                        'filename': spec_file}
            data_spec.append(new_spec)
            script, div = spec_plot(data_spec, {}, reflec=False)
        else:
            logger.warning("No flux file found for " + spec_file)
            script = ''
            div = {"raw_spec": ''}

    else:
        body = source
        p_spec = PreviousSpectra.objects.filter(body=body)
        for spec in p_spec:
            if spec.spec_ir:
                wav, flux, err = pull_data_from_text(spec.spec_ir)
                label = "{} -- {}, {}(IR)".format(body.current_name(), spec.spec_date, spec.spec_source)
                new_spec = {'label': label,
                     'spec': flux,
                     'wav': wav,
                     'err': err,
                     'filename': spec.spec_ir}
                data_spec.append(new_spec)
            if spec.spec_vis:
                wav, flux, err = pull_data_from_text(spec.spec_vis)
                label = "{} -- {}, {}(Vis)".format(body.current_name(), spec.spec_date, spec.spec_ref)
                new_spec = {'label': label,
                     'spec': flux,
                     'wav': wav,
                     'err': err,
                     'filename': spec.spec_vis}
                data_spec.append(new_spec)

        if data_spec:
            script, div = spec_plot(data_spec, {}, reflec=True)
        else:
            script = div = None

    return script, div, p_spec


def plot_floyds_spec(block, obs_num=1):
    """Get plots for requested blocks of FLOYDs data and subtract nearest solar analog."""

    date_obs, obj, req, path, prop = find_spec(block.id)
    filenames = search(path, matchpattern='.*_2df_ex.fits', latest=False)
    if filenames is False:
        return '', {"raw_spec": ''}
    filenames = [os.path.join(path, f) for f in filenames]

    analogs = find_analog(block.when_observed, block.site)

    try:
        raw_label, raw_spec, ast_wav = spectrum_plot(filenames[obs_num-1])
        data_spec = {'label': raw_label,
                     'spec': raw_spec,
                     'wav': ast_wav,
                     'filename': filenames[obs_num-1]}
    except IndexError:
        data_spec = None

    analog_data = []
    offset = 0
    for analog in analogs:
        offset += 2
        analog_label, analog_spec, star_wav = spectrum_plot(analog, offset=offset)
        analog_data.append({'label': analog_label,
                       'spec': analog_spec,
                       'wav': star_wav,
                       'filename': analog})

    script, div = spec_plot([data_spec], analog_data)

    return script, div


class BlockSpec(View):  # make logging required later

    template_name = 'core/plot_spec.html'

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        script, div = plot_floyds_spec(block, int(kwargs['obs_num']))
        params = {'pk': kwargs['pk'], 'obs_num': kwargs['obs_num'], 'sb_id': block.superblock.id}
        if div:
            params["the_script"] = script
            params["raw_div"] = div["raw_spec"]
            if 'reflec_spec' in div:
                params["reflec_div"] = div["reflec_spec"]
        base_path = BOKEH_URL.format(bokeh.__version__)
        params['css_path'] = base_path + 'css'
        params['js_path'] = base_path + 'js'
        return render(request, self.template_name, params)


class PlotSpec(View):

    template_name = 'core/plot_spec.html'

    def get(self, request, *args, **kwargs):
        body = Body.objects.get(pk=kwargs['pk'])
        script, div, p_spec = plot_all_spec(body)
        params = {'body': body, 'floyds': False}
        if div:
            params["the_script"] = script
            params["reflec_div"] = div["reflec_spec"]
            params["p_spec"] = p_spec
        base_path = BOKEH_URL.format(bokeh.__version__)
        params['css_path'] = base_path + 'css'
        params['js_path'] = base_path + 'js'

        return render(request, self.template_name, params)


def display_movie(request, pk):
    """Display previously made guide movie, or make one if no movie found."""

    date_obs, obj, req, path, prop = find_spec(pk)
    base_dir = os.path.join(path, 'Guide_frames')
    logger.info('ID: {}, BODY: {}, DATE: {}, REQNUM: {}, PROP: {}'.format(pk, obj, date_obs, req, prop))
    logger.debug('DIR: {}'.format(path))  # where it thinks an unpacked tar is at

    movie_file = "{}_{}_guidemovie.gif".format(obj, req)

    movie_file = search(base_dir, movie_file, latest=True)

    if movie_file:
        logger.debug('MOVIE FILE: {}'.format(movie_file))
        movie = default_storage.open(movie_file, 'rb').read()
        return HttpResponse(movie, content_type="Image/gif")
    else:
        return HttpResponse()


class GuideMovie(View):
    # make logging required later

    template_name = 'core/guide_movie.html'

    def get(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        params = {'pk': kwargs['pk'], 'sb_id': block.superblock.id}

        return render(request, self.template_name, params)


def update_taxonomy(body, tax_table, dbg=False):
    """Update taxonomy for given body based on passed taxonomy table.
    tax_table should be a 5 element list and have the format of
    [body_name, taxonomic_class, tax_scheme, tax_reference, tax_notes]
    where:
    body_name       := number or provisional designation
    taxonomic_class := string <= 6 characters (X, Sq, etc.)
    tax_scheme      := 2 character string (T, Ba, Td, H, S, B, 3T, 3B, BD)
    tax_reference   := Source of taxonomic data
    tax_notes       := other information/details
    """

    name = [body.current_name(), body.name, body.provisional_name]
    taxonomies = [tax for tax in tax_table if tax[0].rstrip() in name]
    if not taxonomies:
        if dbg is True:
            print("No taxonomy for %s" % body.current_name())
        return False
    else:
        c = 0
        for taxobj in taxonomies:
            check_tax = SpectralInfo.objects.filter(body=body, taxonomic_class=taxobj[1], tax_scheme=taxobj[2], tax_reference=taxobj[3], tax_notes=taxobj[4])
            if check_tax.count() == 0:
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
                else:
                    c += 1
            elif dbg is True:
                print("Data already in DB")
        return c


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
    body_char = get_characterization_targets()
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


def create_calib_sources(calib_sources, cal_type=StaticSource.FLUX_STANDARD):
    """Creates StaticSources from the passed dictionary of <calib_sources>. This
    would normally come from fetch_flux_standards() but other sources are possible.
    The number of sources created is returned"""

    num_created = 0

    for standard in calib_sources:

        params = {
                    'name' : standard,
                    'ra'  : degrees(calib_sources[standard]['ra_rad']),
                    'dec' : degrees(calib_sources[standard]['dec_rad']),
                    'vmag' : calib_sources[standard]['mag'],
                    'spectral_type' : calib_sources[standard].get('spectral_type', ''),
                    'source_type' : cal_type,
                    'notes' : calib_sources[standard].get('notes', '')
                 }
        calib_source, created = StaticSource.objects.get_or_create(**params)
        if created:
            num_created += 1
    return num_created


def find_best_flux_standard(sitecode, utc_date=None, flux_standards=None, debug=False):
    """Finds the "best" flux standard (closest to the zenith at the middle of
    the night (given by [utc_date]; defaults to UTC "now") for the passed <sitecode>
    [flux_standards] is expected to be a dictionary of standards with the keys as the
    name of the standards and pointing to a dictionary with the details. This is
    normally produced by sources_subs.fetch_flux_standards(); which will be
    called if standards=None
    """
    if utc_date is None:
        utc_date = datetime.utcnow()
    close_standard = None
    close_params = {}
    if flux_standards is None:
        flux_standards = StaticSource.objects.filter(source_type=StaticSource.FLUX_STANDARD)

    site_name, site_long, site_lat, site_hgt = get_sitepos(sitecode)
    if site_name != '?':

        # Compute midpoint of the night
        dark_start, dark_end = determine_darkness_times(sitecode, utc_date)

        dark_midpoint = dark_start + (dark_end - dark_start) / 2.0

        if debug:
            print("\nDark midpoint, start, end", dark_midpoint, dark_start, dark_end)

        # Compute Local Sidereal Time at the dark midpoint
        stl = datetime2st(dark_midpoint, site_long)

        if debug:
            print("RA, Dec of zenith@midpoint:", stl, site_lat)
        # Loop through list of standards, recording closest
        min_sep = 360.0
        for standard in flux_standards:
            sep = S.sla_dsep(radians(standard.ra), radians(standard.dec), stl, site_lat)
            if debug:
                print("%10s %.7f %.7f %.3f %7.3f (%10s)" % (standard, standard.ra, standard.dec, sep, min_sep, close_standard))
            if sep < min_sep:
                min_sep = sep
                close_standard = standard
        close_params = model_to_dict(close_standard)
        close_params['separation_rad'] = min_sep
    return close_standard, close_params


def find_best_solar_analog(ra_rad, dec_rad, site, ha_sep=4.0, solar_standards=None, debug=False):
    """Finds the "best" solar analog (closest to the passed RA, Dec (in radians,
    from e.g. compute_ephem)) within [ha_sep] hours (defaults to 4 hours
    of HA) that can be seen from the appropriate site.
    If a match is found, the StaticSource object is returned along with a
    dictionary of parameters, including the additional 'seperation_deg' with the
    minimum separation found (in degrees)"""

    close_standard = None
    close_params = {}
    if solar_standards is None:
        solar_standards = StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD)

    if site == 'E10':
        dec_lim = [-90.0, 20.0]
    elif site == 'F65':
        dec_lim = [-20.0, 90.0]
    else:
        dec_lim = [-20.0, 20.0]

    min_sep = None
    for standard in solar_standards:
        ra_diff = abs(standard.ra - degrees(ra_rad)) / 15
        sep = degrees(S.sla_dsep(radians(standard.ra), radians(standard.dec), ra_rad, dec_rad))
        if debug:
            print("%10s %1d %011.7f %+11.7f %7.3f %7.3f (%10s)" % (standard.name.replace("Landolt ", "") , standard.source_type, standard.ra, standard.dec, sep, ha_sep, close_standard))
        if ra_diff < ha_sep and (dec_lim[0] <= standard.dec <= dec_lim[1]):
            if min_sep is None or sep < min_sep:
                min_sep = sep
                close_standard = standard
    if close_standard is not None:
        close_params = model_to_dict(close_standard)
        close_params['separation_deg'] = min_sep
    return close_standard, close_params
