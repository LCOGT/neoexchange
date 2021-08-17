"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

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
from django.urls import reverse
from django.core.files.storage import default_storage
from datetime import datetime, date
from django.contrib.auth.models import User
from neox.auth_backend import update_proposal_permissions
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from core.models import Block, SuperBlock, Frame, Body, PreviousSpectra, DataProduct
from core.utils import save_dataproduct
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_archive_frames,\
    mock_fetch_archive_frames_2spectra, mock_archive_spectra_header, mock_archive_bad_spectra_header
from django.conf import settings

import os
import tempfile
from shutil import copy2, rmtree
from glob import glob


def build_data_dir(path, base_path, filename):
    if not default_storage.exists(name=path):
        os.makedirs(path)
    copy2(os.path.join(base_path, filename), path)


class SpectraplotTest(FunctionalTest):

    def setUp(self):
        super(SpectraplotTest, self).setUp()
        self.spectradir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))
        spec_path = os.path.join(self.spectradir, 'target_2df_ex.fits')
        analog_path = os.path.join(self.spectradir, 'analog_2df_ex.fits')
        analog2_path = os.path.join(self.spectradir, 'test_2df_ex.fits')

        settings.MEDIA_ROOT = self.test_dir

        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name = 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()

        # build individual target blocks
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
             'site'            : 'coj',
             'body'            : self.body,
             'superblock'      : self.test_sblock,
             'obstype'         : Block.OPT_SPECTRA,
             'block_start'     : '2019-07-27 13:00:00',
             'block_end'       : '2019-07-28 03:00:00',
             'request_number' : '1878696',
             'num_exposures'   : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 16, 42, 51)
           }
        self.test_block = Block.objects.create(pk=3, **block_params)
        save_dataproduct(self.test_block, spec_path, DataProduct.FITS_SPECTRA)

        analog_block_params = {
             'telclass'        : '2m0',
             'site'            : 'coj',
             'body'            : self.body,
             'calibsource'     : self.calib,
             'superblock'      : self.test_sblock,
             'obstype'         : Block.OPT_SPECTRA_CALIB,
             'block_start'     : '2019-07-27 13:00:00',
             'block_end'       : '2019-07-28 03:00:00',
             'request_number' : '1878697',
             'num_exposures'   : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 18, 42, 51)
           }
        self.analog_block = Block.objects.create(pk=7, **analog_block_params)
        save_dataproduct(self.analog_block, analog_path, DataProduct.FITS_SPECTRA)

        fparams = {
            'sitecode'      : 'E10',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2015-04-21 00:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.test_block,
            'frameid'       : 1,
           }
        self.spec_frame = Frame.objects.create(**fparams)

        afparams = {
            'sitecode'      : 'E10',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2015-04-21 00:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.analog_block,
            'frameid'       : 7,
           }
        self.analogspec_frame = Frame.objects.create(**afparams)

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
             'superblock'      : self.test_sblock2,
             'obstype'         : Block.OPT_IMAGING,
             'block_start'     : '2015-04-22 13:00:00',
             'block_end'       : '2015-04-24 03:00:00',
             'request_number' : '54321',
             'num_exposures'   : 1,
             'exp_length'      : 1800.0,
             'active'          : False,
             'when_observed'   : datetime(2015, 7, 27, 16, 42, 51)
           }
        self.test_block2 = Block.objects.create(pk=4, **block2_params)

        save_dataproduct(self.test_block2, spec_path, DataProduct.FITS_SPECTRA, filename='test2_2df_ex.fits')

        analog_block2_params = {
            'telclass': '2m0',
            'site': 'coj',
            'calibsource': self.calib,
            'superblock': self.test_sblock2,
            'obstype': Block.OPT_SPECTRA_CALIB,
            'block_start': '2019-07-27 13:00:00',
            'block_end': '2019-07-28 03:00:00',
            'request_number': '54321',
            'num_exposures': 1,
            'exp_length': 1800.0,
            'active': True,
            'when_observed': datetime(2019, 7, 27, 18, 42, 51)
        }
        self.analog_block2 = Block.objects.create(pk=10, **analog_block2_params)
        save_dataproduct(self.analog_block2, analog2_path, DataProduct.FITS_SPECTRA)

        # Build multi-frame Blocks
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
             'site'            : 'coj',
             'body'            : self.body,
             'superblock'      : self.test_msblock,
             'obstype'         : Block.OPT_SPECTRA,
             'block_start'     : '2018-01-01 00:00:00',
             'block_end'       : '2018-01-01 02:00:00',
             'request_number'  : '54322',
             'num_exposures'   : 2,
             'num_observed'    : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 16, 42, 51)
           }
        self.test_mblock1 = Block.objects.create(pk=5, **mblock1_params)
        save_dataproduct(self.test_mblock1, spec_path, DataProduct.FITS_SPECTRA, filename='test3_2df_ex.fits')
        save_dataproduct(self.test_mblock1, spec_path, DataProduct.FITS_SPECTRA, filename='test3.2_2df_ex.fits')

        mfparams1 = {
            'sitecode'      : 'F65',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2018-01-01 01:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.test_mblock1,
            'frameid'       : 10,
           }
        self.mspec_frame1 = Frame.objects.create(**mfparams1)
        mblock2_params = {
             'telclass'        : '2m0',
             'site'            : 'ogg',
             'body'            : self.body,
             'superblock'      : self.test_msblock,
             'obstype'         : Block.OPT_SPECTRA,
             'block_start'     : '2018-01-01 01:00:00',
             'block_end'       : '2018-01-01 03:00:00',
             'request_number' : '54323',
             'num_exposures'   : 1,
             'num_observed'    : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 16, 42, 51)
           }
        self.test_mblock2 = Block.objects.create(pk=6, **mblock2_params)
        save_dataproduct(self.test_mblock2, spec_path, DataProduct.FITS_SPECTRA, filename='test4_2df_ex.fits')

        mfparams2 = {
            'sitecode'      : 'F65',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2018-01-01 02:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.test_mblock2,
            'frameid'       : 11,
           }
        self.mspec_frame2 = Frame.objects.create(**mfparams2)

        # make empty block
        sblock_params_empty = msblock_params
        self.test_sblock_empty = SuperBlock.objects.create(pk=6, **sblock_params_empty)
        block_params_empty = mblock2_params
        block_params_empty['superblock'] = self.test_sblock_empty
        block_params_empty['when_observed'] = datetime(2019, 9, 27, 16, 42, 51)
        self.test_block_empty = Block.objects.create(**block_params_empty)
        frame_params_empty = mfparams2
        frame_params_empty['block'] = self.test_block_empty
        self.spec_frame_empty = Frame.objects.create(**frame_params_empty)

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

    @patch('core.views.lco_api_call', mock_archive_spectra_header)
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

    @patch('core.views.lco_api_call', mock_archive_spectra_header)
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

        spec_plot = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@name='spec_plot']/div[@class='bk']/div[@class='bk'][2]/div[@class='bk']/div[@class='bk']/div[@class='bk bk-canvas-events']")

    @patch('core.views.lco_api_call', mock_archive_spectra_header)
    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
    def test_multi_request_block(self):    # test opening 2 different blocks in same superblock
        self.login()
        blocks_url = reverse('blocklist')
        self.browser.get(self.live_server_url + blocks_url)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_link_text('5').click()
        with self.wait_for_page_load(timeout=10):
            self.browser.find_elements_by_link_text('Spectrum Plot')[0].click()
        actual_url = self.browser.current_url
        target_url = self.live_server_url+'/block/'+str(self.test_mblock1.pk)+'/spectra/'
        self.assertIn('Spectrum for block: '+str(self.test_mblock1.pk)+' | LCO NEOx', self.browser.title)
        self.assertEqual(target_url, actual_url)

        spec_plot = self.browser.find_element_by_name("spec_plot")
        self.assertIn("HD 196164 -- 20190723 (1.03) [ || ]", spec_plot.text)

        self.wait_for_element_with_id('page')
        with self.wait_for_page_load(timeout=10):
            self.browser.back()

        with self.wait_for_page_load(timeout=10):
            self.browser.find_elements_by_link_text('Spectrum Plot')[1].click()
        actual_url2 = self.browser.current_url
        target_url2 = self.live_server_url+'/block/'+str(self.test_mblock2.pk)+'/spectra/'
        self.assertIn('Spectrum for block: '+str(self.test_mblock2.pk)+' | LCO NEOx', self.browser.title)
        self.assertEqual(target_url2, actual_url2)

        spec_plot = self.browser.find_element_by_name("spec_plot")
        self.assertIn("None", spec_plot.text)

    @patch('core.views.lco_api_call', mock_archive_spectra_header)
    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames_2spectra)
    def test_multi_spectra_block(self):    # test opening 2 different spectra in same block
        self.mspec_frame2.block = self.test_mblock1
        self.mspec_frame2.save()

        self.login()
        blocks_url = reverse('blocklist')
        self.browser.get(self.live_server_url + blocks_url)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_link_text('5').click()
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_link_text('Spectrum Plot').click()
        actual_url = self.browser.current_url
        target_url = self.live_server_url+'/block/'+str(self.test_mblock1.pk)+'/spectra/'
        self.assertIn('Spectrum for block: '+str(self.test_mblock1.pk)+' | LCO NEOx', self.browser.title)
        self.assertEqual(target_url, actual_url)
        spec_plot = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@name='spec_plot']/div[@class='bk']/div[@class='bk'][2]/div[@class='bk']/div[@class='bk']/div[@class='bk bk-canvas-events']")
        target_list = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@name='spec_plot']/div[@class='bk']/div[@class='bk'][1]/div[@class='bk'][1]/div[@class='bk bk-input-group']/select[@class='bk bk-input']")
        self.assertIn('2', target_list.text)
        analog_list = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@name='spec_plot']/div[@class='bk']/div[@class='bk'][1]/div[@class='bk'][2]/div[@class='bk bk-input-group']/select[@class='bk bk-input']")
        self.assertIn('HD 196164', analog_list.text)
        self.assertIn('398188', analog_list.text)

    @patch('core.views.lco_api_call', mock_archive_bad_spectra_header)
    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
    def test_no_analog_no_spectra(self):    # test failure to find fits

        self.login()
        blocks_url = reverse('blocklist')
        self.browser.get(self.live_server_url + blocks_url)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_link_text('6').click()
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_link_text('Spectrum Plot').click()
        actual_url = self.browser.current_url
        target_url = self.live_server_url+'/block/'+str(self.test_block_empty.pk)+'/spectra/'
        self.assertIn('Spectrum for block: '+str(self.test_block_empty.pk)+' | LCO NEOx', self.browser.title)
        self.assertEqual(target_url, actual_url)
        try:
            spec_plot = self.browser.find_element_by_name("spec_plot")
            raise Exception("FAILURE: Should not find spectroscopy plot")
        except NoSuchElementException:
            pass
        source_text = self.browser.find_element_by_id("main")
        self.assertIn('Cannot find data. :(', source_text.text)


class SMASSPlotTest(FunctionalTest):

    def setUp(self):
        super(SMASSPlotTest, self).setUp()
        self.spectradir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))

        settings.MEDIA_ROOT = self.spectradir
        self.filename = 'a001981.4.txt'

        # Create test body
        params = {   'provisional_name': None,
                     'provisional_packed': None,
                     'name': '66146',
                     'origin': 'G',
                     'source_type': 'N',
                     'source_subtype_1': 'N2',
                     'source_subtype_2': None,
                     'elements_type': 'MPC_MINOR_PLANET',
                     'active': True,
                     'fast_moving': False,
                     'urgency': None,
                     'epochofel': datetime(2020, 1, 9, 0, 0),
                     'orbit_rms': 0.0,
                     'orbinc': 5.40597,
                     'longascnode': 102.01922,
                     'argofperih': 84.84692,
                     'eccentricity': 0.4836881,
                     'meandist': 0.7872702,
                     'meananom': 292.23025,
                     'perihdist': None,
                     'epochofperih': None,
                     'abs_mag': 14.34,
                     'slope': 0.15,
                     'score': None,
                     'discovery_date': datetime(1982, 12, 4, 0, 0),
                     'num_obs': 119,
                     'arc_length': 74.0,
                     'not_seen': 809.8523994142245,
                     'updated': True,
                     'ingest': datetime(2017, 8, 2, 5, 3, 24),
                     'update_time': datetime(2020, 1, 16, 20, 25, 28)
                    }
        self.body, created = Body.objects.get_or_create(**params)

        params2 = {  'body' : self.body,
                     'spec_wav': 'Vis+NIR',
                     'spec_vis': self.filename,
                     'spec_ir': self.filename,
                     'spec_ref': 'sp[025]',
                     'spec_source': 'S',
                     'spec_date': date(2012, 11, 6)
                     }
        self.spec_data, created = PreviousSpectra.objects.get_or_create(**params2)

    @patch('core.plots.datetime', MockDateTime)
    def test_can_view_previous_spectra(self):
        MockDateTime.change_datetime(2015, 3, 19, 6, 00, 00)
        # A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a link from the targets' name on the front page to a more
        # detailed view.
        link = self.browser.find_element_by_link_text('66146')

        # She clicks the link and is taken to a page with the targets' details.
        with self.wait_for_page_load(timeout=10):
            link.click()

        # She clicks a link to view external spectra for this target
        link = self.browser.find_element_by_link_text('(Plots)')
        with self.wait_for_page_load(timeout=10):
            link.click()

        spec_plot = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@name='spec_plot']/div[@class='bk']/div[@class='bk'][1]/div[@class='bk']/div[@class='bk']/div[@class='bk bk-canvas-events']")
        try:
            target_list = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@name='spec_plot']/div[@class='bk']/div[@class='bk'][1]/div[@class='bk'][1]/div[@class='bk bk-input-group']/select[@class='bk bk-input']")
            analog_list = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@name='spec_plot']/div[@class='bk']/div[@class='bk'][1]/div[@class='bk'][2]/div[@class='bk bk-input-group']/select[@class='bk bk-input']")
            raise Exception("Target list, or Analog list is present when it shouldn't be.")
        except NoSuchElementException:
            pass
