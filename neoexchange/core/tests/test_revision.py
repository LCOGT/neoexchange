'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2018 LCO

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
import reversion
from reversion.models import Version

from core.views import clean_NEOCP_object, save_and_make_revision
from core.models import Body

class TestReversion(TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_save_unchanging(self):

        params = {'abs_mag': 19.4,
                  'active': True,
                  'arc_length': 6.0,
                  'argofperih': 277.20606,
                  'eccentricity': 0.568069,
                  'elements_type': 'MPC_MINOR_PLANET',
                  'epochofel': datetime(2016, 9, 29, 0, 0),
                  'longascnode': 100.97138,
                  'meananom': 351.98215,
                  'meandist': 2.6763776,
                  'not_seen': None,
                  'orbinc': 8.88451,
                  'origin': 'M',
                  'slope': 0.15,
                  'source_type': 'U',
                  'update_time': datetime(2016, 10, 7, 4, 53, 50, 628012)}
        with reversion.create_revision():
            body, created = Body.objects.get_or_create(**params)

        body_count = Body.objects.count()
        self.assertEqual(1, body_count)

        versions = Version.objects.get_for_object(body)
        self.assertEqual(1, len(versions))
        # Create another revision with same params
        with reversion.create_revision():
            body, created = Body.objects.get_or_create(**params)

        body_count = Body.objects.count()
        self.assertEqual(1, body_count)
        self.assertFalse(created)

        versions = Version.objects.get_for_object(body)
        self.assertEqual(1, len(versions))

    def test_cleaner(self):
        obs_page_list = [u'N00ac38 19.4  0.15  K169T 351.98215  277.20606  100.97138    8.88451  0.5680690  0.22510389   2.6763776                 25   1    6 days 0.16         NEOCPNomin',
                         u'',
                         u'']

        first_kwargs = clean_NEOCP_object(obs_page_list)

        body, created = Body.objects.get_or_create(provisional_name='N00ac38')
        save_and_make_revision(body, first_kwargs)

        body_count = Body.objects.count()
        self.assertEqual(1, body_count)

        versions = Version.objects.get_for_object(body)
        self.assertEqual(1, len(versions))

        # Create another revision with same params
        second_kwargs = clean_NEOCP_object(obs_page_list)
        self.assertNotEqual(first_kwargs, second_kwargs)
        body = Body.objects.get(provisional_name='N00ac38')
        save_and_make_revision(body, second_kwargs)

        body_count = Body.objects.count()
        self.assertEqual(1, body_count)

        versions = Version.objects.get_for_object(body)
        self.assertEqual(1, len(versions))

    def test_cleaner_findordb(self):
        obs_page_list = [u'LSCTLGj 16.54  0.15 K16B8 258.25752   52.27105  101.57581   16.82829  0.0258753  0.17697056   3.1419699    FO 161108    11   1    3 days 0.09         NEOCPNomin 0000 LSCTLGj                     20161108',
                         u'',
                         u'']

        first_kwargs = clean_NEOCP_object(obs_page_list)

        body, created = Body.objects.get_or_create(provisional_name='LSCTLGj')
        save_and_make_revision(body, first_kwargs)

        body_count = Body.objects.count()
        self.assertEqual(1, body_count)

        versions = Version.objects.get_for_object(body)
        self.assertEqual(1, len(versions))

        # Create another revision with same params
        second_kwargs = clean_NEOCP_object(obs_page_list)
        self.assertNotEqual(first_kwargs, second_kwargs)
        body = Body.objects.get(provisional_name='LSCTLGj')
        save_and_make_revision(body, second_kwargs)

        body_count = Body.objects.count()
        self.assertEqual(1, body_count)

        versions = Version.objects.get_for_object(body)
        self.assertEqual(1, len(versions))
