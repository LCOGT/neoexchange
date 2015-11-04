from .base import FunctionalTest
from selenium import webdriver

class LayoutAndStylingTest(FunctionalTest):

    def test_layout_and_styling(self):
        # Eduardo goes to the homepage
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1280, 1024)

        # He notices the targets box is offset from the left edge
        link = self.browser.find_element_by_partial_link_text('active targets')
        # Magic values from masthead padding in styles.css
        self.assertGreaterEqual(link.location['x'] , 35)
