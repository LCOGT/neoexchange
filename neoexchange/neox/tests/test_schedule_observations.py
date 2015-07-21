from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from mock import patch
from neox.tests.mocks import MockDateTime
from datetime import datetime
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from core.models import Body, Proposal

class ScheduleObservations(FunctionalTest):

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
        super(ScheduleObservations,self).setUp()

    def tearDown(self):
        self.bart.delete()
        super(ScheduleObservations,self).tearDown()

    def login(self):
        test_login = self.client.login(username=self.username, password=self.password)
        self.assertEqual(test_login, True)

    def test_login(self):
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        self.browser.find_element_by_xpath('//input[@value="login"]').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')

    def test_logout(self):
        self.test_login()
        logout_link = self.browser.find_element_by_partial_link_text('Logout')
        logout_link.click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        

# Monkey patch the datetime used by forms otherwise it fails with 'window in the past'

    @patch('core.forms.datetime', MockDateTime)
    def test_can_schedule_observations(self):
        self.test_login()

        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Schedule Observations button
        link = self.browser.find_element_by_link_text('Schedule Observations')
        target_url = self.live_server_url + reverse('schedule-body',kwargs={'pk':1})
        self.assertEqual(link.get_attribute('href'), target_url)

        # He clicks the link to go to the Schedule Observations page
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
        self.assertIn('ELP (V37)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP (V37)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        datebox.send_keys(Keys.ENTER)

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn("2.52 '/min", speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').find_element_by_class_name('kv-value').text
        self.assertIn('22.5 mins', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('18', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').find_element_by_class_name('kv-value').text
        self.assertIn('50.0 secs', exp_length)

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
        link = self.browser.find_element_by_partial_link_text('Schedule Observations')
        link.click()
        self.wait_for_element_with_id('username')
        new_url = self.browser.current_url
        self.assertIn('login/', str(new_url))
