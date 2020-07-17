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
from core.models import Body, PreviousSpectra, PhysicalParameters
from django.urls import reverse


class LOOKProjectPageTest(FunctionalTest):

    def insert_extra_test_bodies(self):
        params = {
                     'provisional_name': 'P10Btmr',
                     'provisional_packed': None,
                     'name': 'C/2017 K2',
                     'origin': 'O',
                     'source_type': 'C',
                     'source_subtype_1': 'LP',
                     'source_subtype_2': 'DN',
                     'elements_type': 'MPC_COMET',
                     'active': True,
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
                     'abs_mag': 6.3,
                     'slope': 2.3,
                     'score': 58,
                     'discovery_date': datetime(2017, 5, 21, 9, 36),
                     'num_obs': 14,
                     'arc_length': 2.61,
                     'not_seen': 0.023,
                     'updated': True,
                     'ingest': datetime(2017, 5, 21, 19, 50, 9),
                     'update_time': datetime(2017, 5, 24, 2, 51, 58)}
        self.body_K2, created = Body.objects.get_or_create(**params)

        params = {
                     'provisional_name': None,
                     'provisional_packed': None,
                     'name': 'C/2013 US10',
                     'origin': 'O',
                     'source_type': 'C',
                     'source_subtype_1': 'H',
                     'source_subtype_2': 'DN',
                     'elements_type': 'MPC_COMET',
                     'active': True,
                     'fast_moving': False,
                     'urgency': None,
                     'epochofel': datetime(2019, 4, 27, 0, 0),
                     'orbit_rms': 99.0,
                     'orbinc': 148.83797,
                     'longascnode': 186.25239,
                     'argofperih': 340.51541,
                     'eccentricity': 1.0005522,
                     'meandist': None,
                     'meananom': None,
                     'perihdist': 0.8244693,
                     'epochofperih': datetime(2015, 11, 16, 1, 5, 31),
                     'abs_mag': 8.1,
                     'slope': 2.8,
                     'score': None,
                     'discovery_date': datetime(2013, 8, 14, 0, 0),
                     'num_obs': 4703,
                     'arc_length': 1555.0,
                     'not_seen': 963.9336267593403,
                     'updated': True,
                     'ingest': datetime(2020, 7, 6, 22, 23, 23),
                     'update_time': datetime(2017, 11, 16, 0, 0)
                    }
        self.body_US10, created = Body.objects.get_or_create(**params)

        PhysicalParameters.objects.create(body=self.body_US10, parameter_type='/a', value=0.00005296, preferred=True)

        return

# The LOOK Project page computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.models.body.datetime', MockDateTime)
    def test_lookproject_page(self):

        MockDateTime.change_datetime(2017, 7, 1, 17, 0, 0)
        self.insert_extra_test_bodies()
#        self.insert_another_extra_test_body()
#        self.insert_another_other_extra_test_body()

        # Conan the Barbarian goes to the characterization page and expects to see the list of bodies in need of Characterization.
        lookproject_page_url = self.live_server_url + '/lookproject/'
        self.browser.get(lookproject_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('LOOK Project Page | LCO NEOx', self.browser.title)

        # Position below computed for 2015-07-01 17:00:00

        testlines = [u'C/2013 US10 Comet Hyperbolic, Dynamically New 03 57 50.41 +44 46 52.2 18.5 0.20 Coming soon... [-----]',
                     u'C/2017 K2 Comet Long Period, Dynamically New 17 29 39.56 +64 13 24.1 17.8 0.17 Coming soon... [-----]']

        self.check_for_row_in_table('active_targets', testlines[0])
        self.check_for_row_in_table('active_targets', testlines[1])

        # He checks for fresh victims...comet targets...
        section_text = self.browser.find_element_by_id("new_comets").text
        self.assertIn("New Comet Targets", section_text)
        testlines = [u'C/2013 US10 Hyperbolic, Dynamically New 03 57 50.41 +44 46 52.2 18.5 0.20 1.00055 1e+99 0.8245 5.296e-05 [-----]',]

        self.check_for_row_in_table('new_comets', testlines[0])
