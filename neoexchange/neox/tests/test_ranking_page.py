"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

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
        self.body3, created = Body.objects.get_or_create(pk=3, **params)

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
        self.body4, created = Body.objects.get_or_create(pk=4, **params)

    def insert_one_more_extra_test_body(self):
        params = {  'name'          : 'bloop',
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
                    'not_seen'      : None,
                    'updated'       : False
                    }
        self.body5, created = Body.objects.get_or_create(pk=5, **params)

# The ranking page computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.body.datetime', MockDateTime)
    def test_ranking_page(self):

        MockDateTime.change_datetime(2015, 7, 1, 17, 0, 0)
        self.insert_extra_test_body()
        self.insert_one_more_extra_test_body()
        self.insert_another_extra_test_body()

        # Sarah goes to the ranking page and expects to see the ranked list of NEOs with the FOM.
        ranking_page_url = self.live_server_url + '/ranking/'
        self.browser.get(ranking_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('Ranking Page | LCO NEOx', self.browser.title)
        self.check_for_header_in_table('id_ranked_targets',
            'Rank FOM Target Name NEOCP Score Discovery Date R.A. Dec. South Polar Distance V Mag. Updated? Num. Obs. Arc H Mag. Not Seen (days) Observed? Reported?')
        # Position below computed for 2015-07-01 17:00:00
        testlines = [u'1 1.8e+76 V38821zi 100 May 10, 2015, noon 23 43 14.40 +19 59 08.2 110.0 20.7 2 0.07 21.0 12.29 Not yet Not yet',
                    u'2 2.5e-01 N999r0q 90 May 10, 2015, noon 23 43 14.40 +19 59 08.2 110.0 20.7 17 3.12 21.0 0.42 1/2 1/2',
                    u'3 1.5e-01 q382918r 85 May 10, 2015, noon 23 43 14.40 +19 59 08.2 110.0 20.7 35 42.00 21.0 2.22 Not yet Not yet',
                     '4 bloop 100 May 10, 2015, noon 23 43 14.40 +19 59 08.2 110.0 20.7 2 0.07 21.0 None Not yet Not yet']
        self.check_for_row_in_table('id_ranked_targets', testlines[0])
        self.check_for_row_in_table('id_ranked_targets', testlines[1])
        self.check_for_row_in_table('id_ranked_targets', testlines[2])
        self.check_for_row_in_table('id_ranked_targets', testlines[3])
        # Because we can't find the Updated icon with a simple text search
        # we look for the data-label for 'Updated?'
        updated_statuses = ['No', 'Yes', 'No', 'No']
        data_label = 'Updated?'
        self.check_icon_status_elements('id_ranked_targets', data_label, updated_statuses)

        # Satisfied, she leaves for the day.
