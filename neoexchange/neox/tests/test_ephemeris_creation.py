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

from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from mock import patch
from neox.tests.mocks import MockDateTime, mock_build_visibility_source
# from datetime import datetime as real_datetime
from datetime import datetime
from core.models import Body


class NewVisitorTest(FunctionalTest):

    def insert_test_body(self):
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

# The homepage computes the RA, Dec of each body for 'now' so we need to mock
# patch the datetime used by models.Body.compute_position to give the same
# consistent answer.

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    @patch('core.models.body.datetime', MockDateTime)
    def test_can_compute_ephemeris(self):

        MockDateTime.change_datetime(2015, 7, 1, 17, 0, 0)
        # Eduardo has heard about a new website for NEOs. He goes to the
        # homepage
        self.browser.get(self.live_server_url)

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('Home | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_id('site-name').text
        self.assertIn('Minor planet follow-up portal', header_text)

        # He notices there are several targets that could be followed up
        self.check_for_header_in_table('id_neo_targets',
            'Rank Target Name Type R.A. Dec. Mag. Num.Obs. Arc Not Seen (days) NEOCP Score Updated?')
        # Position below computed for 2015-07-01 17:00:00
        testlines = [u'1 N999r0q Candidate 23 43 14.40 +19 59 08.2 20.7 None None None None', ]
        self.check_for_row_in_table('id_neo_targets', testlines[0])

        # he goes to the page from N999r0q and computes the ephemeris
        link = self.browser.find_element_by_link_text('N999r0q')
        with self.wait_for_page_load(timeout=10):
            link.click()

        # He decides to use the ephemeris form
        inputbox = self.get_item_input_box()

        datebox = self.get_item_input_box_and_clear('id_utc_date')
        datebox.send_keys('2015-04-21')

        site_choices = Select(self.get_item_input_box('id_site_code'))
        self.assertIn('TFN 1.0m - Z31,Z24; (Tenerife, Spain)', [option.text for option in site_choices.options])
        site_choices.select_by_visible_text('TFN 1.0m - Z31,Z24; (Tenerife, Spain)')

        # When he hits Enter, he is taken to a new page and now the page shows an ephemeris
        # for the target with a column header and a series of rows for the position
        # as a function of time.
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_submit").click()

        eduardo_ephem_url = self.browser.current_url
        self.assertRegexpMatches(eduardo_ephem_url, '/ephemeris/.+')
        menu = self.browser.find_element_by_id('extramenu').text
        self.assertIn('Ephemeris for N999r0q at Z24', menu)

        self.check_for_header_in_table('id_ephemeris_table',
            'Date/Time (UTC) RA Dec Mag "/min P.A. Alt Moon Phase Moon Dist. Moon Alt. Score H.A.'
        )
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 04 21 03:00 20 08 59.51 +29 57 16.0 20.4 2.43 89.0 +34 0.07 105 -45 +049 -04:20'
        )

        # # There is a button asking whether to schedule the target
        # link = self.browser.find_element_by_link_text('No')

        # # He clicks 'No' and is returned to the front page
        # link.click()
        # self.assertIn('NEOx home | LCOGT', self.browser.title)

        # Satisfied, he goes back to sleep

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_can_compute_ephemeris_for_specific_site(self):

        # Eduardo has heard about a new website for NEOs. He goes to the
        # homepage
        self.browser.get(self.live_server_url)

        link = self.browser.find_element_by_link_text('N999r0q')
        with self.wait_for_page_load(timeout=10):
            link.click()

        # He notices a new selection for the site code and chooses FTN (F65)
        # XXX Code smell: Too many static text constants
        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('FTN 2.0m - F65; (Maui, Hawaii ) [MuSCAT3]', [option.text for option in site_choices.options])

        # site_choices.select_by_visible_text('Maui, Hawaii (FTN - F65)')
        site_choices.select_by_value("F65")

        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')

        altlimitbox = self.get_item_input_box('id_alt_limit')
        altlimitbox.clear()
        altlimitbox.send_keys('20')

        # When he clicks submit, he is taken to a new page and now the page shows an ephemeris
        # for the target with a column header and a series of rows for the position
        # as a function of time.
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_submit").click()

        eduardo_ephem_url = self.browser.current_url
        self.assertRegexpMatches(eduardo_ephem_url, '/ephemeris/.+')
        menu = self.browser.find_element_by_id('extramenu').text
        self.assertIn('Ephemeris for N999r0q at F65', menu)

        # Check the results for V37 are not in the table
        table = self.browser.find_element_by_id('id_ephemeris_table')
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertNotIn('2015 04 21 08:45 20 10 05.99 +29 56 57.5 20.4 2.43 89.2 +33 0.09 107 -42 +047 -04:25', [row.text for row in rows])

        # Check the values are correct for F65
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 04 21 11:30 20 10 38.15 +29 56 52.1 20.4 2.45 89.0 +20 0.09 108 -47 -999 -05:09'
        )
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 04 21 11:45 20 10 40.97 +29 56 52.8 20.4 2.44 89.0 +24 0.10 108 -49 -999 -04:54'
        )

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_can_compute_ephemeris_for_specific_date(self):

        # Eduardo has heard about a new website for NEOs. He goes to the
        # homepage
        self.browser.get(self.live_server_url)

        # He is invited to enter a target to compute an ephemeris
        link = self.browser.find_element_by_link_text('N999r0q')
        with self.wait_for_page_load(timeout=10):
            link.click()

        # He notices a new selection for the site code and chooses ELP (V37)
        # XXX Code smell: Too many static text constants
        site_choices = Select(self.get_item_input_box('id_site_code'))
        self.assertIn('TFN 1.0m - Z31,Z24; (Tenerife, Spain)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('TFN 1.0m - Z31,Z24; (Tenerife, Spain)')

        # He notices a new textbox for the date that is wanted which is filled
        # in with the current date
        datebox = self.get_item_input_box('id_utc_date')
        current_date = datetime.utcnow().date()
        current_date_str = current_date.strftime('%Y-%m-%d')
        self.assertEqual(
            datebox.get_attribute('value'),
            current_date_str
        )

        # He decides to see where it will be on a specific date in a future
        # so clears the box and put his new date in
        datebox.clear()
        datebox.send_keys('2015-04-28')

        # When he clicks submit, he is taken to a new page and now the page shows an ephemeris
        # for the target with a column header and a series of rows for the position
        # as a function of time.
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_submit").click()

        eduardo_ephem_url = self.browser.current_url
        self.assertRegexpMatches(eduardo_ephem_url, '/ephemeris/.+')
        menu = self.browser.find_element_by_id('extramenu').text
        self.assertIn('Ephemeris for N999r0q at Z24', menu)

        # Check the results for default date are not in the table
        table = self.browser.find_element_by_id('id_ephemeris_table')
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertNotIn('2015 04 21 08:45 20 10 05.99 +29 56 57.5 20.4 2.43 89.2 +33 0.09 107 -42 +047 -04:25', [row.text for row in rows])

        # Check the values are correct for Z24
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 04 28 03:00 20 39 22.77 +29 37 47.1 20.6 2.14 92.6 +33 0.69 137 +00 +033 -04:22'
        )
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 04 28 05:15 20 39 44.51 +29 37 31.9 20.6 2.07 93.7 +62 0.70 137 -26 +071 -02:07'
        )

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_can_compute_ephemeris_for_specific_alt_limit(self):

        # Eduardo has heard about a new website for NEOs. He goes to the
        # homepage
        self.browser.get(self.live_server_url)

        # He is invited to enter a target to compute an ephemeris
        link = self.browser.find_element_by_link_text('N999r0q')
        self.browser.implicitly_wait(3)
        link.click()

        # He notices a new selection for the site code and chooses CPT (K91)
        # XXX Code smell: Too many static text constants
        site_choices = Select(self.get_item_input_box('id_site_code'))
        self.assertIn('CPT 1.0m - K91-93; (Sutherland, S. Africa)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('CPT 1.0m - K91-93; (Sutherland, S. Africa)')

        # He notices a new textbox for the date that is wanted which is filled
        # in with the current date
        datebox = self.get_item_input_box('id_utc_date')
        current_date = datetime.utcnow().date()
        current_date_str = current_date.strftime('%Y-%m-%d')
        self.assertEqual(
            datebox.get_attribute('value'),
            current_date_str
        )

        # He decides to see where it will be on a specific date in a future
        datebox.clear()
        datebox.send_keys('2015-09-04')

        # He notices a new textbox for the altitude limit that is wanted, below
        # which he doesn't want to see ephemeris output. It is filled in with
        # the default value of 30.0 degrees
        datebox = self.get_item_input_box('id_alt_limit')
        self.assertEqual(datebox.get_attribute('value'), str(30.0))

        # When he clicks submit, he is taken to a new page and now the page shows an ephemeris
        # for the target with a column header and a series of rows for the position
        # as a function of time.
        with self.wait_for_page_load(timeout=10):
            self.browser.find_element_by_id("id_submit").click()

        eduardo_ephem_url = self.browser.current_url
        self.assertRegexpMatches(eduardo_ephem_url, '/ephemeris/.+')
        menu = self.browser.find_element_by_id('extramenu').text
        self.assertIn('Ephemeris for N999r0q at K92', menu)

        # Check the results for default date are not in the table
        table = self.browser.find_element_by_id('id_ephemeris_table')
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')

        # Check the default settings are not present
        self.assertNotIn('2015 04 21 08:45 20 10 05.99 +29 56 57.5 20.4 2.43 89.2 +33 0.09 107 -42 +047 -04:25', [row.text for row in rows])
        # Check values before the altitude cutoff are not present
        self.assertNotIn('2015 09 03 17:30 23 53 42.39 -12 42 38.6 19.3 1.84 211.8 +4 0.68 56 -51 -999 Limits', [row.text for row in rows])

        # Check the values are correct for K92
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 09 03 19:45 23 53 33.10 -12 46 09.4 19.3 1.87 213.8 +33 0.67 58 -24 +041 -03:55'
        )
        self.check_for_row_in_table('id_ephemeris_table',
            '2015 09 04 03:30 23 52 58.62 -12 57 59.8 19.3 1.83 215.0 +33 0.64 62 +41 +019 +03:51'
        )
