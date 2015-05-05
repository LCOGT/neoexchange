from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from datetime import datetime
from ingest.models import Body, Proposal

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
        self.body1, created = Body.objects.get_or_create(**params1)

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
        self.body2, created = Body.objects.get_or_create(**params2)

    def insert_test_proposals(self):

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        test_proposal_params = { 'code'  : 'LCOEngineering',
                                 'title' : 'Test Proposal'
                               }
        self.test_proposal, created = Proposal.objects.get_or_create(**test_proposal_params)

    def test_can_schedule_observations(self):

        ## Insert test bodies and proposals otherwise things will fail
        self.insert_test_bodies()
        self.insert_test_proposals()

        # Sharon has heard about a new website for NEOs. She goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        self.browser.get(self.live_server_url + '/target/1/')

        # She sees a Schedule Observations button
        link = self.browser.find_element_by_link_text('Schedule Observations')
        target_url = self.live_server_url + '/schedule/?body_id=1'
        self.assertEqual(link.get_attribute('href'), target_url)

        # She clicks the link to go to the Schedule Observations page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), target_url)


        # She notices a new selection for the proposal and site code and
        # chooses the NEO Follow-up Network and ELP (V37)
        proposal_choices = Select(self.browser.find_element_by_id('id_proposal_code'))
        self.assertIn(self.neo_proposal.title, [option.text for option in proposal_choices.options])

        proposal_choices.select_by_visible_text(self.neo_proposal.title)

        site_choices = Select(self.browser.find_element_by_id('id_site_code'))
        self.assertIn('ELP (V37)', [option.text for option in site_choices.options])

        site_choices.select_by_visible_text('ELP (V37)')

        datebox = self.get_item_input_box('id_utc_date')
        datebox.clear()
        datebox.send_keys('2015-04-21')
        datebox.send_keys(Keys.ENTER)

        # The page refreshes and a series of values for magnitude, speed, slot
        # length, number and length of exposures appear
        magnitude = self.browser.find_element_by_id('id_magnitude').text
        self.assertIn('Magnitude: 20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').text
        self.assertIn("Speed: 2.52 '/min", speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').text
        self.assertIn('Slot length: 22.5 mins', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').text
        self.assertIn('No. of exp: 18', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').text
        self.assertIn('Exp length: 50.0 secs', exp_length)

        self.fail("Finish the test!")
