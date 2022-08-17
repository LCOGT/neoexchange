"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2016-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

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

from core.models import Body, Proposal, SuperBlock, Block, CatalogSources
from .test_catalog_subs import FITSUnitTest

# Import module to test
from photometrics.catalog_subs import *


class StoreCatalogSourcesTest(FITSUnitTest):

    def setUp(self):
        # Read in example FITS source catalog
        self.test_ldacfilename = os.path.abspath(os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits'))
        hdulist = fits.open(self.test_ldacfilename)
        self.test_ldactable = hdulist[2].data
        hdulist.close()
        self.table_firstitem_ldac = self.test_ldactable[0:1]
        self.table_lastitem_ldac = self.test_ldactable[-1:]
        self.table_item_flags24_ldac = self.test_ldactable[2:3]
        self.table_flags0_ldac = self.test_ldactable[where(self.test_ldactable['flags'] == 0)]
        self.table_num_flags0_ldac = len(self.table_flags0_ldac)
        self.table_num_flags0_posve_ldac = len(where(self.table_flags0_ldac['FLUX_AUTO'] > 0.0)[0])

        body_params = {    'provisional_name': '67P',
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
        self.test_body, created = Body.objects.get_or_create(**body_params)

        proposal_params = { 'code': 'test',
                            'title': 'test',
                            'pi': 'sgreenstreet@lcogt.net',
                            'tag': 'LCOGT',
                            'active': True
                          }
        self.test_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        sblock_params = {   'cadence': False,
                            'rapid_response': False,
                            'body': self.test_body,
                            'proposal' : self.test_proposal,
                            'groupid': None,
                            'block_start': datetime(2016, 5, 5, 19),
                            'block_end': datetime(2016, 5, 5, 21),
                            'tracking_number': '0009',
                            'active': False,
                        }
        self.test_sblock, created = SuperBlock.objects.get_or_create(**sblock_params)

        block_params = {   'telclass': '1m0',
                            'site': 'K92',
                            'body': self.test_body,
                            'block_start': datetime(2016, 5, 5, 19),
                            'block_end': datetime(2016, 5, 5, 21),
                            'superblock' : self.test_sblock,
                            'request_number': '0009',
                            'num_exposures': 6,
                            'exp_length': 60.0,
                            'num_observed': 1,
                            'when_observed': datetime(2016, 5, 5, 20, 12, 44),
                            'active': False,
                            'reported': False,
                            'when_reported': None
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)

        frame_params = {   'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'ldac_test_catalog.fits',
                            'exptime': 115.0,
                            'midpoint': datetime(2016, 5, 5, 20, 2, 29),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.825,
                            'frametype': 0,
                            'rms_of_fit': None,
                            'nstars_in_fit': 3.0,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

    def test_create_catalog_sources(self):

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0_posve_ldac)
        self.assertEqual(num_sources_created, self.table_num_flags0_posve_ldac)
        self.assertEqual(num_in_table, self.table_num_flags0_posve_ldac)

        last_catsrc = CatalogSources.objects.last()

        self.assertAlmostEqual(last_catsrc.obs_x, 1758.0390, 4)
        self.assertAlmostEqual(last_catsrc.obs_y, 2024.9652, 4)

    def test_zeropoint_update(self):

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0_posve_ldac)

        header, table = extract_catalog(self.test_ldacfilename, catalog_type='FITS_LDAC')

        header, table, cat_table, cross_match_table, avg_zeropoint, std_zeropoint, count, num_in_calc, cat_name = call_cross_match_and_zeropoint((header, table), std_zeropoint_tolerance=0.1)

        self.assertLess(header['zeropoint'], 0.0)
        self.assertLess(header['zeropoint_err'], 0.0)

        header, table = update_zeropoint(header, table, avg_zeropoint, std_zeropoint)

        self.assertGreater(header['zeropoint'], 0.0)
        self.assertGreater(header['zeropoint_err'], 0.0)

        first_catsrc = CatalogSources.objects.first()

        self.assertGreater(first_catsrc.obs_mag, 0.0)
        self.assertAlmostEqual(first_catsrc.err_obs_mag, sqrt(header['zeropoint_err']**2 + 0.0034573015**2), 4)

    def test_duplicate_entries(self):

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0_posve_ldac)
        self.assertEqual(num_sources_created, self.table_num_flags0_posve_ldac)
        self.assertEqual(num_in_table, self.table_num_flags0_posve_ldac)

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0_posve_ldac)
        self.assertEqual(num_sources_created, 0)
        self.assertEqual(num_in_table, self.table_num_flags0_posve_ldac)

    def test_bad_catalog(self):

        bad_filename = os.path.join('photometrics', 'tests', '__init__.py')

        num_sources_created, num_in_table = store_catalog_sources(bad_filename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(CatalogSources.objects.count(), 0)
        self.assertEqual(num_sources_created, 0)
        self.assertEqual(num_in_table, 0)

    def test_store_catalog_sources_frame_update_no_zeropoint(self):

        frame = Frame.objects.last()
        frame.delete()

        frame_params3 = {   'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'ldac_test_catalog.fits',
                            'exptime': 115.0,
                            'midpoint': datetime(2016, 5, 5, 20, 2, 29),
                            'block': self.test_block,
                            'zeropoint': None,
                            'zeropoint_err': None,
                            'fwhm': 2.825,
                            'frametype': 0,
                            'rms_of_fit': None,
                            'nstars_in_fit': 3.0,
                        }
        self.test_frame3, created = Frame.objects.get_or_create(**frame_params3)
        zp_corr = 2.5*log10(self.test_frame3.exptime)

        expected_num_sources_created = self.table_num_flags0_posve_ldac
        expected_num_in_table = self.table_num_flags0_posve_ldac

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(expected_num_sources_created, num_sources_created)
        self.assertEqual(expected_num_in_table, num_in_table)

        last_catsrc = CatalogSources.objects.last()

        self.assertLess(last_catsrc.obs_mag, 21.62)

        last_frame = Frame.objects.last()

        self.assertAlmostEqual(last_frame.zeropoint, 28.2732-zp_corr, 4)
        self.assertAlmostEqual(last_frame.zeropoint_err, 0.0641, 4)
        self.assertEqual(last_frame.photometric_catalog, 'UCAC4')

    def test_store_catalog_sources_update_frames_zeropoint_lt0(self):

        expected_num_sources_created = self.table_num_flags0_posve_ldac
        expected_num_in_table = self.table_num_flags0_posve_ldac
        zp_corr = 2.5*log10(self.test_frame.exptime)

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(expected_num_sources_created, num_sources_created)
        self.assertEqual(expected_num_in_table, num_in_table)

        last_catsrc = CatalogSources.objects.last()

        self.assertLess(last_catsrc.obs_mag, 21.62)

        last_frame = Frame.objects.last()

        self.assertAlmostEqual(last_frame.zeropoint, 28.2732-zp_corr, 4)
        self.assertAlmostEqual(last_frame.zeropoint_err, 0.0641, 4)
        self.assertEqual(last_frame.photometric_catalog, 'UCAC4')

    def test_store_catalog_sources_update_frames_zeropoint_gt0(self):

        frame = Frame.objects.last()
        frame.delete()

        frame_params3 = {   'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'ldac_test_catalog.fits',
                            'exptime': 115.0,
                            'midpoint': datetime(2016, 5, 5, 20, 2, 29),
                            'block': self.test_block,
                            'zeropoint': 27.3926,
                            'zeropoint_err': 0.0382,
                            'fwhm': 2.825,
                            'frametype': 0,
                            'rms_of_fit': None,
                            'nstars_in_fit': 3.0,
                        }
        self.test_frame3, created = Frame.objects.get_or_create(**frame_params3)
        zp_corr = 2.5*log10(self.test_frame3.exptime)

        expected_num_sources_created = self.table_num_flags0_posve_ldac
        expected_num_in_table = self.table_num_flags0_posve_ldac

        num_sources_created, num_in_table = store_catalog_sources(self.test_ldacfilename, catalog_type='FITS_LDAC', std_zeropoint_tolerance=0.1)

        self.assertEqual(expected_num_sources_created, num_sources_created)
        self.assertEqual(expected_num_in_table, num_in_table)

        last_catsrc = CatalogSources.objects.last()

        self.assertLess(last_catsrc.obs_mag, 21.62)

        last_frame = Frame.objects.last()

        self.assertAlmostEqual(last_frame.zeropoint, 28.2732-zp_corr, 4)
        self.assertAlmostEqual(last_frame.zeropoint_err, 0.0641, 4)
        self.assertEqual(last_frame.photometric_catalog, 'UCAC4')
