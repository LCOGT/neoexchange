from .base import FunctionalTest
from mock import patch
from neox.tests.mocks import MockDateTime
from datetime import datetime
from core.models import Body

class CharacterizationPageTest(FunctionalTest):

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


# The characterization page computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.datetime', MockDateTime)
    def test_ranking_page(self):

        MockDateTime.change_datetime(2015, 7, 1, 17, 0, 0)
        self.insert_extra_test_body()
        self.insert_another_extra_test_body()

        #Kildorn the Unstoppable goes to the characterization page and expects to see the list of bodies in need of Characterization.
        characterization_page_url = self.live_server_url + '/characterization/'
        self.browser.get(characterization_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('Characterization Page | LCO NEOx', self.browser.title)
        self.check_for_header_in_table('characterization_targets',\
            'Rank Target Name R.A. Dec. V Mag. Spectra H Mag. SMASS Obs MANOS Target? Observation Window Reported?')

        # Position below computed for 2015-07-01 17:00:00
        testlines =[u'3 V38821zi 23 43 12.75 +19 58 55.6 20.7 NEEDED 21.0',
                    u'1 N999r0q 23 43 12.75 +19 58 55.6 20.7 NEEDED 21.0 Visible No',
                    u'2 q382918r 23 43 12.75 +19 58 55.6 20.7 NEEDED  21.0']
        self.check_for_row_in_table('characterization_targets', testlines[0])
        self.check_for_row_in_table('characterization_targets', testlines[1])
        self.check_for_row_in_table('characterization_targets', testlines[2])

        #He notices that they are ordered somehow
        
        #Kildorn notices a link to the body page
        
        #He then sees that there is information from other surveys that have already gotten spectra for his targets

        #Now knowing what he must do, Kildorn the Unstoppable takes a lunch break.
