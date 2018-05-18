from .base import FunctionalTest
from django.core.urlresolvers import reverse
#from selenium import webdriver

class CalibrationSourceListViewTest(FunctionalTest):

    def test_can_view_blocks(self):
        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)
