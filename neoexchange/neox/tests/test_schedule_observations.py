from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from datetime import datetime
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from core.models import Body, Proposal

class ScheduleObservations(FunctionalTest):

    def setUp(self):
        # Create a user to test login
        self.bart= User.objects.create_user(username='bart', password='simpson', email='bart@simpson.org')
        self.bart.first_name= 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active=1
        self.bart.save()
        super(ScheduleObservations,self).setUp()

    def login(self):
        self.assertTrue(self.client.login(username='bart', password='simpson'))

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

    def test_can_schedule_observations(self):
        self.login()

        ## Insert test bodies and proposals otherwise things will fail
        self.insert_test_bodies()
        #self.insert_test_proposals()

        # Sharon has heard about a new website for NEOs. She goes to the
        # page of the first target
        # (XXX semi-hardwired but the targets link should be being tested in
        # test_targets_validation.TargetsValidationTest
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)

        # She sees a Schedule Observations button
        link = self.browser.find_element_by_link_text('Schedule Observations')
        target_url = self.live_server_url + reverse('schedule-body',kwargs={'pk':1})
        self.assertEqual(link.get_attribute('href'), target_url)

        # She clicks the link to go to the Schedule Observations page
        link.click()
        self.browser.implicitly_wait(10)
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
        magnitude = self.browser.find_element_by_id('id_magnitude').find_element_by_class_name('kv-value').text
        self.assertIn('20.39', magnitude)
        speed = self.browser.find_element_by_id('id_speed').find_element_by_class_name('kv-value').text
        self.assertIn("2.52 '/min", speed)
        slot_length = self.browser.find_element_by_id('id_slot_length').find_element_by_class_name('kv-value').text
        self.assertIn('22.5 mins', slot_length)
        num_exp = self.browser.find_element_by_id('id_no_of_exps').find_element_by_class_name('kv-value').text
        self.assertIn('18', num_exp)
        exp_length = self.browser.find_element_by_id('id_exp_length').find_element_by_class_name('kv-value').text
        self.assertIn('50.0 secs', exp_length)

        # At this point, a 'Schedule this object' button appears
        submit = self.browser.find_element_by_id('id_submit_button').get_attribute("value")
        self.assertIn('Schedule this Object',submit)
        self.fail("Finish the test!")

    def test_cannot_schedule_observations(self):
        # Sharon tries the same as above but forgets to login
        start_url = reverse('target',kwargs={'pk':1})
        self.browser.get(self.live_server_url + start_url)
        link = self.browser.find_element_by_link_text('Schedule Observations')
        link.click()
        self.browser.implicitly_wait(10)
        new_url = self.browser.current_url
        self.assertContains(str(new_url), 'login')
