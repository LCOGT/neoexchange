import os
import tempfile
from glob import glob
from datetime import datetime

from photometrics.pds_subs import *

from django.test import TestCase

class TestPDSSchemaMappings(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

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

    def test_blank_dir(self):

        schemas = pds_schema_mappings(self.test_dir)

        self.assertEqual({}, schemas)

    def test_schemas_dir_sch(self):

        expected_schemas = {
                            'PDS4::DISP' : {'filename' : os.path.join(self.schemadir, 'PDS4_DISP_1F00_1500.sch'),
                                           },
                            'PDS4::PDS' : {'filename' : os.path.join(self.schemadir, 'PDS4_PDS_1F00.sch'),
                                          }
                           }

        schemas = pds_schema_mappings(self.schemadir)

        self.assertNotEqual({}, schemas)
        self.assertEqual(expected_schemas, schemas)

    def test_schemas_dir_xsd(self):

        expected_schemas = {
                            'PDS4::DISP' : {'filename' : os.path.join(self.schemadir, 'PDS4_DISP_1F00_1500.xsd'),
                                            'namespace' : "http://pds.nasa.gov/pds4/disp/v1"
                                           },
                            'PDS4::PDS' : {'filename' : os.path.join(self.schemadir, 'PDS4_PDS_1F00.xsd'),
                                           'namespace' : "http://pds.nasa.gov/pds4/pds/v1"
                                          },
                           }

        schemas = pds_schema_mappings(self.schemadir, match_pattern='*.xsd')

        self.assertNotEqual({}, schemas)
        self.assertEqual(expected_schemas, schemas)


class TestWritePDSLabel(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.test_dir = '/tmp/tmp_neox_wibble'
#        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        test_xml_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label.xml'))
        with open(test_xml_cat, 'r') as xml_file:
            self.expected_xml = xml_file.readlines()

        self.remove = False
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


    def test_write(self):

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')
        filename = 'elp1m006-fa07-20210502-0048-e92.fits'

        status = write_xml(filename, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        with open(output_xml_file, 'r') as xml_file:
            xml = xml_file.readlines()

        for i, expected_line in enumerate(self.expected_xml):
            if i < len(xml):
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1)
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)
