from .base import FunctionalTest
from django.core.urlresolvers import reverse
#from selenium import webdriver
from core.models import Block, SuperBlock

class BlocksListValidationTest(FunctionalTest):

    def test_can_view_blocks(self):
        # A new user, Timo, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('Blocks | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Blocks', header_text)

        # He notices there are several blocks that are listed
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = [u'1 N999r0q CPT 1m0 LCO2015A-009 00042 5x42.0 secs Yes Active 0 / 1 0 / 1',
                     u'2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1']
        self.check_for_row_in_table('id_blocks', testlines[0])
        self.check_for_row_in_table('id_blocks', testlines[1])

class BlockDetailValidationTest(FunctionalTest):

    def test_can_show_block_details(self):
        # A new user, Timo, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He sees links that will go to a more detailed block view and goes
        # to the first Block.
        link = self.browser.find_element_by_link_text('1')
        target_url = "{0}{1}".format(self.live_server_url, reverse('block-view',kwargs={'pk':1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the block details page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions block details
        self.assertIn('Cadence details', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Block: 1', header_text)

        # He notices there is a table which lists a lot more details about
        # the Block.

        testlines = [u'TELESCOPE CLASS ' + self.test_block.telclass,
                     u'SITE ' + self.test_block.site.upper()]
        for line in testlines:
            self.check_for_row_in_table('id_blockdetail', line)

class SuperBlockListValidationTest(FunctionalTest):

    def insert_cadence_blocks(self):
        # Insert extra blocks as part of a cadence
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-21 13:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '00044',
                         'num_exposures' : 5,
                         'exp_length' : 40.0,
                         'active'   : True,
                         'superblock' : self.test_sblock
                       }
        self.test_block = Block.objects.create(pk=3, **block_params)

    def test_can_view_superblocks_cadence(self):

        self.insert_cadence_blocks()

        # A user Foo, wishes to check on the progress of a multi-day cadence
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He sees that there are both cadence and non-cadence Blocks scheduled.
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = [u'1 N999r0q CPT 1m0 LCO2015A-009 00042 1 of 5x42.0 secs, 1 of 5x40.0 secs Yes Active 0 / 2 0 / 2',
                     u'2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1']
        self.check_for_row_in_table('id_blocks', testlines[0])
        self.check_for_row_in_table('id_blocks', testlines[1])

        # He clicks on one of the cadence block links and is taken to a page with details about the
        # individual blocks
        link = self.browser.find_element_by_link_text('1')
        target_url = "{0}{1}".format(self.live_server_url, reverse('block-view',kwargs={'pk':1}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the block details page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions cadence details
        self.assertIn('Cadence details', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Block: 1', header_text)
        kv_table_text = self.browser.find_element_by_class_name('container').text
        self.assertIn('Details of the Cadence', kv_table_text)

    def test_can_view_superblocks_noncadence(self):

        self.insert_cadence_blocks()

        # A user Foo, wishes to check on the progress of a regular block
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He sees that there are both cadence and non-cadence Blocks scheduled.
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = [u'1 N999r0q CPT 1m0 LCO2015A-009 00042 1 of 5x42.0 secs, 1 of 5x40.0 secs Yes Active 0 / 2 0 / 2',
                     u'2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1']
        self.check_for_row_in_table('id_blocks', testlines[0])
        self.check_for_row_in_table('id_blocks', testlines[1])

        # He clicks on one of the cadence block links and is taken to a page with details about the
        # individual blocks
        link = self.browser.find_element_by_link_text('2')
        target_url = "{0}{1}".format(self.live_server_url, reverse('block-view',kwargs={'pk':2}))
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link for a non-cadence block to go to the block details page
        with self.wait_for_page_load(timeout=10):
            link.click()
        new_url = self.browser.current_url
        self.assertEqual(new_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions cadence details
        self.assertIn('Block details', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Block: 2', header_text)
        kv_table_text = self.browser.find_element_by_class_name('container').text
        self.assertIn('Details of the Block', kv_table_text)

        # He sees that it was observed last night and that is has been reported to MPC
        self.assertIn('2015-04-20 03:31', kv_table_text)
        self.assertNotIn('Not Reported', kv_table_text)
        self.assertIn('2015-04-20 09:29', kv_table_text)

class SpectroBlocksListValidationTest(FunctionalTest):

    def insert_spectro_blocks(self):

        sblock_params = {
                         'cadence' : False,
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '4242',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)

        block_params = { 'telclass' : '2m0',
                         'site'     : 'ogg',
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '12345',
                         'num_exposures' : 1,
                         'exp_length' : 1800.0,
                         'active'   : True,
                         'superblock' : self.test_sblock
                       }
        self.test_block = Block.objects.create(**block_params)

    def test_can_view_blocks(self):
        self.insert_spectro_blocks()

        # A new user, Timo, comes along to the site
        self.browser.get(self.live_server_url)

        # He sees a link to 'active blocks'
        link = self.browser.find_element_by_partial_link_text('active blocks')
        target_url = "{0}{1}".format(self.live_server_url, '/block/list/')
        actual_url = link.get_attribute('href')
        self.assertEqual(actual_url, target_url)

        # He clicks the link to go to the blocks page
        with self.wait_for_page_load(timeout=20):
            link.click()
        actual_url = self.browser.current_url
        self.assertEqual(actual_url, target_url)

        # He notices the page title has the name of the site and the header
        # mentions current targets
        self.assertIn('Blocks | LCO NEOx', self.browser.title)
        header_text = self.browser.find_element_by_class_name('headingleft').text
        self.assertIn('Observing Blocks', header_text)

        # He sees that there are both spectroscopic and non-spectroscopic Blocks scheduled.
        self.check_for_header_in_table('id_blocks',
            'Block # Target Name Site Telescope Type Proposal Tracking Number Obs. Details Cadence? Active? Observed? Reported?')
        testlines = [u'1 N999r0q CPT 1m0 LCO2015A-009 00042 5x42.0 secs Yes Active 0 / 1 0 / 1',
                     u'2 N999r0q COJ 2m0 LCOEngineering 00043 7x30.0 secs No Not Active 1 / 1 1 / 1',
                     u'3 N999r0q OGG 2m0-Spec LCOEngineering 4242 1x1800.0 secs No Active 1 / 1 1 / 1']
        self.check_for_row_in_table('id_blocks', testlines[2])
