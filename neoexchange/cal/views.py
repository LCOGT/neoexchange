from datetime import datetime
from calendar import monthrange
import logging

from django.views.generic import View
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.urls import reverse

from astrometrics.sources_subs import fetch_arecibo_calendar_targets
from core.models import SuperBlock, Block

logger = logging.getLogger(__name__)

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

def arecibo_events(request):
    data = fetch_arecibo_calendar_targets()
    targets = []
    for d in data:
        target = {'title': d['target'], 'start' : d['windows'][0]['start'], 'end' : d['windows'][0]['end']}
        if d.get('extrainfo', None):
            # See if uncertainty is greater than Arecibo beam width (~2 arcmin)
            # If so, set border colo(u)r to red
            if d['extrainfo'].get('uncertainty', 0) >= 120:
                target['borderColor'] = 'red'
        targets.append(target)
    return JsonResponse(targets, safe=False)
