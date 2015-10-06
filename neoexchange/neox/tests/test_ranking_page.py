from .base import FunctionalTest
from mock import patch
from neox.tests.mocks import MockDateTime
from datetime import datetime
from core.models import Body

class RankingPageTest(FunctionalTest):

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
        self.body, created = Body.objects.get_or_create(pk=2, **params)

# The ranking page computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.datetime', MockDateTime)
    def test_ranking_page(self):

        MockDateTime.change_date(2015, 7, 1)
        self.insert_extra_test_body()
        
        #Sarah goes to the ranking page and expects to see the ranked list of NEOs with the FOM.
        ranking_page_url = self.live_server_url + '/ranking/'
        self.browser.get(ranking_page_url)
        self.assertNotIn('Home | LCOGT NEOx', self.browser.title)
        self.assertIn('Ranking Page | LCOGT NEOx', self.browser.title)
        self.check_for_header_in_table('id_ranked_targets',\
            'Rank FOM Target Name NEOCP Score Discovery Date R.A. Dec. South Polar Distance V mag. Updated? Num.Obs. Arc H mag. Not Seen (days) Observed? Reported?')
            
        #Satisfied, she leaves for the day.
        self.fail('Finish the test!')
