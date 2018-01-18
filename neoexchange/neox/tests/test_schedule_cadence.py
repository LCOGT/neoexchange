from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate

from datetime import datetime
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from core.models import Body, Proposal

import time

class ScheduleCadence(FunctionalTest):

    def setUp(self):
        # Create a user to test login
        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name= 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active=1
        self.bart.save()
        super(ScheduleCadence,self).setUp()

    def tearDown(self):
        self.bart.delete()
        super(ScheduleCadence,self).tearDown()

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
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_can_schedule_cadence(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest)
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body',kwargs={'pk':1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        #He sees a Switch to Cadence Observations button
        link = self.browser.find_element_by_id('single-switch')
        target_url = "{0}{1}{2}".format(self.live_server_url, reverse('schedule-body',kwargs={'pk':1}), '#')
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

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code_cad'))
        self.assertIn('McDonald, Texas (ELP - V37; Sinistro)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('McDonald, Texas (ELP - V37; Sinistro)')

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
        periodbox.send_keys('3.0')

        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//button[@id="cadence-submit"]').click()

        #The page refreshes and he reaches the schedule cadence page
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-cadence',kwargs={'pk':1}))
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices that a series of values for magnitude, speed, slot
        # length, number and length of exposures, period, and jitter appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn("2.63 '/min", speed)
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('13', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').find_element_by_class_name('kv-value').text
        self.assertIn('55.0 secs', exp_length)
        jitter = self.browser.find_element_by_id('id_jitter').find_element_by_class_name('kv-value').text
        self.assertIn('0.5', jitter)
        period = self.browser.find_element_by_id('id_period').find_element_by_class_name('kv-value').text
        self.assertIn('3.0', period)
        cadence_cost = self.browser.find_element_by_id('id_cadence_cost').find_element_by_class_name('kv-value').text
        self.assertIn('2 / 0.75', cadence_cost)

        # At this point, a 'Schedule this object' button appears
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object',submit)

    def test_cannot_schedule_observations(self):
        self.test_logout()

        # Bart tries the same as above but forgets to login
        # This has to be pk=2 as get_or_create in setUp makes new objects each
        # time for...reasons...
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)
        self.wait_for_element_with_id('main')
        link = self.browser.find_element_by_id('schedule-obs')
        with self.wait_for_page_load(timeout=10):
            link.click()

        # self.wait_for_element_with_id('username')
        actual_url = self.browser.current_url
        target_url = '/login/'
        self.assertIn(target_url, actual_url)

    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_edit_block(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest)
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body',kwargs={'pk':1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        #He sees a Switch to Cadence Observations button
        link = self.browser.find_element_by_id('single-switch')
        target_url = "{0}{1}{2}".format(self.live_server_url, reverse('schedule-body',kwargs={'pk':1}), '#')
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

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code_cad'))
        self.assertIn('McDonald, Texas (ELP - V37; Sinistro)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('McDonald, Texas (ELP - V37; Sinistro)')

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
        periodbox.send_keys('3.0')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//button[@id="cadence-submit"]').click()

        #The page refreshes and he reaches the schedule cadence page
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-cadence',kwargs={'pk':1}))
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices that a series of values for magnitude, speed, slot
        # length, number and length of exposures, period, and jitter appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn("2.63 '/min", speed)
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('13', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').find_element_by_class_name('kv-value').text
        self.assertIn('55.0 secs', exp_length)
        jitter = self.browser.find_element_by_id('id_jitter').find_element_by_class_name('kv-value').text
        self.assertIn('0.5', jitter)
        period = self.browser.find_element_by_id('id_period').find_element_by_class_name('kv-value').text
        self.assertIn('3.0', period)
        cadence_cost = self.browser.find_element_by_id('id_cadence_cost').find_element_by_class_name('kv-value').text
        self.assertIn('2 / 0.75', cadence_cost)

        # Bart wants to change the slot length and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_name('slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('25.')
        self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length and the Schedule button again
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('25.', slot_length)
        jitter = self.browser.find_element_by_id('id_jitter').find_element_by_class_name('kv-value').text
        self.assertIn('0.5', jitter)
        period = self.browser.find_element_by_id('id_period').find_element_by_class_name('kv-value').text
        self.assertIn('3.0', period)
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object',submit)

    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.datetime', MockDateTime)
    def test_schedule_page_short_block(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest)
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_id('schedule-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body',kwargs={'pk':1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        #He sees a Switch to Cadence Observations button
        link = self.browser.find_element_by_id('single-switch')
        target_url = "{0}{1}{2}".format(self.live_server_url, reverse('schedule-body',kwargs={'pk':1}), '#')
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

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code_cad'))
        self.assertIn('McDonald, Texas (ELP - V37; Sinistro)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('McDonald, Texas (ELP - V37; Sinistro)')

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
        periodbox.send_keys('3.0')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//button[@id="cadence-submit"]').click()

        #The page refreshes and he reaches the schedule cadence page
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-body-cadence',kwargs={'pk':1}))
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices that a series of values for magnitude, speed, slot
        # length, number and length of exposures, period, and jitter appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn("2.63 '/min", speed)
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('13', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').find_element_by_class_name('kv-value').text
        self.assertIn('55.0 secs', exp_length)
        jitter = self.browser.find_element_by_id('id_jitter').find_element_by_class_name('kv-value').text
        self.assertIn('0.5', jitter)
        period = self.browser.find_element_by_id('id_period').find_element_by_class_name('kv-value').text
        self.assertIn('3.0', period)
        cadence_cost = self.browser.find_element_by_id('id_cadence_cost').find_element_by_class_name('kv-value').text
        self.assertIn('2 / 0.75', cadence_cost)

        # Bart wants to change the slot length so it is very short and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_name('slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('2.')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get an error
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn('The slot length is too short',error_msg)
