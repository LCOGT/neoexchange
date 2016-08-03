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

from core.models import Frame, Block, Proposal, SourceMeasurement
from core.frames import block_status, frame_params_from_block, frame_params_from_log, \
    ingest_frames, create_frame, check_for_images, check_request_status, fetch_observations

import logging
import reversion
import json
import requests
from urlparse import urljoin
from django.conf import settings

logger = logging.getLogger(__name__)

class BlockFramesView(DetailView):
    template_name = 'astrometer/lightmonitor.html'
    model = Block

    def get_context_data(self, **kwargs):
        img_list = []
        context = super(BlockFramesView, self).get_context_data(**kwargs)
        images = fetch_observations(context['block'].tracking_number)
        if images:
            for img in images:
                img_dict = {'img'     : img,
                            'sources' : [{'x':100,'y':100},{'x':200,'y':200},{'x':300,'y':300}],
                            'targets' :  [{'x':150,'y':150}]
                            }
                img_list.append(img_dict)
        context['images'] = img_list
        return context

def fitsanalyse(request):
    return True
