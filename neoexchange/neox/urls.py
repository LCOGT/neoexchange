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
from django.urls import path, re_path
from django.contrib.staticfiles import views
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView

from core.models import Body, Block, SourceMeasurement, SuperBlock, StaticSource
from core.views import BodySearchView, BodyDetailView, BlockDetailView, ScheduleParameters, \
    ScheduleSubmit, ephemeris, home, BlockReport, ranking, MeasurementViewBody, MeasurementViewBlock, \
    UploadReport, BlockTimeSummary, ScheduleParametersCadence, ScheduleParametersSpectra, \
    CandidatesViewBlock, BlockReportMPC, \
    MeasurementDownloadMPC, MeasurementDownloadADESPSV, \
    SuperBlockListView, SuperBlockDetailView, characterization, SpectroFeasibility, BlockSpec,\
    display_movie, GuideMovie, LCPlot, SpecDataListView, LCDataListView,\
    StaticSourceView, StaticSourceDetailView, ScheduleCalibSpectra, ScheduleCalibSubmit, \
    CalibSpectroFeasibility, ScheduleCalibParameters, \
    BestStandardsView, PlotSpec, BodyVisibilityView, SuperBlockTimeline, BlockCancel, \
    look_project, AddTarget, display_textfile
from core.plots import make_visibility_plot, \
    make_standards_plot, make_solar_standards_plot

from analyser.views import BlockFramesView, ProcessCandidates


admin.autodiscover()

urlpatterns = [
    path('', home, name='home'),
    # path('makeplot/', make_plot, name='makeplot'),
    # path('plotframe/', TemplateView.as_view(template_name='core/frame_plot.html')),
    path('make-standards-plot/', make_standards_plot, name='make-standards-plot'),
    path('make-solar-standards-plot/', make_solar_standards_plot, name='make-solar-standards-plot'),
    path('visibility_plot/<int:pk>/<str:plot_type>/', make_visibility_plot, name='visibility-plot'),
    re_path(r'^visibility_plot/(?P<pk>\d+)/(?P<plot_type>[a-z]*)/(?P<site_code>[A-Z,0-9]{3})/', make_visibility_plot, name='visibility-plot-site'),
    path('block/summary/', BlockTimeSummary.as_view(), name='block-summary'),
    path('block/list/', SuperBlockListView.as_view(model=SuperBlock, queryset=SuperBlock.objects.order_by('-block_start'), context_object_name="block_list"), name='blocklist'),
    path('block/<int:pk>/spectra/', BlockSpec.as_view(), name='blockspec'),
    path('block/<int:pk>/guidemovie/', GuideMovie.as_view(), name='guidemovie'),
    path('block/<int:pk>/spectra/guidemovie.gif', display_movie, name='display_movie'),
    path('block/<int:pk>/source/<int:source>/report/submit/', BlockReportMPC.as_view(), name='block-submit-mpc'),
    path('block/<int:pk>/report/', BlockReport.as_view(), name='report-block'),
    path('block/<int:pk>/upload/', UploadReport.as_view(), name='upload-report'),
    path('block/<int:pk>/measurements/mpc/', MeasurementViewBlock.as_view(template='core/mpcreport.html'), name='block-report-mpc'),
    path('block/<int:pk>/measurements/', MeasurementViewBlock.as_view(), name='block-report'),
    path('block/<int:pk>/analyser/', BlockFramesView.as_view(), name='block-ast'),
    path('block/<int:pk>/analyser/submit/', ProcessCandidates.as_view(), name='submit-candidates'),
    path('block/<int:pk>/candidates/', CandidatesViewBlock.as_view(), name='view-candidates'),
    path('block/<int:pk>/timeline/', SuperBlockTimeline.as_view(), name='view-timeline'),
    path('block/<int:pk>/cancel/', BlockCancel.as_view(), name='block-cancel'),
    path('block/<int:pk>/', SuperBlockDetailView.as_view(model=SuperBlock), name='block-view'),
    path('summary/spec/', SpecDataListView.as_view(), name='spec_data_summary'),
    path('summary/lc/', LCDataListView.as_view(), name='lc_data_summary'),
    path('target/', ListView.as_view(model=Body, queryset=Body.objects.filter(active=True).order_by('-origin', '-ingest'), context_object_name="target_list"), name='targetlist'),
    path('target/<int:pk>/measurements/ades/download/', MeasurementDownloadADESPSV.as_view(), name='download-ades'),
    path('target/<int:pk>/measurements/mpc/download/', MeasurementDownloadMPC.as_view(), name='download-mpc'),
    path('target/<int:pk>/measurements/ades/', MeasurementViewBody.as_view(template='core/adesreport.html'), name='measurement-ades'),
    path('target/<int:pk>/measurements/mpc/', MeasurementViewBody.as_view(template='core/mpcreport.html'), name='measurement-mpc'),
    path('target/<int:pk>/measurements/', MeasurementViewBody.as_view(), name='measurement'),
    path('target/<int:pk>/visibility/', BodyVisibilityView.as_view(model=Body), name='visibility'),
    path('target/<int:pk>/', BodyDetailView.as_view(model=Body), name='target'),
    path('target/<int:pk>/spectra/', PlotSpec.as_view(), name='plotspec'),
    path('target/<int:pk>/lc/', LCPlot.as_view(), name='lc_plot'),
    path('documents/<int:pk>.txt', display_textfile, name='display_textfile'),
    path('target/add/', AddTarget.as_view(), name='add_target'),
    path('search/', BodySearchView.as_view(context_object_name="target_list"), name='search'),
    path('ephemeris/', ephemeris, name='ephemeris'),
    path('ranking/', ranking, name='ranking'),
    path('calibsources/', StaticSourceView.as_view(), name='calibsource-view'),
    path('calibsources/best/', BestStandardsView.as_view(), name='beststandards-view'),
    path('calibsources/solar/', StaticSourceView.as_view(queryset=StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD).order_by('ra')), name='solarstandard-view'),
    path('calibsources/<int:pk>/', StaticSourceDetailView.as_view(model=StaticSource), name='calibsource'),
    path('characterization/', characterization, name='characterization'),
    path('lookproject/', look_project, name='look_project'),
    path('feasibility/<int:pk>/', SpectroFeasibility.as_view(), name='feasibility'),
    path('feasibility/calib/<int:pk>/', CalibSpectroFeasibility.as_view(), name='feasibility-calib'),
    path('schedule/<int:pk>/confirm/', ScheduleSubmit.as_view(), name='schedule-confirm'),
    path('schedule/<int:pk>/', ScheduleParameters.as_view(), name='schedule-body'),
    path('schedule/calib/<int:pk>/', ScheduleCalibParameters.as_view(), name='schedule-calib'),
    path('schedule/<int:pk>/cadence/', ScheduleParametersCadence.as_view(), name='schedule-body-cadence'),
    path('schedule/<int:pk>/spectra/', ScheduleParametersSpectra.as_view(), name='schedule-body-spectra'),
    path('calib-schedule/<slug:instrument_code>/<pk>/', ScheduleCalibSpectra.as_view(), name='schedule-calib-spectra'),
    path('calib-schedule/<int:pk>/confirm/', ScheduleCalibSubmit.as_view(), name='schedule-calib-confirm'),
    path('accounts/login/', LoginView.as_view(template_name='core/login.html'), name='auth_login'),
    path('accounts/logout/', LogoutView.as_view(template_name='core/logout.html'), name='auth_logout'),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
