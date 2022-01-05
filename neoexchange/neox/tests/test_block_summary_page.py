"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

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
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException


class BlockSummaryTest(FunctionalTest):

    def setUp(self):
        # Create a user to test login
        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name = 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()
        super(BlockSummaryTest, self).setUp()

    def test_can_view_block_summary(self):
        # A seasoned user comes along to the site.
        self.browser.get(self.live_server_url)

        # He sees no link to EFFICIENCY on the front page.
        try:
            link = self.browser.find_element_by_xpath(u'//a[text()="Efficiency"]')
            raise Exception("This should be a hidden link")
        except NoSuchElementException:
            pass

        # He instead manually enters the url for the page with the efficiency
        # details.
        url = self.live_server_url + '/block/' + 'summary/'
        self.browser.get(url)
        self.browser.implicitly_wait(3)
        new_url = self.live_server_url + '/block/' + 'summary/'
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        self.assertEqual(str(new_url), url)

        # He notices the page title has the name of the site and the header
        # states he is on the observing block summary page.
        self.assertIn('Blocks summary | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Block Summary', header_text)

        # He notices there is a plot with the number of blocks
        # "not observed / total requested" for each observing proposal.
