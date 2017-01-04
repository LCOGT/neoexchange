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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import DetailView, ListView, FormView, TemplateView, View
from django.http import Http404, HttpResponse, HttpResponseServerError

from core.models import Frame, Block, Candidate, SourceMeasurement
from core.frames import find_images_for_block

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

class ProcessCandidates(View):

    def post(self, request, *args, **kwargs):
        block = Block.objects.get(pk=kwargs['pk'])
        cand_ids = request.POST.getlist('objects[]','')
        resp = analyser_to_source_measurement(block, cand_ids)
        if resp:
            return HttpResponse("ok", content_type="text/plain")
        else:
            return HttpResponseServerError("There was a problem", content_type="text/plain")

def analyser_to_source_measurement(block, cand_ids):
    body = block.body
    frames = Frame.objects.filter(block=block, frameid__isnull=False).order_by('midpoint')
    if not frames:
        return False
    for cand_id in cand_ids:
        cand = Candidate.objects.get(block=block, cand_id=cand_id)
        detections = cand.unpack_dets()
        if len(detections) != frames.count():
            return False
        for det in detections:
            frame = frames[int(det[1])-1]
            params = {
                'body' :body,
                'frame' : frame
            }
            sm, created = SourceMeasurement.objects.get_or_create(**params)
            sm.obs_ra = det[4]
            sm.obs_dec = det[5]
            sm.obs_mag = det[8]
            sm.aperture_size = det[14]
            sm.save()
    return True

def check_for_source_measurements(blockid):
    sources = SourceMeasurement.objects.filter(frame__block__id=blockid)
    if sources.count() > 0:
        return True
    else:
        return False
