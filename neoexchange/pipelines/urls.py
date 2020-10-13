from django.conf.urls import url
from django.urls import path

from .views import PipelineSubmitView, PipelineProcessDetailView, overview

url_patterns = [
    path('', detail, name='pipelines'),
    path('submit/$', SubmitView.as_view(), name='submit'),
    path('detail/(?P<pk>\d+)/$', PipelineProcessDetailView.as_view() ,name="pipelinedetail" ),
]
