from .base import FunctionalTest
from selenium import webdriver

class LayoutAndStylingTest(FunctionalTest):

    def test_layout_and_styling(self):
        # Eduardo goes to the homepage
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1280, 1024)

        # He notices the input box is nicely centered
        inputbox = self.get_item_input_box()
        self.assertAlmostEqual(
            inputbox.location['x'] + inputbox.size['width'] / 2,
            640, delta=7
        )
