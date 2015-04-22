from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

class NewVisitorTest(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(3)

    def tearDown(self):
        self.browser.quit()

    def test_can_compute_ephemeris(self):
        # Eduardo has heard about a new website for NEOs. He goes to the
        # homepage
        self.browser.get('http://localhost:8000')
        
        # He notices the page title has the name of the site and the header 
        # mentions current targets
        self.assertIn('NEOexchange', self.browser.title)
        header_text = self.browser.find_element_by_tag_name('h1'),text
        self.assertIn('Current Targets', header_text)

        # He notices there are several targets that could be followed up

        # He is invited to enter a target to compute an ephemeris
        inputbox = self.browser.find_element_by_id('id_target')
        self.assertEqual(
            inputbox.get_attribute('placeholder'), 
            'Enter a target name'
        )

        # He types N007r0q into the textbox (he is most interested in NEOWISE targets)
        inputbox.send_keys('N007r0q')

        # When he hits Enter, the page updates and now the page shows an ephemeris
        # for the target with a column header and a series of rows for the position
        # as a function of time.
        inputbox.send_keys(Keys.ENTER)

        table = self.browser.find_element_by_id('id_ephemeris_table')
        header = table.find_elements_by_tag_name('th')
        self.assertEqual('Date (UT)            RA          Dec          Mag   "/min  Alt Phase Dist. Alt. Score FOV #   H.A.',
            header)
        rows = table.find_elements_by_tag_name('tr')
        self.assertTrue(
            any(row.text == '2015 04 21 17:35     13 22 02.92 -22 24 34.6  21.1   7.49  +31  0.11 134   +09  +027    0   -04:26' for row in rows)
        )

        # There is a button asking whether to schedule the target

        # He clicks 'No' and is returned to the front page
        self.fail('Finish the test!')

        # Satisfied, he goes back to sleep
        browser.quit()
