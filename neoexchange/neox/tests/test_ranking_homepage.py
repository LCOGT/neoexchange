from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from mock import patch
from neox.tests.mocks import MockDateTime
#from datetime import datetime as real_datetime
from datetime import datetime
from core.models import Body
from django.core.urlresolvers import reverse

class NewVisitorTest(FunctionalTest):
# The homepage computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    def insert_extra_test_body(self):
        params = {  'name'          : '1995 YR1',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'G',
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : None,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 35,
                    'arc_length'    : 42.0,
                    'not_seen'      : 2.22,
                    'updated'       : False
                    }
        self.body2, created = Body.objects.get_or_create(pk=2, **params)

    @patch('core.models.datetime', MockDateTime)
    def test_homepage_has_ranking(self):

        MockDateTime.change_datetime(2015, 7, 1, 17, 0, 0)
        self.insert_extra_test_body()

        #Matt has heard about a new website that provides a ranked list of NEOs for follow-up.

        #He goes to the homepage for the website and expects to see this ranked list of NEOs.
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCOGT NEOx', self.browser.title)
        self.check_for_header_in_table('id_neo_targets',\
            'Rank Target Name Type R.A. Dec. Mag. Num.Obs. Arc Not Seen (days) NEOCP Score Updated?')
        # Position below computed for 2015-07-01 17:00:00
        testlines =[u'1 N999r0q Candidate 23 43 12.75 +19 58 55.6 20.7 17 3.0 0.42 90',
                    u'2 1995 YR1 NEO 23 43 12.75 +19 58 55.6 20.7 35 42.0 2.22 None']
        self.check_for_row_in_table('id_neo_targets', testlines[0])
        self.check_for_row_in_table('id_neo_targets', testlines[1])
        # Because we can't find the Updated icon with a simple text search
        # we look for the data-label for 'Updated?'
        updated_statuses = ['true','false']
        data_label = 'Updated?'
        self.check_icon_status_elements('id_neo_targets', data_label, updated_statuses)

        #He clicks on the top ranked NEO and is taken to a page that has more information on the object.
        link = self.browser.find_element_by_link_text('N999r0q')
        body_url = self.live_server_url + reverse('target',kwargs={'pk':1})
        self.assertIn(link.get_attribute('href'), body_url)

        # He clicks the link and is taken to a page with the targets' details.
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url)

        # He notices the page title has the name of the site and the header
        # mentions the current target
        self.assertIn(self.body.current_name() + ' details | LCOGT NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Object: ' + self.body.current_name(), header_text)
