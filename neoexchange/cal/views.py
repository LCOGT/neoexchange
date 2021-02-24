from datetime import datetime
from calendar import monthrange
import logging

from django.views.generic import View
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.urls import reverse

from astrometrics.sources_subs import fetch_goldstone_targets
from core.models import SuperBlock, Block
from cal.models import CalEvent

logger = logging.getLogger(__name__)

# Classes for the various calendars that return lists of dicts that the FullCalendar
# uses as `Event Object`s (see https://fullcalendar.io/docs/event-object). Currently
# only 'title', 'start', 'end' and 'url' are populated.

class NeoxEvents(View):
    def get(self, request, *args, **kwargs):
        start = request.GET.get('start',None)
        end = request.GET.get('end', None)
        if not start and not end:
            start = datetime.today().replace(day=1)
            mr = monthrange(start.year, start.month)
            end = start.replace(day=mr[1])
        else:
            start = start[0:19]
            end = end[0:19]
        blocks = Block.objects.filter(block_start__gte=start, block_end__lte=end).order_by('-block_start')
        targets = [{'title':d.current_name(), 'start' : d.block_start, 'end' : d.block_end ,'url':reverse('block-view', kwargs={'pk':d.superblock.id})}  for d in blocks]
        return JsonResponse(targets, safe=False)

class CalEvents(View):
    def get(self, request, *args, **kwargs):
        start = request.GET.get('start',None)
        end = request.GET.get('end', None)
        if not start and not end:
            start = datetime.today().replace(day=1)
            mr = monthrange(start.year, start.month)
            end = start.replace(day=mr[1])
        else:
            start = start[0:19]
            end = end[0:19]
        events = CalEvent.objects.filter(start__gte=start, end__lte=end).order_by('-start')
        targets = [{'title':d.resource, 'start' : d.start, 'end' : d.end, 'url' : reverse('api:cal_events-detail', kwargs={'pk':d.id})} for d in events]
        return JsonResponse(targets, safe=False)

def goldstone_events(request):
    data = fetch_goldstone_targets(calendar_format=True)
    targets = []
    for d in data:
        target = {'title': d['target'], 'start' : d['windows'][0]['start'], 'end' : d['windows'][0]['end']}
        targets.append(target)
    return JsonResponse(targets, safe=False)
