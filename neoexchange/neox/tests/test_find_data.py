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

from .base import FunctionalTest
import os
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from django.urls import reverse
from core.models import Body, Frame, SourceMeasurement
from mock import patch
from neox.tests.mocks import mock_build_visibility_source


class FindDataPageTests(FunctionalTest):

    def insert_test_extra_test_body(self):
        params = {  'name'          : '65803',
                    'origin'        : 'N',
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active': True,
                    'fast_moving': False,
                    'urgency': None,
                    'epochofel': datetime(2023, 2, 25, 0, 0),
                    'orbit_rms': 0.77,
                    'orbinc': 3.41411,
                    'longascnode': 72.99108,
                    'argofperih': 319.56159,
                    'eccentricity': 0.3832817,
                    'meandist': 1.6425445,
                    'meananom': 59.09022,
                    'perihdist': None,
                    'epochofperih': None,
                    'abs_mag': 18.13,
                    'slope': 0.15,
                    'score': None,
                    'discovery_date': datetime(1996, 4, 11, 0, 0),
                    'num_obs': 4089,
                    'arc_length': 9739.0,
                    'not_seen': 4.12823459021991,
                    'updated': True,
                    'ingest': datetime(2018, 8, 14, 17, 45, 42),
                    'update_time': datetime(2023, 6, 2, 6, 23, 8, 64382),
                    'analysis_status': 0,
                    }
        body2, status = Body.objects.get_or_create(**params)
        self.body2 = body2

    def insert_test_measurements(self, rms=False):
        frame_params = { 'sitecode' : 'K91',
                         'instrument' : 'kb70',
                         'filter' : 'w',
                         'filename' : 'cpt1m010-kb70-20150420-0042-e00.fits',
                         'exptime' : 40.0,
                         'midpoint' : '2015-04-20 18:00:00',
                         'block' : self.test_block
                        }
        if rms:
            frame_params['astrometric_catalog'] = 'UCAC-4'
            frame_params['photometric_catalog'] = 'UCAC-4'
        frame, status = Frame.objects.get_or_create(pk=1, **frame_params)
        self.test_frame = frame

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 42.1,
                           'obs_dec' : -30.05,
                           'obs_mag' : 21.05,
                           'err_obs_mag' : 0.03
                         }
        if rms:
            measure_params['err_obs_ra'] = 300e-3/3600.0
            measure_params['err_obs_dec'] = 275e-3/3600.0  
        sourcemeas, status = SourceMeasurement.objects.get_or_create(pk=1, **measure_params)
        self.test_measure1 = sourcemeas

    def insert_satellite_test_measurements(self):
        sat_frame_params = { 'sitecode' : 'C51',
                         'filter' : 'R',
                         'midpoint' : '2016-02-10 06:26:57',
                         'frametype' : Frame.SATELLITE_FRAMETYPE,
                         'extrainfo' : '     N999r0q  s2016 02 10.26872 1 - 3333.4505 - 5792.1311 - 1586.1945        C51'
                        }
        self.sat_test_frame = Frame.objects.create(pk=1, **sat_frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.sat_test_frame,
                           'obs_ra' : 229.21470833333336,
                           'obs_dec' : -10.464194444444443,
                           'astrometric_catalog' : '2MASS'
                         }
        self.test_measure1 = SourceMeasurement.objects.create(pk=1, **measure_params)
        frame_params = { 'sitecode' : 'W86',
                         'instrument' : 'fl03',
                         'filter' : 'R',
                         'filename' : 'lsc1m009-fl03-20160210-0243-e10.fits',
                         'exptime' : 95.0,
                         'midpoint' : '2016-02-11 07:41:44',
                         'block' : self.test_block
                        }
        self.test_frame = Frame.objects.create(pk=2, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 229.66829166666668,
                           'obs_dec' : -10.953888888888889,
                           'obs_mag' : 20.1,
                           'err_obs_mag' : 0.1,
                           'astrometric_catalog' : 'PPMXL'
                         }
        self.test_measure1 = SourceMeasurement.objects.create(pk=2, **measure_params)

    def insert_extra_measurements(self, rms=False):

        frame_params = { 'sitecode' : 'K91',
                         'instrument' : 'kb70',
                         'filter' : 'w',
                         'filename' : 'cpt1m010-kb70-20150421-0042-e00.fits',
                         'exptime' : 40.0,
                         'midpoint' : '2015-04-21 18:00:00',
                         'block' : self.test_block
                        }
        if rms:
            frame_params['astrometric_catalog'] = 'PPMXL'
            frame_params['photometric_catalog'] = 'PPMXL'
            frame_params['fwhm'] = 1.6
        self.test_frame = Frame.objects.create(pk=2, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 42.2,
                           'obs_dec' : -31.05,
                           'obs_mag' : 20.95,
                           'err_obs_mag' : 0.028
                         }
        if rms:
            measure_params['err_obs_ra'] = 300e-3/3600.0
            measure_params['err_obs_dec'] = 275e-3/3600.0
            measure_params['aperture_size'] = 1.56
            measure_params['snr'] = 24.8
        self.test_measure2 = SourceMeasurement.objects.create(pk=2, **measure_params)

        # These measurements are precoverys, earlier in time but discovered later
        # i.e. larger value of the primary keys

        frame_params = { 'sitecode' : 'F51',
                         'instrument' : '',
                         'filter' : 'r',
                         'filename' : '',
                         'midpoint' : '2015-03-21 06:00:00',
                         'block' : None
                        }
        if rms:
            frame_params['astrometric_catalog'] = '2MASS'
            frame_params['photometric_catalog'] = '2MASS'
        self.test_precovery_frame = Frame.objects.create(pk=3, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_precovery_frame,
                           'obs_ra' : 62.2,
                           'obs_dec' : -11.05,
                           'obs_mag' : 21.5,
                           'err_obs_mag' : 0.01
                         }
        if rms:
            measure_params['err_obs_ra'] = 90e-3/3600.0
            measure_params['err_obs_dec'] = 90e-3/3600.0
        self.test_measure3 = SourceMeasurement.objects.create(pk=3, **measure_params)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_finddata_page(self):

        # Setup
        self.insert_test_extra_test_body()
        self.insert_test_measurements()

        # A user, Petr, is interested in reanalyzing data for an existing object

        # He goes to the home page and performs a search for that object
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCO NEOx', self.browser.title)
        inputbox = self.get_item_input_box("id_target_search")
        inputbox.send_keys('65803')
        searchbutton = self.get_item_input_box("id_search_submit")
        searchbutton.click()

        # He is taken to a page with the search results on it.
        search_url = self.live_server_url + '/search/?q=' + \
            self.body2.name
        self.assertEqual(self.browser.current_url, search_url)
        self.assertIn('Targets | LCO NEOx', self.browser.title)

        self.browser.implicitly_wait(5)
        # He sees that the target he wants is in the table and clicks on it
        self.check_for_header_in_table('id_targets',
            'Name Type Origin Ingest date')
        testlines = [u'N999r0q Candidate Minor Planet Center 11 May 2015, 17:20',
                     u'65803 NEO NASA 14 Aug 2018, 17:45']
        self.check_for_row_not_in_table('id_targets', testlines[0])
        self.check_for_row_in_table('id_targets', testlines[1])

        link = self.browser.find_element_by_partial_link_text('65803')
        target_url = "{0}{1}".format(self.live_server_url, reverse('target', kwargs={'pk': 2}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)
        with self.wait_for_page_load(timeout=10):
            link.click()

        # He is taken to a page with the object's details on it.
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn(self.body2.full_name(), header_text)

        # He sees a link that says it will find the data
        # available for this object.
        link = self.browser.find_element_by_id('find-data')
        target_url = "{0}{1}".format(self.live_server_url, reverse('finddata', kwargs={'pk': 2}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()

        self.assertIn(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Find Data for: ' + self.body2.current_name(), header_text)

        self.check_for_header_in_table('id_measurements',
            'Name Date/time RA Dec Magnitude Filter Site Code')

        # He sees that there is a table in which are the original
        # discovery observations from WISE (obs. code C51) and from
        # the LCOGT follow-up network.
        testlines = [u'N999r0q 2015 04 20.75000 02 48 24.00 -30 03 00.0 21.1 w K91',
                     u'N999r0q 2015 04 20.75000 02 48 24.00 -30 03 00.0 21.1 w K91']
        self.check_for_row_in_table('id_measurements', testlines[0])
        self.check_for_row_in_table('id_measurements', testlines[1])

        # Satisfied that the planet is safe from this asteroid, he
        # leaves.
