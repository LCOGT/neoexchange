from .base import FunctionalTest
from selenium import webdriver

class BlocksValidationTest(FunctionalTest):

    def test_can_view_blocks(self):
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

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('Blocks | LCOGT NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Blocks', header_text)

        # He notices there are several blocks that are listed
        self.check_for_header_in_table('id_blocks',
            'Target Name Site Telescope Type Proposal Tracking Number Obs. Details Active?')
        testlines = [u'N999r0q CPT 1m0 LCO2015A-009 00042 5x42.0 secs Active',
                     u'N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs Not Active']
        self.check_for_row_in_table('id_blocks', testlines[0])
        self.check_for_row_in_table('id_blocks', testlines[1])

