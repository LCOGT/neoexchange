from datetime import datetime as real_datetime
from datetime import datetime
import os

from django.contrib.auth import authenticate

from astrometrics.sources_subs import fetch_filter_list


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


def mock_check_request_status(tracking_num):
    status = { u'created' : u'2015-10-21T19:07:26.023049Z',
                u'group_id' : u'Fake group',
                u'id': 42,
                u'ipp_value': 1.0,
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
             u'group_id': u'3122_COJ_cad_20170816-0819',
             u'id': 472636,
             u'ipp_value': 1.0,
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
    elif archive_url.rfind("OBSTYPE=") > 0:
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

def mock_fetch_filter_list(site):
    test_filter_map = os.path.join('astrometrics', 'tests', 'test_camera_mapping.dat')

    return fetch_filter_list(site, test_filter_map)

def mock_expand_cadence(user_request):

    cadence = {
                 u'group_id': u'3122_Q59-20170815',
                 u'ipp_value': 1.0,
                 u'observation_type': u'NORMAL',
                 u'operator': u'MANY',
                 u'proposal': u'LCOSchedulerTest',
                 u'requests': [{u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                   u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                   u'molecules': [{u'ag_mode': u'OPTIONAL',
                     u'ag_name': u'',
                     u'bin_x': 2,
                     u'bin_y': 2,
                     u'exposure_count': 10,
                     u'exposure_time': 2.0,
                     u'filter': u'w',
                     u'instrument_name': u'0M4-SCICAM-SBIG',
                     u'priority': 1,
                     u'type': u'EXPOSE'}],
                   u'target': {u'argofperih': 27.8469,
                    u'eccentricity': 0.4233003,
                    u'epochofel': 58000.0,
                    u'longascnode': 336.0952,
                    u'meananom': 351.43854,
                    u'meandist': 1.7691326,
                    u'name': u'3122',
                    u'orbinc': 22.1508,
                    u'scheme': u'MPC_MINOR_PLANET',
                    u'type': u'NON_SIDEREAL'},
                   u'windows': [{u'end': u'2017-09-02T06:07:30Z',
                     u'start': u'2017-09-02T06:00:00Z'}]},
                  {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                   u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                   u'molecules': [{u'ag_mode': u'OPTIONAL',
                     u'ag_name': u'',
                     u'bin_x': 2,
                     u'bin_y': 2,
                     u'exposure_count': 10,
                     u'exposure_time': 2.0,
                     u'filter': u'w',
                     u'instrument_name': u'0M4-SCICAM-SBIG',
                     u'priority': 1,
                     u'type': u'EXPOSE'}],
                   u'target': {u'argofperih': 27.8469,
                    u'eccentricity': 0.4233003,
                    u'epochofel': 58000.0,
                    u'longascnode': 336.0952,
                    u'meananom': 351.43854,
                    u'meandist': 1.7691326,
                    u'name': u'3122',
                    u'orbinc': 22.1508,
                    u'scheme': u'MPC_MINOR_PLANET',
                    u'type': u'NON_SIDEREAL'},
                   u'windows': [{u'end': u'2017-09-02T08:07:30Z',
                     u'start': u'2017-09-02T07:52:30Z'}]},
                  {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                   u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                   u'molecules': [{u'ag_mode': u'OPTIONAL',
                     u'ag_name': u'',
                     u'bin_x': 2,
                     u'bin_y': 2,
                     u'exposure_count': 10,
                     u'exposure_time': 2.0,
                     u'filter': u'w',
                     u'instrument_name': u'0M4-SCICAM-SBIG',
                     u'priority': 1,
                     u'type': u'EXPOSE'}],
                   u'target': {u'argofperih': 27.8469,
                    u'eccentricity': 0.4233003,
                    u'epochofel': 58000.0,
                    u'longascnode': 336.0952,
                    u'meananom': 351.43854,
                    u'meandist': 1.7691326,
                    u'name': u'3122',
                    u'orbinc': 22.1508,
                    u'scheme': u'MPC_MINOR_PLANET',
                    u'type': u'NON_SIDEREAL'},
                   u'windows': [{u'end': u'2017-09-02T10:07:30Z',
                     u'start': u'2017-09-02T09:52:30Z'}]},
                  {u'constraints': {u'max_airmass': 2.0, u'min_lunar_distance': 15.0},
                   u'location': {u'site': u'ogg', u'telescope_class': u'0m4'},
                   u'molecules': [{u'ag_mode': u'OPTIONAL',
                     u'ag_name': u'',
                     u'bin_x': 2,
                     u'bin_y': 2,
                     u'exposure_count': 10,
                     u'exposure_time': 2.0,
                     u'filter': u'w',
                     u'instrument_name': u'0M4-SCICAM-SBIG',
                     u'priority': 1,
                     u'type': u'EXPOSE'}],
                   u'target': {u'argofperih': 27.8469,
                    u'eccentricity': 0.4233003,
                    u'epochofel': 58000.0,
                    u'longascnode': 336.0952,
                    u'meananom': 351.43854,
                    u'meandist': 1.7691326,
                    u'name': u'3122',
                    u'orbinc': 22.1508,
                    u'scheme': u'MPC_MINOR_PLANET',
                    u'type': u'NON_SIDEREAL'},
                   u'windows': [{u'end': u'2017-09-02T12:07:30Z',
                     u'start': u'2017-09-02T11:52:30Z'}]}],
                 u'submitter': u'tlister@lcogt.net'}
    return True, cadence
