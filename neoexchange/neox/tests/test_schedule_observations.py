from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from datetime import datetime
from ingest.models import Body

class ScheduleObservations(FunctionalTest):

    def insert_test_bodies(self):
        params1 = { 'provisional_name' : 'N999r0q',
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
        self.body = Body.objects.create(**params1)
        self.body.save()

        params2 = { 'provisional_name' : 'WH2845B',
                    'abs_mag'       : 18.2,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-06-27 00:00:00',
                    'meananom'      :  25.57309,
                    'argofperih'    : 314.41870,
                    'longascnode'   : 224.52430,
                    'orbinc'        :  31.31052,
                    'eccentricity'  : 0.5356964,
                    'meandist'      : 2.6132962,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body = Body.objects.create(**params2)
        self.body.save()

    def test_can_schedule_observations(self):

        ## Insert test body otherwise things will fail
        self.insert_test_bodies()

        # Eduardo has heard about a new website for NEOs. He goes to the
        # homepage
        self.browser.get(self.live_server_url)

        # She sees a link to TARGETS
        link = self.browser.find_element_by_link_text('TARGETS')
        target_url = self.live_server_url + '/target/'
        self.assertEqual(link.get_attribute('href'), target_url)

        # She clicks the link to go to the TARGETS page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)
     
