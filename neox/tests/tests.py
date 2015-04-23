from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

class NewVisitorTest(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(3)

    def tearDown(self):
        self.browser.quit()

    def check_for_row_in_table(self, table_id, row_text):
        table = self.browser.find_element_by_id(table_id)
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertIn(row_text, [row.text for row in rows])

    def check_for_header_in_table(self, table_id, header_text):
        table = self.browser.find_element_by_id(table_id)
        table_header = table.find_element_by_tag_name('thead').text
        self.assertEqual(header_text, table_header)

    def get_item_input_box(self):
        return self.browser.find_element_by_id('id_target')


    def test_can_compute_ephemeris(self):
        # Eduardo has heard about a new website for NEOs. He goes to the
        # homepage
        self.browser.get(self.live_server_url)

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('NEOexchange', self.browser.title)
        header_text = self.browser.find_element_by_tag_name('h1').text
        self.assertIn('Current Targets', header_text)

        # He notices there are several targets that could be followed up
        self.check_for_header_in_table('id_neo_targets',
            'Target Name Type Origin Ingested')
        self.check_for_row_in_table('id_neo_targets',
            'N007r0q Unknown/NEO Candidate MPC April 8, 2015, 9:23 p.m.')
        self.check_for_row_in_table('id_neo_targets',
            'P10kfud Unknown/NEO Candidate MPC April 8, 2015, 8:57 p.m.')

        # He is invited to enter a target to compute an ephemeris
        inputbox = self.get_item_input_box()
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

        self.check_for_row_in_table('id_planning_table', 'Computing ephemeris for: N007r0q')

        self.check_for_header_in_table('id_ephemeris_table',
            'Date (UT) RA Dec Mag "/min Alt Moon Phase Moon Dist. Moon Alt. Score FOV # H.A.'
        )
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 04 21 17:35 13 22 02.92 -22 24 34.6 21.1 7.49 +31 0.11 134 +09 +027 0 -04:26'
        )

        # There is a button asking whether to schedule the target

        # He clicks 'No' and is returned to the front page
        self.assertIn('NEOexchange', self.browser.title)

        # Satisfied, he goes back to sleep

    def test_can_view_targets(self):
        # A new user comes along to the site
        self.browser.get(self.live_server_url)
        
        # She sees a link to TARGETS
        link = self.browser.find_element_by_link_text('TARGETS')
        target_url = self.live_server_url + '/target/'
        self.assertEqual(link.get_attribute('href'), target_url)

        # She clicks the link to go to the TARGETS page
        link.click()
        new_url = self.browser.current_url
        self.assertContains(new_url, target_url)

    def test_layout_and_styling(self):
        # Eduardo goes to the homepage
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)

        # He notices the input box is nicely centered
        inputbox = self.get_item_input_box()
        self.assertAlmostEqual(
            inputbox.location['x'] + inputbox.size['width'] / 2,
            512, delta=5
        )
