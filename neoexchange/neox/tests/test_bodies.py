"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

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
from django.test import TestCase
from django.core.urlresolvers import reverse
from selenium import webdriver
from core.models import Body


class BodyDetailsTest(FunctionalTest):

    def test_can_view_body_details(self):

        # A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a link from the targets' name on the front page to a more
        # detailed view.
        link = self.browser.find_element_by_link_text('N999r0q')
        body_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.assertIn(link.get_attribute('href'), body_url)

        # She clicks the link and is taken to a page with the targets' details.
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url)

        # She notices the page title has the name of the site and the header
        # mentions the current target
        self.assertIn(self.body.current_name() + ' details | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Object: ' + self.body.current_name(), header_text)
        title_text = self.browser.find_element_by_class_name('container').text
        self.assertNotIn('Characterization Target', title_text)

        # She notices there is a table which lists a lot more details about
        # the Body.

        testlines = [u'ECCENTRICITY ' + str(self.body.eccentricity),
                     u'MEAN DISTANCE (AU) ' + str(self.body.meandist),
                     u'ABSOLUTE MAGNITUDE (H) ' + str(self.body.abs_mag)]
        for line in testlines:
            self.check_for_row_in_table('id_orbelements', line)

        # She notices there is another table which lists details about
        # the follow-up of the Body.

        testlines = [u'NEOCP DIGEST2 SCORE ' + str(self.body.score),
                     u'NUMBER OF OBSERVATIONS ' + str(self.body.num_obs),
                     u'ARC LENGTH (DAYS) ' + str(round(self.body.arc_length,2)),
                     u'TIME SINCE LAST OBSERVATION (DAYS) ' + str(round(self.body.not_seen,2))]
        for line in testlines:
            self.check_for_row_in_table('id_followup', line)

    def test_results_for_no_H(self):
        self.body.abs_mag = None
        self.body.save()
        # A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a link from the targets' name on the front page to a more
        # detailed view.
        link = self.browser.find_element_by_link_text('N999r0q')
        body_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.assertIn(link.get_attribute('href'), body_url)

        # She clicks the link and is taken to a page with the targets' details.
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url)

        # the target has no Absolute Magnitude
        testlines = [u'ABSOLUTE MAGNITUDE (H) ' + 'None',
                        ]
        for line in testlines:
            self.check_for_row_in_table('id_orbelements', line)

    def test_can_view_spectral_details(self):

        # A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a link from the targets' name on the front page to a more
        # detailed view.
        self.body.origin = 'N'     # This target is from NASA
        self.body.save()

        link = self.browser.find_element_by_link_text('N999r0q')
        body_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.assertIn(link.get_attribute('href'), body_url)

        # She clicks the link and is taken to a page with the targets' details.
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), body_url)

        # She notices the page title has the name of the site and the header
        # mentions the current target
        self.assertIn(self.body.current_name() + ' details | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Object: ' + self.body.current_name(), header_text)
        title_text = self.browser.find_element_by_class_name('container').text
        self.assertIn('Characterization Target', title_text)

        # She notices there is a section describing the object's spectral info
        testlines = ['BUS-DEMEO' + u' TAXONOMIC TYPE   ' + str(self.test_taxonomy.taxonomic_class),
                     'HOWELL' + u' TAXONOMIC TYPE   ' + str(self.test_taxonomy2.taxonomic_class),
                     'THOLEN' + u' TAXONOMIC TYPE   ' + str(self.test_taxonomy3.taxonomic_class),
                     'SMASS SPECTRA Vis+NIR'
                     ]
        for line in testlines:
            self.check_for_row_in_table('id_spectralinfo', line)

        expected_tooltip = self.browser.find_element_by_class_name("tooltiptext").get_attribute('innerHTML')
        tooltips = ['Neese, Asteroid Taxonomy V6.0, (2010).',
                    'Visible: Xu (1994), Xu et al. (1995). NIR: DeMeo et al. (2009).'
                    ]
        for tool in tooltips:
            self.assertIn(tool, expected_tooltip)
