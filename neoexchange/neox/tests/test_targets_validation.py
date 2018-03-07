from .base import FunctionalTest
from selenium import webdriver

class TargetsValidationTest(FunctionalTest):

    def test_can_view_targets(self):
        # A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a link to TARGETS
        link = self.browser.find_element_by_xpath(u'//a[text()="Targets"]')
        target_url = "{0}{1}".format(self.live_server_url, '/target/')
        self.assertEqual(link.get_attribute('href'), target_url)

        # She clicks the link to go to the TARGETS page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)
