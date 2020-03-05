"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2019-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from django.test import TestCase

# Import module to test
from photometrics.obsgeomplot import make_targetname

class TestMakeTargetName(TestCase):

    def test_numbered_ast(self):
        name = '66391 (1999 KW4)'
        expected_name = '66391_1999KW4'

        new_name = make_targetname(name)

        self.assertEqual(expected_name, new_name)

    def test_numbered_comet(self):
        name = '46P/Wirtanen'
        expected_name = '46P_Wirtanen'

        new_name = make_targetname(name)

        self.assertEqual(expected_name, new_name)

    def test_unnumbered_comet_with_name(self):
        name = 'ATLAS (C/2019 Y4)'
        expected_name = 'ATLAS_C_2019Y4'

        new_name = make_targetname(name)

        self.assertEqual(expected_name, new_name)

    def test_unnumbered_comet_with_longname(self):
        name = 'Machholz-Fujikawa-Iwamo (C/2018'
        expected_name = 'Machholz_Fujikawa_IwamoC_2018'

        new_name = make_targetname(name)

        self.assertEqual(expected_name, new_name)
