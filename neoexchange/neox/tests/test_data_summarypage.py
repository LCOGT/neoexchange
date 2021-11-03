"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2021-2021 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from .base import FunctionalTest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from django.conf import settings
from datetime import datetime, date

from core.models import Block, SuperBlock, Frame, Body, PreviousSpectra, DataProduct
from core.utils import save_dataproduct, save_to_default

import os


class SummaryPageTest(FunctionalTest):
    """ The summary pages list Spectra and LC Data taken by Neoexchange.
        Are they broken? Do they do the things? Let's find out.
    """

    def setUp(self):
        super(SummaryPageTest, self).setUp()
        settings.MEDIA_ROOT = self.test_dir
        spectradir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_spectra'))

        spec_path = 'target_2df_ex.fits'
        save_to_default(os.path.join(spectradir, spec_path), spectradir)
        analog_path = 'analog_2df_ex.fits'
        save_to_default(os.path.join(spectradir, analog_path), spectradir)
        analog2_path = 'test_2df_ex.fits'
        save_to_default(os.path.join(spectradir, analog2_path), spectradir)

        # build individual target blocks
        sblock_params = {
             'cadence'         : False,
             'body'            : self.body,
             'proposal'        : self.test_proposal,
             'block_start'     : '2015-04-20 13:00:00',
             'block_end'       : '2015-04-24 03:00:00',
             'tracking_number' : '4242',
             'active'          : True
           }
        self.test_sblock = SuperBlock.objects.create(pk=3, **sblock_params)

        block_params = {
             'telclass'        : '2m0',
             'site'            : 'coj',
             'body'            : self.body,
             'superblock'      : self.test_sblock,
             'obstype'         : Block.OPT_SPECTRA,
             'block_start'     : '2019-07-27 13:00:00',
             'block_end'       : '2019-07-28 03:00:00',
             'request_number' : '1878696',
             'num_exposures'   : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 16, 42, 51)
           }
        self.test_block = Block.objects.create(pk=3, **block_params)
        save_dataproduct(self.test_block, spec_path, DataProduct.FITS_SPECTRA)

        analog_block_params = {
             'telclass'        : '2m0',
             'site'            : 'coj',
             'body'            : self.body,
             'calibsource'     : self.calib,
             'superblock'      : self.test_sblock,
             'obstype'         : Block.OPT_SPECTRA_CALIB,
             'block_start'     : '2019-07-27 13:00:00',
             'block_end'       : '2019-07-28 03:00:00',
             'request_number' : '1878697',
             'num_exposures'   : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 18, 42, 51)
           }
        self.analog_block = Block.objects.create(pk=7, **analog_block_params)
        save_dataproduct(self.analog_block, analog_path, DataProduct.FITS_SPECTRA)

        fparams = {
            'sitecode'      : 'E10',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2015-04-21 00:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.test_block,
            'frameid'       : 1,
           }
        self.spec_frame = Frame.objects.create(**fparams)

        afparams = {
            'sitecode'      : 'E10',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2015-04-21 00:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.analog_block,
            'frameid'       : 7,
           }
        self.analogspec_frame = Frame.objects.create(**afparams)

        sblock2_params = {
             'cadence'         : False,
             'body'            : self.body,
             'proposal'        : self.test_proposal,
             'block_start'     : '2015-04-20 13:00:00',
             'block_end'       : '2015-04-22 03:00:00',
             'tracking_number' : '4243',
             'active'          : False
           }
        self.test_sblock2 = SuperBlock.objects.create(pk=4, **sblock2_params)

        block2_params = {
             'telclass'        : '2m0',
             'site'            : 'ogg',
             'body'            : self.body,
             'superblock'      : self.test_sblock2,
             'obstype'         : Block.OPT_IMAGING,
             'block_start'     : '2015-04-22 13:00:00',
             'block_end'       : '2015-04-24 03:00:00',
             'request_number' : '54321',
             'num_exposures'   : 1,
             'exp_length'      : 1800.0,
             'active'          : False,
             'when_observed'   : datetime(2015, 7, 27, 16, 42, 51)
           }
        self.test_block2 = Block.objects.create(pk=4, **block2_params)

        save_dataproduct(self.test_block2, spec_path, DataProduct.FITS_SPECTRA, filename='test2_2df_ex.fits')

        analog_block2_params = {
            'telclass': '2m0',
            'site': 'coj',
            'calibsource': self.calib,
            'superblock': self.test_sblock2,
            'obstype': Block.OPT_SPECTRA_CALIB,
            'block_start': '2019-07-27 13:00:00',
            'block_end': '2019-07-28 03:00:00',
            'request_number': '54321',
            'num_exposures': 1,
            'exp_length': 1800.0,
            'active': True,
            'when_observed': datetime(2019, 7, 27, 18, 42, 51)
        }
        self.analog_block2 = Block.objects.create(pk=10, **analog_block2_params)
        save_dataproduct(self.analog_block2, analog2_path, DataProduct.FITS_SPECTRA)

        # Build multi-frame Blocks
        msblock_params = {
             'cadence'         : False,
             'body'            : self.body,
             'proposal'        : self.test_proposal,
             'block_start'     : '2018-01-01 00:00:00',
             'block_end'       : '2018-01-01 03:00:00',
             'tracking_number' : '4244',
             'active'          : True
           }
        self.test_msblock = SuperBlock.objects.create(pk=5, **msblock_params)
        mblock1_params = {
             'telclass'        : '2m0',
             'site'            : 'coj',
             'body'            : self.body,
             'superblock'      : self.test_msblock,
             'obstype'         : Block.OPT_SPECTRA,
             'block_start'     : '2018-01-01 00:00:00',
             'block_end'       : '2018-01-01 02:00:00',
             'request_number'  : '54322',
             'num_exposures'   : 2,
             'num_observed'    : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 16, 42, 51)
           }
        self.test_mblock1 = Block.objects.create(pk=5, **mblock1_params)
        save_dataproduct(self.test_mblock1, spec_path, DataProduct.FITS_SPECTRA, filename='test3_2df_ex.fits')
        save_dataproduct(self.test_mblock1, spec_path, DataProduct.FITS_SPECTRA, filename='test3.2_2df_ex.fits')

        mfparams1 = {
            'sitecode'      : 'F65',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2018-01-01 01:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.test_mblock1,
            'frameid'       : 10,
           }
        self.mspec_frame1 = Frame.objects.create(**mfparams1)
        mblock2_params = {
             'telclass'        : '2m0',
             'site'            : 'ogg',
             'body'            : self.body,
             'superblock'      : self.test_msblock,
             'obstype'         : Block.OPT_SPECTRA,
             'block_start'     : '2018-01-01 01:00:00',
             'block_end'       : '2018-01-01 03:00:00',
             'request_number' : '54323',
             'num_exposures'   : 1,
             'num_observed'    : 1,
             'exp_length'      : 1800.0,
             'active'          : True,
             'when_observed'   : datetime(2019, 7, 27, 16, 42, 51)
           }
        self.test_mblock2 = Block.objects.create(pk=6, **mblock2_params)
        save_dataproduct(self.test_mblock2, spec_path, DataProduct.FITS_SPECTRA, filename='test4_2df_ex.fits')

        mfparams2 = {
            'sitecode'      : 'F65',
            'filename'      : 'sp233/a265962.sp233.txt',
            'exptime'       : 1800.0,
            'midpoint'      : '2018-01-01 02:00:00',
            'frametype'     : Frame.SPECTRUM_FRAMETYPE,
            'block'         : self.test_mblock2,
            'frameid'       : 11,
           }
        self.mspec_frame2 = Frame.objects.create(**mfparams2)

        # make empty block
        sblock_params_empty = msblock_params
        self.test_sblock_empty = SuperBlock.objects.create(pk=6, **sblock_params_empty)
        block_params_empty = mblock2_params
        block_params_empty['superblock'] = self.test_sblock_empty
        block_params_empty['when_observed'] = datetime(2019, 9, 27, 16, 42, 51)
        self.test_block_empty = Block.objects.create(**block_params_empty)
        frame_params_empty = mfparams2
        frame_params_empty['block'] = self.test_block_empty
        self.spec_frame_empty = Frame.objects.create(**frame_params_empty)

        # Add ALCDEF Data Products
        lcname = '433_738215_ALCDEF.txt'
        lcpath = os.path.abspath(os.path.join('photometrics', 'tests'))
        save_to_default(os.path.join(lcpath, lcname), lcpath)

        save_dataproduct(self.test_sblock, lcname, DataProduct.ALCDEF_TXT)

    def test_summary_pages_exist(self):
        self.browser.get(self.live_server_url+'/summary/spec/')
        self.assertIn('Data Summary Page | LCO NEOx', self.browser.title)
        self.check_for_header_in_table('id_ranked_targets', 'Date Target Name Block Obs')
        test_lines = ['1 2019-09-27 N999r0q 6 1', '2 2019-07-27 N999r0q 5 1', '3 2019-07-27 N999r0q 5 1']
        for test_line in test_lines:
            self.check_for_row_in_table('id_ranked_targets', test_line)
        lc_link = self.browser.find_element_by_link_text('(LC)')
        with self.wait_for_page_load(timeout=10):
            lc_link.click()
        lc_lines = ['1 N999r0q']
        for lc_line in lc_lines:
            self.check_for_row_in_table('id_ranked_targets', lc_line)
