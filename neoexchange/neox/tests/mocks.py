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
    status = {'created' : '2015-10-21T19:07:26.023049Z',
              'id': 42,
              'name': 'Fake group',
              'observation_type': 'NORMAL',
              'operator': 'SINGLE',
              'ipp_value': 1.05,
              'modified': '2015-10-21T19:07:26.023049Z',
              'proposal': 'LCOEPO2014B-XXX',
              'requests': [{
                 'id': 611796,
                 'location': {'site': 'lsc', 
                              'telescope_class': '1m0'},
                 'configurations': [{
                    'id': 3260058,
                    'constraints': {'max_airmass': 1.74,
                                    'min_lunar_distance': 30.0,
                                    'max_lunar_phase': None,
                                    'max_seeing': None,
                                    'min_transparency': None,
                                    'extra_params': {}
                                   },
                    'instrument_configs': [{'optical_elements': {'filter': 'B'},
                                            'mode': 'default',
                                            'exposure_time': 300.0,
                                            'exposure_count': 1,
                                            'bin_x': 1,
                                            'bin_y': 1,
                                            'rotator_mode': '',
                                            'extra_params': {}
                                          }],
                    'acquisition_config': { 'mode': 'OFF',
                                            'exposure_time': None,
                                            'extra_params': {}
                                          },
                    'guiding_config': { 'optional': True,
                                        'mode': 'ON',
                                        'optical_elements': {},
                                        'exposure_time': None,
                                        'extra_params': {}
                                       },
                    'target': { 'type': 'ORBITAL_ELEMENTS',
                                'name': '481394',
                                'epochofel': 58779.0,
                                'orbinc': 5.86664,
                                'longascnode': 228.05421,
                                'eccentricity': 0.2805321,
                                'scheme': 'MPC_MINOR_PLANET',
                                'argofperih': 305.65638,
                                'meandist': 0.9493052,
                                'meananom': 243.67012,
                                'extra_params': {}
                              },
                    'instrument_type': '1M0-SCICAM-SINISTRO',
                    'type': 'EXPOSE',
                    'extra_params': {},
                    'priority': 1}],
                  'windows': [{'start': '2015-10-22T07:00:00',
                               'end': '2015-10-22T09:00:00Z'
                             }],
                  'duration': 1317,
                  'observation_note': 'Submitted by NEOexchange (by fakeperson@fakeout.net)',
                  'state': 'PENDING',
                  'modified': '2015-10-24T04:12:39.580780Z',
                  'created': '2015-10-21T16:46:56.934774Z',
                  'acceptability_threshold': 90.0}],
              'state': 'PENDING',
              'submitter': 'fakeperson@fakeout.net',
            }
    return status

def mock_check_request_status_cadence(tracking_num):

    status = {'id': 879054,
              'requests': [
                  {
                  'id': 1969385,
                  'location': {'telescope_class': '0m4'},
                  'configurations': [{
                      'id': 3299788,
                      'constraints': {'max_airmass': 2.0,
                                      'min_lunar_distance': 30.0,
                                      'max_lunar_phase': None,
                                      'max_seeing': None,
                                      'min_transparency': None,
                                      'extra_params': {}
                                     },
                      'instrument_configs': [{'optical_elements': {'filter': 'rp'},
                                              'mode': 'default',
                                              'exposure_time': 220.0,
                                              'exposure_count': 4,
                                              'bin_x': 1,
                                              'bin_y': 1,
                                              'rotator_mode': '',
                                              'extra_params': {}
                                            }],
                      'acquisition_config': { 'mode': 'OFF',
                                              'exposure_time': None,
                                              'extra_params': {}
                                            },
                      'guiding_config': { 'optional': True,
                                          'mode': 'ON',
                                          'optical_elements': {},
                                          'exposure_time': None,
                                          'extra_params': {}
                                        },
                      'target': { 'type': 'ORBITAL_ELEMENTS',
                                  'name': '29P',
                                  'epochofel': 58560.0,
                                  'orbinc': 9.36833,
                                  'longascnode': 312.39454,
                                  'eccentricity': 0.0430316,
                                  'scheme': 'MPC_COMET',
                                  'argofperih': 47.77452,
                                  'perihdist': 5.7668222,
                                  'epochofperih': 58549.75763,
                                  'extra_params': {}
                                },
                      'instrument_type': '0M4-SCICAM-SBIG',
                      'type': 'EXPOSE',
                      'extra_params': {},
                      'priority': 1}],
                  'windows': [{ 'start': '2019-11-01T04:00:00Z',
                                'end': '2019-11-01T12:00:00Z'}],
                  'duration': 1044,
                  'observation_note': '',
                  'state': 'COMPLETED',
                  'modified': '2019-11-01T10:14:48.565793Z',
                  'created': '2019-10-31T22:58:57.507939Z',
                  'acceptability_threshold': 90.0
                  },
                  {
                  'id': 1969386,
                  'location': {'telescope_class': '0m4'},
                  'configurations': [{
                      'id': 3299789,
                      'constraints': {'max_airmass': 2.0,
                                      'min_lunar_distance': 30.0,
                                      'max_lunar_phase': None,
                                      'max_seeing': None,
                                      'min_transparency': None,
                                      'extra_params': {}
                                     },
                      'instrument_configs': [{'optical_elements': {'filter': 'rp'},
                                              'mode': 'default',
                                              'exposure_time': 220.0,
                                              'exposure_count': 4,
                                              'bin_x': 1,
                                              'bin_y': 1,
                                              'rotator_mode': '',
                                              'extra_params': {}
                                            }],
                      'acquisition_config': { 'mode': 'OFF',
                                              'exposure_time': None,
                                              'extra_params': {}
                                            },
                      'guiding_config': { 'optional': True,
                                          'mode': 'ON',
                                          'optical_elements': {},
                                          'exposure_time': None,
                                          'extra_params': {}
                                        },
                      'target': { 'type': 'ORBITAL_ELEMENTS',
                                  'name': '29P',
                                  'epochofel': 58560.0,
                                  'orbinc': 9.36833,
                                  'longascnode': 312.39454,
                                  'eccentricity': 0.0430316,
                                  'scheme': 'MPC_COMET',
                                  'argofperih': 47.77452,
                                  'perihdist': 5.7668222,
                                  'epochofperih': 58549.75763,
                                  'extra_params': {}
                                },
                      'instrument_type': '0M4-SCICAM-SBIG',
                      'type': 'EXPOSE',
                      'extra_params': {},
                      'priority': 1}],
                  'windows': [{ 'start': '2019-11-02T04:00:00Z',
                                'end': '2019-11-02T12:00:00Z'}],
                  'duration': 1044,
                  'observation_note': '',
                  'state': 'COMPLETED',
                  'modified': '2019-11-02T10:21:57.881448Z',
                  'created': '2019-10-31T22:58:57.522085Z',
                  'acceptability_threshold': 90.0
                  },
                  {
                  'id': 1969387,
                  'location': {'telescope_class': '0m4'},
                  'configurations': [{
                      'id': 3299790,
                      'constraints': {'max_airmass': 2.0,
                                      'min_lunar_distance': 30.0,
                                      'max_lunar_phase': None,
                                      'max_seeing': None,
                                      'min_transparency': None,
                                      'extra_params': {}
                                     },
                      'instrument_configs': [{'optical_elements': {'filter': 'rp'},
                                              'mode': 'default',
                                              'exposure_time': 220.0,
                                              'exposure_count': 4,
                                              'bin_x': 1,
                                              'bin_y': 1,
                                              'rotator_mode': '',
                                              'extra_params': {}
                                            }],
                      'acquisition_config': { 'mode': 'OFF',
                                              'exposure_time': None,
                                              'extra_params': {}
                                            },
                      'guiding_config': { 'optional': True,
                                          'mode': 'ON',
                                          'optical_elements': {},
                                          'exposure_time': None,
                                          'extra_params': {}
                                        },
                      'target': { 'type': 'ORBITAL_ELEMENTS',
                                  'name': '29P',
                                  'epochofel': 58560.0,
                                  'orbinc': 9.36833,
                                  'longascnode': 312.39454,
                                  'eccentricity': 0.0430316,
                                  'scheme': 'MPC_COMET',
                                  'argofperih': 47.77452,
                                  'perihdist': 5.7668222,
                                  'epochofperih': 58549.75763,
                                  'extra_params': {}
                                },
                      'instrument_type': '0M4-SCICAM-SBIG',
                      'type': 'EXPOSE',
                      'extra_params': {},
                      'priority': 1}],
                  'windows': [{ 'start': '2019-11-03T04:00:00Z',
                                'end': '2019-11-03T12:00:00Z'}],
                  'duration': 1044,
                  'observation_note': '',
                  'state': 'COMPLETED',
                  'modified': '2019-11-03T11:09:02.071643Z',
                  'created': '2019-10-31T22:58:57.535790Z',
                  'acceptability_threshold': 90.0
                  }],
                  'submitter': 'neox_robot',
                  'name': '29P_0M4-cad-20191031-1104',
                  'observation_type': 'NORMAL',
                  'operator': 'MANY',
                  'ipp_value': 1.0,
                  'created': '2019-10-31T22:58:57.504924Z',
                  'state': 'COMPLETED',
                  'modified': '2019-11-03T11:09:02.078988Z',
                  'proposal': 'LCO2019B-023'}

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
                    "INSTRUME" : "kb27",
                    "ORIGNAME" : "ogg0m406-kb27-20160531-0063-e00",
                    "EXPTIME" : "200.0",
                    "GROUPID" : "TEMP",
                    "BLKUID"  : "999999"
            }
        }
    return header

def mock_archive_spectra_header(archive_headers):
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
