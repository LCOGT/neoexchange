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
from datetime import datetime
from django.contrib.auth.models import User, Permission
from django.urls import reverse

from neox.tests.mocks import MockDateTime, mock_build_visibility_source, mock_lco_authenticate, mock_fetchpage_and_make_soup
from core.models import Body, PreviousSpectra, PhysicalParameters, Proposal, SuperBlock
from neox.auth_backend import update_proposal_permissions, update_user_permissions


class LOOKProjectPageTest(FunctionalTest):

    def setUp(self):
        # Create two users to test login and adding object permissions
        self.insert_test_proposals()
        self.lisa_username = 'lisa'
        self.lisa_password = 'simpson'
        self.email = 'lisa@simpson.org'
        self.lisa = User.objects.create_user(username=self.lisa_username, password=self.lisa_password, email=self.email)
        self.lisa.first_name = 'Lisa'
        self.lisa.last_name = 'Simpson'
        self.lisa.is_active = 1
        self.lisa.save()
        # Add Lisa to the right proposal and add permissions to add Body's
        update_proposal_permissions(self.lisa, [{'code': self.neo_proposal.code}])
        update_user_permissions(self.lisa, 'core.add_body')

        # Create the second user, Bart, who is naughty and doesn't get to create Body's
        self.bart_username = 'bart'
        self.bart_password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.bart_username, password=self.bart_password, email=self.email)
        self.bart.first_name = 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()
        # Add Bart to the right proposal and *don't* add permissions to add Body's
        update_proposal_permissions(self.bart, [{'code': self.neo_proposal.code}])
        super(LOOKProjectPageTest, self).setUp()

    def tearDown(self):
        self.lisa.delete()
        self.bart.delete()
        super(LOOKProjectPageTest, self).tearDown()

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login(self):
        test_login = self.client.login(username=self.lisa_username, password=self.lisa_password)
        self.assertEqual(test_login, True)

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
        # Create Key Project proposal
        params = { 'code' : 'KEY2020A-001',
                   'title' : 'LOOK Projectal'
                 }
        self.proposal = Proposal.objects.create(**params)

        sblock_params = {
                            'cadence' : True,
                            'active' : True,
                            'body' : self.body_K2,
                            'proposal' : self.proposal,
                            'block_start' : datetime(2017, 7, 2, 4, 0, 0),
                            'block_end' : datetime(2017, 7, 30, 23, 59, 59)
                        }
        self.sblock_K2 = SuperBlock.objects.create(**sblock_params)

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

        # Conan the Barbarian goes to the LOOK Project page and expects to see the list of bodies in need of observation.
        lookproject_page_url = self.live_server_url + '/lookproject/'
        self.browser.get(lookproject_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('LOOK Project Page | LCO NEOx', self.browser.title)

        testlines = ['Target Name', 'Target Type', 'Target Subtype',
            'R.A.', 'Dec.', 'V Mag.', 'Rate ("/min)', 'Heliocentric Distance (AU)',
            'Observations Scheduled', '(for next 30 days) Observation Window',
            '(for next 90 days)'
            ]
        testline = "\n".join(testlines)
        self.check_for_header_in_table('active_targets', testline)

        # Position below computed for 2017-07-01 17:00:00

        testlines = [u'C/2013 US10 Comet Hyperbolic, Dynamically New 03 57 50.41 +44 46 52.2 18.5 0.20 7.0 Nothing scheduled [-----]',
                     u'C/2017 K2 Comet Long Period, Dynamically New 17 29 39.56 +64 13 24.1 17.8 0.17 11.8 Active until 07/30 [-----]']

        self.check_for_row_in_table('active_targets', testlines[0])
        self.check_for_row_in_table('active_targets', testlines[1])

        # He checks for fresh victims...comet targets...
        section_text = self.browser.find_element_by_id("new_comets").text
        self.assertIn("New Comet Targets", section_text)
        testlines = [u'C/2013 US10 Hyperbolic, Dynamically New 03 57 50.41 +44 46 52.2 18.5 0.20 1.00055 1e+99 0.8245 5.296e-05 [-----]',]

        self.check_for_row_in_table('new_comets', testlines[0])

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    @patch('core.models.body.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_add_lookproject_target(self):

        MockDateTime.change_datetime(2020, 11, 14, 17, 0, 0)
        self.insert_extra_test_bodies()
#        self.insert_another_extra_test_body()
#        self.insert_another_other_extra_test_body()

        # Michaela goes to the the LOOK Project page as she has heard about a new outburst
        lookproject_page_url = self.live_server_url + '/lookproject/'
        self.browser.get(lookproject_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('LOOK Project Page | LCO NEOx', self.browser.title)

        # She looks through the list of targets but does not see her desired target
        table = self.browser.find_element_by_id('active_targets')
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertNotIn('191P', [row.text.replace('\n', ' ') for row in rows])

        # She logs in and sees that a new field and 'Add LOOK target' button has appeared
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.lisa_username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.lisa_password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is received
        self.wait_for_element_with_id('page')
        # Back to LOOK Project page
        self.browser.get(lookproject_page_url)
        self.wait_for_element_with_id('page')

        newtarget_input = self.browser.find_element_by_id('id_target_name')
        newtarget_button = self.browser.find_element_by_id('add_new_target-btn')

        # She fills in the field with the new object name and clicks it
        newtarget_input.send_keys("191P")
        newtarget_button.click()

        # The page refreshes and the new target appears as an active target
        testlines = [u'191P Comet Jupiter Family 21 24 28.42 -23 49 36.4 18.8 0.78 2.4 Nothing scheduled [-----]',
                     ]

        self.check_for_row_in_table('active_targets', testlines[0])

        # She retries adding the same object
        newtarget_input = self.browser.find_element_by_id('id_target_name')
        newtarget_button = self.browser.find_element_by_id('add_new_target-btn')
        newtarget_input.send_keys("191P")
        newtarget_button.click()

        # The message box says that the target is already in the system
        msg_box = self.browser.find_element_by_id('show-messages')
        self.assertIn('191P is already in the system', msg_box.text)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    @patch('core.models.body.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.fetchpage_and_make_soup', mock_fetchpage_and_make_soup)
    def test_cannot_add_lookproject_target(self):

        MockDateTime.change_datetime(2020, 11, 14, 17, 0, 0)
        self.insert_extra_test_bodies()
#        self.insert_another_extra_test_body()
#        self.insert_another_other_extra_test_body()

        # Bart goes to the the LOOK Project page as he has heard about a new outburst
        lookproject_page_url = self.live_server_url + '/lookproject/'
        self.browser.get(lookproject_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('LOOK Project Page | LCO NEOx', self.browser.title)

        # He looks through the list of targets but does not see his desired target
        table = self.browser.find_element_by_id('active_targets')
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertNotIn('191P', [row.text.replace('\n', ' ') for row in rows])

        # He logs in but is disappointed that the 'Add LOOK target' button has not appeared
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.bart_username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.bart_password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is received
        self.wait_for_element_with_id('page')
        # Back to LOOK Project page
        self.browser.get(lookproject_page_url)
        self.wait_for_element_with_id('page')

        newtarget_input = self.browser.find_elements_by_id('id_target_name')
        newtarget_button = self.browser.find_elements_by_id('add_new_target-btn')

        self.assertEqual(0, len(newtarget_input))
        self.assertEqual(0, len(newtarget_button))
