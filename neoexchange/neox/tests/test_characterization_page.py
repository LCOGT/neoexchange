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

from django.urls import reverse
from mock import patch
from freezegun import freeze_time

from neox.tests.mocks import mock_build_visibility_source
from core.models import Body, PreviousSpectra


class CharacterizationPageTest(FunctionalTest):

    def insert_extra_test_body(self):
        params = {  'name'          : 'q382918r',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'N',
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : 85,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 35,
                    'arc_length'    : 42.0,
                    'not_seen'      : 2.22,
                    'updated'       : False
                    }
        self.body, created = Body.objects.get_or_create(pk=3, **params)

        spectra_params = {'body'         : self.body,
                          'spec_wav'     : 'NIR',
                          'spec_ir'     : 'http://smass.mit.edu/data/spex/sp17/au2002HK12.sp17.txt',
                          'spec_ref'     : 'sp[233]',
                          'spec_source'  : 'S',
                          'spec_date'    : '2017-09-25',
                          }
        self.test_spectra = PreviousSpectra.objects.create(pk=4, **spectra_params)

        spectra_params2 = {'body'         : self.body,
                          'spec_wav'     : 'NA',
                          'spec_source'  : 'M',
                          'spec_date'    : '2017-08-25',
                          }
        self.test_spectra2 = PreviousSpectra.objects.create(pk=5, **spectra_params2)

    def insert_another_extra_test_body(self):
        params = {  'name'          : 'V38821zi',
                    'abs_mag'       : 19.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'G',
                    'ingest'        : '2017-05-11 17:20:00',
                    'score'         : 100,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 2,
                    'arc_length'    : 0.07,
                    'not_seen'      : 12.29,
                    'updated'       : False
                    }
        self.body, created = Body.objects.get_or_create(pk=4, **params)

        spectra_params = {'body'         : self.body,
                          'spec_wav'     : 'NIR',
                          'spec_ir'      : 'sp234/a096631.sp234.txt',
                          'spec_source'  : 'S',
                          'spec_date'    : '2017-09-25',
                          }
        self.test_spectra = PreviousSpectra.objects.create(pk=6, **spectra_params)

        spectra_params3 = {'body'         : self.body,
                          'spec_wav'     : 'Vis',
                          'spec_vis'     : 'sp233/a265962.sp234.txt',
                          'spec_source'  : 'S',
                          'spec_date'    : '2010-10-25',
                          }
        self.test_spectra3 = PreviousSpectra.objects.create(pk=7, **spectra_params3)

    def insert_another_other_extra_test_body(self):
        params = {  'name'          : 'T123gh65',
                    'abs_mag'       : 19.0,
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
                    'origin'        : 'G',
                    'ingest'        : '2017-05-11 17:20:00',
                    'score'         : 100,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 2,
                    'arc_length'    : 0.07,
                    'not_seen'      : 12.29,
                    'updated'       : False
                    }
        self.body, created = Body.objects.get_or_create(pk=5, **params)

# The characterization page computes the RA, Dec of each body for 'now' so we need
# to freeze the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @freeze_time(datetime(2015, 7, 1, 17, 0, 0))
    def test_characterization_page(self):

        self.insert_extra_test_body()
        self.insert_another_extra_test_body()
        self.insert_another_other_extra_test_body()

        # Kildorn the Unstoppable goes to the characterization page and expects to see the list of bodies in need of Characterization.
        characterization_page_url = self.live_server_url + '/characterization/'
        self.browser.get(characterization_page_url)
        self.assertNotIn('Home | LCO NEOx', self.browser.title)
        self.assertIn('Characterization Page | LCO NEOx', self.browser.title)

        # Position below computed for 2015-07-01 17:00:00

        testlines = [u'1 V38821zi 23 43 14.40 +19 59 08.2 18.7 1.27 LC 19.0 Goldstone Vis+NIR 08/15-09/15',
                    u'2 q382918r 23 43 14.40 +19 59 08.2 20.7 1.27 Spec/LC 21.0 NASA NIR Yes [-----]']

        self.check_for_row_in_table('characterization_targets', testlines[0])
        self.check_for_row_in_table('characterization_targets', testlines[1])

        # He notices that they are ordered by window

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @freeze_time(datetime(2015, 7, 1, 17, 0, 0))
    def test_characterization_rank(self):

        self.body.origin = 'N'     # First target is from NASA
        self.body.source_type = 'N'  # First target is an NEO
        self.body.abs_mag = 15.5
        self.body.save()
        self.insert_extra_test_body()
        self.insert_another_extra_test_body()
        self.insert_another_other_extra_test_body()

        characterization_page_url = self.live_server_url + '/characterization/'
        self.browser.get(characterization_page_url)

        # Position below computed for 2015-07-01 17:00:00

        testlines = [u'2 V38821zi 23 43 14.40 +19 59 08.2 18.7 1.27 LC 19.0 Goldstone Vis+NIR 08/15-09/15',
                    u'3 q382918r 23 43 14.40 +19 59 08.2 20.7 1.27 Spec/LC 21.0 NASA NIR Yes [-----]',
                    u'1 N999r0q 23 43 14.40 +19 59 08.2 15.2 1.27 LC 15.5 NASA Vis+NIR NIR Now->']

        for line in testlines:
            self.check_for_row_in_table('characterization_targets', line)

        # Kildorn cares not for ALL Characterization targets. He wants to see only spectroscopy targets!
        button = self.browser.find_element_by_id('filter_spec')
        with self.wait_for_page_load(timeout=10):
            button.click()
        self.check_for_row_not_in_table('characterization_targets', testlines[0])
        self.check_for_row_not_in_table('characterization_targets', testlines[2])
        self.check_for_row_in_table('characterization_targets', u'1 q382918r 23 43 14.40 +19 59 08.2 20.7 1.27 Spec/LC 21.0 NASA NIR Yes [-----]')

        # Kildorn notices a link to the body page
        link = self.browser.find_element_by_link_text('q382918r')
        body_url = self.live_server_url + reverse('target', kwargs={'pk': 3})
        self.assertIn(link.get_attribute('href'), body_url)
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url)

        # He then sees that there is information from other surveys that have already gotten spectra for his targets
        testlines = ['SMASS SPECTRA NIR',
                    'MANOS TARGET (No Data Yet)',
                    ]
        for line in testlines:
            self.check_for_row_in_table('id_spectralinfo', line)

        # He sees a link for plots that piques his curiosity.
        plot_link = self.browser.find_element_by_link_text('(Plots)')
        with self.wait_for_page_load(timeout=10):
            plot_link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url+'spectra/')

        # Now knowing nothing shall impede his progress, Kildorn the Unstoppable takes a lunch break.
