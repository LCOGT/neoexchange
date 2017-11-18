'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2017 LCO

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
from django.forms.models import model_to_dict

from core.models import Body, Proposal

#Import module to test
from core.forms import EphemQuery, ScheduleForm

class EphemQueryFormTest(TestCase):


    def setUp(self):

        self.maxDiff = None

        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : datetime(2015, 3, 19, 00,00,00),
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : u'U',
                    'elements_type' : u'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'P10uMBz'
        params['name'] = '2016 GS221'
        self.body_similar_name1, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'P10uMD9'
        params['name'] = '2016 GS216'
        self.body_similar_name2, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'P10uJHG'
        params['name'] = '2016 GS216'
        params['source_type']= 'N'
        self.body_similar_name3, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = u'P10ucyy'
        params['name'] = u'2016 GS2'
        params['source_type']= u'N'
        params['origin'] = u'G'
        self.body_similar_name4, created = Body.objects.get_or_create(**params)

        comet_params = { 'abs_mag': 20.5,
                         'active': True,
                         'arc_length': 77.0,
                         'argofperih': 351.88796,
                         'eccentricity': 0.6652004,
                         'elements_type': u'MPC_COMET',
                         'fast_moving': False,
                         'longascnode': 180.52654,
                         'meananom': 3.32334,
                         'meandist': 3.0251663,
                         'name': 'P/2016 BA141',
                         'not_seen': 24.8857164222,
                         'num_obs': 151L,
                         'orbinc': 18.89365,
                         'origin': u'G',
                         'perihdist': 1.0128244,
                         'provisional_name': u'P10rI5K',
                         'provisional_packed': u'',
                         'score': 100L,
                         'slope': 6.4,
                         'source_type': u'C',
                         'updated': True,
                         'urgency': None}
        self.comet, created = Body.objects.get_or_create(**comet_params)

    def test_form_has_label(self):
        form = EphemQuery()
        self.assertIn('Enter target name...', form.as_p())
        self.assertIn('Site code:', form.as_p())

    def test_form_validation_for_blank_target(self):
        form = EphemQuery(data = {'target' : ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['target'],
            ['Target name is required']
        )

    def test_form_validation_for_blank_date(self):
        form = EphemQuery(data = {'utc_date' : ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['utc_date'],
            ['UTC date is required']
        )

    def test_form_handles_save(self):
        form = EphemQuery(data = {'target' : 'N999r0q',
                                  'utc_date' : '2015-04-20',
                                  'site_code' : 'K92',
                                  'alt_limit' : 30.0
                                  })
        self.assertTrue(form.is_valid())

    def test_ephem_form_has_all_sites(self):
        form = EphemQuery()
        self.assertIsInstance(form, EphemQuery)
        self.assertIn('McDonald, Texas (ELP - V37; Sinistro)', form.as_p())
        self.assertIn('value="V37"', form.as_p())
        self.assertIn('Maui, Hawaii (FTN - F65)', form.as_p())
        self.assertIn('value="F65"', form.as_p())
        self.assertIn('Siding Spring, Aust. (FTS - E10)', form.as_p())
        self.assertIn('value="E10"', form.as_p())
        self.assertIn('CTIO, Chile (LSC - W85-87; Sinistro)', form.as_p())
        self.assertIn('value="W86"', form.as_p())
        self.assertIn('Sutherland, S. Africa (CPT - K91-93; Sinistro)', form.as_p())
        self.assertIn('value="K92"', form.as_p())
        self.assertIn('Siding Spring, Aust. (COJ - Q63-64; Sinistro)', form.as_p())
        self.assertIn('value="Q63"', form.as_p())
        self.assertIn('Siding Spring, Aust. (COJ - Q58-59; 0.4m)', form.as_p())
        self.assertIn('value="Q58"', form.as_p())
        self.assertIn('Tenerife, Spain (TFN - Z17,Z21; 0.4m)', form.as_p())
        self.assertIn('value="Z21"', form.as_p())
        self.assertIn('Maui, Hawaii (OGG - T03-04; 0.4m)', form.as_p())
        self.assertIn('value="T04"', form.as_p())
        self.assertIn('CTIO, Chile (LSC - W89; 0.4m)', form.as_p())
        self.assertIn('value="W89"', form.as_p())
        self.assertIn('McDonald, Texas (ELP - V99; 0.4m)', form.as_p())
        self.assertIn('value="V99"', form.as_p())
        self.assertIn('Sutherland, S. Africa (CPT - K99; 0.4m)', form.as_p())
        self.assertIn('value="K99"', form.as_p())

    def test_form_handles_save_with_long_name(self):
        form = EphemQuery(data = {'target' : 'P/2016 BA141',
                                  'utc_date' : '2016-03-11',
                                  'site_code' : 'K92',
                                  'alt_limit' : 30.0
                                  })
        self.assertTrue(form.is_valid())

    def test_form_returns_correct_target(self):
        form = EphemQuery(data = {'target' : '2016 GS2',
                                  'utc_date' : '2016-05-11',
                                  'site_code' : 'K92',
                                  'alt_limit' : 30.0
                                  })
        self.assertTrue(form.is_valid())
        data = form.cleaned_data
        body_elements = model_to_dict(data['target'])
        self.assertEqual(model_to_dict(self.body_similar_name4), body_elements)

class TestScheduleForm(TestCase):

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

        active_prop_params = { 'code'  : 'LCO2015A-009',
                                 'title' : 'LCOGT NEO Follow-up Network',
                                 'pi'    : 'tlister@lcogt.net',
                                 'tag'   : 'LCOGT',
                                 'active': True
                               }

        inactive_prop_params = { 'code'  : 'LCO2010B-999',
                                 'title' : 'Old NEO Follow-up Proposal',
                                 'pi'    : 'tlister@lcogt.net',
                                 'tag'   : 'LCOGT',
                                 'active': False
                               }
        self.old_prop, created = Proposal.objects.get_or_create(**inactive_prop_params)
        self.prop, created = Proposal.objects.get_or_create(**active_prop_params)

    def test_form_has_fields(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('Proposal', form.as_p())
        self.assertIn('Site code:', form.as_p())

    def test_form_has_lsc_fields(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('CTIO, Chile (LSC - W85-87; Sinistro)', form.as_p())

    def test_form_has_cpt_fields(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('Sutherland, S. Africa (CPT - K91-93; Sinistro)', form.as_p())
        self.assertIn('Sutherland, S. Africa (CPT - K99; 0.4m)', form.as_p())

    def test_sched_form_has_all_sites(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('McDonald, Texas (ELP - V37; Sinistro)', form.as_p())
        self.assertIn('value="V37"', form.as_p())
        self.assertIn('Maui, Hawaii (FTN - F65)', form.as_p())
        self.assertIn('value="F65"', form.as_p())
        self.assertIn('Siding Spring, Aust. (FTS - E10)', form.as_p())
        self.assertIn('value="E10"', form.as_p())
        self.assertIn('CTIO, Chile (LSC - W85-87; Sinistro)', form.as_p())
        self.assertIn('value="W86"', form.as_p())
        self.assertIn('Sutherland, S. Africa (CPT - K91-93; Sinistro)', form.as_p())
        self.assertIn('value="K92"', form.as_p())
        self.assertIn('Siding Spring, Aust. (COJ - Q63-64; Sinistro)', form.as_p())
        self.assertIn('value="Q63"', form.as_p())
        self.assertIn('Siding Spring, Aust. (COJ - Q58-59; 0.4m)', form.as_p())
        self.assertIn('value="Q58"', form.as_p())
        self.assertIn('Tenerife, Spain (TFN - Z17,Z21; 0.4m)', form.as_p())
        self.assertIn('value="Z21"', form.as_p())
        self.assertIn('Maui, Hawaii (OGG - T03-04; 0.4m)', form.as_p())
        self.assertIn('value="T04"', form.as_p())
        self.assertIn('CTIO, Chile (LSC - W89; 0.4m)', form.as_p())
        self.assertIn('value="W89"', form.as_p())
        self.assertIn('McDonald, Texas (ELP - V99; 0.4m)', form.as_p())
        self.assertIn('value="V99"', form.as_p())
        self.assertIn('Sutherland, S. Africa (CPT - K99; 0.4m)', form.as_p())
        self.assertIn('value="K99"', form.as_p())

    def test_sched_form_hides_inactive_proposals(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('LCO2015A-009', form.as_p())
        self.assertIn('LCOGT NEO Follow-up Network', form.as_p())
        self.assertNotIn('LCO2010B-999', form.as_p())
        self.assertNotIn('Old NEO Follow-up Proposal', form.as_p())
