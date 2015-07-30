from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from core.models import Body, Proposal, Block

class FunctionalTest(StaticLiveServerTestCase):


    def insert_test_body(self):
        params = {  'provisional_name' : 'N999r0q',
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
                    }
        self.body, created = Body.objects.get_or_create(pk=1, **params)

    def insert_test_proposals(self):

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        test_proposal_params = { 'code'  : 'LCOEngineering',
                                 'title' : 'Test Proposal'
                               }
        self.test_proposal, created = Proposal.objects.get_or_create(**test_proposal_params)

    def insert_test_blocks(self):
        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(pk=1, **block_params)

        block_params2 = { 'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block2 = Block.objects.create(pk=2, **block_params2)

    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(5)
        self.insert_test_body()
        self.insert_test_proposals()
        self.insert_test_blocks()

    def tearDown(self):
        self.browser.refresh()
#        self.browser.implicitly_wait(5)
        self.browser.quit()

    def check_for_row_in_table(self, table_id, row_text):
        table = self.browser.find_element_by_id(table_id)
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertIn(row_text, [row.text.replace('\n', ' ') for row in rows])

    def check_for_header_in_table(self, table_id, header_text):
        table = self.browser.find_element_by_id(table_id)
        table_header = table.find_element_by_tag_name('thead').text
        self.assertEqual(header_text, table_header)

    def get_item_input_box(self, element_id='id_target'):
        return self.browser.find_element_by_id(element_id)

    def get_item_input_box_and_clear(self, element_id='id_target'):
        inputbox = self.browser.find_element_by_id(element_id)
        inputbox.clear()
        return inputbox

    def wait_for_element_with_id(self, element_id):
        WebDriverWait(self.browser, timeout=10).until(
            lambda b: b.find_element_by_id(element_id),
            'Could not find element with id {}. Page text was:\n{}'.format(
                element_id, self.browser.find_element_by_tag_name('body').text
            )
        )
