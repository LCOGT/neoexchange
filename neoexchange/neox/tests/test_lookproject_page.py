"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2020-2020 LCO

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
from neox.tests.mocks import MockDateTime, mock_build_visibility_source
from datetime import datetime
from core.models import Body, PreviousSpectra
from django.urls import reverse


class LOOKProjectPageTest(FunctionalTest):

    def insert_extra_test_body(self):
        params = {
                     'provisional_name': 'P10Btmr',
                     'provisional_packed': None,
                     'name': 'C/2017 K2',
                     'origin': 'O',
                     'source_type': 'C',
                     'source_subtype_1': 'LP',
                     'source_subtype_2': None,
                     'elements_type': 'MPC_COMET',
                     'active': False,
                     'fast_moving': False,
                     'urgency': None,
                     'epochofel': datetime(2017, 5, 7, 0, 0),
                     'orbit_rms': 99.0,
                     'orbinc': 83.08805,
                     'longascnode': 139.35,
                     'argofperih': 91.4214,
                     'eccentricity': 0.1361539,
                     'meandist': 13.6620146,
                     'meananom': None,
                     'perihdist': 11.801878030353059,
                     'epochofperih': datetime(2017, 5, 12, 23, 16, 41),
                     'abs_mag': 9.2,
                     'slope': 4.0,
                     'score': 58,
                     'discovery_date': datetime(2017, 5, 21, 9, 36),
                     'num_obs': 14,
                     'arc_length': 2.61,
                     'not_seen': 0.023,
                     'updated': True,
                     'ingest': datetime(2017, 5, 21, 19, 50, 9),
                     'update_time': datetime(2017, 5, 24, 2, 51, 58)}
        self.body, created = Body.objects.get_or_create(**params)
# The LOOK Project page computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.body.datetime', MockDateTime)
    def test_characterization_page(self):

        MockDateTime.change_datetime(2020, 7, 1, 17, 0, 0)
        self.insert_extra_test_body()
#        self.insert_another_extra_test_body()
#        self.insert_another_other_extra_test_body()

        # Kildorn the Unstoppable goes to the characterization page and expects to see the list of bodies in need of Characterization.
        lookproject_page_url = self.live_server_url + '/lookproject/'
        self.browser.get(lookproject_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('LOOK Project Page | LCO NEOx', self.browser.title)
