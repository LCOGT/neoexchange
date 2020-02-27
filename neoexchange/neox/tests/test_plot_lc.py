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
from django.contrib.auth.models import User
from neox.auth_backend import update_proposal_permissions
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from core.models import Body
from mock import patch
from neox.tests.mocks import mock_lco_authenticate
from django.conf import settings

import os
import tempfile
from shutil import copy2, rmtree
from glob import glob


def build_data_dir(path, base_path, filename):
    if not default_storage.exists(name=path):
        os.makedirs(path)
        copy2(os.path.join(base_path, filename), path)


class LighCurvePlotTest(FunctionalTest):

    def setUp(self):
        super(LighCurvePlotTest, self).setUp()
        self.lcdir = os.path.abspath(os.path.join('photometrics', 'tests'))

        settings.MEDIA_ROOT = self.test_dir
        build_data_dir(os.path.join(self.test_dir, 'Reduction', '433'), self.lcdir, '433_738215_ALCDEF.txt')

        params = {  'name' : '433',
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
                    'score'         : 90,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 17,
                    'arc_length'    : 3.123456789,
                    'not_seen'      : 0.423456789,
                    'updated'       : True,
                    }
        self.body2, created = Body.objects.get_or_create(pk=2, **params)

        self.body2.save_physical_parameters({'parameter_type' : 'P', 'value': 5.27})

        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name = 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()

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
    def test_no_lightcurve(self):
        self.login()
        lc_url = reverse('lc_plot', args=[self.body.id])
        self.browser.get(self.live_server_url + lc_url)
        error_text = self.browser.find_element_by_class_name('warning').text
        self.assertIn('Lightcurve for object: N999r0q', self.browser.title)
        self.assertIn('Could not find any LC data', error_text)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def test_can_view_lightcurve(self):   # test opening up a ALCDEF file associated with a body
        self.login()
        lc_url = reverse('lc_plot', args=[self.body2.id])
        self.browser.get(self.live_server_url + lc_url)

        self.assertIn('Lightcurve for object: 433', self.browser.title)

        canvas = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@class='bk-root']/div[@class='bk']/div[@class='bk'][2]/div[@class='bk'][1]/div[@class='bk']/div[@class='bk bk-canvas-events']")
        phase_tab = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@class='bk-root']/div[@class='bk']/div[@class='bk bk-tabs-header bk-above']/div[@class='bk bk-headers-wrapper']/div[@class='bk bk-headers']/div[@class='bk bk-tab']")
        phase_tab.click()
        period_box = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@class='bk-root']/div[@class='bk']/div[@class='bk'][2]/div[@class='bk'][2]/div[@class='bk'][2]/div[@class='bk']/div[@class='bk'][1]/div[@class='bk'][1]/div[@class='bk']/div[@class='bk bk-input-group']/input[@class='bk bk-input']")
        period_text = self.browser.find_element_by_xpath("/html/body[@class='page']/div[@id='page-wrapper']/div[@id='page']/div[@id='main']/div[@class='bk-root']/div[@class='bk']/div[@class='bk'][2]/div[@class='bk'][2]/div[@class='bk'][2]/div[@class='bk']/div[@class='bk'][1]/div[@class='bk'][1]/div[@class='bk']/div[@class='bk bk-input-group']/label[@class='bk']").text
        self.assertIn('Period (Default: 5.27h)', period_text)
