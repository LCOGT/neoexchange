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
from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles import views
from django.contrib import admin
from django.views.generic import ListView, DetailView
from ingest.models import Body, Block
from ingest.views import BodySearchView,BodyDetailView, ScheduleParameters, ScheduleConfirm, ephemeris, home

admin.autodiscover()

urlpatterns = [
    url(r'^$', home, name='home'),
    url(r'^block/list/$', ListView.as_view(model=Block, queryset=Block.objects.filter(active=True).order_by('-block_start'), context_object_name="block_list"), name='blocklist'),
    url(r'^target/$', ListView.as_view(model=Body, queryset=Body.objects.filter(active=True).order_by('-origin','-ingest'), context_object_name="target_list"), name='targetlist'),
    url(r'^target/(?P<pk>\d+)/$',BodyDetailView.as_view(model=Body), name='target'),
    url(r'^search/$', BodySearchView.as_view(context_object_name="target_list"), name='search'),
    url(r'^ephemeris/$', ephemeris, name='ephemeris'),
    url(r'^schedule/(?P<pk>\d+)/confirm/$',ScheduleConfirm.as_view(), name='schedule-confirm'),
    url(r'^schedule/(?P<pk>\d+)/$', ScheduleParameters.as_view(), name='schedule-body'),
    # url(r'^schedule/success/$',ScheduleSuccess.as_view(), name='schedule-success'),
    # url(r'^schedule/$', SchedFormDisplay.as_view(), name='schedule'),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', views.serve),
    ]