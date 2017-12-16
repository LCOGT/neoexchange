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
        body_url = self.live_server_url + reverse('target',kwargs={'pk':1})
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

        # She notices there is a table which lists a lot more details about
        # the Body.

        testlines = [u'ECCENTRICITY ' + str(self.body.eccentricity),
                     u'MEAN DISTANCE (AU) ' + str(self.body.meandist),
                     u'ABSOLUTE MAGNITUDE (H) '  + str(self.body.abs_mag)]
        for line in testlines:
            self.check_for_row_in_table('id_orbelements', line)

        # She notices there is another table which lists details about
        # the follow-up of the Body.

        testlines = [u'NEOCP DIGEST2 SCORE ' + str(self.body.score),
                     u'NUMBER OF OBSERVATIONS ' + str(self.body.num_obs),
                     u'ARC LENGTH (DAYS) '  + str(self.body.arc_length)]
        for line in testlines:
            self.check_for_row_in_table('id_followup', line)

    def test_can_view_spectral_details(self):

		# A new user comes along to the site
        self.browser.get(self.live_server_url)

        # She sees a link from the targets' name on the front page to a more
        # detailed view.
        link = self.browser.find_element_by_link_text('N999r0q')
        body_url = self.live_server_url + reverse('target',kwargs={'pk':1})
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

        #She notices there is a section describing the object's spectral info
        testlines = ['BUS-DEMEO' + u' TAXONOMIC TYPE ' + str(self.test_taxonomy.taxonomic_class),
                     'HOWELL' + u' TAXONOMIC TYPE ' + str(self.test_taxonomy2.taxonomic_class),
                     'THOLEN' + u' TAXONOMIC TYPE ' + str(self.test_taxonomy3.taxonomic_class),
                     'Neese, Asteroid Taxonomy V6.0. (2010).',
                     'Visible: Xu (1994), Xu et al. (1995). NIR: DeMeo et al. (2009).',
                     '7 color indices were used. Other notes maybe.',
                     '2 color indices were used. Used groundbased radiometric albedo.',
                     'Used medium-resolution spectrum by Chapman and Gaffey (1979).'
                     ]
        for line in testlines:
            self.check_for_row_in_table('id_spectralinfo', line)
