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
from datetime import date
import os

import astropy.units as u
from astropy.table import Table
from bs4 import BeautifulSoup
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


class MockDate(date, metaclass=MockDateTimeType):

    @classmethod
    def change_date(cls, year, month, day):
        cls.year = year
        cls.month = month
        cls.day = day

    @classmethod
    def today(cls):
        return cls(cls.year, cls.month, cls.day)


def mock_fetchpage_and_make_soup(url, fakeagent=False, dbg=False, parser="html.parser"):
    page = None
    if '191P' in url:
        with open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet191P.html'), 'r') as test_fh:
            page = BeautifulSoup(test_fh, "html.parser")
    else:
        logger.warning("Page retrieval failed because this is a test and no page was attempted.")
    return page


def mock_fetchpage_and_make_soup_pccp(url, fakeagent=False, dbg=False, parser="html.parser"):

        table_header = '''<table class="tablesorter">
          <thead>
            <tr>
              <th>&nbsp;&nbsp;Temp Desig&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Score&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Discovery</th>
              <th>&nbsp;&nbsp;R.A.&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;Decl.&nbsp;&nbsp;</th>
              <th>&nbsp;&nbsp;V&nbsp;&nbsp;</th>
              <th>Updated</th>
              <th>&nbsp;Note&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;NObs&nbsp;&nbsp;&nbsp;</th>
              <th>&nbsp;Arc&nbsp;&nbsp;</th>
              <th>&nbsp;H&nbsp;&nbsp;</th>
              <th>&nbsp;Not Seen/dys&nbsp;&nbsp;</th>
            </tr>
          </thead>

          <tbody>'''
        table_footer = "</tbody>\n</table>"

        html = BeautifulSoup(table_header +
                             '''
        <tr><td><span style="display:none">WR0159E</span>&nbsp;<input type="checkbox" name="obj" VALUE="WR0159E"> WR0159E</td>
        <td align="right"><span style="display:none">010</span> 10&nbsp;&nbsp;&nbsp;</td>
        <td>&nbsp;&nbsp;2015 09 13.4&nbsp;&nbsp;</td>
        <td><span style="display:none">190.5617</span>&nbsp;&nbsp;01 01.5 &nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">089.7649</span>&nbsp;&nbsp;-00 14&nbsp;&nbsp;</td>
        <td align="right"><span style="display:none">31.2</span>&nbsp;&nbsp;18.8&nbsp;&nbsp;</td>
        <td><span style="display:none">U2457294.241781</span>&nbsp;Updated Sept. 28.74 UT&nbsp;</td>
        <td align="center">&nbsp;&nbsp;</td>
        <td align="right">&nbsp; 222&nbsp;</td>
        <td align="right">&nbsp; 15.44&nbsp;</td>
        <td align="right">&nbsp;14.4&nbsp;</td>
        <td align="right">&nbsp; 0.726&nbsp;</td>
        ''' + table_footer, "html.parser")
        return html

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


# Create Mocked output to image request from Valhalla.
# Header URL and Reqnum have been changed for easy tracking.
# no images for last block
def mock_check_for_archive_images(request_id, obstype='EXPOSE', obj=''):
    result_images_out = [{u'BLKUID': 226770074,
                          u'DATE_OBS': u'2018-02-27T04:10:51.702000Z',
                          u'EXPTIME': u'10.238',
                          u'FILTER': u'w',
                          u'INSTRUME': u'kb80',
                          u'L1PUBDAT': u'2019-02-27T04:10:51.702000Z',
                          u'OBJECT': '1test_'+str(request_id),
                          u'OBSTYPE': u'EXPOSE',
                          u'PROPID': u'LCO2018A-012',
                          u'REQNUM': request_id,
                          u'RLEVEL': 91,
                          u'SITEID': u'elp',
                          u'TELID': u'0m4a',
                          u'area': {u'coordinates': [[[175.3634230138293, 73.42041723658008],
                             [176.489579845721, 73.42430056668292],
                             [176.493982451836, 72.94199402324494],
                             [175.39874986356807, 72.93821734095452],
                             [175.3634230138293, 73.42041723658008]]],
                           u'type': u'Polygon'},
                          u'basename': u'elp0m411-kb80-20180226-0077-e91',
                          u'filename': u'elp0m411-kb80-20180226-0077-e91.fits.fz',
                          u'headers': '1test_'+str(request_id),
                          u'id': request_id,
                          u'related_frames': [7203968, 8035197, 8035195, 8030893, 7986266],
                          u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/8387/elp0m411-kb80-20180226-0077-e91?versionId=zeF8aanQzLDJKXGSqhQ6kS5.wRROHUgI&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=S4R2UzFEDpeFgnIN3pVxhaBk6r4%3D&Expires=1520120748',
                          u'version_set': [{u'created': u'2018-02-27T16:16:10.482024Z',
                            u'extension': u'.fits.fz',
                            u'id': 8349661,
                            u'key': u'zeF8aanQzLDJKXGSqhQ6kS5.wRROHUgI',
                            u'md5': u'd21928112095941617fec2372384da36',
                            u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/8387/elp0m411-kb80-20180226-0077-e91?versionId=zeF8aanQzLDJKXGSqhQ6kS5.wRROHUgI&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=S4R2UzFEDpeFgnIN3pVxhaBk6r4%3D&Expires=1520120748'}]},
                         {u'BLKUID': 226770074,
                          u'DATE_OBS': u'2018-02-27T04:10:35.712000Z',
                          u'EXPTIME': u'10.237',
                          u'FILTER': u'w',
                          u'INSTRUME': u'kb80',
                          u'L1PUBDAT': u'2019-02-27T04:10:35.712000Z',
                          u'OBJECT': '2test_'+str(request_id),
                          u'OBSTYPE': u'EXPOSE',
                          u'PROPID': u'LCO2018A-012',
                          u'REQNUM': request_id,
                          u'RLEVEL': 91,
                          u'SITEID': u'elp',
                          u'TELID': u'0m4a',
                          u'area': {u'coordinates': [[[175.36244049289198, 73.42075299265626],
                             [176.48876179976844, 73.42464488204425],
                             [176.49320403467433, 72.94227739986835],
                             [175.39781591212306, 72.93849240870662],
                             [175.36244049289198, 73.42075299265626]]],
                           u'type': u'Polygon'},
                          u'basename': u'elp0m411-kb80-20180226-0076-e91',
                          u'filename': u'elp0m411-kb80-20180226-0076-e91.fits.fz',
                          u'headers': '2test_'+str(request_id),
                          u'id': 8035227,
                          u'related_frames': [7203968, 8035197, 8035195, 8030891, 7986266],
                          u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/c286/elp0m411-kb80-20180226-0076-e91?versionId=YquJyq8u_tEoCSFpVMPPM7kLzxZ0p_it&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=tuTe1RILDACBEaKFfDMtO%2Fr9iyU%3D&Expires=1520120748',
                          u'version_set': [{u'created': u'2018-02-27T16:16:05.924956Z',
                            u'extension': u'.fits.fz',
                            u'id': 2 * request_id,
                            u'key': u'YquJyq8u_tEoCSFpVMPPM7kLzxZ0p_it',
                            u'md5': u'53393c9054c33090df6710215ac72342',
                            u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/c286/elp0m411-kb80-20180226-0076-e91?versionId=YquJyq8u_tEoCSFpVMPPM7kLzxZ0p_it&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=tuTe1RILDACBEaKFfDMtO%2Fr9iyU%3D&Expires=1520120748'}]},
                        {u'BLKUID': 226770074,
                          u'DATE_OBS': u'2018-02-27T04:10:19.822000Z',
                          u'EXPTIME': u'10.237',
                          u'FILTER': u'w',
                          u'INSTRUME': u'kb80',
                          u'L1PUBDAT': u'2019-02-27T04:10:19.822000Z',
                          u'OBJECT': '3test_'+str(request_id),
                          u'OBSTYPE': u'EXPOSE',
                          u'PROPID': u'LCO2018A-012',
                          u'REQNUM': request_id,
                          u'RLEVEL': 91,
                          u'SITEID': u'elp',
                          u'TELID': u'0m4a',
                          u'area': {u'coordinates': [[[175.36112661033172, 73.42086136781433],
                             [176.48737193066208, 73.42475818787373],
                             [176.49184160850814, 72.94242630853277],
                             [175.39652536517892, 72.93863651517941],
                             [175.36112661033172, 73.42086136781433]]],
                           u'type': u'Polygon'},
                          u'basename': u'elp0m411-kb80-20180226-0075-e91',
                          u'filename': u'elp0m411-kb80-20180226-0075-e91.fits.fz',
                          u'headers': '3test_'+str(request_id),
                          u'id': 3 * request_id,
                          u'related_frames': [7203968, 8035197, 8035195, 8030887, 7986266],
                          u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/28d0/elp0m411-kb80-20180226-0075-e91?versionId=hZF3yaFjXBvVWpHhQeiYSPKLJIPeHOnD&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=FxTVEMMOT24%2FzLemz1vYennkko4%3D&Expires=1520120748',
                          u'version_set': [{u'created': u'2018-02-27T16:15:57.913799Z',
                            u'extension': u'.fits.fz',
                            u'id': 8349659,
                            u'key': u'hZF3yaFjXBvVWpHhQeiYSPKLJIPeHOnD',
                            u'md5': u'24f8ca63ef9e25915d49dd80732c1e89',
                            u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/28d0/elp0m411-kb80-20180226-0075-e91?versionId=hZF3yaFjXBvVWpHhQeiYSPKLJIPeHOnD&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=FxTVEMMOT24%2FzLemz1vYennkko4%3D&Expires=1520120748'}]}
                         ]
    if request_id == 9:
        return [], 0
    else:
        return result_images_out, 3


def mock_lco_api_fail(data_url, auth_header=None):
        return None


# Mock Header output read from Valhalla
# modified Origname for easy tracking
def mock_lco_api_call(link):
    header_out= {u'data': {u'AGCAM': u'kb80',
                          u'AGDEC': u'',
                          u'AGDX': 0.0,
                          u'AGDY': 0.0,
                          u'AGFILST': u'Enabled',
                          u'AGFILTER': u'w,',
                          u'AGFILTID': u'PSTR-WX-124,',
                          u'AGFOCDMD': u'',
                          u'AGFOCOFF': 0.0,
                          u'AGFOCST': u'',
                          u'AGFOCUS': u'',
                          u'AGFWHM': u'',
                          u'AGGMAG': u'',
                          u'AGLCKFRC': 0.0,
                          u'AGMIRDMD': u'',
                          u'AGMIRPOS': u'00.0, N/A',
                          u'AGMIRST': u'ERROR',
                          u'AGMODE': u'OFF',
                          u'AGNSRC': 0,
                          u'AGRA': u'',
                          u'AGSTATE': u'IDLE',
                          u'AIRMASS': 4.4792254,
                          u'ALTDMD': u'',
                          u'ALTITUDE': 12.6719931,
                          u'ALTSTAT': u'OKAY',
                          u'AMEND': 4.4792229,
                          u'AMPNAME': u'default',
                          u'AMSTART': 4.4792279,
                          u'AUXPITCH': 0.0,
                          u'AUXROLL': 0.0,
                          u'AZDMD': u'',
                          u'AZIMUTH': 0.0706666,
                          u'AZSTAT': u'OKAY',
                          u'BIASLVL': 1973.494791666667,
                          u'BIASSEC': u'',
                          u'BITPIX': -32,
                          u'BLKAIRCO': u'',
                          u'BLKEDATE': u'2018-02-27T00:25:41',
                          u'BLKMNDST': u'',
                          u'BLKMNPH': u'',
                          u'BLKNOMEX': 4116.0,
                          u'BLKSDATE': u'2018-02-26T23:17:05',
                          u'BLKSEECO': u'',
                          u'BLKTRNCO': u'',
                          u'BLKTYPE': u'POND',
                          u'BLKUID': u'226616444',
                          u'BSCALE': 1.0,
                          u'BZERO': 0.0,
                          u'CAT_DEC': u'NaN',
                          u'CAT_EPOC': 2000.0,
                          u'CAT_RA': u'NaN',
                          u'CCDATEMP': -20.0320677,
                          u'CCDSEC': u'',
                          u'CCDSESIG': u'',
                          u'CCDSTEMP': -20.0045808,
                          u'CCDSUM': u'2 2',
                          u'CCDXPIXE': 9e-06,
                          u'CCDYPIXE': 9e-06,
                          u'CD1_1': 0.0003222,
                          u'CD1_2': 0.0,
                          u'CD2_1': 0.0,
                          u'CD2_2': 0.0003222,
                          u'CHECKSUM': u'BJWAEIV6BIVABIV3',
                          u'CONFMODE': u'',
                          u'CONFNAME': u'',
                          u'CRPIX1': 758.25,
                          u'CRPIX2': 507.25,
                          u'CRVAL1': 42.2781143,
                          u'CRVAL2': -0.16971,
                          u'CTYPE1': u'RA---TAN',
                          u'CTYPE2': u'DEC--TAN',
                          u'CUNIT1': u'deg',
                          u'CUNIT2': u'deg',
                          u'DARKCURR': 0.0,
                          u'DATADICV': u'LCOGT-DIC.FITS-0.11.0',
                          u'DATASEC': u'[1:1550,1:1028]',
                          u'DATASUM': u'198780119',
                          u'DATE': u'2018-02-26',
                          u'DATE_OBS': u'2018-02-27T06:48:55.979000',
                          u'DAY_OBS': u'20180226',
                          u'DEC': u'+72:04:12.33',
                          u'DECTRACK': 0.0,
                          u'DETECTID': u'ccdkb80-1',
                          u'DETECTOR': u'',
                          u'DETSEC': u'',
                          u'DETSIZE': u'[1:0,1:0]',
                          u'ENC1STAT': u'CLOSED',
                          u'ENC2STAT': u'CLOSED',
                          u'ENCAZ': 0.0,
                          u'ENCID': u'aqwa',
                          u'ENCLOSUR': u'Aqawan-01',
                          u'ENCRLIGT': u'OFF',
                          u'ENCWLIGT': u'OFF',
                          u'ENGSTATE': u'',
                          u'EOPSRC': u'IERS BULL. A 2018/02/22',
                          u'EXPTIME': 299.786,
                          u'EXTEND': True,
                          u'EXTNAME': u'SCI',
                          u'FILTER': u'w',
                          u'FILTER1': u'w',
                          u'FILTER2': u'NOTPRESENT',
                          u'FILTER3': u'NOTPRESENT',
                          u'FILTERI1': u'PSTR-WX-124',
                          u'FILTERI2': u'NOTPRESENT',
                          u'FILTERI3': u'NOTPRESENT',
                          u'FOCAFOFF': 1.6191343,
                          u'FOCDMD': 0.0,
                          u'FOCFLOFF': -1.0,
                          u'FOCINOFF': 0.0,
                          u'FOCOBOFF': 0.0,
                          u'FOCPOSN': -0.0071343,
                          u'FOCSTAT': u'HALTED',
                          u'FOCTELZP': 1.5,
                          u'FOCTEMP': 17.6249995,
                          u'FOCTOFF': 0.0359625,
                          u'FOCZOFF': 0.0527706,
                          u'FOLDPORT': u'1',
                          u'FOLDPOSN': u'00.0, N/A',
                          u'FOLDSTAT': u'ERROR',
                          u'FRAMENUM': 18,
                          u'FRMTOTAL': 5,
                          u'FWID': u'p4fw50-01',
                          u'GAIN': 1.0,
                          u'GCOUNT': 1,
                          u'GROUPID': u'LCOGT',
                          u'HDRVER': u'LCOGT-HDR-1.4.0',
                          u'HEIGHT': 2030.0,
                          u'ICSVER': u'master@0xc0b254f',
                          u'INSSTATE': u'OKAY',
                          u'INSTRUME': u'kb80',
                          u'ISSTEMP': u'',
                          u'L1IDBIAS': u'bias_kb80_20180226_bin2x2',
                          u'L1IDMASK': u'bpm_elp_kb80_20171012_bin2x2',
                          u'L1PUBDAT': u'2018-02-27T06:48:55.979000',
                          u'L1STATBI': 1,
                          u'L1STATOV': 0,
                          u'L1STATTR': 1,
                          u'LATITUDE': 30.6800415,
                          u'LONGITUD': -104.015066,
                          u'LST': u'02:50:02.48',
                          u'M1COVER': u'STOWED',
                          u'M1HRTMN': u'STOWED',
                          u'M1TEMP': u'',
                          u'M2PITCH': -166.22,
                          u'M2ROLL': -26.498,
                          u'MAXLIN': 133164.0,
                          u'MJD_OBS': 58175.9715837,
                          u'MOLFRNUM': 1,
                          u'MOLNUM': 3,
                          u'MOLTYPE': u'DARK',
                          u'MOLUID': u'493556972',
                          u'MOONALT': 20.459731,
                          u'MOONDIST': 76.084124,
                          u'MOONFRAC': 0.8790016,
                          u'MOONSTAT': u'UP',
                          u'NAXIS': 2,
                          u'NAXIS1': 1526,
                          u'NAXIS2': 1017,
                          u'OBJECT': u'',
                          u'OBRECIPE': u'',
                          u'OBSGEO_X': -1330017.31,
                          u'OBSGEO_Y': -5328438.752,
                          u'OBSGEO_Z': 3236472.371,
                          u'OBSID': u'300 dark',
                          u'OBSNOTE': u'',
                          u'OBSTELEM': u'',
                          u'OBSTYPE': u'DARK',
                          u'OFSTART': 1400,
                          u'OFSTOP': -10,
                          u'OFST_DEC': u'NaN',
                          u'OFST_RA': u'NaN',
                          u'ORIGIN': u'LCOGT',
                          u'ORIGNAME': link,
                          u'OVERSCAN': 0.0,
                          u'PARALLAX': 0.0,
                          u'PCOUNT': 0,
                          u'PCRECIPE': u'',
                          u'PIPEVER': u'0.7.9dev1212',
                          u'PIXSCALE': 1.16,
                          u'PM_DEC': 0.0,
                          u'PM_RA': 0.0,
                          u'POLARMOX': 0.0022,
                          u'POLARMOY': 0.3359,
                          u'PPRECIPE': u'',
                          u'PROPID': u'calibrate',
                          u'RA': u'14:49:02.155',
                          u'RADESYS': u'ICRS',
                          u'RADVEL': 0.0,
                          u'RATRACK': 0.0,
                          u'RDNOISE': 5.3,
                          u'RDSPEED': 30.0,
                          u'REFHUMID': u'',
                          u'REFPRES': u'',
                          u'REFTEMP': u'',
                          u'REQNUM': None,
                          u'REQTIME': 300.0,
                          u'RLEVEL': 91,
                          u'ROI': u'',
                          u'ROLLERDR': 6.1814493,
                          u'ROLLERND': 6.0029779,
                          u'ROTANGLE': u'',
                          u'ROTDMD': u'',
                          u'ROTMODE': u'FIXED',
                          u'ROTSKYPA': u'',
                          u'ROTSTAT': u'OFF',
                          u'ROTTYPE': u'NONE',
                          u'RWSTART': u'23:19:05.474',
                          u'RWSTOP': u'23:24:06.670',
                          u'SATFRAC': 0.0,
                          u'SATURATE': 153440.0,
                          u'SCHEDNAM': u'POND',
                          u'SCHEDSEE': u'',
                          u'SCHEDTRN': u'',
                          u'SIMPLE': True,
                          u'SITE': u'LCOGT node at McDonald Observatory',
                          u'SITEID': u'elp',
                          u'SKYMAG': 4.1302861,
                          u'SRCTYPE': u'',
                          u'SUNALT': 18.5146595,
                          u'SUNDIST': 106.3795788,
                          u'TAGID': u'LCOGT',
                          u'TCSSTATE': u'OKAY',
                          u'TCSVER': u'0.4',
                          u'TELESCOP': u'0m4-11',
                          u'TELID': u'0m4a',
                          u'TELMODE': u'AUTOMATIC',
                          u'TELSTATE': u'OKAY',
                          u'TIMESYS': u'UTC',
                          u'TPNTMODL': u'20180226124316',
                          u'TPT_DEC': u'NaN',
                          u'TPT_RA': u'NaN',
                          u'TRACKNUM': u'',
                          u'TRIGGER': u'',
                          u'TRIMSEC': u'[11:1536,6:1022]',
                          u'TUBETEMP': 17.6229997,
                          u'USERID': u'ELPOps',
                          u'UT1_UTC': 0.16904,
                          u'UTSTART': u'23:19:06.874',
                          u'UTSTOP': u'23:24:06.660',
                          u'WINDDIR': 193.0,
                          u'WINDSPEE': 19.6560001,
                          u'WMSCLOUD': -23.3893333,
                          u'WMSDEWPT': -7.6999998,
                          u'WMSHUMID': 20.7999992,
                          u'WMSMOIST': 257.6000061,
                          u'WMSPRES': 846.3305789,
                          u'WMSRAIN': u'CLEAR',
                          u'WMSSKYBR': 0.0,
                          u'WMSSTATE': u'OKAY',
                          u'WMSTEMP': 14.5,
                          u'XTENSION': u'BINTABLE',
                          u'ZDITHER0': 7960}}

    return header_out

# Mock api call to cancel block
def mock_lco_api_call_blockcancel(link,method):
    return {'state' : 'CANCELED'}

# Mock block records output from Valhalla
# One for each block in superblock. Changed block id's to match blocks
def mock_check_result_status(tracking_num):
    result_status_out = {'created': '2018-02-23T23:56:01.695109Z',
                         'name': 'N999r0q_V38-cad-0223-0227',
                         'id': 42,
                         'ipp_value': 1.05,
                         'modified': '2018-02-27T05:54:41.007389Z',
                         'observation_type': 'NORMAL',
                         'operator': 'MANY',
                         'proposal': 'LCO2018A-012',
                         'requests': [
                           {'acceptability_threshold': 90.0,
                           'completed': None,
                           'id': 1003,
                           'location': {'site': 'elp', 'telescope_class': '0m4'},
                           'configurations': [{
                             'id': 12345,
                             'constraints': {'max_airmass': 1.74,
                                             'max_lunar_phase': None,
                                             'max_seeing': None,
                                             'min_lunar_distance': 30.0,
                                             'min_transparency': None,
                                             'extra_params': {}
                                            },
                             'instrument_configs': [{'optical_elements': {'filter': 'w'},
                                                     'mode': 'default',
                                                     'exposure_time': 10.0,
                                                     'exposure_count': 386,
                                                     'bin_x': 1,
                                                     'bin_y': 1,
                                                     'rotator_mode': '',
                                                     'extra_params': {}
                                                   }],
                             'acquisition_config': { 'mode': 'OFF',
                                                     'exposure_time' : None,
                                                     'extra_params' : {}
                                                   },
                             'guiding_config': { 'optional': True,
                                                 'mode': 'ON',
                                                 'optical_elements': {},
                                                 'exposure_time': None,
                                                 'extra_params': {}
                                               },
                             'target': {'type': 'ORBITAL_ELEMENTS',
                                        'name': 'N999r0q',
                                        'argofperih': 180.74461,
                                        'eccentricity': 0.2695826,
                                        'epochofel': 58200.0,
                                        'longascnode': 347.31601,
                                        'meananom': 8.89267,
                                        'meandist': 1.36967423,
                                        'orbinc': 9.2247,
                                        'rot_angle': 0.0,
                                        'rot_mode': '',
                                        'scheme': 'MPC_MINOR_PLANET',
                                        'extra_params': {}
                                      },
                             'instrument_type': '0M4-SCICAM-SBIG',
                             'type': 'EXPOSE',
                             'extra_params':{},
                             'priority': 1}],
                           'windows': [{'end': '2018-02-24T11:45:00Z',
                                        'start': '2018-02-24T03:45:00Z'}],
                           'created': '2018-02-23T23:56:01.697048Z',
                           'observation_note': 'Submitted by NEOexchange (by tlister@lcogt.net)',
                           'state': 'WINDOW_EXPIRED',
                           'duration': 9372,
                           'modified': '2018-02-24T11:46:40.239116Z',
                          },
                          {'acceptability_threshold': 90.0,
                           'completed': None,
                           'id': 1430663,
                           'location': {'site': 'elp', 'telescope_class': '0m4'},
                           'configurations': [{
                             'id': 12346,
                             'constraints': {'max_airmass': 1.74,
                                             'max_lunar_phase': None,
                                             'max_seeing': None,
                                             'min_lunar_distance': 30.0,
                                             'min_transparency': None,
                                             'extra_params': {}
                                            },
                             'instrument_configs': [{'optical_elements': {'filter': 'w'},
                                                     'mode': 'default',
                                                     'exposure_time': 10.0,
                                                     'exposure_count': 386,
                                                     'bin_x': 1,
                                                     'bin_y': 1,
                                                     'rotator_mode': '',
                                                     'extra_params': {}
                                                   }],
                             'acquisition_config': { 'mode': 'OFF',
                                                     'exposure_time' : None,
                                                     'extra_params' : {}
                                                   },
                             'guiding_config': { 'optional': True,
                                                 'mode': 'ON',
                                                 'optical_elements': {},
                                                 'exposure_time': None,
                                                 'extra_params': {}
                                               },
                             'target': {'type': 'ORBITAL_ELEMENTS',
                                        'name': 'N999r0q',
                                        'argofperih': 180.74461,
                                        'eccentricity': 0.2695826,
                                        'epochofel': 58200.0,
                                        'longascnode': 347.31601,
                                        'meananom': 8.89267,
                                        'meandist': 1.36967423,
                                        'orbinc': 9.2247,
                                        'rot_angle': 0.0,
                                        'rot_mode': '',
                                        'scheme': 'MPC_MINOR_PLANET',
                                        'extra_params': {}
                                      },
                             'instrument_type': '0M4-SCICAM-SBIG',
                             'type': 'EXPOSE',
                             'extra_params':{},
                             'priority': 1}],
                           'windows': [{'end': '2018-02-25T11:45:00Z',
                                        'start': '2018-02-25T03:45:00Z'}],
                           'created': '2018-02-23T23:56:01.704260Z',
                           'duration': 9372,
                           'modified': '2018-02-25T11:47:06.795120Z',
                          },
                          {'acceptability_threshold': 90.0,
                           'completed': None,
                           'id': 15,
                           'location': {'site': 'elp', 'telescope_class': '0m4'},
                           'configurations': [{
                             'id': 12347,
                             'constraints': {'max_airmass': 1.74,
                                             'max_lunar_phase': None,
                                             'max_seeing': None,
                                             'min_lunar_distance': 30.0,
                                             'min_transparency': None,
                                             'extra_params': {}
                                            },
                             'instrument_configs': [{'optical_elements': {'filter': 'w'},
                                                     'mode': 'default',
                                                     'exposure_time': 10.0,
                                                     'exposure_count': 386,
                                                     'bin_x': 1,
                                                     'bin_y': 1,
                                                     'rotator_mode': '',
                                                     'extra_params': {}
                                                   }],
                             'acquisition_config': { 'mode': 'OFF',
                                                     'exposure_time' : None,
                                                     'extra_params' : {}
                                                   },
                             'guiding_config': { 'optional': True,
                                                 'mode': 'ON',
                                                 'optical_elements': {},
                                                 'exposure_time': None,
                                                 'extra_params': {}
                                               },
                             'target': {'type': 'ORBITAL_ELEMENTS',
                                        'name': 'N999r0q',
                                        'argofperih': 180.74461,
                                        'eccentricity': 0.2695826,
                                        'epochofel': 58200.0,
                                        'longascnode': 347.31601,
                                        'meananom': 8.89267,
                                        'meandist': 1.36967423,
                                        'orbinc': 9.2247,
                                        'rot_angle': 0.0,
                                        'rot_mode': '',
                                        'scheme': 'MPC_MINOR_PLANET',
                                        'extra_params': {}
                                      },
                             'instrument_type': '0M4-SCICAM-SBIG',
                             'type': 'EXPOSE',
                             'extra_params':{},
                             'priority': 1}],
                           'windows': [{'end': '2018-02-26T11:45:00Z',
                                        'start': '2018-02-26T03:45:00Z'}],
                           'created': '2018-02-23T23:56:01.709915Z',
                           'duration': 9372,
                           'modified': '2018-02-26T11:47:31.639510Z',
                          },
                          {'acceptability_threshold': 90.0,
                           'completed': '2018-02-27T05:54:40.984190Z',
                           'id': 9,
                           'location': {'site': 'elp', 'telescope_class': '0m4'},
                           'configurations': [{
                             'id': 12348,
                             'constraints': {'max_airmass': 1.74,
                                             'max_lunar_phase': None,
                                             'max_seeing': None,
                                             'min_lunar_distance': 30.0,
                                             'min_transparency': None,
                                             'extra_params': {}
                                            },
                             'instrument_configs': [{'optical_elements': {'filter': 'w'},
                                                     'mode': 'default',
                                                     'exposure_time': 10.0,
                                                     'exposure_count': 386,
                                                     'bin_x': 1,
                                                     'bin_y': 1,
                                                     'rotator_mode': '',
                                                     'extra_params': {}
                                                   }],
                             'acquisition_config': { 'mode': 'OFF',
                                                     'exposure_time' : None,
                                                     'extra_params' : {}
                                                   },
                             'guiding_config': { 'optional': True,
                                                 'mode': 'ON',
                                                 'optical_elements': {},
                                                 'exposure_time': None,
                                                 'extra_params': {}
                                               },
                             'target': {'type': 'ORBITAL_ELEMENTS',
                                        'name': 'N999r0q',
                                        'argofperih': 180.74461,
                                        'eccentricity': 0.2695826,
                                        'epochofel': 58200.0,
                                        'longascnode': 347.31601,
                                        'meananom': 8.89267,
                                        'meandist': 1.36967423,
                                        'orbinc': 9.2247,
                                        'rot_angle': 0.0,
                                        'rot_mode': '',
                                        'scheme': 'MPC_MINOR_PLANET',
                                        'extra_params': {}
                             },
                             'instrument_type': '0M4-SCICAM-SBIG',
                             'type': 'EXPOSE',
                             'extra_params':{},
                             'priority': 1}],
                          'windows': [{'end': '2018-02-27T11:45:00Z',
                                       'start': '2018-02-27T03:45:00Z'}]
                          }],
                         'created': '2018-02-23T23:56:01.715505Z',
                         'duration': 9372,
                         'modified': '2018-02-27T05:54:40.986064Z',
                         'observation_note': 'Submitted by NEOexchange (by tlister@lcogt.net)',
                         'scheduled_count': 0,
                      'state': 'COMPLETED',
                      'submitter': 'neox_robot'}
    return result_status_out


def mock_check_request_status_spectro(tracking_num):
    result_status_out = {'created': '2018-01-10T22:58:32.524744Z',
                         'name': '8_F65-20180111_spectra',
                         'id': 557017,
                         'ipp_value': 1.0,
                         'modified': '2018-01-11T06:49:53.678461Z',
                         'observation_type': 'NORMAL',
                         'operator': 'SINGLE',
                         'proposal': 'LCOEngineering',
                         'requests': [{'acceptability_threshold': 90.0,
                                       'location': {'site': 'ogg', 'telescope_class': '2m0'},
                                       'configurations': [{
                                           'id': 3126189,
                                           'constraints': {'max_airmass': 1.74,
                                                           'min_lunar_distance': 30.0,
                                                           'max_lunar_phase': None,
                                                           'max_seeing': None,
                                                           'min_transparency': None,
                                                           'extra_params': {}
                                                           },
                                           'instrument_configs': [{'optical_elements': {'slit': 'slit_2.0as'},
                                                                   'mode': 'default',
                                                                   'exposure_time': 20.0,
                                                                   'exposure_count': 1,
                                                                   'bin_x': 1,
                                                                   'bin_y': 1,
                                                                   'rotator_mode': 'VFLOAT',
                                                                   'extra_params': {}
                                                                   }],
                                           'acquisition_config': {'mode': 'OFF',
                                                                  'exposure_time': 5.0,
                                                                  'extra_params': {'acquire_radius': 5.0}
                                                                  },
                                           'guiding_config': {'optional': False,
                                                              'mode': 'OFF',
                                                              'optical_elements': {},
                                                              'exposure_time': 5.0,
                                                              'extra_params': {}
                                                              },
                                           'target': {'type': 'ORBITAL_ELEMENTS',
                                                      'name': '8 Flora',
                                                      'epochofel': 58787.0,
                                                      'orbinc': 5.88696,
                                                      'longascnode': 110.88930,
                                                      'eccentricity': 0.1564993,
                                                      'scheme': 'MPC_MINOR_PLANET',
                                                      'argofperih': 285.28745,
                                                      'meandist': 2.2017642,
                                                      'meananom': 194.883,
                                                      'extra_params': {'v_magnitude': 10.0}
                                                      },
                                           'instrument_name': '2M0-FLOYDS-SCICAM',
                                           'type': 'LAMP_FLAT',
                                           'extra_params': {},
                                           'priority': 1},
                                           {'id': 3126190,
                                            'constraints': {'max_airmass': 1.74,
                                                            'min_lunar_distance': 30.0,
                                                            'max_lunar_phase': None,
                                                            'max_seeing': None,
                                                            'min_transparency': None,
                                                            'extra_params': {}},
                                            'instrument_configs': [{'optical_elements': {'slit': 'slit_2.0as'},
                                                                    'mode': 'default',
                                                                    'exposure_time': 60.0,
                                                                    'exposure_count': 1,
                                                                    'bin_x': 1,
                                                                    'bin_y': 1,
                                                                    'rotator_mode': 'VFLOAT',
                                                                    'extra_params': {}
                                                                    }],
                                            'acquisition_config': {'mode': 'OFF',
                                                                   'exposure_time': 5.0,
                                                                   'extra_params': {'acquire_radius': 5.0}
                                                                   },
                                            'guiding_config': {'optional': False,
                                                               'mode': 'OFF',
                                                               'optical_elements': {},
                                                               'exposure_time': 5.0,
                                                               'extra_params': {}
                                                               },
                                            'target': {'type': 'ORBITAL_ELEMENTS',
                                                       'name': '8 Flora',
                                                       'epochofel': 58787.0,
                                                       'orbinc': 5.88696,
                                                       'longascnode': 110.88930,
                                                       'eccentricity': 0.1564993,
                                                       'scheme': 'MPC_MINOR_PLANET',
                                                       'argofperih': 285.28745,
                                                       'meandist': 2.2017642,
                                                       'meananom': 194.883,
                                                       'extra_params': {'v_magnitude': 10.0}
                                                       },
                                            'instrument_name': '2M0-FLOYDS-SCICAM',
                                            'type': 'ARC',
                                            'extra_params': {},
                                            'priority': 2
                                            },
                                           {'id': 3126191,
                                            'constraints': {'max_airmass': 1.15,
                                                            'min_lunar_distance': 30.0,
                                                            'max_lunar_phase': None,
                                                            'max_seeing': None,
                                                            'min_transparency': None,
                                                            'extra_params': {}
                                                            },
                                            'instrument_configs': [{'optical_elements': {'slit': 'slit_2.0as'},
                                                                    'mode': 'default',
                                                                    'exposure_time': 300.0,
                                                                    'exposure_count': 1,
                                                                    'bin_x': 1,
                                                                    'bin_y': 1,
                                                                    'rotator_mode': 'VFLOAT',
                                                                    'extra_params': {}
                                                                    }],
                                            'acquisition_config': {'mode': 'OFF',
                                                                   'exposure_time': 5.0,
                                                                   'extra_params': {'acquire_radius': 5.0}
                                                                   },
                                            'guiding_config': {'optional': False,
                                                               'mode': 'OFF',
                                                               'optical_elements': {},
                                                               'exposure_time': 5.0,
                                                               'extra_params': {}
                                                               },
                                            'target': {'type': 'ORBITAL_ELEMENTS',
                                                       'name': '8 Flora',
                                                       'epochofel': 58787.0,
                                                       'orbinc': 5.88696,
                                                       'longascnode': 110.88930,
                                                       'eccentricity': 0.1564993,
                                                       'scheme': 'MPC_MINOR_PLANET',
                                                       'argofperih': 285.28745,
                                                       'meandist': 2.2017642,
                                                       'meananom': 194.883,
                                                       'extra_params': {'v_magnitude': 10.0}
                                                       },
                                            'instrument_name': '2M0-FLOYDS-SCICAM',
                                            'type': 'SPECTRUM',
                                            'extra_params': {},
                                            'priority': 3},
                                           {'id': 3126192,
                                            'constraints': {'max_airmass': 1.74,
                                                            'min_lunar_distance': 30.0,
                                                            'max_lunar_phase': None,
                                                            'max_seeing': None,
                                                            'min_transparency': None,
                                                            'extra_params': {}
                                                            },
                                            'instrument_configs': [{'optical_elements': {'slit': 'slit_2.0as'},
                                                                    'mode': 'default',
                                                                    'exposure_time': 20.0,
                                                                    'exposure_count': 1,
                                                                    'bin_x': 1,
                                                                    'bin_y': 1,
                                                                    'rotator_mode': 'VFLOAT',
                                                                    'extra_params': {}
                                                                    }],
                                            'acquisition_config': {'mode': 'OFF',
                                                                   'exposure_time': 5.0,
                                                                   'extra_params': {'acquire_radius': 5.0}
                                                                   },
                                            'guiding_config': {'optional': False,
                                                               'mode': 'OFF',
                                                               'optical_elements': {},
                                                               'exposure_time': 5.0,
                                                               'extra_params': {}
                                                               },
                                            'target': {"name": "HD 154445",
                                                       "type": "ICRS",
                                                       "ra": 256.384411918761,
                                                       "dec": -0.8920663093766,
                                                       "proper_motion_ra": 3.014,
                                                       "proper_motion_dec": -0.463,
                                                       "epoch": 2000,
                                                       "parallax": 3.7212,
                                                       'extra_params': {'v_magnitude': 10.0}
                                                       },
                                            'instrument_name': '2M0-FLOYDS-SCICAM',
                                            'type': 'LAMP_FLAT',
                                            'extra_params': {},
                                            'priority': 1},
                                           {'id': 3126193,
                                            'constraints': {'max_airmass': 1.74,
                                                            'min_lunar_distance': 30.0,
                                                            'max_lunar_phase': None,
                                                            'max_seeing': None,
                                                            'min_transparency': None,
                                                            'extra_params': {}},
                                            'instrument_configs': [{'optical_elements': {'slit': 'slit_2.0as'},
                                                                    'mode': 'default',
                                                                    'exposure_time': 60.0,
                                                                    'exposure_count': 1,
                                                                    'bin_x': 1,
                                                                    'bin_y': 1,
                                                                    'rotator_mode': 'VFLOAT',
                                                                    'extra_params': {}
                                                                    }],
                                            'acquisition_config': {'mode': 'OFF',
                                                                   'exposure_time': 5.0,
                                                                   'extra_params': {'acquire_radius': 5.0}
                                                                   },
                                            'guiding_config': {'optional': False,
                                                               'mode': 'OFF',
                                                               'optical_elements': {},
                                                               'exposure_time': 5.0,
                                                               'extra_params': {}
                                                               },
                                            'target': {"name": "HD 154445",
                                                       "type": "ICRS",
                                                       "ra": 256.384411918761,
                                                       "dec": -0.8920663093766,
                                                       "proper_motion_ra": 3.014,
                                                       "proper_motion_dec": -0.463,
                                                       "epoch": 2000,
                                                       "parallax": 3.7212,
                                                       'extra_params': {'v_magnitude': 10.0}
                                                       },
                                            'instrument_name': '2M0-FLOYDS-SCICAM',
                                            'type': 'ARC',
                                            'extra_params': {},
                                            'priority': 2
                                            },
                                           {'id': 3126194,
                                            'constraints': {'max_airmass': 1.15,
                                                            'min_lunar_distance': 30.0,
                                                            'max_lunar_phase': None,
                                                            'max_seeing': None,
                                                            'min_transparency': None,
                                                            'extra_params': {}
                                                            },
                                            'instrument_configs': [{'optical_elements': {'slit': 'slit_2.0as'},
                                                                    'mode': 'default',
                                                                    'exposure_time': 300.0,
                                                                    'exposure_count': 1,
                                                                    'bin_x': 1,
                                                                    'bin_y': 1,
                                                                    'rotator_mode': 'VFLOAT',
                                                                    'extra_params': {}
                                                                    }],
                                            'acquisition_config': {'mode': 'OFF',
                                                                   'exposure_time': 5.0,
                                                                   'extra_params': {'acquire_radius': 5.0}
                                                                   },
                                            'guiding_config': {'optional': False,
                                                               'mode': 'OFF',
                                                               'optical_elements': {},
                                                               'exposure_time': 5.0,
                                                               'extra_params': {}
                                                               },
                                            'target': {"name": "HD 154445",
                                                       "type": "ICRS",
                                                       "ra": 256.384411918761,
                                                       "dec": -0.8920663093766,
                                                       "proper_motion_ra": 3.014,
                                                       "proper_motion_dec": -0.463,
                                                       "epoch": 2000,
                                                       "parallax": 3.7212,
                                                       'extra_params': {'v_magnitude': 10.0}
                                                       },
                                            'instrument_name': '2M0-FLOYDS-SCICAM',
                                            'type': 'SPECTRUM',
                                            'extra_params': {},
                                            'priority': 3}],
                                       'created': '2018-01-10T22:58:32.526661Z',
                                       'duration': 1690,
                                       'id': 1391169,
                                       'modified': '2018-01-11T06:49:53.667734Z',
                                       'observation_note': 'Submitted by NEOexchange (by tlister@lcogt.net)',
                                       'state': 'COMPLETED',
                                       'windows': [{'end': '2018-01-11T15:50:00Z', 'start': '2018-01-11T05:00:00Z'}]
                                       }],
                         'state': 'COMPLETED',
                         'submitter': 'tlister@lcogt.net'}
    return result_status_out


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
                  u'OBJECT': 'N999r0q',
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
                  u'OBJECT': 'N999r0q',
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
                  u'OBJECT': 'N999r0q',
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
                  u'OBJECT': 'N999r0q',
                  u'basename': u'ogg2m001-en06-20180110-0004-a00',
                  u'filename': u'ogg2m001-en06-20180110-0004-a00.fits.fz',
                  u'id': 7780725,
                  u'related_frames': [],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/292d/ogg2m001-en06-20180110-0004-a00?versionId=6cU5D5EC7Zq1tVEb7OZlR7WFEeXyqGp8&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=o6l5GeCbm%2FgHa7LRI3ycNyFnhQY%3D&Expires=1521844038',
                 },
                {
                  u'OBSTYPE': u'SPECTRUM',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 90,
                  u'OBJECT': 'HD 15445',
                  u'basename': u'LCOEngineering_0001391169_ftn_20180111_58131',
                  u'filename': u'LCOEngineering_0001391169_ftn_20180111_58131.tar.gz',
                  u'id': 7783594,
                  u'related_frames': [7780756],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/372a/LCOEngineering_0001391169_ftn_20180111_58130?versionId=eK7.aDucOKWaiM3AhTPZ8AGDMxBFdNtH&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=x8mve2svKirG7BAiWaEBTyFsHrY%3D&Expires=1521319897',
                 },
                 {
                  u'OBSTYPE': u'SPECTRUM',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 0,
                  u'OBJECT': 'HD 15445',
                  u'basename': u'ogg2m001-en06-20180110-0006-e00',
                  u'filename': u'ogg2m001-en06-20180110-0006-e00.fits.fz',
                  u'id': 7780756,
                  u'related_frames': [7783594],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/dd9f/ogg2m001-en06-20180110-0005-e00?versionId=c1X8nfL_LSwptv_c0m7dultGCOfVJJr3&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=fjmzi9KK%2FqNi3DnvjyEjSP%2BJG8o%3D&Expires=1521319897',
                 },
                 {
                  u'OBSTYPE': u'LAMPFLAT',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 0,
                  u'OBJECT': 'HD 15445',
                  u'basename': u'ogg2m001-en06-20180110-0007-w00',
                  u'filename': u'ogg2m001-en06-20180316-0007-w00.fits.fz',
                  u'id': 7780712,
                  u'related_frames': [],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/f0b3/ogg2m001-en06-20180110-0003-w00?versionId=5_5KtN4yTb1HETGb3SOMkkZdVW2vxOpd&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=vwaE37UFo8gnn46IKWuRZKpSoEA%3D&Expires=1521844038',
                 },
                 {
                  u'OBSTYPE': u'ARC',
                  u'REQNUM': 1391169,
                  u'RLEVEL': 0,
                  u'OBJECT': 'HD 15445',
                  u'basename': u'ogg2m001-en06-20180110-0008-a00',
                  u'filename': u'ogg2m001-en06-20180110-0008-a00.fits.fz',
                  u'id': 7780726,
                  u'related_frames': [],
                  u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/292d/ogg2m001-en06-20180110-0004-a00?versionId=6cU5D5EC7Zq1tVEb7OZlR7WFEeXyqGp8&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=o6l5GeCbm%2FgHa7LRI3ycNyFnhQY%3D&Expires=1521844038',
                 }
                ]
        if 'OBJECT=N9' in archive_url:
            return data[:4]
        elif 'OBJECT=HD' in archive_url:
            return data[4:]
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


def mock_check_for_images(request_id, obstype='EXPOSE', obj=''):

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
            "REQNUM": "1878697",
            "ORIGNAME": "ogg2m001-en06-20180110-0005-e00",
            "GROUPID": "TEMP",
            "BLKUID": "999999"
                }
            }
    else:
        header = {"data":
                      {"DATE_OBS": "2019-07-27T15:52:19.512",
                       "DAY_OBS": "20190727",
                       "ENCID": "clma",
                       "SITEID": "coj",
                       "TELID": "2m0a",
                       "OBJECT": "455432",
                       "REQNUM": "1878696",
                       "ORIGNAME": "ogg2m001-en06-20180110-0005-e00",
                       "GROUPID": "TEMP",
                       "BLKUID": "999999"
                       }
                  }
    return header


def mock_archive_bad_spectra_header(archive_headers):

    header = { "data": {
                    "DATE_OBS": "2019-09-27T15:52:19.512",
                    "DAY_OBS" : "20190927",
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
    if '1m0' in telid.lower():
        camid = "1m0-SciCam-Sinistro"
    elif '0m4' in telid.lower():
        camid = "0m4-SciCam-SBIG"
    elif '2m0' in telid.lower():
        if spec:
            camid = "2m0-FLOYDS-SciCam"
        elif "OGG" in siteid.upper():
            camid = "2M0-SCICAM-MUSCAT"
        else:
            camid = "2m0-SciCam-Spectral"
    else:
        camid = ''

    coj_1m_rsp = {'1M0-SCICAM-SINISTRO': {
        'type': 'IMAGE',
        'class': '1m0',
        'name': '1.0 meter Sinistro',
        'optical_elements':
            {'filters': [
                {'name': 'Bessell-I', 'code': 'I', 'schedulable': True, 'default': False},
                {'name': 'Bessell-R', 'code': 'R', 'schedulable': True, 'default': False},
                {'name': 'Bessell-U', 'code': 'U', 'schedulable': True, 'default': False},
                {'name': 'PanSTARRS-w', 'code': 'w', 'schedulable': True, 'default': False},
                {'name': 'PanSTARRS-Y', 'code': 'Y', 'schedulable': True, 'default': False},
                {'name': 'SDSS-up', 'code': 'up', 'schedulable': True, 'default': False},
                {'name': 'Clear', 'code': 'air', 'schedulable': True, 'default': False},
                {'name': 'SDSS-rp', 'code': 'rp', 'schedulable': True, 'default': False},
                {'name': 'SDSS-ip', 'code': 'ip', 'schedulable': True, 'default': False},
                {'name': 'SDSS-gp', 'code': 'gp', 'schedulable': True, 'default': False},
                {'name': 'PanSTARRS-Z', 'code': 'zs', 'schedulable': True, 'default': False},
                {'name': 'Bessell-V', 'code': 'V', 'schedulable': True, 'default': False},
                {'name': 'Bessell-B', 'code': 'B', 'schedulable': True, 'default': False},
                {'name': '400um Pinhole', 'code': '400um-Pinhole', 'schedulable': False, 'default': False},
                {'name': '150um Pinhole', 'code': '150um-Pinhole', 'schedulable': False, 'default': False},
                {'name': 'ND', 'code': 'ND', 'schedulable': True, 'default': False},
                {'name': 'B*ND', 'code': 'B*ND', 'schedulable': False, 'default': False},
                {'name': 'V*ND', 'code': 'V*ND', 'schedulable': False, 'default': False},
                {'name': 'R*ND', 'code': 'R*ND', 'schedulable': False, 'default': False},
                {'name': 'I*ND', 'code': 'I*ND', 'schedulable': False, 'default': False},
                {'name': 'rp*Diffuser', 'code': 'rp*Diffuser', 'schedulable': False, 'default': False},
                {'name': 'Diffuser_PennState', 'code': 'Diffuser', 'schedulable': False, 'default': False},
                {'name': 'gp*Diffuser', 'code': 'gp*Diffuser', 'schedulable': False, 'default': False}]}}}

    spec_2m_rsp = {'2M0-FLOYDS-SCICAM': {
        'type': 'SPECTRA',
        'class': '2m0',
        'name': '2.0 meter FLOYDS',
        'optical_elements':
            {'slits': [
                {'name': '6.0 arcsec slit', 'code': 'slit_6.0as', 'schedulable': True, 'default': False},
                {'name': '1.6 arcsec slit', 'code': 'slit_1.6as', 'schedulable': True, 'default': False},
                {'name': '2.0 arcsec slit', 'code': 'slit_2.0as', 'schedulable': True, 'default': False},
                {'name': '1.2 arcsec slit', 'code': 'slit_1.2as', 'schedulable': True, 'default': False}],
             }}}

    phot_2m_rsp = {"2M0-SCICAM-SPECTRAL": {
        "type": "IMAGE",
        "class": "2m0",
        "name": "2.0 meter Spectral",
        "optical_elements": {'filters': [
             {'name': 'D51', 'code': 'D51', 'schedulable': True, 'default': False},
             {'name': 'H Beta', 'code': 'H-Beta', 'schedulable': True, 'default': False},
             {'name': 'OIII', 'code': 'OIII', 'schedulable': True, 'default': False},
             {'name': 'OIII', 'code': 'OIII', 'schedulable': True, 'default': False},
             {'name': 'H Alpha', 'code': 'H-Alpha', 'schedulable': True, 'default': False},
             {'name': 'Skymapper CaV', 'code': 'Skymapper-VS', 'schedulable': True, 'default': False},
             {'name': 'Solar (V+R)', 'code': 'solar', 'schedulable': True, 'default': False},
             {'name': 'Astrodon UV', 'code': 'Astrodon-UV', 'schedulable': True, 'default': False},
             {'name': 'Bessell-I', 'code': 'I', 'schedulable': True, 'default': False},
             {'name': 'Bessell-R', 'code': 'R', 'schedulable': True, 'default': False},
             {'name': 'PanSTARRS-Y', 'code': 'Y', 'schedulable': True, 'default': False},
             {'name': 'SDSS-up', 'code': 'up', 'schedulable': True, 'default': False},
             {'name': 'Clear', 'code': 'air', 'schedulable': True, 'default': False},
             {'name': 'SDSS-rp', 'code': 'rp', 'schedulable': True, 'default': False},
             {'name': 'SDSS-ip', 'code': 'ip', 'schedulable': True, 'default': False},
             {'name': 'SDSS-gp', 'code': 'gp', 'schedulable': True, 'default': False},
             {'name': 'PanSTARRS-Z', 'code': 'zs', 'schedulable': True, 'default': False},
             {'name': 'Bessell-V', 'code': 'V', 'schedulable': True, 'default': False},
             {'name': 'Bessell-B', 'code': 'B', 'schedulable': True, 'default': False},
             {'name': '200um Pinhole', 'code': '200um-Pinhole', 'schedulable': False, 'default': False}]}}}

    muscat_2m_rsp = {"2M0-SCICAM-MUSCAT": {
        "type": "IMAGE",
        "class": "2m0",
        "name": "2.0 meter Muscat",
        "optical_elements": {
            "diffuser_z_positions": [
                {"name": "In Beam",
                 "code": "in",
                 "schedulable": True,
                 "default": False},
                {"name": "Out of Beam",
                 "code": "out",
                 "schedulable": True,
                 "default": True}
            ],
            "diffuser_r_positions": [
                {"name": "In Beam",
                 "code": "in",
                 "schedulable": True,
                 "default": False},
                {"name": "Out of Beam",
                 "code": "out",
                 "schedulable": True,
                 "default": True}
            ],
            "diffuser_i_positions": [
                {"name": "In Beam",
                 "code": "in",
                 "schedulable": True,
                    "default": False},
                {"name": "Out of Beam",
                 "code": "out",
                 "schedulable": True,
                 "default": True}
            ],
            "diffuser_g_positions": [
                {"name": "In Beam",
                 "code": "in",
                 "schedulable": True,
                 "default": False},
                {"name": "Out of Beam",
                 "code": "out",
                 "schedulable": True,
                 "default": True}
            ]
        }}}

    empty = {}
    fetch_error = ''

    if '2m0' in telid.lower():
        if spec:
            resp = spec_2m_rsp
        elif 'OGG' in siteid.upper():
            resp = muscat_2m_rsp
        else:
            resp = phot_2m_rsp
    elif '1m0' in telid.lower() or '0m4' in telid.lower():
        resp = coj_1m_rsp
    else:
        resp = empty
        fetch_error = 'The {} at {} is not schedulable'.format(camid, site)

    if 'MUSCAT' in camid:
        out_data = ['gp', 'rp', 'ip', 'zp']
    else:
        out_data = parse_filter_file(resp, spec)
    return out_data, fetch_error


def mock_fetch_filter_list_no2m(site, spec):
    if spec:
        camid = "2m0-FLOYDS-SciCam"
    elif "F65" in site.upper():
        camid = "2M0-SCICAM-MUSCAT"
    else:
        camid = "2M0-SCICAM-SPECTRAL"

    return [], "The {} at {} is not schedulable.".format(camid, site)


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

def mock_expand_cadence_novis(user_request):

    cadence = {'errors': 'No visible requests within cadence window parameters'}
    start_date = datetime.strptime(user_request['requests'][0]['cadence']['start'], '%Y-%m-%dT%H:%M:%S')
    end_date = datetime.strptime(user_request['requests'][0]['cadence']['end'], '%Y-%m-%dT%H:%M:%S')
    if end_date.month > start_date.month:
        # Fake a semester-spanning invalid request
        cadence = {'requests': [{},
                  {'windows': [{'non_field_errors': ['The observation window does not fit within any defined semester.']}]},
                  {},
                  {},
                  {},
                  {},
                  {},
                  {},
                  {}]}

    return False, cadence

def mock_fetch_sfu(sfu_value=None):
    if sfu_value is None:
        sfu = u.def_unit(['sfu', 'solar flux unit'], 10000.0*u.Jy)
        sfu_value = 42.0 * sfu

    return datetime(2018, 4, 20, 5, 0, 0), sfu_value


def mock_get_vizier_catalog_table(ra, dec, ref_width, ref_height, cat_name="GAIA-DR2", set_row_limit=10, rmag_limit="<=15.0"):
    row_data = [(122.87969710600, -58.07853650240,    4.0395,    3.8507, 17.9948,  0.0019,     0),
                (122.61441851900, -58.07346919930,    1.8437,    1.8947, 16.8281,  0.0009,     0)
               ]

    column_units = { 'RAJ2000' : u.deg, 'DEJ2000' : u.deg, 'e_RAJ2000' : u.mas, 'e_DEJ2000' : u.mas,
                     'Gmag' : u.mag, 'e_Gmag' : u.mag, 'Dup' : ''
                   }
    fake_table = Table(rows=row_data, names=('RAJ2000', 'DEJ2000', 'e_RAJ2000', 'e_DEJ2000', 'Gmag', 'e_Gmag', 'Dup'),
                       dtype=('<f8', '<f8', '<f8', '<f8', '<f8', '<f8', 'u1'))
    for column in fake_table.colnames:
        unit = column_units[column]
        fake_table[column].unit = unit

    return fake_table, cat_name


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
           'max_alt': [84, 83, 84, 33, 36, 43],
           'line_alpha': [1, 1, 1, 1, 1, 1]}
    emp = [['2019 10 15 02:00', '22 01 28.18', '-25 38 42.1', '21.7', ' 0.85', ' 72.9', '+5', '0.98', ' 71', '-39', '-999', '-04:54'],
           ['2019 10 15 02:30', '22 01 29.97', '-25 38 34.7', '21.7', ' 0.84', ' 72.7', '+11', '0.98', ' 71', '-33', '-999', '-04:24'],
           ['2019 10 15 03:00', '22 01 31.74', '-25 38 27.1', '21.7', ' 0.83', ' 72.3', '+16', '0.98', ' 71', '-27', '-999', '-03:54'],
           ['2019 10 15 03:30', '22 01 33.49', '-25 38 19.5', '21.7', ' 0.83', ' 72.0', '+22', '0.98', ' 72', '-20', '-999', '-03:24']]

    return vis, emp

### XXX Rewrite for more likely Goldstone information, removed `extrainfo` on uncertainty for now.
def mock_fetch_goldstone_calendar_targets(page=None, calendar_format=True):
    targets = [ { 'target': '2020 RY',
                  'windows' : [ {'start': '2020-09-03T00:00:00', 'end': '2020-09-03T23:59:59'} ],
                },
                { "target": "2020 RK",
                  'windows' : [ {"start": "2020-09-03T00:00:00", "end": "2020-09-03T23:59:59"} ],
                },
              ]

    return targets
