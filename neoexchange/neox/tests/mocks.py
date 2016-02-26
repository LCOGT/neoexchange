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

def mock_check_request_status(tracking_num):
    status = {  "title": "WT1190F_W86-20151022",
                "timestamp": "2015-10-22 18:04:25",
                "tracking_number": str(tracking_num),
                "state": "COMPLETED",
                "requests": {
                    "0000445739": {
                        "schedule": [
                            {
                                "end": "2015-10-22 07:30:37",
                                "telescope": "1m0a.domb.lsc",
                                "start": "2015-10-22 07:09:29",
                                "state": "COMPLETED",
                                "frames": [],
                                "id": 70243611,
                            }
                        ],
                        "timestamp": "2015-10-22 18:04:26",
                        "state": "COMPLETED",
                        "request_number": "0000445739",
                    }
                }
            }
    return status

def mock_check_request_status_null(tracking_num):
    return []

def mock_check_for_images(eventid):
    images = [{"propid":"LCO2015B-005",
                "date_obs":"2015-10-22 07:35:41",
                "origname":"file0.fits",
                "hdrver":"LCOGT-HDR-1.3.0"},
            {"propid":"LCO2015B-005",
            "date_obs":"2015-10-22 07:34:41",
            "origname":"file1.fits",
            "hdrver":"LCOGT-HDR-1.3.0"},
            {"propid":"LCO2015B-005",
            "date_obs":"2015-10-22 07:33:41",
            "origname":"file2.fits",
            "hdrver":"LCOGT-HDR-1.3.0"}]
    return images

def mock_check_for_2_images(eventid):
    images = [{"propid":"LCO2015B-005",
                "date_obs":"2015-10-22 07:35:41",
                "origname":"file0.fits",
                "hdrver":"LCOGT-HDR-1.3.0"},
            {"propid":"LCO2015B-005",
            "date_obs":"2015-10-22 07:34:41",
            "origname":"file1.fits",
            "hdrver":"LCOGT-HDR-1.3.0"}]
    return images

def mock_check_for_images_millisecs(eventid):
    images = [{"propid":"LCO2015B-005",
                "date_obs":"2015-10-22 07:35:41.789",
                "origname":"file0.fits",
                "hdrver":"LCOGT-HDR-1.3.0"},
            {"propid":"LCO2015B-005",
            "date_obs":"2015-10-22 07:34:41.789",
            "origname":"file1.fits",
            "hdrver":"LCOGT-HDR-1.3.0"},
            {"propid":"LCO2015B-005",
            "date_obs":"2015-10-22 07:33:41.789",
            "origname":"file2.fits",
            "hdrver":"LCOGT-HDR-1.3.0"}]
    return images

def mock_check_for_images_bad_date(eventid):
    images = [{"propid":"LCO2015B-005",
                "date_obs":"2015-10-22 07:35",
                "origname":"file0.fits",
                "hdrver":"LCOGT-HDR-1.3.0"},
            {"propid":"LCO2015B-005",
            "date_obs":"2015-10-22 07:34",
            "origname":"file1.fits",
            "hdrver":"LCOGT-HDR-1.3.0"},
            {"propid":"LCO2015B-005",
            "date_obs":"2015-10-22 07:33",
            "origname":"file2.fits",
            "hdrver":"LCOGT-HDR-1.3.0"}]
    return images

def mock_ingest_frames(images, block):
    return None

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
        'code': 'LCOTEST1',
        'id': 4,
        'name': 'Test Proposal #1'}
        ]
    return profile, proposals
