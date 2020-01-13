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

from datetime import datetime
from django.test import TestCase
from django.http import HttpRequest
from django.urls import resolve, reverse
from django.template.loader import render_to_string
from django.views.generic import ListView
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from unittest import skipIf
from mock import patch

# Import module to test
from astrometrics.ephem_subs import call_compute_ephem, determine_darkness_times
from core.models import Body, Proposal, SuperBlock, Block
from neox.settings import VERSION
from neox.tests.mocks import mock_lco_authenticate


class HomePageTest(TestCase):

    def setUp(self):
        params = {  'provisional_name' : 'N999r0q',
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
                    }
        self.body, created = Body.objects.get_or_create(**params)

    def test_home_page_renders_home_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'core/home.html')


class EphemPageTest(TestCase):
    maxDiff = None

    def setUp(self):
        params = {  'provisional_name' : 'N999r0q',
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
                    }
        self.body, created = Body.objects.get_or_create(**params)

    def test_home_page_can_save_a_GET_request(self):

        site_code = 'V37'
        utc_date = datetime(2015, 4, 21, 3, 0, 0)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date)

        response = self.client.get(reverse('ephemeris'),
            data={'target'      : 'N999r0q',
                  'site_code'   : site_code,
                  'utc_date'    : '2015-04-21',
                  'alt_limit'   : 0}
        )
        self.assertIn(u'N999r0q', response.content.decode('utf-8'))
        body_elements = model_to_dict(self.body)
        ephem_lines = call_compute_ephem(body_elements, dark_start, dark_end, site_code, '15m')
        expected_html = render_to_string(
            'core/ephem.html',
            {'target' : self.body,
            'ephem_lines'  : ephem_lines,
            'site_code' : site_code,
            'neox_version' :  VERSION}
        )
        self.assertMultiLineEqual(response.content.decode('utf-8'), expected_html)

    def test_displays_ephem(self):
        response = self.client.get(reverse('ephemeris'),
            data={'target' : 'N999r0q',
                   'utc_date' : '2015-05-11',
                   'site_code' : 'V37',
                   'alt_limit' : 30.0
                   }
            )
        self.assertContains(response, 'Ephemeris for')

    def test_uses_ephem_template(self):
        response = self.client.get('/ephemeris/',
            data={'target' : 'N999r0q',
                    'site_code' : 'W86',
                    'utc_date'  : '2015-04-20',
                    'alt_limit' : 40.0
                    }
            )
        self.assertTemplateUsed(response, 'core/ephem.html')

    def test_form_errors_are_sent_back_to_home_page(self):
        response = self.client.get(reverse('ephemeris'), data={'target' : ''})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')

    def test_ephem_page_displays_site_code(self):
        response = self.client.get(reverse('ephemeris'),
            data={'target' : 'N999r0q',
                    'site_code' : 'F65',
                    'utc_date'  : '2015-04-20',
                    'alt_limit' : 30.0
                    }
            )
        self.assertContains(response, 'Ephemeris for N999r0q at F65')


class TargetsPageTest(TestCase):

    def test_target_url_resolves_to_targets_view(self):
        found = reverse('targetlist')
        self.assertEqual(found, '/target/')

    @skipIf(True, "to be fixed")
    def test_target_page_returns_correct_html(self):
        request = HttpRequest()
        targetlist = ListView.as_view(model=Body, queryset=Body.objects.filter(active=True))
        response = targetlist.render_to_response(targetlist)
        expected_html = render_to_string('core/body_list.html')
        self.assertEqual(response, expected_html)


class ScheduleTargetsPageTest(TestCase):
    maxDiff = None

    def setUp(self):
        # Initialise with a test body and two test proposals
        params = {  'provisional_name' : 'N999r0q',
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
                    }
        self.body, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        test_proposal_params = { 'code'  : 'LCOEngineering',
                                 'title' : 'Test Proposal'
                               }
        self.test_proposal, created = Proposal.objects.get_or_create(**test_proposal_params)
        # Create a user to test login
        self.bart = User.objects.create_user(username='bart', password='simpson', email='bart@simpson.org')
        self.bart.first_name = 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active = 1
        self.bart.save()

    @patch('neox.auth_backend.lco_authenticate', mock_lco_authenticate)
    def login(self):
        self.assertTrue(self.client.login(username='bart', password='simpson'))

    def test_uses_schedule_template(self):
        self.login()
        response = self.client.get(reverse('schedule-body', kwargs={'pk': self.body.pk}),
            data={'body_id'   : self.body.pk,
                    'site_code' : 'F65',
                    'utc_date'  : '2015-04-20',
                    }
        )
        self.assertTemplateUsed(response, 'core/schedule.html')

    def test_schedule_page_contains_object_name(self):
        self.login()
        response = self.client.get(reverse('schedule-body', kwargs={'pk': self.body.pk}),
            data={'body_id'   : self.body.pk,
                    'site_code' : 'F65',
                    'utc_date'  : '2015-04-20',
                    'proposal_code' : self.neo_proposal.code
                    }
            )
        self.assertContains(response, self.body.current_name())


class BlocksPageTest(TestCase):

    def setUp(self):
        # Initialise with a test body and two test proposals
        params = {  'provisional_name' : 'N999r0q',
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
                    }
        self.body, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        test_proposal_params = { 'code'  : 'LCOEngineering',
                                 'title' : 'Test Proposal'
                               }
        self.test_proposal, created = Proposal.objects.get_or_create(**test_proposal_params)
        # Create test blocks
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        self.test_sblock, created = SuperBlock.objects.get_or_create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block, created = Block.objects.get_or_create(**block_params)

        sblock_params2 = {
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'active'   : False,
                       }
        self.test_sblock2, created = SuperBlock.objects.get_or_create(**sblock_params2)
        block_params2 = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body,
                         'superblock' : self.test_sblock2,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block2, created = Block.objects.get_or_create(**block_params2)

    def test_block_url_resolves_to_blocks_view(self):
        found = reverse('blocklist')
        self.assertEqual(found, '/block/list/')

    def test_block_list_page_renders_template(self):
        response = self.client.get(reverse('blocklist'))
        self.assertTemplateUsed(response, 'core/block_list.html')

    def test_block_detail_url_resolves_to_block_detail_view(self):
        found = reverse('block-view', kwargs={'pk': 1})
        self.assertEqual(found, '/block/1/')

    def test_block_detail_page_renders_template(self):
        self.setUp()
        blocks = Block.objects.all()
        response = self.client.get(reverse('block-view', kwargs={'pk': blocks[0].id}))
        self.assertTemplateUsed(response, 'core/block_detail.html')


class RankingPageTest(TestCase):

    def test_ranking_url_resolves_to_ranking_view(self):
        found = reverse('ranking')
        self.assertEqual(found, '/ranking/')

    def test_ranking_page_renders_template(self):
        response = self.client.get(reverse('ranking'))
        self.assertTemplateUsed(response, 'core/ranking.html')
