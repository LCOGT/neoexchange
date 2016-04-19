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
from math import sqrt, log10, log
import os

import mock
from django.test import TestCase
from django.forms.models import model_to_dict
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import Angle
import astropy.units as u

from core.models import Body, CatalogSources
from test_catalog_subs import FITSUnitTest

#Import module to test
from photometrics.catalog_subs import *

class StoreCatalogSourcesTest(FITSUnitTest):

    def test1(self):

        ###
        store_catalog_sources(self.test_filename)

        self.assertEqual(CatalogSources.objects.count(), self.table_num_flags0)

        last_catsrc=CatalogSources.objects.last()

        self.assertAlmostEqual(last_catsrc.obs_x, 1067.9471, 4)
        self.assertAlmostEqual(last_catsrc.obs_y, 1973.7445, 4)
