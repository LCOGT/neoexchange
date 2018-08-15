from .base import FunctionalTest
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from neox.auth_backend import update_proposal_permissions
from selenium import webdriver
from core.models import Block, SuperBlock, Frame
from mock import patch
from neox.tests.mocks import MockDateTime, mock_lco_authenticate, mock_fetch_archive_frames

class GuideMovieTest(FunctionalTest):

        def setUp(self):

            super(GuideMovieTest,self).setUp()

            self.username = 'bart'
            self.password = 'simpson'
            self.email = 'bart@simpson.org'
            self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
            self.bart.first_name= 'Bart'
            self.bart.last_name = 'Simpson'
            self.bart.is_active=1
            self.bart.save()

            # sbparams = {  'body'           :  self.body,
            #               'proposal'       :  self.test_proposal,
            #               'tracking_number':  '00045',
            #            }
            # self.test_spec_sblock = SuperBlock.objects.create(pk=99,**sbparams)
            # bparams = { 'body'           :  self.body,
            #             'proposal'       :  self.test_proposal,
            #             'block_start'    :  '2018-08-01 06:00:00',
            #             'tracking_number':  '00045',
            #             'superblock'     :  self.test_sblock,
            #             'num_exposures'  :  1,
            #             'exp_length'     :  1800.0,
            #             'obstype'        :  Block.OPT_SPECTRA,
            #             'num_observed'   :  1
            #           }
            # self.test_spec_block = Block.objects.create(pk=99,**bparams)
            # fparams = { 'sitecode'      : 'F65',
            #             'filename'      : 'gf1.fits',
            #             'exptime'       : 1800.0,
            #             'midpoint'      : '2018-01-01 00:00:00',
            #             'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            #             'block'         : self.test_spec_block,
            #             'frameid'       : 1,
            #           }
            # self.spec_frame = Frame.objects.create(**fparams)
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
                 'proposal' : self.test_proposal,
                 'superblock' : self.test_sblock,
                 'obstype'  : Block.OPT_SPECTRA,
                 'block_start' : '2015-04-20 13:00:00',
                 'block_end'   : '2015-04-21 03:00:00',
                 'tracking_number' : '12345',
                 'num_exposures' : 1,
                 'exp_length' : 1800.0,
                 'active'   : True,
               }
            self.test_block = Block.objects.create(**block_params)
            fparams = { 'sitecode'      : 'F65',
                        'filename'      : 'gf1.fits',
                        'exptime'       : 1800.0,
                        'midpoint'      : '2018-01-01 00:00:00',
                        'frametype'     : Frame.SPECTRUM_FRAMETYPE,
                        'block'         : self.test_block,
                        'frameid'       : 1,
                      }
            self.spec_frame = Frame.objects.create(**fparams)
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
        def test_can_view_guide_movie(self):
            self.login()
            self.browser.get(self.live_server_url)
            blocks_url = reverse('blocklist')
            self.browser.get(self.live_server_url + blocks_url)
            with self.wait_for_page_load(timeout=10):
                self.browser.find_element_by_link_text(str(self.test_sblock.pk)).click()
            with self.wait_for_page_load(timeout=20):
                self.browser.find_element_by_link_text('Guide Movie').click()
            actual_url = self.browser.current_url
            target_url = self.live_server_url+'/block/'+str(self.test_sblock.pk)+'/guidemovie/'

            self.assertIn('Guide Movie | LCO NEOx', self.browser.title)
            self.assertEqual(target_url, actual_url)
