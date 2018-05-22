import os
from .base import FunctionalTest
from django.core.urlresolvers import reverse
from bs4 import BeautifulSoup
#from selenium import webdriver
from astrometrics.sources_subs import fetch_flux_standards
from core.views import create_calib_sources

class CalibrationSourceListViewTest(FunctionalTest):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.flux_standards = fetch_flux_standards(test_flux_page)
        num_created = create_calib_sources(self.flux_standards)
        super(CalibrationSourceListViewTest, self).setUp()

    def test_can_view_blocks(self):
        # A new user, Daniel, goes to a hidden calibration page on the site
        target_url = "{0}{1}".format(self.live_server_url, reverse('calibsource-view'))
        self.browser.get(target_url)
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions calibrations
        self.assertIn('Calibration Sources | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Calibration Sources', header_text)

        # He notices there are several calibration sources that are listed
        self.check_for_header_in_table('id_calibsources',
            'Source # Name R.A. Dec. V Mag. Spectral Type Source Type')
        testlines = ['1 HR9087 00:01:49.42 -03:01:39.0 5.12 B7III Spectrophotometric standard',
                     '2 CD-34d241 00:41:46.92 -33:39:08.5 11.23 F Spectrophotometric standard',
                     '3 LTT2415 05:56:24.30 -27:51:28.8 12.21 None Spectrophotometric standard']
        self.check_for_row_in_table('id_calibsources', testlines[0])
        self.check_for_row_in_table('id_calibsources', testlines[1])
        self.check_for_row_in_table('id_calibsources', testlines[2])
