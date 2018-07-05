import os
from math import radians
from .base import FunctionalTest
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from bs4 import BeautifulSoup
#from selenium import webdriver
from mock import patch

from neox.tests.mocks import MockDateTime, mock_lco_authenticate, \
    mock_fetch_filter_list, mock_submit_to_scheduler
from neox.auth_backend import update_proposal_permissions
from astrometrics.sources_subs import fetch_flux_standards
from core.views import create_calib_sources
from core.models import Proposal, StaticSource


@patch('core.views.fetch_filter_list', mock_fetch_filter_list)
@patch('core.forms.fetch_filter_list', mock_fetch_filter_list)
class TestCalibrationSources(FunctionalTest):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.flux_standards = fetch_flux_standards(test_flux_page)
        num_created = create_calib_sources(self.flux_standards)
        solar_standards = { 'Landolt SA98-978' : { 'ra_rad' : radians(102.8916666666666),
                                                   'dec_rad' : radians(-0.1925),
                                                   'mag' : 10.5,
                                                   'spec_type' : 'G2V'},
                          }
        num_created = create_calib_sources(solar_standards, StaticSource.SOLAR_STANDARD)

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

        super(TestCalibrationSources, self).setUp()

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

    def test_can_view_calibsources(self):

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He notices there are several calibration sources that are listed
        self.check_for_header_in_table('id_calibsources',
            'Name R.A. Dec. V Mag. Spectral Type Source Type')
        testlines = ['HR9087 00:01:49.42 -03:01:39.0 5.12 B7III Spectrophotometric standard',
                     'CD-34d241 00:41:46.92 -33:39:08.5 11.23 F Spectrophotometric standard',
                     'LTT2415 05:56:24.30 -27:51:28.8 12.21 None Spectrophotometric standard',
                     'Landolt SA98-978 06:51:34.00 -00:11:33.0 10.50 G2V Solar spectrum standard' ]
        self.check_for_row_in_table('id_calibsources', testlines[0])
        self.check_for_row_in_table('id_calibsources', testlines[1])
        self.check_for_row_in_table('id_calibsources', testlines[2])
        self.check_for_row_in_table('id_calibsources', testlines[3])

        # Satisfied that there are many potential calibration sources to choose
        # from, he goes for a beer.

    @patch('core.views.datetime', MockDateTime)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.submit_block_to_scheduler', mock_submit_to_scheduler)
    def test_can_schedule_calibsource(self):
        self.test_login()
        MockDateTime.change_datetime(2018, 5, 22, 5, 0, 0)

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He decides he would like to schedule a standard on FTN
        # He sees a Schedule Calibration Observations button
        link = self.browser.find_element_by_id('schedule-calib-ftn-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra', kwargs={'instrument_code': 'F65-FLOYDS'}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Calibration Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He sees a suggested standard comes up and the parameters are displayed
        self.assertIn('NEOx spectroscopy scheduling | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('section-title').text
        self.assertIn('Parameters for: HR9087', header_text)
        self.assertIn("00:01:49.42", header_text)
        self.assertIn("-03:01:39.0", header_text)
        self.assertIn('V=5.1', header_text)

        # Liking the selected star, he clicks Verify and is taken to a confirmation
        # page
        button = self.browser.find_element_by_id('verify-scheduling')
        with self.wait_for_page_load(timeout=10):
            button.click()

        self.assertIn('NEOx calibration scheduling | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn("HR9087: Confirm Scheduling", header_text)
        filter_pattern = self.browser.find_element_by_id("id_filter_pattern").get_attribute('value')
        self.assertIn("slit_6.0as", filter_pattern)
        exp_length = self.browser.find_element_by_id('id_exp_length').find_element_by_class_name('kv-value').text
        self.assertIn('180.0 secs', exp_length)
        # Liking the selected star parameters, he clicks Submit and is returned to the
        # home page
        button = self.browser.find_element_by_id('id_submit_button')
        with self.wait_for_page_load(timeout=10):
            button.click()

        target_url = "{0}{1}".format(self.live_server_url, reverse('home'))
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # Satisfied, he goes to find a currywurst

    @patch('core.views.datetime', MockDateTime)
    @patch('core.forms.datetime', MockDateTime)
    @patch('core.views.submit_block_to_scheduler', mock_submit_to_scheduler)
    def test_can_schedule_calibsource_fts(self):
        self.test_login()
        MockDateTime.change_datetime(2018, 5, 22, 5, 0, 0)

        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He decides he would like to schedule a standard on FTS
        # He sees a Schedule Calibration Observations button
        link = self.browser.find_element_by_id('schedule-calib-fts-obs')
        target_url = "{0}{1}".format(self.live_server_url, reverse('schedule-calib-spectra', kwargs={'instrument_code': 'E10-FLOYDS'}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Schedule Calibration Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, actual_url)

        # He sees a suggested standard comes up and the parameters are displayed
        self.assertIn('NEOx spectroscopy scheduling | LCO NEOx', self.browser.title)
        self.assertIn("E10-FLOYDS", self.browser.current_url)
        header_text = self.browser.find_element_by_class_name('section-title').text
        self.assertIn('Parameters for: CD-34d241', header_text)
        self.assertIn("00:41:46.92", header_text)
        self.assertIn("-33:39:08.5", header_text)
        self.assertIn('V=11.2', header_text)

        # Liking the selected star, he clicks Verify and is taken to a confirmation
        # page
        button = self.browser.find_element_by_id('verify-scheduling')
        with self.wait_for_page_load(timeout=10):
            button.click()

        self.assertIn('NEOx calibration scheduling | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn("CD-34d241: Confirm Scheduling", header_text)
        filter_pattern = self.browser.find_element_by_id("id_filter_pattern").get_attribute('value')
        self.assertIn("slit_6.0as", filter_pattern)
        exp_length = self.browser.find_element_by_id('id_exp_length').find_element_by_class_name('kv-value').text
        self.assertIn('180.0 secs', exp_length)
        # Liking the selected star parameters, he clicks Submit and is returned to the
        # home page
        button = self.browser.find_element_by_id('id_submit_button')
        with self.wait_for_page_load(timeout=10):
            button.click()

        target_url = "{0}{1}".format(self.live_server_url, reverse('home'))
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # Satisfied, he goes to find a currywurst
