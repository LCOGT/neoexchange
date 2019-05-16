"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

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

from django.core.urlresolvers import reverse
from mock import patch

from neox.tests.mocks import mock_fetch_sfu, mock_fetchpage_and_make_soup


# Imported in the form creation so need to patch there

class SpectroscopicFeasibility(FunctionalTest):

    def tearDown(self):

        # Just quit otherwise alerts will pop-up on refresh
        self.browser.quit()

    @patch('core.forms.fetch_sfu', mock_fetch_sfu)
    def test_feasibility(self):
        # Jose has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Check Feasibility button
        link = self.browser.find_element_by_id('check-feasibility')
        target_url = "{0}{1}".format(self.live_server_url, reverse('feasibility', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Spectroscopy Feasibility page
        with self.wait_for_page_load(timeout=5):
            link.click()
        self.browser.implicitly_wait(2)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a form that allows the details of the proposed spectroscopic
        # observations to be entered. He sees that no details of SNR or slot
        # length are present yet
        self.assertEqual(len(self.browser.find_elements_by_id('id_snr')), 0)
        self.assertEqual(len(self.browser.find_elements_by_id('id_slot_length')), 0)
        self.assertEqual(len(self.browser.find_elements_by_link_text('SNR')), 0)
        self.assertEqual(len(self.browser.find_elements_by_link_text('Slot length')), 0)

        # Check the mock is working
        sfu = self.browser.find_element_by_id('id_sfu').get_attribute("value")
        self.assertEqual('42.0', sfu)

        # He adjusts the settings and calculates the feasibility
        site_choices = Select(self.browser.find_element_by_id('id_instrument_code'))
        self.assertIn('Maui, Hawaii (FTN - F65)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('Maui, Hawaii (FTN - F65)')
        magbox = self.get_item_input_box_and_clear('id_magnitude')
        magbox.send_keys('12')
        exptimebox = self.get_item_input_box_and_clear('id_exp_length')
        exptimebox.send_keys('300')
        moon_choices = Select(self.browser.find_element_by_id('id_moon_phase'))
        self.assertIn('Dark', [option.text for option in moon_choices.options])

        moon_choices.select_by_visible_text('Dark')
        with self.wait_for_page_load(timeout=10):
            magbox.send_keys(Keys.ENTER)

        # The page refreshes and a series of values for SNR, new transformed
        # magnitude, new passband and slot length appear
        snr = self.browser.find_element_by_id('id_snr').find_element_by_class_name('kv-value').text
        self.assertIn('273.2', snr)
        magnitude = self.browser.find_element_by_id('id_newmag').find_element_by_class_name('kv-value').text
        self.assertIn('12.0', magnitude)
        new_passband = self.browser.find_element_by_id('id_newpassband').find_element_by_class_name('kv-value').text
        self.assertIn('V', new_passband)
        slot_length = self.browser.find_element_by_id('id_slot_length').find_element_by_class_name('kv-value').text
        self.assertIn('23.0', slot_length)
        sky_mag = self.browser.find_element_by_id('id_skymag').find_element_by_class_name('kv-value').text
        self.assertIn('19.4', sky_mag)

        # He decides to see if the observations would be feasible in Bright time

        moon_choices = Select(self.browser.find_element_by_id('id_moon_phase'))
        moon_choices.select_by_visible_text('Bright')
        magbox = self.get_item_input_box('id_magnitude')
        calc_button = self.browser.find_element_by_id('id_submit')
        with self.wait_for_page_load(timeout=10):
            calc_button.click()

        # The page refreshes and a series of values for SNR, new transformed
        # magnitude, new passband and slot length appear
        snr = self.browser.find_element_by_id('id_snr').find_element_by_class_name('kv-value').text
        self.assertIn('268.3', snr)
        magnitude = self.browser.find_element_by_id('id_newmag').find_element_by_class_name('kv-value').text
        self.assertIn('12.0', magnitude)
        new_passband = self.browser.find_element_by_id('id_newpassband').find_element_by_class_name('kv-value').text
        self.assertIn('V', new_passband)
        slot_length = self.browser.find_element_by_id('id_slot_length').find_element_by_class_name('kv-value').text
        self.assertIn('23.0', slot_length)
        sky_mag = self.browser.find_element_by_id('id_skymag').find_element_by_class_name('kv-value').text
        self.assertIn('17.1', sky_mag)

        # He decides to see if the observations would be feasible at higher airmass

        moon_choices = Select(self.browser.find_element_by_id('id_moon_phase'))
        moon_choices.select_by_visible_text('Bright')
        airmassbox = self.get_item_input_box_and_clear('id_airmass')
        airmassbox.send_keys('2.0')
        with self.wait_for_page_load(timeout=10):
            airmassbox.send_keys(Keys.ENTER)

        # The page refreshes and a series of values for SNR, new transformed
        # magnitude, new passband and slot length appear
        snr = self.browser.find_element_by_id('id_snr').find_element_by_class_name('kv-value').text
        self.assertIn('253.9', snr)
        magnitude = self.browser.find_element_by_id('id_newmag').find_element_by_class_name('kv-value').text
        self.assertIn('12.0', magnitude)
        new_passband = self.browser.find_element_by_id('id_newpassband').find_element_by_class_name('kv-value').text
        self.assertIn('V', new_passband)
        slot_length = self.browser.find_element_by_id('id_slot_length').find_element_by_class_name('kv-value').text
        self.assertIn('23.0', slot_length)
        sky_mag = self.browser.find_element_by_id('id_skymag').find_element_by_class_name('kv-value').text
        self.assertIn('17.1', sky_mag)

        # Satisfied that the observations will be possible no matter the Moon or altitude,
        # he goes ahead and schedules the observations

    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_sfu_page_Down(self):
        # Jose has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target', kwargs={'pk': 1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Check Feasibility button
        link = self.browser.find_element_by_id('check-feasibility')
        target_url = "{0}{1}".format(self.live_server_url, reverse('feasibility', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Spectroscopy Feasibility page
        with self.wait_for_page_load(timeout=5):
            link.click()
        self.browser.implicitly_wait(2)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a form that allows the details of the proposed spectroscopic
        # observations to be entered. He sees that no details of SNR or slot
        # length are present yet
        self.assertEqual(len(self.browser.find_elements_by_id('id_snr')), 0)
        self.assertEqual(len(self.browser.find_elements_by_id('id_slot_length')), 0)
        self.assertEqual(len(self.browser.find_elements_by_link_text('SNR')), 0)
        self.assertEqual(len(self.browser.find_elements_by_link_text('Slot length')), 0)

        # Check that default is working in case of bad page
        sfu = self.browser.find_element_by_id('id_sfu').get_attribute("value")
        self.assertEqual('70.0', sfu)
