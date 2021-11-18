"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import date
from operator import itemgetter
from django import template
from django.conf import settings
from django.template import Library
from django.template.defaultfilters import floatformat
from astrometrics.time_subs import degreestohours, hourstodegrees, degreestodms, \
    degreestohms, radianstohms, radianstodms, dttodecimalday, mjd_utc2datetime
from astrometrics.ephem_subs import get_alt_from_airmass
from core.models import Block


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


def make_int_list(value):
    """
    Filter - returns a list of integers 1 -> n where n is the given value
    Usage (in template):

    <ul>{% for i in 3|get_range %}
      <li>{{ i }}. Do something</li>
    {% endfor %}</ul>

    Results with the HTML:
    <ul>
      <li>1. Do something</li>
      <li>2. Do something</li>
      <li>3. Do something</li>
    </ul>

    Instead of 3 one may use a variable set in the views
    """
    return range(1, value+1)


@register.filter(is_safe=False)
def multiply(value, arg):
    """multiply the arg by the value."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        try:
            return value * arg
        except Exception:
            return ''


@register.simple_tag
def format_mpc_line_upload(measure):
    return measure.format_mpc_line(include_catcode=False)


@register.simple_tag
def format_mpc_line_catcode(measure):
    return measure.format_mpc_line(include_catcode=True)


@register.filter(is_safe=False)
def get_period(body):
    return body.get_physical_parameters('P', False)


@register.inclusion_tag('partials/block_row.html')
def build_block_row(superblock):
    return {
        'block': superblock,
        'sites': superblock.get_sites(),
        'telclass': superblock.get_telclass(),
        'obsdetails': superblock.get_obsdetails(),
        'num_observed': superblock.get_num_observed(),
        'num_reported': superblock.get_num_reported()
    }


@register.filter(is_safe=False)
def mjd_utc2date(mjd):
    utc_date = None
    if mjd is not None:
        utc_date = mjd_utc2datetime(mjd).date()
    return utc_date


@register.filter(is_safe=False)
def addstr(arg1, arg2):
    """Concatenate 2 strings"""
    out_string = str(arg1) + str(arg2)
    return out_string


register.filter('make_int_list', make_int_list)
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
register.filter('get_alt_from_airmass', get_alt_from_airmass)
