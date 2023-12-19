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
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_filter_list, mock_fetch_filter_list_no2m

from datetime import datetime
from django.test.client import Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from core.models import Body, Proposal
import shutil
import time
import os
from bs4 import BeautifulSoup
from astrometrics.sources_subs import fetch_flux_standards
from core.views import create_calib_sources

from neox.auth_backend import update_proposal_permissions


class ScheduleObservations(FunctionalTest):

    def setUp(self):
        settings.MEDIA_ROOT = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))
        self.flux_filepath = os.path.join(settings.MEDIA_ROOT, 'cdbs', 'ctiostan')
        orig_flux_file = os.path.join(self.flux_filepath, 'fsun.dat')
        self.new_flux_file = os.path.join(self.flux_filepath, 'fhd30455.dat')
        shutil.copy(orig_flux_file, self.new_flux_file)
        orig_flux_file = os.path.join(self.flux_filepath, 'fhr9087.dat')
        self.new_flux_file2 = os.path.join(self.flux_filepath, 'fcd_34d241.dat')
        shutil.copy(orig_flux_file, self.new_flux_file2)

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
        super(ScheduleObservations, self).setUp()

    def tearDown(self):
        self.bart.delete()
        if os.path.exists(self.new_flux_file):
            os.remove(self.new_flux_file)
        if os.path.exists(self.new_flux_file2):
            os.remove(self.new_flux_file2)
        super(ScheduleObservations, self).tearDown()

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

    def add_new_calib_sources(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.flux_standards = fetch_flux_standards(test_flux_page)
        num_created = create_calib_sources(self.flux_standards)

# Monkey patch the datetime used by forms otherwise it fails with 'window in the past'
# TAL: Need to patch the datetime in views also otherwise we will get the wrong
# semester and window bounds.

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_can_schedule_spec_observations(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He's concerned about calibrations!
        start_url = reverse('calibsource', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra', kwargs={'instrument_code': 'F65-FLOYDS', 'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.browser.implicitly_wait(10)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and FTN (F65)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        # Bart doesn't see the proposal to which he doesn't have permissions
        self.assertNotIn(self.test_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_instrument_code'))
        self.assertIn('Maui, Hawaii (FTN - F65)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('Maui, Hawaii (FTN - F65)')

        MockDateTime.change_date(2015, 12, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-12-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('7.0', magnitude)
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('7.6 hrs / 87°', vis)
        slot_length = self.browser.find_element_by_id('id_slot_length_row').find_element_by_class_name('kv-value').text
        self.assertIn('20', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('1', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('180.0', exp_length)
        snr = self.browser.find_element_by_id('id_snr_row').find_element_by_class_name('kv-value').text
        self.assertIn('2149.2', snr)

        # At this point, a 'Schedule this object' button appears
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    def test_cannot_schedule_observations(self):
        self.test_logout()

        # Bart tries the same as above but forgets to login
        # This has to be pk=2 as get_or_create in setUp makes new objects each
        # time for...reasons...
        start_url = reverse('calibsource', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)
        self.wait_for_element_with_id('main')
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        with self.wait_for_page_load(timeout=10):
            link.click()

        # self.wait_for_element_with_id('username')
        actual_url = self.browser.current_url
        target_url = '/login/'
        self.assertIn(target_url, actual_url)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_observations_past(self):
        self.test_login()
        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('calibsource', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra', kwargs={'instrument_code': 'F65-FLOYDS', 'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.browser.implicitly_wait(10)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        # Bart doesn't see the proposal to which he doesn't have permissions
        self.assertNotIn(self.test_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_instrument_code'))
        self.assertIn('Siding Spring, Aust. (FTS - E10)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('Siding Spring, Aust. (FTS - E10)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-03-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page throws an error that observing window cannot end in the past
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn("Window cannot start in the past", error_msg)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_edit_block(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('calibsource', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra',
                                                                   kwargs={'instrument_code': 'F65-FLOYDS', 'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.browser.implicitly_wait(10)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        # Bart doesn't see the proposal to which he doesn't have permissions
        self.assertNotIn(self.test_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_instrument_code'))
        self.assertIn('Siding Spring, Aust. (FTS - E10)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('Siding Spring, Aust. (FTS - E10)')

        MockDateTime.change_date(2015, 12, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-12-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and a series of values for magnitude, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('7.0', magnitude)
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.8 hrs / 40°', vis)
        slot_length = self.browser.find_element_by_id('id_slot_length_row').find_element_by_class_name('kv-value').text
        self.assertIn('20', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('1', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('180.0', exp_length)
        snr = self.browser.find_element_by_id('id_snr_row').find_element_by_class_name('kv-value').text
        self.assertIn('2068.6', snr)

        # Bart wants to change the exposure time and recalculate snr
        slot_length_box = self.browser.find_element_by_id('id_exp_length')
        slot_length_box.clear()
        slot_length_box.send_keys('25')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length and the Schedule button again
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('25', exp_length)
        slot_length = self.browser.find_element_by_id('id_slot_length_row').find_element_by_class_name('kv-value').text
        self.assertIn('18', slot_length)
        snr = self.browser.find_element_by_id('id_snr_row').find_element_by_class_name('kv-value').text
        self.assertIn('770.9', snr)

        # Bart wants to change the max airmass to 2.0 and min moon dist to 160.
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_id('id_max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('2.0')
        moon_box = self.browser.find_element_by_id('id_min_lunar_dist')
        moon_box.clear()
        moon_box.send_keys('160')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct hours visible and a warning on moon dist
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('4.6 hrs', vis)
        moon_warn = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('warning').text
        self.assertIn('35.8', moon_warn)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

        # Bart wants to change the max airmass to 1.1 and gets a warning
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_id('id_max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('1.1')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('warning').text
        self.assertIn('Target Not Visible', vis)

        # Fix issue:
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_id('id_max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('2.0')
        self.browser.find_element_by_id("id_edit_window").click()
        start_time_box = self.browser.find_element_by_id('id_start_time')
        start_time_box.clear()
        start_time_box.send_keys('2015-12-21T13:13:00')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        start_time = self.browser.find_element_by_id('id_start_time').get_attribute('value')
        self.assertEqual(start_time, '2015-12-21T13:13:00')


        # Bart wants to be a little &^%$ and stress test our group ID input
        group_id_box = self.browser.find_element_by_name("group_name")
        group_id_box.clear()
        bs_string = 'ຢູ່ໃກ້Γη小惑星‽'
        group_id_box.send_keys(bs_string)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        group_id = self.browser.find_element_by_id('id_group_name').get_attribute('value')
        self.assertEqual('HD 30455_E10-20151221_spectra', group_id)
        group_id_box = self.browser.find_element_by_name("group_name")
        group_id_box.clear()
        bs_string = 'rcoivny3q5r@@yciht8ycv9njcrnc87vy b0y98uxm9cyh8ycvn0fh 80hfcubfuh87yc 0nhfhxmhf7g 70h'
        group_id_box.send_keys(bs_string)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        group_id = self.browser.find_element_by_id('id_group_name').get_attribute('value')
        self.assertEqual(bs_string[:50], group_id)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list_no2m)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list_no2m)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_spectroscopy_missing_telescope(self):
        self.add_new_calib_sources()
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page for a calib source, but the best case telescope is missing
        start_url = reverse('calibsource-view')
        self.browser.get(self.live_server_url + start_url)
        link = self.browser.find_element_by_link_text('CD-34d241')
        with self.wait_for_page_load(timeout=10):
            link.click()

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        actual_url = link.get_attribute('href')
        self.assertIn('E10-FLOYDS', actual_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), actual_url)

        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and an error appears.
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn('The 2m0-FLOYDS-SciCam at E10 is not schedulable.', error_msg)

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('calibsource', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra',
                                                                   kwargs={'instrument_code': 'F65-FLOYDS', 'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        # Bart doesn't see the proposal to which he doesn't have permissions
        self.assertNotIn(self.test_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_instrument_code'))
        self.assertIn('Siding Spring, Aust. (FTS - E10)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('Siding Spring, Aust. (FTS - E10)')

        MockDateTime.change_date(2015, 12, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-12-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and an error appears.
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn('The 2m0-FLOYDS-SciCam at E10 is not schedulable.', error_msg)
