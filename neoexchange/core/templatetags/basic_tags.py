from django import template
from django.conf import settings
from django.template import Library
from astrometrics.time_subs import degreestohours, hourstodegrees, degreestodms, \
    degreestohms, radianstohms, radianstodms, dttodecimalday

register = Library()

register.filter('degreestohours', degreestohours)
register.filter('hourstodegrees', hourstodegrees)
register.filter('degreestodms', degreestodms)
register.filter('degreestohms', degreestohms)
register.filter('radianstohms', radianstohms)
register.filter('radianstodms', radianstodms)
register.filter('dttodecimalday', dttodecimalday)
