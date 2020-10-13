from django.urls import path

import pipelines.views as pv

urlpatterns = [
    path('', pv.overview, name='pipelines'),
    path('dlc/submit/', pv.DLCSubmitView.as_view(), name='pipesubmitdlc'),
    path('detail/<pk>/', pv.PipelineProcessDetailView.as_view() ,name="pipelinedetail" ),
    path('api/status/<pk>/', pv.AsyncStatusApi.as_view(), name='async_process_status_api'),
    path('api/logs/<pk>/', pv.PipelineProcessApi.as_view(), name='pipeline_api'),
]
