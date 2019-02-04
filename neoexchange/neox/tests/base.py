"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from subprocess import check_output
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from core.models import Body, Proposal, Block, SuperBlock, SpectralInfo, PreviousSpectra


class FunctionalTest(StaticLiveServerTestCase):
    def __init__(self, *args, **kwargs):
        super(FunctionalTest, self).__init__(*args, **kwargs)

        if settings.DEBUG is False:
            settings.DEBUG = True

    @contextmanager
    def wait_for_page_load(self, timeout=30):
        old_page = self.browser.find_element_by_tag_name('html')
        yield
        WebDriverWait(self.browser, timeout).until(
            staleness_of(old_page)
        )

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
                    'score'         : 90,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 17,
                    'arc_length'    : 3.123456789,
                    'not_seen'      : 0.423456789,
                    'updated'       : True,
                    }
        self.body, created = Body.objects.get_or_create(pk=1, **params)

    def insert_test_taxonomy(self):

        taxonomy_params = {'body'          : self.body,
                          'taxonomic_class' : 'Sq',
                          'tax_scheme'    :   'BD',
                          'tax_reference' : 'PDS6',
                          'tax_notes'     : 'b',
                          }
        self.test_taxonomy = SpectralInfo.objects.create(pk=1, **taxonomy_params)

        taxonomy_params2 = {'body'          : self.body,
                          'taxonomic_class' : 'T',
                          'tax_scheme'    :   'H',
                          'tax_reference' : 'PDS6',
                          'tax_notes'     : '7 | Other notes maybe.',
                          }
        self.test_taxonomy2 = SpectralInfo.objects.create(pk=2, **taxonomy_params2)

        taxonomy_params3 = {'body'          : self.body,
                          'taxonomic_class' : 'Sa',
                          'tax_scheme'    :   'T',
                          'tax_reference' : 'PDS6',
                          'tax_notes'     : '2G',
                          }
        self.test_taxonomy3 = SpectralInfo.objects.create(pk=3, **taxonomy_params3)

        taxonomy_params4 = {'body'          : self.body,
                          'taxonomic_class' : 'L',
                          'tax_scheme'    :   'B',
                          'tax_reference' : 'PDS6',
                          'tax_notes'     : 'S',
                          }
        self.test_taxonomy4 = SpectralInfo.objects.create(pk=4, **taxonomy_params4)

    def insert_previous_spectra(self):
        spectra_params = {'body'         : self.body,
                          'spec_wav'     : 'Vis+NIR',
                          'spec_vis'     : 'sp233/a265962.sp233.txt',
                          'spec_ir'      : 'sp233/a265962.sp233.txt',
                          'spec_source'  : 'S',
                          'spec_date'    : '2017-09-25',
                          }
        self.test_spectra = PreviousSpectra.objects.create(pk=1, **spectra_params)

        spectra_params2 = {'body'         : self.body,
                          'spec_wav'     : 'NIR',
                          'spec_source'  : 'M',
                          'spec_ir'     : '2014/09/1999sh10.png',
                          'spec_date'    : '2017-08-25',
                          }
        self.test_spectra2 = PreviousSpectra.objects.create(pk=2, **spectra_params2)

        spectra_params3 = {'body'         : self.body,
                          'spec_wav'     : 'Vis',
                          'spec_vis'     : 'sp233/a265962.sp233.txt',
                          'spec_source'  : 'S',
                          'spec_date'    : '2010-10-25',
                          }
        self.test_spectra3 = PreviousSpectra.objects.create(pk=3, **spectra_params3)

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

        sblock_params = {
                         'cadence' : True,
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(pk=1, **sblock_params)

        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'superblock' : self.test_sblock
                       }
        self.test_block = Block.objects.create(pk=1, **block_params)

        sblock_params = {
                         'cadence'  : False,
                         'body'     : self.body,
                         'proposal' : self.test_proposal,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-22 13:00:00',
                         'tracking_number' : '00043',
                         'active'   : False
                       }
        self.test_sblock2 = SuperBlock.objects.create(pk=2, **sblock_params)

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
                         'superblock' : self.test_sblock2,
                         'num_observed' : 1,
                         'when_observed' : '2015-04-20 03:31:42',
                         'reported' : True,
                         'when_reported' : '2015-04-20 09:29:30',
                       }
        self.test_block2 = Block.objects.create(pk=2, **block_params2)

    def setUp(self):

        fp = webdriver.FirefoxProfile()
        fp.set_preference("browser.startup.homepage", "about:blank")
        fp.set_preference("startup.homepage_welcome_url", "about:blank")
        fp.set_preference("startup.homepage_welcome_url.additional", "about:blank")

        if not hasattr(self, 'browser'):
            firefox_capabilities = DesiredCapabilities.FIREFOX
            # Marionette does not work on Firefox ~< 57. Try and determine the
            # version and check it. Hopefully this code is robust and platform-
            # independent...
            try:
                version = check_output(["firefox", "--version"], universal_newlines=True)
            except (OSError, subprocess.CalledProcessError):
                version = None
            if version and 'Firefox' in version:
                version_num = version.rstrip().split(' ')[-1]
                major_version = version_num.split('.')[0]
                if major_version.isdigit() and int(major_version) <= 52:
                    firefox_capabilities['marionette'] = False

            self.browser = webdriver.Firefox(capabilities=firefox_capabilities, firefox_profile=fp)
        self.browser.implicitly_wait(5)
        self.insert_test_body()
        self.insert_test_proposals()
        self.insert_test_blocks()
        self.insert_test_taxonomy()
        self.insert_previous_spectra()

    def tearDown(self):
        self.browser.refresh()
#       self.browser.implicitly_wait(5)
        self.browser.quit()

    def check_for_row_in_table(self, table_id, row_text):
        table = self.browser.find_element_by_id(table_id)
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertIn(row_text, [row.text.replace('\n', ' ') for row in rows])

    def check_for_row_in_table_array(self, table_id, row_text):
        table = self.browser.find_element_by_id(table_id)
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        input_row = row_text.split()
        table_rows = []
        for row in rows:
            rowline = row.text.replace('\n', ' ')
            table_rows.append(row.text.split())
        self.assertIn(input_row, table_rows)

    def check_icon_status_elements(self, table_id, data_label, statuses):
        table = self.browser.find_element_by_id(table_id)
        table_body = table.find_element_by_tag_name('tbody')
        rows = self.browser.find_elements(By.XPATH, "//td[@data-label='%s']//i" % data_label)
        row_vals = [r.get_attribute("title") for r in rows]
        self.assertEqual(row_vals, statuses)

    def check_for_row_not_in_table(self, table_id, row_text):
        table = self.browser.find_element_by_id(table_id)
        table_body = table.find_element_by_tag_name('tbody')
        rows = table_body.find_elements_by_tag_name('tr')
        self.assertNotIn(row_text, [row.text.replace('\n', ' ') for row in rows])

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
