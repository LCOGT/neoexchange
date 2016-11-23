from datetime import datetime as real_datetime
from datetime import datetime

# Adapted from http://www.ryangallen.com/wall/11/mock-today-django-testing/
# and changed to datetime and python 2.x

class MockDateTimeType(type):

    def __init__(cls, name, bases, d):
        type.__init__(cls, name, bases, d)
        cls.year = 2015
        cls.month =  4
        cls.day = 1
        cls.hour = 17
        cls.minute = 0
        cls.second = 0

    def __instancecheck__(self, instance):
        return isinstance(instance, real_datetime)


class MockDateTime(datetime):

    __metaclass__ = MockDateTimeType

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

def mock_check_request_status(headers, tracking_num):
    status = [{'constraints': [{'id': 611796, 'request': 617292}],
             'end_time': '2015-10-22 07:30:37',
             'fail_count': 0,
             'locations': [{'observatory': None,
               'site': 'lsc',
               'telescope': None,
               'telescope_class': '1m0'}],
             'molecules': [{'acquire_mode': 'WCS',
               'bin_x': 2,
               'exposure_count': 1,
               'exposure_time': 300.0,
               'filter': 'B',
               'id': 1001945,
               'instrument_name': '1M0-SCICAM-SBIG',
               'priority': 1,
               'request': 617292,
               'type': 'EXPOSE'},
              ],
             'proposal_id': 'LCOEPO2014B-XXX',
             'request_number': '0000445739',
             'start_time': '2015-10-22 07:09:29',
             'targets': [{'acquire_mode': 'OPTIONAL',
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
               'type': 'SIDEREAL'}],
             'windows': [{'end': '2015-10-22T09:00:00',
               'start': '2015-10-22T07:00:00'}]
             }]
    return status


def mock_check_request_status_null(headers, tracking_num):
    return []

def mock_check_request_status_notfound(headers, tracking_num):
    return {u'detail': u'Not found.'}

def mock_check_for_images_no_millisecs(auth_header, request_id):
    header = { "data": {
                    "DATE_OBS": "2016-06-01T09:43:28",
                    "ENCID": "clma",
                    "SITEID":"lsc",
                    "TELID":"1m0a",
                    "FILTER": "rp",
                    "INSTRUME" : "kb27",
                    "ORIGNAME" : "ogg0m406-kb27-20160531-0063-e00",
                    "EXPTIME" : "200.0"
            }
        }
    return header

def mock_check_for_images_bad_date(auth_header, request_id):
    header = { "data": {
                    "DATE_OBS": "2016-06-01T09:43",
                    "ENCID": "clma",
                    "SITEID":"lsc",
                    "TELID":"1m0a",
                    "FILTER": "rp",
                    "INSTRUME" : "kb27",
                    "ORIGNAME" : "ogg0m406-kb27-20160531-0063-e00",
                    "EXPTIME" : "200.0"
            }
        }
    return header

def mock_ingest_frames(images, block):
    return ['99999']

def mock_rbauth_login(email, password, request=None):
    profile = {'username': 'bsimpson',
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

def mock_check_for_images(auth_header, request_id):
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
    return images

def mock_archive_frame_header(archive_headers, images):
    header = { "data": {
                    "DATE_OBS": "2016-06-01T09:43:28.067",
                    "ENCID": "clma",
                    "SITEID":"lsc",
                    "TELID":"1m0a",
                    "FILTER": "rp",
                    "INSTRUME" : "kb27",
                    "ORIGNAME" : "ogg0m406-kb27-20160531-0063-e00",
                    "EXPTIME" : "200.0",
                    "GROUPID" : "TEMP",
                    "BLKUID"  : "999999"
            }
        }
    return header

def mock_odin_login(username, password):
    return {}

def mock_fetch_observations(tracking_num):
    images = ['1','2','3']
    return images
