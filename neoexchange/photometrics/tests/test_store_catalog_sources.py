'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime, timedelta
from unittest import skipIf
from math import sqrt, log10, log, pow
import os
import mock
from django.test import TestCase
from django.forms.models import model_to_dict
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import Angle
import astropy.units as u
from numpy import where

from core.models import Body, Proposal, Block, CatalogSources
from test_catalog_subs import FITSUnitTest

#Import module to test
from photometrics.catalog_subs import *

class StoreCatalogSourcesTest(FITSUnitTest):

    def setUp(self):
        # Read in example FITS source catalog
        self.test_filename = os.path.abspath(os.path.join(os.environ['HOME'], 'test_mtdlink', 'elp1m008-fl05-20160225-0100-e90_cat.fits'))
        hdulist = fits.open(self.test_filename)
        self.test_header = hdulist[0].header
        self.test_table = hdulist[1].data
        hdulist.close()
        self.table_firstitem = self.test_table[0:1]
        self.table_lastitem = self.test_table[-1:]
        self.table_item_flags24 = self.test_table[2:3]
        self.table_num_flags0 = len(where(self.test_table['flags']==0)[0])

        body_params = {     'provisional_name': '2016 DX',
                            'origin': 'M',
                            'source_type': 'U',
                            'elements_type': 'MPC Minor Planet',
                            'active': False,
                            'epochofel': '2016-07-31 00:00:00',
                            'orbinc': 27.93004,
                            'longascnode': 124.91942,
                            'argofperih': 82.05117,
                            'eccentricity': 0.3916546,
                            'meandist': 2.6852071,
                            'meananom': 12.96218,
                            'perihdist': 1.6335335,
                            'abs_mag': 17.7,
                            'slope': 0.15,
                        }
        self.test_body, created = Body.objects.get_or_create(**body_params)

        proposal_params = { 'code': 'test',
                            'title': 'test',
                            'pi':'sgreenstreet@lcogt.net',
                            'tag': 'LCOGT',
                            'active': True
                          }
        self.test_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        block_params = {    'telclass': '1m0',
                            'site': 'V37',
                            'body': self.test_body,
                            'proposal': self.test_proposal,
                            'groupid': None,
                            'block_start': datetime(2016, 2, 26, 3),
                            'block_end': datetime(2016, 2, 26, 5),
                            'tracking_number': '0010',
                            'num_exposures': 6,
                            'exp_length': 125.0,
                            'num_observed': 1,
                            'when_observed': datetime(2016, 2, 26, 3, 57, 44),
                            'active': False,
                            'reported': False,
                            'when_reported':None
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)

        frame_params = {    'sitecode':'V37',
                            'instrument':'fl05',
                            'filter':'w',
                            'filename':'elp1m008-fl05-20160225-0100-e90.fits',
                            'exptime':125.0,
                            'midpoint':datetime(2016, 2, 26, 3, 58, 46, 189000),
                            'block':self.test_block,
                            'zeropoint':-99,
                            'zeropoint_err':-99,
                            'fwhm':3.246,
                            'frametype':0,
                            'rms_of_fit':None,
                            'nstars_in_fit':10.0,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

        self.test_ldacfilename = os.path.join(os.path.sep, 'tmp', 'tmp_neox_2016GS2', 'cpt1m013-kb76-20160505-0205-e11_ldac.fits')
        hdulist = fits.open(self.test_ldacfilename)
        self.test_ldactable = hdulist[2].data
        hdulist.close()

        block_params2 = {   'telclass': '1m0',
                            'site': 'K92',
                            'body': self.test_body,
                            'proposal': self.test_proposal,
                            'groupid': None,
                            'block_start': datetime(2016, 5, 5,19),
                            'block_end': datetime(2016, 5, 5, 21),
                            'tracking_number': '0009',
                            'num_exposures': 6,
                            'exp_length': 60.0,
                            'num_observed': 1,
                            'when_observed': datetime(2016, 5, 5, 20, 12, 44),
                            'active': False,
                            'reported': False,
                            'when_reported':None
                        }
        self.test_block2, created = Block.objects.get_or_create(**block_params2)

        frame_params2 = {   'sitecode':'K92',
                            'instrument':'kb76',
                            'filter':'w',
                            'filename':'cpt1m013-kb76-20160505-0205-e11.fits',
                            'exptime':60.0,
                            'midpoint':datetime(2016, 5, 5, 20, 2, 29),
                            'block':self.test_block2,
                            'zeropoint':-99,
                            'zeropoint_err':-99,
                            'fwhm':2.825,
                            'frametype':0,
                            'rms_of_fit':None,
                            'nstars_in_fit':3.0,
                        }
        self.test_frame2, created = Frame.objects.get_or_create(**frame_params2)

        body2_params = {    'provisional_name': '67P',
                            'origin': 'M',
                            'source_type': 'U',
                            'elements_type': 'MPC Comet',
                            'active': False,
                            'epochofel': '2021-11-02 00:00:00',
                            'orbinc': 3.87139,
                            'longascnode': 36.33226,
                            'argofperih': 22.13412,
                            'eccentricity': 0.6497023,
                            'meandist': 3.4559747,
                            'meananom': 359.99129,
                            'perihdist': 1.21062,
                            'epochofperih': '2021-11-02 01:21:47',
                        }
        self.test_body_2, created = Body.objects.get_or_create(**body_params)

        self.test_ldacfilename_2 = os.path.join(os.path.sep, 'tmp', 'tmp_neox_67P', 'coj1m003-kb71-20151229-0202-e91_ldac.fits')
        hdulist = fits.open(self.test_ldacfilename_2)
        self.test_header_2 = hdulist[0].header
        self.test_table_2 = hdulist[2].data
        hdulist.close()
        self.table_2_firstitem = self.test_table[0:1]
        self.table_2_lastitem = self.test_table[-1:]
        self.table_2_item_flags24 = self.test_table[2:3]
        self.table_2_num_flags0 = len(where(self.test_table['flags']==0)[0])

        block_params3 = {   'telclass': '1m0',
                            'site': 'Q64',
                            'body': self.test_body_2,
                            'proposal': self.test_proposal,
                            'groupid': None,
                            'block_start': datetime(2015, 12, 29, 16),
                            'block_end': datetime(2015, 12, 29, 19),
                            'tracking_number': '0011',
                            'num_exposures': 1,
                            'exp_length': 60.0,
                            'num_observed': 1,
                            'when_observed': datetime(2015, 12, 29, 17, 19, 00),
                            'active': False,
                            'reported': False,
                            'when_reported':None
                        }
        self.test_block3, created = Block.objects.get_or_create(**block_params3)

        frame_params3 = {   'sitecode':'W64',
                            'instrument':'kb71',
                            'filter':'rp',
                            'filename':'coj1m003-kb71-20151229-0202-e91.fits',
                            'exptime':60.0,
                            'midpoint':datetime(2015, 12, 29, 17, 19, 30),
                            'block':self.test_block3,
                            'zeropoint':-99,
                            'zeropoint_err':-99,
                            'fwhm':3.811,
                            'frametype':0,
                            'rms_of_fit':None,
                            'nstars_in_fit':3.0,
                        }
        self.test_frame3, created = Frame.objects.get_or_create(**frame_params3)

    def test1(self):

        ###
        std_zeropoint_tolerance = 0.1

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename, std_zeropoint_tolerance)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)
        self.assertEqual(num_sources_created, self.table_num_flags0)
        self.assertEqual(num_in_table, self.table_num_flags0)

        last_catsrc=CatalogSources.objects.last()

        self.assertAlmostEqual(last_catsrc.obs_x, 878.4902, 4)
        self.assertAlmostEqual(last_catsrc.obs_y, 2018.1714, 4)

    def test_zeropoint_update(self):

        std_zeropoint_tolerance = 0.1

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename, std_zeropoint_tolerance)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)

        header, table = extract_catalog(self.test_filename)

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc = call_cross_match_and_zeropoint((header, table), std_zeropoint_tolerance)

        self.assertLess(header['zeropoint'], 0.0)
        self.assertLess(header['zeropoint_err'], 0.0)

        header, table = update_zeropoint(header, table, avg_zeropoint, std_zeropoint)

        self.assertGreater(header['zeropoint'], 0.0)
        self.assertGreater(header['zeropoint_err'], 0.0)

        first_catsrc=CatalogSources.objects.first()

        self.assertGreater(first_catsrc.obs_mag, 0.0)
        self.assertAlmostEqual(first_catsrc.err_obs_mag, 0.0051, 4)

    def test_duplicate_entries(self):

        std_zeropoint_tolerance = 0.1

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename, std_zeropoint_tolerance)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)
        self.assertEqual(num_sources_created, self.table_num_flags0)
        self.assertEqual(num_in_table, self.table_num_flags0)

        num_sources_created, num_in_table = store_catalog_sources(self.test_filename, std_zeropoint_tolerance)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)
        self.assertEqual(num_sources_created, 0)
        self.assertEqual(num_in_table, self.table_num_flags0)

    def test_bad_catalog(self):

        bad_filename = os.path.join('photometrics','tests','__init__.py')

        std_zeropoint_tolerance = 0.1

        num_sources_created, num_in_table = store_catalog_sources(bad_filename, std_zeropoint_tolerance)

        self.assertEqual(CatalogSources.objects.count(), 0)
        self.assertEqual(num_sources_created, 0)
        self.assertEqual(num_in_table, 0)

    def test_ldac_catalog(self):

        std_zeropoint_tolerance = 0.1

        expected_num_sources_created = 692
        expected_num_in_table = 692
        expected_threshold = pow(10, -5.2825128/-2.5) * pow(0.467,2)
        num_sources_created, num_in_table = \
         store_catalog_sources(self.test_ldacfilename, std_zeropoint_tolerance, catalog_type='FITS_LDAC')

        self.assertEqual(expected_num_sources_created, num_sources_created)
        self.assertEqual(expected_num_in_table, num_in_table)

        last_catsrc = CatalogSources.objects.last()

        self.assertAlmostEqual(last_catsrc.flux_max, 4937.96289, 5)
        self.assertAlmostEqual(last_catsrc.threshold, expected_threshold, 5)

    def test_zeropoint_NOT_update(self):

        std_zeropoint_tolerance = 0.1

        expected_num_sources_created = 1367
        expected_num_in_table = 1367

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename_2, std_zeropoint_tolerance, catalog_type='FITS_LDAC')

        self.assertEqual(expected_num_sources_created, num_sources_created)
        self.assertEqual(expected_num_in_table, num_in_table)

        first_catsrc=CatalogSources.objects.first()
        last_catsrc=CatalogSources.objects.last()

        self.assertLess(first_catsrc.obs_mag, 0.0)
        self.assertLess(last_catsrc.obs_mag, 0.0)

    def test_zeropoint_update_no_new_frame(self):

        std_zeropoint_tolerance = 0.1

        expected_num_sources_created = 1367
        expected_num_in_table = 1367

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename_2, std_zeropoint_tolerance, catalog_type='FITS_LDAC')

        self.assertEqual(expected_num_sources_created, num_sources_created)
        self.assertEqual(expected_num_in_table, num_in_table)

        last_catsrc=CatalogSources.objects.last()

        self.assertLess(last_catsrc.obs_mag, 0.0)

        std_zeropoint_tolerance = 0.15

        expected_num_sources_created = 1367
        expected_num_in_table = 1367

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename_2, std_zeropoint_tolerance, catalog_type='FITS_LDAC')

        self.assertEqual(expected_num_sources_created, num_sources_created)
        self.assertEqual(expected_num_in_table, num_in_table)

        last_catsrc=CatalogSources.objects.last()

        self.assertGreater(last_catsrc.obs_mag, 0.0)
