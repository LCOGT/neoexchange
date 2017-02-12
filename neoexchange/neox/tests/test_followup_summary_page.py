from .base import FunctionalTest
from datetime import datetime
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.forms import model_to_dict
from selenium import webdriver
from mock import patch
from neox.tests.mocks import MockDateTime, mock_rbauth_login
from astrometrics.time_subs import get_semester_dates
from core.models import Body, Block

class FollowUpSummaryTest(FunctionalTest):

    def setUp(self):
        # Create a user to test login
        self.username = 'bart'
        self.password = 'simpson'
        self.email = 'bart@simpson.org'
        self.bart = User.objects.create_user(username=self.username, password=self.password, email=self.email)
        self.bart.first_name= 'Bart'
        self.bart.last_name = 'Simpson'
        self.bart.is_active=1
        self.bart.save()
        super(FollowUpSummaryTest,self).setUp()

        params = model_to_dict(self.body)
        del params['id']

        # 0 NEOs, 0 asts, 1 in filtered set, 2 total
        params['origin'] = 'N'
        params['provisional_name'] = 'N999r1q'
        params['source_type'] = 'N'
        new_body = Body.objects.create(**params)

        # 1 NEOs, 0 asts, 2 in filtered set, 3 total
        params['origin'] = 'M'
        params['provisional_name'] = 'N999r2q'
        new_body = Body.objects.create(**params)

        # 1 NEOs, 1 asts, 2 in filtered set, 3 total
        params['source_type'] = 'A'
        params['provisional_name'] = 'N999r3q'
        new_body = Body.objects.create(**params)

        # 1 NEOs, 2 asts, 3 in filtered set, 4 total
        params['source_type'] = 'A'
        params['provisional_name'] = 'N999r4q'
        new_body = Body.objects.create(**params)

        # 1 NEOs, 1 asts, 2 in filtered set, 5 total
        params['ingest'] = datetime(2015, 3, 30, 23, 59, 59)
        params['provisional_name'] = 'N888r0q'
        new_body = Body.objects.create(**params)

        self.summary_date = datetime(2015, 7, 17, 17, 0, 0)
        semester_start, semester_end = get_semester_dates(self.summary_date)
        self.bodies = Body.objects.filter(ingest__range=(semester_start, semester_end), origin='M')
        self.num_cands = self.bodies.count()
        self.assertEqual(4, self.num_cands)
        self.num_asts = self.bodies.filter(source_type='A').count()
        self.assertEqual(2, self.num_asts)
        self.num_neos = self.bodies.filter(source_type='N').count()
        self.assertEqual(1, self.num_neos)
        self.num_dne = self.bodies.filter(source_type='X').count()
        self.assertEqual(0, self.num_dne)

        print "Cands=", self.num_cands, self.num_asts, self.num_neos, self.num_dne

        self.blocks = Block.objects.filter(block_start__range=(semester_start, semester_end),\
            block_end__range=(semester_start, semester_end), body__origin='M')
        self.num_blocks = self.blocks.count()
        self.blocks_obs = self.blocks.filter(num_observed__gte=1)
        self.num_blocks_obs = self.blocks_obs.count()
        self.num_blocks_reported = self.blocks_obs.filter(reported=True).count()
        self.num_blocks_duplicated = self.blocks.filter(num_observed__gte=2).count()
        self.avg_lag = 12.3
        self.num_neo_blocks_obs = self.blocks_obs.filter(body__source_type='N').count()
        self.num_neo_blocks_reported = self.blocks_obs.filter(body__source_type='N', reported=True).count()
        print "Blocks=", self.num_blocks, self.num_blocks_obs, self.num_blocks_duplicated, self.num_blocks_reported

# The test proposal and blocks are for 2015A so we need to mock and wind back 
# time to have the correct semester code come out.
    @patch('core.models.datetime', MockDateTime)
    def test_can_view_followup_summary(self):

        MockDateTime.change_datetime(self.summary_date.year, self.summary_date.month,
            self.summary_date.day, self.summary_date.hour, self.summary_date.minute,
            self.summary_date.second )

        # A seasoned user comes along to the site.
        self.browser.get(self.live_server_url)

	# He sees a link to EFFICIENCY on the front page.
        link = self.browser.find_element_by_link_text('EFFICIENCY')
        url = self.live_server_url + '/block/' + 'summary/'
        self.assertEqual(link.get_attribute('href'), url)

	# He clicks the link and is taken to a page with the efficiency
        # details.
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.live_server_url + '/block/' + 'summary/'
        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        self.browser.find_element_by_xpath('//input[@value="login"]').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        self.assertEqual(str(new_url), url)

        # He notices the page title has the name of the site and the header
        # states he is on the observing block summary page.
        self.assertIn('Blocks summary | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Block Summary', header_text)

        # He notices there is a link to provide a summary of the number of bodies
        # that have been followed

        link = self.browser.find_element_by_link_text('PER SEMESTER FOLLOW-UP SUMMARY')
        url = self.live_server_url + '/followup/' + 'summary/'
        self.assertEqual(link.get_attribute('href'), url)

	# He clicks the link and is taken to a page with the follow-up
        # details.
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.live_server_url + '/followup/' + 'summary/'
        self.wait_for_element_with_id('page')
        self.assertEqual(str(new_url), url)

        # He notices the page title has the name of the site and the header
        # states he is on the followupsummary page.
        self.assertIn('Followup Summary | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Followup Summary', header_text)

        # He notices that there is a table of values for the current semester
        self.check_for_header_in_table('id_currentsemester', 'Followup for 2015A')
        
        testlines = [u'PROPOSAL '+ unicode(self.neo_proposal.title),
                     u'PROPOSAL CODE ' + unicode(self.neo_proposal.code),
                     u'NUMBER OF CANDIDATES ' + unicode(self.num_cands),
                     u'NUMBER OF ASTEROIDS ' + unicode(self.num_asts),
                     u'NUMBER OF NEOS '  + unicode(self.num_neos),
                     u'NUMBER THAT DID NOT EXIST '  + unicode(self.num_dne),
                     u'NUMBER OF BLOCKS REQUESTED ' + unicode(self.num_blocks),
                     u'NUMBER OF BLOCKS OBSERVED '  + unicode(self.num_blocks_obs),
                     u'NUMBER OF BLOCKS REPORTED '  + unicode(self.num_blocks_reported),
                     u'NUMBER OF BLOCKS DUPLICATED ' + unicode(self.num_blocks_duplicated),
                     u'AVERAGE TIME TO BLOCKS REPORTED ' + unicode(self.avg_lag) + u' hours',
                     u'NUMBER OF NEO BLOCKS OBSERVED '  + unicode(self.num_neo_blocks_obs),
                     u'NUMBER OF NEO BLOCKS REPORTED '  + unicode(self.num_neo_blocks_reported)]
        for line in testlines:
            self.check_for_row_in_table('id_currentsemester', line)
