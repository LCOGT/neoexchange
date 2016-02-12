from .base import FunctionalTest
from selenium import webdriver
from django.core.urlresolvers import reverse
from core.models import Body, Frame, SourceMeasurement

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
        self.body2 = Body.objects.create(**params)

    def insert_test_measurements(self):
        frame_params = { 'sitecode' : 'K91',
                         'instrument' : 'kb70',
                         'filter' : 'w',
                         'filename' : 'cpt1m010-kb70-20150420-0042-e00.fits',
                         'exptime' : 40.0,
                         'midpoint' : '2015-04-20 18:00:00',
                         'block' : self.test_block
                        }
        self.test_frame = Frame.objects.create(pk=1, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 42.1,
                           'obs_dec' : -30.05,
                           'obs_mag' : 21.05,
                           'err_obs_mag' : 0.03
                         }
        self.test_measure1 = SourceMeasurement.objects.create(pk=1, **measure_params)

    def insert_satellite_test_measurements(self):
        sat_frame_params = { 'sitecode' : 'C51',
                         'filter' : 'R',
                         'midpoint' : '2016-02-10 06:26:57',
                         'frametype' : Frame.SATELLITE_FRAMETYPE,
                         'extrainfo' : '     N009ags  s2016 02 10.26872 1 - 3333.4505 - 5792.1311 - 1586.1945   NEOCPC51'
                        }
        self.sat_test_frame = Frame.objects.create(pk=1, **sat_frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.sat_test_frame,
                           'obs_ra' : 229.21470833333336,
                           'obs_dec' : -10.464194444444443,
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
                           'err_obs_mag' : 0.1
                         }
        self.test_measure1 = SourceMeasurement.objects.create(pk=2, **measure_params)

    def test_measurements_page(self):

        # Setup
        self.insert_test_extra_test_body()
        self.insert_test_measurements()

        # A user, Timo, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about

        # He goes to the home page and performs a search for that object
        self.browser.get(self.live_server_url)
        self.assertIn('Home | LCOGT NEOx', self.browser.title)
        inputbox = self.get_item_input_box("id_target_search")
        inputbox.send_keys('N999r0q')
        searchbutton = self.get_item_input_box("id_search_submit")
        searchbutton.click()

        # He is taken to a page with the search results on it.
        search_url = self.live_server_url + '/search/?q=' + \
            self.body.provisional_name
        self.assertEqual(self.browser.current_url, search_url)
        self.assertIn('Targets | LCOGT NEOx', self.browser.title)

        # He sees that the target he wants is in the table and clicks on it
        self.check_for_header_in_table('id_targets',
            'Name Type Origin Ingest date')
        testlines = [u'N999r0q Candidate Minor Planet Center 11 May 2015, 17:20',
                     u'V38821zi Candidate Minor Planet Center 11 May 2015, 17:20']
        self.check_for_row_in_table('id_targets', testlines[0])
        self.check_for_row_not_in_table('id_targets', testlines[1])

        target_url = self.live_server_url + reverse('target',kwargs={'pk':1})
        link = self.browser.find_element_by_partial_link_text('N999r0q')
        self.assertEqual(link.get_attribute('href'), target_url)
        link.click()

        # He is taken to a page with the object's details on it.
        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Object: ' + self.body.current_name(), header_text)

        # He sees a link that says it will show the measurements
        # available for this object.
        link = self.browser.find_element_by_partial_link_text('Show Measurements')
        target_url = self.live_server_url + reverse('measurement',kwargs={'pk':1})
        self.assertEqual(link.get_attribute('href'), target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        link.click()

        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements for: ' + self.body.current_name(), header_text)

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

    def test_measurements_mpc_format(self):

        # Setup
        self.insert_test_extra_test_body()
        self.insert_test_measurements()

        # A user, Timo, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target',kwargs={'pk':1})
        self.browser.get(target_url)

        # He sees a link that says it will export the measurements
        # available for this object in MPC 80 char format.
        link = self.browser.find_element_by_partial_link_text('Show Measurements')
        target_url = "%s/target/%d/measurements/" % (self.live_server_url, 1)
        self.assertEqual(link.get_attribute('href'), target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        link.click()

        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements for: ' + self.body.current_name(), header_text)

        # He sees a link that says it will display the measurements in MPC format
        mpc_link = self.browser.find_element_by_partial_link_text('View in MPC format')
        mpc_target_url = "%s/target/%d/measurements/mpc/" % (self.live_server_url, 1)
        self.assertEqual(mpc_link.get_attribute('href'), mpc_target_url)
 
        # He clicks on the link and sees that he is taken to a page with the 
        # source measurements for this object in MPC 80 char format
        mpc_link.click()

        # He sees that there is a table in which are the original
        # discovery observations from WISE (obs. code C51) and from
        # the LCOGT follow-up network.
        testlines = [u'     N999r0q  C2015 04 20.75000002 48 24.00 -30 03 00.0          21.1 w      K91',
                    ]
        pre_block = self.browser.find_element_by_tag_name('pre')
        rows = pre_block.text.splitlines()
        for test_text in testlines:
            self.assertIn(test_text, [row.replace('\n', ' ') for row in rows])

        # Satisfied that the planet is safe from this asteroid, he
        # leaves.

    def test_satellite_measurements_mpc_format(self):

        # Setup
        self.insert_satellite_test_measurements()

        # A user, James, is interested in seeing what existing measurements
        # exist for a NEOCP candidate that he has heard about
        target_url = self.live_server_url + reverse('target',kwargs={'pk':1})
        self.browser.get(target_url)

        # He sees a link that says it will show the source measurements
        # available for this object.
        link = self.browser.find_element_by_partial_link_text('Show Measurements')
        target_url = "%s/target/%d/measurements/" % (self.live_server_url, 1)
        self.assertEqual(link.get_attribute('href'), target_url)

        # He clicks on the link and sees that he is taken to a page with details
        # on the source measurements for this object
        link.click()

        self.assertEqual(self.browser.current_url, target_url)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Source Measurements for: ' + self.body.current_name(), header_text)

        # He sees a link that says it will display the measurements in MPC format
        mpc_link = self.browser.find_element_by_partial_link_text('View in MPC format')
        mpc_target_url = "%s/target/%d/measurements/mpc/" % (self.live_server_url, 1)
        self.assertEqual(mpc_link.get_attribute('href'), mpc_target_url)
 
        # He clicks on the link and sees that he is taken to a page with the 
        # source measurements for this object in MPC 80 char format
        mpc_link.click()

        # He sees that there is a table in which are the original
        # discovery observations from WISE (obs. code C51) and from
        # the LCOGT follow-up network.
        testlines = [u'     N999r0q  S2016 02 10.26872 15 16 51.53 -10 27 51.1                LNEOCPC51',
                     u'     N999r0q  s2016 02 10.26872 1 - 3333.4505 - 5792.1311 - 1586.1945   NEOCPC51',
                     u'     N999r0q  C2016 02 11.32064915 18 40.39 -10 57 14.0          20.1 RtNEOCPW86',
                    ]
        pre_block = self.browser.find_element_by_tag_name('pre')
        rows = pre_block.text.splitlines()
        for test_text in testlines:
            self.assertIn(test_text, [row.replace('\n', ' ') for row in rows])

        # Satisfied that the planet is safe from this asteroid, he
        # leaves.
