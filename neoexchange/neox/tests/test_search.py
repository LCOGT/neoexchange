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
import os
from selenium import webdriver
from django.urls import reverse
from core.models import Body, StaticSource


class SearchPageTests(FunctionalTest):

    def insert_extra_test_bodies(self):
        params = {  'name'          : 'VN938821zi',
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
        body2, status = Body.objects.get_or_create(**params)
        self.body2 = body2

        params = {  'name'          : 'V938822zi',
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
        body3, status = Body.objects.get_or_create(**params)
        self.body3 = body3

        params = {  'name'          : '938',
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
        body4, status = Body.objects.get_or_create(**params)
        self.body4 = body4

        params = {  'name'          : 'test_starN9',
                    'ra'       : 1,
                    'dec'         : 1,
                    'vmag'      : 12
                    }
        star1, status = StaticSource.objects.get_or_create(**params)
        self.star1 = star1

    def test_search_page(self):

        # Setup
        self.insert_extra_test_bodies()

        # A user, Timo, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about

        # He goes to the home page and performs a search for that object
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCO NEOx', self.browser.title)
        inputbox = self.get_item_input_box("id_target_search")
        inputbox.send_keys('N9')
        searchbutton = self.get_item_input_box("id_search_submit")
        searchbutton.click()

        # He is taken to a page with the search results on it.
        search_url = self.live_server_url + '/search/?q=N9'
        self.assertEqual(self.browser.current_url, search_url)
        self.assertIn('Targets | LCO NEOx', self.browser.title)

        self.browser.implicitly_wait(5)
        # He sees that the target he wants is in the table and clicks on it
        self.check_for_header_in_table('id_targets', 'Name Type Origin Ingest date')
        testlines = [u'N999r0q Candidate Minor Planet Center 11 May 2015, 17:20',
                     u'VN938821zi Candidate Minor Planet Center 11 May 2015, 17:20',
                     u'V938822zi Candidate Minor Planet Center 11 May 2015, 17:20',
                     u'test_starN9 Unknown source type',
                     u'938 Candidate Minor Planet Center 11 May 2015, 17:20',
                     ]
        self.check_for_row_in_table('id_targets', testlines[0])
        self.check_for_row_in_table('id_targets', testlines[1])
        self.check_for_row_not_in_table('id_targets', testlines[2])
        self.check_for_row_in_table('id_targets', testlines[3])
        self.check_for_row_not_in_table('id_targets', testlines[4])

        # He want to search for something else
        inputbox = self.get_item_input_box("id_target_search")
        inputbox.send_keys('9')
        searchbutton = self.get_item_input_box("id_search_submit")
        searchbutton.click()

        # He is taken to a page with the search results on it.
        search_url = self.live_server_url + '/search/?q=9'
        self.assertEqual(self.browser.current_url, search_url)

        # His search was a small digit number, so he got no results
        self.check_for_row_not_in_table('id_targets', testlines[0])
        self.check_for_row_not_in_table('id_targets', testlines[1])
        self.check_for_row_not_in_table('id_targets', testlines[2])
        self.check_for_row_not_in_table('id_targets', testlines[3])
        self.check_for_row_not_in_table('id_targets', testlines[4])

        # He wants to search for something else
        inputbox = self.get_item_input_box("id_target_search")
        inputbox.send_keys('938')
        searchbutton = self.get_item_input_box("id_search_submit")
        searchbutton.click()

        # He is taken to a page with the search results on it.
        search_url = self.live_server_url + '/search/?q=938'
        self.assertEqual(self.browser.current_url, search_url)

        # His search was a number with an exact match, so he got 1 result
        self.check_for_row_not_in_table('id_targets', testlines[0])
        self.check_for_row_not_in_table('id_targets', testlines[1])
        self.check_for_row_not_in_table('id_targets', testlines[2])
        self.check_for_row_not_in_table('id_targets', testlines[3])
        self.check_for_row_in_table('id_targets', testlines[4])

        # He wants to search for something else
        inputbox = self.get_item_input_box("id_target_search")
        inputbox.send_keys('3882')
        searchbutton = self.get_item_input_box("id_search_submit")
        searchbutton.click()

        # He is taken to a page with the search results on it.
        search_url = self.live_server_url + '/search/?q=3882'
        self.assertEqual(self.browser.current_url, search_url)

        # His search was a number without exact match, so he got 2 result
        self.check_for_row_not_in_table('id_targets', testlines[0])
        self.check_for_row_in_table('id_targets', testlines[1])
        self.check_for_row_in_table('id_targets', testlines[2])
        self.check_for_row_not_in_table('id_targets', testlines[3])
        self.check_for_row_not_in_table('id_targets', testlines[4])
