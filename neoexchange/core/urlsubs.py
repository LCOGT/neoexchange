"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
import requests
import json
import sys
import os
from datetime import datetime, timedelta
import logging

import numpy as np
from astropy.time import Time
from astropy.table import QTable
from django.conf import settings

from astrometrics.ephem_subs import determine_darkness_times, MPC_site_code_to_domes

OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'https://opensearch.lco.global:443')

logger = logging.getLogger(__name__)
ssl_verify = True
# Check if Python version is less than 2.7.9. If so, disable SSL warnings and SNI verification
if sys.version_info < (2, 7, 9):
    requests.packages.urllib3.disable_warnings()
    ssl_verify = False  # Danger, danger !


def authenticate_to_lco(auth_url, username, password):
    token = ''
    response = requests.post(auth_url,
        data={ 'username' : username,
                 'password' : password
        }
    )
    if response.status_code == 200:
        token = response.json()['token']

    return token


def get_lcogt_headers(auth_url, username, password):
    #  Get the authentication token
    if 'archive' in auth_url:
        token = settings.ARCHIVE_TOKEN
    else:
        token = settings.PORTAL_TOKEN
    if token == '':
        # Token is blank, try to authenticate
        token = authenticate_to_lco(auth_url, username, password)

    headers = {'Authorization': 'Token ' + token}

    return headers

def get_telescope_states(telstates_url='http://observe.lco.global/api/telescope_states/'):

    try:
        response = requests.get(telstates_url).json()
    except ValueError:
        response = {}

    return response

def get_site_names():
    '''
        Sites that have accesible DIMM data
    '''
    return ['cpt', 'lsc', 'elp', 'tfn']

def map_LCOsite_to_sitecode(site):
    """
        Map LCO site names (e.g. 'cpt') MPC site codes (e.g. 'K92'). If no match
        is found, '500' (geocenter) is returned
    """

    site_mapping = { 'cpt' : 'K92',
                     'lsc' : 'W86',
                     'tfn' : 'Z21',
                     'elp' : 'V37'
                   }

    site_code = site_mapping.get(site.lower(), '500')

    return site_code

def get_seeing_for_site(site, start_time=None):
    """Query OpenSearch for DIMM seeing data for the passed <site> on the
    night of [start_time] (defaults to datetime.utcnow()-1 day)
    """
    logger.setLevel(logging.DEBUG)
    start_time = start_time or datetime.utcnow()-timedelta(days=1)
    if site[-1].isdigit() is False:
        site_code = map_LCOsite_to_sitecode(site)
    else:
        site_code = site
        site, enc_id, tel_id = MPC_site_code_to_domes(site_code)

    dark_start, dark_end = determine_darkness_times(site_code, utc_date=start_time, sun_zd=96)
    if (start_time-dark_start).days >= 1:
        logger.debug("Adding 1 day, redetermining")
        dark_start, dark_end = determine_darkness_times(site_code, utc_date=start_time+timedelta(days=1), sun_zd=96)
    logger.debug(f"Darkness times {dark_start} -> {dark_end}")

    sourcecolumns = ['site', 'measure_time', 'seeing']
    # Setup query constraints
    query = f'site:{site} AND measure_time: [{dark_start.strftime("%Y-%m-%dT%H:%M:%S")} TO {dark_end.strftime("%Y-%m-%dT%H:%M:%S")}]'
    dimm_query = {
        "size": 10000,
        "_source": sourcecolumns,
        "sort" : {
                    "measure_time" : { "order" :"asc" }
                  },
        "query": {
            "query_string": {
                "query": query
            }
        }
    }
    headers = {'Content-type': 'application/json'}
    response = requests.get(f'{OPENSEARCH_URL}/dimm/_search',
                            data=json.dumps(dimm_query), headers=headers)
    t = None
    if response.status_code in [200, 201]:
        response = response.json()
        intermediate = [r['_source'] for r in response['hits']['hits']]
        t = [[item[col] for col in sourcecolumns] for item in intermediate]
        t = np.asarray(t)
        t = QTable(t, names=sourcecolumns)
        for col in sourcecolumns:
            new_col_values = None
            if col == 'measure_time':
                new_col_values = [datetime.strptime(d, "%Y-%m-%dT%H:%M:%S") for d in t[col]]
            elif col == 'seeing':
                new_col_values = [float(v) for v in t[col]]
            if new_col_values:
                t.replace_column(col, new_col_values, copy=False)
    else:
        logger.error(f"Error retrieving DIMM seeing data. Response code: {response.status_code}")
    return t
