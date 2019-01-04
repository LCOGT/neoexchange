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
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from mock import patch
from neox.tests.mocks import MockDateTime
# from datetime import datetime as real_datetime
from datetime import datetime
from core.models import Body
from django.core.urlresolvers import reverse


class NewVisitorTest(FunctionalTest):
    """ The homepage computes the RA, Dec of each body for 'now' so we need to mock
    patch the datetime used by models.Body.compute_position to give the same
    consistent answer.
    """

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

    def insert_local_test_body(self):
        params = { 'abs_mag': 17.78,
                   'active': True,
                   'arc_length': 1.07083333333333,
                   'argofperih': 171.83095,
                   'discovery_date': datetime(2017, 2, 1, 4, 19, 24),
                   'eccentricity': 0.1401049,
                   'elements_type': u'MPC_MINOR_PLANET',
                   'epochofel': datetime(2017, 2, 2, 0, 0),
                   'epochofperih': None,
                   'ingest': datetime(2017, 2, 1, 5, 52, 58),
                   'longascnode': 292.00508,
                   'meananom': 27.74632,
                   'meandist': 3.0862545,
                   'name': u'',
                   'not_seen': 0.918786862824074,
                   'num_obs': 16,
                   'orbinc': 15.46491,
                   'origin': u'L',
                   'perihdist': None,
                   'provisional_name': u'LSCTLGm',
                   'provisional_packed': u'',
                   'score': 2,
                   'slope': 0.15,
                   'source_type': u'U',
                   'update_time': datetime(2017, 2, 2, 22, 3, 3),
                   'updated': True,
                   'urgency': None}

        self.body3, created = Body.objects.get_or_create(pk=3, **params)

    @patch('core.models.datetime', MockDateTime)
    def test_homepage_has_ranking(self):

        MockDateTime.change_datetime(2015, 7, 1, 17, 0, 0)
        self.insert_extra_test_body()

        # Matt has heard about a new website that provides a ranked list of NEOs for follow-up.

        # He goes to the homepage for the website and expects to see this ranked list of NEOs.
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCO NEOx', self.browser.title)
        self.check_for_header_in_table('id_neo_targets',
            'Rank Target Name Type R.A. Dec. Mag. Num.Obs. Arc Not Seen (days) NEOCP Score Updated?')
        # Position below computed for 2015-07-01 17:00:00
        testlines = [u'1 N999r0q Candidate 23 43 14.40 +19 59 08.2 20.7 17 3.00 0.420 90',
                    u'2 1995 YR1 NEO 23 43 14.40 +19 59 08.2 20.7 35 42.00 2.220 None']
        self.check_for_row_in_table('id_neo_targets', testlines[0])
        self.check_for_row_in_table('id_neo_targets', testlines[1])
        # Because we can't find the Updated icon with a simple text search
        # we look for the data-label for 'Updated?'
        updated_statuses = ['Yes', 'No']
        data_label = 'Updated?'
        self.check_icon_status_elements('id_neo_targets', data_label, updated_statuses)

        # He clicks on the top ranked NEO and is taken to a page that has more information on the object.
        link = self.browser.find_element_by_link_text('N999r0q')
        body_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.assertIn(link.get_attribute('href'), body_url)

        # He clicks the link and is taken to a page with the targets' details.
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url)

        # He notices the page title has the name of the site and the header
        # mentions the current target
        self.assertIn(self.body.current_name() + ' details | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Object: ' + self.body.current_name(), header_text)

    @patch('core.models.datetime', MockDateTime)
    def test_homepage_rounds_arc_notseen(self):

        MockDateTime.change_datetime(2017, 2, 1, 17, 0, 0)
        self.insert_local_test_body()
        self.insert_extra_test_body()

        # Matt has heard about a new website that provides a ranked list of NEOs for follow-up.

        # He goes to the homepage for the website and expects to see this ranked list of NEOs.
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCO NEOx', self.browser.title)
        self.check_for_header_in_table('id_neo_targets',
            'Rank Target Name Type R.A. Dec. Mag. Num.Obs. Arc Not Seen (days) NEOCP Score Updated?')
        # Position below computed for 2017-02-01 17:00:00
        testlines = [u'1 LSCTLGm Candidate 09 27 31.01 +03 05 27.6 21.6 16 1.07 0.919 2', ]
        self.check_for_row_in_table('id_neo_targets', testlines[0])
        # Because we can't find the Updated icon with a simple text search
        # we look for the data-label for 'Updated?'
        updated_statuses = ['Yes', ]
        data_label = 'Updated?'
        self.check_icon_status_elements('id_neo_targets', data_label, updated_statuses)

        # He clicks on the top ranked NEO and is taken to a page that has more information on the object.
        link = self.browser.find_element_by_link_text('LSCTLGm')
        body_url = self.live_server_url + reverse('target', kwargs={'pk': self.body3.pk})
        self.assertIn(link.get_attribute('href'), body_url)

        # He clicks the link and is taken to a page with the targets' details.
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url)

        # He notices the page title has the name of the site and the header
        # mentions the current target
        self.assertIn(self.body3.current_name() + ' details | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Object: ' + self.body3.current_name(), header_text)
