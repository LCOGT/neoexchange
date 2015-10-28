from .base import FunctionalTest
from selenium import webdriver
from django.core.urlresolvers import reverse
from core.models import Body, Record, SourceMeasurement

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
        frame_params = { 'site' : 'K91',
                         'instrument' : 'kb70',
                         'filter' : 'w',
                         'filename' : 'cpt1m010-kb70-20150420-0042-e00.fits',
                         'exp' : 40.0,
                         'whentaken' : '2015-04-20 18:00:00',
                         'block' : self.test_block
                        }
        self.test_frame = Record.objects.create(pk=1, **frame_params)

        measure_params = { 'body' : self.body,
                           'frame' : self.test_frame,
                           'obs_ra' : 42.0,
                           'obs_dec' : -30.05,
                           'obs_mag' : 21.05,
                           'err_obs_mag' : 0.03
                         }
        self.test_measure1 = SourceMeasurement.objects.create(pk=1, **measure_params)

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
            'Name Type Origin Ingested')
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
        testlines = [u'N999r0q 2015 04 20.75000 02 48 00.00 -30 03 00.0 21.1 w K91',
                     u'N999r0q 2015 04 20.75000 02 48 00.00 -30 03 00.0 21.1 w K91']
        self.check_for_row_in_table('id_measurements', testlines[0])
        self.check_for_row_in_table('id_measurements', testlines[1])

        # Satisfied that the planet is safe from this asteroid, he
        # leaves.
