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
from ingest.models import Body

#Import module to test
from ingest.forms import EphemQuery

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
        self.body = Body.objects.create(**params)
        self.body.save()

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
