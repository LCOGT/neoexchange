"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2020-2020 LCO

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


class TestAdmin(FunctionalTest):

    def setUp(self):
        # Create a superuser to test admin login
        self.insert_test_proposals()
        self.username = 'marge'
        self.password = 'simpson'
        self.email = 'marge@simpson.org'
        self.marge = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.marge.first_name = 'Marge'
        self.marge.last_name = 'Simpson'
        self.marge.is_active = 1
        self.marge.is_staff = 1
        self.marge.is_superuser = 1
        self.marge.save()
        # Add Marge to the right proposal
        update_proposal_permissions(self.marge, [{'code': self.neo_proposal.code}])
        super(TestAdmin, self).setUp()

    def tearDown(self):
        self.marge.delete()
        super(TestAdmin, self).tearDown()

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login(self):
        test_login = self.client.login(username=self.username, password=self.password)
        self.assertEqual(test_login, True)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def test_admin_login(self):
        self.browser.get('%s%s' % (self.live_server_url, '/admin/'))
        username_input = self.browser.find_element_by_id("id_username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("id_password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('container')

        # Check if we have landed on the logged-in page and we're logged in as
        # the right user
        target_url = "{0}{1}".format(self.live_server_url, reverse('admin:index'))
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        site_name = self.browser.find_element_by_id('site-name')
        self.assertIn("Django administration", site_name.text)
        user_bar = self.browser.find_element_by_id('user-tools')
        self.assertIn("WELCOME, " + self.username.upper(), user_bar.text)

    def test_admin_logout(self):
        self.test_admin_login()
        logout_link = self.browser.find_element_by_id('logout-form')
        with self.wait_for_page_load(timeout=10):
            logout_link.click()
        # Wait until response is received
        self.wait_for_element_with_id('container')

        page = self.browser.find_element_by_id('container')
        self.assertIn("Logged out", page.text)
