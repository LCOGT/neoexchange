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
from collections import Counter
from operator import itemgetter
from django import template
from django.conf import settings
from django.template import Library
from django.template.defaultfilters import floatformat
from astrometrics.time_subs import degreestohours, hourstodegrees, degreestodms, \
    degreestohms, radianstohms, radianstodms, dttodecimalday
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


@register.inclusion_tag('partials/block_row.html')
def build_block_row(superblock):
    qs = superblock.block_set.all()

    sites_list = list(set([q.site for q in qs]))
    sites_list = [s for s in sites_list if s is not None]
    if sites_list:
        sites = ", ".join(sites_list)
    else:
        sites = None

    class_list = list(set([(q.telclass, q.obstype) for q in qs]))
    class_obstype = [x[0]+str(x[1]).replace(str(Block.OPT_SPECTRA), '(S)').replace(str(Block.OPT_SPECTRA_CALIB), '(SC)').replace(str(Block.OPT_IMAGING), '') for x in class_list]
    telclass = ", ".join(class_obstype)

    detail_list = list(set([(q.num_exposures, q.exp_length) for q in qs]))
    # Count number of unique N exposure x Y exposure length combinations
    counts = Counter([elem for elem in detail_list])

    obsdetails = ""
    if len(counts) > 1:
        obs_details = []
        for c in counts.items():
            obs_details.append("%d of %dx%.1f secs" % (c[1], c[0][0], c[0][1]))

        obsdetails = ", ".join(obs_details)
    elif len(counts) == 1:
        c = list(counts)
        obsdetails = "%dx%.1f secs" % (c[0][0], c[0][1])

    num_obs = sum([q.num_observed for q in qs if q.num_observed and q.num_observed >= 1])
    num_observed = num_obs, qs.count()

    num_reported = len([q for q in qs if q.reported is True]), qs.count()

    return {
        'block': superblock,
        'sites': sites,
        'telclass': telclass,
        'obsdetails': obsdetails,
        'num_observed': num_observed,
        'num_reported': num_reported
    }


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
