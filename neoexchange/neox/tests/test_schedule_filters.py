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
from selenium.common.exceptions import NoSuchElementException
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_filter_list, mock_build_visibility_source
from unittest import skipIf

from datetime import datetime
from django.test.client import Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Body, Proposal

from neox.auth_backend import update_proposal_permissions


@patch('core.views.fetch_filter_list', mock_fetch_filter_list)
@patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
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

# Monkey patch the datetime used by forms otherwise it fails with 'window in the past'
# TAL: Need to patch the datetime in views also otherwise we will get the wrong
# semester and window bounds.

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def test_can_schedule_observations(self):
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
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
        self.assertIn('9', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('100.0', exp_length)

        # At this point, a 'Schedule this object' button appears
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

        # there is an option to input a filter Pattern with a default value of 'w'
        filter_pattern = self.browser.find_element_by_id('id_filter_pattern').get_attribute("value")
        self.assertIn('w', filter_pattern)
        
        # There is a help option listing the proper input format and available filters
        expected_filters = 'air, ND, U, B, V, R, I, up, gp, rp, ip, zs, Y, w'
        filter_help = self.browser.find_element_by_id('id_filter_pattern_row').find_element_by_class_name('kv-key').get_attribute("name")
        self.assertEqual(expected_filters, filter_help)

        # There is a spot to input the number of iterations (default = number of exposures)
        with self.assertRaises(NoSuchElementException):
            pattern_iterations = self.browser.find_element_by_id('id_pattern_iterations_row').find_element_by_class_name('kv-value').text

        # Updating filter pattern updates the number of iterations
        iterations_expected = u'2.67'
        filter_pattern_box = self.browser.find_element_by_id('id_filter_pattern')
        filter_pattern_box.clear()
        filter_pattern_box.send_keys('V,I,R')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        pattern_iterations = self.browser.find_element_by_id('id_pattern_iterations_row').find_element_by_class_name('kv-value').text
        self.assertEqual(iterations_expected, pattern_iterations)

        # updating the slot length increases the number of iterations
        iterations_expected = u'14.0'
        slot_length_box = self.browser.find_element_by_id('id_slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('106')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()
        pattern_iterations = self.browser.find_element_by_id('id_pattern_iterations_row').find_element_by_class_name('kv-value').text
        self.assertEqual(iterations_expected, pattern_iterations)

        # cannot update filter pattern with unacceptable filters with incorrect syntax
        filter_pattern_box = self.browser.find_element_by_id('id_filter_pattern')
        filter_pattern_box.clear()
        filter_pattern_box.send_keys('42,V,v,W,w,gp fg, hj, k-t/g/h')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get an error
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn('42,v,W,fg,hj,k-t,g,h are not acceptable filters at this site.', error_msg)
