from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from django.core.urlresolvers import reverse

class SpectroscopicFeasibility(FunctionalTest):

    def test_feasibility(self):
        # Bart has heard about a new website for NEOs. He goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)

        # He sees a Check Feasibility button
        link = self.browser.find_element_by_id('check-feasibility')
        target_url = "{0}{1}".format(self.live_server_url, reverse('feasibility',kwargs={'pk':1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the Spectroscopy Feasibility page
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.browser.implicitly_wait(10)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

        # He notices a form that allows the details of the proposed spectroscopic
        # observations to be entered. He sees that no details of SNR or slot
        # length are present yet
        self.assertEqual(len(self.browser.find_elements_by_id('id_snr')), 0)
        self.assertEqual(len(self.browser.find_elements_by_id('id_slot_length')), 0)
        self.assertEqual(len(self.browser.find_elements_by_link_text('SNR')), 0)
        self.assertEqual(len(self.browser.find_elements_by_link_text('Slot length')), 0)

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
        magbox.send_keys(Keys.ENTER)

        # The page refreshes and a series of values for SNR, new transformed
        # magnitude, new passband and slot length appear
        snr = self.browser.find_element_by_id('id_snr').find_element_by_class_name('kv-value').text
        self.assertIn('259.4', snr)
        magnitude = self.browser.find_element_by_id('id_newmag').find_element_by_class_name('kv-value').text
        self.assertIn('11.6', magnitude)
        new_passband = self.browser.find_element_by_id('id_newpassband').find_element_by_class_name('kv-value').text
        self.assertIn('ip', new_passband)
        slot_length = self.browser.find_element_by_id('id_slot_length').find_element_by_class_name('kv-value').text
        self.assertIn('20.5', slot_length)
