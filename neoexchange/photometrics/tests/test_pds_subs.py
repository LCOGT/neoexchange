import os
import shutil
import tempfile
from glob import glob
from lxml import etree
from lxml import objectify
from datetime import datetime

from photometrics.pds_subs import *

from django.test import SimpleTestCase

class TestPDSSchemaMappings(SimpleTestCase):

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
                                            'namespace' : "http://pds.nasa.gov/pds4/disp/v1",
                                            'location' : "https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.xsd",
                                            'version' : "1.5.0.0"
                                           },
                            'PDS4::GEOM' : {'filename' : os.path.join(self.schemadir, 'PDS4_GEOM_1F00_1910.xsd'),
                                            'namespace' : "http://pds.nasa.gov/pds4/geom/v1",
                                            'location' : "https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1F00_1910.xsd",
                                            'version' : "1.9.1.0"
                                           },
                            'PDS4::IMG' : {'filename' : os.path.join(self.schemadir, 'PDS4_IMG_1F00_1810.xsd'),
                                           'namespace' : "http://pds.nasa.gov/pds4/img/v1",
                                           'location' : "https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1F00_1810.xsd",
                                           'version' : "1.8.1.0"
                                          },
                            'PDS4::PDS' : {'filename' : os.path.join(self.schemadir, 'PDS4_PDS_1F00.xsd'),
                                           'namespace' : "http://pds.nasa.gov/pds4/pds/v1",
                                           'location' : "https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1F00.xsd",
                                           'version' : "1.15.0.0"
                                          },
                           }

        schemas = pds_schema_mappings(self.schemadir, match_pattern='*.xsd')

        self.assertNotEqual({}, schemas)
        self.assertEqual(expected_schemas, schemas)


class TestGetNamespace(SimpleTestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.schemas = sorted(glob(os.path.join(self.schemadir, '*.xsd')))

        self.maxDiff = None

    def test_disp_schema(self):

        ns = get_namespace(self.schemas[0])
        expected_ns = { 'namespace' : 'http://pds.nasa.gov/pds4/disp/v1',
                        'location'  : 'https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.xsd',
                        'version' : '1.5.0.0'
                      }

        self.assertEqual(expected_ns, ns)


class TestCreateIDArea(SimpleTestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schemas_mapping = pds_schema_mappings(schemadir, '*.xsd')

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1)
        result = etree.tostring(xml_element)

        self.assertEquals(expect, result)

    def test_default_version(self):
        expected = '''
            <Identification_Area>
                <logical_identifier>urn:nasa:pds:dart_teleobs:lcogt_cal:banzai_test_frame.fits</logical_identifier>
                <version_id>1.0</version_id>
                <title>Las Cumbres Observatory Calibrated Image</title>
                <information_model_version>1.15.0.0</information_model_version>
                <product_class>Product_Observational</product_class>
                <Modification_History>
                    <Modification_Detail>
                        <modification_date>2021-05-10</modification_date>
                        <version_id>1.0</version_id>
                        <description>initial version</description>
                    </Modification_Detail>
                </Modification_History>
              </Identification_Area>'''

        id_area = create_id_area('banzai_test_frame.fits', mod_time=datetime(2021,5,10))

        self.compare_xml(expected, id_area)

    def test_older_version(self):
        expected = '''
            <Identification_Area>
                <logical_identifier>urn:nasa:pds:dart_teleobs:lcogt_cal:banzai_test_frame.fits</logical_identifier>
                <version_id>1.0</version_id>
                <title>Las Cumbres Observatory Calibrated Image</title>
                <information_model_version>1.14.0.0</information_model_version>
                <product_class>Product_Observational</product_class>
                <Modification_History>
                    <Modification_Detail>
                        <modification_date>2021-05-10</modification_date>
                        <version_id>1.0</version_id>
                        <description>initial version</description>
                    </Modification_Detail>
                </Modification_History>
              </Identification_Area>'''

        id_area = create_id_area('banzai_test_frame.fits', '1.14.0.0', mod_time=datetime(2021,5,10))

        self.compare_xml(expected, id_area)

    def test_schema_version(self):
        expected = '''
            <Identification_Area>
                <logical_identifier>urn:nasa:pds:dart_teleobs:lcogt_cal:banzai_test_frame.fits</logical_identifier>
                <version_id>1.0</version_id>
                <title>Las Cumbres Observatory Calibrated Image</title>
                <information_model_version>1.15.0.0</information_model_version>
                <product_class>Product_Observational</product_class>
                <Modification_History>
                    <Modification_Detail>
                        <modification_date>2021-04-20</modification_date>
                        <version_id>1.0</version_id>
                        <description>initial version</description>
                    </Modification_Detail>
                </Modification_History>
              </Identification_Area>'''
        schema_version = self.schemas_mapping['PDS4::PDS']['version']

        id_area = create_id_area('banzai_test_frame.fits', model_version=schema_version, mod_time=datetime(2021,4,20))

        self.compare_xml(expected, id_area)


class TestWritePDSLabel(SimpleTestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        test_xml_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label.xml'))
        with open(test_xml_cat, 'r') as xml_file:
            self.expected_xml = xml_file.readlines()
        self.test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))

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


    def test_write(self):

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_xml(self.test_banzai_file, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        with open(output_xml_file, 'r') as xml_file:
            xml = xml_file.readlines()

        for i, expected_line in enumerate(self.expected_xml):
            if i < len(xml):
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1)
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)


class TestCreatePDSLabels(SimpleTestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        test_xml_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label.xml'))
        with open(test_xml_cat, 'r') as xml_file:
            self.expected_xml = xml_file.readlines()

        self.framedir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'banzai_test_frame.fits'
        test_file_path = os.path.join(self.framedir, self.test_file)

#        self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')


        # Make one copy and rename to an -e92 (so it will get picked up) and
        # a second copy which is renamed to an -e91 (so it shouldn't be found)
        new_name = os.path.join(self.test_dir, 'cpt1m013-kb76-20160606-0396-e92.fits')
        self.test_banzai_file = shutil.copy(test_file_path, new_name)
        new_name = os.path.join(self.test_dir, 'cpt1m013-kb76-20160606-0396-e91.fits')
        shutil.copy(test_file_path, new_name)

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

    def test_generate(self):

        expected_xml_labels = [self.test_banzai_file.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)