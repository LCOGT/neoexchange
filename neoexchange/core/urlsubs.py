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
import sys
import os
from datetime import datetime, timedelta
import logging

from astropy import units as u
from astropy.table import QTable
from django.conf import settings
from opensearchpy import OpenSearch

from astrometrics.ephem_subs import determine_darkness_times

OPENSEARCH_URL = os.getenv('OPENSEARCH_URL', 'https://opensearch.lco.global')

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


class ESMetricsSource(object):
    '''
        Base class for opensearch based metrics. Right now just records the url and the index name.
    '''

    def __init__(self, os_url, index, start_time=datetime.utcnow()-timedelta(days=1),
                 end_time=datetime.utcnow()):
        self.os_url = os_url
        self.index = index
        self.start_time = start_time
        self.end_time = end_time


class QueryTelemetry(ESMetricsSource):
    '''
        Gets sets of telemetry from the FITS header index in elasticsearch.
    '''

    def __init__(self, start_time=datetime.utcnow()-timedelta(days=1),
                 end_time=datetime.utcnow()):
        ESMetricsSource.__init__(self, os_url=OPENSEARCH_URL, index='fitsheaders',
                                 start_time=start_time, end_time=end_time)

    def get_site_names():
        '''
            Sites that have accesible DIMM data
        '''
        return ['cpt', 'lsc', 'elp']

    def map_LCOsite_to_sitecode(self, site):
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

    def get_seeing_for_site(self, site):

        site_code = self.map_LCOsite_to_sitecode(site)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date=self.start_time, sun_zd=96)
        print("Darkness times: {start}->{end}".format(start=dark_start, end=dark_end))

        # Setup ElasticSearch query
        client = OpenSearch(self.os_url)
        formatter = "%Y-%m-%d %H:%M:%S"
        dimm_query = {
              "query": {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "measure_time" : {
                                    "gte" : dark_start.strftime(formatter),
                                    "lte" : dark_end.strftime(formatter),
                                    "format" : "yyyy-MM-dd HH:mm:ss"
                                }
                            }
                        },
                        {
                            "match": {
                                "site": site
                            }
                        }
                    ]
                }
            }
        }
        seeing_results = client.search(index='dimm', request_timeout=60, body=dimm_query,
                             size=10000, sort=['measure_time:asc'])
        if seeing_results['hits']['total'] > 0:
            results = seeing_results['hits']['hits']
        else:
            results = []

        return results

    def get_fwhm_for_site_telescope(self, site, enclosure, telescope="1m0a"):

        site_code = self.map_LCOsite_to_sitecode(site)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date=self.start_time, sun_zd=96)
        print(dark_start, dark_end)

        # Setup ElasticSearch query
        client = OpenSearch(self.os_url)
        formatter = "%Y-%m-%d %H:%M:%S"
        image_query = {
              "query": {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "DATE-OBS" : {
                                    "gte" : dark_start.strftime(formatter),
                                    "lte" : dark_end.strftime(formatter),
                                    "format" : "yyyy-MM-dd HH:mm:ss"
                                }
                            }
                        },
                        {
                            "match": {
                                "SITEID": site
                            }
                        },
                        {
                            "match": {
                                "ENCID": enclosure
                            }
                        },
                        {
                            "match": {
                                "TELID": telescope
                            }
                        },
                        {
                            "term" : {
                              "RLEVEL" : 91
                            }
                        },
                        {
                          "terms" : {
                            "OBSTYPE" : ["EXPOSE", "STANDARD"]
                          }
                        }
                    ]
                }
            }
        }
        image_results = client.search(index=self.es_index, request_timeout=60, body=image_query,
                            size=400, sort=['DATE-OBS:asc'],
                            _source=["FILTER", "FOCOBOFF", "L1FWHM", "DATE-OBS", "AIRMASS"])
        if image_results['hits']['total'] > 0:
            results = image_results['hits']['hits']
        else:
            results = []

        return results


def convert_temps_to_table(temps_data, time_field='timestampmeasured', datum_name='datumname', data_field='seeing', default_units=None):
    """
        Convert a list of temperature measurements read from ES (via
        get_temps_for_site_telescope()) in <temps_data> into an Astropy Table
    """

    times = {}
    temps = {}
    units = None

    for temp in temps_data:
        temp_data = temp.get('_source', {})
        try:
            temp_time = datetime.strptime(temp_data.get(time_field, ''), "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                temp_time = datetime.strptime(temp_data.get(time_field, ''), "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                logger.warning("Could not parse datetime:" + temp_data.get(time_field, ''))
                temp_time = None
        units = temp_data.get('units', None)
        if not units and default_units is None:
            logger.debug("Unknown units found, assuming degrees C")
            units = 'degC'
        datum = temp_data.get('datumname', datum_name)
        temp_value = temp_data.get(data_field, None)
        if temp_value and temp_time and datum:
            if datum in times.keys() and datum in temps.keys():
                # Already known datum, add to list
                times[datum].append(temp_time)
                temps[datum].append(temp_value)
            else:
                times[datum] = [temp_time, ]
                temps[datum] = [temp_value, ]
    tables = []
    if units == 'degC':
        units = u.deg_C
    else:
        units = u.dimensionless_unscaled
    for datum in times.keys():
        foo = u.Quantity([x*units for x in temps[datum]])
        temp_table = QTable([times[datum],foo], names=('UTC Datetime', datum))
        tables.append(temp_table)

    return tables
