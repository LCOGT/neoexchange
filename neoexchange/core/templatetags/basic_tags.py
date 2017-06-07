from django import template
from django.conf import settings
from django.template import Library
from django.template.defaultfilters import floatformat
from astrometrics.time_subs import degreestohours, hourstodegrees, degreestodms, \
    degreestohms, radianstohms, radianstodms, dttodecimalday

register = Library()

def subsblank(value, arg):
    arg = int(arg)
    if not value:
        return arg*" "
    else:
        return value

def roundeddays(value, arg):
    '''Lightly customized version of floatformat to return "None" if the value
    is None rather than a blank space'''
    if value:
        return floatformat(value,arg)
    else:
        return "None"

register.filter('subsblank', subsblank)
register.filter('degreestohours', degreestohours)
register.filter('hourstodegrees', hourstodegrees)
register.filter('degreestodms', degreestodms)
register.filter('degreestohms', degreestohms)
register.filter('radianstohms', radianstohms)
register.filter('radianstodms', radianstodms)
register.filter('dttodecimalday', dttodecimalday)
register.filter('roundeddays', roundeddays)
