from django.views.generic import View
from django.shortcuts import render
from django.http import JsonResponse, Http404

from astrometrics.sources_subs import fetch_arecibo_calendar_targets

def arecibo_events(request):
    data = fetch_arecibo_calendar_targets()
    return JsonResponse(data, safe=False)
