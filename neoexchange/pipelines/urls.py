from django.conf.urls import include, url

from .views import submitjob, detail

url_patterns = [
    url(r'^submit/$', submitjob, name='submit'),
    url(r'^detail/(?P<pk>\d+)/$', detail, name='detail'),
]
