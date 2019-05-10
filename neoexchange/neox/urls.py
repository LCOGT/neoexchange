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
from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles import views
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.views.generic import ListView, DetailView
from django.core.urlresolvers import reverse_lazy

from core.models import Body, Block, SourceMeasurement, SuperBlock, StaticSource
from core.views import BodySearchView, BodyDetailView, BlockDetailView, BlockListView, ScheduleParameters, \
    ScheduleSubmit, ephemeris, home, BlockReport, ranking, MeasurementViewBody, MeasurementViewBlock, \
    UploadReport, BlockTimeSummary, ScheduleParametersCadence, ScheduleParametersSpectra, \
    plotframe, make_plot, CandidatesViewBlock, BlockReportMPC, \
    MeasurementDownloadMPC, MeasurementDownloadADESPSV, \
    SuperBlockListView, SuperBlockDetailView, characterization, SpectroFeasibility, \
    display_spec, display_calibspec, PlotSpec, display_movie, GuideMovie, \
    StaticSourceView, StaticSourceDetailView, ScheduleCalibSpectra, ScheduleCalibSubmit, \
    make_standards_plot, make_solar_standards_plot, CalibSpectroFeasibility, ScheduleCalibParameters

from analyser.views import BlockFramesView, ProcessCandidates


admin.autodiscover()

urlpatterns = [
    url(r'^$', home, name='home'),
    url(r'^makeplot/$', make_plot, name='makeplot'),
    url(r'^plotframe/$', plotframe),
    url(r'^make-standards-plot/$', make_standards_plot, name='make-standards-plot'),
    url(r'^make-solar-standards-plot/$', make_solar_standards_plot, name='make-solar-standards-plot'),
    url(r'^block/summary/$', BlockTimeSummary.as_view(), name='block-summary'),
    url(r'^block/list/$', SuperBlockListView.as_view(model=SuperBlock, queryset=SuperBlock.objects.order_by('-block_start'), context_object_name="block_list"), name='blocklist'),
    url(r'^block/(?P<pk>\d+)/spectra/(?P<obs_num>\d+)/spectra.png$', display_spec, name='display_spec'),
    url(r'^block/(?P<pk>\d+)/spectra/(?P<obs_num>\d+)/$', PlotSpec.as_view(), name='plotspec'),
    url(r'^block/(?P<pk>\d+)/guidemovie/$', GuideMovie.as_view(), name='guidemovie'),
    url(r'^block/(?P<pk>\d+)/spectra/guidemovie.gif$', display_movie, name='display_movie'),
    url(r'^block/(?P<pk>\d+)/source/(?P<source>\d+)/report/submit/$', BlockReportMPC.as_view(), name='block-submit-mpc'),
    url(r'^block/(?P<pk>\d+)/report/$', BlockReport.as_view(), name='report-block'),
    url(r'^block/(?P<pk>\d+)/upload/$', UploadReport.as_view(), name='upload-report'),
    url(r'^block/(?P<pk>\d+)/measurements/mpc/$', MeasurementViewBlock.as_view(template='core/mpcreport.html'), name='block-report-mpc'),
    url(r'^block/(?P<pk>\d+)/measurements/$', MeasurementViewBlock.as_view(), name='block-report'),
    url(r'^block/(?P<pk>\d+)/analyser/$', BlockFramesView.as_view(), name='block-ast'),
    url(r'^block/(?P<pk>\d+)/analyser/submit/$', ProcessCandidates.as_view(), name='submit-candidates'),
    url(r'^block/(?P<pk>\d+)/candidates/$', CandidatesViewBlock.as_view(), name='view-candidates'),
    url(r'^block/(?P<pk>\d+)/$', SuperBlockDetailView.as_view(model=SuperBlock), name='block-view'),
    url(r'^target/$', ListView.as_view(model=Body, queryset=Body.objects.filter(active=True).order_by('-origin', '-ingest'), context_object_name="target_list"), name='targetlist'),
    url(r'^target/(?P<pk>\d+)/measurements/ades/download/$', MeasurementDownloadADESPSV.as_view(), name='download-ades'),
    url(r'^target/(?P<pk>\d+)/measurements/mpc/download/$', MeasurementDownloadMPC.as_view(), name='download-mpc'),
    url(r'^target/(?P<pk>\d+)/measurements/ades/$', MeasurementViewBody.as_view(template='core/adesreport.html'), name='measurement-ades'),
    url(r'^target/(?P<pk>\d+)/measurements/mpc/$', MeasurementViewBody.as_view(template='core/mpcreport.html'), name='measurement-mpc'),
    url(r'^target/(?P<pk>\d+)/measurements/$', MeasurementViewBody.as_view(), name='measurement'),
    url(r'^target/(?P<pk>\d+)/$', BodyDetailView.as_view(model=Body), name='target'),
    url(r'^search/$', BodySearchView.as_view(context_object_name="target_list"), name='search'),
    url(r'^ephemeris/$', ephemeris, name='ephemeris'),
    url(r'^ranking/$', ranking, name='ranking'),
    url(r'^calibsources/$', StaticSourceView.as_view(), name='calibsource-view'),
    url(r'^calibsources/solar/$', StaticSourceView.as_view(queryset=StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD).order_by('ra')), name='solarstandard-view'),
    url(r'^calibsources/(?P<pk>\d+)/$', StaticSourceDetailView.as_view(model=StaticSource), name='calibsource'),
    url(r'^calibsources/(?P<pk>\d+)/spectra/spectra.png$', display_calibspec, name='display_calibspec'),
    url(r'^characterization/$', characterization, name='characterization'),
    url(r'^feasibility/(?P<pk>\d+)/$', SpectroFeasibility.as_view(), name='feasibility'),
    url(r'^feasibility/calib/(?P<pk>\d+)/$', CalibSpectroFeasibility.as_view(), name='feasibility-calib'),
    url(r'^schedule/(?P<pk>\d+)/confirm/$', ScheduleSubmit.as_view(), name='schedule-confirm'),
    url(r'^schedule/(?P<pk>\d+)/$', ScheduleParameters.as_view(), name='schedule-body'),
    url(r'^schedule/calib/(?P<pk>\d+)/$', ScheduleCalibParameters.as_view(), name='schedule-calib'),
    url(r'^schedule/(?P<pk>\d+)/cadence/$', ScheduleParametersCadence.as_view(), name='schedule-body-cadence'),
    url(r'^schedule/(?P<pk>\d+)/spectra/$', ScheduleParametersSpectra.as_view(), name='schedule-body-spectra'),
    url(r'^calib-schedule/(?P<instrument_code>[A-Z,0-9,\-]*)/(?P<pk>[-\d]+)/$', ScheduleCalibSpectra.as_view(), name='schedule-calib-spectra'),
    url(r'^calib-schedule/(?P<pk>\d+)/confirm/$', ScheduleCalibSubmit.as_view(), name='schedule-calib-confirm'),
    url(r'^accounts/login/$', login, {'template_name': 'core/login.html'}, name='auth_login'),
    url(r'^accounts/logout/$', logout, {'template_name': 'core/logout.html'}, name='auth_logout'),
    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', views.serve),
    ]
