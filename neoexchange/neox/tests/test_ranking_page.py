from .base import FunctionalTest
from mock import patch
from neox.tests.mocks import MockDateTime
from datetime import datetime
from core.models import Body

class RankingPageTest(FunctionalTest):

    def insert_extra_test_body(self):
        params = {  'name'          : 'q382918r',
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
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : 85,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 35,
                    'arc_length'    : 42.0,
                    'not_seen'      : 2.22,
                    'updated'       : False
                    }
        self.body, created = Body.objects.get_or_create(pk=3, **params)

    def insert_another_extra_test_body(self):
        params = {  'name'          : 'V38821zi',
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
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : 100,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 2,
                    'arc_length'    : 0.07,
                    'not_seen'      : 12.29,
                    'updated'       : False
                    }
        self.body, created = Body.objects.get_or_create(pk=4, **params)

# The ranking page computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.datetime', MockDateTime)
    def test_ranking_page(self):

        MockDateTime.change_date(2015, 7, 1)
        self.insert_extra_test_body()
        self.insert_another_extra_test_body()
        
        #Sarah goes to the ranking page and expects to see the ranked list of NEOs with the FOM.
        ranking_page_url = self.live_server_url + '/ranking/'
        self.browser.get(ranking_page_url)
        self.assertNotIn('Home | LCOGT NEOx', self.browser.title)
        self.assertIn('Ranking Page | LCOGT NEOx', self.browser.title)
        self.check_for_header_in_table('id_ranked_targets',\
            'Rank FOM Target Name NEOCP Score Discovery Date R.A. Dec. South Polar Distance V Mag. Updated? Num. Obs. Arc H Mag. Not Seen (days) Observed? Reported?')
        # Position below computed for 2015-07-01 17:00:00
        testlines =[u'1 1.7770621156e+76 V38821zi 100 May 10, 2015, noon 23 43 12.75 +19 58 55.6 110.0 20.7 False 2 0.07 21.0 12.29 Not yet Not yet',
                    u'2 0.25275911901 N999r0q 90 May 10, 2015, noon 23 43 12.75 +19 58 55.6 110.0 20.7 True 17 3.0 21.0 0.42 1/2 1/2',
                    u'3 0.153401873374 q382918r 85 May 10, 2015, noon 23 43 12.75 +19 58 55.6 110.0 20.7 False 35 42.0 21.0 2.22 Not yet Not yet']
        self.check_for_row_in_table('id_ranked_targets', testlines[0])
        self.check_for_row_in_table('id_ranked_targets', testlines[1])
        self.check_for_row_in_table('id_ranked_targets', testlines[2])
            
        #Satisfied, she leaves for the day.

