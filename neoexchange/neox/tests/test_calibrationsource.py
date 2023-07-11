"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
from math import radians
from datetime import datetime

from .base import FunctionalTest
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from bs4 import BeautifulSoup
# from selenium import webdriver
from mock import patch
from freezegun import freeze_time
from selenium.common.exceptions import NoSuchElementException

from neox.tests.mocks import MockDateTime, mock_lco_authenticate, \
    mock_fetch_filter_list, mock_submit_to_scheduler, MockDate
from neox.auth_backend import update_proposal_permissions
from astrometrics.sources_subs import fetch_flux_standards
from core.views import create_calib_sources
from core.models import Proposal, StaticSource
from core.utils import save_to_default


@patch('core.views.fetch_filter_list', mock_fetch_filter_list)
@patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
class TestCalibrationSources(FunctionalTest):

    def setUp(self):
        settings.MEDIA_ROOT = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))

        # Create a user to test login
        self.insert_test_proposals()
        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name = 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()
        # Add Bart to the right proposal
        update_proposal_permissions(self.bart, [{'code': self.neo_proposal.code}])

        super(TestCalibrationSources, self).setUp()

    def add_new_calib_sources(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.flux_standards = fetch_flux_standards(test_flux_page)
        num_created = create_calib_sources(self.flux_standards)
        solar_standards = {'Landolt SA98-978': {'ra_rad': radians(102.8916666666666),
                                                'dec_rad': radians(-0.1925),
                                                'mag': 10.5,
                                                'spectral_type': 'G2V'},
                           }
        num_created = create_calib_sources(solar_standards, StaticSource.SOLAR_STANDARD)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login(self):
        test_login = self.client.login(username=self.username, password=self.password)
        self.assertEqual(test_login, True)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def test_login(self):
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')

    def test_logout(self):
        self.test_login()
        logout_link = self.browser.find_element_by_partial_link_text('Logout')
        with self.wait_for_page_load(timeout=10):
            logout_link.click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')

    @freeze_time(datetime(2018, 5, 22, 5, 0, 0))
    def test_can_view_calibsources(self):
        self.add_new_calib_sources()

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He notices the position of the Solar antinode is given.
        expected_coords = ['15:55:45.42', '-20:22:15.3']
        coords_text = self.browser.find_element_by_id('anti_solar_point').text
        for coor in expected_coords:
            self.assertIn(coor, coords_text)

        # He notices there are several calibration sources that are listed
        self.check_for_header_in_table('id_calibsources',
            'Name R.A. Dec. V Mag. Spectral Type Source Type')
        testlines = ['HR9087 00:01:49.42 -03:01:39.0 5.12 B7III Spectrophotometric standard',
                     'CD-34d241 00:41:46.92 -33:39:08.5 11.23 F Spectrophotometric standard',
                     'LTT2415 05:56:24.30 -27:51:28.8 12.21 Spectrophotometric standard',
                     'Landolt SA98-978 06:51:34.00 -00:11:33.0 10.50 G2V Solar spectrum standard']
        self.check_for_row_in_table('id_calibsources', testlines[0])
        self.check_for_row_in_table('id_calibsources', testlines[1])
        self.check_for_row_in_table('id_calibsources', testlines[2])
        self.check_for_row_in_table('id_calibsources', testlines[3])

        # Satisfied that there are many potential calibration sources to choose
        # from, he goes for a beer.

    @freeze_time(datetime(2018, 9, 21, 5, 0, 0))
    @patch('core.views.submit_block_to_scheduler', mock_submit_to_scheduler)
    def test_can_schedule_calibsource(self):
        self.add_new_calib_sources()
        self.test_login()

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He decides he would like to schedule a standard on FTN
        # He sees a Schedule Calibration Observations button
        link = self.browser.find_element_by_id('schedule-calib-ftn-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra', kwargs={'instrument_code': 'F65-FLOYDS', 'pk': '-'}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Calibration Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He sees a suggested standard comes up and the parameters are displayed
        self.assertIn('NEOx spectroscopy scheduling | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('section-title').text
        self.assertIn('Parameters for: HR9087', header_text)
        self.assertIn("00:01:49.42", header_text)
        self.assertIn("-03:01:39.0", header_text)
        self.assertIn('V=5.1', header_text)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2018-09-22')

        # Liking the selected star, he clicks Verify and is taken to a confirmation
        # page
        button = self.browser.find_element_by_id('verify-scheduling')
        with self.wait_for_page_load(timeout=10):
            button.click()

        self.assertIn('NEOx calibration scheduling | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn("HR9087: Confirm Scheduling", header_text)
        filter_pattern = self.browser.find_element_by_id("id_filter_pattern").get_attribute('value')
        self.assertIn("slit_6.0as", filter_pattern)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('180.0', exp_length)
        # Liking the selected star parameters, he clicks Submit and is returned to the
        # home page
        button = self.browser.find_element_by_id('id_submit_button')
        with self.wait_for_page_load(timeout=10):
            button.click()

        target_url = "{0}{1}".format(self.live_server_url, reverse('home'))
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # Satisfied, he goes to find a currywurst

    @freeze_time(datetime(2018, 9, 21, 5, 0, 0))
    @patch('core.views.submit_block_to_scheduler', mock_submit_to_scheduler)
    def test_can_schedule_calibsource_fts(self):
        self.add_new_calib_sources()
        self.test_login()

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He decides he would like to schedule a standard on FTS
        # He sees a Schedule Calibration Observations button
        link = self.browser.find_element_by_id('schedule-calib-fts-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra', kwargs={'instrument_code': 'E10-FLOYDS', 'pk': '-'}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Calibration Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He sees a suggested standard comes up and the parameters are displayed
        self.assertIn('NEOx spectroscopy scheduling | LCO NEOx', self.browser.title)
        self.assertIn("E10-FLOYDS", self.browser.current_url)
        header_text = self.browser.find_element_by_class_name('section-title').text
        self.assertIn('Parameters for: CD-34d241', header_text)
        self.assertIn("00:41:46.92", header_text)
        self.assertIn("-33:39:08.5", header_text)
        self.assertIn('V=11.2', header_text)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2018-09-22')

        # Liking the selected star, he clicks Verify and is taken to a confirmation
        # page
        button = self.browser.find_element_by_id('verify-scheduling')
        with self.wait_for_page_load(timeout=10):
            button.click()

        self.assertIn('NEOx calibration scheduling | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn("CD-34d241: Confirm Scheduling", header_text)
        filter_pattern = self.browser.find_element_by_id("id_filter_pattern").get_attribute('value')
        self.assertIn("slit_6.0as", filter_pattern)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('180.0', exp_length)
        # Liking the selected star parameters, he clicks Submit and is returned to the
        # home page
        button = self.browser.find_element_by_id('id_submit_button')
        with self.wait_for_page_load(timeout=10):
            button.click()

        target_url = "{0}{1}".format(self.live_server_url, reverse('home'))
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # Satisfied, he goes to find a currywurst

    @patch('core.views.datetime', MockDateTime)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.submit_block_to_scheduler', mock_submit_to_scheduler)
    def test_can_schedule_specific_calibsource(self):
        self.add_new_calib_sources()
        self.test_login()
        MockDateTime.change_datetime(2019, 1, 21, 5, 0, 0)

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He decides he would like to schedule a Solar Analog
        # He sees a Solar Analog Only button
        link = self.browser.find_element_by_id('show-solar-standards')
        target_url = "{0}{1}".format(self.live_server_url, reverse('solarstandard-view'))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        table_text = self.browser.find_element_by_id('id_calibsources').text
        self.assertIn('Spectrophotometric', table_text)

        # He clicks the button to remove non-solar statndards
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        table_text = self.browser.find_element_by_id('id_calibsources').text
        self.assertNotIn('Spectrophotometric', table_text)

        # He picks a star
        link = self.browser.find_element_by_link_text('Landolt SA98-978')
        target = StaticSource.objects.filter(name='Landolt SA98-978')
        target_key = target[0].id
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource' , kwargs={'pk': target_key}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to visit the Solar Standard detail page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He sees the detail page for his standard
        table_text = self.browser.find_element_by_id('id_staticsource_detail').text
        self.assertIn('06:51:34.00', table_text)
        self.assertIn('G2V', table_text)
        self.assertIn('Solar spectrum standard', self.browser.find_element_by_class_name("section-title").text)

        # He schedules a spectra
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra', kwargs={'instrument_code': 'E10-FLOYDS', 'pk': target_key}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to schedule a spectra
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He sees the scheduling parameters are displayed
        self.assertIn('NEOx spectroscopy scheduling | LCO NEOx', self.browser.title)
        self.assertIn("E10-FLOYDS", self.browser.current_url)
        header_text = self.browser.find_element_by_class_name('section-title').text
        self.assertIn('Parameters for: Landolt SA98-978', header_text)
        self.assertIn("06:51:34.00", header_text)
        self.assertIn("-00:11:33.0", header_text)
        self.assertIn('V=10.5', header_text)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2019-01-22')

        # Liking the selected star, he clicks Verify and is taken to a confirmation
        # page
        button = self.browser.find_element_by_id('verify-scheduling')
        with self.wait_for_page_load(timeout=10):
            button.click()

        self.assertIn('NEOx calibration scheduling | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn("Landolt SA98-978: Confirm Scheduling", header_text)
        filter_pattern = self.browser.find_element_by_id("id_filter_pattern").get_attribute('value')
        self.assertIn("slit_6.0as", filter_pattern)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('180.0', exp_length)
        # Liking the selected star parameters, he clicks Submit and is returned to the
        # home page
        button = self.browser.find_element_by_id('id_submit_button')
        with self.wait_for_page_load(timeout=10):
            button.click()

        target_url = "{0}{1}".format(self.live_server_url, reverse('home'))
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # Satisfied, he goes to find a currywurst

    @patch('core.views.datetime', MockDateTime)
    def test_can_view_calibsource_spectra(self):
        settings.MEDIA_ROOT = os.path.abspath('data')
        self.add_new_calib_sources()
        MockDateTime.change_datetime(2018, 5, 22, 5, 0, 0)

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He decides he would like to schedule a hot spectrophotometric standard
        test_line = 'HR9087 00:01:49.42 -03:01:39.0 5.12 B7III Spectrophotometric standard'
        self.check_for_row_in_table('id_calibsources', test_line)

        # He picks HR9087 as being a suitably hot star
        link = self.browser.find_element_by_link_text('HR9087')
        target = StaticSource.objects.get(name='HR9087')
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource', kwargs={'pk': target.pk}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to check the detail page to see if the spectrum
        # is suitable
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He sees the detail page for his standard
        table_text = self.browser.find_element_by_id('id_staticsource_detail').text
        self.assertIn('00:01:49.42', table_text)
        self.assertIn('-03:01:39.0', table_text)
        self.assertIn('B7III', table_text)
        self.assertIn('Spectrophotometric standard', self.browser.find_element_by_class_name("section-title").text)

        spec_plot = self.browser.find_element_by_name("spec_plot")
        self.assertNotIn("Target Frames", spec_plot.text)
        self.assertNotIn("Analog", spec_plot.text)

    @patch('core.views.datetime', MockDateTime)
    def test_can_view_best_calibsources(self):
        self.add_new_calib_sources()
        MockDateTime.change_datetime(2019, 10, 5, 22, 0, 0)

        # A new user, Curtis, goes to a calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        anti_solar_element = self.browser.find_element_by_id("anti_solar_point")
        anti_solar_point = "Current Anti-Solar Point: RA = 00:45:30.55 / Dec = +04:53:15.7"
        self.assertEqual(anti_solar_point, anti_solar_element.text)

        # He decides he would like to find a calibration standard to schedule
        # which will be up all night.
        # He sees a Show Best Standards button
        link = self.browser.find_element_by_id('show-best-standards')
        target_url = "{0}{1}".format(self.live_server_url, reverse('beststandards-view'))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        with self.wait_for_page_load(timeout=10):
            link.click()

        # He notices the page title has best suggested calibraions and the header
        # mentions calibrations for the current date
        self.assertIn('Best Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_id('night_banner').text
        self.assertIn('Best Calibration Sources for Oct. 5, 2019', header_text)

        # He checks there are some suitable targets for FTS
        test_lines = ['HR9087 00:01:49.42 -03:01:39.0 5.12 B7III',
                      'CD-34d241 00:41:46.92 -33:39:08.5 11.23 F']
        for test_line in test_lines:
            self.check_for_row_in_table('id_fts_calibsources', test_line)

        # Satisified, he cycles off into the sunset
