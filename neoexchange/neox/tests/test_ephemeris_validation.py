from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from core.models import Body

class EphemerisValidationTest(FunctionalTest):

    def test_cannot_get_ephem_for_bad_objects(self):
        # Eduardo goes to the site and accidentally tries to submit a blank
        # form. He hits Enter on the empty input box
        self.browser.get(self.live_server_url)
        inputbox = self.get_item_input_box()
        inputbox.send_keys(Keys.ENTER)

        # The page refreshes and there is an error message saying that targets'
        # can't be blank
        error = self.browser.find_element_by_css_selector('.error')
        self.assertEqual(error.text, "Target name is required")
