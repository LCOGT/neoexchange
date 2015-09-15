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

from django.test import TestCase
from core.models import Body

#Import module to test
from core.forms import EphemQuery, ScheduleForm

class EphemQueryFormTest(TestCase):


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

    def test_form_has_fields(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('Proposal', form.as_p())
        self.assertIn('Site code:', form.as_p())

    def test_form_has_lsc_field(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('LSC (W85; SBIG)', form.as_p())
        self.assertIn('LSC (W86-87)', form.as_p())

    def test_sched_form_has_all_sites(self):
        form = ScheduleForm()
        self.assertIsInstance(form, ScheduleForm)
        self.assertIn('ELP (V37)', form.as_p())
        self.assertIn('value="V37"', form.as_p())
        self.assertIn('FTN (F65)', form.as_p())
        self.assertIn('value="F65"', form.as_p())
        self.assertIn('FTS (E10)', form.as_p())
        self.assertIn('value="E10"', form.as_p())
        self.assertIn('LSC (W85; SBIG)', form.as_p())
        self.assertIn('value="W85"', form.as_p())
        self.assertIn('LSC (W86-87)', form.as_p())
        self.assertIn('value="W86"', form.as_p())
        self.assertIn('CPT (K91-93)', form.as_p())
        self.assertIn('value="K92"', form.as_p())
        self.assertIn('COJ (Q63-64)', form.as_p())
        self.assertIn('value="Q63"', form.as_p())

    def test_ephem_form_has_all_sites(self):
        form = EphemQuery()
        self.assertIsInstance(form, EphemQuery)
        self.assertIn('ELP (V37)', form.as_p())
        self.assertIn('value="V37"', form.as_p())
        self.assertIn('FTN (F65)', form.as_p())
        self.assertIn('value="F65"', form.as_p())
        self.assertIn('FTS (E10)', form.as_p())
        self.assertIn('value="E10"', form.as_p())
        self.assertIn('LSC (W85; SBIG)', form.as_p())
        self.assertIn('value="W85"', form.as_p())
        self.assertIn('LSC (W86-87)', form.as_p())
        self.assertIn('value="W86"', form.as_p())
        self.assertIn('CPT (K91-93)', form.as_p())
        self.assertIn('value="K92"', form.as_p())
        self.assertIn('COJ (Q63-64)', form.as_p())
        self.assertIn('value="Q63"', form.as_p())
