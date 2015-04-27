from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from ingest.models import Body

class NewVisitorTest(FunctionalTest):

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
