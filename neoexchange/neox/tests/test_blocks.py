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

from django.urls import reverse
from django.contrib.auth.models import User

from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_archive_frames, \
    mock_lco_api_call_blockcancel
from neox.auth_backend import update_proposal_permissions
from core.models import Block, SuperBlock


class BlocksListValidationTest(FunctionalTest):

    def test_can_view_blocks(self):
        # A new user, Timo, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('Blocks | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Blocks', header_text)

        # He notices there are several blocks that are listed
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = [u'1 N999r0q CPT 1m0 LCO2015A-009 00042 5x42.0 secs Yes Active 0 / 1 0 / 1',
                     u'2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1']
        self.check_for_row_in_table('id_blocks', testlines[0])
        self.check_for_row_in_table('id_blocks', testlines[1])


class BlockDetailValidationTest(FunctionalTest):

    def test_can_show_block_details(self):
        # A new user, Timo, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He sees links that will go to a more detailed block view and goes
        # to the first Block.
        link = self.browser.find_element_by_link_text('1')
        target_url = "{0}{1}".format(self.live_server_url, reverse('block-view',kwargs={'pk':1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the block details page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions block details
        self.assertIn('Cadence details', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Block: 1', header_text)

        # He notices there is a table which lists a lot more details about
        # the Block.

        testlines = [u'TELESCOPE CLASS ' + self.test_block.telclass,
                     u'SITE ' + self.test_block.site.upper()]
        for line in testlines:
            self.check_for_row_in_table('id_blockdetail', line)


class SuperBlockListValidationTest(FunctionalTest):

    def insert_cadence_blocks(self):
        # Insert extra blocks as part of a cadence
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'block_start' : '2015-04-21 13:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'request_number' : '00044',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'superblock' : self.test_sblock
                       }
        self.test_block = Block.objects.create(pk=3, **block_params)

    def test_can_view_superblocks_cadence(self):

        self.insert_cadence_blocks()

        # A user Foo, wishes to check on the progress of a multi-day cadence
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He sees that there are both cadence and non-cadence Blocks scheduled.
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = [u'1 N999r0q CPT 1m0 LCO2015A-009 00042 1 of 5x42.0 secs, 1 of 5x40.0 secs Yes Active 0 / 2 0 / 2',
                     u'2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1']
        self.check_for_row_in_table('id_blocks', testlines[0])
        self.check_for_row_in_table('id_blocks', testlines[1])

        # He clicks on one of the cadence block links and is taken to a page with details about the
        # individual blocks
        link = self.browser.find_element_by_link_text('1')
        target_url = "{0}{1}".format(self.live_server_url, reverse('block-view', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the block details page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions cadence details
        self.assertIn('Cadence details', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Block: 1', header_text)
        kv_table_text = self.browser.find_element_by_class_name('container').text
        self.assertIn('Details of the Cadence', kv_table_text)

    def test_can_view_superblocks_noncadence(self):

        self.insert_cadence_blocks()

        # A user Foo, wishes to check on the progress of a regular block
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He sees that there are both cadence and non-cadence Blocks scheduled.
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = [u'1 N999r0q CPT 1m0 LCO2015A-009 00042 1 of 5x42.0 secs, 1 of 5x40.0 secs Yes Active 0 / 2 0 / 2',
                     u'2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1']
        self.check_for_row_in_table('id_blocks', testlines[0])
        self.check_for_row_in_table('id_blocks', testlines[1])

        # He clicks on one of the cadence block links and is taken to a page with details about the
        # individual blocks
        link = self.browser.find_element_by_link_text('2')
        target_url = "{0}{1}".format(self.live_server_url, reverse('block-view', kwargs={'pk': 2}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link for a non-cadence block to go to the block details page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions cadence details
        self.assertIn('Block details', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Block: 2', header_text)
        kv_table_text = self.browser.find_element_by_class_name('container').text
        self.assertIn('Details of the Block', kv_table_text)

        # He sees that it was observed last night and that is has been reported to MPC
        self.assertIn('2015-04-20 03:31', kv_table_text)
        self.assertNotIn('Not Reported', kv_table_text)
        self.assertIn('2015-04-20 09:29', kv_table_text)


class SpectroBlocksListValidationTest(FunctionalTest):

    def insert_spectro_blocks(self):

        sblock_params = {
                         'cadence' : False,
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '4242',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(pk=3, **sblock_params)

        block_params = { 'telclass' : '2m0',
                         'site'     : 'ogg',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'obstype'  : Block.OPT_SPECTRA,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '12345',
                         'num_exposures' : 1,
                         'exp_length' : 1800.0,
                         'active'   : True,
                       }
        self.test_block = Block.objects.create(pk=4, **block_params)

    def test_can_view_blocks(self):
        self.insert_spectro_blocks()

        # A new user, Jose, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('Blocks | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Blocks', header_text)

        # He sees that there are both spectroscopic and non-spectroscopic Blocks scheduled.
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = ['1 N999r0q CPT 1m0 LCO2015A-009 00042 5x42.0 secs Yes Active 0 / 1 0 / 1',
                     '2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1',
                     '3 N999r0q OGG 2m0(S) LCOEngineering 4242 1x1800.0 secs No Active 0 / 1 0 / 1']
        self.check_for_row_in_table('id_blocks', testlines[2])


class SpectroBlocksDetailValidationTest(FunctionalTest):

    def setUp(self):
        # Create a user to test login
        self.insert_test_proposals()
        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name= 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()
        # Add Bart to the right proposal
        update_proposal_permissions(self.bart, [{'code': self.neo_proposal.code}])
        super(SpectroBlocksDetailValidationTest, self).setUp()

        sblock_params = {
                         'cadence' : False,
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '4242',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(pk=3, **sblock_params)

        block_params = { 'telclass' : '2m0',
                         'site'     : 'ogg',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'obstype'  : Block.OPT_SPECTRA,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '12345',
                         'num_exposures' : 1,
                         'exp_length' : 1800.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-04-21 12:13:14'
                       }
        self.test_block = Block.objects.create(pk=4, **block_params)

        analog_block_params = {'telclass': '2m0',
                               'site': 'ogg',
                               'body': None,
                               'calibsource': self.calib,
                               'superblock': self.test_sblock,
                               'obstype': Block.OPT_SPECTRA_CALIB,
                               'block_start': '2015-04-20 13:00:00',
                               'block_end': '2015-04-21 03:00:00',
                               'request_number': '12345',
                               'num_exposures': 1,
                               'exp_length': 50.0,
                               'active': True,
                               'num_observed': 1,
                               'when_observed': '2015-04-21 12:13:14'
                               }
        self.analog_block = Block.objects.create(pk=5, **analog_block_params)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login(self):
        test_login = self.client.login(username=self.username, password=self.password)
        self.assertEqual(test_login, True)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login_user(self):
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is recieved

    @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
    def test_can_view_block_detail(self):
        self.login_user()

        # A new user, Jose, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('Blocks | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Blocks', header_text)

        # He sees that there are both spectroscopic and non-spectroscopic Blocks scheduled.
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = ['1 N999r0q CPT 1m0 LCO2015A-009 00042 5x42.0 secs Yes Active 0 / 1 0 / 1',
                     '2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1',
                     '3 N999r0q OGG 2m0(S), 2m0(SC) LCOEngineering 4242 1 of 1x1800.0 secs, 1 of 1x50.0 secs No Active 2 / 2 0 / 2']
        self.check_for_row_in_table('id_blocks', testlines[2])

        # He wishes to get more details on the spectroscopic block that is scheduled
        link = self.browser.find_element_by_link_text('3')
        target_url = "{0}{1}".format(self.live_server_url, reverse('block-view', kwargs={'pk': 3}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the block details page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions block details
        self.assertIn('Block details', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Block: 3', header_text)

        # He notices there is a table which lists a lot more details about
        # the Block.

        testlines = ['TELESCOPE CLASS ' + self.test_block.telclass + '(S), ' + self.test_block.telclass + '(SC)',
                     'SITE ' + self.test_block.site.upper()]
        for line in testlines:
            self.check_for_row_in_table('id_blockdetail', line)

        side_text = self.browser.find_element_by_class_name('block-status').text
        block_lines = side_text.splitlines()
        testlines = ['TAR: 1, SPECTRUM: 1, LAMPFLAT: 1, ARC: 1',
                    ]
        for line in testlines:
            self.assertIn(line, block_lines)


class BlockCancelTest(FunctionalTest):
    def setUp(self):
        # Create a user to test login
        self.insert_test_proposals()
        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name= 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()
        # Add Bart to the right proposal
        update_proposal_permissions(self.bart, [{'code': self.neo_proposal.code}])
        super(BlockCancelTest, self).setUp()

        sblock_params = {
                         'cadence' : False,
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '4242',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(pk=3, **sblock_params)

        block_params = { 'telclass' : '2m0',
                         'site'     : 'ogg',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'obstype'  : Block.OPT_SPECTRA,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '12345',
                         'num_exposures' : 1,
                         'exp_length' : 1800.0,
                         'active'   : True,
                         'num_observed' : 1,
                         'when_observed' : '2015-04-21 12:13:14'
                       }
        self.test_block = Block.objects.create(pk=4, **block_params)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login(self):
        test_login = self.client.login(username=self.username, password=self.password)
        self.assertEqual(test_login, True)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login_user(self):
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('login-btn').click()
        # Wait until response is recieved

    @patch('core.views.lco_api_call',mock_lco_api_call_blockcancel)
    def test_cancel_block_loggedin(self):
        self.login_user()
        # Reginald wants to cancel a block, so goes to the block page
        url = "{}{}".format(self.live_server_url,reverse('block-view', kwargs={'pk': self.test_sblock.pk}))
        self.browser.get(url)
        link = self.browser.find_element_by_id('cancelblock')
        target_url = "{0}{1}".format(self.live_server_url, f'/block/{self.test_sblock.pk}/cancel/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)
        self.check_for_row_in_table('id_blockdetail', 'ACTIVE? Active')
        # Click the link to cancel and go back to the block details page
        link.click()
        # Reginald checks status is now inactive
        self.check_for_row_in_table('id_blockdetail', 'ACTIVE? Not Active')

    def test_cancel_block_loggedout(self):
        # Judith wants to cancel a block, but forgets to log in
        url = "{}{}".format(self.live_server_url,reverse('block-view', kwargs={'pk': self.test_sblock.pk}))
        self.browser.get(url)
        button = self.browser.find_elements_by_link_text('Cancel Block')
        self.assertEqual(button,[])
