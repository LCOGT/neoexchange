from .base import FunctionalTest
from django.test import TestCase, override_settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from selenium import webdriver
from mock import patch
from neox.tests.mocks import MockDateTime, mock_rbauth_login, mock_find_images_for_block
from core.models import Frame, SourceMeasurement
import time

class AnalyserTest(FunctionalTest):
    def setUp(self):

        super(AnalyserTest,self).setUp()

        self.username = 'marge'
        self.password = 'simpson'
        self.email = 'marge@simpson.org'
        self.marge = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.marge.first_name= 'Marge'
        self.marge.last_name = 'Simpson'
        self.marge.is_active=1
        self.marge.save()

        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'file1.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2017-01-01 21:09:51',
                    'block'         : self.test_block,
                    'frameid'       : 1
                 }
        self.frame1 = Frame.objects.create(**params)
        params = {  'sitecode'      : 'K93',
                    'instrument'    : 'kb75',
                    'filter'        : 'w',
                    'filename'      : 'file2.fits',
                    'exptime'       : 40.0,
                    'midpoint'      : '2017-01-01 21:20:00',
                    'block'         : self.test_block,
                    'frameid'       : 2
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

    def login(self):
        self.browser.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_xpath('//button[@id="login-btn"]').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')

    @patch('core.frames.find_images_for_block', mock_find_images_for_block)
    def test_analyser_appears(self):
        self.login()
        analyser_url = reverse('block-view', kwargs={'pk':self.test_block.pk})
        self.browser.get(self.live_server_url + analyser_url)

        self.wait_for_element_with_id('page')
        # Make sure we are on the Block details page
        self.assertIn('Block details | LCO NEOx', self.browser.title)

        # Click the analyse images button
        self.browser.find_element_by_xpath('//a[@id="analyse-btn"]').click()

        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        # Make sure we are back to the Block details page
        self.assertIn('Light Monitor', self.browser.title)


    def test_analyser_not_available(self):
        self.login()
        analyser_url = reverse('block-ast', kwargs={'pk':self.test_block2.pk})
        self.browser.get(self.live_server_url + analyser_url)

        # Marge should be returned to the block details page because test_block2
        # doesn't have any frames or candidates
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        # Make sure we are back to the Block details page
        self.assertIn('Block details | LCO NEOx', self.browser.title)
