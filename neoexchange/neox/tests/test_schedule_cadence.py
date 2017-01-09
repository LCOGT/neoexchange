from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from mock import patch
from neox.tests.mocks import MockDateTime, mock_rbauth_login

from datetime import datetime
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from core.models import Body, Proposal

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

    @patch('neox.auth_backend.rbauth_login', mock_rbauth_login)
    def login(self):
        test_login = self.client.login(username=self.username, password=self.password)
        self.assertEqual(test_login, True)

    @patch('neox.auth_backend.rbauth_login', mock_rbauth_login)
    def test_login(self):
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//input[@value="login"]').click()
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

        # He sees a Schedule Cadence button (?)

        # He clicks the link to go to the Schedule Cadence page (?)

        # He notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures, period, and jitter appear

        # At this point, a 'Schedule this object' button appears
