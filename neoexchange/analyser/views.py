'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2017 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import DetailView, ListView, FormView, TemplateView, View
from django.http import Http404, HttpResponse, HttpResponseServerError, HttpResponseRedirect

from core.models import Frame, Block, Candidate, SourceMeasurement
from core.frames import find_images_for_block
from core.views import generate_new_candidate

import logging

logger = logging.getLogger(__name__)

class BlockFramesView(DetailView):
    template_name = 'analyser/lightmonitor.html'
    model = Block

    def get_context_data(self, **kwargs):
        img_list = []
        context = super(BlockFramesView, self).get_context_data(**kwargs)
        images = find_images_for_block(context['block'].id)
        analysed = check_for_source_measurements(context['block'].id)
        if images:
            context['images'] = images[0]
            context['candidates'] = images[1]
            context['xaxis'] = images[2]
            context['yaxis'] = images[3]
            context['analysed'] = analysed
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        if context.get('images', False):
            return self.render_to_response(context)
        else:
            messages.error(request, 'There are no frame IDs for Block {}'.format(self.object.pk))
            return HttpResponseRedirect(reverse('block-view', kwargs={'pk':kwargs['pk']}))


class ProcessCandidates(View):

    def post(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        cand_ids = request.POST.getlist('objects[]','')
        blockcandidate = request.POST.get('blockcandidate','')
        resp = analyser_to_source_measurement(block, cand_ids, blockcandidate)
        if resp:
            return HttpResponse("ok", content_type="text/plain")
        else:
            return HttpResponseServerError("There was a problem", content_type="text/plain")

def analyser_to_source_measurement(block, cand_ids, blockcandidate):

    red_frames = Frame.objects.filter(block=block, frameid__isnull=False, frametype=Frame.BANZAI_RED_FRAMETYPE).order_by('midpoint')
    ql_frames = Frame.objects.filter(block=block, frameid__isnull=False, frametype=Frame.BANZAI_QL_FRAMETYPE).order_by('midpoint')
    if red_frames.count() >= ql_frames.count():
        frames = red_frames
    else:
        frames = ql_frames
    if not frames:
        return False
    for cand_id in cand_ids:
        cand = Candidate.objects.get(id=cand_id)
        # If this candidate (cand_id) is the intended target of the Block, use
        # that. Otherwise generate a new Body/asteroid candidate
        discovery = False
        if str(cand_id) == str(blockcandidate):
            body = block.body
        else:
            body = generate_new_candidate(frames)
            discovery = True
        if not body:
            return False
        detections = cand.unpack_dets()
        if len(detections) != frames.count():
            return False
        for det in detections:
            frame = frames[int(det[1])-1]
            params = {
                'body'  : body,
                'frame' : frame
            }
            sm, created = SourceMeasurement.objects.get_or_create(**params)
            # Convert the detections RA's (in decimal hours) into decimal degrees
            # before storing
            sm.obs_ra = det[4] * 15.0
            sm.obs_dec = det[5]
            sm.obs_mag = det[8]
            sm.aperture_size = det[14]
            if discovery:
                # Add discovery asterisk to the first detection
                sm.flags = '*'
                discovery = False
            sm.save()
    return True

def check_for_source_measurements(blockid):
    sources = SourceMeasurement.objects.filter(frame__block__id=blockid)
    if sources.count() > 0:
        return True
    else:
        return False
