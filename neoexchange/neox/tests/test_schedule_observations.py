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
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_filter_list, mock_fetch_filter_list_no2m,\
    mock_build_visibility_source

from datetime import datetime
from django.test.client import Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Body, Proposal

from neox.auth_backend import update_proposal_permissions


class ScheduleObservations(FunctionalTest):

    def setUp(self):
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

    # Monkey patch the datetime used by forms otherwise it fails with 'window in the past'
    # TAL: Need to patch the datetime in views also otherwise we will get the wrong
    # semester and window bounds.
    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_can_schedule_observations(self):
        self.test_login()
        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
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

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.37 "/min', speed)
        binning = self.browser.find_element_by_id('id_bin_mode_row').find_element_by_class_name('kv-value').text
        self.assertIn('Full Chip, 1x1', binning)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('15', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('50.0', exp_length)

        # At this point, a 'Schedule this object' button appears
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_cannot_schedule_observations(self):
        self.test_logout()

        # Bart tries the same as above but forgets to login
        # This has to be pk=2 as get_or_create in setUp makes new objects each
        # time for...reasons...
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)
        self.wait_for_element_with_id('main')
        link = self.browser.find_element_by_id('schedule-obs')
        with self.wait_for_page_load(timeout=10):
            link.click()

        # self.wait_for_element_with_id('username')
        actual_url = self.browser.current_url
        target_url = '/login/'
        self.assertIn(target_url, actual_url)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
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
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
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

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-03-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page throws an error that observing window cannot end in the past
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn("Window cannot start in the past", error_msg)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
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
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.37 "/min', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('15', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('50.0', exp_length)

        # Bart wants to change the slot length and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('25.')
        self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length and the Schedule button again
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('25', slot_length)
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_short_block(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
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

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.37 "/min', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('15', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('50.0', exp_length)

        # Bart wants to change the slot length so it is very short and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('2.')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and slot length is automatically adjusted to minimum possible length
        new_slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('3.5', new_slot_length)
        warn_num = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('warning').text
        self.assertIn('1', warn_num)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list_no2m)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list_no2m)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_missing_telescope(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
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

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('TFN 0.4m - Z17,Z21; (Tenerife, Spain)', [option.text for option in site_choices.options])

        # He tries to use a telescope and site group that are currently unavailable
        site_choices.select_by_visible_text('TFN 0.4m - Z17,Z21; (Tenerife, Spain)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn("Z21 is not schedulable.", error_msg)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_spectroscopy(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Spectroscopic Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-spectra', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Spectroscopic Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and FTN (F65)
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
        datebox.send_keys('2016-01-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and a series of values for the Solar Analog appear at the bottom.
        snr = self.browser.find_element_by_id('id_snr_row').find_element_by_class_name('kv-value').text
        self.assertIn('0.0', snr)
        analog_sep = self.browser.find_element_by_id('id_solaranalog_sep_row').find_element_by_class_name('kv-value').text
        self.assertIn('54.3°', analog_sep)
        analog_exptime = self.browser.find_element_by_id('id_calibsource_exptime').get_attribute('value')
        self.assertIn('50', analog_exptime)

        # Bart wants to change the exposure time for the analog, but gets warned about it.
        slot_length_box = self.browser.find_element_by_id('id_calibsource_exptime')
        slot_length_box.clear()
        slot_length_box.send_keys('10')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        analog_exptime = self.browser.find_element_by_id('id_calibsource_exptime').get_attribute('value')
        self.assertIn('10', analog_exptime)
        sa_exptime_warn = self.browser.find_element_by_id('id_solaranalog_exptime_row').find_element_by_class_name('warning').text
        self.assertIn('Exposure Time', sa_exptime_warn)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list_no2m)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list_no2m)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_spectroscopy_missing_telescope(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Spectroscopic Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-spectra', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Spectroscopic Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and FTN (F65)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        # Bart doesn't see the proposal to which he doesn't have permissions
        self.assertNotIn(self.test_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_instrument_code'))
        self.assertIn('Siding Spring, Aust. (FTS - E10)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('Siding Spring, Aust. (FTS - E10)')

        # select the Solar Analog Option
        sa_box = self.browser.find_element_by_id('id_solar_analog')
        sa_box.click()

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2016-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and an error appears.
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn('The 2m0-FLOYDS-SciCam at E10 is not schedulable.', error_msg)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_spectroscopy_no_sa(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Spectroscopic Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-spectra', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Spectroscopic Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

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

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and a series of values for the Solar Analog appear at the bottom.
        snr = self.browser.find_element_by_id('id_snr_row').find_element_by_class_name('kv-value').text
        self.assertIn('5.2', snr)
        analog_warn = self.browser.find_element_by_id('id_no_solaranalog_row').find_element_by_class_name('warning').text
        self.assertIn('No Valid Solar Analog Found!'.upper(), analog_warn)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_spectroscopy_multiple_exps(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Spectroscopic Observations button
        link = self.browser.find_element_by_id('schedule-spectro-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-spectra', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Spectroscopic Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

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

        # He decides he wants to do many short exposures
        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        exp_length_box = self.get_item_input_box_and_clear('id_exp_length')
        exp_length_box.send_keys('30')
        exp_num_box = self.get_item_input_box_and_clear('id_exp_count')
        exp_num_box.send_keys('10')
        sa_checkbox = self.get_item_input_box('id_solar_analog')
        if sa_checkbox.is_selected():  # If checkbox is ticked
            sa_checkbox.click()  # to untick it
        tc_checkbox = self.get_item_input_box('id_too_mode')
        self.assertEqual(tc_checkbox.is_selected(), False)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('verify-scheduling').click()

        # The page refreshes and a series of values for the Spectroscopic observations
        slot_length = self.browser.find_element_by_id('id_slot_length_row').find_element_by_class_name('kv-value').text
        self.assertIn('26 mins', slot_length)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_advanced_options(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.37 "/min', speed)
        self.assertIn('1.98 "/exp', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('15', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('50.0', exp_length)
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('63', vis)
        self.assertIn('2.2 hrs', vis)
        moon_sep = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('kv-value').text
        self.assertIn('108.0', moon_sep)

        # Bart wants to change the slot length to less than 1 exposure.
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('1')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('3.5', slot_length)

        # Bart wants to change the max airmass to 1.5 and min moon dist to 160.
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_id('id_max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('1.5')
        moon_box = self.browser.find_element_by_id('id_min_lunar_dist')
        moon_box.clear()
        moon_box.send_keys('160')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct hours visible and a warning on moon dist
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('1.7 hrs', vis)
        moon_warn = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('warning').text
        self.assertIn('108.1', moon_warn)

        # Bart wants to change the max airmass to 1.1 and gets a warning
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_id('id_max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('1.1')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('warning').text
        self.assertIn('Target Not Visible', vis)
        error_message = self.browser.find_element_by_class_name("errorlist").text
        self.assertIn('Requested Observations will not fit within Scheduling Window.', error_message)

        # Fix issue:
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_id('id_max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('1.5')
        self.browser.find_element_by_id("id_edit_window").click()
        start_time_box = self.browser.find_element_by_id('id_start_time')
        start_time_box.clear()
        start_time_box.send_keys('2020-03-10T00:53:00')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # Bart wants to be a little &^%$ and stress test our group ID input
        group_id_box = self.browser.find_element_by_name("group_name")
        group_id_box.clear()
        bs_string = 'ຢູ່ໃກ້Γη小惑星‽'
        group_id_box.send_keys(bs_string)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        group_id = self.browser.find_element_by_id('id_group_name').get_attribute('value')
        self.assertEqual('N999r0q_V37-20150422', group_id)
        group_id_box = self.browser.find_element_by_name("group_name")
        group_id_box.clear()
        bs_string = 'rcoivny3q5r@@yciht8ycv9njcrnc87vy b0y98uxm9cyh8ycvn0fh 80hfcubfuh87yc 0nhfhxmhf7g 70h'
        group_id_box.send_keys(bs_string)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        group_id = self.browser.find_element_by_id('id_group_name').get_attribute('value')
        self.assertEqual(bs_string[:50], group_id)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_edit_windows(self):
        MockDateTime.change_date(2015, 2, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('TFN 0.4m - Z17,Z21; (Tenerife, Spain)', [option.text for option in site_choices.options])

        # site_choices.select_by_visible_text('TFN 0.4m - Z17,Z21; (Tenerife, Spain)')
        # site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')
        site_choices.select_by_visible_text('CPT 1.0m - K91-93; (Sutherland, S. Africa)')

        MockDateTime.change_date(2015, 2, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-02-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('35.0', exp_length)
        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('57', vis)
        self.assertIn('3.8 hrs', vis)
        utc_date = self.browser.find_element_by_id('id_utc_date_row').find_element_by_class_name('kv-value').text
        self.assertIn('2015-02-21', utc_date)
        start_time = self.browser.find_element_by_id('id_start_time').get_attribute('value')
        end_time = self.browser.find_element_by_id('id_end_time').get_attribute('value')
        self.assertIn('2015-02-20T23:12:00', start_time)
        self.assertIn('2015-02-21T02:58:00', end_time)

        self.browser.find_element_by_id("id_edit_window").click()
        end_time_box = self.browser.find_element_by_id('id_end_time')
        end_time_box.clear()
        end_time_box.send_keys('2015-02-20T23:53:00')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('57', vis)
        self.assertIn('3.8 hrs', vis)
        utc_date = self.browser.find_element_by_id('id_utc_date_row').find_element_by_class_name('kv-value').text
        self.assertIn('2015-02-21', utc_date)
        warning = self.browser.find_element_by_class_name('warning').text
        self.assertIn('2015-02-20T23:12:00', warning)
        start_time = self.browser.find_element_by_id('id_start_time').get_attribute('value')
        end_time = self.browser.find_element_by_id('id_end_time').get_attribute('value')
        self.assertIn('2015-02-20T23:12:00', start_time)
        self.assertIn('2015-02-20T23:53:00', end_time)

        start_time_box = self.browser.find_element_by_id('id_start_time')
        start_time_box.clear()
        start_time_box.send_keys('2015-02-24T23:00:00')
        end_time_box = self.browser.find_element_by_id('id_end_time')
        end_time_box.clear()
        end_time_box.send_keys('2015-02-25T06:53:00')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        vis = self.browser.find_element_by_id('id_visibility_row').find_element_by_class_name('kv-value').text
        self.assertIn('54', vis)
        self.assertIn('3.7 hrs', vis)
        utc_date = self.browser.find_element_by_id('id_utc_date_row').find_element_by_class_name('kv-value').text
        self.assertIn('2015-02-25', utc_date)
        start_time = self.browser.find_element_by_id('id_start_time').get_attribute('value')
        end_time = self.browser.find_element_by_id('id_end_time').get_attribute('value')
        self.assertIn('2015-02-24T23:24:00', start_time)
        self.assertIn('2015-02-25T03:08:00', end_time)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_generic_1m(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('------------ Any 1.0m ------------', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('------------ Any 1.0m ------------')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.49 "/min', speed)
        self.assertIn('1.87 "/exp', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('17', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('45.0', exp_length)
        moon_sep = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('kv-value').text
        self.assertIn('108.4', moon_sep)

        # Bart wants to use 2x2 binning for fast readout.
        bin_box = Select(self.browser.find_element_by_id('id_bin_mode'))
        bin_box.select_by_visible_text('Central 2k, 2x2')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct exp_count
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('23', num_exp)

        # Bart wants to change the slot length to less than 1 exposure.
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('1')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('3.0', slot_length)

        # Bart wants streaks
        exp_length_box = self.browser.find_element_by_id('id_exp_length')
        exp_length_box.clear()
        exp_length_box.send_keys('100')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        speed_warn = self.browser.find_element_by_class_name('warning').text
        self.assertIn('4.16 "/exp', speed_warn)

        # Bart wants to change the min moon dist to 160.
        self.browser.find_element_by_id("advanced-switch").click()
        moon_box = self.browser.find_element_by_id('id_min_lunar_dist')
        moon_box.clear()
        moon_box.send_keys('160')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct hours visible and a warning on moon dist
        moon_warn = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('warning').text
        self.assertIn('108.4', moon_warn)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    # @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    # @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    # @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    # @patch('core.forms.datetime', MockDateTime)
    # @patch('core.views.datetime', MockDateTime)
    # def test_schedule_page_generic_2m(self):
    #     MockDateTime.change_date(2015, 4, 20)
    #     self.test_login()
    #
    #     # make sure works for very bright targets too.
    #     self.body.abs_mag = 10
    #     self.body.save()
    #
    #     # Bart has heard about a new website for NEOs. He goes to the
    #     # page of the first target
    #     # (XXX semi-hardwired but the targets link should be being tested in
    #     # test_targets_validation.TargetsValidationTest
    #     start_url = reverse('target', kwargs={'pk': 1})
    #     self.browser.get(self.live_server_url + start_url)
    #
    #     # He sees a Schedule Observations button
    #     link = self.browser.find_element_by_id('schedule-obs')
    #     target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
    #     actual_url = link.get_attribute('href')
    #     self.assertEqual(actual_url, target_url)
    #
    #     # He clicks the link to go to the Schedule Observations page
    #     with self.wait_for_page_load(timeout=10):
    #         link.click()
    #     new_url = self.browser.current_url
    #     self.assertEqual(new_url, actual_url)
    #
    #     # He notices a new selection for the proposal and site code and
    #     # chooses the NEO Follow-up Network and ELP (V37)
    #     proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
    #     self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])
    #
    #     proposal_choices.select_by_visible_text(self.neo_proposal.title)
    #
    #     site_choices = Select(self.browser.find_element_by_id('id_site_code'))
    #     self.assertIn('------------ Any 2.0m ------------', [option.text for option in site_choices.options])
    #
    #     site_choices.select_by_visible_text('------------ Any 2.0m ------------')
    #
    #     MockDateTime.change_date(2015, 4, 20)
    #     datebox = self.get_item_input_box('id_utc_date')
    #     datebox.clear()
    #     datebox.send_keys('2015-04-21')
    #     with self.wait_for_page_load(timeout=10):
    #         self.browser.find_element_by_id('single-submit').click()
    #
    #     # The page refreshes and a series of values for magnitude, speed, slot
    #     # length, number and length of exposures appear
    #     magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
    #     self.assertIn('9.40', magnitude)
    #     speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
    #     self.assertIn('2.49 "/min', speed)
    #     self.assertIn('0.27 "/exp', speed)
    #     slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
    #     self.assertIn('6', slot_length)
    #     num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
    #     self.assertIn('4', num_exp)
    #     exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
    #     self.assertIn('6.5', exp_length)
    #     moon_sep = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('kv-value').text
    #     self.assertIn('108.4', moon_sep)
    #
    #     # Bart wants longer exposures
    #     exp_length_box = self.browser.find_element_by_id('id_exp_length')
    #     exp_length_box.clear()
    #     exp_length_box.send_keys('750')
    #     self.browser.find_element_by_id("id_edit_button").click()
    #     speed_warn = self.browser.find_element_by_class_name('warning').text
    #     self.assertIn('31.16 "/exp', speed_warn)
    #     slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
    #     self.assertIn('17.5', slot_length)
    #
    #     # Bart wants to change the min moon dist to 160.
    #     self.browser.find_element_by_id("advanced-switch").click()
    #     moon_box = self.browser.find_element_by_id('id_min_lunar_dist')
    #     moon_box.clear()
    #     moon_box.send_keys('160')
    #     self.browser.find_element_by_id("id_edit_button").click()
    #
    #     # The page refreshes and we get correct hours visible and a warning on moon dist
    #     moon_warn = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('warning').text
    #     self.assertIn('108.4', moon_warn)
    #
    #     submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
    #     self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_muscat_2m(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # make sure works for very bright targets too.
        self.body.abs_mag = 10
        self.body.save()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('FTN 2.0m - F65; (Maui, Hawaii ) [MuSCAT3]', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('FTN 2.0m - F65; (Maui, Hawaii ) [MuSCAT3]')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('9.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.35 "/min', speed)
        self.assertIn('1.19 "/exp', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('6', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('4', num_exp)
        gp_exp_length = self.browser.find_element_by_id('id_gp_explength').get_attribute('value')
        self.assertIn('30.5', gp_exp_length)
        rp_exp_length = self.browser.find_element_by_id('id_rp_explength').get_attribute('value')
        self.assertIn('30.5', rp_exp_length)
        moon_sep = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('kv-value').text
        self.assertIn('109.2', moon_sep)

        # Bart wants longer exposures in ip and zp
        ip_exp_length_box = self.browser.find_element_by_id('id_ip_explength')
        ip_exp_length_box.clear()
        ip_exp_length_box.send_keys('750')
        zp_exp_length_box = self.browser.find_element_by_id('id_zp_explength')
        zp_exp_length_box.clear()
        zp_exp_length_box.send_keys('750')
        self.browser.find_element_by_id("id_edit_button").click()
        speed_warn = self.browser.find_element_by_class_name('warning').text
        self.assertIn('29.32 "/exp', speed_warn)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('16.0', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('1', num_exp)
        gp_exp_length = self.browser.find_element_by_id('id_gp_explength').get_attribute('value')
        self.assertIn('30.5', gp_exp_length)
        ip_exp_length = self.browser.find_element_by_id('id_ip_explength').get_attribute('value')
        self.assertIn('750', ip_exp_length)

        # Bart wants to change the min moon dist to 160.
        self.browser.find_element_by_id("advanced-switch").click()
        moon_box = self.browser.find_element_by_id('id_min_lunar_dist')
        moon_box.clear()
        moon_box.send_keys('160')
        self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct hours visible and a warning on moon dist
        moon_warn = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('warning').text
        self.assertIn('109.2', moon_warn)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_generic_0m4(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('------------ Any 0.4m ------------', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('------------ Any 0.4m ------------')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.49 "/min', speed)
        self.assertIn('1.87 "/exp', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('32.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('31', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('45', exp_length)
        moon_sep = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('kv-value').text
        self.assertIn('108.4', moon_sep)

        # Bart wants to change the slot length to less than 1 exposure.
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('1')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('3.0', slot_length)

        # Bart wants to change the min moon dist to 160.
        self.browser.find_element_by_id("advanced-switch").click()
        moon_box = self.browser.find_element_by_id('id_min_lunar_dist')
        moon_box.clear()
        moon_box.send_keys('160')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct hours visible and a warning on moon dist
        moon_warn = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('warning').text
        self.assertIn('108.4', moon_warn)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_generic_1m_tootc(self):
        MockDateTime.change_date(2015, 4, 20)
        self.test_login()

        # Set the proposal to have Time Critical time available (only technically
        # possible from 2020A onwards but tests ~reality...)
        self.neo_proposal.time_critical = True
        self.neo_proposal.save()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('------------ Any 1.0m ------------', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('------------ Any 1.0m ------------')

        # He decides that this is a high priority target and need to be done
        # using Time Critical time so he ticks that box
        # select the Time Critical option
        tc_box = self.browser.find_element_by_id('id_too_mode')
        tc_box.click()

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        # He notes at the top that the proposal has now indicated that this will
        # be Time Critical (TC) time
        proposal = self.browser.find_element_by_id('id_proposal_row').find_element_by_class_name('kv-value').text
        self.assertIn('LCO2015A-009 (TC)', proposal)

        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.49 "/min', speed)
        self.assertIn('1.87 "/exp', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('17', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('45.0', exp_length)
        moon_sep = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('kv-value').text
        self.assertIn('108.4', moon_sep)

        # Bart wants to change the slot length to less than 1 exposure.
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('1')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('3.5', slot_length)

        # Bart wants to change the min moon dist to 160.
        self.browser.find_element_by_id("advanced-switch").click()
        moon_box = self.browser.find_element_by_id('id_min_lunar_dist')
        moon_box.clear()
        moon_box.send_keys('160')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct hours visible and a warning on moon dist
        moon_warn = self.browser.find_element_by_id('id_moon_row').find_element_by_class_name('warning').text
        self.assertIn('108.4', moon_warn)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)
