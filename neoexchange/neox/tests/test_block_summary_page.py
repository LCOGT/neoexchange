from .base import FunctionalTest
from django.test import TestCase
from django.core.urlresolvers import reverse
from selenium import webdriver
from mock import patch
from neox.tests.mocks import MockDateTime, mock_rbauth_login
from django.contrib.auth.models import User

class BlockSummaryTest(FunctionalTest):

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
        super(BlockSummaryTest,self).setUp()


    def test_can_view_block_summary(self):

        # A seasoned user comes along to the site.
        self.browser.get(self.live_server_url)

	# He sees a link to EFFICIENCY on the front page.
        link = self.browser.find_element_by_link_text('EFFICIENCY')
        url = self.live_server_url + '/block/' + 'summary/'
        self.assertEqual(link.get_attribute('href'), url)

	# He clicks the link and is taken to a page with the efficiency
        # details.
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.live_server_url + '/block/' + 'summary/'
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        self.browser.find_element_by_xpath('//input[@value="login"]').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        self.assertEqual(str(new_url), url)

        # He notices the page title has the name of the site and the header
        # states he is on the observing block summary page.
        self.assertIn('Blocks summary | LCOGT NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Block Summary', header_text)

        # He notices there is a plot with the number of blocks
        # "not observed / total requested" for each observing proposal.
