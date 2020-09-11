from django.conf.urls import url

from .views import SubmitView, detail

url_patterns = [
    url(r'^$', detail),
    url(r'^submit/$', SubmitView.as_view(), name='submit')
]
