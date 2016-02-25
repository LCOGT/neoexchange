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
import os

import mock
from django.test import TestCase
from django.forms.models import model_to_dict

from core.models import Body

#Import module to test
from photometrics.catalog_subs import *

class FITSCatalogReader(TestCase):

    def setUp(self):
        # Read in example FITS source catalog
        test_filename = os.path.join('photometrics', 'tests', 'test_catalog.fits')
#        self.test_arecibo_page = BeautifulSoup(test_fh, "html.parser")
#        test_fh.close()

    def test_get_header_details(self):
        self.fail('Finish the test')
