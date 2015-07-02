from django import template
from django.conf import settings
from django.template import Library
from astrometrics.time_subs import degreestohours, hourstodegrees, degreestodms, degreestohms

register = Library()

register.filter('degreestohours', degreestohours)
register.filter('hourstodegrees', hourstodegrees)
register.filter('degreestodms', degreestodms)
register.filter('degreestohms', degreestohms)