"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

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
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_filter_list, mock_build_visibility_source

from datetime import datetime
from django.test.client import Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Body, Proposal
from neox.auth_backend import update_proposal_permissions
import time


@patch('core.views.fetch_filter_list', mock_fetch_filter_list)
@patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
class ScheduleCadence(FunctionalTest):

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
        super(ScheduleCadence, self).setUp()

    def tearDown(self):
        self.bart.delete()
        super(ScheduleCadence, self).tearDown()

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
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_can_schedule_cadence(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest)
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

        # He sees a Switch to Cadence Observations button
        link = self.browser.find_element_by_id('single-switch')
        target_url = "{0}{1}{2}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}), '#')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to Switch to Cadence Observations
        link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a new selection for the proposal, site code,
        # UTC start date, UTC end date, period, and jitter and
        # chooses the NEO Follow-up Network, ELP (V37), period=2 hrs,
        # and jitter=0.25 hrs
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code_cad'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        # Bart doesn't see the proposal to which he doesn't have permissions
        self.assertNotIn(self.test_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        # He enters the correct details
        site_choices = Select(self.browser.find_element_by_id('id_site_code_cad'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])
        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        # Submits with a typo in the start date box
        MockDateTime.change_datetime(2015, 4, 20, 1, 30, 00)
        datebox = self.get_item_input_box('id_start_time')
        datebox.clear()
        datebox.send_keys('2005-04-21 01:30:00')

        MockDateTime.change_datetime(2015, 4, 20, 1, 30, 00)
        datebox = self.get_item_input_box('id_end_time')
        datebox.clear()
        datebox.send_keys('2015-04-21 07:30:00')

        jitterbox = self.get_item_input_box('id_jitter')
        jitterbox.clear()
        jitterbox.send_keys('0.5')

        periodbox = self.get_item_input_box('id_period')
        periodbox.clear()
        periodbox.send_keys('3.0')

        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//button[@id="cadence-submit"]').click()

        # The page refreshes and he reaches the schedule cadence page
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-cadence', kwargs={'pk': 1}))
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices that a series of values for magnitude, speed, slot
        # length, number and length of exposures, period, and jitter appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.37', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.42 "/min', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('10', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('95.0', exp_length)
        start_time = self.browser.find_element_by_id('id_start_time').get_attribute('value')
        self.assertIn('2015-04-20T01:30:00', start_time)
        jitter = self.browser.find_element_by_id('id_jitter').get_attribute('value')
        self.assertIn('0.5', jitter)
        period = self.browser.find_element_by_id('id_period').get_attribute('value')
        self.assertIn('3.0', period)
        cadence_cost = self.browser.find_element_by_id('id_cadence_cost_row').find_element_by_class_name('kv-value').text
        self.assertIn('10 / 3.75', cadence_cost)

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
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_edit_block(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest)
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

        # He sees a Switch to Cadence Observations button
        link = self.browser.find_element_by_id('single-switch')
        target_url = "{0}{1}{2}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}), '#')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to Switch to Cadence Observations
        link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a new selection for the proposal, site code,
        # UTC start date, UTC end date, period, and jitter and
        # chooses the NEO Follow-up Network, ELP (V37), period=2 hrs,
        # and jitter=0.5 hrs
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code_cad'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])
        # self.browser.implicitly_wait(15)

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code_cad'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        MockDateTime.change_datetime(2015, 4, 20, 1, 30, 00)
        datebox = self.get_item_input_box('id_start_time')
        datebox.clear()
        datebox.send_keys('2015-04-21 01:30:00')

        MockDateTime.change_datetime(2015, 4, 20, 7, 30, 00)
        datebox = self.get_item_input_box('id_end_time')
        datebox.clear()
        datebox.send_keys('2015-04-21 07:30:00')

        jitterbox = self.get_item_input_box('id_jitter')
        jitterbox.clear()
        jitterbox.send_keys('0.5')

        periodbox = self.get_item_input_box('id_period')
        periodbox.clear()
        periodbox.send_keys('1.0')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//button[@id="cadence-submit"]').click()

        # The page refreshes and he reaches the schedule cadence page
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-cadence', kwargs={'pk': 1}))
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices that a series of values for magnitude, speed, slot
        # length, number and length of exposures, period, and jitter appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.37 "/min', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('9', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('100.0', exp_length)
        jitter = self.browser.find_element_by_id('id_jitter').get_attribute('value')
        self.assertIn('0.5', jitter)
        period = self.browser.find_element_by_id('id_period').get_attribute('value')
        self.assertIn('1.0', period)
        cadence_cost = self.browser.find_element_by_id('id_cadence_cost_row').find_element_by_class_name('kv-value').text
        self.assertIn('2 / 0.75', cadence_cost)

        # Bart wants to change the slot length and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('25.')

        # He also wants to change the period to 0 because he thinks it will be funny
        periodbox = self.browser.find_element_by_id('id_period')
        periodbox.clear()
        periodbox.send_keys('0')

        # He wants the cadence to end a few days later
        self.browser.find_element_by_id("id_edit_window").click()
        datebox = self.get_item_input_box('id_end_time')
        datebox.clear()
        datebox.send_keys('2015-04-23 07:30:00')

        self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length and the Schedule button again
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('25.', slot_length)
        jitter = self.browser.find_element_by_id('id_jitter').get_attribute('value')
        self.assertIn('0.5', jitter)
        period = self.browser.find_element_by_id('id_period').get_attribute('value')
        self.assertIn('0.02', period)

        # He sees a warning about the large number of hours now required for this cadence. As well as a message about potential overlap
        cadence_cost = self.browser.find_element_by_id('id_cadence_cost_row').find_element_by_class_name('warning').text
        self.assertIn('2328 / 970', cadence_cost)
        period_warning = self.browser.find_element_by_id('id_period_row').find_element_by_class_name('warning').text
        self.assertIn('PERIOD', period_warning)
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_short_block(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest)
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

        # He sees a Switch to Cadence Observations button
        link = self.browser.find_element_by_id('single-switch')
        target_url = "{0}{1}{2}".format(self.live_server_url, reverse('schedule-body', kwargs={'pk': 1}), '#')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to Switch to Cadence Observations
        link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a new selection for the proposal, site code,
        # UTC start date, UTC end date, period, and jitter and
        # chooses the NEO Follow-up Network, ELP (V37), period=2 hrs,
        # and jitter=0.1 hrs
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code_cad'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code_cad'))
        self.assertIn('ELP 1.0m - V37,V39; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37,V39; (McDonald, Texas)')

        MockDateTime.change_datetime(2015, 4, 20, 1, 30, 00)
        datebox = self.get_item_input_box('id_start_time')
        datebox.clear()
        datebox.send_keys('2015-04-21 01:30:00')

        MockDateTime.change_datetime(2015, 4, 20, 7, 30, 00)
        datebox = self.get_item_input_box('id_end_time')
        datebox.clear()
        datebox.send_keys('2015-04-21 07:30:00')

        # He wants a very small jitter
        jitterbox = self.get_item_input_box('id_jitter')
        jitterbox.clear()
        jitterbox.send_keys('0.1')

        periodbox = self.get_item_input_box('id_period')
        periodbox.clear()
        periodbox.send_keys('1.0')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//button[@id="cadence-submit"]').click()

        # The page refreshes and he reaches the schedule cadence page
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-cadence', kwargs={'pk': 1}))
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices that a series of values for magnitude, speed, slot
        # length, number and length of exposures, period, and jitter appear
        magnitude = self.browser.find_element_by_id('id_magnitude_row').find_element_by_class_name('kv-value').text
        self.assertIn('20.40', magnitude)
        speed = self.browser.find_element_by_id('id_speed_row').find_element_by_class_name('kv-value').text
        self.assertIn('2.37 "/min', speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('kv-value').text
        self.assertIn('9', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('100.0', exp_length)

        # He notices the Jitter automatically adjusts to fit the slot length.
        jitter = self.browser.find_element_by_id('id_jitter').get_attribute('value')
        self.assertIn('0.39', jitter)
        period = self.browser.find_element_by_id('id_period').get_attribute('value')
        self.assertIn('1.0', period)
        cadence_cost = self.browser.find_element_by_id('id_cadence_cost_row').find_element_by_class_name('kv-value').text
        self.assertIn('2 / 0.75', cadence_cost)

        # Bart wants to change the slot length so it is very short and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('2.')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and slot length is automatically adjusted to minimum possible length
        new_slot_length = self.browser.find_element_by_id('id_slot_length').get_attribute('value')
        self.assertIn('4', new_slot_length)
        warn_num = self.browser.find_element_by_id('id_no_of_exps_row').find_element_by_class_name('warning').text
        self.assertIn('1', warn_num)
