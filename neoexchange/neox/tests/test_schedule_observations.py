from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_filter_list

from datetime import datetime
from django.test.client import Client
from django.core.urlresolvers import reverse
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
        self.assertIn('ELP 1.0m - V37; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn('2.52 "/min', speed)
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('12', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('60.0', exp_length)

        # At this point, a 'Schedule this object' button appears
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

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
        self.assertIn('ELP 1.0m - V37; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-03-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page throws an error that observing window cannot end in the past
        error_msg = self.browser.find_element_by_class_name('errorlist').text
        self.assertIn("Window cannot start in the past", error_msg)

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
        self.assertIn('ELP 1.0m - V37; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn('2.52 "/min', speed)
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('12', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('60.0', exp_length)

        # Bart wants to change the slot length and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_name('slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('25.')
        self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length and the Schedule button again
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('25.', slot_length)
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)

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
        self.assertIn('ELP 1.0m - V37; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn('2.52 "/min', speed)
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('12', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('60.0', exp_length)

        # Bart wants to change the slot length so it is very short and recalculate the number of exposures
        slot_length_box = self.browser.find_element_by_name('slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('2.')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and slot length is automatically adjusted to minimum possible length
        new_slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('3.5', new_slot_length)
        warn_num = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('warning').text
        self.assertIn('1', warn_num)

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
        self.assertIn('This Site/Telescope combination is not currently available.', error_msg)

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
        self.assertIn('ELP 1.0m - V37; (McDonald, Texas)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP 1.0m - V37; (McDonald, Texas)')

        MockDateTime.change_date(2015, 4, 20)
        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('single-submit').click()

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn('2.52 "/min', speed)
        self.assertIn('2.52 "/exp', speed)
        speed_warn = self.browser.find_element_by_class_name('warning').text
        self.assertIn('2.52 "/exp', speed_warn)
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('22.5', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('12', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').get_attribute('value')
        self.assertIn('60.0', exp_length)
        vis = self.browser.find_element_by_id('id_visibility').find_element_by_class_name('kv-value').text
        self.assertIn('62', vis)
        self.assertIn('2.0 hrs', vis)
        moon_sep = self.browser.find_element_by_id('id_moon').find_element_by_class_name('kv-value').text
        self.assertIn('106.3', moon_sep)

        # Bart wants to change the slot length to less than 1 exposure.
        slot_length_box = self.browser.find_element_by_name('slot_length')
        slot_length_box.clear()
        slot_length_box.send_keys('1')
        self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct slot length
        slot_length = self.browser.find_element_by_name('slot_length').get_attribute('value')
        self.assertIn('3.5', slot_length)

        # Bart wants to change the max airmass to 1.5 and min moon dist to 160.
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_name('max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('1.5')
        moon_box = self.browser.find_element_by_name('min_lunar_dist')
        moon_box.clear()
        moon_box.send_keys('160')
        self.browser.find_element_by_id("id_edit_button").click()

        # The page refreshes and we get correct hours visible and a warning on moon dist
        vis = self.browser.find_element_by_id('id_visibility').find_element_by_class_name('kv-value').text
        self.assertIn('1.5 hrs', vis)
        moon_warn = self.browser.find_element_by_id('id_moon').find_element_by_class_name('warning').text
        self.assertIn('106.3', moon_warn)

        # Bart wants to change the max airmass to 1.1 and gets a warning
        self.browser.find_element_by_id("advanced-switch").click()
        airmass_box = self.browser.find_element_by_name('max_airmass')
        airmass_box.clear()
        airmass_box.send_keys('1.1')
        self.browser.find_element_by_id("id_edit_button").click()
        vis = self.browser.find_element_by_id('id_visibility').find_element_by_class_name('warning').text
        self.assertIn('Target Not Visible', vis)

        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object', submit)
