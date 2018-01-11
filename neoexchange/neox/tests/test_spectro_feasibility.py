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

        # He clicks the link to go to the Schedule Observations page
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.browser.implicitly_wait(10)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)