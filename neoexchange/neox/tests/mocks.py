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

from datetime import datetime as real_datetime
from datetime import datetime
import os

import astropy.units as u
from django.contrib.auth import authenticate
import logging
from astrometrics.sources_subs import parse_filter_file
from astrometrics.ephem_subs import MPC_site_code_to_domes

logger = logging.getLogger(__name__)

# Adapted from http://www.ryangallen.com/wall/11/mock-today-django-testing/
# and changed to datetime and python 2.x


class MockDateTimeType(type):

    def __init__(cls, name, bases, d):
        type.__init__(cls, name, bases, d)
        cls.year = 2015
        cls.month = 4
        cls.day = 1
        cls.hour = 17
        cls.minute = 0
        cls.second = 0

    def __instancecheck__(self, instance):
        return isinstance(instance, real_datetime)


class MockDateTime(datetime, metaclass=MockDateTimeType):

    @classmethod
    def change_date(cls, year, month, day):
        cls.year = year
        cls.month = month
        cls.day = day

    @classmethod
    def change_datetime(cls, year, month, day, hour, minute, second):
        cls.year = year
        cls.month = month
        cls.day = day
        cls.hour = hour
        cls.minute = minute
        cls.second = second

    @classmethod
    def utcnow(cls):
        return cls(cls.year, cls.month, cls.day, cls.hour, cls.minute, cls.second)


def mock_fetchpage_and_make_soup(url, fakeagent=False, dbg=False, parser="html.parser"):
    logger.warning("Page retrieval failed because this is a test and no page was attempted.")
    return None


def mock_check_request_status(tracking_num):
    status = { u'created' : u'2015-10-21T19:07:26.023049Z',
                u'name' : u'Fake group',
                u'id': 42,
                u'ipp_value': 1.05,
                u'modified': u'2015-10-21T19:07:26.023049Z',
                u'observation_type': u'NORMAL',
                u'operator': u'SINGLE',
                u'proposal': u'LCOEPO2014B-XXX',
                u'requests': [{
                    u'completed': None,
                    u'constraints': {u'max_airmass': 1.74,
                                     u'max_lunar_phase': None,
                                     u'max_seeing': None,
                                     u'min_lunar_distance': 30.0,
                                     u'min_transparency': None},
                    u'created' : u'2015-10-21T19:07:26.023049Z',
                    u'duration' : 1317,
                    u'fail_count': 0,
                    u'id': 611796,
                    u'location': {u'observatory': None,
                                    u'site': 'lsc',
                                    u'telescope': None,
                                    u'telescope_class': '1m0'},
                    u'modified': u'2015-10-21T19:07:26.023049Z',
                    u'molecules': [{'acquire_mode': 'WCS',
                       'bin_x': 2,
                       'exposure_count': 1,
                       'exposure_time': 300.0,
                       'filter': 'B',
                       'id': 1001945,
                       'instrument_name': '1M0-SCICAM-SBIG',
                       'priority': 1,
                       'request': 617292,
                       'type': 'EXPOSE'}],
                    u'target': {'acquire_mode': 'OPTIONAL',
                       'argofperih': None,
                       'coordinate_system': 'ICRS',
                       'dailymot': None,
                       'dec': 47.1952583333,
                       'eccentricity': None,
                       'epoch': 2000.0,
                       'epochofel': None,
                       'epochofperih': None,
                       'equinox': 'J2000',
                       'longascnode': None,
                       'longofperih': None,
                       'meananom': None,
                       'meandist': None,
                       'meanlong': None,
                       'name': 'M51',
                       'orbinc': None,
                       'parallax': 0.0,
                       'perihdist': None,
                       'proper_motion_dec': 0.0,
                       'proper_motion_ra': 0.0,
                       'ra': 202.469575,
                       'type': 'SIDEREAL'},
                    u'windows': [{'end': '2015-10-22T09:00:00',
                        'start': '2015-10-22T07:00:00'}],
                }],
                u'state': u'PENDING',
                u'submitter': u'fakeperson@fakeout.net'
             }
    return status


def mock_check_request_status_cadence(tracking_num):

    status = {u'created': u'2017-08-15T19:18:24.869792Z',
             u'name': u'3122_COJ_cad_20170816-0819',
             u'id': 472636,
             u'ipp_value': 1.05,
             u'modified': u'2017-08-15T19:18:24.869822Z',
             u'observation_type': u'NORMAL',
             u'operator': u'MANY',
             u'proposal': u'LCO2017AB-016',
             u'requests': [{u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.871932Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257363,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.008044Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-16T12:00:00Z',
                 u'start': u'2017-08-16T10:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.878834Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257364,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.015119Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'rot_angle': 0.0,
                u'rot_mode': u'',
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-16T16:00:00Z',
                 u'start': u'2017-08-16T14:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.883743Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257365,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.032071Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-16T20:00:00Z',
                 u'start': u'2017-08-16T18:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.888474Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257366,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.038166Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-17T12:00:00Z',
                 u'start': u'2017-08-17T10:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.893286Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257367,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.044241Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-17T16:00:00Z',
                 u'start': u'2017-08-17T14:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.898072Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257368,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.050400Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-17T20:00:00Z',
                 u'start': u'2017-08-17T18:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.902794Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257369,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.056587Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-18T12:00:00Z',
                 u'start': u'2017-08-18T10:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.907553Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257370,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.062716Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-18T16:00:00Z',
                 u'start': u'2017-08-18T14:00:00Z'}]},
              {u'completed': None,
               u'constraints': {u'max_airmass': 2.0,
                u'max_lunar_phase': None,
                u'max_seeing': None,
                u'min_lunar_distance': 30.0,
                u'min_transparency': None},
               u'created': u'2017-08-15T19:18:24.912247Z',
               u'duration': 3576,
               u'fail_count': 0,
               u'id': 1257371,
               u'location': {u'telescope_class': u'0m4'},
               u'modified': u'2017-08-15T23:05:55.069066Z',
               u'molecules': [{u'acquire_mode': u'OFF',
                 u'ag_exp_time': 10.0,
                 u'ag_filter': u'',
                 u'ag_mode': u'OPTIONAL',
                 u'ag_name': u'',
                 u'bin_x': 2,
                 u'bin_y': 2,
                 u'defocus': 0.0,
                 u'exposure_count': 102,
                 u'exposure_time': 20.0,
                 u'filter': u'w',
                 u'instrument_name': u'0M4-SCICAM-SBIG',
                 u'priority': 1,
                 u'type': u'EXPOSE'}],
               u'observation_note': u'',
               u'scheduled_count': 0,
               u'state': u'PENDING',
               u'target': {u'acquire_mode': None,
                u'argofperih': 27.8469,
                u'eccentricity': 0.4233003,
                u'epochofel': 58000.0,
                u'longascnode': 336.0952,
                u'meananom': 351.43853,
                u'meandist': 1.7691326,
                u'name': u'3122',
                u'orbinc': 22.1508,
                u'scheme': u'MPC_MINOR_PLANET',
                u'type': u'NON_SIDEREAL',
                u'vmag': None},
               u'windows': [{u'end': u'2017-08-18T20:00:00Z',
                 u'start': u'2017-08-18T18:00:00Z'}]}],
             u'state': u'PENDING',
             u'submitter': u'tlister@lcogt.net'}

    return status


def mock_check_request_status_null(tracking_num):
    return []


def mock_check_request_status_notfound(tracking_num):
    return {u'detail': u'Not found.'}


def mock_check_for_images_no_millisecs(request_id):
    header = { "data": {
                    "DATE_OBS": "2016-06-01T09:43:28",
                    "ENCID": "clma",
                    "SITEID" : "lsc",
                    "TELID" : "1m0a",
                    "FILTER": "rp",
                    "INSTRUME" : "kb27",
                    "ORIGNAME" : "ogg0m406-kb27-20160531-0063-e00",
                    "EXPTIME" : "200.0"
            }
        }
    return header


def mock_check_for_images_bad_date(request_id):
    header = { "data": {
                    "DATE_OBS": "2016-06-01T09:43",
                    "ENCID": "clma",
                    "SITEID" : "lsc",
                    "TELID" : "1m0a",
                    "FILTER": "rp",
                    "INSTRUME" : "kb27",
                    "ORIGNAME" : "ogg0m406-kb27-20160531-0063-e00",
                    "EXPTIME" : "200.0"
            }
        }
    return header


def mock_ingest_frames(images, block):
    return ['99999']


def mock_fetch_archive_frames_2spectra(auth_header, archive_url, frames=[]):
    data = [{
              u'OBSTYPE': u'SPECTRUM',
              u'REQNUM': 1391169,
              u'RLEVEL': 90,
              u'basename': u'LCOEngineering_0001391169_ftn_20180111_58130',
              u'filename': u'LCOEngineering_0001391169_ftn_20180111_58130.tar.gz',
              u'id': 7783593,
              u'related_frames': [7780755, 7780756],
              u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/372a/LCOEngineering_0001391169_ftn_20180111_58130?versionId=eK7.aDucOKWaiM3AhTPZ8AGDMxBFdNtH&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=x8mve2svKirG7BAiWaEBTyFsHrY%3D&Expires=1521319897',
             },
            {
              u'OBSTYPE': u'SPECTRUM',
              u'REQNUM': 1391169,
              u'RLEVEL': 0,
              u'basename': u'ogg2m001-en06-20180110-0005-e00',
              u'filename': u'ogg2m001-en06-20180110-0005-e00.fits.fz',
              u'id': 7780755,
              u'related_frames': [7783593],
              u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/dd9f/ogg2m001-en06-20180110-0005-e00?versionId=c1X8nfL_LSwptv_c0m7dultGCOfVJJr3&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=fjmzi9KK%2FqNi3DnvjyEjSP%2BJG8o%3D&Expires=1521319897',
             },
            {
              u'OBSTYPE': u'SPECTRUM',
              u'REQNUM': 1391169,
              u'RLEVEL': 0,
              u'basename': u'ogg2m001-en06-20180110-0006-e00',
              u'filename': u'ogg2m001-en06-20180110-0006-e00.fits.fz',
              u'id': 7780756,
              u'related_frames': [7783593],
              u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/dd9f/ogg2m001-en06-20180110-00056-e00?versionId=c1X8nfL_LSwptv_c0m7dultGCOfVJJr3&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=fjmzi9KK%2FqNi3DnvjyEjSP%2BJG8o%3D&Expires=1521319897',
             }
            ]
    return data


def mock_fetch_archive_frames(auth_header, archive_url, frames=[]):
    if 'SPECTRUM' in archive_url:
        data = [{
                  u'OBSTYPE': u'SPECTRUM',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 90,
                  u'basename': u'LCOEngineering_0001391169_ftn_20180111_58130',
                  u'filename': u'LCOEngineering_0001391169_ftn_20180111_58130.tar.gz',
                  u'id': 7783593,
                  u'related_frames': [7780755],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/372a/LCOEngineering_0001391169_ftn_20180111_58130?versionId=eK7.aDucOKWaiM3AhTPZ8AGDMxBFdNtH&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=x8mve2svKirG7BAiWaEBTyFsHrY%3D&Expires=1521319897',
                 },
                 {
                  u'OBSTYPE': u'SPECTRUM',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 0,
                  u'basename': u'ogg2m001-en06-20180110-0005-e00',
                  u'filename': u'ogg2m001-en06-20180110-0005-e00.fits.fz',
                  u'id': 7780755,
                  u'related_frames': [7783593],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/dd9f/ogg2m001-en06-20180110-0005-e00?versionId=c1X8nfL_LSwptv_c0m7dultGCOfVJJr3&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=fjmzi9KK%2FqNi3DnvjyEjSP%2BJG8o%3D&Expires=1521319897',
                 }]
    elif archive_url.rfind("OBSTYPE=") > 0 and 'EXPOSE' not in archive_url:
        data = [{
                  u'OBSTYPE': u'SPECTRUM',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 90,
                  u'basename': u'LCOEngineering_0001391169_ftn_20180111_58130',
                  u'filename': u'LCOEngineering_0001391169_ftn_20180111_58130.tar.gz',
                  u'id': 7783593,
                  u'related_frames': [7780755],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/372a/LCOEngineering_0001391169_ftn_20180111_58130?versionId=eK7.aDucOKWaiM3AhTPZ8AGDMxBFdNtH&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=x8mve2svKirG7BAiWaEBTyFsHrY%3D&Expires=1521319897',
                 },
                 {
                  u'OBSTYPE': u'SPECTRUM',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 0,
                  u'basename': u'ogg2m001-en06-20180110-0005-e00',
                  u'filename': u'ogg2m001-en06-20180110-0005-e00.fits.fz',
                  u'id': 7780755,
                  u'related_frames': [7783593],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/dd9f/ogg2m001-en06-20180110-0005-e00?versionId=c1X8nfL_LSwptv_c0m7dultGCOfVJJr3&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=fjmzi9KK%2FqNi3DnvjyEjSP%2BJG8o%3D&Expires=1521319897',
                 },
                 {
                  u'OBSTYPE': u'LAMPFLAT',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 0,
                  u'basename': u'ogg2m001-en06-20180110-0003-w00',
                  u'filename': u'ogg2m001-en06-20180316-0003-w00.fits.fz',
                  u'id': 7780711,
                  u'related_frames': [],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/f0b3/ogg2m001-en06-20180110-0003-w00?versionId=5_5KtN4yTb1HETGb3SOMkkZdVW2vxOpd&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=vwaE37UFo8gnn46IKWuRZKpSoEA%3D&Expires=1521844038',
                 },
                 {
                  u'OBSTYPE': u'ARC',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 0,
                  u'basename': u'ogg2m001-en06-20180110-0004-a00',
                  u'filename': u'ogg2m001-en06-20180110-0004-a00.fits.fz',
                  u'id': 7780725,
                  u'related_frames': [],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/292d/ogg2m001-en06-20180110-0004-a00?versionId=6cU5D5EC7Zq1tVEb7OZlR7WFEeXyqGp8&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=o6l5GeCbm%2FgHa7LRI3ycNyFnhQY%3D&Expires=1521844038',
                 }]
    else:
        data = [
                 {u'OBSTYPE': u'EXPOSE',
                  u'RLEVEL': 91,
                  u'filename': u'ogg0m406-kb27-20160531-0063-e91.fits.fz',
                  u'id': 4029371,
                  u'url': u'https://s3-us-west-2.amazonaws.com/archive.lcogt.net/32de/ogg0m406-kb27-20160531-0063-e91'},
                 {u'OBSTYPE': u'EXPOSE',
                  u'RLEVEL': 11,
                  u'filename': u'ogg0m406-kb27-20160531-0063-e11.fits.fz',
                  u'id': 4029372,
                  u'url': u'https://s3-us-west-2.amazonaws.com/archive.lcogt.net/e00c/ogg0m406-kb27-20160531-0063-e11'},
                 {u'OBSTYPE': u'EXPOSE',
                  u'RLEVEL': 00,
                  u'filename': u'ogg0m406-kb27-20160531-0063-e00.fits.fz',
                  u'id': 4028223,
                  u'url': u'https://s3-us-west-2.amazonaws.com/archive.lcogt.net/bbd6/ogg0m406-kb27-20160531-0063-e00'},
                ]
    return data


def mock_check_for_images(request_id, obstype='EXPOSE'):

    if obstype == 'SPECTRUM':
        images = [
                  {u'filename': u'LCOEngineering_0001391169_ftn_20180111_58130.tar.gz',
                   u'id': 7783593,
                   u'headers': u'https://archive-api.lcogt.net/frames/7783593/headers/',
                   u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/372a/LCOEngineering_0001391169_ftn_20180111_58130?versionId=eK7.aDucOKWaiM3AhTPZ8AGDMxBFdNtH&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=x8mve2svKirG7BAiWaEBTyFsHrY%3D&Expires=1521319897',
                  },
                  {u'filename': u'ogg2m001-en06-20180110-0005-e00.fits.fz',
                   u'id': 7780755,
                   u'headers': u'https://archive-api.lcogt.net/frames/7780755/headers/',
                   u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/dd9f/ogg2m001-en06-20180110-0005-e00?versionId=c1X8nfL_LSwptv_c0m7dultGCOfVJJr3&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=fjmzi9KK%2FqNi3DnvjyEjSP%2BJG8o%3D&Expires=1521319897',
                  }]
    else:
        images = [
                  {u'filename': u'ogg0m406-kb27-20160531-0063-e90_cat.fits',
                   u'headers': u'https://archive-api.lcogt.net/frames/4029371/headers/',
                   u'id': 4029371,
                   u'url': u'https://s3-us-west-2.amazonaws.com/archive.lcogt.net/32de/ogg0m406-kb27-20160531-0063-e90_cat'},
                  {u'filename': u'ogg0m406-kb27-20160531-0063-e90.fits',
                   u'headers': u'https://archive-api.lcogt.net/frames/4029372/headers/',
                   u'id': 4029372,
                   u'url': u'https://s3-us-west-2.amazonaws.com/archive.lcogt.net/e00c/ogg0m406-kb27-20160531-0063-e90'},
                  {u'filename': u'ogg0m406-kb27-20160531-0063-e00.fits.fz',
                   u'headers': u'https://archive-api.lcogt.net/frames/4028223/headers/',
                   u'id': 4028223,
                   u'url': u'https://s3-us-west-2.amazonaws.com/archive.lcogt.net/bbd6/ogg0m406-kb27-20160531-0063-e00'},
                 ]
    return images, len(images)

# Authentication/login related mocks


def mock_odin_login(username, password):
    return {}


def mock_lco_authenticate(request, username, password):
    return None


def mock_lco_login(email, password, request=None):
    profile = {'username': 'bart',
    'first_name': 'Bart',
    'last_name': 'Simpson',
    'email': 'bsimpson@lcogt.net',
    'id': 24,
    'userprofile': {'user_title': 'Mx',
        'onsky': False,
        'institution_name': 'LCOGT',
        'timezone': 'UTC'}
    }
    proposals = [{'allocation': [
            {'semester_code': '2015B',
            'std_allocation': 100.0,
            'telescope_class': '1m0',
            'too_allocation': 0.0,
            'too_time_used': 0.0,
            'std_time_used': 0.02},
            {'semester_code': '2015B',
            'std_allocation': 100.0,
            'telescope_class': '2m0',
            'too_allocation': 0.0,
            'too_time_used': 0.0,
            'std_time_used': 1.57055555555556}],
        'code': 'LCO2015A-009',
        'id': 4,
        'name': 'LCOGT NEO Follow-up Network'}
        ]
    return profile, proposals

# Data download/processing mocks


def mock_archive_frame_header(archive_headers):
    header = { "data": {
                    "DATE_OBS": "2016-06-01T09:43:28.067",
                    "ENCID": "clma",
                    "SITEID" : "lsc",
                    "TELID" : "1m0a",
                    "FILTER": "rp",
                    "OBJECT": 'Test obj',
                    "INSTRUME" : "kb27",
                    "ORIGNAME" : "ogg0m406-kb27-20160531-0063-e00",
                    "EXPTIME" : "200.0",
                    "GROUPID" : "TEMP",
                    "BLKUID"  : "999999"
            }
        }
    return header


def mock_archive_spectra_header(archive_headers):
    if '/7/' in archive_headers:
        header = {"data": {
            "DATE_OBS": "2019-07-27T15:52:19.512",
            "DAY_OBS": "20190727",
            "ENCID": "clma",
            "SITEID": "coj",
            "TELID": "2m0a",
            "OBJECT": "HD 30455",
            "REQNUM": "1878697"
                }
            }
    else:
        header = { "data": {
                        "DATE_OBS": "2019-07-27T15:52:19.512",
                        "DAY_OBS" : "20190727",
                        "ENCID" : "clma",
                        "SITEID" : "coj",
                        "TELID" : "2m0a",
                        "OBJECT" : "455432",
                        "REQNUM" : "1878696"
                            }
                 }
    return header


def mock_find_images_for_block(blockid):
    data = ([{'img': '1'}, {'img': '2'}, ], [{'coords': [{'y': 1086.004, 'x': 1278.912}, {'y': 1086.047, 'x': 1278.9821}], 'id': '15'}], 2028, 2028)
    return data


def mock_fetch_observations(tracking_num):
    images = ['1', '2', '3']
    return images


def mock_run_sextractor_make_catalog(configs_dir, dest_dir, fits_file):

    return -1, None


class MockCandidate(object):

    def __init__(cls, id=None, block=None, cand_id=None):
        pass

    @classmethod
    def unpack_dets(cls):
        detections = [ (1, 1, 308, 2457652.799609, 22.753496, -21.67525, 1278.9119873046875, 1086.0040283203125, 21.280000686645508, 1.190000057220459, 1.0110000371932983, -37.599998474121094, 0.019999999552965164, 3.7699999809265137, 1, 2.130000114440918, 0.1979999989271164, 41.400001525878906, 4.599999904632568, 4.5),
       (1, 2, 321, 2457652.80265, 22.753466, -21.67479, 1278.9820556640625, 1086.0469970703125, 21.06999969482422, 1.2999999523162842, 1.0770000219345093, 42.79999923706055, 0.019999999552965164, 3.890000104904175, 1, 2.130000114440918, 0.1979999989271164, 41.400001525878906, 4.599999904632568, 4.5)]
        return detections


# Submission-related mocks

def mock_fetch_filter_list(site, spec):

    siteid, encid, telid = MPC_site_code_to_domes(site)

    lsc_1m_rsp = {
                        "count": 1,
                        "next": 'null',
                        "previous": 'null',
                        "results": [
                            {
                                "id": 92,
                                "code": "fa15",
                                "state": "SCHEDULABLE",
                                "telescope": "http://configdb.lco.gtn/telescopes/10/",
                                "science_camera": {
                                    "id": 93,
                                    "code": "fa15",
                                    "camera_type": {
                                        "id": 3,
                                        "name": "1.0 meter Sinistro",
                                        "code": "1m0-SciCam-Sinistro",
                                    },
                                    "filters": "I,R,U,w,Y,up,air,rp,ip,gp,zs,V,B,ND,400um-Pinhole,150um-Pinhole",
                                    "host": "inst.1m0a.doma.lsc.lco.gtn"
                                },
                                "__str__": "lsc.doma.1m0a.fa15-ef06"
                            }
                        ]
                    }
    all_2m_rsp = {
                        "count": 2,
                        "next": 'null',
                        "previous": 'null',
                        "results": [
                            {
                                "id": 40,
                                "code": "floyds01",
                                "state": "SCHEDULABLE",
                                "telescope": "http://configdb.lco.gtn/telescopes/14/",
                                "science_camera": {
                                    "id": 17,
                                    "code": "floyds01",
                                    "camera_type": {
                                        "name": "2.0 meter FLOYDS",
                                        "code": "2m0-FLOYDS-SciCam",
                                    },
                                    "filters": "slit_6.0as,slit_1.6as,slit_2.0as,slit_1.2as",
                                    "host": "floyds.ogg.lco.gtn"
                                },
                                "__str__": "ogg.clma.2m0a.floyds01-kb42"
                            },
                            {
                                "id": 7,
                                "code": "fs01",
                                "state": "SCHEDULABLE",
                                "telescope": "http://configdb.lco.gtn/telescopes/3/",
                                "science_camera": {
                                    "id": 19,
                                    "code": "fs01",
                                    "camera_type": {
                                        "name": "2.0 meter Spectral",
                                        "code": "2m0-SciCam-Spectral",
                                    },
                                    "filters": "D51,H-Beta,OIII,H-Alpha,Skymapper-VS,solar,Astrodon-UV,I,R,Y,up,air,rp,ip,gp,zs,V,B,200um-Pinhole",
                                    "host": "fs.coj.lco.gtn"
                                },
                                "__str__": "coj.clma.2m0a.fs01-kb34"
                            }
                        ]
                    }

    empty = {
                        "count": 0,
                        "next": 'null',
                        "previous": 'null',
                        "results": []
                    }

    if '2m0' in telid.lower():
        resp = all_2m_rsp
    elif '1m0' in telid.lower() or '0m4' in telid.lower():
        resp = lsc_1m_rsp
    else:
        resp = empty

    out_data = parse_filter_file(resp, spec)
    return out_data


def mock_fetch_filter_list_no2m(site, spec):

    return []


def mock_expand_cadence(user_request):

    location = user_request['requests'][0]['location']
    cadence_params = user_request['requests'][0]['cadence']
    config = user_request['requests'][0]['configurations']
    target = config[0]['target']
    ipp = user_request['ipp_value']
    group_name = user_request['name']

    cadence = { 'name': group_name,
                'proposal': 'LCOSchedulerTest',
                'ipp_value': ipp,
                'operator': 'MANY',
                'observation_type': 'NORMAL',
                'requests':  [{
                    'location': location,
                    'configurations': [{
                        'constraints': {
                            'max_airmass': 2.0,
                            'min_lunar_distance': 30.0
                        },
                        'instrument_configs': [{
                            'optical_elements': {
                                'filter': 'w'
                            },
                            'exposure_time': 2.0,
                            'exposure_count': 10,
                            'bin_x': 1,
                            'bin_y': 1
                        }],
                        'target': target,
                        'instrument_type': '0M4-SCICAM-SBIG',
                        'type': 'EXPOSE',
                        'priority': 1
                    }],
                    'windows': [{
                        'start': '2019-11-01T00:00:00Z',
                        'end': '2019-11-01T00:30:00Z'
                    }],
                },
                    {'location': location,
                        'configurations': [{
                            'constraints': {
                                'max_airmass': 2.0,
                                'min_lunar_distance': 30.0
                            },
                            'instrument_configs': [{
                                'optical_elements': {
                                    'filter': 'w'
                                },
                                'exposure_time': 2.0,
                                'exposure_count': 10,
                                'bin_x': 1,
                                'bin_y': 1
                              }],
                            'target': target,
                            'instrument_type': '0M4-SCICAM-SBIG',
                            'type': 'EXPOSE',
                            'priority': 1
                        }],
                        'windows': [{
                            'start': '2019-11-01T01:30:00Z',
                            'end': '2019-11-01T02:30:00Z'
                            }],
                    }, {
                        'location': location,
                        'configurations': [{
                            'constraints': {
                                'max_airmass': 2.0,
                                'min_lunar_distance': 30.0
                            },
                            'instrument_configs': [{
                                'optical_elements': {
                                    'filter': 'w'
                                },
                                'exposure_time': 2.0,
                                'exposure_count': 10,
                                'bin_x': 1,
                                'bin_y': 1
                            }],
                            'target': target,
                            'instrument_type': '0M4-SCICAM-SBIG',
                            'type': 'EXPOSE',
                            'priority': 1
                        }],
                        'windows': [{
                            'start': '2019-11-01T03:30:00Z',
                            'end': '2019-11-01T04:30:00Z'
                        }],
                    }]
                }
    return True, cadence


def mock_fetch_sfu(sfu_value=None):
    if sfu_value is None:
        sfu = u.def_unit(['sfu', 'solar flux unit'], 10000.0*u.Jy)
        sfu_value = 42.0 * sfu

    return datetime(2018, 4, 20, 5, 0, 0), sfu_value


def mock_submit_to_scheduler(elements, params):
    return -42, params


def mock_update_elements_with_findorb(source_dir, dest_dir, filename, site_code, start_time):

    if filename.lower() == 'i_am_broken':
        elements_or_status = 255
    else:
        if start_time == datetime(2015, 11, 19):
            not_seen_td = datetime.utcnow()-datetime(2015,11,19)
            not_seen = not_seen_td.total_seconds() / 86400.0
            elements = {
                            'abs_mag' : 21.91,
                            'slope' : 0.15,
                            'active' : True,
                            'origin' : 'M',
                            'source_type' : 'U',
                            'elements_type' : 'MPC_MINOR_PLANET',
                            'provisional_name' : 'P10pqB2',
                            'epochofel' : datetime(2015, 11, 20),
                            'meananom' : 272.51789,
                            'argofperih' : 339.46072,
                            'longascnode' : 197.07906,
                            'orbinc' : 10.74064,
                            'eccentricity' :  0.3006186,
                            'meandist' :  1.1899499,
                            'arc_length' : 22.5/24.0,
                            'num_obs' : 9,
                            'not_seen' : not_seen,
                            'orbit_rms' : 0.10,
                            'update_time' : datetime.utcnow()
                        }
        else:
            not_seen_td = datetime.utcnow()-datetime(2015,11,18)
            not_seen = not_seen_td.total_seconds() / 86400.0
            elements = {
                            'abs_mag' : 21.91,
                            'slope' : 0.15,
                            'active' : True,
                            'origin' : 'M',
                            'source_type' : 'U',
                            'elements_type' : 'MPC_MINOR_PLANET',
                            'provisional_name' : 'P10pqB2',
                            'epochofel' : datetime(2015, 11, 18),
                            'meananom' : 270.89733,
                            'argofperih' : 339.47051,
                            'longascnode' : 197.11047,
                            'orbinc' : 10.74649,
                            'eccentricity' :  0.3001867,
                            'meandist' :  1.1896136,
                            'arc_length' : 22.5/24.0,
                            'num_obs' : 9,
                            'not_seen' : not_seen,
                            'orbit_rms' : 0.10,
                            'update_time' : datetime.utcnow()
                        }
        elements_or_status = elements
        ephem_filename = os.path.join(dest_dir, 'new.ephem')
        with open(ephem_filename, 'w') as f:
            print("#(Z21) Tenerife-LCO Aqawan A #1: P10pqB2", file=f)
            print("Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  '/hr    PA   \" sig PA", file=f)
            print("---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---", file=f)
            print("2015 11 19 00:00  03 41 05.068   -08 33 34.43  .32187 1.2819 152.1 21.1   2.25 219.1  3.16  35", file=f)
            print("2015 11 19 00:30  03 41 02.195   -08 34 26.80  .32182 1.2818 152.1 21.1   2.25 219.2  3.24  34", file=f)
            print("2015 11 19 01:00  03 40 59.317   -08 35 19.10  .32176 1.2817 152.1 21.1   2.25 219.2  3.33  33", file=f)
            print("2015 11 19 01:30  03 40 56.439   -08 36 11.33  .32171 1.2816 152.1 21.1   2.25 219.3  3.42  32", file=f)

    return elements_or_status


def mock_update_elements_with_findorb_badrms(source_dir, dest_dir, filename, site_code, start_time):

    not_seen_td = datetime.utcnow()-datetime(2015, 11, 18)
    not_seen = not_seen_td.total_seconds() / 86400.0
    elements = {
                    'abs_mag' : 21.91,
                    'slope' : 0.15,
                    'active' : True,
                    'origin' : 'M',
                    'source_type' : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'provisional_name' : 'P10pqB2',
                    'epochofel' : datetime(2015, 11, 18),
                    'meananom' : 270.89733,
                    'argofperih' : 339.47051,
                    'longascnode' : 197.11047,
                    'orbinc' : 10.74649,
                    'eccentricity' :  0.3001867,
                    'meandist' :  1.1896136,
                    'arc_length' : 22.5/24.0,
                    'num_obs' : 9,
                    'not_seen' : not_seen,
                    'orbit_rms' : 1.0,
                    'update_time' : datetime.utcnow()
                }
    elements_or_status = elements

    ephem_filename = os.path.join(dest_dir, 'new.ephem')
    with open(ephem_filename, 'w') as f:
        print("#(Z21) Tenerife-LCO Aqawan A #1: P10pqB2", file=f)
        print("Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  '/hr    PA   \" sig PA", file=f)
        print("---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---", file=f)
        print("2015 11 19 00:00  03 41 05.068   -08 33 34.43  .32187 1.2819 152.1 21.1   2.25 219.1  3.16  35", file=f)
        print("2015 11 19 00:30  03 41 02.195   -08 34 26.80  .32182 1.2818 152.1 21.1   2.25 219.2  3.24  34", file=f)

    return elements_or_status


def mock_update_elements_with_findorb_badepoch(source_dir, dest_dir, filename, site_code, start_time):

    not_seen_td = datetime.utcnow()-datetime(2015, 11, 18)
    not_seen = not_seen_td.total_seconds() / 86400.0
    elements = {
                    'abs_mag' : 21.91,
                    'slope' : 0.15,
                    'active' : True,
                    'origin' : 'M',
                    'source_type' : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'provisional_name' : 'P10pqB2',
                    'epochofel' : datetime(2013, 11, 16),
                    'meananom' : 269.48064,
                    'argofperih' : 339.46074,
                    'longascnode' : 197.07906,
                    'orbinc' : 10.74064,
                    'eccentricity' :  0.3006183,
                    'meandist' :  1.1899464,
                    'arc_length' : 22.5/24.0,
                    'num_obs' : 9,
                    'not_seen' : not_seen,
                    'orbit_rms' : 0.10,
                    'update_time' : datetime.utcnow()
                }
    elements_or_status = elements

    ephem_filename = os.path.join(dest_dir, 'new.ephem')
    with open(ephem_filename, 'w') as f:
        print("#(T03) Haleakala-LCO Clamshell #3: P10pqB2", file=f)
        print("Date (UTC) HH:MM   RA              Dec         delta   r     elong  mag  '/hr    PA   \" sig PA", file=f)
        print("---- -- -- -----  -------------   -----------  ------ ------ -----  --- ------ ------ ---- ---", file=f)
        print("2015 11 19 00:00  03 41 05.422   -08 33 24.33  .32194 1.2819 152.1 21.1   2.13 214.8  3.45  34", file=f)
        print("2015 11 19 00:30  03 41 02.956   -08 34 16.84  .32189 1.2818 152.1 21.1   2.14 214.9  3.62  35", file=f)

    return elements_or_status


def mock_build_visibility_source(body, site_list, site_code, color_list, d, alt_limit, step_size):
    vis = {'x': [0, 0, 0, 0, 0, 0],
           'y': [0, 0, 0, 0, 0, 0],
           'sun_rise': [3.7823567876644617, 2.167927229569707, 6.225817740456523, 4.56775495106191, 3.0405918555668716, 5.440419577059075],
           'sun_set': [1.469795528771975, -0.1446340293227797, 3.9132564815640363, 1.8624946104706992, 0.3353315149756608, 2.778792467767722],
           'obj_rise': [0.8152970592741018, 5.3967863457592165, 3.1714915494664453, 1.9933943043702742, 6.705783284754963, 2.6478927738681475],
           'obj_set': [2.909692161667297, 7.622081142051987, 5.396786345759216, 2.647892773868148, 7.491181448152411, 3.82599001896432],
           'moon_rise': [1.9634954084936211, 0.26179938779914913, 4.319689898685965, 2.4870941840919194, 0.9162978572970228, 3.1415926535897927],
           'moon_set': [4.188790204786391, 2.4870941840919194, 6.544984694978735, 4.71238898038469, 3.141592653589793, 5.890486225480862],
           'moon_phase': [0.9845098575723441, 0.9865640543741148, 0.9870247356841624, 0.984547400308345, 0.9855244584496232, 0.9855361594868062],
           'colors': ['darkviolet', 'forestgreen', 'saddlebrown', 'coral', 'darkslategray', 'dodgerblue'],
           'site': ['LSC', 'CPT', 'COJ', 'ELP', 'TFN', 'OGG'],
           'obj_vis': [5.5, 5.5, 5.5, 2.5, 3.0, 4.0],
           'max_alt': [84, 83, 84, 33, 36, 43]}
    emp = [['2019 10 15 02:00', '22 01 28.18', '-25 38 42.1', '21.7', ' 0.85', ' 72.9', '+5', '0.98', ' 71', '-39', '-999', '-04:54'],
           ['2019 10 15 02:30', '22 01 29.97', '-25 38 34.7', '21.7', ' 0.84', ' 72.7', '+11', '0.98', ' 71', '-33', '-999', '-04:24'],
           ['2019 10 15 03:00', '22 01 31.74', '-25 38 27.1', '21.7', ' 0.83', ' 72.3', '+16', '0.98', ' 71', '-27', '-999', '-03:54'],
           ['2019 10 15 03:30', '22 01 33.49', '-25 38 19.5', '21.7', ' 0.83', ' 72.0', '+22', '0.98', ' 72', '-20', '-999', '-03:24']]

    return vis, emp
