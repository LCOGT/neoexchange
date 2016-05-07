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
        self.assertEqual(str(new_url), target_url)

        # He sees links that will go to a more detailed block view and goes
        # to the first Block.
        link = self.browser.find_element_by_link_text('1')
        block_url = self.live_server_url + reverse('block-view',kwargs={'pk':1})
        self.assertEqual(link.get_attribute('href'), block_url)

        # He clicks the link to go to the block details page
        link.click()
        self.browser.implicitly_wait(3)
        new_url = self.browser.current_url
        self.assertEqual(str(new_url), block_url)

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
        self.assertEqual(str(cands_url), new_url)

      
