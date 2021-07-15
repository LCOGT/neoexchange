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
from datetime import datetime, timedelta
from dateutil import relativedelta

from django.conf import settings
from pydrive.auth import GoogleAuth, ServiceAccountCredentials
import gspread
from gspread.utils import a1_to_rowcol, rowcol_to_a1

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

def authenticate_to_gdrive(credentials_file="mycreds.json"):
    gauth = GoogleAuth()
    # Try to load saved client credentials
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)

    if gauth.credentials is None:
        # Authenticate if they're not there
        # Need to download from Google Developers Console and save credentials
        # from Google Cloud and save as 'client_secrets.json'
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()

    return gauth

def get_sheet_client(auth):
    """Returns a gspread Client from the passed Google API <auth>"""

    return gspread.authorize(auth.credentials)

def get_spreadsheet(client, name='LOOK LPC Overview'):
    """Gets or creates the Google Sheets spreadsheet specified by <name>"""

    try:
        sheet = client.open(name)
    except gspread.SpreadsheetNotFound:
        sheet = client.create(name)

    return sheet

def get_worksheet(sheet, name='testing'):
    """Gets or creates the worksheet specified by <name> in the passed <sheet>"""

    created = False
    try:
        worksheet = sheet.worksheet(name)
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=name, rows="20", cols="100")
        created = True

    return worksheet, created

def initialize_look_lpc_sheet(sheet):
    """Creates headings for LOOK LPC Overview spreadsheet
    """

    title_format = {'textFormat' : {"fontSize" : 14, "fontFamily" : "PT Sans"}}
    hdr_format   = {'textFormat' : {"fontSize" : 11,
                                    "fontFamily" : "PT Sans",
                                    "bold" : True}
                   }

    sheet.update('A1', 'Observed LPCs')
    sheet.format('A1', title_format)

    headings = ['Name', 'Start Date', 'Start r', 'Perihelion Dist', 'Perihelion Date', '1/a (Nakano)' , 'Notes', 'Total Visits']

    start_date = datetime(2020, 8, 1)
    end_date = start_date + timedelta(days=(3*365)-1)
    a_month = relativedelta.relativedelta(months=1)
    date = start_date
    while date < end_date:
        headings.append(date.strftime("%B %Y"))
        date += a_month
    sheet.insert_row(headings, 3)

    last_cell = sheet.cell(3, len(headings)+1)
    sheet.format('A3:' + last_cell.address, hdr_format)

    return

def populate_comet_lines(sheet, qs):

    text_format   = {'textFormat' : {"fontSize" : 11,
                                    "fontFamily" : "PT Sans" }
                   }

    index = 4
    for comet in qs:
        values = [comet.current_name(), "", "", comet.perihdist, comet.epochofperih.strftime("%Y-%m-%d"), comet.recip_a]
        sheet.insert_row(values, index)
        cell_range = "{}:{}".format(rowcol_to_a1(index, 1), rowcol_to_a1(index,8))
        sheet.format(cell_range, text_format)
        index += 1

    return
