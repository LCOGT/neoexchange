from operator import itemgetter
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
    """Lightly customized version of floatformat to return "None" if the value
    is None rather than a blank space"""
    if value:
        return floatformat(value, arg)
    else:
        return "None"


def dictsortreversed_with_none(value, arg):
    """
    Takes a list of dicts, returns that list sorted in reverse order by the
    property given in the argument. Separates out None values and places them
    at the end.
    """
    try:
        return sorted(value, key=lambda x: (itemgetter(arg)(x) is not None, itemgetter(arg)(x)), reverse=True)
    except TypeError:
        return ''

@register.simple_tag
def format_mpc_line_upload(measure):
    return measure.format_mpc_line(include_catcode=False)

@register.simple_tag
def format_mpc_line_catcode(measure):
    return measure.format_mpc_line(include_catcode=True)

register.filter('dictsortreversed_with_none', dictsortreversed_with_none)
register.filter('subsblank', subsblank)
register.filter('degreestohours', degreestohours)
register.filter('hourstodegrees', hourstodegrees)
register.filter('degreestodms', degreestodms)
register.filter('degreestohms', degreestohms)
register.filter('radianstohms', radianstohms)
register.filter('radianstodms', radianstodms)
register.filter('dttodecimalday', dttodecimalday)
register.filter('roundeddays', roundeddays)
