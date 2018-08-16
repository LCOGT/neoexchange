"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

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
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from neox.auth_backend import update_proposal_permissions
from selenium import webdriver
from core.models import Block, SuperBlock, Frame
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_archive_frames
from django.conf import settings
import os


class SpectraplotTest(FunctionalTest):

        def setUp(self):

            super(SpectraplotTest, self).setUp()

            settings.DATA_ROOT = os.getcwd()+'/photometrics/tests/'

            self.username = 'bart'
            self.password = 'simpson'
            self.email = 'bart@simpson.org'
            self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
            self.bart.first_name = 'Bart'
            self.bart.last_name = 'Simpson'
            self.bart.is_active = 1
            self.bart.save()

            sblock_params = {
                 'cadence'         : False,
                 'body'            : self.body,
                 'proposal'        : self.test_proposal,
                 'block_start'     : '2015-04-20 13:00:00',
                 'block_end'       : '2015-04-24 03:00:00',
                 'tracking_number' : '4242',
                 'active'          : True
               }
            self.test_sblock = SuperBlock.objects.create(pk=3, **sblock_params)

            block_params = {
                 'telclass'        : '2m0',
                 'site'            : 'ogg',
                 'body'            : self.body,
                 'proposal'        : self.test_proposal,
                 'superblock'      : self.test_sblock,
                 'obstype'         : Block.OPT_SPECTRA,
                 'block_start'     : '2015-04-20 13:00:00',
                 'block_end'       : '2015-04-21 03:00:00',
                 'tracking_number' : '12345',
                 'num_exposures'   : 1,
                 'exp_length'      : 1800.0,
                 'active'          : True,
               }
            self.test_block = Block.objects.create(pk=3, **block_params)
            fparams = {
                'sitecode'      : 'F65',
                'filename'      : 'sp233/a265962.sp233.txt',
                'exptime'       : 1800.0,
                'midpoint'      : '2015-04-21 00:00:00',
                'frametype'     : Frame.SPECTRUM_FRAMETYPE,
                'block'         : self.test_block,
                'frameid'       : 1,
               }
            self.spec_frame = Frame.objects.create(**fparams)

            sblock2_params = {
                 'cadence'         : False,
                 'body'            : self.body,
                 'proposal'        : self.test_proposal,
                 'block_start'     : '2015-04-20 13:00:00',
                 'block_end'       : '2015-04-22 03:00:00',
                 'tracking_number' : '4243',
                 'active'          : False
               }
            self.test_sblock2 = SuperBlock.objects.create(pk=4, **sblock2_params)

            block2_params = {
                 'telclass'        : '2m0',
                 'site'            : 'ogg',
                 'body'            : self.body,
                 'proposal'        : self.test_proposal,
                 'superblock'      : self.test_sblock2,
                 'obstype'         : 0,
                 'block_start'     : '2015-04-22 13:00:00',
                 'block_end'       : '2015-04-24 03:00:00',
                 'tracking_number' : '54321',
                 'num_exposures'   : 1,
                 'exp_length'      : 1800.0,
                 'active'          : False,
               }
            self.test_block2 = Block.objects.create(pk=4, **block2_params)

            msblock_params = {
                 'cadence'         : False,
                 'body'            : self.body,
                 'proposal'        : self.test_proposal,
                 'block_start'     : '2018-01-01 00:00:00',
                 'block_end'       : '2018-01-01 03:00:00',
                 'tracking_number' : '4244',
                 'active'          : True
               }
            self.test_msblock = SuperBlock.objects.create(pk=5, **msblock_params)
            mblock1_params = {
                 'telclass'        : '2m0',
                 'site'            : 'ogg',
                 'body'            : self.body,
                 'proposal'        : self.test_proposal,
                 'superblock'      : self.test_msblock,
                 'obstype'         : Block.OPT_SPECTRA,
                 'block_start'     : '2018-01-01 00:00:00',
                 'block_end'       : '2018-01-01 02:00:00',
                 'tracking_number' : '54322',
                 'num_exposures'   : 1,
                 'num_observed'    : 1,
                 'exp_length'      : 1800.0,
                 'active'          : True,
               }
            self.test_mblock1 = Block.objects.create(pk=5, **mblock1_params)
            mfparams1 = {
                'sitecode'      : 'F65',
                'filename'      : 'sp233/a265962.sp233.txt',
                'exptime'       : 1800.0,
                'midpoint'      : '2018-01-01 01:00:00',
                'frametype'     : Frame.SPECTRUM_FRAMETYPE,
                'block'         : self.test_mblock1,
                'frameid'       : 1,
               }
            self.mspec_frame1 = Frame.objects.create(**mfparams1)
            mblock2_params = {
                 'telclass'        : '2m0',
                 'site'            : 'ogg',
                 'body'            : self.body,
                 'proposal'        : self.test_proposal,
                 'superblock'      : self.test_msblock,
                 'obstype'         : Block.OPT_SPECTRA,
                 'block_start'     : '2018-01-01 01:00:00',
                 'block_end'       : '2018-01-01 03:00:00',
                 'tracking_number' : '54323',
                 'num_exposures'   : 1,
                 'num_observed'    : 1,
                 'exp_length'      : 1800.0,
                 'active'          : True,
               }
            self.test_mblock2 = Block.objects.create(pk=6, **mblock2_params)
            mfparams2 = {
                'sitecode'      : 'F65',
                'filename'      : 'sp233/a265962.sp233.txt',
                'exptime'       : 1800.0,
                'midpoint'      : '2018-01-01 02:00:00',
                'frametype'     : Frame.SPECTRUM_FRAMETYPE,
                'block'         : self.test_mblock2,
                'frameid'       : 1,
               }
            self.mspec_frame2 = Frame.objects.create(**mfparams2)

            update_proposal_permissions(self.bart, [{'code': self.neo_proposal.code}])

        @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
        def login(self):
            self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
            username_input = self.browser.find_element_by_id("username")
            username_input.send_keys(self.username)
            password_input = self.browser.find_element_by_id("password")
            password_input.send_keys(self.password)
            with self.wait_for_page_load(timeout=10):
                self.browser.find_element_by_id("login-btn").click()
            # Wait until response is recieved
            self.wait_for_element_with_id('page')

        @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
        @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
        def test_failed_block(self):
            self.login()
            blocks_url = reverse('blocklist')
            self.browser.get(self.live_server_url + blocks_url)
            with self.wait_for_page_load(timeout=10):
                self.browser.find_element_by_link_text('4').click()
            side_text = self.browser.find_element_by_class_name('block-status').text
            block_lines = side_text.splitlines()
            testlines = ['2015-04-22', '13:00 2015-04-24', '03:00']
            for line in testlines:
                self.assertIn(line, block_lines)
            actual_url = self.browser.current_url
            target_url = self.live_server_url+'/block/'+'4/'
            self.assertIn('Block details | LCO NEOx', self.browser.title)
            self.assertEqual(target_url, actual_url)

        @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
        @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
        def test_can_view_spectrum(self):   # test opening up a spectrum file associated with a block
            self.login()
            self.browser.get(self.live_server_url)
            blocks_url = reverse('blocklist')
            self.browser.get(self.live_server_url + blocks_url)
            with self.wait_for_page_load(timeout=10):
                self.browser.find_element_by_link_text(str(self.test_sblock.pk)).click()
            with self.wait_for_page_load(timeout=10):
                self.browser.find_element_by_link_text('Spectrum Plot').click()
                # note: block and body do not match spectra.
                # mismatch due to recycling and laziness
            actual_url = self.browser.current_url
            target_url = self.live_server_url+'/block/'+str(self.test_block.pk)+'/spectra/'
            self.assertIn('Spectrum for block: '+str(self.test_block.pk)+' | LCO NEOx', self.browser.title)
            self.assertEqual(target_url, actual_url)

        @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
        @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
        def test_multi_spec_block(self):    # test opening 2 different spectra in same superblock
            self.login()
            blocks_url = reverse('blocklist')
            self.browser.get(self.live_server_url + blocks_url)
            self.browser.find_element_by_link_text('5').click()
            with self.wait_for_page_load(timeout=10):
                plots = self.browser.find_elements_by_link_text('Spectrum Plot')[0].click()
                actual_url = self.browser.current_url
                target_url = self.live_server_url+'/block/'+str(self.test_mblock1.pk)+'/spectra/'
            self.assertIn('Spectrum for block: '+str(self.test_mblock1.pk)+' | LCO NEOx', self.browser.title)
            self.assertEqual(target_url, actual_url)

            self.wait_for_element_with_id('page')
            self.browser.back()
            with self.wait_for_page_load(timeout=10):
                self.browser.find_elements_by_link_text('Spectrum Plot')[1].click()
            # note: this spectrum is same as first one. really just checking if pages are different.
                actual_url2 = self.browser.current_url
                target_url2 = self.live_server_url+'/block/'+str(self.test_mblock2.pk)+'/spectra/'
            self.assertIn('Spectrum for block: '+str(self.test_mblock2.pk)+' | LCO NEOx', self.browser.title)
            self.assertEqual(target_url2, actual_url2)
