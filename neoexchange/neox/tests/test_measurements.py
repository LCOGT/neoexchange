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
import os
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from django.urls import reverse
from core.models import Body, Frame, SourceMeasurement
from mock import patch
from neox.tests.mocks import mock_build_visibility_source


class MeasurementsPageTests(FunctionalTest):

    def insert_test_extra_test_body(self):
        params = {  'name'          : 'V38821zi',
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
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : 100,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 2,
                    'arc_length'    : 0.07,
                    'not_seen'      : 12.29,
                    'updated'       : False
                    }
        body2, status = Body.objects.get_or_create(**params)
        self.body2 = body2

    def insert_test_measurements(self, rms=False):
        frame_params = { 'sitecode' : 'K91',
                         'instrument' : 'kb70',
                         'filter' : 'w',
                         'filename' : 'cpt1m010-kb70-20150420-0042-e00.fits',
                         'exptime' : 40.0,
                         'midpoint' : '2015-04-20 18:00:00',
                         'block' : self.test_block
                        }
        if rms:
            frame_params['astrometric_catalog'] = 'UCAC-4'
            frame_params['photometric_catalog'] = 'UCAC-4'
        frame, status = Frame.objects.get_or_create(pk=1, **frame_params)
        self.test_frame = frame

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 42.1,
                           'obs_dec' : -30.05,
                           'obs_mag' : 21.05,
                           'err_obs_mag' : 0.03
                         }
        if rms:
            measure_params['err_obs_ra'] = 300e-3/3600.0
            measure_params['err_obs_dec'] = 275e-3/3600.0  
        sourcemeas, status = SourceMeasurement.objects.get_or_create(pk=1, **measure_params)
        self.test_measure1 = sourcemeas

    def insert_satellite_test_measurements(self):
        sat_frame_params = { 'sitecode' : 'C51',
                         'filter' : 'R',
                         'midpoint' : '2016-02-10 06:26:57',
                         'frametype' : Frame.SATELLITE_FRAMETYPE,
                         'extrainfo' : '     N999r0q  s2016 02 10.26872 1 - 3333.4505 - 5792.1311 - 1586.1945        C51'
                        }
        self.sat_test_frame = Frame.objects.create(pk=1, **sat_frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.sat_test_frame,
                           'obs_ra' : 229.21470833333336,
                           'obs_dec' : -10.464194444444443,
                           'astrometric_catalog' : '2MASS'
                         }
        self.test_measure1 = SourceMeasurement.objects.create(pk=1, **measure_params)
        frame_params = { 'sitecode' : 'W86',
                         'instrument' : 'fl03',
                         'filter' : 'R',
                         'filename' : 'lsc1m009-fl03-20160210-0243-e10.fits',
                         'exptime' : 95.0,
                         'midpoint' : '2016-02-11 07:41:44',
                         'block' : self.test_block
                        }
        self.test_frame = Frame.objects.create(pk=2, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 229.66829166666668,
                           'obs_dec' : -10.953888888888889,
                           'obs_mag' : 20.1,
                           'err_obs_mag' : 0.1,
                           'astrometric_catalog' : 'PPMXL'
                         }
        self.test_measure1 = SourceMeasurement.objects.create(pk=2, **measure_params)

    def insert_extra_measurements(self, rms=False):

        frame_params = { 'sitecode' : 'K91',
                         'instrument' : 'kb70',
                         'filter' : 'w',
                         'filename' : 'cpt1m010-kb70-20150421-0042-e00.fits',
                         'exptime' : 40.0,
                         'midpoint' : '2015-04-21 18:00:00',
                         'block' : self.test_block
                        }
        if rms:
            frame_params['astrometric_catalog'] = 'PPMXL'
            frame_params['photometric_catalog'] = 'PPMXL'
            frame_params['fwhm'] = 1.6
        self.test_frame = Frame.objects.create(pk=2, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 42.2,
                           'obs_dec' : -31.05,
                           'obs_mag' : 20.95,
                           'err_obs_mag' : 0.028
                         }
        if rms:
            measure_params['err_obs_ra'] = 300e-3/3600.0
            measure_params['err_obs_dec'] = 275e-3/3600.0
            measure_params['aperture_size'] = 1.56
            measure_params['snr'] = 24.8
        self.test_measure2 = SourceMeasurement.objects.create(pk=2, **measure_params)

        # These measurements are precoverys, earlier in time but discovered later
        # i.e. larger value of the primary keys

        frame_params = { 'sitecode' : 'F51',
                         'instrument' : '',
                         'filter' : 'r',
                         'filename' : '',
                         'midpoint' : '2015-03-21 06:00:00',
                         'block' : None
                        }
        if rms:
            frame_params['astrometric_catalog'] = '2MASS'
            frame_params['photometric_catalog'] = '2MASS'
        self.test_precovery_frame = Frame.objects.create(pk=3, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_precovery_frame,
                           'obs_ra' : 62.2,
                           'obs_dec' : -11.05,
                           'obs_mag' : 21.5,
                           'err_obs_mag' : 0.01
                         }
        if rms:
            measure_params['err_obs_ra'] = 90e-3/3600.0
            measure_params['err_obs_dec'] = 90e-3/3600.0
        self.test_measure3 = SourceMeasurement.objects.create(pk=3, **measure_params)

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_measurements_page(self):

        # Setup
        self.insert_test_extra_test_body()
        self.insert_test_measurements()

        # A user, Timo, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about

        # He goes to the home page and performs a search for that object
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCO NEOx', self.browser.title)
        inputbox = self.get_item_input_box("id_target_search")
        inputbox.send_keys('N999r0q')
        searchbutton = self.get_item_input_box("id_search_submit")
        searchbutton.click()

        # He is taken to a page with the search results on it.
        search_url = self.live_server_url + '/search/?q=' + \
            self.body.provisional_name
        self.assertEqual(self.browser.current_url, search_url)
        self.assertIn('Targets | LCO NEOx', self.browser.title)

        self.browser.implicitly_wait(5)
        # He sees that the target he wants is in the table and clicks on it
        self.check_for_header_in_table('id_targets',
            'Name Type Origin Ingest date')
        testlines = [u'N999r0q Candidate Minor Planet Center 11 May 2015, 17:20',
                     u'V38821zi Candidate Minor Planet Center 11 May 2015, 17:20']
        self.check_for_row_in_table('id_targets', testlines[0])
        self.check_for_row_not_in_table('id_targets', testlines[1])

        link = self.browser.find_element_by_partial_link_text('N999r0q')
        target_url = "{0}{1}".format(self.live_server_url, reverse('target', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)
        with self.wait_for_page_load(timeout=10):
            link.click()

        # He is taken to a page with the object's details on it.
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn(self.body.full_name(), header_text)

        # He sees a link that says it will show the measurements
        # available for this object.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}{1}".format(self.live_server_url, reverse('measurement', kwargs={'pk': 1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()

        self.assertIn(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        self.check_for_header_in_table('id_measurements',
            'Name Date/time RA Dec Magnitude Filter Site Code')

        # He sees that there is a table in which are the original
        # discovery observations from WISE (obs. code C51) and from
        # the LCOGT follow-up network.
        testlines = [u'N999r0q 2015 04 20.75000 02 48 24.00 -30 03 00.0 21.1 w K91',
                     u'N999r0q 2015 04 20.75000 02 48 24.00 -30 03 00.0 21.1 w K91']
        self.check_for_row_in_table('id_measurements', testlines[0])
        self.check_for_row_in_table('id_measurements', testlines[1])

        # Satisfied that the planet is safe from this asteroid, he
        # leaves.

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_measurements_mpc_format(self):

        # Setup
        self.insert_test_extra_test_body()
        self.insert_test_measurements()

        # A user, Timo, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.browser.get(target_url)

        # He sees a link that says it will export the measurements
        # available for this object in MPC 80 char format.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}/target/{1}/measurements/".format(self.live_server_url, 1)
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()

        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        # He sees a link that says it will display the measurements in MPC format
        mpc_link = self.browser.find_element_by_partial_link_text('View in MPC format')
        mpc_target_url = "{0}/target/{1}/measurements/mpc/".format(self.live_server_url, 1)
        actual_url = mpc_link.get_attribute('href')
        self.assertEqual(actual_url, mpc_target_url)

        # He clicks on the link and sees that he is taken to a page with the
        # source measurements for this object in MPC 80 char format
        mpc_link.click()

        # He sees that there is a table in which are the original
        # discovery observations from WISE (obs. code C51) and from
        # the LCOGT follow-up network.
        testlines = [u'     N999r0q  C2015 04 20.75000002 48 24.00 -30 03 00.0          21.1 R      K91',
                    ]
        pre_block = self.browser.find_element_by_tag_name('pre')
        rows = pre_block.text.splitlines()
        for test_text in testlines:
            self.assertIn(test_text, [row.replace('\n', ' ') for row in rows])

        # Satisfied that the planet is safe from this asteroid, he
        # leaves.

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_satellite_measurements_mpc_format(self):

        # Setup
        self.insert_satellite_test_measurements()

        # A user, James, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.browser.get(target_url)

        # He sees a link that says it will show the source measurements
        # available for this object.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}/target/{1}/measurements/".format(self.live_server_url, 1)
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()

        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        # He sees a link that says it will display the measurements in MPC format
        mpc_link = self.browser.find_element_by_partial_link_text('View in MPC format')
        mpc_target_url = "{0}/target/{1}/measurements/mpc/".format(self.live_server_url, 1)
        actual_url = mpc_link.get_attribute('href')
        self.assertEqual(actual_url, mpc_target_url)

        # He clicks on the link and sees that he is taken to a page with the
        # source measurements for this object in MPC 80 char format
        mpc_link.click()

        # He sees that there is a table in which are the original
        # discovery observations from WISE (obs. code C51) and from
        # the LCOGT follow-up network.
        testlines = [u'     N999r0q  S2016 02 10.26872 15 16 51.53 -10 27 51.1               RL     C51',
                     u'     N999r0q  s2016 02 10.26872 1 - 3333.4505 - 5792.1311 - 1586.1945        C51',
                     u'     N999r0q  C2016 02 11.32064815 18 40.39 -10 57 14.0          20.1 Rt     W86',
                    ]
        pre_block = self.browser.find_element_by_tag_name('pre')
        rows = pre_block.text.splitlines()
        for test_text in testlines:
            self.assertIn(test_text, [row.replace('\n', ' ') for row in rows])

        # Satisfied that the planet is safe from this asteroid, he
        # leaves.

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_precovery_measurements(self):

        self.insert_test_measurements()
        self.insert_extra_measurements()

        # A user, Marco, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.browser.get(target_url)

        # He sees a link that says it will show the source measurements
        # available for this object.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}/target/{1}/measurements/".format(self.live_server_url, 1)
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        # He has just found some precovery observations from a month earlier
        # from PanSTARRS (site code F51) and wants to see if they appear in the
        # correct time order
        testlines = [u'N999r0q 2015 03 21.25000 04 08 48.00 -11 03 00.0 21.5 r F51',
                     u'N999r0q 2015 04 20.75000 02 48 24.00 -30 03 00.0 21.1 w K91',
                     u'N999r0q 2015 04 21.75000 02 48 48.00 -31 03 00.0 21.0 w K91']

        # Can't use check_for_row_in_table as we want to check ordering
        table = self.browser.find_element_by_id('id_measurements')
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        rownum = 0
        while rownum < len(testlines):
            self.assertIn(testlines[rownum], rows[rownum].text.replace('\n', ' '))
            rownum += 1

        # Satisfied that his newly reported precovery for this asteroid has
        # been recorded, he leaves.

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_display_ADES_measurements(self):

        self.insert_test_measurements()
        self.insert_extra_measurements()

        # A user, Marco, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.browser.get(target_url)

        # He sees a link that says it will show the source measurements
        # available for this object.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}/target/{1}/measurements/".format(self.live_server_url, 1)
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        # He sees a link that says it will display the measurements in ADES format
        ades_link = self.browser.find_element_by_partial_link_text('View in ADES format')
        ades_target_url = "{0}/target/{1}/measurements/ades/".format(self.live_server_url, 1)
        actual_url = ades_link.get_attribute('href')
        self.assertEqual(actual_url, ades_target_url)

        # He clicks on the link and sees that he is taken to a page with the
        # source measurements for this object in ADES PSV format
        ades_link.click()

        # He sees that there is a table in which are the original
        # discovery observations from PanSTARRS (obs. code F51) and from
        # the LCOGT follow-up network.
        testlines = [ 'permID |provID     |trkSub  |mode|stn |obsTime                |ra         |dec        |astCat  |mag  |band|photCat |notes|remarks',
                      '       |           | N999r0q| CCD|F51 |2015-03-21T06:00:00.00Z| 62.200000 |-11.050000 |        |21.5 |   r|        |     |',
                      '       |           | N999r0q| CCD|K91 |2015-04-20T18:00:00.00Z| 42.100000 |-30.050000 |        |21.1 |   R|        |     |',
                    ]
        pre_block = self.browser.find_element_by_tag_name('pre')
        rows = pre_block.text.splitlines()
        for test_text in testlines:
            self.assertIn(test_text, [row.replace('\n', ' ') for row in rows])

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_display_ADES_measurements_withRMS(self):

        self.insert_test_measurements(rms=True)
        self.insert_extra_measurements(rms=True)

        # A user, Marco, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.browser.get(target_url)

        # He sees a link that says it will show the source measurements
        # available for this object.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}/target/{1}/measurements/".format(self.live_server_url, 1)
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        # He sees a link that says it will display the measurements in ADES format
        ades_link = self.browser.find_element_by_partial_link_text('View in ADES format')
        ades_target_url = "{0}/target/{1}/measurements/ades/".format(self.live_server_url, 1)
        actual_url = ades_link.get_attribute('href')
        self.assertEqual(actual_url, ades_target_url)

        # He clicks on the link and sees that he is taken to a page with the
        # source measurements for this object in ADES PSV format
        ades_link.click()

        # He sees that there is a table in which are the original
        # discovery observations from PanSTARRS (obs. code F51) and from
        # the LCOGT follow-up network.
        testlines = [ 'permID |provID     |trkSub  |mode|stn |obsTime                |ra         |dec        |rmsRA|rmsDec|astCat  |mag  |rmsMag|band|photCat |photAp|logSNR|seeing|notes|remarks',
                      '       |           | N999r0q| CCD|F51 |2015-03-21T06:00:00.00Z| 62.200000 |-11.050000 |0.090| 0.090|   2MASS|21.5 |0.010 |   r|   2MASS|      |      |      |     |',
                      '       |           | N999r0q| CCD|K91 |2015-04-20T18:00:00.00Z| 42.100000 |-30.050000 | 0.30|  0.28|   UCAC4|21.1 |0.030 |   R|   UCAC4|      |      |      |     |',
                      '       |           | N999r0q| CCD|K91 |2015-04-21T18:00:00.00Z| 42.200000 |-31.050000 | 0.30|  0.28|   PPMXL|20.9 |0.028 |   R|   PPMXL|  1.56|1.3945|1.6000|     |',
                    ]
        pre_block = self.browser.find_element_by_tag_name('pre')
        rows = pre_block.text.splitlines()
        for test_text in testlines:
            self.assertIn(test_text, [row.replace('\n', ' ') for row in rows])

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_download_mpc_measurements(self):

        self.insert_test_measurements()
        self.insert_extra_measurements()

        # A user, Marco, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.browser.get(target_url)

        # He sees a link that says it will show the source measurements
        # available for this object.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}/target/{1}/measurements/".format(self.live_server_url, 1)
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        # He sees a link that says it will download the measurements in MPC format
        mpc_dl_link = self.browser.find_element_by_partial_link_text('Download in MPC format')
        mpc_dl_target_url = "{0}/target/{1}/measurements/mpc/download/".format(self.live_server_url, 1)
        actual_url = mpc_dl_link.get_attribute('href')
        self.assertEqual(actual_url, mpc_dl_target_url)

        # He clicks the link and gets the file downloaded
        mpc_dl_link.click()
        dl_filepath = os.path.join(self.test_dir, self.body.current_name() + "_mpc.dat")
        self.assertTrue(os.path.exists(dl_filepath))

    @patch('core.plots.build_visibility_source', mock_build_visibility_source)
    def test_download_ades_measurements(self):

        self.insert_test_measurements(rms=True)
        self.insert_extra_measurements(rms=True)

        # A user, Marco, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target', kwargs={'pk': 1})
        self.browser.get(target_url)

        # He sees a link that says it will show the source measurements
        # available for this object.
        link = self.browser.find_element_by_id('show-measurements')
        target_url = "{0}/target/{1}/measurements/".format(self.live_server_url, 1)
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        with self.wait_for_page_load(timeout=10):
            link.click()
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements: ' + self.body.current_name(), header_text)

        # He sees a link that says it will download the measurements in ADES format
        ades_dl_link = self.browser.find_element_by_partial_link_text('Download in ADES format')
        ades_dl_target_url = "{0}/target/{1}/measurements/ades/download/".format(self.live_server_url, 1)
        actual_url = ades_dl_link.get_attribute('href')
        self.assertEqual(actual_url, ades_dl_target_url)

        # He clicks the link and gets the file downloaded
        ades_dl_link.click()
        dl_filepath = os.path.join(self.test_dir, self.body.current_name() + ".psv")
        self.assertTrue(os.path.exists(dl_filepath))

    def test_no_body_bad_measurements(self):

        self.insert_test_measurements(rms=True)
        self.insert_extra_measurements(rms=True)

        # A user, Marco the trouble maker, is typing in random object IDs for the measurement page
        target_url = self.live_server_url + reverse('measurement', kwargs={'pk': 10})
        self.browser.get(target_url)

        try:
            error_text = self.browser.find_element_by_id('site-name').text
        except NoSuchElementException:
            error_text = self.browser.find_element_by_tag_name('h1').text
        self.assertIn('Page not found', error_text)
        self.assertNotIn('Server error', error_text)
