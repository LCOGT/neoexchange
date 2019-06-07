"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

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
from selenium.webdriver.common.action_chains import ActionChains


class TargetsValidationTest(FunctionalTest):

    def test_can_view_targets(self):
        # A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a dropdown menu for TARGETS
        menu = self.browser.find_element_by_class_name("dropdown-menu")
        drop_menu = ActionChains(self.browser).move_to_element(menu)
        drop_menu.perform()

        # she wants to look at active targets
        link = self.browser.find_element_by_xpath(u'//a[text()="Active"]')
        target_url = "{0}{1}".format(self.live_server_url, '/target/')
        self.assertEqual(link.get_attribute('href'), target_url)

        # She clicks the link to go to the TARGETS page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)
