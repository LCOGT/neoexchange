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
from django.core.urlresolvers import reverse_lazy
from core.models import Body, Block, SourceMeasurement
from core.views import BodySearchView, BodyDetailView, BlockDetailView, ScheduleParameters, \
    ScheduleSubmit, ephemeris, home, BlockReport, ranking, MeasurementView, UploadReport, ViewMPCReport, \
    BlockListView
from django.contrib.auth.views import login, logout

admin.autodiscover()

urlpatterns = [
    url(r'^$', home, name='home'),
    url(r'^block/list/$', BlockListView.as_view(), name='blocklist'),
    url(r'^block/report/(?P<pk>\d+)/$',BlockReport.as_view(), name='report-block'),
    url(r'^block/(?P<pk>\d+)/upload/$',UploadReport.as_view(), name='upload-report'),
    url(r'^block/(?P<pk>\d+)/mpc/$',ViewMPCReport.as_view(), name='view-report'),
    url(r'^block/(?P<pk>\d+)/$',BlockDetailView.as_view(model=Block), name='block-view'),
    url(r'^target/$', ListView.as_view(model=Body, queryset=Body.objects.filter(active=True).order_by('-origin','-ingest'), context_object_name="target_list"), name='targetlist'),
    url(r'^target/(?P<pk>\d+)/$',BodyDetailView.as_view(model=Body), name='target'),
    url(r'^search/$', BodySearchView.as_view(context_object_name="target_list"), name='search'),
    url(r'^ephemeris/$', ephemeris, name='ephemeris'),
    url(r'^ranking/$', ranking, name='ranking'),
    url(r'^measurement/(?P<pk>\d+)/$', MeasurementView.as_view(), name='measurement'),
    url(r'^schedule/(?P<pk>\d+)/confirm/$',ScheduleSubmit.as_view(), name='schedule-confirm'),
    url(r'^schedule/(?P<pk>\d+)/$', ScheduleParameters.as_view(), name='schedule-body'),
    url(r'^accounts/login/$', login, {'template_name': 'core/login.html'}, name='auth_login'),
    url(r'^accounts/logout/$', logout, {'template_name': 'core/logout.html'}, name='auth_logout' ),
    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', views.serve),
    ]
