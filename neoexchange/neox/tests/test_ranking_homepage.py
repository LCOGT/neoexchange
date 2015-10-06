from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from mock import patch
from neox.tests.mocks import MockDateTime
#from datetime import datetime as real_datetime
from datetime import datetime
from core.models import Body

class NewVisitorTest(FunctionalTest):
# The homepage computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.datetime', MockDateTime)
    def test_homepage_has_ranking(self):

        MockDateTime.change_date(2015, 7, 1)

        #Matt has heard about a new website that provides a ranked list of NEOs for follow-up.
        
        #He goes to the homepage for the website and expects to see this ranked list of NEOs.
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCOGT NEOx', self.browser.title)
        self.check_for_header_in_table('id_neo_targets',\
            'Rank Target Name Type R.A. Dec. Mag. Num.Obs. Arc Not Seen (days) NEOCP Score Updated?')

        #He clicks on the top ranked NEO and is taken to a page that has more information on the object.
        self.browser.implicitly_wait(30)
        self.fail('Finish the test!')
