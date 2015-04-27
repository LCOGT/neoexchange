from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from ingest.models import Body

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

    def insert_test_body(self):
        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body = Body.objects.create(**params)
        self.body.save()


    def test_can_compute_ephemeris(self):
        ## Insert test body otherwise things will fail
        self.insert_test_body()

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
            'N999r0q Unknown/NEO Candidate MPC April 8, 2015, 9:23 p.m.')
        self.check_for_row_in_table('id_neo_targets',
            'P10kfud Unknown/NEO Candidate MPC April 8, 2015, 8:57 p.m.')

        # He is invited to enter a target to compute an ephemeris
        inputbox = self.get_item_input_box()
        self.assertEqual(
            inputbox.get_attribute('placeholder'), 
            'Enter a target name'
        )

        # He types N999r0q into the textbox (he is most interested in NEOWISE targets)
        inputbox.send_keys('N999r0q')

        # When he hits Enter, he is taken to a new page and now the page shows an ephemeris
        # for the target with a column header and a series of rows for the position
        # as a function of time.
        inputbox.send_keys(Keys.ENTER)

        eduardo_ephem_url = self.browser.current_url
        self.assertRegexpMatches(eduardo_ephem_url, '/ephemeris/.+')
        self.check_for_row_in_table('id_planning_table', 'Computing ephemeris for: N999r0q')

        self.check_for_header_in_table('id_ephemeris_table',
            'Date/Time (UTC) RA Dec Mag "/min Alt Moon Phase Moon Dist. Moon Alt. Score H.A.'
        )
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 04 21 08:45 20 10 05.99 +29 56 57.5 20.4 2.43 +33 0.09 107 -42 +047 -04:25'
        )

        # There is a button asking whether to schedule the target

        # He clicks 'No' and is returned to the front page
        self.assertIn('NEOexchange', self.browser.title)

        # Satisfied, he goes back to sleep

    def test_cannot_get_ephem_for_bad_objects(self):
        # Eduardo goes to the site and accidentally tries to submit a blank
        # form. He hits Enter on the empty input box
        self.browser.get(self.live_server_url)
        inputbox = self.get_item_input_box()
        inputbox.send_keys(Keys.ENTER)

        # The page refreshes and there is an error message saying that targets'
        # can't be blank
        error = self.browser.find_element_by_css_selector('.error')
        self.assertEqual(error.text, "You didn't specify a target")

    def test_can_view_targets(self):
        # A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a link to TARGETS
        link = self.browser.find_element_by_link_text('TARGETS')
        target_url = self.live_server_url + '/target/'
        self.assertEqual(link.get_attribute('href'), target_url)

        # She clicks the link to go to the TARGETS page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)

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
