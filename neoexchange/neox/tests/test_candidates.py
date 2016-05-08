from .base import FunctionalTest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

class TestBlockCandidates(FunctionalTest):

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
        super(TestBlockCandidates,self).setUp()

    def test_can_view_candidates(self):
        # A new user, Timo, comes along to the site
        self.browser.get(self.live_server_url)
        
        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = self.live_server_url + '/block/list/'
        self.assertEqual(link.get_attribute('href'), target_url)

        # He clicks the link to go to the blocks page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He sees links that will go to a more detailed block view and goes
        # to the first Block.
        link = self.browser.find_element_by_link_text('1')
        block_url = self.live_server_url + reverse('block-view',kwargs={'pk':1})
        self.assertEqual(link.get_attribute('href'), block_url)

        # He clicks the link to go to the block details page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(new_url, block_url)

        # He goes to the (secret for now) candidates display page
        cands_url = self.live_server_url + reverse('view-candidates',kwargs={'pk':1})
        self.browser.get(cands_url)

        username_input = self.browser.find_element_by_id("username")
        username_input.send_keys(self.username)
        password_input = self.browser.find_element_by_id("password")
        password_input.send_keys(self.password)
        self.browser.find_element_by_xpath('//input[@value="login"]').click()
        # Wait until response is recieved
        self.wait_for_element_with_id('page')
        new_url = self.browser.current_url
        self.assertEqual(cands_url, new_url)

        self.check_for_header_in_table('id_candidates',\
            'ID Score R.A. Dec. CCD X CCD Y Magnitude Speed Position Angle')
        # Position below computed for 2015-07-01 17:00:00
        testlines =[u'1 1.10 10:55:27.54 +39:16:37.2 2103.245 2043.026 19.26 1.2425 0.2',
                    u'2 2.10 10:55:41.11 +39:04:33.9 1695.444  173.967 20.01 1.2275 357.0']
        self.check_for_row_in_table('id_candidates', testlines[0])
        self.check_for_row_in_table('id_candidates', testlines[1])

      
