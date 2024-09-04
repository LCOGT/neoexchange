"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
import os
import shutil
from datetime import datetime, timedelta, date
from unittest import skipIf
import tempfile
from glob import glob
from math import degrees

from django.test import TestCase, SimpleTestCase, override_settings
from django.forms.models import model_to_dict
from django.conf import settings
from django.http import Http404
from bs4 import BeautifulSoup
from mock import patch
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.table import QTable
from numpy.testing import assert_allclose

from neox.tests.mocks import MockDateTime, mock_check_request_status, mock_check_for_images, \
    mock_check_request_status_null, mock_check_request_status_notfound, \
    mock_check_for_images_no_millisecs, \
    mock_check_for_images_bad_date, mock_ingest_frames, mock_archive_frame_header, \
    mock_archive_spectra_header, \
    mock_odin_login, mock_run_sextractor_make_catalog, mock_fetch_filter_list, \
    mock_update_elements_with_findorb, mock_update_elements_with_findorb_badrms, \
    mock_update_elements_with_findorb_badepoch, mock_get_vizier_catalog_table, mock_lco_api_fail

from neox.tests.base import assertDeepAlmostEqual
from photometrics.tests.test_external_codes import ExternalCodeUnitTest

from astrometrics.ephem_subs import compute_ephem, determine_darkness_times
from astrometrics.sources_subs import parse_mpcorbit, parse_mpcobs, \
    fetch_flux_standards, read_solar_standards
from photometrics.catalog_subs import open_fits_catalog, get_catalog_header
from photometrics.gf_movie import make_gif
from core.frames import block_status, create_frame
from core.models import Body, Proposal, Block, SourceMeasurement, Frame, Candidate,\
    SuperBlock, SpectralInfo, PreviousSpectra, StaticSource
from core.forms import EphemQuery
from core.utils import save_dataproduct, save_to_default
# Import modules to test
from core.views import *
from core.plots import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)


class TestCleanNEOCPObject(TestCase):

    def test_X33656(self):
        obs_page = [u'X33656  23.9  0.15  K1548 330.99052  282.94050   31.81272   13.02458  0.7021329  0.45261672   1.6800247                  3   1    0 days 0.21         NEOCPNomin',
                    u'X33656  23.9  0.15  K1548 250.56430  257.29551   60.34849    2.58054  0.0797769  0.87078998   1.0860765                  3   1    0 days 0.20         NEOCPV0001',
                    u'X33656  23.9  0.15  K1548 256.86580  263.73491   53.18662    3.17001  0.1297341  0.88070404   1.0779106                  3   1    0 days 0.20         NEOCPV0002',
                   ]
        expected_elements = { 'abs_mag'     : 23.9,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 4, 8, 0, 0, 0),
                              'meananom'    : 330.99052,
                              'argofperih'  : 282.94050,
                              'longascnode' :  31.81272,
                              'orbinc'      :  13.02458,
                              'eccentricity':  0.7021329,
                             # 'MDM':   0.45261672,
                              'meandist'    :  1.6800247,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'orbit_rms'   : 0.21
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    def test_missing_absmag(self):
        obs_page = ['Object   H     G    Epoch    M         Peri.      Node       Incl.        e           n         a                     NObs NOpp   Arc    r.m.s.       Orbit ID',
                    'N007riz       0.15  K153J 340.52798   59.01148  160.84695   10.51732  0.3080134  0.56802014   1.4439768                  6   1    0 days 0.34         NEOCPNomin',
                    'N007riz       0.15  K153J 293.77087  123.25671  129.78437    3.76739  0.0556350  0.93124537   1.0385481                  6   1    0 days 0.57         NEOCPV0001'
                   ]

        expected_elements = { 'abs_mag'     : 99.99,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 3, 19, 0, 0, 0),
                              'meananom'    : 340.52798,
                              'argofperih'  :  59.01148,
                              'longascnode' : 160.84695,
                              'orbinc'      :  10.51732,
                              'eccentricity':  0.3080134,
                             # 'MDM':   0.56802014,
                              'meandist'    :  1.4439768,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'orbit_rms'   : 0.34
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    def test_findorb_without_replace(self):
        obs_page = [u'LSCTLFr 18.04  0.15 K158Q 359.91024    8.53879  335.41846    3.06258  0.1506159  0.29656016   2.2270374    FO 150826     3   1 10.4 min  0.08         Find_Orb   0000 LSCTLFr                     20150826',
                   ]
        expected_elements = {}
        elements = clean_NEOCP_object(obs_page)
        self.assertEqual(expected_elements, elements)

    @patch('core.views.datetime', MockDateTime)
    def test_findorb(self):

        MockDateTime.change_datetime(2015, 8, 27, 12, 0, 0)

        obs_page = [u'LSCTLFr 18.04  0.15 K158Q 359.91024    8.53879  335.41846    3.06258  0.1506159  0.29656016   2.2270374    FO 150826     3   1 10.4 min  0.08         Find_Orb   0000 LSCTLFr                     20150826',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 18.04,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 8, 26, 0, 0, 0),
                              'meananom'    : 359.91024,
                              'argofperih'  : 8.53879,
                              'longascnode' : 335.41846,
                              'orbinc'      :   3.06258,
                              'eccentricity':  0.1506159,
                              'meandist'    :  2.2270374,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'L',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 10.4/1440.0,
                              'not_seen'    : 1.5,
                              'orbit_rms'   : 0.08
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_findorb_with_perturbers(self):

        MockDateTime.change_datetime(2015, 9, 27, 6, 00, 00)

        obs_page = [u'CPTTL89 19.03  0.15 K159F 343.17326  209.67924  172.85027   25.18528  0.0920324  0.36954350   1.9232054    FO 150916    30   1    3 days 0.14 M-P 06  Find_Orb   0000 CPTTL89                     20150915',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 19.03,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 9, 15, 0, 0, 0),
                              'meananom'    : 343.17326,
                              'argofperih'  : 209.67924,
                              'longascnode' : 172.85027,
                              'orbinc'      :  25.18528,
                              'eccentricity':  0.0920324,
                              'meandist'    :  1.9232054,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'L',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 3.0,
                              'not_seen'    : 12.25,
                              'orbit_rms'   : 0.14
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_findorb_with_min_units(self):

        MockDateTime.change_datetime(2018, 3, 10, 6, 00, 00)

        obs_page = [u'ZTF00HU 32.92  0.15 K1837 199.07689  171.91365  166.14977    2.83538  0.4561885  1.73092232   0.6869909    FO 180921     8   1 87.0 min  1.21         Find_Orb   0000 ZTF00HU                     20180307',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 32.92,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2018, 3,  7, 0, 0, 0),
                              'meananom'    : 199.07689,
                              'argofperih'  : 171.91365,
                              'longascnode' : 166.14977,
                              'orbinc'      :   2.83538,
                              'eccentricity':  0.4561885,
                              'meandist'    :  0.6869909,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 87/1440.0,
                              'not_seen'    :  3.25,
                              'orbit_rms'   : 1.21
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_findorb_with_hrs_units(self):

        MockDateTime.change_datetime(2018, 3, 10, 6, 00, 00)

        obs_page = [u'ZTF00HU 32.92  0.15 K1837 199.07689  171.91365  166.14977    2.83538  0.4561885  1.73092232   0.6869909    FO 180921     8   1 87.0 hrs  1.21         Find_Orb   0000 ZTF00HU                     20180307',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 32.92,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2018, 3,  7, 0, 0, 0),
                              'meananom'    : 199.07689,
                              'argofperih'  : 171.91365,
                              'longascnode' : 166.14977,
                              'orbinc'      :   2.83538,
                              'eccentricity':  0.4561885,
                              'meandist'    :  0.6869909,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 87/24.0,
                              'not_seen'    :  3.25,
                              'orbit_rms'   : 1.21
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_findorb_with_permnumber(self):

        MockDateTime.change_datetime(2015, 9, 27, 6, 00, 00)

        obs_page = [u'h6724   19.6   0.16 K156R 349.64418    8.64714  286.27302    4.64985  0.3751307  0.47926447   1.6171584  0 MPO342195   185   3 2011-2015 0.37 M-h 3Eh Find_Orb   0000         (436724) 2011 UW158 20150629',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 19.6,
                              'slope'       : 0.16,
                              'epochofel'   : datetime(2015, 6, 27, 0, 0, 0),
                              'meananom'    : 349.64418,
                              'argofperih'  :   8.64714,
                              'longascnode' : 286.27302,
                              'orbinc'      :   4.64985,
                              'eccentricity':  0.3751307,
                              'meandist'    :  1.6171584,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'num_obs'     : 185,
                              'arc_length'  : 1826.0,
                              'not_seen'    : 90.25,
                              'orbit_rms'   : 0.37
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_findorb_with_permplusprov(self):

        MockDateTime.change_datetime(2015, 9, 27, 6, 00, 00)

        obs_page = [u'h6724K11UF8W19.55  0K157A 355.88753    8.63457  286.27078    4.65085  0.3756709  0.47863758   1.6185701    FO 180921   339   1 2011-2015 0.33         Find_Orb   0000 (436724) = 2011 UW158       20150710',
                   ]
        obs_page[0] = obs_page[0].replace('Find_Orb  ', 'NEOCPNomin')

        expected_elements = { 'abs_mag'     : 19.55,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2015, 7, 10, 0, 0, 0),
                              'meananom'    : 355.88753,
                              'argofperih'  :   8.63457,
                              'longascnode' : 286.27078,
                              'orbinc'      :   4.65085,
                              'eccentricity':  0.3756709,
                              'meandist'    :  1.6185701,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'num_obs'     : 339,
                              'arc_length'  : 1826.0,
                              'not_seen'    : 79.25,
                              'orbit_rms'   : 0.33
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_findorb_local_discovery(self):

        MockDateTime.change_datetime(2016, 11, 19, 18, 00, 00)

        obs_page_list = [u'LSCTLGj 16.54  0.15 K16B8 258.25752   52.27105  101.57581   16.82829  0.0258753  0.17697056   3.1419699    FO 161108    11   1    3 days 0.09         NEOCPNomin 0000 LSCTLGj                     20161108',
                         u'',
                         u'']

        expected_elements = { 'provisional_name' : 'LSCTLGj',
                              'abs_mag'     : 16.54,
                              'slope'       : 0.15,
                              'epochofel'   : datetime(2016, 11,  8, 0, 0, 0),
                              'meananom'    : 258.25752,
                              'argofperih'  :  52.27105,
                              'longascnode' : 101.57581,
                              'orbinc'      :  16.82829,
                              'eccentricity':  0.0258753,
                              'meandist'    :  3.1419699,
                              'elements_type': 'MPC_MINOR_PLANET',
                              'origin'      : 'L',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 3.0,
                              'not_seen'    : 11.75,
                              'orbit_rms'   : 0.09
                            }
        elements = clean_NEOCP_object(obs_page_list)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    def save_N007riz(self):
        obj_id = 'N007riz'
        elements = { 'abs_mag'     : 23.9,
                      'slope'       : 0.15,
                      'epochofel'   : datetime(2015, 3, 19, 0, 0, 0),
                      'meananom'    : 340.52798,
                      'argofperih'  :  59.01148,
                      'longascnode' : 160.84695,
                      'orbinc'      :  10.51732,
                      'eccentricity':  0.3080134,
                      'meandist'    :  1.4439768,
                      'elements_type': 'MPC_MINOR_PLANET',
                      'origin'      : 'M',
                      'source_type' : 'U',
                      'active'      : True
                    }
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
        # We are creating this object
        self.assertEqual(True, created)
        resp = save_and_make_revision(body, elements)
        # We are saving all the detailing elements
        self.assertEqual(True, resp)

    def test_revise_N007riz(self):
        self.save_N007riz()
        obj_id = 'N007riz'
        elements = { 'abs_mag'     : 23.9,
                      'slope'       : 0.15,
                      'epochofel'   : datetime(2015, 4, 19, 0, 0, 0),
                      'meananom'    : 340.52798,
                      'argofperih'  :  59.01148,
                      'longascnode' : 160.84695,
                      'orbinc'      :  10.51732,
                      'eccentricity':  0.4080134,
                      'meandist'    :  1.4439768,
                      'elements_type': 'MPC_MINOR_PLANET',
                      'origin'      : 'M',
                      'source_type' : 'U',
                      'active'      : False
                    }
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
        # Created should now be false
        self.assertEqual(False, created)
        resp = save_and_make_revision(body, elements)
        # Saving the new elements
        self.assertEqual(True, resp)

    def test_update_MPC_duplicate(self):
        self.save_N007riz()
        obj_id = 'N007riz'
        update_MPC_orbit(obj_id)

    def test_create_discovered_object(self):
        obj_id = 'LSCTLF8'
        elements = { 'abs_mag'     : 16.2,
                      'slope'       : 0.15,
                      'epochofel'   : datetime(2015, 6, 23, 0, 0, 0),
                      'meananom'    : 333.70614,
                      'argofperih'  :  40.75306,
                      'longascnode' : 287.97838,
                      'orbinc'      :  23.61657,
                      'eccentricity':  0.1186953,
                      'meandist'    :  2.7874893,
                      'elements_type': 'MPC_MINOR_PLANET',
                      'origin'      : 'L',
                      'source_type' : 'D',
                      'active'      : True
                    }
        body, created = Body.objects.get_or_create(provisional_name=obj_id)
        # We are creating this object
        self.assertEqual(True, created)
        resp = save_and_make_revision(body, elements)
        # Need to call full_clean() to validate the fields as this is not
        # done on save() (called by get_or_create() or save_and_make_revision())
        body.full_clean()
        # We are saving all the detailing elements
        self.assertEqual(True, resp)

        # Test it came from LCOGT as a discovery
        self.assertEqual('L', body.origin)
        self.assertEqual('D', body.source_type)

    @patch('core.views.datetime', MockDateTime)
    def test_should_be_comets(self):

        MockDateTime.change_datetime(2016, 8, 1, 23, 00, 00)

        obs_page = [u'P10vY9r 11.8  0.15  K167B 359.98102  162.77868  299.00048  105.84058  0.9976479  0.00002573 1136.349844                 66   1   35 days 0.42         NEOCPNomin',
                   ]

        expected_elements = { 'abs_mag'     : 11.8,
                              'slope'       : 4.0,
                              'epochofel'   : datetime(2016, 7, 11, 0, 0, 0),
                              'argofperih'  : 162.77868,
                              'longascnode' : 299.00048,
                              'orbinc'      : 105.84058,
                              'eccentricity':  0.9976479,
                              'epochofperih': datetime(2018, 7, 18, 16, 0, 8, 802657),
                              'perihdist'   : 1136.349844 * (1.0 - 0.9976479),
                              'meananom'    : None,
                              'elements_type': 'MPC_COMET',
                              'origin'      : 'M',
                              'source_type' : 'U',
                              'active'      : True,
                              'arc_length'  : 35.0,
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_should_be_comet_lowE(self):

        MockDateTime.change_datetime(2018, 9, 21, 3, 00, 00)

        obs_page = [u'0046PJ54R02013.38  0K034B  41.15662  356.39037   82.16911   11.73795  0.6578477  0.18109548   3.0940760    FO 180921   621   1 1991-2003 53.4 M-N 06  NEOCPNomin 0000 P/46                        20030411',
                   ]

        expected_elements = { 'abs_mag'     : 13.38,
                              'slope'       : 4.0,
                              'epochofel'   : datetime(2003, 4, 11, 0, 0, 0),
                              'argofperih'  : 356.39037,
                              'longascnode' :  82.16911,
                              'orbinc'      :  11.73795,
                              'eccentricity':  0.6578477,
                              'epochofperih': datetime(2002, 8, 26, 17, 38, 45, 1858),
                              'perihdist'   : 3.0940760 * (1.0 - 0.6578477),
                              'meananom'    : None,
                              'elements_type': 'MPC_COMET',
                              'origin'      : 'M',
                              'source_type' : 'C',
                              'active'      : True,
                              'num_obs'     : 621,
                              'arc_length'  : 4748,
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_should_be_comet_bad_start_year(self):

        MockDateTime.change_datetime(2018, 9, 21, 3, 00, 00)

        obs_page = [u'0046PJ54R02013.38  0K034B  41.15662  356.39037   82.16911   11.73795  0.6578477  0.18109548   3.0940760    FO 180921   621   1 cRap-2003 53.4 M-N 06  NEOCPNomin 0000 P/46                        20030411',
                   ]

        expected_elements = { 'abs_mag'     : 13.38,
                              'slope'       : 4.0,
                              'epochofel'   : datetime(2003, 4, 11, 0, 0, 0),
                              'argofperih'  : 356.39037,
                              'longascnode' :  82.16911,
                              'orbinc'      :  11.73795,
                              'eccentricity':  0.6578477,
                              'epochofperih': datetime(2002, 8, 26, 17, 38, 45, 1858),
                              'perihdist'   : 3.0940760 * (1.0 - 0.6578477),
                              'meananom'    : None,
                              'elements_type': 'MPC_COMET',
                              'origin'      : 'M',
                              'source_type' : 'C',
                              'active'      : True,
                              'num_obs'     : 621,
                              'arc_length'  : None
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])

    @patch('core.views.datetime', MockDateTime)
    def test_should_be_comet_bad_last_year(self):

        MockDateTime.change_datetime(2018, 9, 21, 3, 00, 00)

        obs_page = [u'0046PJ54R02013.38  0K034B  41.15662  356.39037   82.16911   11.73795  0.6578477  0.18109548   3.0940760    FO 180921   621   1 1991-CRAP 53.4 M-N 06  NEOCPNomin 0000 P/46                        20030411',
                   ]

        expected_elements = { 'abs_mag'     : 13.38,
                              'slope'       : 4.0,
                              'epochofel'   : datetime(2003, 4, 11, 0, 0, 0),
                              'argofperih'  : 356.39037,
                              'longascnode' :  82.16911,
                              'orbinc'      :  11.73795,
                              'eccentricity':  0.6578477,
                              'epochofperih': datetime(2002, 8, 26, 17, 38, 45, 1858),
                              'perihdist'   : 3.0940760 * (1.0 - 0.6578477),
                              'meananom'    : None,
                              'elements_type': 'MPC_COMET',
                              'origin'      : 'M',
                              'source_type' : 'C',
                              'active'      : True,
                              'num_obs'     : 621,
                              'arc_length'  : None
                            }
        elements = clean_NEOCP_object(obs_page)
        for element in expected_elements:
            self.assertEqual(expected_elements[element], elements[element])


class TestCheckForBlock(TestCase):

    def setUp(self):
        # Initialise with three test bodies a test proposal and several blocks.
        # The first body has a provisional name (e.g. a NEO candidate), the
        # other 2 do not (e.g. Goldstone targets)
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
                    }
        self.body_with_provname, created = Body.objects.get_or_create(**params)

        params['provisional_name'] = 'N999R0Q'
        self.body_with_uppername = Body.objects.create(**params)

        params['provisional_name'] = 'N999R0q'
        self.body_with_uppername2 = Body.objects.create(**params)

        params['provisional_name'] = ''
        params['name'] = '2014 UR'
        params['origin'] = 'G'
        self.body_no_provname1, created = Body.objects.get_or_create(**params)

        params['name'] = '436724'
        self.body_no_provname2, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body_with_provname,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        sblock_params2 = {
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'active'   : False,
                       }
        self.test_sblock2 = SuperBlock.objects.create(**sblock_params2)
        block_params2 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body_with_provname,
                         'superblock' : self.test_sblock2,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block2 = Block.objects.create(**block_params2)

        sblock_params3 = {
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_LSC-20150421',
                         'block_start' : '2015-04-21 23:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '00044',
                         'active'   : True,
                       }
        self.test_sblock3 = SuperBlock.objects.create(**sblock_params3)
        block_params3 = { 'telclass' : '1m0',
                         'site'     : 'LSC',
                         'body'     : self.body_with_provname,
                         'superblock' : self.test_sblock3,
                         'block_start' : '2015-04-21 23:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'request_number' : '10044',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block3 = Block.objects.create(**block_params3)

        sblock_params4 = {
                         'body'     : self.body_no_provname1,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_no_provname1.current_name() + '_LSC-20150421',
                         'block_start' : '2015-04-21 23:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'tracking_number' : '00045',
                         'active'   : True,
                       }
        self.test_sblock4 = SuperBlock.objects.create(**sblock_params4)
        block_params4 = { 'telclass' : '1m0',
                         'site'     : 'LSC',
                         'body'     : self.body_no_provname1,
                         'superblock' : self.test_sblock4,
                         'block_start' : '2015-04-21 23:00:00',
                         'block_end'   : '2015-04-22 03:00:00',
                         'request_number' : '10045',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block4 = Block.objects.create(**block_params4)

        sblock_params5 = {
                         'body'     : self.body_no_provname2,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_no_provname2.current_name() + '_ELP-20141121_lc',
                         'block_start' : '2014-11-21 03:00:00',
                         'block_end'   : '2014-11-21 13:00:00',
                         'tracking_number' : '00006',
                         'active'   : True,
                       }
        self.test_sblock5 = SuperBlock.objects.create(**sblock_params5)
        block_params5 = { 'telclass' : '1m0',
                         'site'     : 'ELP',
                         'body'     : self.body_no_provname2,
                         'superblock' : self.test_sblock5,
                         'block_start' : '2014-11-21 03:00:00',
                         'block_end'   : '2014-11-21 13:00:00',
                         'request_number' : '10006',
                         'num_exposures' : 77,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block5 = Block.objects.create(**block_params5)

        sblock_params6 = {
                         'body'     : self.body_no_provname2,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_no_provname2.current_name() + '_ELP-20141121',
                         'block_start' : '2014-11-21 03:00:00',
                         'block_end'   : '2014-11-21 13:00:00',
                         'tracking_number' : '00007',
                         'active'   : True,
                       }
        self.test_sblock6 = SuperBlock.objects.create(**sblock_params6)
        block_params6 = { 'telclass' : '1m0',
                         'site'     : 'ELP',
                         'body'     : self.body_no_provname2,
                         'superblock' : self.test_sblock6,
                         'block_start' : '2014-11-21 03:00:00',
                         'block_end'   : '2014-11-21 13:00:00',
                         'request_number' : '10007',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block6 = Block.objects.create(**block_params6)

        sblock_params7 = {
                         'body'     : self.body_with_uppername,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_uppername.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00069',
                         'active'   : False,
                       }
        self.test_sblock7 = SuperBlock.objects.create(**sblock_params7)
        block_params7 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body_with_uppername,
                         'superblock' : self.test_sblock7,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10069',
                         'num_exposures' : 5,
                         'exp_length' : 130.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        self.test_block7 = Block.objects.create(**block_params7)

    def test_db_storage(self):
        expected_body_count = 5  # Pew, pew, bang, bang...
        expected_block_count = 7
        expected_sblock_count = 7

        body_count = Body.objects.count()
        block_count = Block.objects.count()
        sblock_count = SuperBlock.objects.count()

        self.assertEqual(expected_body_count, body_count)
        self.assertEqual(expected_block_count, block_count)
        self.assertEqual(expected_sblock_count, sblock_count)

    def test_body_with_provname_no_blocks(self):

        new_body = self.body_with_provname
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_with_provname.current_name() + '_CPT-20150422'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_provname_one_block(self):

        new_body = self.body_with_provname
        params = { 'site_code' : 'W86'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_with_provname.current_name() + '_LSC-20150421'
                    }
        expected_state = 1

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_provname_two_blocks(self):

        new_body = self.body_with_provname
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_with_provname.current_name() + '_CPT-20150420'
                    }
        expected_state = 2

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname1_no_blocks(self):

        new_body = self.body_no_provname1
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_no_provname1.current_name() + '_CPT-20150422'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname1_no_blocks_sinistro(self):

        new_body = self.body_no_provname1
        params = { 'site_code' : 'K93'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_no_provname1.current_name() + '_CPT-20150422'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname1_one_block(self):

        new_body = self.body_no_provname1
        params = { 'site_code' : 'W86'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_no_provname1.current_name() + '_LSC-20150421'
                    }
        expected_state = 1

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_no_provname2_two_blocks(self):

        new_body = self.body_no_provname2
        params = { 'site_code' : 'V37'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_no_provname2.current_name() + '_ELP-20141121'
                    }
        expected_state = 2

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    def test_body_with_uppercase_name(self):
        # This passes but shouldn't as SQlite goes string checks case-insensitively whatever you do
        new_body = self.body_with_uppername2
        params = { 'site_code' : 'K92'
                 }
        form_data = { 'proposal_code' : self.neo_proposal.code,
                      'group_name' : self.body_with_uppername2.current_name() + '_CPT-20150420'
                    }
        expected_state = 0

        block_state = check_for_block(form_data, params, new_body)

        self.assertEqual(expected_state, block_state)

    # These mocks via the patch decorator for check_for_archive_images() and
    # lco_api_call() need to patch core.frames even though they are in
    # core.archive_subs otherwise they will be overridden by the
    # 'from core.archive_subs import lco_api_call' in core.frames.

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_active(self):
        resp = block_status(1)
        self.assertTrue(resp)

    @skipIf(True, "Edward needs to fix...")
    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_not_active(self):
        resp = block_status(2)
        self.assertFalse(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.views.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_check_status_change_not_enough_frames(self):
        blockid = self.test_block6.id
        resp = block_status(blockid)
        myblock = Block.objects.get(id=blockid)
        self.assertTrue(myblock.active)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.views.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_check_status_change_enough_frames(self):
        self.test_block6.num_exposures = 3
        self.test_block6.save()
        blockid = self.test_block6.id
        resp = block_status(blockid)
        myblock = Block.objects.get(id=blockid)
        self.assertTrue(myblock.active)

    @patch('core.frames.check_request_status', mock_check_request_status_null)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_block_update_check_no_obs(self):
        blockid = self.test_block6.id
        resp = block_status(blockid)
        self.assertFalse(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_check_for_images_no_millisecs)
    def test_block_update_no_millisecs(self):
        blockid = self.test_block5.id
        resp = block_status(blockid)
        self.assertTrue(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.lco_api_call', mock_check_for_images_bad_date)
    def test_block_update_bad_datestamp(self):
        blockid = self.test_block5.id
        resp = block_status(blockid)
        self.assertFalse(resp)

    @patch('core.frames.check_request_status', mock_check_request_status)
    @patch('core.frames.check_for_archive_images', mock_check_for_images)
    @patch('core.frames.ingest_frames', mock_ingest_frames)
    @patch('core.frames.lco_api_call', mock_check_for_images_no_millisecs)
    def test_block_update_check_num_observed(self):
        bid = 1
        resp = block_status(block_id=bid)
        blk = Block.objects.get(id=bid)
        self.assertEqual(blk.num_observed, 1)

    @patch('core.frames.check_request_status', mock_check_request_status_notfound)
    def test_block_not_found(self):
        bid = 1
        resp = block_status(block_id=bid)
        self.assertEqual(False, resp)


class TestRecordBlock(TestCase):

    def setUp(self):

        self.spectro_tracknum = '606083'
        self.spectro_params = {'binning': 1,
                               'block_duration': 988.0,
                               'calibs': 'both',
                               'end_time': datetime(2018, 3, 16, 18, 50),
                               'exp_count': 1,
                               'exp_time': 180.0,
                               'exp_type': 'SPECTRUM',
                               'fractional_rate': 1.0,
                               'group_name': '4_E10-20180316_spectra',
                               'instrument': '2M0-FLOYDS-SCICAM',
                               'instrument_code': 'E10-FLOYDS',
                               'observatory': '',
                               'pondtelescope': '2m0',
                               'proposal_id': 'LCO2019A-001',
                               'request_numbers': {1450339: 'NON_SIDEREAL'},
                               'request_windows': [[{'end': '2018-03-16T18:30:00',
                                                     'start': '2018-03-16T11:20:00'}]],
                               'site': 'COJ',
                               'site_code': 'E10',
                               'spectra_slit': 'slit_6.0as',
                               'spectroscopy': True,
                               'start_time': datetime(2018, 3, 16, 9, 20),
                               'user_id': 'tlister@lcogt.net'}

        self.spectro_form = { 'start_time' : self.spectro_params['start_time'],
                              'end_time' : self.spectro_params['end_time'],
                              'proposal_code' : self.spectro_params['proposal_id'],
                              'group_name' : self.spectro_params['group_name'],
                              'exp_count' : self.spectro_params['exp_count'],
                              'exp_length' : self.spectro_params['exp_time'],
                            }
        body_params = {'name' : '4'}
        self.spectro_body = Body.objects.create(**body_params)

        proposal_params = { 'code' : self.spectro_params['proposal_id'], }
        self.proposal = Proposal.objects.create(**proposal_params)
        # Create Time-Critical version of proposal
        proposal_params = { 'code' : self.spectro_params['proposal_id'] + 'b',
                            'time_critical' : True}
        self.proposal_tc = Proposal.objects.create(**proposal_params)

        self.imaging_tracknum = '576013'
        self.imaging_params = {'binning': 1,
                               'block_duration': 1068.0,
                               'end_time': datetime(2018, 3, 16, 3, 50),
                               'exp_count': 12,
                               'exp_time': 42.0,
                               'exp_type': 'EXPOSE',
                               'fractional_rate': 0.5,
                               'group_name': 'N999r0q_K91-20180316',
                               'instrument': '1M0-SCICAM-SINISTRO',
                               'observatory': '',
                               'pondtelescope': '1m0',
                               'proposal_id': 'LCO2019A-001',
                               'request_numbers': {1440123: 'NON_SIDEREAL'},
                               'request_windows': [[{'end': '2018-03-16T03:30:00.600000Z',
                                                     'start': '2018-03-15T20:20:00.400000Z'}]],
                               'site': 'CPT',
                               'site_code': 'K91',
                               'start_time': datetime(2018, 3, 15, 18, 20),
                               'user_id': 'tlister@lcogt.net'}

        self.imaging_form = { 'start_time' : self.imaging_params['start_time'],
                              'end_time' : self.imaging_params['end_time'],
                              'proposal_code' : self.imaging_params['proposal_id'],
                              'group_name' : self.imaging_params['group_name'],
                              'exp_count' : self.imaging_params['exp_count'],
                              'exp_length' : self.imaging_params['exp_time'],
                            }
        body_params = {'provisional_name' : 'N999r0q'}
        self.imaging_body = Body.objects.create(**body_params)

        ssource_params = { 'name'   : 'Landolt SA107-684',
                           'ra'     : 234.325,
                           'dec'    : -0.164,
                           'vmag'   : 8.2,
                           'source_type' : StaticSource.SOLAR_STANDARD,
                           'spectral_type' : "G2V"
                         }
        self.solar_analog = StaticSource.objects.create(**ssource_params)

    def test_spectro_block(self):
        block_resp = record_block(self.spectro_tracknum, self.spectro_params, self.spectro_form, self.spectro_body)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_SPECTRA, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.spectro_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.spectro_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 16, 11, 20, 0), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 18, 30, 0), blocks[0].block_end)
        self.assertEqual(self.spectro_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.spectro_tracknum != blocks[0].request_number)
        self.assertEqual(self.spectro_params['block_duration'], sblocks[0].timeused)
        self.assertEqual(blocks[0].tracking_rate, 100)

    def test_imaging_block(self):
        block_resp = record_block(self.imaging_tracknum, self.imaging_params, self.imaging_form, self.imaging_body)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_IMAGING, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.imaging_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.imaging_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 15, 20, 20, 0, 400000), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 3, 30, 0, 600000), blocks[0].block_end)
        self.assertEqual(self.imaging_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.imaging_tracknum != blocks[0].request_number)
        self.assertEqual(self.imaging_params['block_duration'], sblocks[0].timeused)
        self.assertEqual(False, sblocks[0].rapid_response)
        self.assertEqual(blocks[0].tracking_rate, 50)

    def test_imaging_block_notz(self):
        imaging_params = self.imaging_params.copy()
        imaging_params['request_windows'] = [[{'end': '2018-03-16T03:30:59',
                                               'start': '2018-03-15T20:20:01'}]]

        block_resp = record_block(self.imaging_tracknum, imaging_params, self.imaging_form, self.imaging_body, observer=self.bart)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, len(sblocks[0].observers))
        self.assertEqual(self.bart, sblocks[0].observers[0])

        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_IMAGING, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.imaging_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.imaging_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 15, 20, 20, 1, ), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 3, 30, 59, 0), blocks[0].block_end)
        self.assertEqual(self.imaging_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.imaging_tracknum != blocks[0].request_number)
        self.assertEqual(self.imaging_params['block_duration'], sblocks[0].timeused)
        self.assertEqual(False, sblocks[0].rapid_response)
        self.assertEqual(blocks[0].tracking_rate, 50)

    def test_imaging_block_rr_proposal(self):
        imaging_params = self.imaging_params
        imaging_params['proposal_id'] += 'b'
        imaging_form = self.imaging_form
        imaging_form['proposal_code'] += 'b'

        block_resp = record_block(self.imaging_tracknum, imaging_params, imaging_form, self.imaging_body)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_IMAGING, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.imaging_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.imaging_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 15, 20, 20, 0, 400000), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 3, 30, 0, 600000), blocks[0].block_end)
        self.assertEqual(self.imaging_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.imaging_tracknum != blocks[0].request_number)
        self.assertEqual(self.imaging_params['block_duration'], sblocks[0].timeused)
        self.assertEqual(self.proposal_tc, sblocks[0].proposal)
        self.assertEqual(True, sblocks[0].rapid_response)

    def test_spectro_and_solar_block(self):
        new_params = {'calibsource': {'id': 1,
                                      'name': 'Landolt SA107-684',
                                      'ra_deg': 234.325,
                                      'dec_deg': -0.164,
                                      'pm_ra': 0.0,
                                      'pm_dec': 0.0,
                                      'parallax': 0.0
                                      },
                      'calibsrc_exptime': 60.0,
                      'dec_deg': -0.164,
                      'ra_deg': 234.325,
                      'solar_analog': True
                      }
        spectro_params = {**new_params, **self.spectro_params}
        spectro_params['group_name'] = self.spectro_params['group_name'] + '+solstd'
        spectro_params['request_numbers'] = {1450339: 'NON_SIDEREAL'}
        spectro_params['request_windows'] = [[{'end': '2018-03-16T18:30:00', 'start': '2018-03-16T11:20:00'}]]

        block_resp = record_block(self.spectro_tracknum, spectro_params, self.spectro_form, self.spectro_body)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        solar_analogs = StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD)
        self.assertEqual(1, sblocks.count())
        self.assertEqual(2, blocks.count())
        self.assertEqual(Block.OPT_SPECTRA, blocks[0].obstype)
        self.assertEqual(Block.OPT_SPECTRA_CALIB, blocks[1].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.spectro_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.spectro_form['end_time'], sblocks[0].block_end)
        self.assertFalse(sblocks[0].cadence)
        self.assertEqual(self.spectro_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.spectro_tracknum != blocks[0].request_number)
        self.assertEqual(self.spectro_params['block_duration'], sblocks[0].timeused)

        self.assertEqual(datetime(2018, 3, 16, 11, 20, 0), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 18, 30, 0), blocks[0].block_end)
        self.assertEqual(self.spectro_body, blocks[0].body)

        self.assertEqual(solar_analogs[0], blocks[1].calibsource)
        self.assertEqual(None, blocks[1].body)
        self.assertEqual(spectro_params['calibsrc_exptime'], blocks[1].exp_length)
        self.assertEqual(blocks[0].tracking_rate, 100)
        self.assertEqual(blocks[1].tracking_rate, 0)

    def test_solo_solar_spectro_block(self):
        # adjust parameters for sidereal target
        self.spectro_params['request_numbers'] = {1450339: 'SIDEREAL'}
        self.spectro_params['group_name'] = 'Landolt SA107-684_E10-20180316_spectra'
        self.spectro_form['group_name'] = self.spectro_params['group_name']
        block_resp = record_block(self.spectro_tracknum, self.spectro_params, self.spectro_form, self.solar_analog)

        self.assertTrue(block_resp)
        sblocks = SuperBlock.objects.all()
        blocks = Block.objects.all()
        self.assertEqual(1, sblocks.count())
        self.assertEqual(1, blocks.count())
        self.assertEqual(Block.OPT_SPECTRA_CALIB, blocks[0].obstype)
        # Check the SuperBlock has the broader time window but the Block(s) have
        # the (potentially) narrower per-Request windows
        self.assertEqual(self.spectro_form['start_time'], sblocks[0].block_start)
        self.assertEqual(self.spectro_form['end_time'], sblocks[0].block_end)
        self.assertEqual(datetime(2018, 3, 16, 11, 20, 0), blocks[0].block_start)
        self.assertEqual(datetime(2018, 3, 16, 18, 30, 0), blocks[0].block_end)
        self.assertEqual(self.spectro_tracknum, sblocks[0].tracking_number)
        self.assertTrue(self.spectro_tracknum != blocks[0].request_number)
        self.assertEqual(self.spectro_params['block_duration'], sblocks[0].timeused)


class TestScheduleCheck(TestCase):

    def setUp(self):
        # Initialise with three test bodies a test proposal and several blocks.
        # The first body has a provisional name (e.g. a NEO candidate), the
        # other 2 are a comet (specified with MPC_COMET elements type) and 1 that
        # should be a comet (high eccentricity but MPC_MINOR_PLANET)
        params = {  'provisional_name' : 'LM059Y5',
                    'name'          : '2009 HA21',
                    'abs_mag'       : 20.7,
                    'slope'         : 0.15,
                    'epochofel'     : '2016-01-13 00:00:00',
                    'meananom'      : 352.95033,
                    'argofperih'    : 219.7865,
                    'longascnode'   : 205.50221,
                    'orbinc'        : 6.41173,
                    'eccentricity'  : 0.728899,
                    'meandist'      : 1.4607441,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body_mp, created = Body.objects.get_or_create(**params)

        params['elements_type'] = 'MPC_MINOR_PLANET'
        params['name'] = '2015 ER61'
        params['eccentricity'] = 0.9996344
        self.body_bad_elemtype, created = Body.objects.get_or_create(**params)

        params['elements_type'] = 'MPC_COMET'
        params['perihdist'] = 1.0540487
        params['epochofperih'] = datetime(2017, 5, 17)
        self.body_good_elemtype, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        src_params = {  'name' : 'SA42-999',
                        'ra'   : 200.0,
                        'dec'  : -15.0,
                        'vmag' : 9.0,
                        'spectral_type' : "G2V",
                        'source_type' : StaticSource.SOLAR_STANDARD
                     }
        self.solar_analog, created = StaticSource.objects.get_or_create(pk=1, **src_params)
        self.maxDiff = None

        self.expected_resp = {
                            'target_name': self.body_mp.current_name(),
                            'magnitude': 19.09694937750832,
                            'speed': 2.904310588055287,
                            'slot_length': 20.0,
                            'filter_pattern': 'w',
                            'pattern_iterations': 10.0,
                            'available_filters': 'air, ND, U, B, V, R, I, up, gp, rp, ip, zs, Y, w',
                            'bin_mode': None,
                            'exp_count': 10,
                            'exp_length': 80.0,
                            'schedule_ok': True,
                            'start_time': '2016-04-06T10:10:00',
                            'end_time': '2016-04-06T17:12:00',
                            'mid_time': '2016-04-06T13:41:00',
                            'vis_start': '2016-04-06T10:10:00',
                            'vis_end': '2016-04-06T17:12:00',
                            'edit_window': False,
                            'ra_midpoint': 3.3125083790342504,
                            'dec_midpoint': -0.16076987814455768,
                            'period': None,
                            'jitter': None,
                            'instrument_code': '',
                            'saturated': None,
                            'snr': None,
                            'too_mode': False,
                            'calibs': '',
                            'spectroscopy': False,
                            'calibsource': {},
                            'calibsource_id': -1,
                            'calibsource_exptime': 60,
                            'calibsource_list': None,
                            'calibsource_list_options': [],
                            'calibsource_predict_exptime': 60,
                            'solar_analog': False,
                            'vis_time': 7.033333333333333,
                            'lco_enc': 'DOMA',
                            'lco_site': 'COJ',
                            'lco_tel': '1M0',
                            'max_alt': 67,
                            'moon_alt': -59.5216514230195,
                            'moon_phase': 1.2020664612667709,
                            'moon_sep': 170.4033428302428,
                            'trail_len': 1.9362070587035247,
                            'typical_seeing': 2.0,
                            'ipp_value': 1.0,
                            'para_angle': False,
                            'ag_exp_time': None,
                            'max_airmass': 1.74,
                            'max_alt_airmass': 1.0861815238132588,
                            'min_lunar_dist': 30,
                            'acceptability_threshold': 90,
                            'dither_distance': 10,
                            'add_dither': False,
                            'fractional_rate': 0.5,
                        }

    def make_visible_obj(self, test_date):
        """
        Create Test Body named "over_there" that will always be visible on the given date.
        Assumes Ecliptic is always visible. Will not work from poles during winter.
        :param test_date: datetime upon which the object must be visible
        :return: body object
        """
        sun_ra, sun_dec = accurate_astro_darkness('500', test_date, solar_pos=True)
        params = {  'provisional_name' : 'vis',
                    'name'          : 'over_there',
                    'abs_mag'       : 20.7,
                    'slope'         : 0.15,
                    'epochofel'     : test_date,
                    'meananom'      : 0,
                    'argofperih'    : 0,
                    'longascnode'   : degrees(sun_ra - pi),
                    'orbinc'        : 0,
                    'eccentricity'  : 0,
                    'meandist'      : 1.4607441,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        vis_body, created = Body.objects.get_or_create(**params)
        return vis_body

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_good(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data['site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = data['utc_date'].isoformat()

        resp = schedule_check(data, self.body_mp)

        assertDeepAlmostEqual(self, expected_resp1, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_no_changes_if_good(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = { 'site_code' : 'Q63',
                 'utc_date' : date(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code
               }

        expected_resp = schedule_check(data, self.body_mp)
        data2 = expected_resp.copy()
        data2['start_time'] = datetime.strptime(data2['start_time'], '%Y-%m-%dT%H:%M:%S')
        data2['mid_time'] = datetime.strptime(data2['mid_time'], '%Y-%m-%dT%H:%M:%S')
        data2['utc_date'] = datetime.strptime(data2['utc_date'], '%Y-%m-%d').date()
        data2['end_time'] = datetime.strptime(data2['end_time'], '%Y-%m-%dT%H:%M:%S')

        resp = schedule_check(data2, self.body_mp)

        assertDeepAlmostEqual(self, expected_resp, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_change_start_time(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 6, 15, 10, 0),
                'end_time': datetime(2016, 4, 6, 17, 12, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = data['utc_date'].isoformat()
        expected_resp1['start_time'] = data['start_time'].isoformat()
        expected_resp1['mid_time'] = '2016-04-06T16:11:00'

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_change_start_time_early(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 6, 5, 10, 0),
                'end_time': datetime(2016, 4, 6, 17, 12, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = data['utc_date'].isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_change_start_time_late(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 7, 5, 10, 0),
                'end_time': datetime(2016, 4, 6, 17, 12, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 7).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 7, 10, 6, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-07T13:35:00'
        expected_resp1['end_time'] = datetime(2016, 4, 7, 17, 4, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_change_end_time_late(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 6, 10, 10, 0),
                'end_time': datetime(2016, 4, 8, 17, 12, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time', 'group_name']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_change_end_time_less(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 6, 10, 10, 0),
                'end_time': datetime(2016, 4, 6, 12, 10, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()
        expected_resp1['end_time'] = data['end_time'].isoformat()
        expected_resp1['mid_time'] = '2016-04-06T11:10:00'

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_change_end_time_early(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 6, 10, 10, 0),
                'end_time': datetime(2016, 4, 2, 12, 10, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_generic(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': '1M0',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 6, 2, 0, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-06T14:00:00'
        expected_resp1['end_time'] = datetime(2016, 4, 7, 2, 0, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_generic_change_start(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': '1M0',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 6, 10, 0, 0),
                'end_time': datetime(2016, 4, 7, 0, 0, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 6, 10, 0, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-06T17:00:00'
        expected_resp1['end_time'] = datetime(2016, 4, 7, 0, 0, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_generic_change_start_late(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': '1M0',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 18, 0, 0, 0),
                'end_time': datetime(2016, 4, 7, 0, 0, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 18).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 18, 0, 0, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-18T00:00:00'
        expected_resp1['end_time'] = datetime(2016, 4, 18, 0, 0, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_generic_change_end_late(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': '1M0',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time' : datetime(2016, 4, 6, 0, 0, 0),
                'end_time': datetime(2016, 4, 17, 0, 0, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 11).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 6, 2, 0, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-11T13:00:00'
        expected_resp1['end_time'] = datetime(2016, 4, 17, 0, 0, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_generic_change_end_early(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': '1M0',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'start_time': datetime(2016, 4, 6, 0, 0, 0),
                'end_time': datetime(2016, 4, 2, 0, 0, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 6, 2, 0, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-06T02:00:00'
        expected_resp1['end_time'] = datetime(2016, 4, 6, 2, 0, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_cadence(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'period': 2,
                'jitter': 2,
                'proposal_code': self.neo_proposal.code,
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data['site_code'].upper() + '-' +\
                                       'cad-{}-{}'.format(datetime.strftime(data['utc_date'], '%Y%m%d'), datetime.strftime(data['utc_date'], '%m%d'))
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time', 'group_name']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_cadence_change_much(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 7),
                'proposal_code': self.neo_proposal.code,
                'period': 2,
                'jitter': 2,
                'start_time': datetime(2016, 4, 6, 12, 0, 0),
                'end_time': datetime(2016, 4, 8, 12, 0, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + 'cad-{}-{}'.format(datetime.strftime(data['start_time'], '%Y%m%d'), datetime.strftime(data['end_time'], '%m%d'))
        expected_resp1['utc_date'] = date(2016, 4, 7).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 6, 12, 0, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-07T12:00:00'
        expected_resp1['end_time'] = datetime(2016, 4, 8, 12, 0, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time', 'group_name']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_time_cadence_change_little(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'period': 2,
                'jitter': 2,
                'start_time': datetime(2016, 4, 6, 12, 0, 0),
                'end_time': datetime(2016, 4, 6, 19, 0, 0),
                'edit_window': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data[
            'site_code'].upper() + '-' + 'cad-{}-{}'.format(datetime.strftime(data['start_time'], '%Y%m%d'), datetime.strftime(data['end_time'], '%m%d'))
        expected_resp1['utc_date'] = date(2016, 4, 6).isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 6, 12, 0, 0).isoformat()
        expected_resp1['mid_time'] = '2016-04-06T14:36:00'
        expected_resp1['end_time'] = datetime(2016, 4, 6, 17, 12, 0).isoformat()

        check_list = ['utc_date', 'start_time', 'mid_time', 'end_time', 'group_name']

        resp = schedule_check(data, self.body_mp)

        for check in check_list:
            self.assertEqual(expected_resp1[check], resp[check], msg=check)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_good_too(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)
        # Turn on ToO mode on proposal
        self.neo_proposal.time_critical = True
        self.neo_proposal.save()

        data = { 'site_code' : 'Q63',
                 'utc_date' : date(2016, 4, 6),
                 'proposal_code' : self.neo_proposal.code,
                 'too_mode' : True
               }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data['site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d') + '_ToO'
        expected_resp1['utc_date'] = data['utc_date'].isoformat()
        expected_resp1['too_mode'] = True

        resp = schedule_check(data, self.body_mp)

        assertDeepAlmostEqual(self, expected_resp1, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_bad_too(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'site_code': 'Q63',
                'utc_date': datetime(2016, 4, 6).date(),
                'proposal_code': self.neo_proposal.code,
                'too_mode': True
                }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data['site_code'].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d')
        expected_resp1['utc_date'] = data['utc_date'].isoformat()

        resp = schedule_check(data, self.body_mp)

        assertDeepAlmostEqual(self, expected_resp1, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_good_spectro(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'instrument_code': 'E10-FLOYDS',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'spectroscopy': True,
                'calibs': 'both',
                'exp_length': 300.0,
                'exp_count': 1,
                'max_airmass': 2.0,
                'fractional_rate': 0.5
                }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.096949378287967,
                        'speed': 2.904309581894179,
                        'slot_length': 22,
                        'filter_pattern': 'slit_6.0as',
                        'pattern_iterations': 1.0,
                        'available_filters': 'slit_1.2as, slit_1.6as, slit_2.0as, slit_6.0as',
                        'exp_count': 1,
                        'exp_length': 300.0,
                        'schedule_ok': True,
                        'site_code': data['instrument_code'][0:3],
                        'proposal_code': data['proposal_code'],
                        'group_name': self.body_mp.current_name() + '_' + data['instrument_code'][0:3].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d') + '_spectra',
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:42:00',
                        'end_time': '2016-04-06T17:40:00',
                        'vis_start': '2016-04-06T09:42:00',
                        'vis_end': '2016-04-06T17:40:00',
                        'mid_time': '2016-04-06T13:41:00',
                        'edit_window': False,
                        'ra_midpoint': 3.3125083797952244,
                        'dec_midpoint': -0.16076987807708198,
                        'period': None,
                        'jitter': None,
                        'bin_mode': None,
                        'instrument_code': 'E10-FLOYDS',
                        'saturated': False,
                        'snr': 4.961338560320349,
                        'calibs': 'both',
                        'spectroscopy': True,
                        'too_mode': False,
                        'calibsource': {},
                        'calibsource_id': -1,
                        'calibsource_exptime': 60,
                        'calibsource_list': None,
                        'calibsource_list_options': [],
                        'calibsource_predict_exptime': 60,
                        'solar_analog': False,
                        'vis_time': 7.966666666666667,
                        'lco_enc': 'CLMA',
                        'lco_site': 'COJ',
                        'lco_tel': '2M0',
                        'max_alt': 67,
                        'moon_alt': -59.52147932253441,
                        'moon_phase': 1.2020671312553743,
                        'moon_sep': 170.40334265453788,
                        'trail_len': 0.4840515969823632,
                        'typical_seeing': 2.0,
                        'ipp_value': 1.0,
                        'para_angle': False,
                        'ag_exp_time': 10,
                        'max_airmass': 2.0,
                        'max_alt_airmass': 1.0861815238132588,
                        'min_lunar_dist': 30,
                        'acceptability_threshold': 90,
                        'dither_distance': 10,
                        'add_dither': False,
                        'fractional_rate': 1.0,
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_good_spectro_solar_analog(self):
        MockDateTime.change_datetime(2016, 4, 6, 2, 0, 0)

        data = {'instrument_code': 'E10-FLOYDS',
                'utc_date': date(2016, 4, 6),
                'proposal_code': self.neo_proposal.code,
                'spectroscopy': True,
                'calibs': 'both',
                'exp_length': 300.0,
                'exp_count': 1,
                'solar_analog': True,
                'max_airmass': 2.0
                }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'magnitude': 19.096949378287967,
                        'speed': 2.904309581894179,
                        'slot_length': 22,
                        'filter_pattern': 'slit_6.0as',
                        'pattern_iterations': 1.0,
                        'available_filters': 'slit_1.2as, slit_1.6as, slit_2.0as, slit_6.0as',
                        'bin_mode': None,
                        'exp_count': 1,
                        'exp_length': 300.0,
                        'schedule_ok': True,
                        'site_code': data['instrument_code'][0:3],
                        'proposal_code': data['proposal_code'],
                        'group_name': self.body_mp.current_name() + '_' + data['instrument_code'][0:3].upper() + '-' + datetime.strftime(data['utc_date'], '%Y%m%d') + '_spectra',
                        'utc_date': data['utc_date'].isoformat(),
                        'start_time': '2016-04-06T09:42:00',
                        'end_time': '2016-04-06T17:40:00',
                        'mid_time': '2016-04-06T13:41:00',
                        'vis_start': '2016-04-06T09:42:00',
                        'vis_end': '2016-04-06T17:40:00',
                        'edit_window': False,
                        'ra_midpoint': 3.3125083797952244,
                        'dec_midpoint': -0.16076987807708198,
                        'period': None,
                        'jitter': None,
                        'instrument_code': 'E10-FLOYDS',
                        'saturated': False,
                        'snr': 4.961338560320349,
                        'calibs': 'both',
                        'spectroscopy': True,
                        'too_mode': False,
                        'calibsource': {'separation_deg': 11.532781052438736, **model_to_dict(self.solar_analog)},
                        'calibsource_id': 1,
                        'calibsource_exptime': 180,
                        'calibsource_list': None,
                        'calibsource_list_options': ['1: SA42-999 (11.5°)'],
                        'calibsource_predict_exptime': 180,
                        'solar_analog': True,
                        'vis_time': 7.966666666666667,
                        'lco_enc': 'CLMA',
                        'lco_site': 'COJ',
                        'lco_tel': '2M0',
                        'max_alt': 67,
                        'moon_alt': -59.52147932253441,
                        'moon_phase': 1.2020671312553743,
                        'moon_sep': 170.40334265453788,
                        'trail_len': 0.4840515969823632,
                        'typical_seeing': 2.0,
                        'ipp_value': 1.0,
                        'para_angle': False,
                        'ag_exp_time': 10,
                        'max_airmass': 2.0,
                        'max_alt_airmass': 1.0861815238132588,
                        'min_lunar_dist': 30,
                        'acceptability_threshold': 90,
                        'dither_distance': 10,
                        'add_dither': False,
                        'fractional_rate': 1.0,
                        }

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_cadence_short_name(self):
        MockDateTime.change_datetime(2016, 4, 4, 2, 0, 0)
        self.body_mp.name = '2009 HA'
        self.body_mp.save()

        data = { 'site_code': 'Q63',
                 'utc_date': date(2016, 4, 6),
                 'proposal_code': self.neo_proposal.code,
                 'period': 4.0,
                 'jitter': 1.0,
                 'start_time': datetime(2016, 4, 5, 4, 22, 0),
                 'end_time': datetime(2016, 4, 7, 23, 0, 0),
                 'edit_window': True
               }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data['site_code'].upper() + '-cad-' + datetime.strftime(data['start_time'], '%Y%m%d') + '-' + datetime.strftime(data['end_time'], '%m%d')
        expected_resp1['utc_date'] = data['utc_date'].isoformat()
        expected_resp1['jitter'] = data['jitter']
        expected_resp1['period'] = data['period']
        expected_resp1['start_time'] = datetime(2016, 4, 5, 4, 22, 0).isoformat()
        expected_resp1['end_time'] = datetime(2016, 4, 7, 23, 0, 0).isoformat()
        expected_resp1['vis_start'] = datetime(2016, 4, 5, 4, 22, 0).isoformat()
        expected_resp1['vis_end'] = datetime(2016, 4, 7, 23, 0, 0).isoformat()
        expected_resp1['edit_window'] = True
        expected_resp1['num_times'] = 16
        expected_resp1['total_time'] = 5.333333333333333
        expected_resp1['target_name'] = self.body_mp.name

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp1, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_cadence_bad_jitter(self):
        MockDateTime.change_datetime(2016, 4, 4, 2, 0, 0)
        self.body_mp.name = '2009 HA'
        self.body_mp.save()

        data = { 'site_code': 'Q63',
                 'utc_date': date(2016, 4, 6),
                 'proposal_code': self.neo_proposal.code,
                 'period': 4.0,
                 'jitter': 0.1,
                 'start_time': datetime(2016, 4, 5, 4, 22, 0),
                 'end_time': datetime(2016, 4, 7, 23, 0, 0),
                 'edit_window': True
               }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data['site_code'].upper() + '-cad-' + datetime.strftime(data['start_time'], '%Y%m%d') + '-' + datetime.strftime(data['end_time'], '%m%d')
        expected_resp1['utc_date'] = data['utc_date'].isoformat()
        expected_resp1['jitter'] = .34
        expected_resp1['period'] = data['period']
        expected_resp1['start_time'] = datetime(2016, 4, 5, 4, 22, 0).isoformat()
        expected_resp1['end_time'] = datetime(2016, 4, 7, 23, 0, 0).isoformat()
        expected_resp1['vis_start'] = datetime(2016, 4, 5, 4, 22, 0).isoformat()
        expected_resp1['vis_end'] = datetime(2016, 4, 7, 23, 0, 0).isoformat()
        expected_resp1['edit_window'] = True
        expected_resp1['num_times'] = 16
        expected_resp1['total_time'] = 5.333333333333333
        expected_resp1['target_name'] = self.body_mp.name

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp1, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_cadence_long_name(self):
        MockDateTime.change_datetime(2016, 4, 4, 2, 0, 0)

        data = { 'site_code': 'Q63',
                 'utc_date': date(2016, 4, 6),
                 'proposal_code': self.neo_proposal.code,
                 'period': 4.0,
                 'jitter': 1.0,
                 'start_time': datetime(2016, 4, 5, 4, 22, 0),
                 'end_time': datetime(2016, 4, 7, 23, 0, 0),
                 'edit_window': True
               }

        expected_resp1 = self.expected_resp
        expected_resp1['site_code'] = data['site_code']
        expected_resp1['proposal_code'] = data['proposal_code']
        expected_resp1['group_name'] = self.body_mp.current_name() + '_' + data['site_code'].upper() + '-cad-' + datetime.strftime(data['start_time'], '%Y%m%d') + '-' + datetime.strftime(data['end_time'], '%m%d')
        expected_resp1['utc_date'] = data['utc_date'].isoformat()
        expected_resp1['start_time'] = datetime(2016, 4, 5, 4, 22, 0).isoformat()
        expected_resp1['end_time'] = datetime(2016, 4, 7, 23, 0, 0).isoformat()
        expected_resp1['edit_window'] = True
        expected_resp1['vis_start'] = datetime(2016, 4, 5, 4, 22, 0).isoformat()
        expected_resp1['vis_end'] = datetime(2016, 4, 7, 23, 0, 0).isoformat()
        expected_resp1['jitter'] = data['jitter']
        expected_resp1['period'] = data['period']
        expected_resp1['num_times'] = 16
        expected_resp1['total_time'] = 5.333333333333333

        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp1, resp)
        self.assertLessEqual(len(resp['group_name']), 50)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_B_semester(self):
        MockDateTime.change_datetime(2016, 3, 30, 22, 0, 0)

        data = {'site_code': 'K92',
                'utc_date': date(2016, 4, 1),
                'proposal_code': self.neo_proposal.code
                }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time': '2016-03-31T19:18:00',
                        'end_time': '2016-03-31T23:59:00',
                        'exp_count': 14,
                        'exp_length': 50.0,
                        'mid_time': '2016-03-31T21:38:00',
                        }
        resp = schedule_check(data, self.body_mp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])
        self.assertEqual(expected_resp['exp_count'], resp['exp_count'])
        self.assertEqual(expected_resp['exp_length'], resp['exp_length'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_start_A_semester(self):
        MockDateTime.change_datetime(2016, 4, 1, 0, 0, 2)

        data = { 'site_code': 'K92',
                 'utc_date': datetime(2016, 4, 1).date(),
                 'proposal_code': self.neo_proposal.code
               }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time': '2016-04-01T00:00:00',
                        'end_time': '2016-04-01T02:44:00',
                        'exp_count': 14,
                        'exp_length': 50.0,
                        'mid_time': '2016-04-01T01:22:00',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])
        self.assertEqual(expected_resp['exp_count'], resp['exp_count'])
        self.assertEqual(expected_resp['exp_length'], resp['exp_length'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_mid_A_semester(self):
        MockDateTime.change_datetime(2016, 4, 20, 23, 0, 0)

        data = {'site_code': 'V37',
                'utc_date': datetime(2016, 4, 21).date(),
                'proposal_code': self.neo_proposal.code
                }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time': '2016-04-21T02:30:00',
                        'end_time': '2016-04-21T08:06:00',
                        'vis_start': '2016-04-21T02:30:00',
                        'vis_end': '2016-04-21T08:06:00',
                        'exp_count': 4,
                        'exp_length': 255,
                        'mid_time': '2016-04-21T05:18:00',
                        'magnitude': 20.97
                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])
        self.assertEqual(expected_resp['exp_count'], resp['exp_count'])
        self.assertEqual(expected_resp['exp_length'], resp['exp_length'])
        self.assertAlmostEqual(expected_resp['magnitude'], resp['magnitude'], 2)

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_mid_past_A_semester(self):
        MockDateTime.change_datetime(2015, 4, 20, 23, 1, 0)

        data = {'site_code': 'V37',
                'utc_date': datetime(2015, 4, 21).date(),
                'proposal_code': self.neo_proposal.code
                }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time': '2015-04-21T09:22:00',
                        'end_time': '2015-04-21T11:08:00',
                        'vis_start': '2015-04-21T09:22:00',
                        'vis_end': '2015-04-21T11:08:00',
                        'exp_count': 6,
                        'exp_length': 125,
                        'mid_time': '2015-04-21T10:15:00',
                        'magnitude': 20.97
                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_A_semester(self):
        MockDateTime.change_datetime(2016, 9, 29, 23, 0, 0)

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2016, 10, 1).date(),
                 'proposal_code' : self.neo_proposal.code
               }

        body = self.make_visible_obj(datetime(2016, 9, 30, 23, 0, 0))

        expected_resp = {
                        'target_name': body.current_name(),
                        'start_time': '2016-09-30T19:28:00',
                        'end_time': '2016-09-30T23:59:00',
                        'mid_time': '2016-09-30T21:43:00',
                        'vis_start': '2016-09-30T19:28:00',
                        'vis_end': '2016-09-30T23:59:00',
                        }
        resp = schedule_check(data, body)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_schedule_for_B_at_A_semester_end(self):
        MockDateTime.change_datetime(2017, 3, 31, 23, 0, 0)

        data = {'site_code': 'K92',
                'utc_date': datetime(2017, 4, 2).date(),
                'proposal_code': self.neo_proposal.code
                }

        expected_resp = {
                        'target_name': self.body_mp.current_name(),
                        'start_time': '2017-04-02T01:10:00',
                        'end_time': '2017-04-02T03:38:00',
                        'mid_time': '2017-04-02T02:24:00',

                        }
        resp = schedule_check(data, self.body_mp)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_schedule_for_B_at_A_semester_end2(self):

        data = { 'site_code' : 'K92',
                 'utc_date' : datetime(2017, 4, 1).date(),
                 'proposal_code' : self.neo_proposal.code
               }

        MockDateTime.change_datetime(2017, 3, 31, 23, 0, 0)

        body = self.make_visible_obj(datetime(2017, 3, 31, 23, 0, 0))

        expected_resp = {
                        'target_name': body.current_name(),
                        'start_time' : '2017-04-01T00:00:00',
                        'end_time'   : '2017-04-01T01:46:00',
                        'mid_time': '2017-04-01T00:53:00',

                        }
        resp = schedule_check(data, body)
#        self.assertEqual(expected_resp, resp)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_2017AB_semester(self):
        MockDateTime.change_datetime(2017, 9, 28, 19, 0, 0)

        data = { 'site_code' : 'Z17',
                 'utc_date' : datetime(2017, 10, 1).date(),
                 'proposal_code' : self.neo_proposal.code
               }

        body = self.make_visible_obj(datetime(2017, 9, 28, 19, 0, 0))

        expected_resp = {
                        'target_name': body.current_name(),
                        'start_time' : '2017-09-30T21:26:00',
                        'end_time'   : '2017-10-01T03:56:00',
                        'mid_time': '2017-10-01T00:41:00',

                        }
        resp = schedule_check(data, body)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_2017AB_semester(self):
        MockDateTime.change_datetime(2017, 11, 30, 19, 0, 0)

        data = { 'site_code' : 'Z17',
                 'utc_date' : datetime(2017, 12, 1).date(),
                 'proposal_code' : self.neo_proposal.code
               }

        body = self.make_visible_obj(datetime(2017, 11, 30, 19, 0, 0))

        expected_resp = {
                        'target_name': body.current_name(),
                        'start_time' : '2017-11-30T20:38:00',
                        'end_time'   : '2017-11-30T23:59:00',
                        'mid_time': '2017-11-30T22:18:00',

                        }
        resp = schedule_check(data, body)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_start_2018A_semester_window_too_small(self):
        MockDateTime.change_datetime(2017, 12,  1,  1, 0, 0)

        data = { 'site_code' : 'K91',
                 'utc_date' : datetime(2017, 12, 1).date(),
                 'proposal_code' : self.neo_proposal.code,
               }

        body = self.make_visible_obj(datetime(2017, 12,  1,  1, 0, 0))

        expected_resp = {
                        'target_name': body.current_name(),
                        'start_time' : '2017-12-01T01:00:00',
                        'end_time'   : '2017-12-01T01:00:00',
                        'mid_time': '2017-12-01T01:00:00',
                        }
        resp = schedule_check(data, body)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_2018A_semester(self):
        MockDateTime.change_datetime(2018, 5, 30, 23, 0, 0)

        data = { 'site_code' : 'K91',
                 'utc_date' : datetime(2018,  6, 1).date(),
                 'proposal_code' : self.neo_proposal.code
               }

        body = self.make_visible_obj(datetime(2018,  5, 31, 23, 0, 0))

        expected_resp = {
                        'target_name': body.current_name(),
                        'start_time' : '2018-05-31T18:16:00',
                        'end_time'   : '2018-05-31T23:59:00',
                        'mid_time': '2018-05-31T21:07:00',

                        }
        resp = schedule_check(data, body)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_mp_semester_end_2018B_semester(self):
        MockDateTime.change_datetime(2018, 11, 29, 23, 0, 0)

        data = {'site_code': 'Z17',
                 'utc_date': datetime(2018, 12, 1).date(),
                 'proposal_code': self.neo_proposal.code
                }

        body = self.make_visible_obj(datetime(2018, 11, 30, 23, 0, 0))

        expected_resp = {
                        'target_name': body.current_name(),
                        'start_time' : '2018-11-30T20:38:00',
                        'end_time'   : '2018-11-30T23:59:00',
                        'mid_time'   : '2018-11-30T22:18:00',
                        }
        resp = schedule_check(data, body)

        self.assertEqual(expected_resp['start_time'], resp['start_time'])
        self.assertEqual(expected_resp['end_time'], resp['end_time'])
        self.assertEqual(expected_resp['mid_time'], resp['mid_time'])

    @patch('core.views.fetch_filter_list', mock_fetch_filter_list)
    @patch('core.views.datetime', MockDateTime)
    def test_muscat_sub(self):
        MockDateTime.change_datetime(2018, 11, 29, 23, 0, 0)

        data = {'site_code': 'F65',
                'utc_date': datetime(2018, 12, 1).date(),
                'proposal_code': self.neo_proposal.code
                }

        body = self.make_visible_obj(datetime(2018, 11, 30, 23, 0, 0))

        new_resp = {'site_code': 'F65',
                    'available_filters': 'gp, rp, ip, zp',
                    'exp_count': 4,
                    'exp_length': 240.0,
                    'slot_length': 22.5,
                    'filter_pattern': 'gp',
                    'pattern_iterations': 4.0,
                    'gp_explength': 240.0,
                    'rp_explength': 240.0,
                    'ip_explength': 240.0,
                    'zp_explength': 240.0,
                    'muscat_sync': False,
                    'group_name': 'over_there_F65-20181201',
                    'lco_enc': 'CLMA',
                    'lco_site': 'OGG',
                    'lco_tel': '2M0',
                    }

        resp = schedule_check(data, body)

        for key in new_resp:
            self.assertEqual(new_resp[key], resp[key])


class TestUpdateMPCOrbit(TestCase):

    def setUp(self):

        # Read and make soup from a static version of the HTML tables/pages for
        # 3 objects
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_2014UR.html'), 'r')
        self.test_mpcdb_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet243P.html'), 'r')
        self.test_mpcdb_page_spcomet = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet2016C2.html'), 'r')
        self.test_mpcdb_page_comet = BeautifulSoup(test_fh, "html.parser")

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet2017K2.html'), 'r')
        self.test_mpcdb_page_dnc_comet = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()


        # We preset some things here to avoid having to actually call JPL in the test
        self.test_body_2014UR, created = Body.objects.get_or_create(id=1, name='2014 UR')
        self.test_body_243P, created = Body.objects.get_or_create(id=2, name='243P/NEAT', source_subtype_1='JF')
        params = {  'parameter_type' : 'M1',
                    'value' : 10.4,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_243P, **params)
        params = {  'parameter_type' : 'K1',
                    'value' : 15.5,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_243P, **params)

        self.test_body_C2016C2, created = Body.objects.get_or_create(id=3, name='C/2016 C2', source_subtype_1='LP')
        params = {  'parameter_type' : 'M1',
                    'value' : 13.8,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_C2016C2, **params)
        params = {  'parameter_type' : 'K1',
                    'value' : 21.0,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_C2016C2, **params)
        params = {  'parameter_type' : 'M2',
                    'value' : 17.5,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_C2016C2, **params)
        params = {  'parameter_type' : 'K2',
                    'value' : 5.0,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_C2016C2, **params)

        self.test_body_C2017K2, created = Body.objects.get_or_create(id=4, name='C/2017 K2', source_subtype_1='LP')
        params = {  'parameter_type' : 'M1',
                    'value' : 6.3,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_C2017K2, **params)
        params = {  'parameter_type' : 'K1',
                    'value' : 5.75,
                    'preferred' : True
                 }
        pp = PhysicalParameters.objects.create(body=self.test_body_C2017K2, **params)

        self.nocheck_keys = ['ingest']   # Involves datetime.utcnow(), hard to check

        self.expected_elements = {u'id': 1,
                                  'name': u'2014 UR',
                                  'provisional_name': None,
                                  'provisional_packed': None,
                                  'elements_type': u'MPC_MINOR_PLANET',
                                  'abs_mag' : 26.6,
                                  'argofperih': 222.91160,
                                  'longascnode': 24.87559,
                                  'eccentricity': 0.0120915,
                                  'epochofel': datetime(2016, 1, 13, 0),
                                  'meandist': 0.9967710,
                                  'orbinc': 8.25708,
                                  'meananom': 221.74204,
                                  'epochofperih': None,
                                  'perihdist': None,
                                  'slope': 0.15,
                                  'origin': u'M',
                                  'active': True,
                                  'arc_length': 357.0,
                                  'discovery_date': datetime(2014, 10, 17, 0),
                                  'num_obs': 147,
                                  'not_seen': 5.5,
                                  'orbit_rms': 0.57,
                                  'fast_moving': False,
                                  'score': None,
                                  'source_type': 'N',
                                  'source_subtype_1': None,
                                  'source_subtype_2': None,
                                  'update_time': datetime(2015, 10, 9, 0),
                                  'updated': True,
                                  'urgency': None,
                                  'analysis_status': 0,
                                  'as_updated': None
                                  }

        # Elements from epoch=2018-03-23 set
        self.expected_elements_sp_comet = {
                                             'id': 2,
                                             'name': u'243P/NEAT',
                                             'provisional_name': None,
                                             'provisional_packed': None,
                                             'elements_type': u'MPC_COMET',
                                             'abs_mag': 10.4,
                                             'argofperih': 283.56217,
                                             'longascnode': 87.66076,
                                             'eccentricity': 0.3591386,
                                             'epochofel': datetime(2018, 3, 23, 0),
                                             'meandist': None,
                                             'orbinc': 7.64150,
                                             'meananom': None,
                                             'epochofperih': datetime(2018, 8, 26, 0, 59, 55, int(0.968*1e6)),
                                             'perihdist': 2.4544160,
                                             'slope': 15.5/2.5,
                                             'origin': u'M',
                                             'active': True,
                                             'arc_length': 5528.0,
                                             'discovery_date': datetime(2003,  8,  1, 0),
                                             'num_obs': 334,
                                             'not_seen': -151.5,
                                             'orbit_rms': 0.60,
                                             'fast_moving': False,
                                             'score': None,
                                             'source_type': 'C',
                                             'source_subtype_1': 'JF',
                                             'source_subtype_2': None,
                                             'update_time' : datetime(2018, 9, 19, 0),
                                             'updated': True,
                                             'urgency': None,
                                             'analysis_status': 0,
                                             'as_updated': None
                                             }

        # Elements from epoch=2016-04-19 set
        self.expected_elements_comet_set1 = {
                                             'id': 3,
                                             'name': u'C/2016 C2',
                                             'provisional_name': None,
                                             'provisional_packed': None,
                                             'elements_type': u'MPC_COMET',
                                             'abs_mag': 13.8,
                                             'argofperih': 214.01052,
                                             'longascnode': 24.55858,
                                             'eccentricity': 1.0000000,
                                             'epochofel': datetime(2016, 4, 19, 0),
                                             'meandist': None,
                                             'orbinc': 38.19233,
                                             'meananom': None,
                                             'epochofperih': datetime(2016, 4, 19, 0, 41, 44, int(0.736*1e6)),
                                             'perihdist': 1.5671127,
                                             'slope': 21/2.5,
                                             'origin': u'M',
                                             'active': True,
                                             'arc_length': 10.0,
                                             'discovery_date': datetime(2016, 2, 8, 0),
                                             'num_obs': 89,
                                             'not_seen': 62.5,
                                             'orbit_rms': 99.0,
                                             'fast_moving': False,
                                             'score': None,
                                             'source_type': 'C',
                                             'source_subtype_1': 'LP',
                                             'source_subtype_2': None,
                                             'update_time': datetime(2016, 2, 18, 0),
                                             'updated': True,
                                             'urgency': None,
                                             'analysis_status': 0,
                                             'as_updated': None
                                             }

        # Elements from epoch=2016-07-30 set
        self.expected_elements_comet_set2 = {
                                             'id': 3,
                                             'name': u'C/2016 C2',
                                             'provisional_name': None,
                                             'provisional_packed': None,
                                             'elements_type': u'MPC_COMET',
                                             'abs_mag': 13.8,
                                             'argofperih': 214.40704,
                                             'longascnode': 24.40401,
                                             'eccentricity': 0.9755678,
                                             'epochofel': datetime(2016, 7, 31, 0),
                                             'meandist': None,
                                             'orbinc': 38.15649,
                                             'meananom': None,
                                             'epochofperih': datetime(2016, 4, 19, 14, 26, 29, int(0.472*1e6)),
                                             'perihdist': 1.5597633,
                                             'slope': 21.0/2.5,
                                             'origin': u'M',
                                             'active': True,
                                             'arc_length': 126,
                                             'discovery_date': datetime(2016, 2, 8, 0),
                                             'num_obs': 138,
                                             'not_seen': 311.5,
                                             'orbit_rms': 0.40,
                                             'fast_moving': False,
                                             'score': None,
                                             'source_type': 'C',
                                             'source_subtype_1': 'LP',
                                             'source_subtype_2': None,
                                             'update_time': datetime(2016, 6, 13, 0),
                                             'updated': True,
                                             'urgency': None,
                                             'analysis_status': 0,
                                             'as_updated': None
                                             }

        # Elements from epoch=2019-04-27 set
        self.expected_elements_dnc_comet_set1 = {
                                             'id': 4,
                                             'name': u'C/2017 K2',
                                             'provisional_name': None,
                                             'provisional_packed': None,
                                             'elements_type': u'MPC_COMET',
                                             'abs_mag': 6.3,
                                             'argofperih': 236.10242,
                                             'longascnode': 88.27001,
                                             'eccentricity': 1.0003739,
                                             'epochofel': datetime(2019, 4, 27, 0),
                                             'meandist': None,
                                             'orbinc': 87.54153,
                                             'meananom': None,
                                             'epochofperih': datetime(2022, 12, 20, 10, 25, 51, int(0.168*1e6)),
                                             'perihdist': 1.8037084,
                                             'slope': 5.75/2.5,
                                             'origin': u'O',
                                             'active': True,
                                             'arc_length': 2339,
                                             'discovery_date': datetime(2013, 5, 12, 0),
                                             'num_obs': 1452,
                                             'not_seen': -169.5,
                                             'orbit_rms': 0.40,
                                             'fast_moving': False,
                                             'score': None,
                                             'source_type': 'C',
                                             'source_subtype_1': 'LP',
                                             'source_subtype_2': 'DN',
                                             'update_time': datetime(2019, 10, 7, 0),
                                             'updated': True,
                                             'urgency': None,
                                             'analysis_status': 0,
                                             'as_updated': None
                                             }

        self.maxDiff = None

    def test_badresponse(self):

        num_bodies_before = Body.objects.count()
        status = update_MPC_orbit(BeautifulSoup('<html></html>', 'html.parser'), origin='M')
        self.assertEqual(False, status)
        num_bodies_after = Body.objects.count()
        self.assertEqual(num_bodies_before, num_bodies_after)

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_MPC(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_2014UR.id)
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(self.expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in self.expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(self.expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_MPC_physparams(self):

        expected_types = ['H', 'D', 'G']
        expected_values = [26.6, 17.0, 0.15]
        expected_params = list(zip(expected_types, expected_values))

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='M')
        self.assertEqual(True, status)

        body = Body.objects.get(id=self.test_body_2014UR.id)
        phys_params = body.get_physical_parameters

        for param in phys_params():
            test_list = (param['parameter_type'], param['value'])
            self.assertIn(test_list, expected_params)
            expected_params.remove(test_list)
        self.assertEqual(expected_params, [])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Goldstone(self, mock_class):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'G'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='G')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_2014UR.id)
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Arecibo(self, mock_class):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'A'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Arecibo_better_exists(self):
        params = {'name': '2014 UR',
                  'abs_mag': 21.0,
                  'slope': 0.1,
                  'epochofel': '2017-03-19 00:00:00',
                  'elements_type': u'MPC_MINOR_PLANET',
                  'meananom': 325.2636,
                  'argofperih': 85.19251,
                  'longascnode': 147.81325,
                  'orbinc': 8.34739,
                  'eccentricity': 0.1896865,
                  'meandist': 1.2176312,
                  'source_type': 'U',
                  'num_obs': 1596,
                  'origin': 'M',
                  }

        self.body, created = Body.objects.get_or_create(**params)
        expected_elements = self.expected_elements
        expected_elements['origin'] = 'A'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))

        test_elements = ['epochofel', 'meananom', 'argofperih', 'longascnode', 'orbinc', 'eccentricity']
        for key in test_elements:
            self.assertNotEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    def test_physparams_given_albedo(self, mock_class):
        params = {'name': '2014 UR',
                  'abs_mag': 21.0,
                  'slope': 0.1,
                  'epochofel': '2012-03-19 00:00:00',
                  'elements_type': u'MPC_MINOR_PLANET',
                  'meananom': 325.2636,
                  'argofperih': 85.19251,
                  'longascnode': 147.81325,
                  'orbinc': 8.34739,
                  'eccentricity': 0.1896865,
                  'meandist': 1.2176312,
                  'source_type': 'U',
                  'num_obs': 1596,
                  'origin': 'M',
                  }

        Body.objects.filter(id=self.test_body_2014UR.id).update(**params)

        expected_types = ['H', 'D', 'G', 'ab']
        expected_values = [26.6, 28.45, 0.15, 0.05]
        expected_params = list(zip(expected_types, expected_values))

        body = Body.objects.last()
        phys_params = body.get_physical_parameters
        albedo_dict = {'value': 0.2,
                       'parameter_type': 'ab',
                       'preferred': True
                       }

        # Save first albedo
        body.save_physical_parameters(albedo_dict)

        # update albedo
        albedo_dict['value'] = 0.05
        body.save_physical_parameters(albedo_dict)

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        # test diameter uses only updated albedo and not default or old albedo
        for param in phys_params(return_all=False):
            test_list = (param['parameter_type'], param['value'])
            self.assertIn(test_list, expected_params)
            expected_params.remove(test_list)
        self.assertEqual(expected_params, [])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_Arecibo_older_exists(self, mock_class):
        params = {
                  'name': '2014 UR',
                  'abs_mag': 26.6,
                  'slope': 0.1,
                  'epochofel': '2013-03-19 00:00:00',
                  'elements_type': u'MPC_MINOR_PLANET',
                  'meananom': 325.2636,
                  'argofperih': 85.19251,
                  'longascnode': 147.81325,
                  'orbinc': 8.34739,
                  'eccentricity': 0.1896865,
                  'meandist': 1.2176312,
                  'source_type': 'U',
                  'num_obs': 15,
                  'origin': 'M',
                  }

        Body.objects.filter(id=self.test_body_2014UR.id).update(**params)
        expected_elements = self.expected_elements
        expected_elements['origin'] = 'A'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))

        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_goldstone_then_arecibo(self, mock_class):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'R'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='G')
        self.assertEqual(True, status)

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_arecibo_then_goldstone(self, mock_class):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'R'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='G')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    def test_2014UR_arecibo_then_NASA(self, mock_class):

        expected_elements = self.expected_elements
        expected_elements['origin'] = 'N'

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='A')
        self.assertEqual(True, status)

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        status = update_MPC_orbit(self.test_mpcdb_page, origin='N')
        self.assertEqual(True, status)

        new_body = Body.objects.last()
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(expected_elements)+len(self.nocheck_keys), len(new_body_elements))
        for key in expected_elements:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(expected_elements[key], new_body_elements[key])

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_243P_MPC(self, mock_class):

        MockDateTime.change_datetime(2018,  4, 20, 12, 0, 0)

        status = update_MPC_orbit(self.test_mpcdb_page_spcomet, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_243P.id)
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(self.expected_elements_sp_comet)+len(self.nocheck_keys), len(new_body_elements))
        for key in self.expected_elements_sp_comet:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(self.expected_elements_sp_comet[key], new_body_elements[key], msg="Failure on key: " + key)

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_243P_MPC_physpar(self, mock_class):

        MockDateTime.change_datetime(2018,  4, 20, 12, 0, 0)

        expected_types = ['M1', 'K1', 'G']
        expected_values = [10.4, 15.5, 4,0]
        expected_params = list(zip(expected_types, expected_values))

        status = update_MPC_orbit(self.test_mpcdb_page_spcomet, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_243P.id)
        phys_params = new_body.get_physical_parameters()
        self.assertEqual(len(expected_types), len(phys_params))
        for param in phys_params:
            test_list = (param['parameter_type'], param['value'])
            self.assertIn(test_list, expected_params)

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_C2016C2_April_epoch(self, mock_class):

        MockDateTime.change_datetime(2016,  4, 20, 12, 0, 0)

        status = update_MPC_orbit(self.test_mpcdb_page_comet, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_C2016C2.id)
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(self.expected_elements_comet_set1)+len(self.nocheck_keys), len(new_body_elements))
        for key in self.expected_elements_comet_set1:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(self.expected_elements_comet_set1[key], new_body_elements[key], msg="Failure on key: " + key)

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_C2016C2_July_epoch(self, mock_class):

        MockDateTime.change_datetime(2017,  4, 20, 12, 0, 0)

        status = update_MPC_orbit(self.test_mpcdb_page_comet, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_C2016C2.id)
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(self.expected_elements_comet_set2)+len(self.nocheck_keys), len(new_body_elements))
        for key in self.expected_elements_comet_set2:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(self.expected_elements_comet_set2[key], new_body_elements[key], msg="Failure on key: " + key)

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_C2016C2_physpar(self, mock_class):

        MockDateTime.change_datetime(2017,  4, 20, 12, 0, 0)

        expected_types = ['M1', 'K1', 'M2', 'K2', 'G', '/a']
        expected_values = [13.8, 21.0, 17.5, 5.0, 4.0, 0.01664452]
        expected_units = [None, None, None, None, None, 'au']
        expected_params = list(zip(expected_types, expected_values, expected_units))

        status = update_MPC_orbit(self.test_mpcdb_page_comet, origin='M')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_C2016C2.id)
        phys_params = new_body.get_physical_parameters()
        self.assertEqual(len(expected_types), len(phys_params))
        for param in phys_params:
            test_list = (param['parameter_type'], param['value'], param['units'])
            self.assertIn(test_list, expected_params)

    @patch('core.views.update_jpl_phys_params')
    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.sources_subs.datetime', MockDateTime)
    def test_C2017K2_April_epoch(self, mock_class):

        MockDateTime.change_datetime(2019, 4, 20, 12, 0, 0)

        status = update_MPC_orbit(self.test_mpcdb_page_dnc_comet, origin='O')
        self.assertEqual(True, status)

        new_body = Body.objects.get(id=self.test_body_C2017K2.id)
        new_body_elements = model_to_dict(new_body)

        self.assertEqual(len(self.expected_elements_dnc_comet_set1)+len(self.nocheck_keys), len(new_body_elements))
        for key in self.expected_elements_dnc_comet_set1:
            if key not in self.nocheck_keys and key != 'id':
                self.assertEqual(self.expected_elements_dnc_comet_set1[key], new_body_elements[key], msg="Failure on key: " + key)


class TestIngestNewObject(TestCase):

    def setUp(self):

        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.orig_orbit_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_2019EN.neocp'))
        self.orig_obs_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_2019EN.dat'))
        self.orbit_file = os.path.join(self.test_dir, '2019EN.neocp')
        self.obs_file = os.path.join(self.test_dir, '2019EN.dat')
        os.symlink(self.orig_orbit_file, self.orbit_file)
        os.symlink(self.orig_obs_file, self.obs_file)

        self.orig_disc_orbit_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_LSCTLZZ.neocp'))
        self.orig_disc_obs_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_LSCTLZZ.dat'))
        self.disc_orbit_file = os.path.join(self.test_dir, 'LSCTLZZ.neocp')
        self.disc_obs_file = os.path.join(self.test_dir, 'LSCTLZZ.dat')
        os.symlink(self.orig_disc_orbit_file, self.disc_orbit_file)
        os.symlink(self.orig_disc_obs_file, self.disc_obs_file)

        self.orig_eros_orbit_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_433.neocp'))
        self.orig_eros_obs_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_433.dat'))
        self.eros_orbit_file = os.path.join(self.test_dir, '433.neocp')
        self.eros_obs_file = os.path.join(self.test_dir, '433.dat')
        os.symlink(self.orig_eros_orbit_file, self.eros_orbit_file)
        os.symlink(self.orig_eros_obs_file, self.eros_obs_file)

        self.orig_K11H00P_orbit_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_2011HP.neocp'))
        self.orig_K11H00P_obs_file = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcorbit_2011HP.dat'))
        self.K11H00P_orbit_file = os.path.join(self.test_dir, '2011HP.neocp')
        self.K11H00P_obs_file = os.path.join(self.test_dir, '2011HP.dat')
        os.symlink(self.orig_K11H00P_orbit_file, self.K11H00P_orbit_file)
        os.symlink(self.orig_K11H00P_obs_file, self.K11H00P_obs_file)

        self.params = { 'id' : 1,
                        'provisional_name' : None,
                        'provisional_packed' : 'K19E00N',
                        'name' : '2019 EN',
                        'source_type' : 'N',
                        'abs_mag': 21.17,
                        'slope'  : 0.15,
                        'epochofel' : datetime(2019, 3, 9, 0, 0),
                        'meananom'  : 343.19351,
                        'argofperih' : 46.63108,
                        'longascnode' : 192.93185,
                        'orbinc' : 9.77594,
                        'eccentricity' : 0.618787,
                        'meandist' : 2.1786196,
                        'elements_type' : 'MPC_MINOR_PLANET',
                        'active' : True,
                        'origin' : 'M',
                        'num_obs' : 190,
                        'orbit_rms' : 0.21,
                        'discovery_date' : datetime(2019, 3,  2,  6, 51,  5, 472000),
                        'update_time' : datetime(2019, 3, 12, 16, 55, 35, 113989),
                        'arc_length' : 59.0,
                        'not_seen' : 3.7052675231018517
                      }
        self.body_2019EN = Body(**self.params)

        self.params_LSCTLZZ = self.params.copy()
        self.params_LSCTLZZ['provisional_name'] = 'LSCTLZZ'
        self.params_LSCTLZZ['provisional_packed'] = None
        self.params_LSCTLZZ['name'] = None
        self.params_LSCTLZZ['origin'] = 'L'
        self.params_LSCTLZZ['source_type'] = 'U'
        self.body_LSCTLZZ = Body(**self.params_LSCTLZZ)

        self.eros_params = { 'id' : 1,
                        'provisional_name' : None,
                        'provisional_packed' : '00433',
                        'name' : '433',
                        'source_type' : 'N',
                        'abs_mag': 10.59,
                        'slope'  : 0.15,
                        'epochofel' : datetime(2019, 2, 10, 0, 0),
                        'meananom'  :   4.70349,
                        'argofperih' : 178.80773,
                        'longascnode' : 304.30790,
                        'orbinc' : 10.82903,
                        'eccentricity' : 0.222729,
                        'meandist' : 1.4580661,
                        'elements_type' : 'MPC_MINOR_PLANET',
                        'active' : True,
                        'origin' : 'M',
                        'num_obs' : 7707,
                        'orbit_rms' : 0.51,
                        'update_time' : datetime(2019, 3, 12, 16, 55, 35, 113989),
                        'arc_length' : 46385,
                        'not_seen' : 3.7052675231018517
                      }
        self.body_433 = Body(**self.eros_params)

        self.K11H00P_params = { 'id' : 1,
                        'provisional_name' : None,
                        'provisional_packed' : 'K11H00P',
                        'name' : '2011 HP',
                        'source_type' : 'N',
                        'abs_mag': 22.23,
                        'slope'  : 0.15,
                        'epochofel' : datetime(2011, 10, 1, 0, 0),
                        'meananom'  :  37.31731,
                        'argofperih' :  45.96308,
                        'longascnode' : 229.74785,
                        'orbinc' :  3.74433,
                        'eccentricity' : 0.4800081,
                        'meandist' : 1.9235922,
                        'elements_type' : 'MPC_MINOR_PLANET',
                        'active' : True,
                        'origin' : 'M',
                        'num_obs' : 213,
                        'orbit_rms' : 0.35,
                        'update_time' : datetime(2019, 3, 12, 16, 55, 35, 113989),
                        'arc_length' : 160.0,
                        'not_seen' : 3.7052675231018517
                      }
        self.body_K11H00P = Body(**self.K11H00P_params)

        self.remove = True
        self.debug_print = False

        self.maxDiff = None

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)
        else:
            print("Not removing. Temporary test directory=", self.test_dir)

    def _compare_bodies(self, body1, body2, excluded_keys={'_state', '_prefetched_objects_cache', 'not_seen', 'ingest', 'update_time'}):
        d1, d2 = body1.__dict__, body2.__dict__
        for key, value in d1.items():
            if key in excluded_keys:
                continue
            self.assertEqual(value, d2[key], "Compare failure on " + key)

    def test_no_orbit_file(self):
        expected_body = None
        expected_msg = "Could not read orbit file: wibble"

        body, created, msg = ingest_new_object('wibble')

        self.assertEqual(expected_body, body)
        self.assertFalse(created)
        self.assertEqual(expected_msg, msg)

    def test_discovery_not_existing(self):

        expected_body = self.body_LSCTLZZ
        expected_msg = "Added new local target LSCTLZZ"

        body, created, msg = ingest_new_object(self.disc_orbit_file)

        self._compare_bodies(expected_body, body)
        self.assertTrue(created)
        self.assertEqual(expected_msg, msg)

    def test_phys_params_new_body(self):
        body = self.body_LSCTLZZ
        self.assertEqual(body.get_physical_parameters(), [])

        expected_types = ['H', 'D', 'G']
        expected_values = [21.17, 207.23, 0.15]
        expected_params = list(zip(expected_types, expected_values))
        expected_diam_range = [568, 98]

        expected_names = [['C', 'LSCTLZZ']]

        ingest_new_object(self.disc_orbit_file)

        phys_params = body.get_physical_parameters()
        names = Designations.objects.filter(body=body)

        for param in phys_params:
            test_list = (param['parameter_type'], param['value'])
            self.assertIn(test_list, expected_params)
            expected_params.remove(test_list)
            if param['parameter_type'] == 'D':
                self.assertEqual(param['error'], expected_diam_range[0])
                self.assertEqual(param['error2'], expected_diam_range[1])
        self.assertEqual(expected_params, [])

        for name in names:
            test_list = [name.desig_type, name.value]
            self.assertIn(test_list, expected_names)
            expected_names.remove(test_list)
        self.assertEqual(expected_names, [])

    def test_discovery_existing_no_changes(self):

        expected_body = self.body_LSCTLZZ
        expected_msg = "No changes saved for LSCTLZZ"

        self.body_LSCTLZZ.save()
        num_bodies_before = Body.objects.count()
        self.assertEqual(1, num_bodies_before)
        body, created, msg = ingest_new_object(self.disc_orbit_file)

        num_bodies_after = Body.objects.count()
        self.assertEqual(1, num_bodies_after)
        # Update expected values
        expected_body.updated = True
        self._compare_bodies(expected_body, body)
        self.assertFalse(created)
        self.assertEqual(expected_msg, msg)

    def test_phys_params_no_changes(self):
        body = self.body_LSCTLZZ
        expected_params = 3
        expected_names = 1

        ingest_new_object(self.disc_orbit_file)

        phys_params = body.get_physical_parameters
        names = Designations.objects.filter(body=body)

        self.assertEqual(len(phys_params()), expected_params)
        self.assertEqual(len(names), expected_names)

        ingest_new_object(self.disc_orbit_file)

        self.assertEqual(len(phys_params()), expected_params)
        self.assertEqual(len(names), expected_names)

    def test_discovery_existing_new_provname(self):

        expected_body = self.body_LSCTLZZ
        expected_msg = "Updated LSCTLZZ"

        self.body_LSCTLZZ.save()
        self.body_LSCTLZZ.refresh_from_db()
        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(1, num_bodies_before)
        self.assertEqual('L', self.body_LSCTLZZ.origin)
        # Remove symlink to LSCTLZZ.neocp orbit file and re-symlink to the 2019EN.neocp one
        # so desigination inside the file changes but it stays as LSCTLZZ.neocp
        os.unlink(self.disc_orbit_file)
        os.symlink(self.orig_orbit_file, self.disc_orbit_file)
        body, created, msg = ingest_new_object(self.disc_orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)
        # Update expected values
        expected_body.updated = True
        expected_body.provisional_packed = 'K19E00N'
        expected_body.name = '2019 EN'
        expected_body.origin = 'L'
        expected_body.source_type = 'D'

        self._compare_bodies(expected_body, body)
        self.assertFalse(created)
        self.assertEqual(expected_msg, msg)

    def test_designation_new_provname(self):
        body = self.body_LSCTLZZ
        expected_types = ['C', 'P']
        expected_desigs = ['LSCTLZZ', '2019 EN']
        expected_names = list(zip(expected_types, expected_desigs))

        ingest_new_object(self.disc_orbit_file)

        names = Designations.objects.filter(body=body)

        # Remove symlink to LSCTLZZ.neocp orbit file and re-symlink to the 2019EN.neocp one
        # so desigination inside the file changes but it stays as LSCTLZZ.neocp
        os.unlink(self.disc_orbit_file)
        os.symlink(self.orig_orbit_file, self.disc_orbit_file)

        ingest_new_object(self.disc_orbit_file)

        for name in names:
            test_list = (name.desig_type, name.value)
            self.assertIn(test_list, expected_names)
            expected_names.remove(test_list)
        self.assertEqual(expected_names, [])

    def test_knownNEO_not_existing(self):

        expected_body = self.body_2019EN
        expected_msg = "Added new local target 2019EN"

        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(0, num_bodies_before)
        body, created, msg = ingest_new_object(self.orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)

        self._compare_bodies(expected_body, body)
        self.assertTrue(created)
        self.assertEqual(expected_msg, msg)

    def test_designation_knownNEO(self):
        body = self.body_2019EN
        expected_types = ['P']
        expected_desigs = ['2019 EN']
        expected_names = list(zip(expected_types, expected_desigs))

        ingest_new_object(self.orbit_file)

        names = Designations.objects.filter(body=body)

        for name in names:
            test_list = (name.desig_type, name.value)
            self.assertIn(test_list, expected_names)
            expected_names.remove(test_list)
        self.assertEqual(expected_names, [])

    def test_knownNEO_not_existing_no_obsfile(self):

        expected_body = self.body_2019EN
        expected_msg = "Added new local target 2019EN"

        os.unlink(self.obs_file)
        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(0, num_bodies_before)
        body, created, msg = ingest_new_object(self.orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)
        # Update expected values, deleting discovery date (since no obs file)
        expected_body.discovery_date = None

        self._compare_bodies(expected_body, body)
        self.assertTrue(created)
        self.assertEqual(expected_msg, msg)

    def test_knownNEO_existing(self):

        expected_body = self.body_2019EN
        expected_msg = "No changes saved for 2019EN"

        self.body_2019EN.save()
        self.body_2019EN.refresh_from_db()

        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(1, num_bodies_before)
        body, created, msg = ingest_new_object(self.orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)
        expected_body.updated = True

        self._compare_bodies(expected_body, body)
        self.assertFalse(created)
        self.assertEqual(expected_msg, msg)

    def test_knownnumNEO_not_existing(self):

        expected_body = self.body_433
        expected_msg = "Added new local target 433"

        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(0, num_bodies_before)
        body, created, msg = ingest_new_object(self.eros_orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)

        self._compare_bodies(expected_body, body)
        self.assertTrue(created)
        self.assertEqual(expected_msg, msg)

    def test_knownnumNEO_existing(self):

        expected_body = self.body_433
        expected_msg = "No changes saved for 433"

        self.body_433.save()
        self.body_433.refresh_from_db()

        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(1, num_bodies_before)
        body, created, msg = ingest_new_object(self.eros_orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)
        expected_body.updated = True

        self._compare_bodies(expected_body, body)
        self.assertFalse(created)
        self.assertEqual(expected_msg, msg)

    def test_designation_known_num_NEO(self):
        body = self.body_433
        expected_types = ['#']
        expected_desigs = ['433']
        expected_names = list(zip(expected_types, expected_desigs))

        ingest_new_object(self.eros_orbit_file)

        names = Designations.objects.filter(body=body)

        for name in names:
            test_list = (name.desig_type, name.value)
            self.assertIn(test_list, expected_names)
            expected_names.remove(test_list)
        self.assertEqual(expected_names, [])

    def test_known_provNEO_not_existing(self):

        expected_body = self.body_K11H00P
        expected_msg = "Added new local target 2011HP"

        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(0, num_bodies_before)
        body, created, msg = ingest_new_object(self.K11H00P_orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)

        self._compare_bodies(expected_body, body)
        self.assertTrue(created)
        self.assertEqual(expected_msg, msg)

    def test_known_provNEO_existing(self):

        expected_body = self.body_K11H00P
        expected_msg = "No changes saved for 2011HP"

        self.body_K11H00P.save()
        self.body_K11H00P.refresh_from_db()

        bodies_before = Body.objects.all()
        num_bodies_before = bodies_before.count()
        self.assertEqual(1, num_bodies_before)
        body, created, msg = ingest_new_object(self.K11H00P_orbit_file)

        bodies = Body.objects.all()
        num_bodies_after = bodies.count()
        self.assertEqual(1, num_bodies_after)
        expected_body.updated = True

        self._compare_bodies(expected_body, body)
        self.assertFalse(created)
        self.assertEqual(expected_msg, msg)


class TestUpdateMPCObs(TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.debug_print = False
        self.maxDiff = None

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_WSAE9A6.dat'), 'r')
        self.test_mpcobs_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_13553.dat'), 'r')
        self.test_mpcobs_page2 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_13553_old.dat'), 'r')
        self.test_mpcobs_page3 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_215426.dat'), 'r')
        self.test_mpcobs_page4 = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

    @classmethod
    def setUpTestData(cls):
        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        cls.test_body = Body.objects.create(**WSAE9A6_params)

        params_13553 = { 'name' : '13553',
                         'provisional_name' : '1992 JE'
                         }
        cls.test_body2 = Body.objects.create(**params_13553)

        params_215426 = { 'name' : '215426',
                         'provisional_name' : '2002 JF45'
                         }
        cls.test_body3 = Body.objects.create(**params_215426)

    def test1(self):
        expected_num_srcmeas = 6
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 27, 12, int(0.672*1e6)),
                            'obs_ra'    : 325.2828333333333,
                            'obs_dec'   : -10.8525,
                            'obs_mag'   : 21.8,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        measures = update_MPC_obs(self.test_mpcobs_page)

        self.assertEqual(expected_num_srcmeas, len(measures))
        source_measures = SourceMeasurement.objects.filter(body=self.test_body)
        self.assertEqual(expected_num_srcmeas, source_measures.count())
        source_measure = source_measures[len(source_measures) - 1]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)

    def test2_multiple_designations(self):
        expected_measures = 28
        measures = update_MPC_obs(self.test_mpcobs_page2)
        self.assertEqual(len(measures), expected_measures)

    def test_repeat_sources(self):
        expected_measures = 16
        total_measures = 28
        expected_frames = 28
        first_date = datetime(1992, 6, 3, 5, 27, 4, 896000)
        last_date = datetime(2018, 12, 4, 21, 4, 6, 240000)

        # Read in old measures
        initial_measures = update_MPC_obs(self.test_mpcobs_page3)
        # update with new ones
        final_measures = update_MPC_obs(self.test_mpcobs_page2)
        self.assertEqual(len(final_measures), expected_measures)

        source_measures = SourceMeasurement.objects.filter(body=self.test_body2)
        sorted_source_measures = sorted(source_measures, key=lambda sm: sm.frame.midpoint)
        self.assertEqual(total_measures, source_measures.count())
        source_measure1 = sorted_source_measures[len(source_measures) - 1]
        source_measure2 = sorted_source_measures[0]
        self.assertEqual(last_date, source_measure1.frame.midpoint)
        self.assertEqual(first_date, source_measure2.frame.midpoint)

        frames = Frame.objects.all()
        self.assertEqual(len(frames), expected_frames)

    def test_packed_name_with_change(self):
        expected_measures = 15

        measures = update_MPC_obs(self.test_mpcobs_page4)
        self.assertEqual(len(measures), expected_measures)

    def test_obs_export(self):
        measures = update_MPC_obs(self.test_mpcobs_page2)
        expected_filename = os.path.join(self.test_dir, '13553.mpc')
        expected_out1 = '13553         C1998 02 21.09248010 31 21.78 +03 20 23.2          20.1 V      557\n'
        expected_out0 = '13553         A1994 06 05.27986 14 24 59.76 -00 36 53.4                      675\n'
        expected_num_lines = 24

        body = Body.objects.get(name='13553')
        filename, num_lines = export_measurements(body.id, self.test_dir)

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_num_lines, num_lines)

        lines = []
        with open(filename, 'r') as test_mpc_out:
            line = test_mpc_out.readline()
            while line:
                lines.append(line)
                line = test_mpc_out.readline()
        self.assertEqual(expected_out0, lines[0])
        self.assertEqual(expected_out1, lines[1])
        self.assertEqual(num_lines, len(lines)-1)


class TestCleanMPCOrbit(TestCase):

    def setUp(self):
        # Read and make soup from a static version of the HTML table/page for
        # an object
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_2014UR.html'), 'r')
        test_mpcdb_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.test_elements = parse_mpcorbit(test_mpcdb_page)

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet2016C2.html'), 'r')
        test_mpcdb_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()

        self.test_comet_elements = parse_mpcorbit(test_mpcdb_page, epoch_now=datetime(2016, 4, 24, 18, 0, 0))

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcdb_Comet243P.html'), 'r')
        self.test_multiple_epochs_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.test_comet_elements_2018Aug_epoch = parse_mpcorbit(self.test_multiple_epochs_page, epoch_now=datetime(2018, 9, 25))
        self.test_comet_elements_2018Mar_epoch = parse_mpcorbit(self.test_multiple_epochs_page, epoch_now=datetime(2018, 2, 14))

        self.test_hyperbolic_elements = {
                                         'argument of perihelion': '325.96205',
                                         'ascending node': '276.22261',
                                         'eccentricity': '1.0014825',
                                         'epoch': '2018-03-23.0',
                                         'epoch JD': '2458200.5',
                                         'first observation date used': '2017-09-18.0',
                                         'inclination': '142.63838',
                                         'last observation date used': '2018-02-10.0',
                                         'mean anomaly': None,
                                         'mean daily motion': None,
                                         'obj_id': u'A/2017 U7',
                                         'observations used': '87',
                                         'perihelion JD': '2458737.02791',
                                         'perihelion date': '2019-09-10.52791',
                                         'perihelion distance': '6.4186788',
                                         'period': None,
                                         'perturbers coarse indicator': None,
                                         'perturbers precise indicator': '0000',
                                         'radial non-grav. param.': None,
                                         'recip semimajor axis error': None,
                                         'recip semimajor axis future': '-0.00000374',
                                         'recip semimajor axis orig': '0.00011957',
                                         'reference': 'MPEC 2018-E17',
                                         'residual rms': '0.2',
                                         'semimajor axis': None,
                                         'transverse non-grav. param.': None}

        self.expected_params = {
                             'elements_type': 'MPC_MINOR_PLANET',
                             'abs_mag' : '26.6',
                             'argofperih': '222.91160',
                             'longascnode': '24.87559',
                             'eccentricity': '0.0120915',
                             'epochofel': datetime(2016, 1, 13, 0),
                             'meandist': '0.9967710',
                             'orbinc': '8.25708',
                             'meananom': '221.74204',
                             'slope': '0.15',
                             'origin' : 'M',
                             'active' : True,
                             'source_type' : 'N',
                             'discovery_date': datetime(2014, 10, 17, 0),
                             'num_obs': '147',
                             'arc_length': '357',
                             'not_seen' : 5.5,
                             # 'score' : None,
                             'orbit_rms' : 0.57,
                             'update_time' : datetime(2015, 10, 9, 0),
                             'updated' : True
                             }
        self.expected_comet_params = {
                                        'elements_type': 'MPC_COMET',
                                        'argofperih': '214.01052',
                                        'longascnode' : '24.55858',
                                        'eccentricity' : '1.0000000',
                                        'epochofel': datetime(2016, 4, 19, 0),
                                        'meandist' : None,
                                        'orbinc' : '38.19233',
                                        'meananom': None,
                                        'perihdist' : '1.5671127',
                                        'epochofperih': datetime(2016, 4, 19, 0, 41, 44, int(0.736*1e6)),
                                        'slope': '4.0',
                                        'origin' : 'M',
                                        'active' : True,
                                        'source_type' : 'C',
                                        'discovery_date': datetime(2016, 2, 8, 0),
                                        'num_obs': '89',
                                        'arc_length': '10',
                                        'not_seen' : 66.75,
                                        'update_time' : datetime(2016, 2, 18, 0),
                                        'updated' : True
                                     }
        self.expected_hyperbolic_params = {
                                        'elements_type': 'MPC_COMET',
                                        'argofperih': '325.96205',
                                        'longascnode' : '276.22261',
                                        'eccentricity' : '1.0014825',
                                        'epochofel': datetime(2018, 3, 23, 0),
                                        'meandist' : None,
                                        'orbinc' : '142.63838',
                                        'meananom': None,
                                        'perihdist' : '6.4186788',
                                        'epochofperih': datetime(2019, 9, 10, 12, 40, 11, int(0.424*1e6)),
                                        'slope': '4.0',
                                        'origin' : 'M',
                                        'active' : True,
                                        'source_type' : 'H',
                                        'discovery_date': datetime(2017, 9, 18, 0),
                                        'num_obs': '87',
                                        'arc_length': '145',
                                        'not_seen' : 23.75,
                                        'orbit_rms' : 0.2,
                                        'update_time' : datetime(2018, 2, 10, 0),
                                        'updated' : True
                                     }

        self.expected_mulepoch_params = {
                                        'elements_type': 'MPC_COMET',
                                        'argofperih': '283.55482',
                                        'longascnode' : '87.65877',
                                        'eccentricity' : '0.3593001',
                                        'epochofel': datetime(2018, 8, 30, 0),
                                        'meandist' : None,
                                        'orbinc' : '7.64145',
                                        'meananom': None,
                                        'perihdist' : '2.4544438',
                                        'epochofperih': datetime(2018, 8, 26, 0,  9, 55, int(0.296*1e6)),
                                        'slope': '4.0',
                                        'origin' : 'M',
                                        'active' : True,
                                        'source_type' : 'C',
                                        'discovery_date': datetime(2003, 8, 1, 0),
                                        'num_obs': '334',
                                        'arc_length': '5528',
                                        'not_seen' :  6.75,
                                        'orbit_rms' : 0.60,
                                        'update_time' : datetime(2018, 9, 19, 0),
                                        'updated' : True
                                    }

        self.expected_mulepoch_Mar18_params = {
                                        'elements_type': 'MPC_COMET',
                                        'argofperih': '283.56217',
                                        'longascnode' : '87.66076',
                                        'eccentricity' : '0.3591386',
                                        'epochofel': datetime(2018, 3, 23, 0),
                                        'meandist' : None,
                                        'orbinc' : '7.64150',
                                        'meananom': None,
                                        'perihdist' : '2.4544160',
                                        'epochofperih': datetime(2018, 8, 26, 0, 59, 55, int(0.968*1e6)),
                                        'slope': '4.0',
                                        'origin' : 'M',
                                        'active' : True,
                                        'source_type' : 'C',
                                        'discovery_date': datetime(2003, 8, 1, 0),
                                        'num_obs': '334',
                                        'arc_length': '5528',
                                        'not_seen' : -216.87383101851853,
                                        'orbit_rms' : 0.60,
                                        'update_time' : datetime(2018, 9, 19, 0),
                                        'updated' : True
                                    }
        self.maxDiff = None

    @patch('core.views.datetime', MockDateTime)
    def test_clean_2014UR(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        params = clean_mpcorbit(self.test_elements)

        self.assertEqual(self.expected_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_2014UR_no_arclength(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        new_test_elements = self.test_elements
        del new_test_elements['arc length']

        params = clean_mpcorbit(new_test_elements)

        self.assertEqual(self.expected_params, params)

    def test_bad_not_seen(self):

        new_test_elements = self.test_elements
        new_test_elements['last observation date used'] = 'Wibble'
        params = clean_mpcorbit(new_test_elements)

        new_expected_params = self.expected_params
        new_expected_params['not_seen'] = None
        new_expected_params['update_time'] = None
        self.assertEqual(new_expected_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_bad_discovery_date(self):

        MockDateTime.change_datetime(2015, 10, 14, 12, 0, 0)
        new_test_elements = self.test_elements
        new_test_elements['first observation date used'] = 'Wibble'
        params = clean_mpcorbit(new_test_elements)

        new_expected_params = self.expected_params
        new_expected_params['discovery_date'] = None
        self.assertEqual(new_expected_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_C_2016C2(self):

        MockDateTime.change_datetime(2016, 4, 24, 18, 0, 0)
        params = clean_mpcorbit(self.test_comet_elements)

        self.assertEqual(self.expected_comet_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_A_2017U7(self):

        MockDateTime.change_datetime(2018, 3, 5, 18, 0, 0)
        params = clean_mpcorbit(self.test_hyperbolic_elements)

        self.assertEqual(self.expected_hyperbolic_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_243P_postAug18_epoch(self):

        MockDateTime.change_datetime(2018, 9, 25, 18, 0, 0)
        params = clean_mpcorbit(self.test_comet_elements_2018Aug_epoch)

        self.assertEqual(self.expected_mulepoch_params, params)

    @patch('core.views.datetime', MockDateTime)
    def test_clean_243P_preMar18_epoch(self):

        MockDateTime.change_datetime(2018, 2, 14, 3, 1, 41)
        params = clean_mpcorbit(self.test_comet_elements_2018Mar_epoch)

        self.assertEqual(self.expected_mulepoch_Mar18_params, params)


class TestCreate_sourcemeasurement(TestCase):

    def setUp(self):
        # Read in MPC 80 column format observations lines from a static file
        # for testing purposes
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_WSAE9A6.dat'), 'r')
        self.test_obslines = test_fh.readlines()
        test_fh.close()

        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        self.test_body = Body.objects.create(**WSAE9A6_params)

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_N009ags.dat'), 'r')
        self.sat_test_obslines = test_fh.readlines()
        test_fh.close()

        N009ags_params = { 'provisional_name' : 'N009ags',
                         }

        self.sat_test_body = Body.objects.create(**N009ags_params)

        G07212_params = { 'provisional_name' : 'G07212',
                        }

        self.gbot_test_body = Body.objects.create(**G07212_params)

        self.maxDiff = None

    def test_create_nonLCO(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 27, 12, int(0.672*1e6)),
                            'obs_ra'    : 325.2828333333333,
                            'obs_dec'   : -10.8525,
                            'obs_mag'   : 21.8,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        source_measures = create_source_measurement(self.test_obslines[0])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_nonLCO_nocat(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 34,  8, int(0.256*1e6)),
                            'obs_ra'    : 325.28441666666663,
                            'obs_dec'   : -10.857111111111111,
                            'obs_mag'   : 20.9,
                            'filter'    : 'V',
                            'astrometric_catalog' : '',
                            'site_code' : 'G96'
                          }

        source_measures = create_source_measurement(self.test_obslines[1])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_nonLCO_nomag(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : ' ',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 5, 41,  6, int(0.432*1e6)),
                            'obs_ra'    : 325.28599999999994,
                            'obs_dec'   : -10.861583333333332,
                            'obs_mag'   : None,
                            'filter'    : 'V',
                            'astrometric_catalog' : 'UCAC-4',
                            'site_code' : 'G96'
                          }

        source_measures = create_source_measurement(self.test_obslines[2])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_nonLCO_flags(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 9, 54, 16, int(0.416*1e6)),
                            'obs_ra'    : 325.34804166666663,
                            'obs_dec'   : -11.01686111111111,
                            'obs_mag'   : 20.9,
                            'filter'    : 'R',
                            'astrometric_catalog' : 'PPMXL',
                            'site_code' : '474'
                          }

        source_measures = create_source_measurement(self.test_obslines[3])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_blankline(self):

        source_measures = create_source_measurement(self.test_obslines[4])

        self.assertEqual([], source_measures)

    def test_create_LCO_stack(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : 'K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 23, 24, 46, int(0.4832*1e6)),
                            'obs_ra'    : 325.540625,
                            'obs_dec'   : -11.536666666666667,
                            'obs_mag'   : 21.4,
                            'filter'    : 'R',
                            'astrometric_catalog' : '',
                            'site_code' : 'K93'
                          }

        source_measures = create_source_measurement(self.test_obslines[5])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.STACK_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_LCO_flagI(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : 'I',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 23, 31, 40, int(0.08*1e6)),
                            'obs_ra'    : 325.54225,
                            'obs_dec'   : -11.541111111111112,
                            'obs_mag'   : 21.6,
                            'filter'    : 'R',
                            'astrometric_catalog' : '',
                            'site_code' : 'K93'
                          }

        source_measures = create_source_measurement(self.test_obslines[6])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.SINGLE_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_LCO_flagI_and_discovery(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : '*,I',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 23, 31, 40, int(0.08*1e6)),
                            'obs_ra'    : 325.54225,
                            'obs_dec'   : -11.541111111111112,
                            'obs_mag'   : 21.6,
                            'filter'    : 'R',
                            'astrometric_catalog' : '',
                            'site_code' : 'K93'
                          }

        test_obsline = self.test_obslines[6].replace('6 IC', '6*IC')
        source_measures = create_source_measurement(test_obsline)
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.SINGLE_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_LCO_flagK_and_discovery(self):
        expected_params = { 'body'  : 'WSAE9A6',
                            'flags' : '*,K',
                            'obs_type'  : 'C',
                            'obs_date'  : datetime(2015, 9, 20, 23, 24, 46, int(0.4832*1e6)),
                            'obs_ra'    : 325.540625,
                            'obs_dec'   : -11.536666666666667,
                            'obs_mag'   : 21.4,
                            'filter'    : 'R',
                            'astrometric_catalog' : '',
                            'site_code' : 'K93'
                          }

        test_obsline = self.test_obslines[5].replace('6 KC', '6*KC')
        source_measures = create_source_measurement(test_obsline)
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.SINGLE_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_satellite(self):
        expected_params = { 'body'  : 'N009ags',
                            'flags' : '*',
                            'obs_type'  : 'S',
                            'obs_date'  : datetime(2016, 2, 8, 18, 15, 30, int(0.528*1e6)),
                            'obs_ra'    : 228.56833333333333,
                            'obs_dec'   : -9.775,
                            'obs_mag'   : 19.0,
                            'filter'    : 'R',
                            'astrometric_catalog' : '2MASS',
                            'site_code' : 'C51',
                          }

        expected_extrainfo = '     N009ags  s2016 02 08.76077 1 - 3484.5127 - 5749.6261 - 1405.6769   NEOCPC51'

        source_measures = create_source_measurement(self.sat_test_obslines[0:2])
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.SATELLITE_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_extrainfo, source_measure.frame.extrainfo)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)

    def test_create_non_existant_body(self):

        source_measures = create_source_measurement(self.test_obslines[3].replace('WSAE9A6', 'FOOBAR'))

        self.assertEqual([], source_measures)

    def test_create_whole_file(self):

        source_measures = create_source_measurement(self.test_obslines)
        source_measure = source_measures[0]

        sources = SourceMeasurement.objects.filter(body=self.test_body)
        nonLCO_frames = Frame.objects.filter(frametype=Frame.NONLCO_FRAMETYPE)
        LCO_frames = Frame.objects.filter(frametype__in=[Frame.SINGLE_FRAMETYPE, Frame.STACK_FRAMETYPE])

        self.assertEqual(6, len(sources))
        self.assertEqual(4, len(nonLCO_frames))
        self.assertEqual(2, len(LCO_frames))

    def test_create_duplicates(self):

        source_measures = create_source_measurement(self.test_obslines)
        source_measure = source_measures[0]
        source_measure2 = create_source_measurement(self.test_obslines)

        sources = SourceMeasurement.objects.filter(body=self.test_body)
        nonLCO_frames = Frame.objects.filter(frametype=Frame.NONLCO_FRAMETYPE)
        LCO_frames = Frame.objects.filter(frametype__in=[Frame.SINGLE_FRAMETYPE, Frame.STACK_FRAMETYPE])

        self.assertEqual(6, len(sources))
        self.assertEqual(4, len(nonLCO_frames))
        self.assertEqual(2, len(LCO_frames))

    def test_create_with_trailing_space(self):

        expected_params = { 'body' : 'G07212',
                            'flags' : "'",
                            'filter' : 'G',
                            'obs_date' : datetime(2017, 11, 2, 4, 10, 16, int(0.32*1e6)),
                            'site_code' : '309',
                            'obs_ra' : 48.408025,
                            'obs_dec'   : 19.463075,
                            'obs_mag'   : 21.4,
                          }

        test_obslines = u"     G07212  'C2017 11 02.17380 03 13 37.926+19 27 47.07         21.4 GUNEOCP309"

        source_measures = create_source_measurement(test_obslines)
        self.assertIsNot(source_measures, False)
        source_measure = source_measures[0]

        self.assertEqual(SourceMeasurement, type(source_measure))
        self.assertEqual(Body, type(source_measure.body))
        self.assertEqual(expected_params['body'], source_measure.body.current_name())
        self.assertEqual(expected_params['filter'], source_measure.frame.filter)
        self.assertEqual(Frame.NONLCO_FRAMETYPE, source_measure.frame.frametype)
        self.assertEqual(expected_params['obs_date'], source_measure.frame.midpoint)
        self.assertEqual(expected_params['site_code'], source_measure.frame.sitecode)
        self.assertAlmostEqual(expected_params['obs_ra'], source_measure.obs_ra, 7)
        self.assertAlmostEqual(expected_params['obs_dec'], source_measure.obs_dec, 7)
        self.assertEqual(expected_params['obs_mag'], source_measure.obs_mag)
        self.assertEqual(expected_params['flags'], source_measure.flags)
        self.assertEqual(None, source_measure.err_obs_ra)
        self.assertEqual(None, source_measure.err_obs_dec)
        self.assertEqual(None, source_measure.err_obs_mag)


class TestFrames(TestCase):
    def setUp(self):
        # Read in MPC 80 column format observations lines from a static file
        # for testing purposes
        test_fh = open(os.path.join('astrometrics', 'tests', 'test_multiframe.dat'), 'r')
        self.test_obslines = test_fh.readlines()
        test_fh.close()

        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        self.test_body = Body.objects.create(**WSAE9A6_params)

        WV2997A_params = { 'provisional_name' : 'WV2997A',
                         }
        self.test_body2 = Body.objects.create(**WV2997A_params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)
        # Create test blocks
        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2015-09-20 13:00:00',
                         'block_end'   : '2015-09-21 03:00:00',
                         'tracking_number' : '00001',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock,
                         'block_start' : '2015-09-20 13:00:00',
                         'block_end'   : '2015-09-21 03:00:00',
                         'request_number' : '00001',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP',
                         'block_start' : '2017-12-11 13:00:00',
                         'block_end'   : '2017-12-12 03:00:00',
                         'tracking_number' : '522289',
                         'active'   : True
                       }
        self.test_sblock_0m4 = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '0m4',
                         'site'     : 'CPT',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock_0m4,
                         'block_start' : '2017-12-11 13:00:00',
                         'block_end'   : '2017-12-12 03:00:00',
                         'request_number' : '522289',
                         'num_exposures' : 5,
                         'exp_length' : 145.0,
                         'active'   : True
                       }
        self.test_block_0m4 = Block.objects.create(**block_params)

        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : 'TEMP_GROUP_spectra',
                         'block_start' : '2017-12-11 13:00:00',
                         'block_end'   : '2017-12-12 03:00:00',
                         'tracking_number' : '1509481',
                         'active'   : True
                       }
        self.test_sblock_spec = SuperBlock.objects.create(**sblock_params)
        block_params = { 'obstype' : Block.OPT_SPECTRA,
                         'telclass' : '2m0',
                         'site'     : 'coj',
                         'body'     : self.test_body,
                         'superblock' : self.test_sblock_spec,
                         'block_start' : '2017-12-11 13:00:00',
                         'block_end'   : '2017-12-12 03:00:00',
                         'request_number' : '1509481',
                         'num_exposures' : 1,
                         'exp_length' : 1800.0,
                         'active'   : True
                       }
        self.test_spec_block = Block.objects.create(**block_params)

    def test_add_frame(self):
        params = parse_mpcobs(self.test_obslines[-1])
        resp = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K93')
        self.assertEqual(1, frames.count())

    def test_add_frames(self):
        for line in self.test_obslines:
            params = parse_mpcobs(line)
            resp = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K93')
        self.assertEqual(3, frames.count())
        # Did the block get Added
        frames = Frame.objects.filter(sitecode='K93', block__isnull=False)
        # Although there are 4 sources in the file 2 are in the same frame
        self.assertEqual(3, frames.count())

    def test_ingest_frames_block(self):
        params = {
                        "DATE_OBS": "2016-06-01T09:43:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00.fits",
                        "EXPTIME" : "30",
                        "GROUPID"   : "TEMP"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME'])/2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, None)

    def test_ingest_frames_block_no_fits_extn(self):
        params = {
                        "DATE_OBS": "2016-06-01T09:43:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00",
                        "EXPTIME" : "30",
                        "GROUPID"   : "TEMP"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME'])/2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].filename, params['ORIGNAME']+'.fits')
        self.assertEqual(frames[0].midpoint, midpoint)

    def test_ingest_frames_block_fwhm(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00.fits",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))

    def test_ingest_frames_block_bad_fwhm(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00.fits",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "L1FWHM"   : "NaN"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SINGLE_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, None)

    def test_ingest_frames_banzai_ql(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e11.fits",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 11,
                        "L1FWHM"   : "2.42433",
                        "UTSTOP"   : "00:01:53.067"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_QL_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].filename, params['ORIGNAME'])

    def test_ingest_frames_banzai_red(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433",
                        "CONFMODE" : "full_frame",
                        "UTSTOP"   : "00:01:53.067"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))
        self.assertEqual(frames[0].extrainfo, None)

    def test_ingest_frames_2x2_red(self):
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433",
                        "CONFMODE" : "central_2k_2x2",
                        "UTSTOP"   : "00:01:53.067"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))
        self.assertEqual(frames[0].extrainfo, params['CONFMODE'])

    def test_ingest_frames_banzai_red_badexptime(self):
        """Test that we preferentially take midpoint from UTSTOP over EXPTIME"""
        params = {
                        "DATE_OBS": "2015-12-31T23:59:28.067",
                        "ENCID": "doma",
                        "SITEID": "cpt",
                        "TELID": "1m0a",
                        "FILTER": "R",
                        "INSTRUME" : "kb70",
                        "ORIGNAME" : "cpt1m010-kb70-20150420-0001-e00",
                        "EXPTIME"  : "200",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433",
                        "UTSTOP"   : "00:00:54.067"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block)
        frames = Frame.objects.filter(sitecode='K91')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'K91')
        self.assertEqual(frames[0].quality, 'ABORTED')
        self.assertNotEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_cpt_0m4_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "cpt",
                        "TELID": "0m4a",
                        "FILTER": "R",
                        "INSTRUME" : "kb96",
                        "ORIGNAME" : "cpt0m407-kb96-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='L09')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'L09')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_elp_0m4_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "elp",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb80",
                        "ORIGNAME" : "elp0m407-kb96-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='V38')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'V38')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_tfn_0m4n1_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "tfn",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb29",
                        "ORIGNAME" : "tfn0m414-kb29-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='Z21')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'Z21')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_tfn_0m4n2_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-11T23:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "tfn",
                        "TELID": "0m4b",
                        "FILTER": "w",
                        "INSTRUME" : "kb88",
                        "ORIGNAME" : "tfn0m410-kb88-20171211-0001-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='Z17')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'Z17')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_lsc_0m4n1_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-12T03:59:28.067",
                        "ENCID": "aqwa",
                        "SITEID": "lsc",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb95",
                        "ORIGNAME" : "lsc0m409-kb95-20171211-0121-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='W89')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'W89')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))

    def test_ingest_frames_lsc_0m4n2_banzai_red(self):
        params = {
                        "DATE_OBS": "2017-12-12T03:59:28.067",
                        "ENCID": "aqwb",
                        "SITEID": "lsc",
                        "TELID": "0m4a",
                        "FILTER": "w",
                        "INSTRUME" : "kb26",
                        "ORIGNAME" : "lsc0m412-kb26-20171211-0041-e00",
                        "EXPTIME"  : "145",
                        "GROUPID"  : "TEMP",
                        "RLEVEL"   : 91,
                        "CONFMODE" : 'default',
                        "L1FWHM"   : "2.42433"
                }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_block_0m4)
        frames = Frame.objects.filter(sitecode='W79')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.BANZAI_RED_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'W79')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e91.fits'))
        self.assertEqual(frames[0].extrainfo, None)

    def test_ingest_frames_spectro_spectrum(self):
        params = {
                    "DATE_OBS": "2018-05-09T13:28:52.383",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "SPECTRUM",
                    "FILTER" : "air     ",
                    "APERTYPE" : "SLIT    ",
                    "APERLEN" : 30.0,
                    "APERWID" : 2.0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0017-e00",
                    "EXPTIME"  : "1800.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                    "UTSTOP"   : "13:59:13.383"

                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0x2.0AS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e00.fits'))

    def test_ingest_frames_spectro_spectrum_realistic_exptime(self):
        """ In the wild, FLOYDS exposure times vary by 10s of miliseconds"""
        params = {
                    "DATE_OBS": "2018-05-09T13:28:52.383",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "SPECTRUM",
                    "FILTER" : "air     ",
                    "APERTYPE" : "SLIT    ",
                    "APERLEN" : 30.0,
                    "APERWID" : 2.0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0017-e00",
                    "EXPTIME"  : "1800.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                    "UTSTOP"   : "13:59:13.327"

                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        expdif = frames[0].midpoint-midpoint
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertNotEqual(frames[0].midpoint, midpoint)
        self.assertAlmostEqual(expdif.total_seconds(), 0.0, places=1)
        self.assertEqual(frames[0].filter, 'SLIT_30.0x2.0AS')
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('e00', 'e00.fits'))

    def test_ingest_frames_spectro_arc(self):
        params = {
                    "DATE_OBS": "2018-05-09T11:44:33.898",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "ARC",
                    "FILTER" : "air     ",
                    "APERTYPE" : "SLIT    ",
                    "APERLEN" : 30.0,
                    "APERWID" : 2.0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0006-a00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0x2.0AS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('a00', 'a00.fits'))

    def test_ingest_frames_spectro_lampflat(self):
        params = {
                    "DATE_OBS": "2018-05-09T11:42:18.352",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "LAMPFLAT",
                    "FILTER" : "air",
                    "APERTYPE" : "SLIT",
                    "APERLEN" : 30.0,
                    "APERWID" : 2.0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0005-w00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0x2.0AS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('w00', 'w00.fits'))

    def test_ingest_frames_spectro_lampflat_badslit(self):
        params = {
                    "DATE_OBS": "2018-05-09T13:28:52.383",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "LAMPFLAT",
                    "FILTER" : "air",
                    "APERTYPE" : "SLIT",
                    "APERLEN" : 30.0,
                    "APERWID" : '',
                    "RLEVEL"  : 0,
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0017-w00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0xUNKAS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('w00', 'w00.fits'))

    def test_ingest_frames_spectro_lampflat_badslit2(self):
        params = {
                    "DATE_OBS": "2018-05-09T13:28:52.383",
                    "ENCID": "clma",
                    "SITEID" : "coj",
                    "TELID" : "2m0a",
                    "OBSTYPE" : "LAMPFLAT",
                    "FILTER" : "air",
                    "APERTYPE" : "SLIT",
                    "APERLEN" : 30.0,
                    "APERWID" : 'UNKNOWN',
                    "INSTRUME" : "en05",
                    "ORIGNAME" : "coj2m002-en05-20180509-0017-w00",
                    "EXPTIME"  : "60.0000",
                    "GROUPID"  : "4709_E10-20180509_spectra",
                  }
        midpoint = datetime.strptime(params['DATE_OBS'], "%Y-%m-%dT%H:%M:%S.%f")
        midpoint += timedelta(seconds=float(params['EXPTIME']) / 2.0)

        frame = create_frame(params, self.test_spec_block)
        frames = Frame.objects.filter(sitecode='E10')
        self.assertEqual(1, frames.count())
        self.assertEqual(frames[0].frametype, Frame.SPECTRUM_FRAMETYPE)
        self.assertEqual(frames[0].sitecode, 'E10')
        self.assertEqual(frames[0].midpoint, midpoint)
        self.assertEqual(frames[0].filter, 'SLIT_30.0xUNKAS')
#        self.assertEqual(frames[0].fwhm, float(params['L1FWHM']))
        self.assertEqual(frames[0].instrument, params['INSTRUME'])
        self.assertEqual(frames[0].filename, params['ORIGNAME'].replace('w00', 'w00.fits'))

    def test_add_source_measurements(self):
        # Test we don't get duplicate frames when adding new source measurements
        # if the sources are in the same frame
        resp = create_source_measurement(self.test_obslines, self.test_block)
        frames = Frame.objects.filter(sitecode='K93', block__isnull=False)
        self.assertEqual(3, frames.count())

    def test_add_source_measurements_twice(self):
        # Test we don't get duplicate frames when adding new source measurements
        # if the sources are in the same frame
        resp = create_source_measurement(self.test_obslines, self.test_block)
        # And we forgot that we've already done this, so we do it again
        resp = create_source_measurement(self.test_obslines, self.test_block)
        frames = Frame.objects.filter(sitecode='K93', block__isnull=False)
        # We should get the same number in the previous test,
        # i.e. on the second run the frames are not created
        self.assertEqual(3, frames.count())


@patch('core.views.datetime', MockDateTime)
@patch('astrometrics.time_subs.datetime', MockDateTime)
class TestCleanCrossid(TestCase):

    def setUp(self):
        MockDateTime.change_datetime(2015, 11, 5, 18, 0, 0)

    def test_regular_asteroid(self):
        crossid = [u'P10p9py', u'2015 VV1', '', u'(Nov. 5.30 UT)']
        expected_params = { 'active' : False,
                            'name' : '2015 VV1',
                            'source_type' : 'A',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_NEO_recent_confirm(self):
        crossid = [u'WV82468', u'2015 VB2', u'MPEC 2015-V51', u'(Nov. 5.60 UT)']
        expected_params = { 'active' : True,
                            'name' : '2015 VB2',
                            'source_type' : 'N',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_NEO_older_confirm(self):
        crossid = [u'P10o0Ha', u'2015 SE20', u'MPEC 2015-T29', u'(Oct. 8.59 UT)']
        expected_params = { 'active' : False,
                            'name' : '2015 SE20',
                            'source_type' : 'N',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_did_not_exist(self):
        crossid = [u'WTB842B', 'doesnotexist', '', u'(Oct. 9.19 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'X',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_not_confirmed(self):
        crossid = [u'P10oYZI', 'wasnotconfirmed', '', u'(Nov. 4.81 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'U',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_not_interesting(self):
        crossid = [u'P10oYZI', '', '', u'(Nov. 4.81 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'W',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_was_minor_planet(self):
        crossid = [u'A10422t', 'wasnotminorplanet', '', u'(Sept. 20.89 UT)']
        expected_params = { 'active' : False,
                            'name' : '',
                            'source_type' : 'J',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_cbet_recent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'CBET 5432', u'(Nov. 5.49 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_cbet_notrecent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'CBET 5432', u'(Nov. 1.49 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_iauc_recent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'IAUC-', u'(Nov. 5.49 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_iauc_notrecent(self):
        crossid = [u'WV2B5A8', u'C/2015 V2', u'IAUC-', u'(Nov. 1.49 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 V2',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_asteroid_number(self):
        crossid = [u'LM02L2J', u'C/2015 TQ209', u'IAUC 2015-', u'(Oct. 24.07 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 TQ209',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_mpec_recent(self):
        crossid = [u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Nov. 3.63 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_mpec_notrecent(self):
        crossid = [u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Oct. 18.63 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_numbered(self):
        MockDateTime.change_datetime(2018, 9, 19, 0, 30, 0)

        crossid = ['ZS9E891 ', '0046P  ', '', '(Sept. 16.62 UT)']
        expected_params = { 'active' : True,
                            'name' : '46P',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_comet_numbered_past_time(self):
        MockDateTime.change_datetime(2018, 9, 29, 0, 30, 0)

        crossid = ['ZS9E891 ', '0046P  ', '', '(Sept. 16.62 UT)']
        expected_params = { 'active' : False,
                            'name' : '46P',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_active_asteroid1(self):
        crossid = [u'ZC82561', u'A/2018 C2', u'MPEC 2018-E18', u'(Nov. 4.95 UT)']
        expected_params = { 'active' : True,
                            'name' : 'A/2018 C2',
                            'source_type' : 'A',
                            'source_subtype_1': 'A'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_hyperbolic_asteroid2(self):
        crossid = [u'P10EwQh', u'I/2017 U7', u'MPEC 2018-E17', u'(Nov. 4.94 UT)']
        expected_params = { 'active' : True,
                            'name' : 'I/2017 U7',
                            'source_type' : 'A',
                            'source_subtype_1': 'H'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_new_year_switchover(self):
        MockDateTime.change_datetime(2016, 1, 1, 0, 30, 0)
        crossid = [u'NM0015a', u'C/2015 X8', u'MPEC 2015-Y20', u'(Oct. 18.63 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2015 X8',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_bad_date(self):
        MockDateTime.change_datetime(2016, 3, 1, 0, 30, 0)
        crossid = [u'P10sKEk', u'2016 CP264', '', u'(Feb. 30.00 UT)']
        expected_params = { 'active' : False,
                            'name' : '2016 CP264',
                            'source_type' : 'A',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_extra_spaces(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)
        crossid = [u'P10tmAL ', u'2013 AM76', '', u'(Mar.  9.97 UT)']
        expected_params = { 'active' : False,
                            'name' : '2013 AM76',
                            'source_type' : 'A',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_moon(self):
        MockDateTime.change_datetime(2016, 4, 8, 0, 30, 0)
        crossid = [u'P10tmAL ', u'Mars II', '', u'(Mar.  9.97 UT)']
        expected_params = { 'active' : False,
                            'name' : 'Mars II',
                            'source_type' : 'M',
                            'source_subtype_1': 'P4'
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_newstyle_comet_numbered_pre_time(self):
        MockDateTime.change_datetime(2020, 4, 9, 6, 30, 0)

        crossid = ['SWAN20A ', '58P', '', '(Apr. 9.13 UT)']
        expected_params = { 'active' : True,
                            'name' : '58P',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_newstyle_comet_numbered_post_time(self):
        MockDateTime.change_datetime(2020, 4, 19, 6, 30, 0)

        crossid = ['SWAN20A ', '58P', '', '(Apr. 9.13 UT)']
        expected_params = { 'active' : False,
                            'name' : '58P',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_newstyle_comet_unnumbered_pre_time_1(self):
        MockDateTime.change_datetime(2020, 4, 9, 0, 30, 0)

        crossid = ['P10XLLe ', 'C/2020 F6', '', '(Apr. 8.96 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2020 F6',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_newstyle_comet_unnumbered_post_time_1(self):
        MockDateTime.change_datetime(2020, 4, 12, 0, 0, 0)

        crossid = ['P10XLLe ', 'C/2020 F6', '', '(Apr. 8.96 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2020 F6',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_newstyle_comet_unnumbered_pre_time_2(self):
        MockDateTime.change_datetime(2020, 4, 8, 6, 30, 0)

        crossid = ['M60B7LC ', 'C/2020 F5', '', '(Apr. 8.11 UT)']
        expected_params = { 'active' : True,
                            'name' : 'C/2020 F5',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)

    def test_newstyle_comet_unnumbered_post_time_2(self):
        MockDateTime.change_datetime(2020, 4, 11, 2, 39, 0)

        crossid = ['M60B7LC ', 'C/2020 F5', '', '(Apr. 8.11 UT)']
        expected_params = { 'active' : False,
                            'name' : 'C/2020 F5',
                            'source_type' : 'C',
                            'source_subtype_1': ''
                          }

        params = clean_crossid(crossid)

        self.assertEqual(expected_params, params)



class TestSummarizeBlockEfficiency(TestCase):

    def setUp(self):
        # Initialise with a test body, three test proposals and several blocks.
        # The first proposal has two blocks (one observed, one not), the 2nd one
        # has a block scheduled but not observed and the third has no blocks
        # scheduled.
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
                    }
        self.body, created = Body.objects.get_or_create(**params)

    def test_proposal_with_scheduled_and_obs_blocks(self):
        proposal_params = { 'code'  : 'LCO2015A-009',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal = Proposal.objects.create(**proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : proposal,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'superblock' : test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        sblock_params2 = {
                         'body'     : self.body,
                         'proposal' : proposal,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'active'   : False,
                       }
        test_sblock2 = SuperBlock.objects.create(**sblock_params2)
        block_params2 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'superblock' : test_sblock2,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        test_block2 = Block.objects.create(**block_params2)

        expected_summary = [{ 'Not Observed': 1,
                              'Observed': 1,
                              'proposal': u'LCO2015A-009'}
                           ]

        summary = summarize_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_proposal_with_scheduled_blocks(self):
        proposal_params = { 'code'  : 'LCO2015B-005',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal = Proposal.objects.create(**proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : proposal,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'superblock' : test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        expected_summary = [{ 'Not Observed': 1,
                              'Observed': 0,
                              'proposal': u'LCO2015B-005'}
                           ]

        summary = summarize_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_multiple_proposals_with_scheduled_and_obs_blocks(self):
        proposal_params = { 'code'  : 'LCO2015A-009',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal1 = Proposal.objects.create(**proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : proposal1,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'superblock' : test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        sblock_params2 = {
                         'body'     : self.body,
                         'proposal' : proposal1,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'tracking_number' : '00043',
                         'active'   : False,
                       }
        test_sblock2 = SuperBlock.objects.create(**sblock_params2)
        block_params2 = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'superblock' : test_sblock2,
                         'block_start' : '2015-04-20 03:00:00',
                         'block_end'   : '2015-04-20 13:00:00',
                         'request_number' : '10043',
                         'num_exposures' : 7,
                         'exp_length' : 30.0,
                         'active'   : False,
                         'num_observed' : 1,
                         'reported' : True
                       }
        test_block2 = Block.objects.create(**block_params2)

        proposal_params = { 'code'  : 'LCO2015B-005',
                            'title' : 'LCOGT NEO Follow-up Network'
                          }
        proposal2 = Proposal.objects.create(**proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body,
                         'proposal' : proposal2,
                         'groupid'  : self.body.current_name() + '_CPT-20150420',
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'CPT',
                         'body'     : self.body,
                         'superblock' : test_sblock,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'request_number' : '10042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        test_block = Block.objects.create(**block_params)

        expected_summary = [
                             { 'Not Observed': 1,
                               'Observed': 0,
                               'proposal': u'LCO2015B-005'},
                            { 'Not Observed': 1,
                               'Observed': 1,
                               'proposal': u'LCO2015A-009'}

                           ]

        summary = summarize_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_proposal_with_no_blocks(self):
        proposal_params = { 'code'  : 'LCO2016A-021',
                            'title' : 'LCOGT NEO Follow-up Network (16A)'
                          }
        proposal = Proposal.objects.create(**proposal_params)

        expected_summary = []

        summary = summarize_block_efficiency()

        self.assertEqual(expected_summary, summary)

    def test_no_proposals(self):
        expected_summary = []

        summary = summarize_block_efficiency()

        self.assertEqual(expected_summary, summary)


class TestCheckCatalogAndRefitNew(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')

#        self.phot_tests_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
#        self.test_catalog = os.path.join(self.phot_tests_dir, 'oracdr_test_catalog.fits')
        self.configs_dir = os.path.abspath(os.path.join('photometrics', 'configs'))

        self.debug_print = False

        original_test_banzai_fits = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        original_test_cat_bad_wcs = os.path.abspath(os.path.join('photometrics', 'tests', 'oracdr_test_catalog.fits'))
        self.test_cat_good_wcs_not_BANZAI = os.path.abspath(os.path.join('photometrics', 'tests', 'ldac_test_catalog.fits'))
        self.test_fits_e10 = os.path.abspath(os.path.join('photometrics', 'tests', 'example-sbig-e10.fits'))

        self.test_banzai_fits = os.path.abspath(os.path.join(self.temp_dir, 'banzai_test_frame.fits'))
        self.test_cat_bad_wcs = os.path.abspath(os.path.join(self.temp_dir, 'oracdr_test_catalog.fits'))

        self.test_externscamp_headfile = os.path.join('photometrics', 'tests', 'example_externcat_scamp.head')
        self.test_externcat_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp.xml')
        self.test_externscamp_TPV_headfile = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.head')
        self.test_externcat_TPV_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.xml')

        shutil.copyfile(original_test_banzai_fits, self.test_banzai_fits)
        shutil.copyfile(original_test_cat_bad_wcs, self.test_cat_bad_wcs)

        body_params = {     'provisional_name': 'P10w5z5',
                            'origin': 'M',
                            'source_type': 'U',
                            'elements_type': 'MPC Minor Planet',
                            'active': False,
                            'epochofel': '2016-07-11 00:00:00',
                            'orbinc': 6.35992,
                            'longascnode': 108.82267,
                            'argofperih': 202.15361,
                            'eccentricity': 0.384586,
                            'meandist': 2.3057577,
                            'meananom': 352.55523,
                            'abs_mag': 21.3,
                            'slope': 0.15,
                        }
        self.test_body, created = Body.objects.get_or_create(**body_params)

        proposal_params = { 'code': 'test',
                            'title': 'test',
                            'pi': 'sgreenstreet@lcogt.net',
                            'tag': 'LCOGT',
                            'active': True
                          }
        self.test_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        sblock_params = {
                            'body': self.test_body,
                            'proposal': self.test_proposal,
                            'groupid': 'P10w5z5_cpt_20160801',
                            'block_start': datetime(2016, 8, 1, 17),
                            'block_end': datetime(2016, 8, 2, 4),
                            'tracking_number': '0013',
                            'active': False,
                        }
        self.test_sblock, created = SuperBlock.objects.get_or_create(**sblock_params)
        block_params = {    'telclass': '1m0',
                            'site': 'K92',
                            'body': self.test_body,
                            'superblock': self.test_sblock,
                            'block_start': datetime(2016, 8, 1, 17),
                            'block_end': datetime(2016, 8, 2, 4),
                            'request_number': '1013',
                            'num_exposures': 5,
                            'exp_length': 225.0,
                            'num_observed': 1,
                            'when_observed': datetime(2016, 8, 2, 2, 15, 0),
                            'active': False,
                            'reported': True,
                            'when_reported': datetime(2016, 8, 2, 4, 44, 0)
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)

        frame_params = {    'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'banzai_test_frame.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.390,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.temp_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.temp_dir)
            try:
                os.rmdir(self.temp_dir)
                if self.debug_print:
                    print("Removed", self.temp_dir)
            except OSError:
                print("Error removing temporary test directory", self.temp_dir)

    def test_check_catalog_and_refit_new_good(self):

        expected_status_and_num_frames = (os.path.abspath(os.path.join(self.temp_dir, 'banzai_test_frame_ldac.fits')), 1)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_bad_astrometric_fit(self):

        expected_status_and_num_frames = (-1, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_cat_bad_wcs)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_cattype_not_BANZAI(self):

        expected_status_and_num_frames = (-99, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_cat_good_wcs_not_BANZAI)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_BANZAI_catalog_found(self):

        expected_status_and_num_frames = (os.path.abspath(os.path.join(self.temp_dir, 'banzai_test_frame.fits'.replace('.fits', '_ldac.fits'))), 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_matching_image_file_found(self):

        expected_fits_file = self.test_banzai_fits.replace('.fits', '.fits[SCI]')

        fits_file = find_matching_image_file(self.test_banzai_fits)

        self.assertEqual(expected_fits_file, fits_file)

    def test_matching_image_file_not_found(self):

        expected_fits_file = None

        fits_file = find_matching_image_file(self.test_banzai_fits.replace('neox', 'neoxs'))

        self.assertEqual(expected_fits_file, fits_file)

        expected_fits_file = None

        fits_file = find_matching_image_file(self.test_banzai_fits.replace('frame.fits', 'frames.fits'))

        self.assertEqual(expected_fits_file, fits_file)

    def test_matching_image_file_not_found_check_catalog_and_refit_new(self):

        expected_status_and_num_frames = (-1, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('neox', 'neoxs'))

        self.assertEqual(expected_status_and_num_frames, status)

        expected_status_and_num_frames = (-1, 0)

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('frame.fits', 'frames.fits'))

        self.assertEqual(expected_status_and_num_frames, status)

    def test_run_sextractor_good(self):

        expected_status_and_catalog = (0, os.path.join(self.temp_dir, os.path.basename(self.test_banzai_fits).replace('.fits', '_ldac.fits')))

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        self.assertEqual(expected_status_and_catalog, (status, new_ldac_catalog))

    def test_run_sextractor_bad(self):

        expected_status_and_catalog = (1, -4)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_cat_bad_wcs)

        self.assertEqual(expected_status_and_catalog, (status, new_ldac_catalog))

    @patch('core.views.run_sextractor_make_catalog', mock_run_sextractor_make_catalog)
    def test_cannot_run_sextractor(self):

        expected_num_new_frames_created = 0

        status, num_new_frames_created = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(-4, status)
        self.assertEqual(expected_num_new_frames_created, num_new_frames_created)

    def test_find_block_for_frame_good(self):

        expected_block = self.test_block

        block = find_block_for_frame(self.test_banzai_fits)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_multiple_frames(self):

        frame_params_2 = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'banzai_test_frame.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.380,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame_2, created = Frame.objects.get_or_create(**frame_params_2)

        expected_block = None

        block = find_block_for_frame(self.test_banzai_fits)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_DNE_multiple_frames(self):

        frame_params = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'example-sbig-e00.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.390,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

        frame_params_2 = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'example-sbig-e00.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.380,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame_2, created = Frame.objects.get_or_create(**frame_params_2)

        expected_block = None

        block = find_block_for_frame(self.test_fits_e10)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_DNE(self):

        expected_block = None

        block = find_block_for_frame(self.test_fits_e10)

        self.assertEqual(expected_block, block)

    def test_find_block_for_frame_check_catalog_and_refit_new(self):

        expected_status_and_num_frames = (-3, 0)

        block = Block.objects.last()
        block.delete()

        status = check_catalog_and_refit(self.configs_dir, self.temp_dir, self.test_banzai_fits)

        self.assertEqual(expected_status_and_num_frames, status)

    def test_make_new_catalog_entry_good(self):

        expected_num_new_frames = 1

        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        header = get_catalog_header(fits_header, cattype)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

    def test_make_new_catalog_entry_multiple_frames(self):

        frame_params_2 = {  'sitecode': 'K92',
                            'instrument': 'kb76',
                            'filter': 'w',
                            'filename': 'banzai_test_frame_ldac.fits',
                            'exptime': 225.0,
                            'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                            'block': self.test_block,
                            'zeropoint': -99,
                            'zeropoint_err': -99,
                            'fwhm': 2.380,
                            'frametype': 0,
                            'rms_of_fit': 0.3,
                            'nstars_in_fit': -4,
                        }
        self.test_frame_2, created = Frame.objects.get_or_create(**frame_params_2)

        expected_num_new_frames = 0

        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        header = get_catalog_header(fits_header, cattype)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        self.assertEqual(expected_num_new_frames, num_new_frames)

    def test_make_new_catalog_entry_not_needed(self):

        expected_num_new_frames = 0

        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        header = get_catalog_header(fits_header, cattype)

        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        self.assertEqual(expected_num_new_frames, num_new_frames)

    def test_make_new_catalog_entry_gaiadr2(self):
        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        fits_file_output = self.test_banzai_fits.replace('_frame', '_frame_new')
        status, new_header = updateFITSWCS(self.test_banzai_fits, self.test_externscamp_headfile, self.test_externcat_xml, fits_file_output)
        header = get_catalog_header(new_header, cattype)
        new_wcs = WCS(new_header)
        expected_wcs = new_wcs.wcs
        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        frames = Frame.objects.filter(frametype=Frame.BANZAI_LDAC_CATALOG)
        self.assertEqual(1, frames.count())
        frame = frames[0]
        self.assertEqual('GAIA-DR2', frame.astrometric_catalog)
        self.assertEqual(' ', frame.photometric_catalog)
        self.assertEqual(0.30818, frame.rms_of_fit)
        self.assertEqual(23, frame.nstars_in_fit)

        frame_wcs = frame.wcs.wcs
        assert_allclose(expected_wcs.crval, frame_wcs.crval, rtol=1e-8)
        assert_allclose(expected_wcs.crpix, frame_wcs.crpix, rtol=1e-8)
        assert_allclose(expected_wcs.cd, frame_wcs.cd, rtol=1e-8)

    def test_make_new_catalog_entry_gaiadr2_tpv(self):
        fits_header, junk_table, cattype = open_fits_catalog(self.test_banzai_fits, header_only=True)
        (status, new_ldac_catalog) = run_sextractor_make_catalog(self.configs_dir, self.temp_dir, self.test_banzai_fits.replace('.fits', '.fits[SCI]'))

        fits_file_output = self.test_banzai_fits.replace('_frame', '_frame_new')
        status, new_header = updateFITSWCS(self.test_banzai_fits, self.test_externscamp_TPV_headfile, self.test_externcat_TPV_xml, fits_file_output)
        header = get_catalog_header(new_header, cattype)
        new_wcs = WCS(new_header)
        expected_wcs = new_wcs.wcs
        num_new_frames = make_new_catalog_entry(new_ldac_catalog, header, self.test_block)

        frames = Frame.objects.filter(frametype=Frame.BANZAI_LDAC_CATALOG)
        self.assertEqual(1, frames.count())
        frame = frames[0]
        self.assertEqual('GAIA-DR2', frame.astrometric_catalog)
        self.assertEqual(' ', frame.photometric_catalog)
        self.assertAlmostEqual(0.327895, frame.rms_of_fit, 6)
        self.assertEqual(23, frame.nstars_in_fit)

        frame_wcs = frame.wcs.wcs
        assert_allclose(expected_wcs.crval, frame_wcs.crval, rtol=1e-8)
        assert_allclose(expected_wcs.crpix, frame_wcs.crpix, rtol=1e-8)
        assert_allclose(expected_wcs.cd, frame_wcs.cd, rtol=1e-8)


class TestUpdateCrossids(TestCase):

    @classmethod
    def setUpTestData(cls):
        params = {  'provisional_name' : 'LM05OFG',
                    'abs_mag'       : 24.7,
                    'slope'         : 0.15,
                    'epochofel'     : datetime(2016, 7, 31, 00, 0, 0),
                    'meananom'      :   8.5187,
                    'argofperih'    : 227.23234,
                    'longascnode'   :  57.83134,
                    'orbinc'        : 5.40829,
                    'eccentricity'  : 0.6914565,
                    'meandist'      : 2.8126642,
                    'source_type'   : 'N',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'G',
                    }
        cls.body, created = Body.objects.get_or_create(**params)

        des_dict = {'desig_type': 'C',
                    'value': params['provisional_name'],
                    'notes': 'Test_candidate',
                    'preferred': True,
                    }
        cls.body.save_physical_parameters(des_dict)

        params = {  'provisional_name': 'ZC82561',
                    'provisional_packed': None,
                    'origin': 'M',
                    'source_type': 'U',
                    'elements_type': None,
                    'active': False,
                    'fast_moving': False,
                    'urgency': None,
                    'epochofel': None,
                    'orbinc': None,
                    'longascnode': None,
                    'argofperih': None,
                    'eccentricity': None,
                    'meandist': None,
                    'meananom': None,
                    'perihdist': None,
                    'epochofperih': None,
                    'abs_mag': None,
                    'slope': None,
                    'score': None,
                    'discovery_date': None,
                    'num_obs': None,
                    'arc_length': None,
                    'not_seen': None,
                    'updated': False,
                    'ingest': datetime(2018, 5, 24, 16, 45, 42),
                    'update_time': None
                    }
        cls.blank_body, created = Body.objects.get_or_create(**params)

        des_dict['value'] = params['provisional_name']
        cls.blank_body.save_physical_parameters(des_dict)

        neo_proposal_params = { 'code'  : 'LCO2015B-005',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        cls.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

    def setUp(self):
        self.body.refresh_from_db()

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_crossids_update_designations_to_prov_des(self):
        expected_types = ['C', 'P']
        expected_desigs = ['LM05OFG', '2016 JD18']
        expected_names = list(zip(expected_types, expected_desigs))

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)
        names = Designations.objects.filter(body=body)

        for name in names:
            test_list = (name.desig_type, name.value)
            self.assertIn(test_list, expected_names)
            expected_names.remove(test_list)
        self.assertEqual(expected_names, [])

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_goldstone_is_not_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('G', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_arecibo_comet_is_not_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'C/2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.source_type = u'C'
        self.body.origin = u'A'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('C', body.source_type)
        self.assertEqual('A', body.origin)
        self.assertEqual('C/2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_crossids_update_designations_to_comet_des(self):
        expected_types = ['C', 'P']
        expected_desigs = ['LM05OFG', 'C/2016 JD18']
        expected_names = list(zip(expected_types, expected_desigs))

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'C/2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)
        names = Designations.objects.filter(body=body)

        for name in names:
            test_list = (name.desig_type, name.value)
            self.assertIn(test_list, expected_names)
            expected_names.remove(test_list)
        self.assertEqual(expected_names, [])

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_jointradar_neo_is_not_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.origin = u'R'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('R', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_old_mpc_neo_is_overridden(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 13, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.origin = u'M'
        self.assertEqual(True, self.body.active)
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_new_mpc_neo_is_not_overridden(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2016, 5, 11, 10, 40, 0)

        crossid_info = [u'LM05OFG', u'2016 JD18', u'MPEC 2016-J96', u'(May 9.64 UT)']

        self.body.origin = u'M'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('2016 JD18', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_artsat(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 9, 21, 10, 40, 0)

        crossid_info = [u'A10422t', 'wasnotminorplanet', '', u'(Sept. 20.89 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'A10422t'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('J', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('', body.name)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_hyperbolic_ast(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 9, 21, 10, 40, 0)

        crossid_info = [u'ZC99999', u'I/2018 C2', u'MPEC 2018-E18', u'(Mar. 4.95 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'ZC99999'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('A', body.source_type)
        self.assertEqual('H', body.source_subtype_1)
        self.assertEqual('M', body.origin)
        self.assertEqual('I/2018 C2', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_active_ast(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 9, 21, 10, 40, 0)

        crossid_info = [u'ZC99999', u'A/2018 C2', u'MPEC 2018-E18', u'(Mar. 4.95 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'ZC99999'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('A', body.source_type)
        self.assertEqual('A', body.source_subtype_1)
        self.assertEqual('M', body.origin)
        self.assertEqual('A/2018 C2', body.name)
        self.assertEqual('MPC_MINOR_PLANET', body.elements_type)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_moon(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 9, 21, 10, 40, 0)

        crossid_info = [u'ZC99999', u'Saturn XIV', '', u'(Mar. 4.95 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'ZC99999'
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('M', body.source_type)
        self.assertEqual('P6', body.source_subtype_1)
        self.assertEqual('M', body.origin)
        self.assertEqual('Saturn XIV', body.name)
        self.assertEqual('MPC_MINOR_PLANET', body.elements_type)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_new_comet_has_epochperih(self):

        # Remove other Body to check we don't create extra
        self.blank_body.delete()

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 1, 20, 10, 40, 0)

        crossid_info = ['P10G50L', 'C/2018 A5', 'MPEC 2018-B20', '(Jan. 17.81 UT)']

        self.body.origin = u'M'
        self.body.source_type = u'U'
        self.body.provisional_name = 'P10G50L'
        self.body.epochofel = datetime(2018, 1, 2, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None

        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(1, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('C', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('C/2018 A5', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)
        self.assertIsNot(None, body.perihdist)
        self.assertAlmostEqual(2.6725494646558405, body.perihdist, 7)
        self.assertEqual(datetime(2017, 9, 14, 22, 34, 45, 428836), body.epochofperih)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_check_Hyperbolic_ast_blank_body(self):

        # Set Mock time to more than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2017, 3,  8, 10, 40, 0)

        crossid_info = [u'ZC82561', u'I/2018 C2', u'MPEC 2018-E18', u'(Mar. 4.95 UT)']

        status = update_crossids(crossid_info, dbg=False)

        body = Body.objects.get(provisional_name=self.blank_body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(False, body.active)
        self.assertEqual('A', body.source_type)
        self.assertEqual('H', body.source_subtype_1)
        self.assertEqual('M', body.origin)
        self.assertEqual('I/2018 C2', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_same_obj_different_provids(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9,  5, 10, 40, 0)

        crossid_info = ['ZTF00Y8 ', '2015 FP118', '', '(Sept. 3.50 UT)']

        self.body.origin = u'A'
        self.body.source_type = u'N'
        self.body.provisional_name = 'P10jZsv'
        self.body.name = '2015 FP118'
        self.body.epochofel = datetime(2018, 9, 5, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None

        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('A', body.origin)
        self.assertEqual('2015 FP118', body.name)
        self.assertEqual('MPC_MINOR_PLANET', body.elements_type)
        self.assertIs(None, body.perihdist)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_same_obj_multiple_copies_different_provids(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9,  5, 10, 40, 0)

        crossid_info = ['ZTF00Y8 ', '2015 FP118', '', '(Sept. 3.50 UT)']

        self.body.origin = u'A'
        self.body.source_type = u'N'
        self.body.provisional_name = 'P10jZsv'
        self.body.name = '2015 FP118'
        self.body.epochofel = datetime(2018, 9, 5, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None
        self.body.ingest = datetime(2018, 9, 1, 1, 2, 3)
        self.body.save()

        # Create duplicate with different info
        body = Body.objects.get(pk=self.body.pk)
        body.pk = None
        body.provisional_name = 'A9999'
        body.origin = 'N'
        body.ingest = datetime(2018, 9, 2, 12, 13, 14)
        body.save()
        self.assertEqual(3, Body.objects.count(), msg="Before update_crossids; should be 3 Bodies")

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count(), msg="After update_crossids; should be 2 Bodies")

        body = Body.objects.get(name='2015 FP118')

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('A', body.origin)
        self.assertEqual('2015 FP118', body.name)
        self.assertEqual('MPC_MINOR_PLANET', body.elements_type)
        self.assertIs(None, body.perihdist)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_crossids_update_multiple_designations(self):
        expected_types = ['C', 'P', 'C', 'C']
        expected_desigs = ['LM05OFG', '2015 FP118', 'ZTF00Y8', 'A9999']
        expected_names = list(zip(expected_types, expected_desigs))

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9, 5, 10, 40, 0)

        crossid_info = ['ZTF00Y8 ', '2015 FP118', '', '(Sept. 3.50 UT)']

        self.body.origin = u'A'
        self.body.source_type = u'N'
        self.body.name = '2015 FP118'
        self.body.epochofel = datetime(2018, 9, 5, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None
        self.body.ingest = datetime(2018, 9, 1, 1, 2, 3)
        self.body.save()

        # Create duplicate with different info
        body = Body.objects.get(pk=self.body.pk)
        body.pk = None
        body.provisional_name = 'A9999'
        body.origin = 'N'
        body.ingest = datetime(2018, 9, 2, 12, 13, 14)
        body.save()

        des_dicts = [{'desig_type': 'C', 'value': 'A9999'},
                     {'desig_type': 'P', 'value': '2015 FP118'}
                     ]
        for des in des_dicts:
            body.save_physical_parameters(des)

        self.assertEqual(3, Body.objects.count(), msg="Before update_crossids; should be 3 Bodies")

        update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count(), msg="After update_crossids; should be 2 Bodies")

        body = Body.objects.get(name='2015 FP118')
        names = Designations.objects.filter(body=body)

        for name in names:
            test_list = (name.desig_type, name.value)
            self.assertIn(test_list, expected_names)
            expected_names.remove(test_list)
        self.assertEqual(expected_names, [])

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_same_obj_multiple_copies_different_provids_from_MPC(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9,  5, 10, 40, 0)

        crossid_info = ['ZTF00Y8 ', '2015 FP118', '', '(Sept. 3.50 UT)']

        self.body.origin = u'A'
        self.body.source_type = u'N'
        self.body.provisional_name = 'P10jZsv'
        self.body.name = '2015 FP118'
        self.body.epochofel = datetime(2018, 9, 5, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None
        self.body.ingest = datetime(2018, 9, 1, 1, 2, 3)
        self.body.save()

        # Create duplicate with different info
        body = Body.objects.get(pk=self.body.pk)
        body.pk = None
        body.provisional_name = 'A9999'
        body.origin = 'M'
        body.ingest = datetime(2018, 9, 2, 12, 13, 14)
        body.save()
        self.assertEqual(3, Body.objects.count(), msg="Before update_crossids; should be 3 Bodies")

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(3, Body.objects.count(), msg="After update_crossids; should still be 3 Bodies (MPC origin)")

        body = Body.objects.get(pk=1)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('N', body.source_type)
        self.assertEqual('A', body.origin)
        self.assertEqual('2015 FP118', body.name)
        self.assertEqual('MPC_MINOR_PLANET', body.elements_type)
        self.assertIs(None, body.perihdist)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_same_obj_multiple_copies_with_block(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9,  5, 10, 40, 0)

        crossid_info = ['ZTF00Y8 ', '2015 FP118', '', '(Sept. 3.50 UT)']

        self.body.origin = u'A'
        self.body.source_type = u'N'
        self.body.provisional_name = 'P10jZsv'
        self.body.name = '2015 FP118'
        self.body.epochofel = datetime(2018, 9, 5, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None
        self.body.ingest = datetime(2018, 9, 1, 1, 2, 3)

        self.body.save()
        # Create duplicate with different info
        body = Body.objects.get(pk=self.body.pk)
        body.pk = None
        body.provisional_name = 'A9999'
        body.origin = 'M'
        body.ingest = datetime(2018, 9, 2, 12, 13, 14)
        body.save()

        block, created = Block.objects.get_or_create(body=body)
        self.assertEqual(3, Body.objects.count(), msg="Before update_crossids; should be 3 Bodies")

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(3, Body.objects.count(), msg="After update_crossids; should still be 3 Bodies")

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_same_obj_multiple_copies_with_superblock(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9,  5, 10, 40, 0)

        crossid_info = ['ZTF00Y8 ', '2015 FP118', '', '(Sept. 3.50 UT)']

        self.body.origin = u'A'
        self.body.source_type = u'N'
        self.body.provisional_name = 'P10jZsv'
        self.body.name = '2015 FP118'
        self.body.epochofel = datetime(2018, 9, 5, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None
        self.body.ingest = datetime(2018, 9, 1, 1, 2, 3)

        self.body.save()
        # Create duplicate with different info
        body = Body.objects.get(pk=self.body.pk)
        body.pk = None
        body.provisional_name = 'A9999'
        body.origin = 'M'
        body.ingest = datetime(2018, 9, 2, 12, 13, 14)
        body.save()

        sblock, created = SuperBlock.objects.get_or_create(body=body, proposal=self.neo_proposal)
        self.assertEqual(3, Body.objects.count(), msg="Before update_crossids; should be 3 Bodies")

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(3, Body.objects.count(), msg="After update_crossids; should still be 3 Bodies")

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_NEO_to_numbered_comet_match(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9,  17, 10, 40, 0)

        crossid_info = ['ZS9E891 ', '0046P  ', '', '(Sept. 16.62 UT)']

        self.body.origin = 'M'
        self.body.source_type = 'U'
        self.body.provisional_name = 'ZS9E891'
        self.body.name = None
        self.body.epochofel = datetime(2018, 9, 5, 0, 0)
        self.body.eccentricity = 0.5415182
        self.body.meandist = 5.8291288
        self.body.meananom = 7.63767
        self.body.perihdist = None
        self.body.epochofperih = None

        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('C', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('46P', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)
        q = self.body.meandist * (1.0 - self.body.eccentricity)
        self.assertAlmostEqual(q, body.perihdist, 7)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_NEO_to_numbered_comet_match2(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2018, 9,  19, 10, 40, 0)

        crossid_info = ['ZS0B8B9 ', '0060P  ', '', '(Sept. 18.83 UT)']

        self.body.origin = 'M'
        self.body.source_type = 'U'
        self.body.provisional_name = 'ZS0B8B9'
        self.body.name = None
        self.body.epochofel = datetime(2018, 9, 18, 0, 0)
        self.body.eccentricity = 0.5377759
        self.body.meandist = 3.5105122
        self.body.meananom = 347.37843
        self.body.perihdist = None
        self.body.epochofperih = None

        q = self.body.meandist * (1.0 - self.body.eccentricity)
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual(True, body.active)
        self.assertEqual('C', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('60P', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)
        self.assertAlmostEqual(q, body.perihdist, 7)
        self.assertIs(None, body.meananom)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_newstyle_to_numbered_comet_match1(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2020, 4,  13, 10, 40, 0)

        crossid_info = ['SWAN20A ', '58P', '', '(Apr. 9.13 UT)']

        self.body.origin = 'M'
        self.body.source_type = 'U'
        self.body.provisional_name = 'SWAN20A'
        self.body.name = None
        self.body.epochofel = datetime(2020, 4, 12, 0, 0)
        self.body.eccentricity = 0.9964264
        self.body.meandist = 118.3168684
        self.body.meananom = 347.37843
        self.body.perihdist = None
        self.body.epochofperih = None

        q = self.body.meandist * (1.0 - self.body.eccentricity)
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual('C', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('58P', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)
        self.assertAlmostEqual(q, body.perihdist, 7)
        self.assertIs(None, body.meananom)
        self.assertEqual(False, body.active)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_newstyle_to_unnumbered_comet_match1(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2020, 4,  10, 10, 40, 0)

        crossid_info = ['P10XLLe ', 'C/2020 F6', '', '(Apr. 8.96 UT)']

        self.body.origin = 'M'
        self.body.source_type = 'U'
        self.elements_type = 'MPC_COMET'
        self.body.provisional_name = 'P10XLLe'
        self.body.name = None
        self.body.epochofel = datetime(2020, 3, 22, 0, 0)
        self.body.eccentricity = 0.9857459
        self.body.meandist = 246.2398975
        self.body.meananom = 359.93312
        self.body.perihdist = None
        self.body.epochofperih = None

        q = self.body.meandist * (1.0 - self.body.eccentricity)
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual('C', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('C/2020 F6', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)
        self.assertAlmostEqual(q, body.perihdist, 7)
        self.assertIs(None, body.meananom)
        self.assertEqual(True, body.active)

    @patch('core.views.datetime', MockDateTime)
    @patch('astrometrics.time_subs.datetime', MockDateTime)
    def test_newstyle_to_unnumbered_comet_match2(self):

        # Set Mock time to less than 3 days past the time of the cross ident.
        MockDateTime.change_datetime(2020, 4,  8, 10, 40, 0)

        crossid_info = ['M60B7LC ', 'C/2020 F5', '', '(Apr. 8.11 UT)']

        self.body.origin = 'M'
        self.body.source_type = 'U'
        self.body.provisional_name = 'M60B7LC'
        self.body.name = None
        self.body.epochofel = datetime(2020, 3, 23, 0, 0)
        self.body.eccentricity = 0.9997408
        self.body.meandist = 16761.69106
        self.body.meananom = 359.93312
        self.body.perihdist = None
        self.body.epochofperih = None

        q = self.body.meandist * (1.0 - self.body.eccentricity)
        self.body.save()

        status = update_crossids(crossid_info, dbg=False)
        self.assertEqual(2, Body.objects.count())

        body = Body.objects.get(provisional_name=self.body.provisional_name)

        self.assertEqual(True, status)
        self.assertEqual('C', body.source_type)
        self.assertEqual('M', body.origin)
        self.assertEqual('C/2020 F5', body.name)
        self.assertEqual('MPC_COMET', body.elements_type)
        self.assertAlmostEqual(q, body.perihdist, 7)
        self.assertIs(None, body.meananom)
        self.assertEqual(True, body.active)


class TestStoreDetections(TestCase):

    def setUp(self):

        self.phot_tests_dir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_mtds = os.path.join(self.phot_tests_dir, 'elp1m008-fl05-20160225-0095-e90.mtds')
        # Initialise with three test bodies a test proposal and several blocks.
        # The first body has a provisional name (e.g. a NEO candidate), the
        # other 2 do not (e.g. Goldstone targets)
        params = {  'provisional_name' : 'P10sSA6',
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
                    }
        self.body_with_provname, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015B-005',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test blocks
        sblock_params = {
                         'body'     : self.body_with_provname,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.body_with_provname.current_name() + '_CPT-20150420',
                         'block_start' : '2016-02-26 03:00:00',
                         'block_end'   : '2016-02-26 13:00:00',
                         'tracking_number' : '00042',
                         'active'   : True
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = { 'telclass' : '1m0',
                         'site'     : 'ELP',
                         'body'     : self.body_with_provname,
                         'superblock'  : self.test_sblock,
                         'block_start' : '2016-02-26 03:00:00',
                         'block_end'   : '2016-02-26 13:00:00',
                         'request_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.test_block = Block.objects.create(**block_params)

        frame_params = { 'block'    : self.test_block,
                         'filename' : 'elp1m008-fl05-20160225-0095-e90.fits',
                         'sitecode' : 'V37',
                         'midpoint' : datetime(2016, 2, 26, 3, 44, 42)
                       }

        self.test_frame = Frame.objects.create(**frame_params)

    def test_store_detections(self):
        expected_num_cands = 23

        store_detections(self.test_mtds)

        cands = Candidate.objects.all()
        self.assertEqual(expected_num_cands, len(cands))


class TestGenerateNewCandidateIdBlank(TestCase):

    def test_no_discoveries(self):
        expected_id = 'LNX0001'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)

    def test_no_discoveries_with_prefix(self):
        expected_id = 'NEOX001'

        new_id = generate_new_candidate_id('NEOX')

        self.assertEqual(expected_id, new_id)

    def test_no_discoveries_other_bodies(self):

        params = {  'provisional_name' : 'LCOTL01',
                    'origin' : 'L'
                 }
        body = Body.objects.create(**params)

        expected_id = 'LNX0001'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)


class TestGenerateNewCandidateId(TestCase):

    def setUp(self):

        params = { 'provisional_name' : 'LNX0001',
                   'origin' : 'L',
                   'ingest' : datetime(2017, 1, 1)
                 }
        body = Body.objects.create(**params)

    def test_one_body(self):
        expected_id = 'LNX0002'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)

    def test_one_body_new_prefix(self):
        expected_id = 'LCOTL01'

        new_id = generate_new_candidate_id('LCOTL')

        self.assertEqual(expected_id, new_id)

    def test_three_body(self):
        params = { 'provisional_name' : 'LNX0002',
                   'origin' : 'L',
                   'ingest' : datetime(2017, 1, 2)
                 }

        body = Body.objects.create(**params)

        params = { 'provisional_name' : 'LNX0003',
                   'origin' : 'L',
                   'ingest' : datetime(2017, 1, 1, 12)
                 }

        body = Body.objects.create(**params)

        expected_id = 'LNX0004'

        new_id = generate_new_candidate_id()

        self.assertEqual(expected_id, new_id)
        self.assertEqual(3, Body.objects.count())


class TestAddNewTaxonomyData(TestCase):

    def setUp(self):

        params = { 'name' : '980',
                   'provisional_name' : 'LNX0003',
                   'origin' : 'L',
                 }
        self.body = Body.objects.create(pk=1, **params)

        tax_params = {'body'          : self.body,
                      'taxonomic_class' : 'S3',
                      'tax_scheme'    :   'Ba',
                      'tax_reference' : 'PDS6',
                      'tax_notes'     : '7I',
                      }
        self.test_spectra = SpectralInfo.objects.create(pk=1, **tax_params)

    def test_one_body(self):
        expected_res = 1
        test_obj = [['LNX0003', 'SU', "T", "PDS6", "7G"]]
        new_tax = update_taxonomy(self.body, test_obj)

        self.assertEqual(expected_res, new_tax)

    def test_new_target(self):
        expected_res = False
        test_obj = [['4702', 'S', "B", "PDS6", "s"]]
        new_tax = update_taxonomy(self.body, test_obj)

        self.assertEqual(expected_res, new_tax)

    def test_same_data(self):
        expected_res = 0
        test_obj = [['980', 'S3', "Ba", "PDS6", "7I"]]
        new_tax = update_taxonomy(self.body, test_obj)

        self.assertEqual(expected_res, new_tax)

    def test_same_data_twice(self):
        expected_res = 0
        test_obj = [['980', 'SU', "T", "PDS6", "7G"]]
        new_tax = update_taxonomy(self.body, test_obj)
        new_tax = update_taxonomy(self.body, test_obj)

        self.assertEqual(expected_res, new_tax)


class TestAddExternalSpectroscopyData(TestCase):

    def setUp(self):

        params = {'name': '980',
                  'provisional_name': 'LNX0003',
                  'origin': 'L',
                  'active': True,
                  }
        self.body = Body.objects.create(pk=1, **params)

        spec_params = {'body': self.body,
                       'spec_wav': 'Vis',
                       'spec_vis': 'spex/sp233/a265962.sp233.txt',
                       'spec_ref': 'sp[234]',
                       'spec_source': 'S',
                       'spec_date': '2017-09-25',
                       }
        self.test_spectra = PreviousSpectra.objects.create(pk=1, **spec_params)

    def test_same_body_different_wavelength(self):
        expected_res = True
        test_obj = ['LNX0003', 'NIR', '', "spex/sp233/a416584.sp233.txt", "sp[233]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'S', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_same_everything_different_link(self):
        expected_res = False
        new_link = 'spex/sp233/a416584.sp234.txt'
        self.assertNotEqual(new_link, self.test_spectra.spec_vis)
        test_obj = ['LNX0003', 'Vis', new_link, "", "sp[234]", datetime.strptime('2017-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'S', dbg=True)
        self.test_spectra.refresh_from_db()

        self.assertEqual(expected_res, new_spec)
        self.assertEqual(new_link, self.test_spectra.spec_vis)

    def test_same_body_older(self):
        expected_res = False
        test_obj = ['980', 'Vis', 'spex/sp233/a416584.sp234.txt', "", "sp[24]", datetime.strptime('2015-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'S', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_same_body_newer(self):
        expected_res = True
        test_obj = ['980', 'Vis', 'spex/sp233/a416584.sp234.txt', "", "sp[24]", datetime.strptime('2017-12-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'S', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_same_body_different_source(self):
        expected_res = True
        test_obj = ['980', 'Vis', '2014/09/1999sh10.png', "", "MANOS Site", datetime.strptime('2015-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'M', dbg=True)

        self.assertEqual(expected_res, new_spec)

    def test_new_body(self):
        expected_res = False
        test_obj = ['9801', 'Vis', '2014/09/1999sh10.png', "", "MANOS Site", datetime.strptime('2015-09-25', '%Y-%m-%d').date()]
        new_spec = update_previous_spectra(test_obj, 'M', dbg=True)

        self.assertEqual(expected_res, new_spec)


class TestCreateStaticSource(TestCase):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.test_flux_standards = fetch_flux_standards(test_flux_page)

        solar_standards_test = os.path.join('astrometrics', 'tests', 'solar_standards_test_list.dat')
        self.test_solar_analogs = read_solar_standards(solar_standards_test)

        self.maxDiff = None
        self.precision = 10

    def test_num_created(self):
        expected_created = 3

        num_created = create_calib_sources(self.test_flux_standards)

        self.assertEqual(expected_created, num_created)
        self.assertEqual(expected_created, StaticSource.objects.count())

    def test_correct_units(self):
        expected_num = 3
        expected_src1_ra = ((((49.42/60.0)+1.0)/60.0)+0)*15.0
        expected_src1_dec = -((((39.0/60.0)+1.0)/60.0)+3.0)
        expected_src3_ra = ((((24.30/60.0)+56.0)/60.0)+5)*15.0
        expected_src3_dec = -((((28.8/60.0)+51.0)/60.0)+27.0)

        num_created = create_calib_sources(self.test_flux_standards)

        cal_sources = StaticSource.objects.filter(source_type=StaticSource.FLUX_STANDARD)
        self.assertEqual(expected_num, cal_sources.count())
        self.assertAlmostEqual(expected_src1_ra, cal_sources[0].ra, self.precision)
        self.assertAlmostEqual(expected_src1_dec, cal_sources[0].dec, self.precision)
        self.assertAlmostEqual(expected_src3_ra, cal_sources[2].ra, self.precision)
        self.assertAlmostEqual(expected_src3_dec, cal_sources[2].dec, self.precision)

    def test_solar_standards(self):
        expected_num = 46
        expected_src1_name = 'Landolt SA93-101'
        expected_src1_ra = ((((18.00/60.0)+53.0)/60.0)+1)*15.0
        expected_src1_dec = ((((25.0/60.0)+22.0)/60.0)+0.0)
        expected_src1_sptype = 'G2V'

        num_created = create_calib_sources(self.test_solar_analogs, cal_type=StaticSource.SOLAR_STANDARD)

        cal_sources = StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD)
        self.assertEqual(expected_num, cal_sources.count())
        self.assertEqual(expected_src1_name, cal_sources[0].name)
        self.assertEqual(expected_src1_sptype, cal_sources[0].spectral_type)
        self.assertAlmostEqual(expected_src1_ra, cal_sources[0].ra, self.precision)
        self.assertAlmostEqual(expected_src1_dec, cal_sources[0].dec, self.precision)


class TestFindBestFluxStandard(TestCase):

    def setUp(self):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        self.flux_standards = fetch_flux_standards(test_flux_page)
        num_created = create_calib_sources(self.flux_standards)

        self.maxDiff = None
        self.precision = 8

    def test_FTN(self):
        expected_standard = StaticSource.objects.get(name='HR9087')
        expected_params = { 'separation_rad' : 0.9379758789119819}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2017, 11, 15, 1, 10, 0)
        close_standard, close_params = find_best_flux_standard('F65', utc_date)

        self.assertEqual(expected_standard, close_standard)
        for key in expected_params:
            if '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])

    def test_FTS(self):
        expected_standard = StaticSource.objects.get(name='CD-34d241')
        expected_params = { 'separation_rad' : 0.11565764559405214}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2017, 9, 27, 1, 10, 0)
        close_standard, close_params = find_best_flux_standard('E10', utc_date)

        self.assertEqual(expected_standard, close_standard)
        for key in expected_params:
            if '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])


class TestFindBestSolarAnalog(TestCase):

    def setUp(self):

        self.maxDiff = None
        self.precision = 8

    @classmethod
    def setUpTestData(cls):
        test_fh = open(os.path.join('astrometrics', 'tests', 'flux_standards_lis.html'), 'r')
        test_flux_page = BeautifulSoup(test_fh, "html.parser")
        test_fh.close()
        cls.flux_standards = fetch_flux_standards(test_flux_page)
        cls.num_flux_created = create_calib_sources(cls.flux_standards)

        test_file = os.path.join('astrometrics', 'tests', 'solar_standards_test_list.dat')
        cls.test_solar_analogs = read_solar_standards(test_file)
        cls.num_solar_created = create_calib_sources(cls.test_solar_analogs, cal_type=StaticSource.SOLAR_STANDARD)
        params = {
                 'name': '1093',
                 'origin': 'M',
                 'source_type': 'A',
                 'elements_type': 'MPC_MINOR_PLANET',
                 'epochofel': datetime(2018, 3, 23, 0, 0),
                 'orbinc': 25.21507,
                 'longascnode': 55.63599,
                 'argofperih': 251.40338,
                 'eccentricity': 0.2712664,
                 'meandist': 3.1289388,
                 'meananom': 211.36057,
                 'abs_mag': 8.83,
                 'slope': 0.15,
                 'num_obs': 2187,
                }
        cls.test_body, created = Body.objects.get_or_create(pk=1, **params)

    def test_ingest(self):
        calib_sources = StaticSource.objects.all()
        flux_standards = calib_sources.filter(source_type=StaticSource.FLUX_STANDARD)
        solar_standards = calib_sources.filter(source_type=StaticSource.SOLAR_STANDARD)

        self.assertEqual(self.num_flux_created+self.num_solar_created, calib_sources.count())
        self.assertEqual(self.num_flux_created, flux_standards.count())
        self.assertEqual(self.num_solar_created, solar_standards.count())

    def test_FTN(self):
        expected_ra = 2.7772337523336565
        expected_dec = 0.6247970652631909
        expected_standard = StaticSource.objects.get(name='35 Leo')
        expected_params = {'separation_deg': 13.031726234959416}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2017, 11, 15, 14, 0, 0)
        emp = compute_ephem(utc_date, model_to_dict(self.test_body), 'F65', perturb=False)
        self.assertAlmostEqual(expected_ra, emp['ra'], self.precision)
        self.assertAlmostEqual(expected_dec, emp['dec'], self.precision)
        close_standard, close_params, close_std_list = find_best_solar_analog(emp['ra'], emp['dec'], 'F65')

        self.assertEqual(expected_standard, close_standard)
        self.assertEqual(len(close_std_list), 5)
        self.assertGreater(close_std_list[1]["separation"], close_std_list[0]["separation"])
        self.assertGreater(close_std_list[2]["separation"], close_std_list[1]["separation"])
        self.assertGreater(close_std_list[3]["separation"], close_std_list[2]["separation"])

        for key in expected_params:
            if '_deg' in key or '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])

        close_standard2, close_params2, close_std_list2 = find_best_solar_analog(emp['ra'], emp['dec'], 'F65', num=2)
        self.assertNotEqual(expected_params['name'], close_params2['name'])
        self.assertNotEqual(expected_params['ra'], close_params2['ra'])
        self.assertEqual(close_std_list2, close_std_list)
        self.assertEqual(close_std_list[1]['calib'], close_standard2)

    def test_FTS(self):
        expected_ra = 4.334041503242261
        expected_dec = -0.3877173805762358
        expected_standard = StaticSource.objects.get(name='HD 140990')
        expected_params = {'separation_deg': 10.838361371951908}
        # Python 3.5 dict merge; see PEP 448
        expected_params = {**expected_params, **model_to_dict(expected_standard)}

        utc_date = datetime(2014, 4, 20, 13, 30, 0)
        emp = compute_ephem(utc_date, model_to_dict(self.test_body), 'E10', perturb=False)
        self.assertAlmostEqual(expected_ra, emp['ra'], self.precision)
        self.assertAlmostEqual(expected_dec, emp['dec'], self.precision)
        close_standard, close_params, close_std_list = find_best_solar_analog(emp['ra'], emp['dec'], 'E10')

        self.assertEqual(expected_standard, close_standard)
        self.assertEqual(len(close_std_list), 5)
        self.assertGreater(close_std_list[1]["separation"], close_std_list[0]["separation"])
        self.assertGreater(close_std_list[2]["separation"], close_std_list[1]["separation"])
        self.assertGreater(close_std_list[3]["separation"], close_std_list[2]["separation"])
        for key in expected_params:
            if '_deg' in key or '_rad' in key:
                self.assertAlmostEqual(expected_params[key], close_params[key], places=self.precision)
            else:
                self.assertEqual(expected_params[key], close_params[key])

    def test_FTS_no_match(self):
        expected_ra = 5.840671145434903
        expected_dec = -0.9524603478856751
        expected_standard = None
        expected_params = {}
        expected_list = []

        utc_date = datetime(2020, 9, 5, 13, 30, 0)
        emp = compute_ephem(utc_date, model_to_dict(self.test_body), 'E10', perturb=False)
        self.assertAlmostEqual(expected_ra, emp['ra'], self.precision)
        self.assertAlmostEqual(expected_dec, emp['dec'], self.precision)
        close_standard, close_params, close_std_list = find_best_solar_analog(emp['ra'], emp['dec'], 'E10', ha_sep=0.5)

        self.assertEqual(expected_standard, close_standard)
        self.assertEqual(expected_params, close_params)
        self.assertEqual(expected_list, close_std_list)


class TestDownloadMeasurementsFile(TestCase):

    def setUp(self):
        self.ades_template = get_template('core/mpc_ades_psv_outputfile.txt')
        self.mpc_template = get_template('core/mpc_outputfile.txt')

        body_params = {
                        'provisional_name': 'C1HDFQ2',
                        'provisional_packed': None,
                        'name': '2019 XS',
                        'origin': 'G',
                        'source_type': 'N',
                        'source_subtype_1': '',
                        'source_subtype_2': None,
                        'elements_type': 'MPC_MINOR_PLANET',
                        'active': True,
                        'fast_moving': True,
                        'urgency': None,
                        'epochofel': datetime(2021, 11, 10, 0, 0),
                        'orbit_rms': 0.33,
                        'orbinc': 4.4386,
                        'longascnode': 49.49322,
                        'argofperih': 250.25583,
                        'eccentricity': 0.3277499,
                        'meandist': 1.0048339,
                        'meananom': 69.71659,
                        'perihdist': 0.0815255040820201,
                        'epochofperih': datetime(2019, 9, 30, 19, 58, 17),
                        'abs_mag': 23.86,
                        'slope': 0.15,
                        'score': 96,
                        'discovery_date': datetime(2012, 12, 22, 0, 0),
                        'num_obs': 72,
                        'arc_length': 6210.0,
                        'not_seen': 334.05341602897,
                        'updated': True,
                        'ingest': datetime(2019, 12, 2, 7, 20, 38),
                        'update_time': datetime(2021, 11, 9, 1, 16, 55, 144878)
                        }
        self.test_body, created = Body.objects.get_or_create(**body_params)

        test_proposal, created = Proposal.objects.get_or_create(code='LCOTesting', title='LCOTesting')

        sblock_params = {
                         'cadence': False,
                         'body': self.test_body,
                         'calibsource': None,
                         'proposal': test_proposal,
                         'block_start': datetime(2021, 11, 10, 3, 40),
                         'block_end': datetime(2021, 11, 10, 9, 22),
                         'groupid': '2019 XS_V37-20211110',
                         'tracking_number': '1335839',
                         'timeused': 883.0,
                         'active': False
                         }

        self.test_sblock, created = SuperBlock.objects.get_or_create(**sblock_params)

        block_params = {
                         'telclass': '1m0',
                         'site': 'elp',
                         'body': self.test_body,
                         'calibsource': None,
                         'superblock': self.test_sblock,
                         'obstype': 0,
                         'block_start': datetime(2021, 11, 10, 3, 40),
                         'block_end': datetime(2021, 11, 10, 9, 22),
                         'request_number': '2704510',
                         'num_exposures': 26,
                         'exp_length': 2.0,
                         'num_observed': 1,
                         'when_observed': datetime(2021, 11, 10, 4, 47, 22),
                         'active': False,
                         'reported': True,
                         'when_reported': datetime(2021, 11, 12, 1, 30, 32, 830720)
                       }
        self.test_block, created = Block.objects.get_or_create(**block_params)

        frame_params = {
                         'sitecode': 'V37',
                         'instrument': 'fa05',
                         'filter': 'w',
                         'filename': 'elp1m008-fa05-20211109-0177-e91.fits',
                         'exptime': 2.028,
                         'midpoint': datetime(2021, 11, 10, 4, 47, 23, 867000),
                         'block': self.test_block,
                         'quality': ' ',
                         'zeropoint': 25.197377268962,
                         'zeropoint_err': 0.0819936287107206,
                         'fwhm': 1.7449277159035,
                         'frametype': 91,
                         'extrainfo': None,
                         'rms_of_fit': 0.283035,
                         'nstars_in_fit': 45.0,
                         'time_uncertainty': None,
                         'frameid': 46146456,
                         'astrometric_catalog': 'GAIA-DR2',
                         'photometric_catalog': 'GAIA-DR2'
                       }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

        sm_params = {
                     'body': self.test_body,
                     'frame': self.test_frame,
                     'obs_ra': 41.7905144822113,
                     'obs_dec': -4.34047400302277,
                     'obs_mag': 14.3134813308716,
                     'err_obs_ra': 2.39723807836075e-06,
                     'err_obs_dec': 2.48654937873956e-06,
                     'err_obs_mag': 0.0827159211039543,
                     'astrometric_catalog': 'GAIA-DR2',
                     'photometric_catalog': 'GAIA-DR2',
                     'aperture_size': 3.0,
                     'snr': 12.0895709877091,
                     'flags': ' '}
        self.test_sm, created = SourceMeasurement.objects.get_or_create(**sm_params)

        self.psv_header =  'permID |provID     |trkSub  |mode|stn |obsTime                |ra         |dec        |rmsRA|rmsDec|astCat  |mag  |rmsMag|band|photCat |photAp|logSNR|seeing|notes|remarks'

        self.maxDiff = None

    def test_V37_ades(self):
        expected_response = '\n'.join([self.psv_header,
        '       |2019 XS    |        | CCD|V37 |2021-11-10T04:47:23.87Z| 41.790514 | -4.340474 | 0.28|  0.28|   Gaia2|14.3 |0.083 |   G|   Gaia2|  3.00|1.0824|1.7449|     |', '',''])

        request = ''
        response = download_measurements_file(self.ades_template, self.test_body, '.psv', request)

        self.assertEqual(expected_response, response.content.decode())

    def test_V37_mpc(self):
        expected_response = '     K19X00S  C2021 11 10.19958202 47 09.72 -04 20 25.7          14.3 G      V37' + '\n\n'

        request = ''
        response = download_measurements_file(self.mpc_template, self.test_body, '.psv', request)

        self.assertEqual(expected_response, response.content.decode())

    def test_V39_ades(self):
        expected_response = '\n'.join([self.psv_header,'       |2019 XS    |        | CCD|V39 |2021-11-10T04:47:23.87Z| 41.790514 | -4.340474 | 0.28|  0.28|   Gaia2|14.3 |0.083 |   G|   Gaia2|  3.00|1.0824|1.7449|     |', '',''])

        self.test_frame.sitecode = 'V39'
        self.test_frame.instrument = 'fa07'
        self.test_frame.save()

        request = ''
        response = download_measurements_file(self.ades_template, self.test_body, '.psv', request)

        self.assertEqual(expected_response, response.content.decode())

    def test_V39_mpc(self):
        expected_response = '     K19X00S  C2021 11 10.19958202 47 09.72 -04 20 25.7          14.3 G      V39' + '\n\n'

        self.test_frame.sitecode = 'V39'
        self.test_frame.instrument = 'fa07'
        self.test_frame.save()

        request = ''
        response = download_measurements_file(self.mpc_template, self.test_body, '.psv', request)

        self.assertEqual(expected_response, response.content.decode())


class TestExportMeasurements(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.debug_print = False
        self.maxDiff = None

    @classmethod
    def setUpTestData(cls):
        WSAE9A6_params = { 'provisional_name' : 'WSAE9A6',
                         }

        cls.test_body = Body.objects.create(**WSAE9A6_params)

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_WSAE9A6.dat'), 'r')
        test_obslines = test_fh.readlines()
        test_fh.close()
        source_measures = create_source_measurement(test_obslines)

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)

    def test1(self):
        expected_num_sources = 6
        sources = SourceMeasurement.objects.all()
        self.assertEqual(expected_num_sources, sources.count())

    def test_export(self):
        expected_filename = os.path.join(self.test_dir, 'WSAE9A6.mpc')
        expected_num_lines = 6

        body = Body.objects.get(provisional_name='WSAE9A6')
        filename, num_lines = export_measurements(body.id, self.test_dir)

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_num_lines, num_lines)


class TestUpdateElementsWithFindOrb(TestCase):

    def setUp(self):
        self.source_dir = os.path.abspath(os.path.join(os.path.expanduser('~'), '.find_orb'))
        self.dest_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        orig_filename = os.path.abspath(os.path.join('astrometrics', 'tests', 'test_mpcobs_P10pqB2.dat'))
        self.filename = os.path.basename(orig_filename)
        os.symlink(orig_filename, os.path.join(self.dest_dir, self.filename))

        self.debug_print = False
        self.maxDiff = None

    def tearDown(self):
        remove = True
        if remove:
            try:
                files_to_remove = glob(os.path.join(self.dest_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.dest_dir)
            try:
                os.rmdir(self.dest_dir)
                if self.debug_print:
                    print("Removed", self.dest_dir)
            except OSError:
                print("Error removing temporary test directory", self.dest_dir)

    @patch('core.views.datetime', MockDateTime)
    @patch('neox.tests.mocks.datetime', MockDateTime)
    def test_goodelements(self):

        MockDateTime.change_datetime(2015, 11, 18, 12, 0, 0)
        # Overwrite real method with Mock. Not sure why 'patch' isn't working
        # but it isn't...
        update_elements_with_findorb = mock_update_elements_with_findorb

        expected_elements = {   'abs_mag' : 21.91,
                                'slope' : 0.15,
                                'active' : True,
                                'origin' : 'M',
                                'source_type' : 'U',
                                'elements_type' : 'MPC_MINOR_PLANET',
                                'provisional_name' : 'P10pqB2',
                                'epochofel' : datetime(2015, 11, 18),
                                'meananom' : 270.89733,
                                'argofperih' : 339.47051,
                                'longascnode' : 197.11047,
                                'orbinc' : 10.74649,
                                'eccentricity' :  0.3001867,
                                'meandist' :  1.1896136,
                                'arc_length' : 22.5/24.0,
                                'num_obs' : 9,
                                'not_seen' : 0.5,
                                'update_time' : datetime(2015, 11, 18, 12, 0, 0),
                                'orbit_rms' : 0.1
                            }

        start_time = datetime(2015, 11, 18, 23)
        site_code = 'Z21'
        elements_or_status = update_elements_with_findorb(self.source_dir, self.dest_dir, self.filename, site_code, start_time)

        self.assertEqual(expected_elements, elements_or_status)

    def test_bad_filename(self):

        # Overwrite real method with Mock. Not sure why 'patch' isn't working
        # but it isn't...
        update_elements_with_findorb = mock_update_elements_with_findorb

        expected_status = 255

        start_time = datetime(2015, 11, 19)
        site_code = 'Z21'

        elements_or_status = update_elements_with_findorb(self.source_dir, self.dest_dir, 'i_am_broken', site_code, start_time)

        self.assertEqual(expected_status, elements_or_status)


class TestRefitWithFindOrb(TestCase):

    @classmethod
    def setUpTestData(cls):
        P10pqB2_params = { 'provisional_name' : 'P10pqB2',
                           'source_type' : 'U',
                           'epochofel' : datetime(2014, 12, 23)
                         }

        cls.test_body = Body.objects.create(**P10pqB2_params)

        test_fh = open(os.path.join('astrometrics', 'tests', 'test_mpcobs_P10pqB2.dat'), 'r')
        test_obslines = test_fh.readlines()
        test_fh.close()
        source_measures = create_source_measurement(test_obslines)

    def setUp(self):
        self.source_dir = os.path.abspath(os.path.join(os.path.expanduser('~'), '.find_orb'))
        self.dest_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.debug_print = False
        self.remove = True

        self.maxDiff = None

        self.test_body.refresh_from_db()

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.dest_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.dest_dir)
            try:
                os.rmdir(self.dest_dir)
                if self.debug_print:
                    print("Removed", self.dest_dir)
            except OSError:
                print("Error removing temporary test directory", self.dest_dir)
        else:
            print("dest_dir=", self.dest_dir)

    @patch('core.views.update_elements_with_findorb', mock_update_elements_with_findorb)
    def test_Z21(self):
        start_time = datetime(2015, 11, 19)
        site_code = 'Z21'

        expected_emp_info = { 'obj_id' : self.test_body.current_name(),
                              'emp_sitecode' : site_code,
                              'emp_timesys' : '(UTC)',
                              'emp_rateunits' : "'/hr"}
        expected_ephem = [(datetime(2015, 11, 19, 0,  0, 0), 0.9646629670872465, -0.14939257239592119,  21.1, 2.25, 3.16),
                          (datetime(2015, 11, 19, 0, 30, 0), 0.9644540366313723, -0.14964646932071826, 21.1, 2.25, 3.24),
                          (datetime(2015, 11, 19, 1,  0, 0), 0.9642447425652374, -0.14990002687593854, 21.1, 2.25, 3.33),
                          (datetime(2015, 11, 19, 1, 30, 0), 0.9640354484991024, -0.15015324506158206, 21.1, 2.25, 3.42)
                         ]
        expected_ephem_length = 4
        expected_num_srcmeas = SourceMeasurement.objects.filter(body=self.test_body).count()
        expected_meananom = 272.51789
        expected_eccentricity = 0.3006186
        expected_epoch = datetime(2015, 11, 20)
        expected_src_type = 'U'
        expected_origin = 'M'

        emp_info, new_ephem = refit_with_findorb(self.test_body.pk, site_code, start_time, self.dest_dir)
        self.assertEqual(expected_emp_info, emp_info)
        self.assertEqual(expected_ephem_length, len(new_ephem))
        i = 0
        while i < len(expected_ephem):
            self.assertEqual(expected_ephem[i], new_ephem[i])
            i += 1

        body = Body.objects.get(provisional_name=self.test_body.current_name())

        self.assertEqual(expected_num_srcmeas, body.num_obs)
        self.assertEqual(expected_epoch, body.epochofel)
        self.assertEqual(expected_meananom, body.meananom)
        self.assertEqual(expected_eccentricity, body.eccentricity)
        self.assertEqual(expected_src_type, body.source_type)
        self.assertEqual(expected_origin, body.origin)

    @patch('core.views.update_elements_with_findorb', mock_update_elements_with_findorb_badrms)
    def test_with_bad_RMS(self):
        start_time = datetime(2015, 11, 19)
        site_code = 'Z21'

        expected_emp_info = { 'obj_id' : self.test_body.current_name(),
                              'emp_sitecode' : site_code,
                              'emp_timesys' : '(UTC)',
                              'emp_rateunits' : "'/hr"}
        expected_ephem = [(datetime(2015, 11, 19, 0,  0, 0), 0.9646629670872465, -0.14939257239592119,  21.1, 2.25, 3.16),
                          (datetime(2015, 11, 19, 0, 30, 0), 0.9644540366313723, -0.14964646932071826, 21.1, 2.25, 3.24)
                         ]
        expected_ephem_length = 2
        expected_num_srcmeas = None
        expected_meananom = None
        expected_epoch = datetime(2014, 12, 23)
        expected_src_type = 'U'
        expected_origin = 'M'

        emp_info, new_ephem = refit_with_findorb(self.test_body.pk, site_code, start_time, self.dest_dir)

        self.assertEqual(expected_emp_info, emp_info)
        self.assertEqual(expected_ephem_length, len(new_ephem))
        i = 0
        while i < len(expected_ephem):
            self.assertEqual(expected_ephem[i], new_ephem[i])
            i += 1

        body = Body.objects.get(provisional_name=self.test_body.current_name())

        self.assertEqual(expected_num_srcmeas, body.num_obs)
        self.assertEqual(expected_epoch, body.epochofel)
        self.assertEqual(expected_meananom, body.meananom)
        self.assertEqual(expected_src_type, body.source_type)
        self.assertEqual(expected_origin, body.origin)

    @patch('core.views.update_elements_with_findorb', mock_update_elements_with_findorb_badepoch)
    def test_with_bad_epoch(self):
        start_time = datetime(2015, 11, 19)
        site_code = 'T03'

        expected_emp_info = { 'obj_id' : self.test_body.current_name(),
                              'emp_sitecode' : site_code,
                              'emp_timesys' : '(UTC)',
                              'emp_rateunits' : "'/hr"}
        expected_ephem = [(datetime(2015, 11, 19, 0,  0, 0), 0.9646887106937134, -0.14934360621412912,  21.1, 2.13, 3.45),
                          (datetime(2015, 11, 19, 0, 30, 0), 0.9645093781130711, -0.14959818187807974, 21.1, 2.14, 3.62)
                         ]
        expected_ephem_length = 2
        expected_num_srcmeas = None
        expected_meananom = None
        expected_epoch = datetime(2014, 12, 23)
        expected_src_type = 'U'
        expected_origin = 'M'

        emp_info, new_ephem = refit_with_findorb(self.test_body.pk, site_code, start_time, self.dest_dir)

        self.assertEqual(expected_emp_info, emp_info)
        self.assertEqual(expected_ephem_length, len(new_ephem))
        i = 0
        while i < len(expected_ephem):
            self.assertEqual(expected_ephem[i], new_ephem[i])
            i += 1

        body = Body.objects.get(provisional_name=self.test_body.current_name())

        self.assertEqual(expected_num_srcmeas, body.num_obs)
        self.assertEqual(expected_epoch, body.epochofel)
        self.assertEqual(expected_meananom, body.meananom)
        self.assertEqual(expected_src_type, body.source_type)
        self.assertEqual(expected_origin, body.origin)


class TestDetermineActiveProposals(TestCase):

    @classmethod
    def setUpTestData(cls):
        proposal_params = { 'code'   : 'LCO2019A-005',
                                'title'  : 'LCOGT NEO Follow-up Network',
                                'active' : True
                              }
        cls.active_proposal, created = Proposal.objects.get_or_create(**proposal_params)
        proposal_params['code'] = 'LCOEngineering'
        cls.eng_proposal, created = Proposal.objects.get_or_create(**proposal_params)
        proposal_params['code'] = 'LCOEPO2014B-010'
        proposal_params['download'] = False
        cls.epo_proposal, created = Proposal.objects.get_or_create(**proposal_params)
        proposal_params['code'] = 'LCO2018B-010'
        proposal_params['download'] = True
        proposal_params['active'] = False
        cls.inactive_proposal, created = Proposal.objects.get_or_create(**proposal_params)
        proposal_params['code'] = 'LCO2019A-008'
        proposal_params['active'] = True
        proposal_params['download'] = False
        cls.skipped_proposal, created = Proposal.objects.get_or_create(**proposal_params)

    def test_setup(self):
        proposals = Proposal.objects.all()
        self.assertEqual(5, proposals.count())

        active_proposals = proposals.filter(active=True, download=True)
        self.assertEqual(2, active_proposals.count())

        inactive_proposals = proposals.filter(active=False)
        self.assertEqual(1, inactive_proposals.count())

    def test_nodefault(self):
        expected_num = 2
        expected_code_1 = 'LCO2019A-005'
        expected_code_2 = 'LCOEngineering'

        proposals = determine_active_proposals()

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_code_1, proposals[0])
        self.assertEqual(expected_code_2, proposals[1])

    def test_default_existing_active(self):
        expected_num = 1
        expected_code_1 = 'LCO2019A-005'

        proposals = determine_active_proposals('LCO2019A-005')

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_code_1, proposals[0])

    def test_default_existing_inactive(self):
        expected_num = 1
        expected_code_1 = 'LCO2018B-010'

        proposals = determine_active_proposals('LCO2018B-010')

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_code_1, proposals[0])

    def test_default_not_existing(self):
        expected_num = 0
        expected_proposals = []

        proposals = determine_active_proposals('LCO2019A-905')

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_proposals, proposals)

    def test_default_existing_active_lc(self):
        expected_num = 1
        expected_code_1 = 'LCO2019A-005'

        proposals = determine_active_proposals('lco2019a-005')

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_code_1, proposals[0])

    def test_include_epo_proposal(self):
        expected_num = 4
        expected_code_1 = 'LCO2019A-005'
        expected_code_2 = 'LCO2019A-008'
        expected_code_3 = 'LCOEPO2014B-010'
        expected_code_4 = 'LCOEngineering'

        proposals = determine_active_proposals(filter_proposals=False)

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_code_1, proposals[0])
        self.assertEqual(expected_code_2, proposals[1])
        self.assertEqual(expected_code_3, proposals[2])
        self.assertEqual(expected_code_4, proposals[3])

    def test_specific_epo_proposal(self):
        expected_num = 1
        expected_code_1 = 'LCOEPO2014B-010'

        proposals = determine_active_proposals('LCOEPO2014B-010')

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_code_1, proposals[0])

    def test_specific_skipped_proposal(self):
        expected_num = 1
        expected_code_1 = 'LCO2019A-008'

        proposals = determine_active_proposals('LCO2019A-008')

        self.assertEqual(expected_num, len(proposals))
        self.assertEqual(expected_code_1, proposals[0])


class TestBestStandardsView(TestCase):

    def setUp(self):
        self.precision = 2
        self.HA_hours = 3

    def test_march_default_HA(self):
        # Time is for March Equinox so anti-solar point is ~12h RA (=180 degrees)
        expected_min_ra = 180 - self.HA_hours*15
        expected_max_ra = 180 + self.HA_hours*15

        min_ra, max_ra = BestStandardsView.determine_ra_range(self, utc_dt=datetime(2019, 3, 20,  22, 00, 00))

        self.assertAlmostEqual(expected_min_ra, min_ra, self.precision)
        self.assertAlmostEqual(expected_max_ra, max_ra, self.precision)

    def test_march_HA1(self):
        self.HA_hours = 1
        # Time is for March Equinox so anti-solar point is ~12h RA (=180 degrees)
        expected_min_ra = 180 - self.HA_hours*15
        expected_max_ra = 180 + self.HA_hours*15

        min_ra, max_ra = BestStandardsView.determine_ra_range(self, utc_dt=datetime(2019, 3, 20,  22, 00, 00), HA_hours=self.HA_hours)

        self.assertAlmostEqual(expected_min_ra, min_ra, self.precision)
        self.assertAlmostEqual(expected_max_ra, max_ra, self.precision)

    def test_after_sept_equinox_default_HA(self):
        # Time is for September Equinox so anti-solar point is ~00h RA
        expected_min_ra = (0 - self.HA_hours*15) + 360
        expected_max_ra = 0 + self.HA_hours*15

        min_ra, max_ra = BestStandardsView.determine_ra_range(self, utc_dt=datetime(2019, 9, 23,  7, 40, 50))

        self.assertAlmostEqual(expected_min_ra, min_ra, self.precision)
        self.assertAlmostEqual(expected_max_ra, max_ra, self.precision)

    def test_before_sept_equinox_default_HA(self):
        # Time is for September Equinox so anti-solar point is ~00h RA
        expected_min_ra = (0 - self.HA_hours*15) + 360
        expected_max_ra = 0 + self.HA_hours*15

        min_ra, max_ra = BestStandardsView.determine_ra_range(self, utc_dt=datetime(2019, 9, 23,  7, 40, 30))

        self.assertAlmostEqual(expected_min_ra, min_ra, self.precision)
        self.assertAlmostEqual(expected_max_ra, max_ra, self.precision)


class TestFindSpec(TestCase):

    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': 'j5432',
                         'name': '455432',
                         'origin': 'A',
                         'source_type': 'N',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': True,
                         'urgency': None,
                         'epochofel': datetime(2019, 7, 31, 0, 0),
                         'orbit_rms': 0.46,
                         'orbinc': 31.23094,
                         'longascnode': 301.42266,
                         'argofperih': 22.30793,
                         'eccentricity': 0.3660154,
                         'meandist': 1.7336673,
                         'meananom': 352.55084,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.54,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(2003, 9, 7, 3, 7, 18),
                         'num_obs': 130,
                         'arc_length': 6209.0,
                         'not_seen': 3.7969329574421296,
                         'updated': True,
                         'ingest': datetime(2019, 7, 4, 5, 28, 39),
                         'update_time': datetime(2019, 7, 30, 19, 7, 35)
                        }
        self.test_body = Body.objects.create(**body_params)

        proposal_params = { 'code'   : 'LCOEngineering',
                                'title'  : 'LCOEngineering',
                                'active' : True
                              }
        self.eng_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        sblock_params = {
                        'body' : self.test_body,
                        'block_start' : datetime(2019, 7, 27, 8, 30),
                        'block_end'   : datetime(2019, 7, 27,19, 30),
                        'proposal' : self.eng_proposal,
                        'tracking_number' : '818566'
                        }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)

        block_params = {
                        'body' : self.test_body,
                        'superblock' : self.test_sblock,
                        'block_start' : datetime(2019, 7, 27, 8, 30),
                        'block_end'   : datetime(2019, 7, 27,19, 30),
                        'obstype' : Block.OPT_SPECTRA,
                        'request_number' : '1878696',
                        'num_exposures' : 1,
                        'exp_length' : 1800
                        }
        self.test_block = Block.objects.create(**block_params)

        frame_params = {
                         'block' : self.test_block,
                         'sitecode': 'E10',
                         'instrument': 'en12',
                         'filter': 'SLIT_30.0x6.0AS',
                         'filename': 'coj2m002-en12-20190727-0014-w00.fits',
                         'frameid' : 12272496,
                         'frametype' : Frame.SPECTRUM_FRAMETYPE,
                         'midpoint': datetime(2019, 7, 27, 15, 52, 29, 495000),

                        }
        self.test_flatframe = Frame.objects.create(**frame_params)

    @patch('core.views.lco_api_call', mock_archive_spectra_header)
    def test_local_data_no_tarball(self):
        settings.USE_S3 = False

        expected_date = '20190727'
        expected_path = os.path.join(expected_date, self.test_body.current_name() + '_' + self.test_block.request_number)

        date_obs, obj, req, path, prop = find_spec(self.test_block.pk)

        self.assertEqual(expected_date, date_obs)
        self.assertEqual(self.test_body.current_name(), obj)
        self.assertEqual(self.test_block.request_number, req)
        self.assertEqual(expected_path, path)
        self.assertEqual(self.eng_proposal.code, prop)

    @patch('core.views.lco_api_call', mock_archive_spectra_header)
    def test_local_data_with_tarball(self):

        with self.settings(MEDIA_ROOT=tempfile.mkdtemp()):
            expected_date = '20190727'
            expected_path = os.path.join(expected_date, self.test_body.current_name() + '_' + self.test_block.request_number)
            # os.makedirs(expected_date)
            fake_tar = os.path.join(expected_date, self.eng_proposal.code + '_' + self.test_block.request_number + '.tar.gz')

            date_obs, obj, req, path, prop = find_spec(self.test_block.pk)

            self.assertEqual(expected_date, date_obs)
            self.assertEqual(self.test_body.current_name(), obj)
            self.assertEqual(self.test_block.request_number, req)
            self.assertEqual(expected_path, path)
            self.assertEqual(self.eng_proposal.code, prop)

    @patch('core.views.lco_api_call', mock_archive_spectra_header)
    def test_S3_data(self):
        settings.USE_S3 = True
        settings.DATA_ROOT = None

        expected_date = '20190727'
        expected_path = os.path.join('', expected_date, self.test_body.current_name() + '_' + self.test_block.request_number)

        date_obs, obj, req, path, prop = find_spec(self.test_block.pk)

        self.assertEqual(expected_date, date_obs)
        self.assertEqual(self.test_body.current_name(), obj)
        self.assertEqual(self.test_block.request_number, req)
        self.assertEqual(expected_path, path)
        self.assertEqual(self.eng_proposal.code, prop)

    @patch('core.views.lco_api_call', mock_lco_api_fail)
    def test_S3_data(self):
        settings.USE_S3 = True
        settings.DATA_ROOT = None

        expected_results = ('', '', '', '', '')
        results = find_spec(self.test_block.pk)
        self.assertEqual(expected_results, results)


class TestFindAnalog(TestCase):

    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': 'j5432',
                         'name': '455432',
                         'origin': 'A',
                         'source_type': 'N',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': True,
                         'urgency': None,
                         'epochofel': datetime(2019, 7, 31, 0, 0),
                         'orbit_rms': 0.46,
                         'orbinc': 31.23094,
                         'longascnode': 301.42266,
                         'argofperih': 22.30793,
                         'eccentricity': 0.3660154,
                         'meandist': 1.7336673,
                         'meananom': 352.55084,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.54,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(2003, 9, 7, 3, 7, 18),
                         'num_obs': 130,
                         'arc_length': 6209.0,
                         'not_seen': 3.7969329574421296,
                         'updated': True,
                         'ingest': datetime(2019, 7, 4, 5, 28, 39),
                         'update_time': datetime(2019, 7, 30, 19, 7, 35)
                        }
        self.test_body = Body.objects.create(**body_params)

        statsrc_params = {
                         'name': '9 Cet',
                         'ra' : 0.5,
                         'dec' : -12.2,
                         'vmag' : 7.0,
                         'spectral_type' : 'G2.5V',
                         'source_type' : StaticSource.SOLAR_STANDARD
                        }
        self.solar_analog = StaticSource.objects.create(**statsrc_params)

        proposal_params = { 'code'   : 'LCOEngineering',
                                'title'  : 'LCOEngineering',
                                'active' : True
                              }
        self.eng_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        sblock_params = {
                        'body' : self.test_body,
                        'block_start' : datetime(2019, 7, 27, 8, 30),
                        'block_end'   : datetime(2019, 7, 27,19, 30),
                        'proposal' : self.eng_proposal,
                        'tracking_number' : '818566'
                        }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)

        block_params = {
                        'body' : self.test_body,
                        'superblock' : self.test_sblock,
                        'site' : 'coj',
                        'block_start' : datetime(2019, 7, 27, 8, 30),
                        'block_end'   : datetime(2019, 7, 27,19, 30),
                        'obstype' : Block.OPT_SPECTRA,
                        'request_number' : '1878696',
                        'num_observed' : 1,
                        'when_observed' : datetime(2019, 7, 27, 17, 15),
                        'num_exposures' : 1,
                        'exp_length' : 1800
                        }
        self.test_objblock = Block.objects.create(**block_params)

        block_params = {
                        'calibsource' : self.solar_analog,
                        'superblock' : self.test_sblock,
                        'site' : 'coj',
                        'block_start' : datetime(2019, 7, 27, 8, 30),
                        'block_end'   : datetime(2019, 7, 27,19, 30),
                        'obstype' : Block.OPT_SPECTRA_CALIB,
                        'request_number' : '1878697',
                        'num_exposures' : 1,
                        'exp_length' : 120
                        }
        self.test_calblock = Block.objects.create(**block_params)

        frame_params = {
                         'block' : self.test_objblock,
                         'sitecode': 'E10',
                         'instrument': 'en12',
                         'filter': 'SLIT_30.0x6.0AS',
                         'filename': 'coj2m002-en12-20190727-0014-w00.fits',
                         'frameid' : 12272496,
                         'frametype' : Frame.SPECTRUM_FRAMETYPE,
                         'midpoint': datetime(2019, 7, 27, 15, 52, 29, 495000),

                        }
        self.test_specframe = Frame.objects.create(**frame_params)

    def test_no_obsdate(self):
        expected_analog_list = []

        analog_list = find_analog(None, 'coj')

        self.assertEqual(expected_analog_list, analog_list)

    def test_obsdate_in_range(self):
        expected_analog_list = []

        analog_list = find_analog(self.test_objblock.when_observed+timedelta(days=1), 'coj')

        self.assertEqual(expected_analog_list, analog_list)


class TestBuildVisibilitySource(TestCase):

    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': 'j5432',
                         'name': '455432',
                         'origin': 'A',
                         'source_type': 'N',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': True,
                         'urgency': None,
                         'epochofel': datetime(2019, 7, 31, 0, 0),
                         'orbit_rms': 0.46,
                         'orbinc': 31.23094,
                         'longascnode': 301.42266,
                         'argofperih': 22.30793,
                         'eccentricity': 0.3660154,
                         'meandist': 1.7336673,
                         'meananom': 352.55084,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.54,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(2003, 9, 7, 3, 7, 18),
                         'num_obs': 130,
                         'arc_length': 6209.0,
                         'not_seen': 3.7969329574421296,
                         'updated': True,
                         'ingest': datetime(2019, 7, 4, 5, 28, 39),
                         'update_time': datetime(2019, 7, 30, 19, 7, 35)
                        }
        self.test_body = Body.objects.create(**body_params)

    def test_build_visibility_source(self):
        site_code = ['LSC', 'CPT', 'COJ', 'ELP', 'TFN', 'OGG']
        site_list = ['W85', 'K91', 'Q63', 'V37', 'Z21', 'F65']
        color_list = ['darkviolet', 'forestgreen', 'saddlebrown', 'coral', 'darkslategray', 'dodgerblue']
        d = datetime(2019, 10, 10, 0, 0, 0)
        step_size = '30 m'
        alt_limit = 30
        vis, emp = build_visibility_source(self.test_body, site_list, site_code, color_list, d, alt_limit, step_size)

        expected_vis = {'x': [0, 0, 0, 0, 0, 0],
                        'y': [0, 0, 0, 0, 0, 0],
                        'sun_rise': [10.210176124166827, 8.595746566072073, 6.370451769779303, 4.625122517784973, 9.381144729469522, 5.541420375081996],
                        'sun_set': [7.810348402674624, 6.239552075879727, 3.9706240482870996, 1.9634954084936207, 6.719517620178169, 2.879793265790644],
                        'obj_rise': [0.0, 0.0, 0.0, 0.7853981633974487, 5.366887449882563, 1.5707963267948966],
                        'obj_set': [0, 0, 0, 2.879793265790644, 7.592182246175334, 3.796091123087667],
                        'moon_rise': [1.0471975511965979, -0.5235987755982989, 3.534291735288517, 1.7016960206944711, 0.13089969389957457, 2.4870941840919194],
                        'moon_set': [3.4033920413889427, 1.7016960206944713, 5.759586531581287, 3.9269908169872414, 2.356194490192345, 4.974188368183839],
                        'moon_phase': [0.8706345970199544, 0.8651789635607248, 0.8701262242502456, 0.8701177903593142, 0.8645091870127206, 0.8712568525897345],
                        'colors': ['darkviolet', 'forestgreen', 'saddlebrown', 'coral', 'darkslategray', 'dodgerblue'],
                        'site': ['LSC', 'CPT', 'COJ', 'ELP', 'TFN', 'OGG'],
                        'obj_vis': [0, 0, 0, 3.5, 3.0, 3.5],
                        'max_alt': [0, 0, 0, 60, 57, 50],
                        'line_alpha': [0, 0, 0, 1, 1, 1]}

        for key in vis.keys():
            assertDeepAlmostEqual(self, expected_vis[key], vis[key])


class TestParsePortalErrors(SimpleTestCase):

    def setUp(self):
        self.no_parse_msg = "It was not possible to submit your request to the scheduler."
        self.no_extrainfo_msg = self.no_parse_msg + "\nAdditional information:"

        self.maxDiff = None

    def test_no_response(self):
        params = {}
        msg = parse_portal_errors(params)

        self.assertEqual(self.no_parse_msg, msg)

    def test_empty_response(self):
        params = {'error_msg': {}}
        msg = parse_portal_errors(params)

        self.assertEqual(self.no_parse_msg, msg)

    def test_bad_proposal(self):
        expected_msg = self.no_extrainfo_msg + '\nproposal: Invalid pk "foo" - object does not exist.'
        params = {'error_msg': {'proposal': ['Invalid pk "foo" - object does not exist.']}}

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)

    def test_no_visibility(self):
        expected_msg = self.no_extrainfo_msg + "\nrequests: non_field_errors: According to the constraints of the request, the target is never visible within the time window. Check that the target is in the nighttime sky. Consider modifying the time window or loosening the airmass or lunar separation constraints. If the target is non sidereal, double check that the provided elements are correct."
        params = {'error_msg': {'requests': [{'non_field_errors': ['According to the constraints of the request, the target is never visible within the time window. Check that the target is in the nighttime sky. Consider modifying the time window or loosening the airmass or lunar separation constraints. If the target is non sidereal, double check that the provided elements are correct.']}]}}

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)

    def test_no_visibility_bad_proposal(self):
        expected_msg = self.no_extrainfo_msg + "\nrequests: non_field_errors: According to the constraints of the request, the target is never visible within the time window. Check that the target is in the nighttime sky. Consider modifying the time window or loosening the airmass or lunar separation constraints. If the target is non sidereal, double check that the provided elements are correct."
        expected_msg += '\nproposal: Invalid pk "foo" - object does not exist.'

        params = {'error_msg': {'requests': [{'non_field_errors': ['According to the constraints of the request, the target is never visible within the time window. Check that the target is in the nighttime sky. Consider modifying the time window or loosening the airmass or lunar separation constraints. If the target is non sidereal, double check that the provided elements are correct.']}],
                                 'proposal': ['Invalid pk "foo" - object does not exist.']}
                  }

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)

    def test_multiple_blocks_same_name_error(self):
        expected_msg = self.no_extrainfo_msg
        expected_msg += '\nneox: Multiple Blocks for same day and site found'

        params = {'error_msg': {'neox': ['Multiple Blocks for same day and site found']}}

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)

    def test_no_proposal_permission(self):
        expected_msg = self.no_extrainfo_msg
        expected_msg += '\nneox: You do not have permission to schedule using proposal LCO20XXB-003'

        params = {'error_msg': {'neox': ['You do not have permission to schedule using proposal LCO20XXB-003']}}

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)

    def test_no_cadence_windows(self):
        expected_msg = self.no_extrainfo_msg
        expected_msg += '\nNo visible requests within cadence window parameters'

        params = {'error_msg' : "No visible requests within cadence window parameters" }

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)

    def test_semester_crossing(self):
        expected_msg = self.no_extrainfo_msg
        expected_msg += '\nrequests: windows: non_field_errors: The observation window does not fit within any defined semester.'

        params = {'error_msg': {'requests': [{'windows': [{'non_field_errors': ['The observation window does not fit within any defined semester.']}]}]}
        }

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)

    def test_muchfail(self):
        params = {'error_msg': {
                                'requests': [
                                    {
                                        'configurations': [
                                            {
                                                'instrument_configs': [
                                                    {
                                                        'exposure_time':['A valid number is required.']
                                                    }
                                                ],
                                                'target': {
                                                    'name': ['Please provide a name.'],
                                                    'ra': ['A valid number is required.'],
                                                    'dec': ['A valid number is required.']
                                                }
                                            }
                                        ],
                                        'windows': [
                                            {
                                                'non_field_errors': ['The observation window does not fit within any defined semester.']
                                            }
                                        ]
                                    },
                                    {
                                        'configurations':[
                                            {
                                                'instrument_configs': [
                                                    {
                                                        'exposure_time': ['A valid number is required.']
                                                    },
                                                    {
                                                        'exposure_time': ['A valid number is required.']
                                                    }
                                                ],
                                                'target': {
                                                    'name': ['Please provide a name.'],
                                                    'ra': ['A valid number is required.'],
                                                    'dec': ['A valid number is required.']
                                                }
                                            },
                                            {
                                                'instrument_configs': [
                                                    {
                                                        'exposure_time': ['A valid number is required.']
                                                    },
                                                    {
                                                        'exposure_time': ['A valid number is required.']
                                                    }
                                                ],
                                                'target': {
                                                    'name': ['Please provide a name.'],
                                                    'ra': ['A valid number is required.'],
                                                    'dec': ['A valid number is required.']
                                                }
                                            }
                                        ]
                                    }
                                ],
                                'name': ['Please provide a name.'],
                                'proposal': ['Please provide a proposal.']
                            }
                    }

        expected_msg = self.no_extrainfo_msg + "\n".join(["",
                        "requests: configurations: instrument_configs: exposure_time: A valid number is required.",
                        "target: name: Please provide a name.",
                        "ra: A valid number is required.",
                        "dec: A valid number is required.",
                        "windows: non_field_errors: The observation window does not fit within any defined semester.",
                        "configurations: instrument_configs: exposure_time: A valid number is required.",
                        "exposure_time: A valid number is required.",
                        "target: name: Please provide a name.",
                        "ra: A valid number is required.",
                        "dec: A valid number is required.",
                        "instrument_configs: exposure_time: A valid number is required.",
                        "exposure_time: A valid number is required.",
                        "target: name: Please provide a name.",
                        "ra: A valid number is required.",
                        "dec: A valid number is required.",
                        "name: Please provide a name.",
                        "proposal: Please provide a proposal."])

        msg = parse_portal_errors(params)

        self.assertEqual(expected_msg, msg)


class TestCreateLatexTable(TestCase):

    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': None,
                         'name': '2005 QN173',
                         'origin': 'O',
                         'source_type': 'A',
                         'source_subtype_1': 'M',
                         'source_subtype_2': None,
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': False,
                         'urgency': None,
                         'epochofel': datetime(2020, 12, 17, 0, 0),
                         'orbit_rms': 0.65,
                         'orbinc': 0.06654,
                         'longascnode': 174.67813,
                         'argofperih': 145.83613,
                         'eccentricity': 0.2260268,
                         'meandist': 3.0664,
                         'meananom': 332.73044,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 16.02,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(2000, 11, 27, 0, 0),
                         'num_obs': 292,
                         'arc_length': 7149.0,
                         'not_seen': 380.627780639225,
                         'updated': True,
                         'ingest': datetime(2021, 7, 9, 15, 4, 0, 238661),
                         'update_time': datetime(2020, 6, 24, 0, 0)}

        self.test_body = Body.objects.create(**body_params)
        
        proposal_params = { 'code'   : 'KEY202B-009',
                            'title'  : 'LOOK Project',
                            'active' : True
                          }
        self.key_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        sblock_params = {
                        'body' : self.test_body,
                        'cadence' : False,
                        'block_start' : datetime(2021, 7, 4, 3, 0),
                        'block_end'   : datetime(2021, 7, 4,19, 30),
                        'proposal' : self.key_proposal,
                        'groupid' : '2005 QN173_E10-20210704_spectra',
                        'tracking_number' : '1255400',
                        }
        self.test_sblock_spectra = SuperBlock.objects.create(**sblock_params)

        self.block_spectra_params = {
                                'body' : self.test_body,
                                'superblock' : self.test_sblock_spectra,
                                'telclass' : '2m0',
                                'site' : 'coj',
                                'block_start' : datetime(2021, 7, 4, 3, 30),
                                'block_end'   : datetime(2021, 7, 4, 19, 30),
                                'obstype' : Block.OPT_SPECTRA,
                                'request_number' : 4242,
                                'num_observed' : 1,
                                'when_observed' : datetime(2021, 7, 4, 6, 15),
                                'num_exposures' : 1,
                                'exp_length' : 3600
                               }
        self.test_specblock = Block.objects.create(**self.block_spectra_params)

        self.frame_params = { 'block'    : self.test_specblock,
                              'filename' : 'coj2m002-en99-20210704-0042-e90.fits',
                              'sitecode' : 'E10',
                              'frametype': Frame.SPECTRUM_FRAMETYPE,
                              'filter' : 'SLIT_30.0x6.0AS',
                              'exptime' : 3600,
                              'midpoint' : datetime(2021, 7, 4, 6, 30)
                            }
        test_frame = Frame.objects.create(**self.frame_params)

        sblock_params = {
                        'body' : self.test_body,
                        'cadence' : True,
                        'block_start' : datetime(2021, 7, 1, 19, 0),
                        'block_end'   : datetime(2019, 7, 23,19, 30),
                        'proposal' : self.key_proposal,
                        'tracking_number' : '1255300',
                        'period' : 7*24,
                        'jitter' : 72
                        }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)

        for sitecode, day in zip(['K91', 'K93', 'K92'], range(7,22,7)):
            self.block_params = {
                                'body' : self.test_body,
                                'superblock' : self.test_sblock,
                                'site' : 'cpt',
                                'block_start' : datetime(2021, 7, day, 22, 30),
                                'block_end'   : datetime(2021, 7, day, 6, 30),
                                'obstype' : Block.OPT_IMAGING,
                                'request_number' : day*1000,
                                'num_observed' : 1,
                                'when_observed' : datetime(2021, 7, day, 23, 15),
                                'num_exposures' : 4,
                                'exp_length' : 120
                               }
            self.test_objblock = Block.objects.create(**self.block_params)

            for i, obs_filter in enumerate(['gp', 'gp', 'rp', 'rp']):
                self.frame_params = { 'block'    : self.test_objblock,
                                      'filename' : f'cpt1m003-fa99-202107{day}-{42+i:04d}-e91.fits',
                                      'sitecode' : sitecode,
                                      'frametype': Frame.BANZAI_RED_FRAMETYPE,
                                      'exptime' : 120,
                                      'filter' : obs_filter,
                                      'midpoint' : datetime(2021, 7, day, 3, (i*2)+1, 0)
                                    }

                test_frame = Frame.objects.create(**self.frame_params)

        self.table_hdr = [ '\\begin{table}' + os.linesep,
                           '\\caption{Table of observations for 2005 QN173 with LCOGT}' + os.linesep,
                           '\\begin{tabular}{cccccccc}' + os.linesep,
                           '\\hline \\hline' + os.linesep,
                           'Block Start & Block End & Site & Telclass & MPC Site Code & Observation Type & Filters & Num Exposures \\\\' + os.linesep,
                           '\\hline' + os.linesep
                         ]

        self.deluxetable_hdr = [\
                           '\\begin{deluxetable}{cccccccc}' + os.linesep,
                           '\\tablecaption{Table of observations for 2005 QN173 with LCOGT}' + os.linesep,
                           r'\tablehead{\colhead{Block Start} & \colhead{Block End} & \colhead{Site} & \colhead{Telclass} & \colhead{MPC Site Code} & \colhead{Observation Type} & \colhead{Filters} & \colhead{Num Exposures}}'+ os.linesep,
                           '\\startdata' + os.linesep
                         ]

        self.table_hdr_no_obstype = \
                         [ '\\begin{table}' + os.linesep,
                           '\\caption{Table of observations for 2005 QN173 with LCOGT}' + os.linesep,
                           '\\begin{tabular}{ccccccc}' + os.linesep,
                           '\\hline \\hline' + os.linesep,
                           'Block Start & Block End & Site & Telclass & MPC Site Code & Filters & Num Exposures \\\\' + os.linesep,
                           '\\hline' + os.linesep
                         ]

        self.table_ftr = [
                           '\\hline' + os.linesep,
                           '\\end{tabular}' + os.linesep,
                           '' + os.linesep,
                           '\\end{table}' + os.linesep
                         ]

        self.deluxetable_ftr = [
                           '\\enddata' + os.linesep,
                           '' + os.linesep,
                           '\\end{deluxetable}' + os.linesep
                         ]

        self.expected_colnames = ['Block Start', 'Block End', 'Site', 'Telclass', 'MPC Site Code', 'Observation Type', 'Filters', 'Num Exposures']

        self.maxDiff = None

    def test_table_by_body(self):

        lines = [
                  "2021-07-04 06:00 & 2021-07-04 07:00 & coj & 2m0 & E10 & Opt. spectra & $30.0\\arcsec\\times6.0\\arcsec$ slit & 0/1 \\\\" + os.linesep,
                  "2021-07-07 03:00 & 2021-07-07 03:08 & cpt & 1m0 & K91 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-14 03:00 & 2021-07-14 03:08 & cpt & 1m0 & K93 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-21 03:00 & 2021-07-21 03:08 & cpt & 1m0 & K92 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                ]

        expected_lines = self.table_hdr + lines + self.table_ftr

        self.assertEqual(1, Body.objects.all().count())
        self.assertEqual(2, SuperBlock.objects.all().count())
        self.assertEqual(4, Block.objects.all().count())
        self.assertEqual(13, Frame.objects.all().count())
        
        out_buf = create_latex_table(self.test_body, return_table=False)
        with open(os.path.join(tempfile.mkdtemp(), 'Didymos_obs_no_obstype.tex'), 'w') as fd:
            out_buf.seek(0)
            shutil.copyfileobj(out_buf, fd)

        out_buf.seek(0)

        for i, line in enumerate(out_buf.readlines()):
            self.assertEqual(expected_lines[i], line)

    def test_deluxetable_by_body(self):

        lines = [
                  "2021-07-04 06:00 & 2021-07-04 07:00 & coj & 2m0 & E10 & Opt. spectra & $30.0\\arcsec\\times6.0\\arcsec$ slit & 0/1 \\\\" + os.linesep,
                  "2021-07-07 03:00 & 2021-07-07 03:08 & cpt & 1m0 & K91 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-14 03:00 & 2021-07-14 03:08 & cpt & 1m0 & K93 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-21 03:00 & 2021-07-21 03:08 & cpt & 1m0 & K92 & Opt. imaging & g',r' & 4/4" + os.linesep,
                ]

        expected_lines = self.deluxetable_hdr + lines + self.deluxetable_ftr

        self.assertEqual(1, Body.objects.all().count())
        self.assertEqual(2, SuperBlock.objects.all().count())
        self.assertEqual(4, Block.objects.all().count())
        self.assertEqual(13, Frame.objects.all().count())

        out_buf = create_latex_table(self.test_body, return_table=False, deluxetable=True)
        # with open(os.path.join('/tmp', 'Didymos_obs_no_obstype.tex'), 'w') as fd:
            # out_buf.seek(0)
            # shutil.copyfileobj(out_buf, fd)

        out_buf.seek(0)

        for i, line in enumerate(out_buf.readlines()):
            self.assertEqual(expected_lines[i], line)

    def test_table_by_name(self):

        lines = [
                  "2021-07-04 06:00 & 2021-07-04 07:00 & coj & 2m0 & E10 & Opt. spectra & $30.0\\arcsec\\times6.0\\arcsec$ slit & 0/1 \\\\" + os.linesep,
                  "2021-07-07 03:00 & 2021-07-07 03:08 & cpt & 1m0 & K91 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-14 03:00 & 2021-07-14 03:08 & cpt & 1m0 & K93 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-21 03:00 & 2021-07-21 03:08 & cpt & 1m0 & K92 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                ]

        expected_lines = self.table_hdr + lines + self.table_ftr

        self.assertEqual(1, Body.objects.all().count())
        self.assertEqual(2, SuperBlock.objects.all().count())
        self.assertEqual(4, Block.objects.all().count())
        self.assertEqual(13, Frame.objects.all().count())
        
        out_buf = create_latex_table(self.test_body.name, return_table=False)
        out_buf.seek(0)

        for i, line in enumerate(out_buf.readlines()):
            self.assertEqual(expected_lines[i], line)

    def test_return_table(self):

        lines = [
                  "2021-07-04 06:00 & 2021-07-04 07:00 & coj & 2m0 & E10 & Opt. spectra & $30.0\\arcsec\\times6.0\\arcsec$ slit & 0/1 \\\\" + os.linesep,
                  "2021-07-07 03:00 & 2021-07-07 03:08 & cpt & 1m0 & K91 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-14 03:00 & 2021-07-14 03:08 & cpt & 1m0 & K93 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-21 03:00 & 2021-07-21 03:08 & cpt & 1m0 & K92 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                ]

        expected_lines = self.table_hdr + lines + self.table_ftr

        self.assertEqual(1, Body.objects.all().count())
        self.assertEqual(2, SuperBlock.objects.all().count())
        self.assertEqual(4, Block.objects.all().count())
        self.assertEqual(13, Frame.objects.all().count())

        out_buf, data_table = create_latex_table(self.test_body.name, return_table=True)
        out_buf.seek(0)

        for i, line in enumerate(out_buf.readlines()):
            self.assertEqual(expected_lines[i], line)

        self.assertFalse(type(data_table) == dict)
        self.assertEqual(Block.objects.all().count(), len(data_table))
        self.assertEqual(self.expected_colnames, data_table.colnames)

    def test_table_filter_trans(self):

        # Create MuSCAT block
        self.test_objblock.id = None
        self.test_objblock.site = 'ogg'
        self.test_objblock.telclass = '2m0'
        self.test_objblock.block_start : datetime(2021, 7, 22, 5, 30)
        self.test_objblock.block_end : datetime(2021, 7, 22, 15, 30)
        self.test_objblock.when_observed : datetime(2021, 7, 22, 15, 15)
        self.test_objblock.save()

        for i, obs_filter in enumerate(['gp', 'rp', 'ip', 'zs']):
            frame_params = { 'block'    : self.test_objblock,
                                  'filename' : f'ogg2m001-ep99-20210822-{42+i:04d}-e91.fits',
                                  'sitecode' : 'F65',
                                  'frametype': Frame.BANZAI_RED_FRAMETYPE,
                                  'exptime' : 60,
                                  'filter' : obs_filter,
                                  'midpoint' : datetime(2021, 7, 22, 15, i*2+1, 0)
                                }

            test_frame = Frame.objects.create(**frame_params)

        lines = [
                  "2021-07-07 03:00 & 2021-07-07 03:08 & cpt & 1m0 & K91 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-14 03:00 & 2021-07-14 03:08 & cpt & 1m0 & K93 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-21 03:00 & 2021-07-21 03:08 & cpt & 1m0 & K92 & Opt. imaging & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-22 15:00 & 2021-07-22 15:06 & ogg & 2m0 & F65 & Opt. imaging & g',r',i',$\mathrm{z_{s}}$ & 4/4 \\\\" + os.linesep,
                ]

        expected_lines = self.table_hdr + lines + self.table_ftr

        self.assertEqual(1, Body.objects.all().count())
        self.assertEqual(2, SuperBlock.objects.all().count())
        self.assertEqual(5, Block.objects.all().count())
        self.assertEqual(17, Frame.objects.all().count())

    def test_table_filter_trans_no_obstype(self):

        # Remove spectra SuperBlock
        self.test_sblock_spectra.delete()

        # Create MuSCAT block
        self.test_objblock.id = None
        self.test_objblock.site = 'ogg'
        self.test_objblock.telclass = '2m0'
        self.test_objblock.block_start : datetime(2021, 7, 22, 5, 30)
        self.test_objblock.block_end : datetime(2021, 7, 22, 15, 30)
        self.test_objblock.when_observed : datetime(2021, 7, 22, 15, 15)
        self.test_objblock.save()

        for i, obs_filter in enumerate(['gp', 'rp', 'ip', 'zs']):
            frame_params = { 'block'    : self.test_objblock,
                                  'filename' : f'ogg2m001-ep99-20210822-{42+i:04d}-e91.fits',
                                  'sitecode' : 'F65',
                                  'frametype': Frame.BANZAI_RED_FRAMETYPE,
                                  'exptime' : 60,
                                  'filter' : obs_filter,
                                  'midpoint' : datetime(2021, 7, 22, 15, i*2+1, 0)
                                }

            test_frame = Frame.objects.create(**frame_params)

        lines = [
                  "2021-07-07 03:00 & 2021-07-07 03:08 & cpt & 1m0 & K91 & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-14 03:00 & 2021-07-14 03:08 & cpt & 1m0 & K93 & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-21 03:00 & 2021-07-21 03:08 & cpt & 1m0 & K92 & g',r' & 4/4 \\\\" + os.linesep,
                  "2021-07-22 15:00 & 2021-07-22 15:07 & ogg & 2m0 & F65 & g',r',i',$\mathrm{z_{s}}$ & 4/4 \\\\" + os.linesep,
                ]

        expected_lines = self.table_hdr_no_obstype + lines + self.table_ftr

        self.assertEqual(1, Body.objects.all().count())
        self.assertEqual(1, SuperBlock.objects.all().count())
        self.assertEqual(4, Block.objects.all().count())
        self.assertEqual(16, Frame.objects.all().count())

        out_buf, data_table = create_latex_table(self.test_body.name, return_table=True)
        out_buf.seek(0)

        for i, line in enumerate(out_buf.readlines()):
            self.assertEqual(expected_lines[i], line)

        self.assertFalse(type(data_table) == dict)
        self.assertEqual(Block.objects.all().count(), len(data_table))
        self.expected_colnames.remove('Observation Type')
        self.assertEqual(self.expected_colnames, data_table.colnames)

@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestDisplayDataproduct(TestCase):
    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': 'j5432',
                         'name': '455432',
                         'origin': 'A',
                         'source_type': 'N',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': True,
                         'urgency': None,
                         'epochofel': datetime(2019, 7, 31, 0, 0),
                         'orbit_rms': 0.46,
                         'orbinc': 31.23094,
                         'longascnode': 301.42266,
                         'argofperih': 22.30793,
                         'eccentricity': 0.3660154,
                         'meandist': 1.7336673,
                         'meananom': 352.55084,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.54,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(2003, 9, 7, 3, 7, 18),
                         'num_obs': 130,
                         'arc_length': 6209.0,
                         'not_seen': 3.7969329574421296,
                         'updated': True,
                         'ingest': datetime(2019, 7, 4, 5, 28, 39),
                         'update_time': datetime(2019, 7, 30, 19, 7, 35)
                        }
        self.test_body = Body.objects.create(**body_params)

        proposal_params = {'code': 'LCOEngineering',
                           'title': 'LCOEngineering',
                           'active': True
                           }
        self.eng_proposal, created = Proposal.objects.get_or_create(**proposal_params)

        sblock_params = {
                        'body': self.test_body,
                        'block_start': datetime(2019, 7, 27, 8, 30),
                        'block_end': datetime(2019, 7, 27,19, 30),
                        'proposal': self.eng_proposal,
                        'tracking_number': '818566'
                        }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)

        block_params = {
                        'body': self.test_body,
                        'superblock': self.test_sblock,
                        'site': 'coj',
                        'block_start': datetime(2019, 7, 27, 8, 30),
                        'block_end': datetime(2019, 7, 27, 19, 30),
                        'obstype': Block.OPT_IMAGING,
                        'request_number': '1878696',
                        'num_observed': 1,
                        'when_observed': datetime(2019, 7, 27, 17, 15),
                        'num_exposures': 1,
                        'exp_length': 1800
                        }
        self.test_block = Block.objects.create(**block_params)

        frame_params = {'sitecode': 'K92',
                        'instrument': 'kb76',
                        'filter': 'w',
                        'filename': 'banzai_test_frame.fits',
                        'exptime': 225.0,
                        'midpoint': datetime(2016, 8, 2, 2, 17, 19),
                        'block': self.test_block,
                        'zeropoint': -99,
                        'zeropoint_err': -99,
                        'fwhm': 2.390,
                        'frametype': 0,
                        'rms_of_fit': 0.3,
                        'nstars_in_fit': -4,
                        }
        self.test_frame, created = Frame.objects.get_or_create(**frame_params)

        block2_params = {
            'body': self.test_body,
            'superblock': self.test_sblock,
            'site': 'coj',
            'block_start': datetime(2019, 7, 27, 8, 30),
            'block_end': datetime(2019, 7, 27, 19, 30),
            'obstype': Block.OPT_SPECTRA,
            'request_number': '1878696',
            'num_observed': 1,
            'when_observed': datetime(2019, 7, 27, 17, 15),
            'num_exposures': 1,
            'exp_length': 1800
        }
        self.test_block2 = Block.objects.create(**block2_params)

    def test_display_movie(self):
        # test empty response
        request = ''
        response = display_movie(request, self.test_block.id)
        self.assertEqual(b'', response.content)
        # ALCDEF Only (superblock)
        file_name = 'test_SB_ALCDEF.txt'
        file_content = "some text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)
        response = display_movie(request, self.test_block.id)
        self.assertEqual(b'', response.content)
        # build movie
        fits = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        frames = [fits, fits, fits, fits, fits]
        movie_file = make_gif(frames, sort=False, init_fr=100, out_path=settings.MEDIA_ROOT, center=3, progress=False)
        save_dataproduct(obj=self.test_block, filepath=movie_file, filetype=DataProduct.FRAME_GIF)
        response = display_movie(request, self.test_block.id)
        self.assertIn(b'GIF', response.content)

        # test fits only, no gif
        save_to_default(fits, os.path.abspath(os.path.join('photometrics', 'tests')))
        fits_path = os.path.basename(fits)
        save_dataproduct(obj=self.test_block2, filepath=fits_path, filetype=DataProduct.FITS_SPECTRA)
        response = display_movie(request, self.test_block2.id)
        self.assertEqual(b'', response.content)
        # check Guider gif
        save_dataproduct(obj=self.test_block2, filepath=movie_file, filetype=DataProduct.GUIDER_GIF)
        response = display_movie(request, self.test_block2.id)
        self.assertIn(b'GIF', response.content)

    def test_display_text(self):
        # test non-existant DP
        request = ''
        with self.assertRaises(Http404) as context:
            response = display_textfile(request, 0)
            self.assertTrue("Dataproduct does not exist." in str(context.exception))
        # create ALCDEF
        file_name = 'test_SB_ALCDEF.txt'
        file_content = "some text here"
        save_dataproduct(obj=self.test_sblock, filepath=None, filetype=DataProduct.ALCDEF_TXT, filename=file_name, content=file_content)
        dp = DataProduct.objects.filter(filetype=DataProduct.ALCDEF_TXT)
        response = display_textfile(request, dp[0].id)
        self.assertEqual(b"some text here", response.content)


class TestRunSExtractorMakeCatalog(ExternalCodeUnitTest):

    def setUp(self):
        # Copying over some files to the temp directory to manipulate
        super(TestRunSExtractorMakeCatalog, self).setUp()

        """banzai_test_frame.fits"""
        # This image DOES NOT have a 'L1ZP' keyword in the header
        test_banzai_file = os.path.join(self.testfits_dir, 'banzai_test_frame.fits')
        # Create new output name closer to normal use
        output_filename = 'banzai-test-frame-e91.fits'
        shutil.copy(os.path.abspath(test_banzai_file), os.path.join(self.test_dir, output_filename))
        self.test_banzai_file = os.path.join(self.test_dir, output_filename)

        """banzai_test_frame.fits.fz"""
        # This image DOES NOT have a 'L1ZP' keyword in the header
        test_banzai_comp_file = os.path.join(self.testfits_dir, 'banzai_test_frame.fits.fz')
        # Create new output name closer to normal use
        output_filename = 'banzai-test-frame-e91.fits.fz'
        shutil.copy(os.path.abspath(test_banzai_comp_file), os.path.join(self.test_dir, output_filename))
        self.test_banzai_comp_file = os.path.join(self.test_dir, output_filename)

        # Decompress
        # funpack_fits_file(self.test_banzai_comp_file, all_hdus=True)
        # self.test_banzai_comp_file = os.path.join(self.test_dir, os.path.basename('banzai_test_frame.fits'))

        self.remove = True

    def tearDown(self):
        super(TestRunSExtractorMakeCatalog, self).tearDown()
        if self.remove is False:
            print(f"Not removing {self.test_dir}")

    def test1(self):
        expected_status = 0
        expected_ldac_catalog = self.test_banzai_file.replace('e91.fits', 'e91_ldac.fits')

        status, new_ldac_catalog = run_sextractor_make_catalog(self.source_dir, self.test_dir, self.test_banzai_file)

        self.assertEqual(expected_status, status)
        self.assertTrue(os.path.exists(self.test_banzai_file))
        self.assertTrue(os.path.exists(new_ldac_catalog))
        self.assertEqual(expected_ldac_catalog, new_ldac_catalog)

class TestSummarizeBlockQuality(TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.dataroot = self.test_dir

        staticsrc_params = {
                             'name': 'Didymos COJ 2024 Field v2 #34',
                             'ra': 260.722915,
                             'dec': -28.64188,
                             'vmag': 9.0,
                             'spectral_type': '',
                             'source_type': 16,
                           }
        self.ref_field1 = StaticSource.objects.create(**staticsrc_params)

        proposal_params = { 'code' : 'LCOEngineering', }
        self.proposal = Proposal.objects.create(**proposal_params)

        sblock_params = {
                         'cadence': False,
                         'rapid_response': False,
                         'body': None,
                         'calibsource': self.ref_field1,
                         'proposal': self.proposal,
                         'block_start': datetime(2024, 7, 12, 0, 0),
                         'block_end': datetime(2024, 7, 12, 23, 59, 59),
                         'groupid': 'Didymos COJ 2024 Field v2 #34 try2',
                         'tracking_number': '2003076',
                         'period': None,
                         'jitter': None,
                         'timeused': 804.0,
                         'active': False}
        self.sblock = SuperBlock.objects.create(**sblock_params)

        block_params = {
                         'telclass': '2m0',
                         'site': 'coj',
                         'body': None,
                         'calibsource': self.ref_field1,
                         'superblock': self.sblock,
                         'obstype': 0,
                         'block_start': datetime(2024, 7, 12, 0, 0),
                         'block_end': datetime(2024, 7, 12, 23, 59, 59),
                         'request_number': '3586212',
                         'num_exposures': 9,
                         'exp_length': 60.0,
                         'num_observed': 1,
                         'when_observed': datetime(2024, 7, 12, 11, 36, 43),
                         'active': False,
                         'reported': False,
                         'when_reported': None,
                         'tracking_rate': 0}
        self.block = Block.objects.create(**block_params)

        frame_params = {
                         'sitecode': 'E10',
                         'instrument': 'ep06',
                         'filter': 'gp',
                         'filename': 'coj2m002-ep06-20240712-0056-e92.fits',
                         'exptime': 60.0,
                         'midpoint': datetime(2024, 7, 12, 11, 36, 20),
                         'block': self.block,
                         'quality': ' ',
                         'zeropoint': -99.0,
                         'zeropoint_err': 0.03,
                         'zeropoint_src': 'BANZAI',
                         'fwhm': 4.25,
                         'frametype': 92,
                         'rms_of_fit': 0.15,
                         'nstars_in_fit': 18.0,
                         'astrometric_catalog': 'GAIA-DR2',
                         'photometric_catalog': ' '}
        self.test_frames = []
        for camera, obs_filter in zip(['ep06', 'ep07', 'ep08', 'ep09'], ['gp', 'rp', 'ip', 'zs']):
            frame_params['instrument'] = camera
            frame_params['filter'] = obs_filter
            frame_params['filename'] = f'coj2m002-{camera}-20240712-0056-e92.fits'
            camera_num = int(camera[-1])
            frame_params['nstars_in_fit'] = camera_num * 4
            frame_params['zeropoint'] = 24.0 + 1.0-camera_num / 10.0
            self.test_frames.append(Frame.objects.create(**frame_params))

        self.test_qc_table = Table.read(os.path.join('core', 'tests', 'data', 'test_block_summary_table.ecsv'), format='ascii.ecsv')

        self.remove = True
        self.debug_print = False

        self.maxDiff = None

    def tearDown(self):
        if self.remove:
            try:
                files_to_remove = glob(os.path.join(self.test_dir, '*'))
                for file_to_rm in files_to_remove:
                    os.remove(file_to_rm)
            except OSError:
                print("Error removing files in temporary test directory", self.test_dir)
            try:
                os.rmdir(self.test_dir)
                if self.debug_print:
                    print("Removed", self.test_dir)
            except OSError:
                print("Error removing temporary test directory", self.test_dir)
        else:
            print("Not removing. Temporary test directory=", self.test_dir)

    def compare_tables(self, expected_table, table, column=None, num_to_check=None, precision=6):

        columns = [column,]
        if column is None:
            columns = expected_table.colnames

        if num_to_check is None:
            num_to_check = len(expected_table)-1

        for i in range(0, num_to_check+1):
            for column in columns:
                self.assertAlmostEqual(expected_table[column][i], table[column][i], precision)

    def test_no_obs_blocks(self):

        qc_table = summarize_block_quality(self.dataroot, [])

        self.assertEqual(None, qc_table)

    def test_obs_blocks(self):

        qc_table = summarize_block_quality(self.dataroot, self.block)

        self.assertEqual(len(self.test_qc_table), len(qc_table))
        self.compare_tables(self.test_qc_table, qc_table)

class TestPerformAperPhotometry(TestCase):

    def setUp(self):

        self.framedir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'hotpants_test_frame.fits'
        self.test_file_path = os.path.join(self.framedir, self.test_file)
        self.test_file_rms = 'hotpants_test_frame.rms.fits'
        self.test_file_path_rms = os.path.join(self.framedir, self.test_file)

#       self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir =  '/tmp/tmp_neox_fjody5q5' #tempfile.mkdtemp(prefix='tmp_neox_')

        self.test_output_dir = os.path.join(self.test_dir, '20240610')
        os.makedirs(self.test_output_dir, exist_ok=True)

        body_params = {
                         'id': 36254,
                         'provisional_name': None,
                         'provisional_packed': None,
                         'name': '65803',
                         'origin': 'N',
                         'source_type': 'N',
                         'source_subtype_1': 'N3',
                         'source_subtype_2': 'PH',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': False,
                         'fast_moving': False,
                         'urgency': None,
                         'epochofel': datetime(2021, 2, 25, 0, 0),
                         'orbit_rms': 0.56,
                         'orbinc': 3.40768,
                         'longascnode': 73.20234,
                         'argofperih': 319.32035,
                         'eccentricity': 0.3836409,
                         'meandist': 1.6444571,
                         'meananom': 77.75787,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.27,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(1996, 4, 11, 0, 0),
                         'num_obs': 829,
                         'arc_length': 7305.0,
                         'not_seen': 2087.29154187494,
                         'updated': True,
                         'ingest': datetime(2018, 8, 14, 17, 45, 42),
                         'update_time': datetime(2021, 3, 1, 19, 59, 56, 957500)
                         }

        self.test_body, created = Body.objects.get_or_create(**body_params)

        desig_params = { 'body' : self.test_body, 'value' : 'Didymos', 'desig_type' : 'N', 'preferred' : True, 'packed' : False}
        test_desig, created = Designations.objects.get_or_create(**desig_params)
        desig_params['value'] = '65803'
        desig_params['desig_type'] = '#'
        test_desig, created = Designations.objects.get_or_create(**desig_params)

        block_params = {
                         'body' : self.test_body,
                         'request_number' : '12345',
                         'block_start' : datetime(2024, 6, 10, 0, 40),
                         'block_end' : datetime(2024, 6, 10, 17, 59),
                         'obstype' : Block.OPT_IMAGING,
                         'num_observed' : 1
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)
        # Second block with no frames attached
        block_params['num_observed'] = 0
        self.test_block2, created = Block.objects.get_or_create(**block_params)

        midpoints_for_good_elevs = []
        for i in range (0, 28):
            desired_midpoint = datetime(2024, 6, 10, 17, 2 * i)
            midpoints_for_good_elevs.append(desired_midpoint)

        frame_params = {
                         'sitecode' : 'E10',
                         'instrument' : 'ep07',
                         'exptime' : 170.0,
                         'filter' : 'rp',
                         'block' : self.test_block,
                         'frametype' : Frame.BANZAI_RED_FRAMETYPE,
                         'fwhm': 2.7,
                         'zeropoint' : 27.0,
                         'zeropoint_err' : 0.03,
                         'midpoint' : block_params['block_start'] + timedelta(minutes=5)
                       }
        #print(f"filter {frame_params['filter']}")
        i = 0
        self.test_banzai_files = []
        source_details = { 45234032 : {'mag' : 14.8447, 'err_mag' : 0.0054, 'flags' : 0},
                           45234584 : {'mag' : 14.8637, 'err_mag' : 0.0052, 'flags' : 3},
                           45235052 : {'mag' : 14.8447, 'err_mag' : 0.0051, 'flags' : 0}
                         }
        ra = [0, 283.50961, 283.50922, 283.50883]
        dec = [0, -25.07526, -25.07538, -25.07550]
        for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
            #print(f"FRAME NUM {frame_num, i}")
            i += 1
            frame_params['filename'] = f"coj2m002-ep07-20240610-{frame_num:04d}-e91.fits"
            frame_params['midpoint'] = midpoints_for_good_elevs[i]
            frame_params['frameid'] = frameid
            self.e91_frame, created = Frame.objects.get_or_create(**frame_params)
            #print(self.e91_frame.filename)
            # Create NEOX_RED_FRAMETYPE type also
            red_frame_params = frame_params.copy()
            red_frame_params['frametype'] = Frame.NEOX_RED_FRAMETYPE
            red_frame_params['filename'] = red_frame_params['filename'].replace('e91', 'e92')
            self.e92_frame, created = Frame.objects.get_or_create(**red_frame_params)
            #print(self.e92_frame.filename)
            # Create NEOX_SUB_FRAMETYPE type also
            sub_frame_params = frame_params.copy()
            sub_frame_params['frametype'] = Frame.NEOX_SUB_FRAMETYPE
            sub_frame_params['filename'] = red_frame_params['filename'].replace('e92', 'e93')
            self.e93_frame, created = Frame.objects.get_or_create(**sub_frame_params)
            #print(self.e93_frame.filename)

            cat_source = source_details[frameid]
            source_params = { 'body' : self.test_body,
                              'frame' : self.e93_frame,
                              'obs_ra' : 208.728,
                              'obs_dec' : -10.197,
                              'obs_mag' : cat_source['mag'],
                              'err_obs_ra' : 0.0003,
                              'err_obs_dec' : 0.0003,
                              'err_obs_mag' : cat_source['err_mag'],
                              'astrometric_catalog' : self.e93_frame.astrometric_catalog,
                              'photometric_catalog' : self.e93_frame.photometric_catalog,
                              'aperture_size' : 10*0.389,
                              'snr' : 1/cat_source['err_mag'],
                              'flags' : cat_source['flags']
                            }
            source, created = SourceMeasurement.objects.get_or_create(**source_params)
            source_params = { 'frame' : self.e93_frame,
                              'obs_x' : 2048+frame_num/10.0,
                              'obs_y' : 2043-frame_num/10.0,
                              'obs_ra' : 208.728,
                              'obs_dec' : -10.197,
                              'obs_mag' : cat_source['mag'],
                              'err_obs_ra' : 0.0003,
                              'err_obs_dec' : 0.0003,
                              'err_obs_mag' : cat_source['err_mag'],
                              'background' : 42,
                              'major_axis' : 3.5,
                              'minor_axis' : 3.25,
                              'position_angle' : 42.5,
                              'ellipticity' : 0.3711,
                              'aperture_size' : 10*0.389,
                              'flags' : cat_source['flags']
                            }
            cat_src, created = CatalogSources.objects.get_or_create(**source_params)
            for extn in ['e92-ldac', 'e92.bkgsub', 'e92', 'e92.rms', 'e93', 'e93.rms']:
                new_name = os.path.join(self.test_output_dir, frame_params['filename'].replace('e91', extn))
                filename = shutil.copy(self.test_file_path, new_name)
                # Change object name to 65803
                with fits.open(filename) as hdulist:
                    #print(f"FILENAME {filename}")
                    hdulist[0].header['telescop'] = '2m0-02'
                    hdulist[0].header['instrume'] = 'ep07'
                    hdulist[0].header['object'] = '65803 '
                    half_exp = timedelta(seconds=hdulist[0].header['exptime'] / 2.0)
                    date_obs = frame_params['midpoint'] - half_exp
                    #print("SUB LOOP MIDPOINT", frame_params['midpoint'])
                    hdulist[0].header['date-obs'] = date_obs.strftime("%Y-%m-%dT%H:%M:%S")
                    utstop = frame_params['midpoint'] + half_exp + timedelta(seconds=8.77)
                    hdulist[0].header['utstop'] = utstop.strftime("%H:%M:%S.%f")[0:12]
                    hdulist[0].header['crval1'] = ra[i]
                    hdulist[0].header['crval2'] = dec[i]
                    hdulist.writeto(filename, overwrite=True, checksum=True)
#                   hdulist.close()
                    self.test_banzai_files.append(os.path.basename(filename))

        # Make one additional copy which is renamed to an -e91 (so it shouldn't be found)
        new_name = os.path.join(self.test_output_dir, 'coj2m002-ep07-20240610-0065-e91.fits')
        shutil.copy(self.test_file_path, new_name)
        self.test_banzai_files.insert(1, os.path.basename(new_name))

        self.remove = True
        self.debug_print = True
        self.maxDiff = None

    def tearDown(self):
        # Generate an example test dir to compare root against and then remove it
        temp_test_dir = tempfile.mkdtemp(prefix='tmp_neox')
        os.rmdir(temp_test_dir)
        if self.remove and self.test_dir.startswith(temp_test_dir[:-8]):
            shutil.rmtree(self.test_dir)
        else:
            if self.debug_print:
                print("Not removing temporary test directory", self.test_dir)

    def test_basic(self):
        expected_num_body = 1
        expected_num_blocks = 2
        expected_num_frames = 9
        expected_num_files = 3*6 + 1 #3 is the number of original files, 6 is number of products per file, plus one extra random e91

        self.assertEqual(expected_num_body, Body.objects.all().count())
        self.assertEqual(expected_num_blocks, Block.objects.all().count())
        self.assertEqual(expected_num_frames, Frame.objects.all().count())

        num_files = len(glob(self.test_output_dir + '/*'))
        self.assertEqual(expected_num_files, num_files)

    def compare_aper_tables(self, expected_table, table, column, num_to_check=6, precision=6):
        for i in range(0, num_to_check+1):
            self.assertAlmostEqual(expected_table[column][i], table[column][i], precision)
            print(f'{column} OK')
        # for i in range(0, num_to_check+1):
        #     try:
        #         self.assertAlmostEqual(expected_table[column][i], table[column][i], precision)
        #     except TypeError:
        #         print(f"TYPERROR {expected_table[column][i], table[column][i][0], precision}")
        #         self.assertAlmostEqual(expected_table[column][i], table[column][i][0], precision)
    def compare_tables_with_strings(self, expected_table, table, column, num_to_check=6, precision=6):
        for i in range(0, num_to_check+1):
            self.assertEqual(expected_table[column][i], table[column][i], precision)
            print(f'{column} OK')

    def compare_rows(self, expected_table, table, column):
        self.assertEqual(expected_table[column], table[column])
        print(f'{column} OK')

    def test_perform_aperture_photometry_default(self):

        FLUX2MAG = 2.5/np.log(10)
        expected_results = QTable()
        expected_results['path to frame'] = ['/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0065-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0095-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0125-e93.fits']
        expected_results['times'] = [datetime(2024, 6, 10, 17, 2, 0), datetime(2024, 6, 10, 17, 4, 0), datetime(2024, 6, 10, 17, 6, 0)]

        expected_row2 = QTable()
        expected_row2['path to frame'] = [os.path.join(self.test_output_dir, self.e93_frame.filename)]
        expected_row2['times'] = [self.e93_frame.midpoint]
        expected_row2['filters'] = [np.str_(self.e93_frame.filter)]
        expected_row2['xcenter'] = [48.76999999999983] #*u.pix
        expected_row2['ycenter'] = [48.2699999999529] #* u.pix
        expected_row2['aperture sum'] = [135.68437393971408]
        expected_row2['aperture sum err'] = [11.646125295033322]
        expected_row2['FWHM'] = [self.e93_frame.fwhm]
        expected_row2['ZP'] = [self.e93_frame.zeropoint]
        expected_row2['ZP_sig'] = [self.e93_frame.zeropoint_err]
        expected_row2['mag'] = -2.5*np.log10(expected_row2['aperture sum']) + self.e93_frame.zeropoint
        expected_row2['magerr'] = FLUX2MAG * expected_row2['aperture sum err'] / expected_row2['aperture sum']
        expected_row2['aperture radius'] = [2.5*self.e93_frame.fwhm]
        dataroot = self.test_output_dir
        results = perform_aper_photometry(self.test_block, dataroot)

        exp_dtypes = expected_row2.dtype
        dtypes = results.dtype
        expected_table_length = len(Frame.objects.filter(block = self.test_block, filename__contains = 'e93.fits'))
        self.assertEqual(expected_row2.colnames, results.colnames)
        self.assertEqual(len(expected_results), len(results))
        self.assertEqual(len(results), expected_table_length)
        self.compare_tables_with_strings(expected_results, results, column = 'path to frame',num_to_check= 2, precision=6)
        self.compare_tables_with_strings(expected_results, results, column = 'times',num_to_check= 2, precision=6)
        self.compare_rows(expected_row2, results[:][2], column = 'path to frame')
        self.compare_rows(expected_row2, results[:][2], column = 'times')
        self.compare_rows(expected_row2, results[:][2], column = 'filters')
        self.compare_rows(expected_row2, results[:][2], column = 'xcenter')
        self.compare_rows(expected_row2, results[:][2], column = 'ycenter')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum err')
        self.compare_rows(expected_row2, results[:][2], column = 'mag')
        self.compare_rows(expected_row2, results[:][2], column = 'magerr')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture radius')

    def test_perform_aperture_photometry_default_ap_ignore_zp(self):
        FLUX2MAG = 2.5/np.log(10)
        expected_results = QTable()
        expected_results['path to frame'] = ['/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0065-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0095-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0125-e93.fits']
        expected_results['times'] = [datetime(2024, 6, 10, 17, 2, 0), datetime(2024, 6, 10, 17, 4, 0), datetime(2024, 6, 10, 17, 6, 0)]

        expected_row2 = QTable()
        expected_row2['path to frame'] = [os.path.join(self.test_output_dir, self.e93_frame.filename)]
        expected_row2['times'] = [self.e93_frame.midpoint]
        expected_row2['filters'] = [np.str_(self.e93_frame.filter)]
        expected_row2['xcenter'] = [48.76999999999983] #*u.pix
        expected_row2['ycenter'] = [48.2699999999529] #* u.pix
        expected_row2['aperture sum'] = [135.68437393971408]
        expected_row2['aperture sum err'] = [11.646125295033322]
        expected_row2['FWHM'] = [self.e93_frame.fwhm]
        expected_row2['ZP'] = [self.e93_frame.zeropoint]
        expected_row2['ZP_sig'] = [self.e93_frame.zeropoint_err]
        expected_row2['mag'] = -2.5*np.log10(expected_row2['aperture sum'])
        expected_row2['magerr'] = FLUX2MAG * expected_row2['aperture sum err'] / expected_row2['aperture sum']
        expected_row2['aperture radius'] = [2.5*self.e93_frame.fwhm]
        dataroot = self.test_output_dir
        results = perform_aper_photometry(self.test_block, dataroot, account_zps= False)

        exp_dtypes = expected_row2.dtype
        dtypes = results.dtype

        expected_table_length = len(Frame.objects.filter(block = self.test_block, filename__contains = 'e93.fits'))

        self.assertEqual(exp_dtypes, dtypes)
        self.assertEqual(expected_row2.colnames, results.colnames)
        self.assertEqual(len(expected_results), len(results))
        self.assertEqual(len(results), expected_table_length)
        self.compare_tables_with_strings(expected_results, results, column = 'path to frame',num_to_check= 2, precision=6)
        self.compare_tables_with_strings(expected_results, results, column = 'times',num_to_check= 2, precision=6)
        self.compare_rows(expected_row2, results[:][2], column = 'path to frame')
        self.compare_rows(expected_row2, results[:][2], column = 'times')
        self.compare_rows(expected_row2, results[:][2], column = 'filters')
        self.compare_rows(expected_row2, results[:][2], column = 'xcenter')
        self.compare_rows(expected_row2, results[:][2], column = 'ycenter')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum err')
        self.compare_rows(expected_row2, results[:][2], column = 'mag')
        self.compare_rows(expected_row2, results[:][2], column = 'magerr')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture radius')

    def test_perform_aperture_photometry_manual_ap_ignore_zp(self):
        FLUX2MAG = 2.5/np.log(10)
        expected_results = QTable()
        expected_results['path to frame'] = ['/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0065-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0095-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0125-e93.fits']
        expected_results['times'] = [datetime(2024, 6, 10, 17, 2, 0), datetime(2024, 6, 10, 17, 4, 0), datetime(2024, 6, 10, 17, 6, 0)]

        expected_row2 = QTable()
        expected_row2['path to frame'] = [os.path.join(self.test_output_dir, self.e93_frame.filename)]
        expected_row2['times'] = [self.e93_frame.midpoint]
        expected_row2['filters'] = [np.str_(self.e93_frame.filter)]
        expected_row2['xcenter'] = [48.76999999999983] #*u.pix
        expected_row2['ycenter'] = [48.2699999999529] #* u.pix
        expected_row2['aperture sum'] = [99.9718286829744]
        expected_row2['aperture sum err'] = [8.690970405159566]
        expected_row2['FWHM'] = [self.e93_frame.fwhm]
        expected_row2['ZP'] = [self.e93_frame.zeropoint]
        expected_row2['ZP_sig'] = [self.e93_frame.zeropoint_err]
        expected_row2['mag'] = -2.5*np.log10(expected_row2['aperture sum'])
        expected_row2['magerr'] = FLUX2MAG * expected_row2['aperture sum err'] / expected_row2['aperture sum']
        expected_row2['aperture radius'] = [3.0]
        dataroot = self.test_output_dir
        results = perform_aper_photometry(self.test_block, dataroot, account_zps= False, aperture_radius= 3.0)

        exp_dtypes = expected_row2.dtype
        dtypes = results.dtype

        expected_table_length = len(Frame.objects.filter(block = self.test_block, filename__contains = 'e93.fits'))

        self.assertEqual(exp_dtypes, dtypes)
        self.assertEqual(expected_row2.colnames, results.colnames)
        self.assertEqual(len(expected_results), len(results))
        self.assertEqual(len(results), expected_table_length)
        self.compare_tables_with_strings(expected_results, results, column = 'path to frame',num_to_check= 2, precision=6)
        self.compare_tables_with_strings(expected_results, results, column = 'times',num_to_check= 2, precision=6)
        self.compare_rows(expected_row2, results[:][2], column = 'path to frame')
        self.compare_rows(expected_row2, results[:][2], column = 'times')
        self.compare_rows(expected_row2, results[:][2], column = 'filters')
        self.compare_rows(expected_row2, results[:][2], column = 'xcenter')
        self.compare_rows(expected_row2, results[:][2], column = 'ycenter')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum err')
        self.compare_rows(expected_row2, results[:][2], column = 'mag')
        self.compare_rows(expected_row2, results[:][2], column = 'magerr')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture radius')

    def test_perform_aperture_photometry_manual_ap_include_zp(self):
        FLUX2MAG = 2.5/np.log(10)
        expected_results = QTable()
        expected_results['path to frame'] = ['/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0065-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0095-e93.fits', '/tmp/tmp_neox_fjody5q5/20240610/coj2m002-ep07-20240610-0125-e93.fits']
        expected_results['times'] = [datetime(2024, 6, 10, 17, 2, 0), datetime(2024, 6, 10, 17, 4, 0), datetime(2024, 6, 10, 17, 6, 0)]

        expected_row2 = QTable()
        expected_row2['path to frame'] = [os.path.join(self.test_output_dir, self.e93_frame.filename)]
        expected_row2['times'] = [self.e93_frame.midpoint]
        expected_row2['filters'] = [np.str_(self.e93_frame.filter)]
        expected_row2['xcenter'] = [48.76999999999983] #*u.pix
        expected_row2['ycenter'] = [48.2699999999529] #* u.pix
        expected_row2['aperture sum'] = [99.9718286829744]
        expected_row2['aperture sum err'] = [8.690970405159566]
        expected_row2['FWHM'] = [self.e93_frame.fwhm]
        expected_row2['ZP'] = [self.e93_frame.zeropoint]
        expected_row2['ZP_sig'] = [self.e93_frame.zeropoint_err]
        expected_row2['mag'] = -2.5*np.log10(expected_row2['aperture sum']) + self.e93_frame.zeropoint
        expected_row2['magerr'] = FLUX2MAG * expected_row2['aperture sum err'] / expected_row2['aperture sum']
        expected_row2['aperture radius'] = [3.0]
        dataroot = self.test_output_dir
        results = perform_aper_photometry(self.test_block, dataroot, account_zps= True, aperture_radius= 3.0)

        exp_dtypes = expected_row2.dtype
        dtypes = results.dtype

        expected_table_length = len(Frame.objects.filter(block = self.test_block, filename__contains = 'e93.fits'))

        self.assertEqual(exp_dtypes, dtypes)
        self.assertEqual(expected_row2.colnames, results.colnames)
        self.assertEqual(len(expected_results), len(results))
        self.assertEqual(len(results), expected_table_length)
        self.compare_tables_with_strings(expected_results, results, column = 'path to frame',num_to_check= 2, precision=6)
        self.compare_tables_with_strings(expected_results, results, column = 'times',num_to_check= 2, precision=6)
        self.compare_rows(expected_row2, results[:][2], column = 'path to frame')
        self.compare_rows(expected_row2, results[:][2], column = 'times')
        self.compare_rows(expected_row2, results[:][2], column = 'filters')
        self.compare_rows(expected_row2, results[:][2], column = 'xcenter')
        self.compare_rows(expected_row2, results[:][2], column = 'ycenter')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture sum err')
        self.compare_rows(expected_row2, results[:][2], column = 'mag')
        self.compare_rows(expected_row2, results[:][2], column = 'magerr')
        self.compare_rows(expected_row2, results[:][2], column = 'aperture radius')

    def test_generate_ecsv_file_post_photomet_default(self):
        block_date_str = f"{self.test_block.block_start}"[:-9]
        expected_file_name = os.path.join(self.test_output_dir, f"aperture_photometry_table_{block_date_str}_aper_radius_2.5*fwhm_zps_included.ecsv")
        photometry_file_name = generate_ecsv_file_post_photomet(self.test_block, self.test_output_dir, overwrite = True)
        photometry_file_contents = Table.read(photometry_file_name, format = 'ascii.ecsv')
        photometry_table = perform_aper_photometry(self.test_block, self.test_output_dir)
        self.assertTrue(os.path.exists(photometry_file_name))
        self.assertTrue(os.path.getsize(photometry_file_name) > 0)
        self.assertEqual(expected_file_name, photometry_file_name)
        self.assertEqual(str(photometry_file_contents), str(photometry_table))

    def test_generate_ecsv_file_post_photomet_default_ap_ignore_zp(self):
        block_date_str = f"{self.test_block.block_start}"[:-9]
        expected_file_name = os.path.join(self.test_output_dir, f"aperture_photometry_table_{block_date_str}_aper_radius_2.5*fwhm_zps_excluded.ecsv")
        photometry_file_name = generate_ecsv_file_post_photomet(self.test_block, self.test_output_dir, overwrite = True, account_zps= False)
        photometry_file_contents = Table.read(photometry_file_name, format = 'ascii.ecsv')
        photometry_table = perform_aper_photometry(self.test_block, self.test_output_dir, account_zps= False)
        self.assertTrue(os.path.exists(photometry_file_name))
        self.assertTrue(os.path.getsize(photometry_file_name) > 0)
        self.assertEqual(expected_file_name, photometry_file_name)
        self.assertEqual(str(photometry_file_contents), str(photometry_table))

    def test_generate_ecsv_file_post_photomet_manual_ap_ignore_zp(self):
        block_date_str = f"{self.test_block.block_start}"[:-9]
        expected_file_name = os.path.join(self.test_output_dir, f"aperture_photometry_table_{block_date_str}_aper_radius_3.0_zps_excluded.ecsv")
        photometry_file_name = generate_ecsv_file_post_photomet(self.test_block, self.test_output_dir, overwrite = True,aperture_radius=3.0, account_zps= False)
        photometry_file_contents = Table.read(photometry_file_name, format = 'ascii.ecsv')
        photometry_table = perform_aper_photometry(self.test_block, self.test_output_dir, aperture_radius= 3.0, account_zps= False)
        self.assertTrue(os.path.exists(photometry_file_name))
        self.assertTrue(os.path.getsize(photometry_file_name) > 0)
        self.assertEqual(expected_file_name, photometry_file_name)
        self.assertEqual(str(photometry_file_contents), str(photometry_table))

    def test_generate_ecsv_file_post_photomet_manual_ap_include_zp(self):
        block_date_str = f"{self.test_block.block_start}"[:-9]
        expected_file_name = os.path.join(self.test_output_dir, f"aperture_photometry_table_{block_date_str}_aper_radius_3.0_zps_included.ecsv")
        photometry_file_name = generate_ecsv_file_post_photomet(self.test_block, self.test_output_dir, overwrite = True,aperture_radius=3.0, account_zps= True)
        photometry_file_contents = Table.read(photometry_file_name, format = 'ascii.ecsv')
        photometry_table = perform_aper_photometry(self.test_block, self.test_output_dir, aperture_radius= 3.0, account_zps= True)
        self.assertTrue(os.path.exists(photometry_file_name))
        self.assertTrue(os.path.getsize(photometry_file_name) > 0)
        self.assertEqual(expected_file_name, photometry_file_name)
        self.assertEqual(str(photometry_file_contents), str(photometry_table))

