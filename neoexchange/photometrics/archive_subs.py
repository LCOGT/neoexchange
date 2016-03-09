'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

archive_subs.py -- Routines for downloading data from the LCOGT Archive

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import requests
from datetime import datetime, timedelta

def get_base_url():
    '''Return the base URL of the archive service'''
    archive_url = 'https://archive-api.lcogt.net'
    return archive_url

def archive_login(username, password):

    base_url = get_base_url()
    archive_url = base_url + '/api-token-auth/'
    #  Get the authentication token
    response = requests.post(archive_url,
        data = {
                'username': username,
                'password': password
               }).json()

    try:
        token = response.get('token')

        # Store the Authorization header
        headers = {'Authorization': 'Token ' + token}
    except TypeError:
        headers = None

    return headers

def get_proposal_data(start_date, end_date, auth_header='', proposal='LCO2015B-005'):

    base_url = get_base_url()
    archive_url = '%s/frames/?start=%s&end=%s&PROPID=%s' % (base_url, start_date, end_date, proposal)

    response = requests.get(archive_url, headers=auth_header).json()

    frames = response['results']

    return frames
