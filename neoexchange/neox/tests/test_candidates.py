"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

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
from datetime import datetime

from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Candidate


class TestBlockCandidates(FunctionalTest):

    def setUp(self):
        # Create a user to test login
        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name= 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active=1
        self.bart.save()
        super(TestBlockCandidates,self).setUp()

    def insert_candidates(self):
        # Insert test candidate detections
        cparams = { 'block' : self.test_block,
                    'cand_id': 1,
                    'score' : 1.10,
                    'avg_midpoint' : datetime(2015, 4, 20, 18, 6, 6),
                    'avg_x' : 2103.245,
                    'avg_y' : 2043.026,
                    'avg_ra' : 10.924317*15.0,
                    'avg_dec' : 39.27700,
                    'avg_mag' : 19.26,
                    'speed' : 0.497,
                    'sky_motion_pa' : 0.2
                    }
        self.detection1, created = Candidate.objects.get_or_create(pk=1, **cparams)

        cparams = { 'block' : self.test_block,
                    'cand_id' : 2,
                    'score' : 2.10,
                    'avg_midpoint' : datetime(2015, 4, 20, 18, 6, 6),
                    'avg_x' : 1695.444,
                    'avg_y' :  173.967,
                    'avg_ra' : 10.928085*15.0,
                    'avg_dec' : 39.07607,
                    'avg_mag' : 20.01,
                    'speed' : 0.491,
                    'sky_motion_pa' : 357.0
                    }
        self.detection2, created = Candidate.objects.get_or_create(pk=42, **cparams)

    def test_can_view_candidates(self):

        self.insert_candidates()

        # A new user, Timo, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = self.live_server_url + '/block/list/'
        self.assertEqual(link.get_attribute('href'), target_url)

        # He clicks the link to go to the blocks page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He sees links that will go to a more detailed block view and goes
        # to the first Block.
        link = self.browser.find_element_by_link_text('1')
        block_url = self.live_server_url + reverse('block-view',kwargs={'pk':1})
        self.assertEqual(link.get_attribute('href'), block_url)

        # He clicks the link to go to the block details page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(new_url, block_url)

        # He goes to the (secret for now) candidates display page
        cands_url = self.live_server_url + reverse('view-candidates',kwargs={'pk':1})
        self.browser.get(cands_url)

        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        new_url = self.browser.current_url
        self.assertEqual(cands_url, new_url)

        # Check for the UTC midpoint
        self.check_for_row_in_table('id_canddetail', 'UTC MIDPOINT: 2015-04-20T18:06:06 (2015 04 20.75424 )' )

        self.check_for_header_in_table('id_candidates',\
            'ID Score R.A. Dec. Separation (") CCD X CCD Y Magnitude Speed Position Angle')
        # Position below computed for 2015-07-01 17:00:00
        testlines =[u'1 1.10 10:55:27.54 +39:16:37.2 361682.5 2103.245 2043.026 19.26 1.24 0.2',
                    u'2 2.10 10:55:41.11 +39:04:33.9 362173.0 1695.444 173.967 20.01 1.23 357.0']
        self.check_for_row_in_table('id_candidates', testlines[0])
        self.check_for_row_in_table('id_candidates', testlines[1])
