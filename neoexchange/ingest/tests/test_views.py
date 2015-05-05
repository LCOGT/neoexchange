'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime
from django.test import TestCase
from django.http import HttpRequest
from django.core.urlresolvers import resolve, reverse
from django.template.loader import render_to_string
from django.views.generic import ListView
from django.forms.models import model_to_dict
from django.utils.html import escape
from unittest import skipIf

#Import module to test
from ingest.ephem_subs import call_compute_ephem, determine_darkness_times
from ingest.views import home, clean_NEOCP_object
from ingest.models import Body, Proposal
from ingest.forms import EphemQuery


class TestClean_NEOCP_Object(TestCase):

    def test_X33656(self):
        obs_page = [u'X33656  23.9  0.15  K1548 330.99052  282.94050   31.81272   13.02458  0.7021329  0.45261672   1.6800247                  3   1    0 days 0.21         NEOCPNomin',
                    u'X33656  23.9  0.15  K1548 250.56430  257.29551   60.34849    2.58054  0.0797769  0.87078998   1.0860765                  3   1    0 days 0.20         NEOCPV0001',
                    u'X33656  23.9  0.15  K1548 256.86580  263.73491   53.18662    3.17001  0.1297341  0.88070404   1.0779106                  3   1    0 days 0.20         NEOCPV0002',
                   ]
        expected_elements = { 'abs_mag'     : 23.9,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 4, 8, 0, 0, 0),
                              'meananom'    : 330.99052,
                              'argofperih'  : 282.94050,
                              'longascnode' :  31.81272,
                              'orbinc'      :  13.02458,
                              'eccentricity':  0.7021329,
                             # 'MDM':   0.45261672,
                              'meandist'    :  1.6800247,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    def test_missing_absmag(self):
        obs_page = ['Object   H     G    Epoch    M         Peri.      Node       Incl.        e           n         a                     NObs NOpp   Arc    r.m.s.       Orbit ID',
                    'N007riz       0.15  K153J 340.52798   59.01148  160.84695   10.51732  0.3080134  0.56802014   1.4439768                  6   1    0 days 0.34         NEOCPNomin',
                    'N007riz       0.15  K153J 293.77087  123.25671  129.78437    3.76739  0.0556350  0.93124537   1.0385481                  6   1    0 days 0.57         NEOCPV0001'
                   ]

        expected_elements = { 'abs_mag'     : 99.99,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 3, 19, 0, 0, 0),
                              'meananom'    : 340.52798,
                              'argofperih'  :  59.01148,
                              'longascnode' : 160.84695,
                              'orbinc'      :  10.51732,
                              'eccentricity':  0.3080134,
                             # 'MDM':   0.56802014,
                              'meandist'    :  1.4439768,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

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
        self.assertTemplateUsed(response, 'ingest/home.html')

    def test_home_page_uses_ephemquery_form(self):
        response = self.client.get('/')
        self.assertIsInstance(response.context['form'], EphemQuery)


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
        utc_date = datetime(2015, 4, 21, 3,0,0)
        dark_start, dark_end = determine_darkness_times(site_code, utc_date )

        response = self.client.get('/ephemeris/',
            data={'target'      : 'N999r0q',
                  'site_code'   : site_code,
                  'utc_date'    : '2015-04-21',
                  'alt_limit'   : 0}
        )
        self.assertIn('N999r0q', response.content.decode())
        body_elements = model_to_dict(self.body)
        ephem_lines = call_compute_ephem(body_elements, dark_start, dark_end, site_code, '5m' )
        expected_html = render_to_string(
            'ingest/ephem.html',
            {'new_target_name' : 'N999r0q',
            'ephem_lines'  : ephem_lines,
            'site_code' : site_code }
        )
        self.assertMultiLineEqual(response.content.decode(), expected_html)

    def test_displays_ephem(self):
        response = self.client.get('/ephemeris/',
            data ={'target' : 'N999r0q',
                   'utc_date' : '2015-05-11',
                   'site_code' : 'V37',
                   'alt_limit' : 30.0
                   }
            )
        self.assertContains(response, 'Ephemeris for')

    def test_uses_ephem_template(self):
        response = self.client.get('/ephemeris/',
            data = {'target' : 'N999r0q',
                    'site_code' : 'W86',
                    'utc_date'  : '2015-04-20',
                    'alt_limit' : 40.0
                    }
            )
        self.assertTemplateUsed(response, 'ingest/ephem.html')

    def test_form_errors_are_sent_back_to_home_page(self):
        response = self.client.get('/ephemeris/', data={'target' : ''})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ingest/home.html')
        expected_error = escape("Target name is required")
        self.assertContains(response, expected_error)

    def test_ephem_page_displays_site_code(self):
        response = self.client.get('/ephemeris/',
            data = {'target' : 'N999r0q',
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
        expected_html = render_to_string('ingest/body_list.html')
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

    def test_uses_schedule_template(self):
        response = self.client.get('/schedule/',
            data = {'body_id'   : self.body.pk,
                    'site_code' : 'F65',
                    'utc_date'  : '2015-04-20',
                    }
        )
        self.assertTemplateUsed(response, 'ingest/schedule.html')

    def test_schedule_page_contains_object_name(self):
        response = self.client.get('/schedule/',
            data = {'body_id'   : self.body.pk,
                    'site_code' : 'F65',
                    'utc_date'  : '2015-04-20',
                    'proposal_code' : self.neo_proposal.code
                    }
            )
        self.assertContains(response, 'Scheduling for: ' + self.body.current_name())
