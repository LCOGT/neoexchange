"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2019 LCO

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
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from selenium import webdriver
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_find_images_for_block
from core.models import Frame, SourceMeasurement, Candidate
from astropy.wcs import WCS
from numpy import array
import time


class AnalyserTest(FunctionalTest):
    def setUp(self):
        # self.browser = webdriver.Firefox()

        super(AnalyserTest, self).setUp()

        self.username = 'marge'
        self.password = 'simpson'
        self.email = 'marge@simpson.org'
        self.marge = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.marge.first_name = 'Marge'
        self.marge.last_name = 'Simpson'
        self.marge.is_active = 1
        self.marge.save()

        null_wcs = WCS(naxis=2)
        null_wcs.pixel_shape = (4096,4096)
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'file1.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2017-01-01 21:09:51',
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                    'block'         : self.test_block,
                    'frameid'       : 1,
                    'wcs'           : null_wcs
                 }
        self.frame1 = Frame.objects.create(**params)
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'file2.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2017-01-01 21:20:00',
                    'frametype'     : Frame.BANZAI_RED_FRAMETYPE,
                    'block'         : self.test_block,
                    'frameid'       : 2,
                    'wcs'           : null_wcs
                 }
        self.frame2 = Frame.objects.create(**params)
        params1 = {
            'body'   : self.body,
            'frame'  : self.frame1,
            'obs_ra' : 10.1,
            'obs_dec': 10.2,
            'aperture_size' : 1
        }
        self.source1 = SourceMeasurement.objects.create(**params1)
        params2 = {
            'body'   : self.body,
            'frame'  : self.frame2,
            'obs_ra' : 10.15,
            'obs_dec': 10.25,
            'aperture_size' : 1
        }
        self.source2 = SourceMeasurement.objects.create(**params2)

        self.test_block.num_observed = 1
        self.test_block.save()

        # Build Candidate --- WHY??? This cannot be the best way...
        self.dtypes =\
             {  'names' : ('det_number', 'frame_number', 'sext_number', 'jd_obs', 'ra', 'dec', 'x', 'y', 'mag', 'fwhm', 'elong', 'theta', 'rmserr', 'deltamu', 'area', 'score', 'velocity', 'sky_pos_angle', 'pixels_frame', 'streak_length'),
                'formats' : ('i4',       'i1',           'i4',          'f8',     'f8', 'f8', 'f4', 'f4', 'f4', 'f4',   'f4',    'f4',    'f4',     'f4',       'i4',   'f4',   'f4',       'f4',        'f4',           'f4')
             }

        self.dets_array = array([(1, 1, 3283, 2457444.656045, 10.924317, 39.27700, 2103.245, 2043.026, 19.26, 12.970, 1.764, -60.4, 0.27, 1.39, 34, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 2,    0, 2457444.657980, 10.924298, 39.27793, 2103.468, 2043.025,  0.00,  1.000, 1.000,   0.0, 0.27, 0.00,  0, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 3, 3409, 2457444.659923, 10.924271, 39.27887, 2104.491, 2043.034, 19.20, 11.350, 1.373, -57.3, 0.27, 1.38, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 4, 3176, 2457444.661883, 10.924257, 39.27990, 2104.191, 2043.844, 19.01, 10.680, 1.163, -41.5, 0.27, 1.52, 52, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 5, 3241, 2457444.663875, 10.924237, 39.28087, 2104.365, 2043.982, 19.17, 12.940, 1.089, -31.2, 0.27, 1.27, 55, 1.10, 0.497, 0.2, 9.0, 6.7),
                                (1, 6, 3319, 2457444.665812, 10.924220, 39.28172, 2104.357, 2043.175, 18.82, 12.910, 1.254, -37.8, 0.27, 1.38, 69, 1.10, 0.497, 0.2, 9.0, 6.7), ],
                                dtype=self.dtypes)
        self.dets_byte_array = self.dets_array.tostring()
        params3 = {
            'block'   : self.test_block,
            'cand_id' : 1,
            'score'  : 1.42,
            'avg_midpoint' : datetime(2016, 2, 26, 3, 53, 7),
            'avg_x'  : 1024.0,
            'avg_y'  : 1042.3,
            'avg_ra' : 123.42,
            'avg_dec' : -42.3,
            'avg_mag' : 20.7,
            'speed'   : 0.497,
            'sky_motion_pa' : 90.4,
            'detections' : self.dets_byte_array
        }
        self.candidate = Candidate.objects.create(**params3)

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

    @patch('core.frames.find_images_for_block', mock_find_images_for_block)
    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def test_analyser_appears(self):
        self.login()
        analyser_url = reverse('block-view', kwargs={'pk': self.test_block.pk})
        self.browser.get(self.live_server_url + analyser_url)

        self.wait_for_element_with_id('page')
        # Make sure we are on the Block details page
        self.assertIn('Cadence details | LCO NEOx', self.browser.title)

        # Click the analyse images button
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id('analyse-btn').click()

        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        # Make sure we are back to the Block details page
        self.assertIn('Light Monitor', self.browser.title)

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def test_analyser_not_available(self):
        self.login()
        analyser_url = reverse('block-ast', kwargs={'pk': self.test_block2.pk})
        self.browser.get(self.live_server_url + analyser_url)

        # Marge should be returned to the block details page because test_block2
        # doesn't have any frames or candidates
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        # Make sure we are back to the Block details page
        self.assertIn('Block details | LCO NEOx', self.browser.title)
