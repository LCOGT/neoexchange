import os
import io
import shutil
import tempfile
from glob import glob
from pathlib import Path
from lxml import etree, objectify
from datetime import datetime
from mock import patch, MagicMock, PropertyMock

from astropy.io import fits

from core.models import Body, Designations, SuperBlock, Block, Frame
from photometrics.pds_subs import *
from photometrics.lightcurve_subs import read_photompipe_file, write_photompipe_file

from unittest import skipIf
from django.test import SimpleTestCase, TestCase

import logging
logging.disable(logging.FATAL)

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


class TestCreateProductCollection(SimpleTestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schemas_mapping = pds_schema_mappings(schemadir, '*.xsd')

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1)
        result = etree.tostring(xml_element)

        self.assertEquals(expect, result)

    def test_default(self):
        expected_xml = '''
            <Product_Collection xmlns="http://pds.nasa.gov/pds4/pds/v1" xmlns:disp="http://pds.nasa.gov/pds4/disp/v1" xmlns:geom="http://pds.nasa.gov/pds4/geom/v1" xmlns:img="http://pds.nasa.gov/pds4/img/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pds.nasa.gov/pds4/disp/v1 https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.xsd    http://pds.nasa.gov/pds4/geom/v1 https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1F00_1910.xsd    http://pds.nasa.gov/pds4/img/v1 https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1F00_1810.xsd    http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1F00.xsd"/>
        '''

        prod_coll = create_product_collection(self.schemas_mapping)

        self.compare_xml(expected_xml, prod_coll)


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
                <logical_identifier>urn:nasa:pds:dart_teleobs:data_lcogtcal:banzai_test_frame</logical_identifier>
                <version_id>1.0</version_id>
                <title>Las Cumbres Observatory Calibrated Image: banzai_test_frame</title>
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
                <logical_identifier>urn:nasa:pds:dart_teleobs:data_lcogtcal:banzai_test_frame</logical_identifier>
                <version_id>1.0</version_id>
                <title>Las Cumbres Observatory Calibrated Image: banzai_test_frame</title>
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
                <logical_identifier>urn:nasa:pds:dart_teleobs:data_lcogtcal:banzai_test_frame</logical_identifier>
                <version_id>1.0</version_id>
                <title>Las Cumbres Observatory Calibrated Image: banzai_test_frame</title>
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


class TestCreateObsArea(TestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schemas_mapping = pds_schema_mappings(schemadir, '*.xsd')

        self.test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        self.test_banzai_header, table, cattype = open_fits_catalog(self.test_banzai_file, header_only=True)
        self.test_raw_file = os.path.abspath(os.path.join('photometrics', 'tests', 'mef_raw_test_frame.fits'))
        self.test_raw_header, table, cattype = open_fits_catalog(self.test_raw_file, header_only=True)

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

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1).decode()
        result = etree.tostring(xml_element).decode()

        self.assertEquals(expect, result)

    def test_banzai_not_didymos(self):
        expected = '''
            <Observation_Area>
              <Time_Coordinates>
                <start_date_time>2016-06-06T22:48:14.00Z</start_date_time>
                <stop_date_time>2016-06-06T22:50:02.77Z</stop_date_time>
              </Time_Coordinates>
              <Investigation_Area>
                <name>Double Asteroid Redirection Test</name>
                <type>Mission</type>
                <Internal_Reference>
                  <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                  <reference_type>data_to_investigation</reference_type>
                </Internal_Reference>
              </Investigation_Area>
              <Observing_System>
                <Observing_System_Component>
                  <name>Las Cumbres Observatory (LCOGT)</name>
                  <type>Host</type>
                  <description>The description for the host can be found in the document collection for this bundle.</description>
                  <Internal_Reference>
                    <lid_reference>urn:nasa:pds:context:facility:observatory.las_cumbres</lid_reference>
                    <reference_type>is_facility</reference_type>
                  </Internal_Reference>
                </Observing_System_Component>
                <Observing_System_Component>
                  <name>Las Cumbres Global Telescope Network - 1m Telescopes</name>
                  <type>Telescope</type>
                  <description>
          LCOGT 1m0-13 Telescope
          LCOGT CPT Node 1m0 Dome B at Sutherland
          The description for the telescope can be found in the document collection for this bundle.</description>
                  <Internal_Reference>
                    <lid_reference>urn:nasa:pds:context:instrument_host:las_cumbres.1m0_telescopes</lid_reference>
                    <reference_type>is_telescope</reference_type>
                  </Internal_Reference>
                </Observing_System_Component>
                <Observing_System_Component>
                  <name>Las Cumbres 1m Telescopes - Sinistro Camera</name>
                  <type>Instrument</type>
                  <description>The description for the instrument can be found in the document collection for this bundle.</description>
                  <Internal_Reference>
                    <lid_reference>urn:nasa:pds:context:instrument:las_cumbres.1m0_telescopes.sinistro</lid_reference>
                    <reference_type>is_instrument</reference_type>
                  </Internal_Reference>
                </Observing_System_Component>
              </Observing_System>
              <Target_Identification>
                <name>XL8B85F</name>
                <type>Asteroid</type>
              </Target_Identification>
            </Observation_Area>'''

        obs_area = create_obs_area(self.test_banzai_header, self.test_banzai_file)

        self.compare_xml(expected, obs_area)

    def test_banzai_didymos(self):
        expected = '''
            <Observation_Area>
              <Time_Coordinates>
                <start_date_time>2016-06-06T22:48:14.00Z</start_date_time>
                <stop_date_time>2016-06-06T22:50:02.77Z</stop_date_time>
              </Time_Coordinates>
              <Investigation_Area>
                <name>Double Asteroid Redirection Test</name>
                <type>Mission</type>
                <Internal_Reference>
                  <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                  <reference_type>data_to_investigation</reference_type>
                </Internal_Reference>
              </Investigation_Area>
              <Observing_System>
                <Observing_System_Component>
                  <name>Las Cumbres Observatory (LCOGT)</name>
                  <type>Host</type>
                  <description>The description for the host can be found in the document collection for this bundle.</description>
                  <Internal_Reference>
                    <lid_reference>urn:nasa:pds:context:facility:observatory.las_cumbres</lid_reference>
                    <reference_type>is_facility</reference_type>
                  </Internal_Reference>
                </Observing_System_Component>
                <Observing_System_Component>
                  <name>Las Cumbres Global Telescope Network - 1m Telescopes</name>
                  <type>Telescope</type>
                  <description>
          LCOGT 1m0-13 Telescope
          LCOGT CPT Node 1m0 Dome B at Sutherland
          The description for the telescope can be found in the document collection for this bundle.</description>
                  <Internal_Reference>
                    <lid_reference>urn:nasa:pds:context:instrument_host:las_cumbres.1m0_telescopes</lid_reference>
                    <reference_type>is_telescope</reference_type>
                  </Internal_Reference>
                </Observing_System_Component>
                <Observing_System_Component>
                  <name>Las Cumbres 1m Telescopes - Sinistro Camera</name>
                  <type>Instrument</type>
                  <description>The description for the instrument can be found in the document collection for this bundle.</description>
                  <Internal_Reference>
                    <lid_reference>urn:nasa:pds:context:instrument:las_cumbres.1m0_telescopes.sinistro</lid_reference>
                    <reference_type>is_instrument</reference_type>
                  </Internal_Reference>
                </Observing_System_Component>
              </Observing_System>
              <Target_Identification>
                <name>(65803) Didymos</name>
                <type>Asteroid</type>
                <Internal_Reference>
                  <lid_reference>urn:nasa:pds:context:target:asteroid.65803_didymos</lid_reference>
                  <reference_type>data_to_target</reference_type>
                </Internal_Reference>
              </Target_Identification>
            </Observation_Area>'''

        self.test_banzai_header['OBJECT'] = '65803'
        obs_area = create_obs_area(self.test_banzai_header, self.test_banzai_file)

        self.compare_xml(expected, obs_area)


class TestCreateContextArea(TestCase):

    def setUp(self):

        self.tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))

        self.test_file = 'banzai_test_frame.fits'
        self.test_file_path = os.path.join(self.tests_path, self.test_file)

#        self.test_dir = '/tmp/tmp_neox_wibble'
#        self.test_dir = 'C:\\Users\\liste\\AppData\\Local\\Temp\\tmp_neox_fli\\'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.test_input_dir = os.path.join(self.test_dir, 'input')
        self.test_input_daydir = os.path.join(self.test_dir, 'input', '20211013')
        os.makedirs(self.test_input_daydir, exist_ok=True)
        self.test_output_dir = os.path.join(self.test_dir, 'output')
        self.expected_root_dir = os.path.join(self.test_output_dir, '')
        self.test_ddp_dir = os.path.join(self.expected_root_dir, 'data_lcogtddp')
        self.test_blockdir = 'lcogt_1m0_01_fa11_20211013'
        self.test_ddp_daydir = os.path.join(self.test_ddp_dir, self.test_blockdir)
        os.makedirs(self.test_ddp_daydir, exist_ok=True)

        self.test_cal_dir = os.path.join(self.expected_root_dir, 'data_lcogtcal')
        self.test_cal_daydir = os.path.join(self.test_cal_dir, self.test_blockdir)
        os.makedirs(self.test_cal_daydir, exist_ok=True)

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

        self.remove = True
        self.debug_print = False
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

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_cal_data(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2016-06-06T22:48:14.00Z</start_date_time>
              <stop_date_time>2016-06-06T22:50:02.77Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Calibrated</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>SBIG Imager</name>
                <type>Instrument</type>
                <description>The description for the SBIG Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>XL8B85F</name>
              <type>Asteroid</type>
            </Target_Identification>
          </Context_Area>
        '''

        test_cal_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy files to output directory, renaming phot file
        new_name = os.path.join(self.test_cal_daydir, 'tfn1m001-fa11-20211012-0076-e92.fits')
        shutil.copy(test_cal_file, new_name)

        xml = create_context_area(self.test_cal_dir, 'cal')

        self.compare_xml(expected_xml, xml)

    def test_cal_data_by_daydir(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2016-06-06T22:48:14.00Z</start_date_time>
              <stop_date_time>2016-06-06T22:50:02.77Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Calibrated</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>SBIG Imager</name>
                <type>Instrument</type>
                <description>The description for the SBIG Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>XL8B85F</name>
              <type>Asteroid</type>
            </Target_Identification>
          </Context_Area>
        '''

        test_cal_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy files to output directory, renaming phot file
        new_name = os.path.join(self.test_cal_daydir, 'tfn1m001-fa11-20211012-0076-e92.fits')
        shutil.copy(test_cal_file, new_name)

        xml = create_context_area(self.test_cal_daydir, 'cal')

        self.compare_xml(expected_xml, xml)

    def test_cal_data_didymos(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2016-06-06T22:48:14.00Z</start_date_time>
              <stop_date_time>2016-06-06T22:50:02.77Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Calibrated</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>Sinistro Imager</name>
                <type>Instrument</type>
                <description>The description for the Sinistro Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>(65803) Didymos</name>
              <type>Asteroid</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:target:asteroid.65803_didymos</lid_reference>
                <reference_type>collection_to_target</reference_type>
              </Internal_Reference>
            </Target_Identification>
          </Context_Area>
        '''

        test_cal_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy files to output directory, renaming phot file
        new_name = os.path.join(self.test_cal_daydir, 'tfn1m001-fa11-20211012-0076-e92.fits')
        shutil.copy(test_cal_file, new_name)
        with fits.open(new_name, mode='update') as hdulist:
            hdulist[0].header['INSTRUME'] = 'fa11'
            hdulist[0].header['OBJECT'] = '65803'
            hdulist.flush()
        xml = create_context_area(self.test_cal_daydir, 'cal')

        self.compare_xml(expected_xml, xml)

    def test_phot_table(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2021-10-12T20:00:52.34Z</start_date_time>
              <stop_date_time>2021-10-12T20:57:10.08Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
          </Context_Area>
        '''

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_dartphotom.dat'))
        # Copy files to output directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, new_name)

        xml = create_context_area(self.test_ddp_dir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_table_by_daydir(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2021-10-12T20:00:52.34Z</start_date_time>
              <stop_date_time>2021-10-12T20:57:10.08Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
          </Context_Area>
        '''

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_dartphotom.dat'))
        # Copy files to output directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, new_name)

        xml = create_context_area(self.test_ddp_daydir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_table_with_files(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2021-10-12T20:00:52.34Z</start_date_time>
              <stop_date_time>2021-10-12T20:57:10.08Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>Sinistro Imager</name>
                <type>Instrument</type>
                <description>The description for the Sinistro Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>(65803) Didymos</name>
              <type>Asteroid</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:target:asteroid.65803_didymos</lid_reference>
                <reference_type>collection_to_target</reference_type>
              </Internal_Reference>
            </Target_Identification>
          </Context_Area>
        '''

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_dartphotom.dat'))
        # Copy ddp files to output ddp directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, new_name)

        test_fits_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy FITS files to output cal directory, renaming to e92
        new_name = os.path.join(self.test_cal_daydir, 'tfn1m001-fa11-20211012-0076-e92.fits')
        shutil.copy(test_fits_file, new_name)
        with fits.open(new_name, mode='update') as hdulist:
            hdulist[0].header['INSTRUME'] = 'fa11'
            hdulist[0].header['OBJECT'] = '65803'
            hdulist.flush()

        xml = create_context_area(self.test_ddp_daydir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_table_with_fli_files(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2021-10-12T20:00:52.34Z</start_date_time>
              <stop_date_time>2021-10-12T20:57:10.08Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-10 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-10 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-12 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-12 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>FLI Imager</name>
                <type>Instrument</type>
                <description>The description for the FLI Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>(65803) Didymos</name>
              <type>Asteroid</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:target:asteroid.65803_didymos</lid_reference>
                <reference_type>collection_to_target</reference_type>
              </Internal_Reference>
            </Target_Identification>
          </Context_Area>
        '''

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_dartphotom.dat'))
        # Copy ddp files to output ddp directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, new_name)

        test_fits_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy FITS files to multiple output cal directories, renaming to e92, setting
        # INSTRUME(nt), TELESCOP(e) and OBJECT header keywords appropriately
        for tel_serial, instrument in zip(['1m0-10', '1m0-12', '1m0-13'], ['ef02', 'ef04', 'ef03']):
            test_cal_daydir = os.path.join(self.test_cal_dir, f"lcogt_{tel_serial.replace('-','_')}_{instrument}_20211013")
            os.makedirs(test_cal_daydir, exist_ok=True)
            new_name = os.path.join(test_cal_daydir, f"cpt{tel_serial.replace('-', '')}-{instrument}-20211012-0076-e92.fits")
            shutil.copy(test_fits_file, new_name)
            with fits.open(new_name, mode='update') as hdulist:
                hdulist[0].header['INSTRUME'] = instrument
                hdulist[0].header['TELESCOP'] = tel_serial
                hdulist[0].header['OBJECT'] = '65803'
                hdulist.flush()

        xml = create_context_area(self.test_ddp_dir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_table_with_files_not_didymos(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2021-10-12T20:00:52.34Z</start_date_time>
              <stop_date_time>2021-10-12T20:57:10.08Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>Sinistro Imager</name>
                <type>Instrument</type>
                <description>The description for the Sinistro Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>(99942) Apophis</name>
              <type>Asteroid</type>
            </Target_Identification>
          </Context_Area>
        '''

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_dartphotom.dat'))
        # Copy ddp files to output ddp directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, new_name)

        test_fits_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy FITS files to output cal directory, renaming to e92
        new_name = os.path.join(self.test_cal_daydir, 'tfn1m001-fa11-20211012-0076-e92.fits')
        shutil.copy(test_fits_file, new_name)
        with fits.open(new_name, mode='update') as hdulist:
            hdulist[0].header['INSTRUME'] = 'fa11'
            hdulist[0].header['OBJECT'] = '99942'
            hdulist.flush()

        xml = create_context_area(self.test_ddp_daydir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def update_dirs_for_fli(self):
        """Renames the output directories and updates the variables for FLI data"""
        new_test_output_dir = self.test_output_dir.replace('output', 'output_fli')
        if os.path.exists(new_test_output_dir):
            self.test_output_dir = new_test_output_dir
        else:
            self.test_output_dir = shutil.move(self.test_output_dir, new_test_output_dir)
        if self.debug_print: print("new dir=", self.test_output_dir)
        self.test_ddp_dir = os.path.join(self.test_output_dir, 'data_lcogtddp')
        self.test_ddp_daydir = os.path.join(self.test_ddp_dir, self.test_blockdir)
        self.test_cal_dir = os.path.join(self.test_output_dir, 'data_lcogtcal')
        self.test_cal_daydir = os.path.join(self.test_cal_dir, self.test_blockdir)
        return

    def test_phot_bintable(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2022-09-26T23:03:41.98Z</start_date_time>
              <stop_date_time>2022-09-26T23:09:23.60Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
          </Context_Area>
        '''

        self.update_dirs_for_fli()
        # Copy files to output directory, renaming phot file
        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_bintable.fits'))
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.fits')
        shutil.copy(test_lc_file, new_name)

        xml = create_context_area(self.test_ddp_dir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_bintable_by_daydir(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2022-09-26T23:03:41.98Z</start_date_time>
              <stop_date_time>2022-09-26T23:09:23.60Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
          </Context_Area>
        '''

        self.update_dirs_for_fli()

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_bintable.fits'))
        # Copy files to output directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.fits')
        shutil.copy(test_lc_file, new_name)

        xml = create_context_area(self.test_ddp_daydir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_bintable_with_files(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2022-09-26T23:03:41.98Z</start_date_time>
              <stop_date_time>2022-09-26T23:09:23.60Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>Sinistro Imager</name>
                <type>Instrument</type>
                <description>The description for the Sinistro Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>(65803) Didymos</name>
              <type>Asteroid</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:target:asteroid.65803_didymos</lid_reference>
                <reference_type>collection_to_target</reference_type>
              </Internal_Reference>
            </Target_Identification>
          </Context_Area>
        '''

        self.update_dirs_for_fli()

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_bintable.fits'))
        # Copy ddp files to output ddp directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.fits')
        shutil.copy(test_lc_file, new_name)

        test_fits_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy FITS files to output cal directory, renaming to e92
        new_name = os.path.join(self.test_cal_daydir, 'tfn1m001-fa11-20211012-0076-e92.fits')
        shutil.copy(test_fits_file, new_name)
        with fits.open(new_name, mode='update') as hdulist:
            hdulist[0].header['INSTRUME'] = 'fa11'
            hdulist[0].header['OBJECT'] = '65803'
            hdulist.flush()

        xml = create_context_area(self.test_ddp_daydir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_bintable_with_fli_files(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2022-09-26T23:03:41.98Z</start_date_time>
              <stop_date_time>2022-09-26T23:09:23.60Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-10 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-10 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-12 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-12 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>FLI Imager</name>
                <type>Instrument</type>
                <description>The description for the FLI Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>(65803) Didymos</name>
              <type>Asteroid</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:target:asteroid.65803_didymos</lid_reference>
                <reference_type>collection_to_target</reference_type>
              </Internal_Reference>
            </Target_Identification>
          </Context_Area>
        '''

        self.update_dirs_for_fli()

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_bintable.fits'))
        # Copy ddp files to output ddp directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.fits')
        shutil.copy(test_lc_file, new_name)

        test_fits_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy FITS files to multiple output cal directories, renaming to e92, setting
        # INSTRUME(nt), TELESCOP(e) and OBJECT header keywords appropriately
        for tel_serial, instrument in zip(['1m0-10', '1m0-12', '1m0-13'], ['ef02', 'ef04', 'ef03']):
            test_cal_daydir = os.path.join(self.test_cal_dir, f"lcogt_{tel_serial.replace('-','_')}_{instrument}_20211013")
            os.makedirs(test_cal_daydir, exist_ok=True)
            new_name = os.path.join(test_cal_daydir, f"cpt{tel_serial.replace('-', '')}-{instrument}-20211012-0076-e92.fits")
            shutil.copy(test_fits_file, new_name)
            with fits.open(new_name, mode='update') as hdulist:
                hdulist[0].header['INSTRUME'] = instrument
                hdulist[0].header['TELESCOP'] = tel_serial
                hdulist[0].header['OBJECT'] = '65803'
                hdulist.flush()

        xml = create_context_area(self.test_ddp_dir, 'ddp')

        self.compare_xml(expected_xml, xml)

    def test_phot_bintable_with_files_not_didymos(self):
        expected_xml = '''
          <Context_Area>
            <Time_Coordinates>
              <start_date_time>2022-09-26T23:03:41.98Z</start_date_time>
              <stop_date_time>2022-09-26T23:09:23.60Z</stop_date_time>
            </Time_Coordinates>
            <Primary_Result_Summary>
              <purpose>Science</purpose>
              <processing_level>Derived</processing_level>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Dynamical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Lightcurve</facet1>
              </Science_Facets>
              <Science_Facets>
                <discipline_name>Small Bodies</discipline_name>
                <facet1>Physical Properties</facet1>
              </Science_Facets>
              <Science_Facets>
                <wavelength_range>Visible</wavelength_range>
                <discipline_name>Flux Measurements</discipline_name>
                <facet1>Photometry</facet1>
              </Science_Facets>
            </Primary_Result_Summary>
            <Investigation_Area>
              <name>Double Asteroid Redirection Test</name>
              <type>Mission</type>
              <Internal_Reference>
                <lid_reference>urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test</lid_reference>
                <reference_type>collection_to_investigation</reference_type>
              </Internal_Reference>
            </Investigation_Area>
            <Observing_System>
              <Observing_System_Component>
                <name>Las Cumbres Observatory (LCOGT)</name>
                <type>Host</type>
                <description>The description for the Las Cumbres Observatory (LCOGT) can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>LCOGT 1m0-13 Telescope</name>
                <type>Telescope</type>
                <description>The description for the LCOGT 1m0-13 Telescope can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
              <Observing_System_Component>
                <name>Sinistro Imager</name>
                <type>Instrument</type>
                <description>The description for the Sinistro Imager can be found in the document collection for this bundle.</description>
              </Observing_System_Component>
            </Observing_System>
            <Target_Identification>
              <name>(99942) Apophis</name>
              <type>Asteroid</type>
            </Target_Identification>
          </Context_Area>
        '''

        self.update_dirs_for_fli()

        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_bintable.fits'))
        # Copy ddp files to output ddp directory, renaming phot file
        new_name = os.path.join(self.test_ddp_daydir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.fits')
        shutil.copy(test_lc_file, new_name)

        test_fits_file = os.path.abspath(os.path.join(self.tests_path, 'banzai_test_frame.fits'))
        # Copy FITS files to output cal directory, renaming to e92
        new_name = os.path.join(self.test_cal_daydir, 'tfn1m001-fa11-20211012-0076-e92.fits')
        shutil.copy(test_fits_file, new_name)
        with fits.open(new_name, mode='update') as hdulist:
            hdulist[0].header['INSTRUME'] = 'fa11'
            hdulist[0].header['OBJECT'] = '99942'
            hdulist.flush()

        xml = create_context_area(self.test_ddp_daydir, 'ddp')

        self.compare_xml(expected_xml, xml)


class TestCreateFileAreaObs(SimpleTestCase):

    def setUp(self):

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        kpno_prihdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_kpno_mef_prihdr'))
        kpno_extnhdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_kpno_mef_extnhdr'))
        self.test_kpno_header = [kpno_prihdr,]
        for extn in range(1, 4+1):
            kpno_extnhdr['extver'] = extn
            kpno_extnhdr['extname'] = 'im' + str(extn)
            kpno_extnhdr['imageid'] = extn
            self.test_kpno_header.append(kpno_extnhdr)

        self.test_raw_filename = os.path.join(tests_path, 'mef_raw_test_frame.fits')
        self.test_raw_header, table, cattype = open_fits_catalog(self.test_raw_filename)
        # Make copy of raw MEF header and scale to full 4k x 4k Sinistro frame
        self.test_raw_4k_header = []
        for header in self.test_raw_header:
            new_header = header.copy()
            self.test_raw_4k_header.append(new_header)

        for extn in range(1, 4+1):
            self.test_raw_4k_header[extn]['NAXIS1'] = 2080
            self.test_raw_4k_header[extn]['NAXIS2'] = 2058
            self.test_raw_4k_header[extn]['CCDSUM'] = '1 1     '

        lco_calib_prihdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_proc_hdr'))
        lco_calib_prihdr["NAXIS1"] = 4096
        lco_calib_prihdr["NAXIS2"] = 4096
        lco_calib_prihdr["OBSTYPE"] = "DARK"
        for keyword in ['L1IDDARK', 'L1STATDA', 'L1IDFLAT', 'L1STATFL', 'L1MEAN', 'L1MEDIAN', 'L1SIGMA', 'L1FWHM', 'L1ELLIP', 'L1ELLIPA', 'WCSERR']:
            lco_calib_prihdr.remove(keyword)
        lco_bpm_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_bpmhdr'))
        lco_err_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_errhdr'))
        self.test_lco_calib_header = [lco_calib_prihdr, lco_bpm_exthdr, lco_err_exthdr]

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_kpno_mef(self):
        expected = '''
          <File_Area_Observational>
            <File>
              <file_name>kp050709_031.fit</file_name>
            </File>
            <Header>
              <name>main_header</name>
              <offset unit="byte">0</offset>
              <object_length unit="byte">17280</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Header>
              <name>ccd1_header</name>
              <offset unit="byte">17280</offset>
              <object_length unit="byte">17280</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>ccd1_image</local_identifier>
              <offset unit="byte">34560</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>4096</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2136</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>ccd2_header</name>
              <offset unit="byte">17533440</offset>
              <object_length unit="byte">17280</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>ccd2_image</local_identifier>
              <offset unit="byte">17550720</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>4096</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2136</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>ccd3_header</name>
              <offset unit="byte">35049600</offset>
              <object_length unit="byte">17280</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>ccd3_image</local_identifier>
              <offset unit="byte">35066880</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>4096</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2136</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>ccd4_header</name>
              <offset unit="byte">52565760</offset>
              <object_length unit="byte">17280</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>ccd4_image</local_identifier>
              <offset unit="byte">52583040</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>4096</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2136</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
          </File_Area_Observational>'''

        file_obs_area = create_file_area_obs(self.test_kpno_header, 'kp050709_031.fit')

        self.compare_xml(expected, file_obs_area)

    def test_lco_raw(self):
        expected = '''
          <File_Area_Observational>
            <File>
              <file_name>mef_raw_test_frame.fits</file_name>
              <comment>Raw LCOGT image file</comment>
            </File>
            <Header>
              <name>main_header</name>
              <offset unit="byte">0</offset>
              <object_length unit="byte">20160</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Header>
              <name>amp1_header</name>
              <offset unit="byte">20160</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp1_image</local_identifier>
              <offset unit="byte">23040</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>522</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>544</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>amp2_header</name>
              <offset unit="byte">593280</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp2_image</local_identifier>
              <offset unit="byte">596160</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>522</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>544</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>amp3_header</name>
              <offset unit="byte">1166400</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp3_image</local_identifier>
              <offset unit="byte">1169280</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>522</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>544</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>amp4_header</name>
              <offset unit="byte">1739520</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp4_image</local_identifier>
              <offset unit="byte">1742400</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>522</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>544</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
          </File_Area_Observational>'''

        file_obs_area = create_file_area_obs(self.test_raw_header, self.test_raw_filename)

        self.compare_xml(expected, file_obs_area)

    def test_lco_raw_fullframe(self):
        expected = '''
          <File_Area_Observational>
            <File>
              <file_name>mef_raw_test_frame.fits</file_name>
              <comment>Raw LCOGT image file</comment>
            </File>
            <Header>
              <name>main_header</name>
              <offset unit="byte">0</offset>
              <object_length unit="byte">20160</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Header>
              <name>amp1_header</name>
              <offset unit="byte">20160</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp1_image</local_identifier>
              <offset unit="byte">23040</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>2058</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2080</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>amp2_header</name>
              <offset unit="byte">8585280</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp2_image</local_identifier>
              <offset unit="byte">8588160</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>2058</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2080</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>amp3_header</name>
              <offset unit="byte">17150400</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp3_image</local_identifier>
              <offset unit="byte">17153280</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>2058</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2080</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>amp4_header</name>
              <offset unit="byte">25715520</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>amp4_image</local_identifier>
              <offset unit="byte">25718400</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>SignedMSB2</data_type>
                <scaling_factor>1</scaling_factor>
                <value_offset>32768</value_offset>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>2058</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>2080</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
          </File_Area_Observational>'''

        file_obs_area = create_file_area_obs(self.test_raw_4k_header, self.test_raw_filename)

        self.compare_xml(expected, file_obs_area)

    def test_lco_calib(self):
        expected = '''
          <File_Area_Observational>
            <File>
              <file_name>tfn1m001-fa11-20211013-dark-bin1x1.fits</file_name>
              <comment>Median combined stack of dark images. Used in calibration pipeline to generate the calibrated image data.</comment>
            </File>
            <Header>
              <name>main_header</name>
              <offset unit="byte">0</offset>
              <object_length unit="byte">20160</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>tfn1m001-fa11-20211013-dark-bin1x1</local_identifier>
              <offset unit="byte">20160</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>IEEE754MSBSingle</data_type>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>4096</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>4096</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>bpm_header</name>
              <offset unit="byte">67129920</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>bpm_image</local_identifier>
              <offset unit="byte">67132800</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>UnsignedByte</data_type>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>4096</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>4096</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
            <Header>
              <name>err_header</name>
              <offset unit="byte">83911680</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Array_2D_Image>
              <local_identifier>err_image</local_identifier>
              <offset unit="byte">83914560</offset>
              <axes>2</axes>
              <axis_index_order>Last Index Fastest</axis_index_order>
              <Element_Array>
                <data_type>IEEE754MSBSingle</data_type>
              </Element_Array>
              <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>4096</elements>
                <sequence_number>1</sequence_number>
              </Axis_Array>
              <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>4096</elements>
                <sequence_number>2</sequence_number>
              </Axis_Array>
            </Array_2D_Image>
          </File_Area_Observational>'''

        file_obs_area = create_file_area_obs(self.test_lco_calib_header, 'tfn1m001-fa11-20211013-dark-bin1x1.fits')

        self.compare_xml(expected, file_obs_area)


class TestCreateFileAreaTable(SimpleTestCase):

    def setUp(self):

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_ddp_filename = os.path.join(tests_path, 'example_dartphotom.dat')

        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        # Read original file, add blank lines, write new file to temp directory
        with open(self.test_ddp_filename, 'r') as table_file:
            lines = table_file.readlines()
        self.test_lc_file = os.path.join(self.test_dir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        #print("Original length=", len(lines))
        lines.append('\r\n')
        lines.append('\r\n')
        #print("New length=", len(lines))
        with open(self.test_lc_file, 'w', newline='\r\n') as fp:
            fp.writelines(lines)

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_lco_ddp(self):
        expected = '''
          <File_Area_Observational>
            <File>
              <file_name>example_dartphotom.dat</file_name>
              <comment>photometry summary table</comment>
            </File>
             <Header>
               <offset unit="byte">0</offset>
               <object_length unit="byte">143</object_length>
               <parsing_standard_id>UTF-8 Text</parsing_standard_id>
             </Header>
             <Table_Character>
              <offset unit="byte">143</offset>
              <records>62</records>
              <record_delimiter>Carriage-Return Line-Feed</record_delimiter>
              <Record_Character>
                <fields>12</fields>
                <groups>0</groups>
                <record_length unit="byte">143</record_length>
                <Field_Character>
                  <name>validity_flag</name>
                  <field_number>1</field_number>
                  <field_location unit="byte">1</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">1</field_length>
                  <description>Flag whether this is a valid photometric datapoint, # indicates probably invalid blended data due to asteroid interference with the star.</description>
                </Field_Character>
                <Field_Character>
                  <name>file</name>
                  <field_number>2</field_number>
                  <field_location unit="byte">2</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">36</field_length>
                  <description>File name of the calibrated image where data were measured.</description>
                </Field_Character>
                <Field_Character>
                  <name>julian_date</name>
                  <field_number>3</field_number>
                  <field_location unit="byte">40</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">15</field_length>
                  <description>UTC Julian date of the exposure midtime</description>
                </Field_Character>
                <Field_Character>
                  <name>mag</name>
                  <field_number>4</field_number>
                  <field_location unit="byte">56</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Calibrated PanSTARRs r-band apparent magnitude of asteroid</description>
                </Field_Character>
                <Field_Character>
                  <name>sig</name>
                  <field_number>5</field_number>
                  <field_location unit="byte">66</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">6</field_length>
                  <description>1-sigma error on the apparent magnitude</description>
                </Field_Character>
                <Field_Character>
                  <name>ZP</name>
                  <field_number>6</field_number>
                  <field_location unit="byte">73</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Calibrated zero point magnitude in PanSTARRs r-band</description>
                </Field_Character>
                <Field_Character>
                  <name>ZP_sig</name>
                  <field_number>7</field_number>
                  <field_location unit="byte">83</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">6</field_length>
                  <description>1-sigma error on the zero point magnitude</description>
                </Field_Character>
                <Field_Character>
                  <name>inst_mag</name>
                  <field_number>8</field_number>
                  <field_location unit="byte">91</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>instrumental magnitude of asteroid</description>
                </Field_Character>
                <Field_Character>
                  <name>inst_sig</name>
                  <field_number>9</field_number>
                  <field_location unit="byte">101</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>1-sigma error on the instrumental magnitude</description>
                </Field_Character>
                <Field_Character>
                  <name>filter</name>
                  <field_number>10</field_number>
                  <field_location unit="byte">111</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">6</field_length>
                  <description>Transformed filter used for calibration.</description>
                </Field_Character>
                <Field_Character>
                  <name>SExtractor_flag</name>
                  <field_number>11</field_number>
                  <field_location unit="byte">119</field_location>
                  <data_type>ASCII_Integer</data_type>
                  <field_length unit="byte">15</field_length>
                  <description>Flags associated with the Source Extractor photometry measurements. See source_extractor_flags.txt in the documents folder for this archive for more detailed description.</description>
                </Field_Character>
                <Field_Character>
                  <name>aprad</name>
                  <field_number>12</field_number>
                  <field_location unit="byte">136</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">5</field_length>
                  <description>radius in pixels of the aperture used for the photometry measurement</description>
                </Field_Character>
              </Record_Character>
            </Table_Character>
          </File_Area_Observational>'''

        file_table_area = create_file_area_table(self.test_ddp_filename)

        self.compare_xml(expected, file_table_area)

    def test_lco_ddp_blanklines(self):
        expected = '''
          <File_Area_Observational>
            <File>
              <file_name>lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab</file_name>
              <comment>photometry summary table</comment>
            </File>
             <Header>
               <offset unit="byte">0</offset>
               <object_length unit="byte">143</object_length>
               <parsing_standard_id>UTF-8 Text</parsing_standard_id>
             </Header>
             <Table_Character>
              <offset unit="byte">143</offset>
              <records>62</records>
              <record_delimiter>Carriage-Return Line-Feed</record_delimiter>
              <Record_Character>
                <fields>12</fields>
                <groups>0</groups>
                <record_length unit="byte">143</record_length>
                <Field_Character>
                  <name>validity_flag</name>
                  <field_number>1</field_number>
                  <field_location unit="byte">1</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">1</field_length>
                  <description>Flag whether this is a valid photometric datapoint, # indicates probably invalid blended data due to asteroid interference with the star.</description>
                </Field_Character>
                <Field_Character>
                  <name>file</name>
                  <field_number>2</field_number>
                  <field_location unit="byte">2</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">36</field_length>
                  <description>File name of the calibrated image where data were measured.</description>
                </Field_Character>
                <Field_Character>
                  <name>julian_date</name>
                  <field_number>3</field_number>
                  <field_location unit="byte">40</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">15</field_length>
                  <description>UTC Julian date of the exposure midtime</description>
                </Field_Character>
                <Field_Character>
                  <name>mag</name>
                  <field_number>4</field_number>
                  <field_location unit="byte">56</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Calibrated PanSTARRs r-band apparent magnitude of asteroid</description>
                </Field_Character>
                <Field_Character>
                  <name>sig</name>
                  <field_number>5</field_number>
                  <field_location unit="byte">66</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">6</field_length>
                  <description>1-sigma error on the apparent magnitude</description>
                </Field_Character>
                <Field_Character>
                  <name>ZP</name>
                  <field_number>6</field_number>
                  <field_location unit="byte">73</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Calibrated zero point magnitude in PanSTARRs r-band</description>
                </Field_Character>
                <Field_Character>
                  <name>ZP_sig</name>
                  <field_number>7</field_number>
                  <field_location unit="byte">83</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">6</field_length>
                  <description>1-sigma error on the zero point magnitude</description>
                </Field_Character>
                <Field_Character>
                  <name>inst_mag</name>
                  <field_number>8</field_number>
                  <field_location unit="byte">91</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>instrumental magnitude of asteroid</description>
                </Field_Character>
                <Field_Character>
                  <name>inst_sig</name>
                  <field_number>9</field_number>
                  <field_location unit="byte">101</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>1-sigma error on the instrumental magnitude</description>
                </Field_Character>
                <Field_Character>
                  <name>filter</name>
                  <field_number>10</field_number>
                  <field_location unit="byte">111</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">6</field_length>
                  <description>Transformed filter used for calibration.</description>
                </Field_Character>
                <Field_Character>
                  <name>SExtractor_flag</name>
                  <field_number>11</field_number>
                  <field_location unit="byte">119</field_location>
                  <data_type>ASCII_Integer</data_type>
                  <field_length unit="byte">15</field_length>
                  <description>Flags associated with the Source Extractor photometry measurements. See source_extractor_flags.txt in the documents folder for this archive for more detailed description.</description>
                </Field_Character>
                <Field_Character>
                  <name>aprad</name>
                  <field_number>12</field_number>
                  <field_location unit="byte">136</field_location>
                  <data_type>ASCII_Real</data_type>
                  <field_length unit="byte">5</field_length>
                  <description>radius in pixels of the aperture used for the photometry measurement</description>
                </Field_Character>
              </Record_Character>
            </Table_Character>
          </File_Area_Observational>'''

        file_table_area = create_file_area_table(self.test_lc_file)

        self.compare_xml(expected, file_table_area)


class TestCreateFileAreaBinTable(SimpleTestCase):

    def setUp(self):

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_bintable_filename = os.path.join(tests_path, 'example_bintable.fits')

        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_lco_bintable(self):
        expected = '''
          <File_Area_Observational>
            <File>
              <file_name>example_bintable.fits</file_name>
              <comment>multi-aperture photometry summary table</comment>
            </File>
            <Header>
              <name>primary_header</name>
              <offset unit="byte">0</offset>
              <object_length unit="byte">2880</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Header>
              <name>table_header</name>
              <offset unit="byte">2880</offset>
              <object_length unit="byte">8640</object_length>
              <parsing_standard_id>FITS 3.0</parsing_standard_id>
            </Header>
            <Table_Binary>
              <offset unit="byte">11520</offset>
              <records>22</records>
              <Record_Binary>
                <fields>49</fields>
                <groups>0</groups>
                <record_length unit="byte">476</record_length>
                <Field_Binary>
                  <name>filename</name>
                  <field_number>1</field_number>
                  <field_location unit="byte">1</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">36</field_length>
                  <description>Filename of the calibrated image where data were measured.</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mjd</name>
                  <field_number>2</field_number>
                  <field_location unit="byte">37</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>UTC Modified Julian Date of the exposure midtime</description>
                </Field_Binary>
                <Field_Binary>
                  <name>obs_midpoint</name>
                  <field_number>3</field_number>
                  <field_location unit="byte">45</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">36</field_length>
                  <description>UTC datetime string of the exposure midtime</description>
                </Field_Binary>
                <Field_Binary>
                  <name>exptime</name>
                  <field_number>4</field_number>
                  <field_location unit="byte">81</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Exposure time in seconds</description>
                </Field_Binary>
                <Field_Binary>
                  <name>filter</name>
                  <field_number>5</field_number>
                  <field_location unit="byte">89</field_location>
                  <data_type>ASCII_String</data_type>
                  <field_length unit="byte">36</field_length>
                  <description>Name of the filter used</description>
                </Field_Binary>
                <Field_Binary>
                  <name>obs_ra</name>
                  <field_number>6</field_number>
                  <field_location unit="byte">125</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Right ascension of the asteroid</description>
                </Field_Binary>
                <Field_Binary>
                  <name>obs_dec</name>
                  <field_number>7</field_number>
                  <field_location unit="byte">133</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Declination of the asteroid</description>
                </Field_Binary>
                <Field_Binary>
                  <name>flux_radius</name>
                  <field_number>8</field_number>
                  <field_location unit="byte">141</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Flux radius</description>
                </Field_Binary>
                <Field_Binary>
                  <name>fwhm</name>
                  <field_number>9</field_number>
                  <field_location unit="byte">149</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Full Width Half Maximum of the frame</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_0</name>
                  <field_number>10</field_number>
                  <field_location unit="byte">157</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 0th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_0</name>
                  <field_number>11</field_number>
                  <field_location unit="byte">165</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 0th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_1</name>
                  <field_number>12</field_number>
                  <field_location unit="byte">173</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 1st index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_1</name>
                  <field_number>13</field_number>
                  <field_location unit="byte">181</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 1st index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_2</name>
                  <field_number>14</field_number>
                  <field_location unit="byte">189</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 2nd index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_2</name>
                  <field_number>15</field_number>
                  <field_location unit="byte">197</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 2nd index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_3</name>
                  <field_number>16</field_number>
                  <field_location unit="byte">205</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 3rd index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_3</name>
                  <field_number>17</field_number>
                  <field_location unit="byte">213</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 3rd index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_4</name>
                  <field_number>18</field_number>
                  <field_location unit="byte">221</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 4th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_4</name>
                  <field_number>19</field_number>
                  <field_location unit="byte">229</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 4th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_5</name>
                  <field_number>20</field_number>
                  <field_location unit="byte">237</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 5th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_5</name>
                  <field_number>21</field_number>
                  <field_location unit="byte">245</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 5th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_6</name>
                  <field_number>22</field_number>
                  <field_location unit="byte">253</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 6th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_6</name>
                  <field_number>23</field_number>
                  <field_location unit="byte">261</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 6th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_7</name>
                  <field_number>24</field_number>
                  <field_location unit="byte">269</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 7th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_7</name>
                  <field_number>25</field_number>
                  <field_location unit="byte">277</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 7th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_8</name>
                  <field_number>26</field_number>
                  <field_location unit="byte">285</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 8th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_8</name>
                  <field_number>27</field_number>
                  <field_location unit="byte">293</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 8th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_9</name>
                  <field_number>28</field_number>
                  <field_location unit="byte">301</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 9th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_9</name>
                  <field_number>29</field_number>
                  <field_location unit="byte">309</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 9th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_10</name>
                  <field_number>30</field_number>
                  <field_location unit="byte">317</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 10th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_10</name>
                  <field_number>31</field_number>
                  <field_location unit="byte">325</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 10th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_11</name>
                  <field_number>32</field_number>
                  <field_location unit="byte">333</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 11th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_11</name>
                  <field_number>33</field_number>
                  <field_location unit="byte">341</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 11th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_12</name>
                  <field_number>34</field_number>
                  <field_location unit="byte">349</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 12th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_12</name>
                  <field_number>35</field_number>
                  <field_location unit="byte">357</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 12th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_13</name>
                  <field_number>36</field_number>
                  <field_location unit="byte">365</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 13th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_13</name>
                  <field_number>37</field_number>
                  <field_location unit="byte">373</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 13th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_14</name>
                  <field_number>38</field_number>
                  <field_location unit="byte">381</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 14th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_14</name>
                  <field_number>39</field_number>
                  <field_location unit="byte">389</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 14th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_15</name>
                  <field_number>40</field_number>
                  <field_location unit="byte">397</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 15th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_15</name>
                  <field_number>41</field_number>
                  <field_location unit="byte">405</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 15th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_16</name>
                  <field_number>42</field_number>
                  <field_location unit="byte">413</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 16th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_16</name>
                  <field_number>43</field_number>
                  <field_location unit="byte">421</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 16th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_17</name>
                  <field_number>44</field_number>
                  <field_location unit="byte">429</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 17th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_17</name>
                  <field_number>45</field_number>
                  <field_location unit="byte">437</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 17th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_18</name>
                  <field_number>46</field_number>
                  <field_location unit="byte">445</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 18th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_18</name>
                  <field_number>47</field_number>
                  <field_location unit="byte">453</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 18th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_aperture_19</name>
                  <field_number>48</field_number>
                  <field_location unit="byte">461</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude in the 19th index aperture</description>
                </Field_Binary>
                <Field_Binary>
                  <name>mag_err_aperture_19</name>
                  <field_number>49</field_number>
                  <field_location unit="byte">469</field_location>
                  <data_type>IEEE754MSBDouble</data_type>
                  <field_length unit="byte">8</field_length>
                  <description>Magnitude error in the 19th index aperture</description>
                </Field_Binary>
              </Record_Binary>
            </Table_Binary>
          </File_Area_Observational>'''

        file_table_area = create_file_area_bintable(self.test_bintable_filename)

        self.compare_xml(expected, file_table_area)


class TestCreateDisplaySettings(SimpleTestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schema_mappings = pds_schema_mappings(schemadir, '*.xsd')

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_raw_filename = os.path.join(tests_path, 'mef_raw_test_frame.fits')
        self.test_raw_header, table, cattype = open_fits_catalog(self.test_raw_filename)
        test_proc_header = os.path.join(tests_path, 'example_lco_proc_hdr')
        self.test_proc_header = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr["OBSTYPE"] = "DARK"
        for keyword in ['L1IDDARK', 'L1STATDA', 'L1IDFLAT', 'L1STATFL', 'L1MEAN', 'L1MEDIAN', 'L1SIGMA', 'L1FWHM', 'L1ELLIP', 'L1ELLIPA', 'WCSERR']:
            lco_calib_prihdr.remove(keyword)
        lco_bpm_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_bpmhdr'))
        lco_err_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_errhdr'))
        self.test_lco_calib_header = [lco_calib_prihdr, lco_bpm_exthdr, lco_err_exthdr]

        kpno_prihdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_kpno_mef_prihdr'))
        kpno_extnhdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_kpno_mef_extnhdr'))
        self.test_kpno_header = [kpno_prihdr,]
        for extn in range(1, 4+1):
            kpno_extnhdr['extver'] = extn
            kpno_extnhdr['extname'] = 'im' + str(extn)
            kpno_extnhdr['imageid'] = extn
            self.test_kpno_header.append(kpno_extnhdr)

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_raw_frame_single_amp(self):
        expected = '''
          <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
            <Local_Internal_Reference>
              <local_identifier_reference>tfn1m001-fa11-20211013-0095-e92</local_identifier_reference>
              <local_reference_type>display_settings_to_array</local_reference_type>
            </Local_Internal_Reference>
          </disp:Display_Settings>'''

        display_settings = create_display_settings('tfn1m001-fa11-20211013-0095-e92.fits', self.schema_mappings)

        self.compare_xml(expected, display_settings)

    def test_raw_frame_multi_amp(self):
        expected = '''
          <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
            <Local_Internal_Reference>
              <local_identifier_reference>amp1_image</local_identifier_reference>
              <local_identifier_reference>amp2_image</local_identifier_reference>
              <local_identifier_reference>amp3_image</local_identifier_reference>
              <local_identifier_reference>amp4_image</local_identifier_reference>
              <local_reference_type>display_settings_to_array</local_reference_type>
            </Local_Internal_Reference>
          </disp:Display_Settings>'''

        extension_names = ['amp1_image', 'amp2_image', 'amp3_image', 'amp4_image']

        display_settings = create_display_settings(extension_names, self.schema_mappings)

        self.compare_xml(expected, display_settings)


class TestCreateImageArea(SimpleTestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schema_mappings = pds_schema_mappings(schemadir, '*.xsd')

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_raw_filename = os.path.join(tests_path, 'mef_raw_test_frame.fits')
        self.test_raw_header, table, cattype = open_fits_catalog(self.test_raw_filename)
        test_proc_header = os.path.join(tests_path, 'example_lco_proc_hdr')
        self.test_proc_header = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr["OBSTYPE"] = "DARK"
        for keyword in ['L1IDDARK', 'L1STATDA', 'L1IDFLAT', 'L1STATFL', 'L1MEAN', 'L1MEDIAN', 'L1SIGMA', 'L1FWHM', 'L1ELLIP', 'L1ELLIPA', 'WCSERR']:
            lco_calib_prihdr.remove(keyword)
        lco_bpm_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_bpmhdr'))
        lco_err_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_errhdr'))
        self.test_lco_calib_header = [lco_calib_prihdr, lco_bpm_exthdr, lco_err_exthdr]

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_single_filename(self):
        expected = '''
            <img:Imaging xmlns:img="http://pds.nasa.gov/pds4/img/v1">
              <Local_Internal_Reference>
                <local_identifier_reference>tfn0m410-kb98-20210925-0172-e91</local_identifier_reference>
                <local_reference_type>imaging_parameters_to_image_object</local_reference_type>
              </Local_Internal_Reference>
              <img:Exposure>
                <img:exposure_duration unit="s">100.000</img:exposure_duration>
              </img:Exposure>
              <img:Optical_Filter>
                <img:filter_name>w</img:filter_name>
                <img:bandwidth unit="Angstrom">4409.8</img:bandwidth>
                <img:center_filter_wavelength unit="Angstrom">6080.0</img:center_filter_wavelength>
              </img:Optical_Filter>
            </img:Imaging>'''

        image_area = create_image_area(self.test_proc_header, 'tfn0m410-kb98-20210925-0172-e91.fits', self.schema_mappings)

        self.compare_xml(expected, image_area)

    def test_multiple_filenames(self):
        expected = '''
            <img:Imaging xmlns:img="http://pds.nasa.gov/pds4/img/v1">
              <Local_Internal_Reference>
                <local_identifier_reference>tfn0m410-kb98-20210925-0172-e91</local_identifier_reference>
                <local_identifier_reference>tfn0m410-kb98-20210925-0173-e91</local_identifier_reference>
                <local_reference_type>imaging_parameters_to_image_object</local_reference_type>
              </Local_Internal_Reference>
              <img:Exposure>
                <img:exposure_duration unit="s">100.000</img:exposure_duration>
              </img:Exposure>
              <img:Optical_Filter>
                <img:filter_name>w</img:filter_name>
                <img:bandwidth unit="Angstrom">4409.8</img:bandwidth>
                <img:center_filter_wavelength unit="Angstrom">6080.0</img:center_filter_wavelength>
              </img:Optical_Filter>
            </img:Imaging>'''

        image_area = create_image_area(self.test_proc_header,
            ['tfn0m410-kb98-20210925-0172-e91.fits', 'tfn0m410-kb98-20210925-0173-e91.fits'],
            self.schema_mappings)

        self.compare_xml(expected, image_area)


class TestCreateImgDispGeometry(SimpleTestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schema_mappings = pds_schema_mappings(schemadir, '*.xsd')

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_raw_filename = os.path.join(tests_path, 'mef_raw_test_frame.fits')
        self.test_raw_header, table, cattype = open_fits_catalog(self.test_raw_filename)
        test_proc_header = os.path.join(tests_path, 'example_lco_proc_hdr')
        self.test_proc_header = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr["OBSTYPE"] = "DARK"
        for keyword in ['L1IDDARK', 'L1STATDA', 'L1IDFLAT', 'L1STATFL', 'L1MEAN', 'L1MEDIAN', 'L1SIGMA', 'L1FWHM', 'L1ELLIP', 'L1ELLIPA', 'WCSERR']:
            lco_calib_prihdr.remove(keyword)
        lco_bpm_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_bpmhdr'))
        lco_err_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_errhdr'))
        self.test_lco_calib_header = [lco_calib_prihdr, lco_bpm_exthdr, lco_err_exthdr]

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_single_filename(self):
        expected = '''
            <geom:Image_Display_Geometry xmlns:geom="http://pds.nasa.gov/pds4/geom/v1">
              <Local_Internal_Reference>
                <local_identifier_reference>tfn0m410-kb98-20210925-0172-e91</local_identifier_reference>
                <local_reference_type>display_to_data_object</local_reference_type>
              </Local_Internal_Reference>
            </geom:Image_Display_Geometry>'''

        image_area = create_imgdisp_geometry('tfn0m410-kb98-20210925-0172-e91.fits', self.schema_mappings)

        self.compare_xml(expected, image_area)

    def test_multiple_filenames(self):
        expected = '''
            <geom:Image_Display_Geometry xmlns:geom="http://pds.nasa.gov/pds4/geom/v1">
              <Local_Internal_Reference>
                <local_identifier_reference>tfn0m410-kb98-20210925-0172-e91</local_identifier_reference>
                <local_identifier_reference>tfn0m410-kb98-20210925-0173-e91</local_identifier_reference>
                <local_reference_type>display_to_data_object</local_reference_type>
              </Local_Internal_Reference>
            </geom:Image_Display_Geometry>'''

        image_area = create_imgdisp_geometry(
            ['tfn0m410-kb98-20210925-0172-e91.fits', 'tfn0m410-kb98-20210925-0173-e91.fits'],
            self.schema_mappings)

        self.compare_xml(expected, image_area)


class TestCreateDisciplineArea(SimpleTestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schema_mappings = pds_schema_mappings(schemadir, '*.xsd')

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_raw_filename = os.path.join(tests_path, 'mef_raw_test_frame.fits')
        self.test_raw_header, table, cattype = open_fits_catalog(self.test_raw_filename)
        test_proc_header = os.path.join(tests_path, 'example_lco_proc_hdr')
        self.test_proc_header = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr = fits.Header.fromtextfile(test_proc_header)
        lco_calib_prihdr["OBSTYPE"] = "DARK"
        for keyword in ['L1IDDARK', 'L1STATDA', 'L1IDFLAT', 'L1STATFL', 'L1MEAN', 'L1MEDIAN', 'L1SIGMA', 'L1FWHM', 'L1ELLIP', 'L1ELLIPA', 'WCSERR']:
            lco_calib_prihdr.remove(keyword)
        lco_bpm_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_bpmhdr'))
        lco_err_exthdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_lco_calib_errhdr'))
        self.test_lco_calib_header = [lco_calib_prihdr, lco_bpm_exthdr, lco_err_exthdr]

        kpno_prihdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_kpno_mef_prihdr'))
        kpno_extnhdr = fits.Header.fromtextfile(os.path.join(tests_path, 'example_kpno_mef_extnhdr'))
        self.test_kpno_header = [kpno_prihdr,]
        for extn in range(1, 4+1):
            kpno_extnhdr['extver'] = extn
            kpno_extnhdr['extname'] = 'im' + str(extn)
            kpno_extnhdr['imageid'] = extn
            self.test_kpno_header.append(kpno_extnhdr)

        self.maxDiff = None

    def compare_xml(self, expected, xml_element):
        """Compare the expected XML string <expected> with the passed etree.Element
        in <xml_element>
        """

        obj1 = objectify.fromstring(expected)
        expect = etree.tostring(obj1, pretty_print=True)
        result = etree.tostring(xml_element, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_proc_frame(self):
        expected = '''
            <Discipline_Area>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>tfn1m001-fa11-20211013-0095-e92</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <img:Imaging xmlns:img="http://pds.nasa.gov/pds4/img/v1">
                <Local_Internal_Reference>
                    <local_identifier_reference>tfn1m001-fa11-20211013-0095-e92</local_identifier_reference>
                    <local_reference_type>imaging_parameters_to_image_object</local_reference_type>
                  </Local_Internal_Reference>
                <img:Exposure>
                  <img:exposure_duration unit="s">100.000</img:exposure_duration>
                </img:Exposure>
                <img:Optical_Filter>
                  <img:filter_name>w</img:filter_name>
                  <img:bandwidth unit="Angstrom">4409.8</img:bandwidth>
                  <img:center_filter_wavelength unit="Angstrom">6080.0</img:center_filter_wavelength>
                </img:Optical_Filter>
              </img:Imaging>
              <geom:Geometry xmlns:geom="http://pds.nasa.gov/pds4/geom/v1">
                <geom:Image_Display_Geometry>
                  <Local_Internal_Reference>
                    <local_identifier_reference>tfn1m001-fa11-20211013-0095-e92</local_identifier_reference>
                    <local_reference_type>display_to_data_object</local_reference_type>
                  </Local_Internal_Reference>
                  <geom:Display_Direction>
                    <geom:horizontal_display_axis>Sample</geom:horizontal_display_axis>
                    <geom:horizontal_display_direction>Left to Right</geom:horizontal_display_direction>
                    <geom:vertical_display_axis>Line</geom:vertical_display_axis>
                    <geom:vertical_display_direction>Bottom to Top</geom:vertical_display_direction>
                  </geom:Display_Direction>
                  <geom:Object_Orientation_RA_Dec>
                    <geom:right_ascension_angle unit="deg">272.953000</geom:right_ascension_angle>
                    <geom:declination_angle unit="deg">1.280402</geom:declination_angle>
                    <geom:celestial_north_clock_angle unit="deg">0.0</geom:celestial_north_clock_angle>
                    <geom:Reference_Frame_Identification>
                      <geom:name>J2000</geom:name>
                      <geom:comment>equinox of RA and DEC</geom:comment>
                    </geom:Reference_Frame_Identification>
                  </geom:Object_Orientation_RA_Dec>
                </geom:Image_Display_Geometry>
              </geom:Geometry>
            </Discipline_Area>'''

        file_obs_area = create_discipline_area(self.test_proc_header, 'tfn1m001-fa11-20211013-0095-e92.fits', self.schema_mappings)

        self.compare_xml(expected, file_obs_area)

    def test_kpno_mef(self):
        expected = '''
            <Discipline_Area>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>ccd1_image</local_identifier_reference>
                  <local_identifier_reference>ccd2_image</local_identifier_reference>
                  <local_identifier_reference>ccd3_image</local_identifier_reference>
                  <local_identifier_reference>ccd4_image</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <img:Imaging xmlns:img="http://pds.nasa.gov/pds4/img/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>ccd1_image</local_identifier_reference>
                  <local_identifier_reference>ccd2_image</local_identifier_reference>
                  <local_identifier_reference>ccd3_image</local_identifier_reference>
                  <local_identifier_reference>ccd4_image</local_identifier_reference>
                  <local_reference_type>imaging_parameters_to_image_object</local_reference_type>
                </Local_Internal_Reference>
                <img:Exposure>
                  <img:exposure_duration unit="s">120.000</img:exposure_duration>
                </img:Exposure>
                <img:Optical_Filter>
                  <img:filter_name>R Harris k1004</img:filter_name>
                </img:Optical_Filter>
              </img:Imaging>
              <geom:Geometry xmlns:geom="http://pds.nasa.gov/pds4/geom/v1">
                <geom:Image_Display_Geometry>
                  <Local_Internal_Reference>
                    <local_identifier_reference>ccd1_image</local_identifier_reference>
                    <local_identifier_reference>ccd2_image</local_identifier_reference>
                    <local_identifier_reference>ccd3_image</local_identifier_reference>
                    <local_identifier_reference>ccd4_image</local_identifier_reference>
                    <local_reference_type>display_to_data_object</local_reference_type>
                  </Local_Internal_Reference>
                  <geom:Display_Direction>
                    <geom:horizontal_display_axis>Sample</geom:horizontal_display_axis>
                    <geom:horizontal_display_direction>Left to Right</geom:horizontal_display_direction>
                    <geom:vertical_display_axis>Line</geom:vertical_display_axis>
                    <geom:vertical_display_direction>Bottom to Top</geom:vertical_display_direction>
                  </geom:Display_Direction>
                  <geom:Object_Orientation_RA_Dec>
                    <geom:right_ascension_angle unit="deg">206.689792</geom:right_ascension_angle>
                    <geom:declination_angle unit="deg">-11.545108</geom:declination_angle>
                    <geom:celestial_north_clock_angle unit="deg">0.0</geom:celestial_north_clock_angle>
                    <geom:Reference_Frame_Identification>
                      <geom:name>J2000</geom:name>
                      <geom:comment>equinox of RA and DEC</geom:comment>
                    </geom:Reference_Frame_Identification>
                  </geom:Object_Orientation_RA_Dec>
                </geom:Image_Display_Geometry>
              </geom:Geometry>
            </Discipline_Area>'''

        file_obs_area = create_discipline_area(self.test_kpno_header, 'kp050709_031.fit', self.schema_mappings)


        self.compare_xml(expected, file_obs_area)

    def test_raw_frame(self):
        expected = '''
            <Discipline_Area>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>amp1_image</local_identifier_reference>
                  <local_identifier_reference>amp2_image</local_identifier_reference>
                  <local_identifier_reference>amp3_image</local_identifier_reference>
                  <local_identifier_reference>amp4_image</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <img:Imaging xmlns:img="http://pds.nasa.gov/pds4/img/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>amp1_image</local_identifier_reference>
                  <local_identifier_reference>amp2_image</local_identifier_reference>
                  <local_identifier_reference>amp3_image</local_identifier_reference>
                  <local_identifier_reference>amp4_image</local_identifier_reference>
                  <local_reference_type>imaging_parameters_to_image_object</local_reference_type>
                </Local_Internal_Reference>
                <img:Exposure>
                  <img:exposure_duration unit="s">94.975</img:exposure_duration>
                </img:Exposure>
                <img:Optical_Filter>
                  <img:filter_name>w</img:filter_name>
                  <img:bandwidth unit="Angstrom">4409.8</img:bandwidth>
                  <img:center_filter_wavelength unit="Angstrom">6080.0</img:center_filter_wavelength>
                </img:Optical_Filter>
              </img:Imaging>
              <geom:Geometry xmlns:geom="http://pds.nasa.gov/pds4/geom/v1">
                <geom:Image_Display_Geometry>
                  <Local_Internal_Reference>
                    <local_identifier_reference>amp1_image</local_identifier_reference>
                    <local_identifier_reference>amp2_image</local_identifier_reference>
                    <local_identifier_reference>amp3_image</local_identifier_reference>
                    <local_identifier_reference>amp4_image</local_identifier_reference>
                    <local_reference_type>display_to_data_object</local_reference_type>
                  </Local_Internal_Reference>
                  <geom:Display_Direction>
                    <geom:horizontal_display_axis>Sample</geom:horizontal_display_axis>
                    <geom:horizontal_display_direction>Left to Right</geom:horizontal_display_direction>
                    <geom:vertical_display_axis>Line</geom:vertical_display_axis>
                    <geom:vertical_display_direction>Bottom to Top</geom:vertical_display_direction>
                  </geom:Display_Direction>
                  <geom:Object_Orientation_RA_Dec>
                    <geom:right_ascension_angle unit="deg">287.324817</geom:right_ascension_angle>
                    <geom:declination_angle unit="deg">59.493929</geom:declination_angle>
                    <geom:celestial_north_clock_angle unit="deg">0.0</geom:celestial_north_clock_angle>
                    <geom:Reference_Frame_Identification>
                      <geom:name>J2000</geom:name>
                      <geom:comment>equinox of RA and DEC</geom:comment>
                    </geom:Reference_Frame_Identification>
                  </geom:Object_Orientation_RA_Dec>
                </geom:Image_Display_Geometry>
              </geom:Geometry>
            </Discipline_Area>'''

        file_obs_area = create_discipline_area(self.test_raw_header, 'tfn1m001-fa11-20211013-0095-e00.fits', self.schema_mappings)

        self.compare_xml(expected, file_obs_area)

    def test_calib_frame(self):
        expected = '''
            <Discipline_Area>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>tfn1m001-fa11-20211013-dark-bin1x1</local_identifier_reference>
                  <local_identifier_reference>bpm_image</local_identifier_reference>
                  <local_identifier_reference>err_image</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <img:Imaging xmlns:img="http://pds.nasa.gov/pds4/img/v1">
                <Local_Internal_Reference>
                    <local_identifier_reference>tfn1m001-fa11-20211013-dark-bin1x1</local_identifier_reference>
                    <local_identifier_reference>bpm_image</local_identifier_reference>
                    <local_identifier_reference>err_image</local_identifier_reference>
                    <local_reference_type>imaging_parameters_to_image_object</local_reference_type>
                  </Local_Internal_Reference>
                <img:Exposure>
                  <img:exposure_duration unit="s">100.000</img:exposure_duration>
                </img:Exposure>
                <img:Optical_Filter>
                  <img:filter_name>w</img:filter_name>
                  <img:bandwidth unit="Angstrom">4409.8</img:bandwidth>
                  <img:center_filter_wavelength unit="Angstrom">6080.0</img:center_filter_wavelength>
                </img:Optical_Filter>
              </img:Imaging>
              <geom:Geometry xmlns:geom="http://pds.nasa.gov/pds4/geom/v1">
                <geom:Image_Display_Geometry>
                  <Local_Internal_Reference>
                    <local_identifier_reference>tfn1m001-fa11-20211013-dark-bin1x1</local_identifier_reference>
                    <local_identifier_reference>bpm_image</local_identifier_reference>
                    <local_identifier_reference>err_image</local_identifier_reference>
                    <local_reference_type>display_to_data_object</local_reference_type>
                  </Local_Internal_Reference>
                  <geom:Display_Direction>
                    <geom:horizontal_display_axis>Sample</geom:horizontal_display_axis>
                    <geom:horizontal_display_direction>Left to Right</geom:horizontal_display_direction>
                    <geom:vertical_display_axis>Line</geom:vertical_display_axis>
                    <geom:vertical_display_direction>Bottom to Top</geom:vertical_display_direction>
                  </geom:Display_Direction>
                  <geom:Object_Orientation_RA_Dec>
                    <geom:right_ascension_angle unit="deg">272.953000</geom:right_ascension_angle>
                    <geom:declination_angle unit="deg">1.280402</geom:declination_angle>
                    <geom:celestial_north_clock_angle unit="deg">0.0</geom:celestial_north_clock_angle>
                    <geom:Reference_Frame_Identification>
                      <geom:name>J2000</geom:name>
                      <geom:comment>equinox of RA and DEC</geom:comment>
                    </geom:Reference_Frame_Identification>
                  </geom:Object_Orientation_RA_Dec>
                </geom:Image_Display_Geometry>
              </geom:Geometry>
            </Discipline_Area>'''

        file_obs_area = create_discipline_area(self.test_lco_calib_header, 'tfn1m001-fa11-20211013-dark-bin1x1.fits', self.schema_mappings)

        self.compare_xml(expected, file_obs_area)


class TestPreambleMapping(SimpleTestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.schema_mappings = pds_schema_mappings(self.schemadir, '*.xsd')
        new_schemadir = os.path.abspath(os.path.join('photometrics', 'configs', 'PDS_schemas'))
        self.new_schema_mappings = pds_schema_mappings(new_schemadir, '*.xsd')
        self.pds_schema_only = {'PDS4::PDS' : self.schema_mappings['PDS4::PDS']}

        self.test_orig_dict = OrderedDict([('PDS4::PDS',
              b'<?xml-model href="https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1F00.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>'),
             ('PDS4::DISP',
              b'<?xml-model href="https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>'),
             ('PDS4::IMG',
              b'<?xml-model href="https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1F00_1810.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>'),
             ('PDS4::GEOM',
              b'<?xml-model href="https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1F00_1910.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>')
              ])

        self.test_new_dict = OrderedDict([('PDS4::PDS',
              b'<?xml-model href="https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1J00.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>'),
             ('PDS4::DISP',
              b'<?xml-model href="https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1J00_1510.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>'),
             ('PDS4::IMG',
              b'<?xml-model href="https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1J00_1870.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>'),
             ('PDS4::GEOM',
              b'<?xml-model href="https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1J00_1960.sch"\n            schematypens="http://purl.oclc.org/dsdl/schematron"?>')
              ])

        self.test_pdsonly_dict = OrderedDict([('PDS4::PDS' , self.test_orig_dict['PDS4::PDS'])])
        self.maxDiff = None

    def test_original_mapping(self):

        mapping_dict = preamble_mapping(self.schema_mappings)

        self.assertEqual(self.test_orig_dict, mapping_dict)

    def test_original_mapping_pds(self):

        mapping_dict = preamble_mapping(self.pds_schema_only)

        self.assertEqual(self.test_pdsonly_dict, mapping_dict)

    def test_new_mapping(self):

        mapping_dict = preamble_mapping(self.new_schema_mappings)

        self.assertEqual(self.test_new_dict, mapping_dict)


class TestWritePDSLabel(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        schema_mappings = pds_schema_mappings(self.schemadir, '*.xsd')
        self.pds_schema = schema_mappings['PDS4::PDS']
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.test_xml_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label.xml'))
        self.test_xml_cat_didymos = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_didymos.xml'))
        self.test_xml_raw_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_raw.xml'))
        self.test_xml_ddp_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_ddp.xml'))
        self.test_xml_ddp_bintable_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_ddp_bintable.xml'))
        self.test_xml_bpm_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_bpm.xml'))
        self.test_xml_bias_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_bias.xml'))
        self.test_xml_dark_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_dark.xml'))
        self.test_xml_flat_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_flat.xml'))

        test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        self.test_raw_file = os.path.abspath(os.path.join('photometrics', 'tests', 'mef_raw_test_frame.fits'))

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_dartphotom.dat'))
        test_lc_bintable_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_bintable.fits'))
        # Copy files to input directory, renaming lc files
        self.test_lc_file = os.path.join(self.test_dir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, self.test_lc_file)
        self.test_lc_bintable_file = os.path.join(self.test_dir, 'lcogt_1m0_12_ef04_20220926_65803didymos_photometry.fits')
        shutil.copy(test_lc_bintable_file, self.test_lc_bintable_file)
        self.test_banzai_file = os.path.join(self.test_dir, os.path.basename(test_banzai_file))
        shutil.copy(test_banzai_file, self.test_banzai_file)


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
            if self.debug_print:
                print("Not removing temporary test directory", self.test_dir)


    def compare_xml_files(self, expected_xml_file, xml_file, modifications={}):
        """Compare the expected XML in <expected_xml_file> with that in the passed
        <xml_file>. Can pass a dict of [modifications] to alter the XML in <expected_xml_file>;
        the modifications dict should contain:
            'xpath' : XPath to the element to modify (e.g. './/pds:Target_Identification/pds:name'),
            'namespaces' : dict of namespaces for elements (e.g. {'pds': 'http://pds.nasa.gov/pds4/pds/v1'}),
            'replacement' : replacement text for the modified element (e.g. '(65803) Didymos'
        """

        obj1 = etree.parse(expected_xml_file)
        if len(modifications) >= 1:
            elements = obj1.xpath(modifications['xpath'], namespaces=modifications['namespaces'])
            for element in elements:
                element.text = modifications['replacement']

        expect = etree.tostring(obj1, pretty_print=True)
        obj2 = etree.parse(xml_file)
        result = etree.tostring(obj2, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_write_proc_label(self):

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(self.test_banzai_file, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        self.compare_xml_files(self.test_xml_cat, output_xml_file)

    def test_write_proc_label_body_name(self):

        # modify object name in FITS file to match Body
        hdulist = fits.open(self.test_banzai_file, mode='update')
        hdulist[0].header['OBJECT'] = '65803'
        hdulist.close()

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(self.test_banzai_file, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        bodies = Body.objects.all()
        self.assertEqual(1, bodies.count())
        self.assertEqual('65803 Didymos', bodies[0].full_name())
        # Define modifications to the standard XML for the new name
        # modifications = { 'xpath' : './/pds:Target_Identification/pds:name',
                          # 'namespaces' : {'pds' : self.pds_schema['namespace']},
                          # 'replacement' : '(65803) Didymos'}

        self.compare_xml_files(self.test_xml_cat_didymos, output_xml_file)

    def test_write_bpm_label(self):

        # Create example bpm frame
        hdulist = fits.open(self.test_raw_file)
        for hdu in hdulist:
            hdu.header['obstype'] = 'BPM'
            hdu.header['moltype'] = 'BIAS'
            hdu.header['exptime'] = 900
            hdu.header['extname'] = 'BPM'
            hdu.data = np.zeros(hdu.shape, np.uint8)
        test_bpm_file = os.path.join(self.test_dir, 'banzai-test-bpm-bin1x1.fits')
        hdulist.writeto(test_bpm_file, checksum=True, overwrite=True)
        hdulist.close()

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(test_bpm_file, output_xml_file, self.schemadir, mod_time=datetime(2021,6,24))

        self.compare_xml_files(self.test_xml_bpm_cat, output_xml_file)

    def test_write_bias_label(self):

        # Create example bias frame
        hdulist = fits.open(self.test_banzai_file)
        hdulist[0].header['obstype'] = 'BIAS'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_bias_file = os.path.join(self.test_dir, 'banzai-test-bias-bin1x1.fits')
        hdulist.writeto(test_bias_file, checksum=True, overwrite=True)
        hdulist.close()

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(test_bias_file, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        self.compare_xml_files(self.test_xml_bias_cat, output_xml_file)

    def test_write_dark_label(self):

        # Create example dark frame
        hdulist = fits.open(self.test_banzai_file)
        hdulist[0].header['obstype'] = 'DARK'
        hdulist[0].header['moltype'] = 'DARK'
        hdulist[0].header['exptime'] = 300
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_dark_file = os.path.join(self.test_dir, 'banzai-test-dark-bin1x1.fits')
        hdulist.writeto(test_dark_file, checksum=True, overwrite=True)
        hdulist.close()

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(test_dark_file, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        self.compare_xml_files(self.test_xml_dark_cat, output_xml_file)

    def test_write_flat_label(self):

        # Create example flat frame
        hdulist = fits.open(self.test_banzai_file)
        hdulist[0].header['obstype'] = 'SKYFLAT'
        hdulist[0].header['moltype'] = 'SKYFLAT'
        hdulist[0].header['exptime'] = 2.5
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_flat_file = os.path.join(self.test_dir, 'banzai-test-flat-bin1x1.fits')
        hdulist.writeto(test_flat_file, checksum=True, overwrite=True)
        hdulist.close()

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(test_flat_file, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        self.compare_xml_files(self.test_xml_flat_cat, output_xml_file)

    def test_write_raw_label(self):

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(self.test_raw_file, output_xml_file, self.schemadir, mod_time=datetime(2021,10,15))

        self.compare_xml_files(self.test_xml_raw_cat, output_xml_file)

    def test_write_ddp_label(self):

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(self.test_lc_file, output_xml_file, self.schemadir, mod_time=datetime(2021,10,15))

        self.compare_xml_files(self.test_xml_ddp_cat, output_xml_file)

    def test_write_ddp_bintable_label(self):

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(self.test_lc_bintable_file, output_xml_file, self.schemadir, mod_time=datetime(2021,10,15))

        self.compare_xml_files(self.test_xml_ddp_bintable_cat, output_xml_file)


class TestCreatePDSLabels(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        test_xml_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label.xml'))
        with open(test_xml_cat, 'r') as xml_file:
            self.expected_xml = xml_file.readlines()

        self.tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'banzai_test_frame.fits'
        test_file_path = os.path.join(self.tests_path, self.test_file)

#        self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')


        # Make one copy and rename to an -e92 (so it will get picked up) and
        # a second copy which is renamed to an -e91 (so it shouldn't be found)
        new_name = os.path.join(self.test_dir, 'cpt1m013-kb76-20160606-0396-e92.fits')
        self.test_banzai_file = shutil.copy(test_file_path, new_name)
        new_name = os.path.join(self.test_dir, 'cpt1m013-kb76-20160606-0396-e91.fits')
        shutil.copy(test_file_path, new_name)

        test_lc_file = os.path.join(self.tests_path, 'example_dartphotom.dat')
        # Copy files to input directory, renaming lc file
        self.test_lc_file = os.path.join(self.test_dir, 'lcogt_tfn_fa11_20211013_12345_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, self.test_lc_file)

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
            if self.debug_print:
                print("Not removing temporary test directory", self.test_dir)

    def test_generate_e92(self):

        expected_xml_labels = [self.test_banzai_file.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for xml_file in xml_labels:
            self.assertTrue(os.path.exists(xml_file))

    def test_generate_e92_specified_match(self):

        expected_xml_labels = [self.test_banzai_file.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir, '\S*e92')

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for xml_file in xml_labels:
            self.assertTrue(os.path.exists(xml_file))

    def test_generate_e92_body_name(self):

        # modify object name in FITS file to match Body
        hdulist = fits.open(self.test_banzai_file, mode='update')
        hdulist[0].header['OBJECT'] = '65803'
        hdulist.close()

        expected_xml_labels = [self.test_banzai_file.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir)

        bodies = Body.objects.all()
        self.assertEqual(1, bodies.count())
        self.assertEqual('65803 Didymos', bodies[0].full_name())
        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for xml_file in xml_labels:
            self.assertTrue(os.path.exists(xml_file))

    def test_generate_bias(self):

        hdulist = fits.open(self.test_banzai_file)
        hdulist[0].header['obstype'] = 'BIAS'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_bias_file = os.path.join(self.test_dir, 'cpt1m013-kb76-20160606-bias-bin1x1.fits')
        hdulist.writeto(test_bias_file, checksum=True, overwrite=True)
        hdulist.close()

        expected_xml_labels = [test_bias_file.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir, '.*-bias.*')

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for xml_file in xml_labels:
            self.assertTrue(os.path.exists(xml_file))

    def test_generate_ddp(self):

        expected_xml_labels = [self.test_lc_file.replace('.tab', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir, '*photometry.tab')

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for xml_file in xml_labels:
            self.assertTrue(os.path.exists(xml_file))

    def test_generate_ddp_fits(self):

        # Copy FITS files to output directory, renaming phot file and removing
        # ASCII tab file
        test_lc_file = os.path.abspath(os.path.join(self.tests_path, 'example_bintable.fits'))
        new_name = os.path.join(self.test_dir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.fits')
        shutil.copy(test_lc_file, new_name)
        os.remove(self.test_lc_file)

        expected_xml_labels = [new_name.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir, match='*photometry.fits')

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for xml_file in xml_labels:
            self.assertTrue(os.path.exists(xml_file))


class TestSplitFilename(SimpleTestCase):

    def test_cpt_1m(self):
        expected_parts = { 'site' : 'cpt',
                           'tel_class' : '1m0',
                           'tel_serial' : '13',
                           'instrument' : 'fa14',
                           'dayobs' : '20211013',
                           'frame_num' : '0035',
                           'frame_type' : 'e91',
                           'extension' : '.fits'
                          }

        parts = split_filename('cpt1m013-fa14-20211013-0035-e91.fits')

        self.assertEqual(expected_parts, parts)

    def test_tfn_1m(self):
        expected_parts = { 'site' : 'tfn',
                           'tel_class' : '1m0',
                           'tel_serial' : '01',
                           'instrument' : 'fa11',
                           'dayobs' : '20211013',
                           'frame_num' : '0126',
                           'frame_type' : 'e91',
                           'extension' : '.fits'
                         }

        parts = split_filename('tfn1m001-fa11-20211013-0126-e91.fits')

        self.assertEqual(expected_parts, parts)

    def test_Swope_1m(self):
        expected_parts = { 'site' : 'lco',
                           'tel_class' : '1m0',
                           'tel_serial' : '01',
                           'instrument' : 'Direct4Kx4K-4',
                           'dayobs' : '20220925',
                           'frame_num' : '1258',
                           'frame_type' : 'e72',
                           'extension' : '.fits'
                         }

        parts = split_filename('rccd1258.fits')

        self.assertEqual(expected_parts, parts)

    def test_Swope_1m_long(self):
        expected_parts = { 'site' : 'lco',
                           'tel_class' : '1m0',
                           'tel_serial' : '01',
                           'instrument' : 'Direct4Kx4K-4',
                           'dayobs' : '20220924',
                           'frame_num' : '1258',
                           'frame_type' : 'e72',
                           'extension' : '.fits'
                         }

        parts = split_filename('rccd-20220924-1258.fits')

        self.assertEqual(expected_parts, parts)

    def test_Swope_1m_banzai(self):
        expected_parts = { 'site' : 'lco',
                           'tel_class' : '1m0',
                           'tel_serial' : '01',
                           'instrument' : 'Direct4Kx4K-4',
                           'dayobs' : '20220824',
                           'frame_num' : '1473',
                           'frame_type' : 'e72',
                           'extension' : '.fits'
                         }

        parts = split_filename('ccd1473-20220824-e91.fits')

        self.assertEqual(expected_parts, parts)

    def test_invalid(self):
        expected_parts = {'extension' : '.fits',}

        parts = split_filename('foobar.fits')

        self.assertEqual(expected_parts, parts)


class TestMakePDSAsteroidName(SimpleTestCase):

    def test_none(self):
        expected_filename = None
        expected_pds_name = None

        filename, pds_name = make_pds_asteroid_name(None)

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_pds_name, pds_name)

    def test_nullstring(self):
        expected_filename = None
        expected_pds_name = None

        filename, pds_name = make_pds_asteroid_name('')

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_pds_name, pds_name)

    def test_12923_Zephyr(self):
        expected_filename = '12923zephyr'
        expected_pds_name = '(12923) Zephyr'

        filename, pds_name = make_pds_asteroid_name('12923 Zephyr (1999 GK4)')

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_pds_name, pds_name)

    def test_didymos(self):
        expected_filename = '65803didymos'
        expected_pds_name = '(65803) Didymos'

        filename, pds_name = make_pds_asteroid_name('65803 Didymos (1996 GT)')

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_pds_name, pds_name)

    def test_unnumbered_ast(self):
        expected_filename = '2021so2'
        expected_pds_name = '2021 SO2'

        filename, pds_name = make_pds_asteroid_name('2021 SO2')

        self.assertEqual(expected_filename, filename)
        self.assertEqual(expected_pds_name, pds_name)

class TestDetermineTargetNameType(TestCase):

    def setUp(self):

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

        self.test_header = fits.Header({'SIMPLE' : True, 'OBJECT' : '65803   ',
            'SRCTYPE' : 'MINORPLANET',
            'OBSTYPE' : 'EXPOSE  ',
            })

    def test_expose_known_ast_didymos(self):
        expected_name = '(65803) Didymos'
        expected_type = 'Asteroid'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_expose_known_ast_notdidymos(self):
        expected_name = '(12923) Zephyr'
        expected_type = 'Asteroid'

        self.test_header['object'] = '12923'
        self.test_body.name = '12923'
        self.test_body.save()
        new_desigs = {'#' : 12923, 'N' : 'Zephyr'}
        for desig_type, new_value in new_desigs.items():
            desig = Designations.objects.get(desig_type=desig_type)
            desig.value = new_value
            desig.save()

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_expose_known_ast_nodesigs(self):
        expected_name = '(12923) Zephyr'
        expected_type = 'Asteroid'

        self.test_header['object'] = '12923'
        self.test_body.name = '12923'
        self.test_body.save()
        Designations.objects.filter(body=self.test_body).delete()

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_expose_unknown_ast(self):
        expected_name = '(12923) Zephyr'
        expected_type = 'Asteroid'

        self.test_header['object'] = '12923'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_expose_unknown_ast_no_jpl(self):
        expected_name = 'XL8B85F'
        expected_type = 'Asteroid'

        self.test_header['object'] = 'XL8B85F'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_expose_unknown_ast_no_shortname(self):
        expected_name = '2021 SO2'
        expected_type = 'Asteroid'

        self.test_header['object'] = '2021 SO2'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_bpm(self):
        expected_name = 'BPM'
        expected_type = 'Calibrator'
        self.test_header['object'] = '41 Cyg x talk q 2'
        self.test_header['obstype'] = 'BPM'
        self.test_header['srctype'] = 'EXTRASOLAR'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_bias(self):
        expected_name = 'BIAS'
        expected_type = 'Calibrator'

        self.test_header['object'] = 'N/A'
        self.test_header['obstype'] = 'BIAS'
        self.test_header['srctype'] = 'N/A'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_dark(self):
        expected_name = 'DARK'
        expected_type = 'Calibrator'

        self.test_header['object'] = 'N/A'
        self.test_header['obstype'] = 'DARK'
        self.test_header['srctype'] = 'N/A'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)

    def test_skyflat(self):
        expected_name = 'FLAT FIELD'
        expected_type = 'Calibrator'

        self.test_header['object'] = 'Flat'
        self.test_header['obstype'] = 'SKYFLAT'
        self.test_header['srctype'] = 'CALIBRATION'

        target_name, target_type = determine_target_name_type(self.test_header)

        self.assertEqual(expected_name, target_name)
        self.assertEqual(expected_type, target_type)


class TestDetermineFirstLastTimesFromTable(SimpleTestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_dartphotom.dat'))
        test_lc_bintable_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_bintable.fits'))

        # Copy files to input directory, renaming lc files
        self.test_lc_file = os.path.join(self.test_dir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, self.test_lc_file)
        self.test_lc_bintable_file = os.path.join(self.test_dir, 'lcogt_1m0_10_ef02_20220926_65803didymos_photometry.fits')
        shutil.copy(test_lc_bintable_file, self.test_lc_bintable_file)

    def test_ascii(self):
        expected_first_time = datetime(2021, 10, 12, 20, 0, 52, 346863)
        expected_last_time = datetime(2021, 10, 12, 20, 57, 10, 85774)

        first_frametime, last_frametime = determine_first_last_times_from_table(self.test_lc_file)

        self.assertEqual(expected_first_time, first_frametime)
        self.assertEqual(expected_last_time, last_frametime)

    def test_ascii_subdir(self):
        expected_first_time = datetime(2021, 10, 12, 20, 0, 52, 346863)
        expected_last_time = datetime(2021, 10, 12, 20, 57, 10, 85774)

        os.mkdir(os.path.join(self.test_dir, '20220926'))
        self.test_lc_file = shutil.move(self.test_lc_file, os.path.join(self.test_dir, '20220926'))
        first_frametime, last_frametime = determine_first_last_times_from_table(self.test_lc_file)

        self.assertEqual(expected_first_time, first_frametime)
        self.assertEqual(expected_last_time, last_frametime)

    def test_bintable(self):
        expected_first_time = datetime(2022, 9, 26, 23, 3, 41, 986000)
        expected_last_time = datetime(2022, 9, 26, 23, 9, 23, 601500)

        first_frametime, last_frametime = determine_first_last_times_from_table(self.test_lc_bintable_file, match_pattern='*_photometry.fits')

        self.assertEqual(expected_first_time, first_frametime)
        self.assertEqual(expected_last_time, last_frametime)

    def test_bintable_subdir(self):
        expected_first_time = datetime(2022, 9, 26, 23, 3, 41, 986000)
        expected_last_time = datetime(2022, 9, 26, 23, 9, 23, 601500)

        os.mkdir(os.path.join(self.test_dir, '20220926'))
        self.test_lc_bintable_file = shutil.move(self.test_lc_bintable_file, os.path.join(self.test_dir, '20220926'))
        first_frametime, last_frametime = determine_first_last_times_from_table(self.test_lc_bintable_file, match_pattern='*_photometry.fits')

        self.assertEqual(expected_first_time, first_frametime)
        self.assertEqual(expected_last_time, last_frametime)


class TestDetermineFilenameFromTable(SimpleTestCase):

    def setUp(self):
        self.test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_dartphotom.dat'))

    def test_none(self):
        expected_filename = None

        filename = determine_filename_from_table(None)

        self.assertEqual(expected_filename, filename)

    def test_nonexistant(self):
        expected_filename = None

        filename = determine_filename_from_table('\tmp\wibble')

        self.assertEqual(expected_filename, filename)

    def test_tfn(self):
        expected_filename = 'tfn1m001-fa11-20211012-0073-e91.fits'

        filename = determine_filename_from_table(self.test_lc_file)

        self.assertEqual(expected_filename, filename)


class TestExportBlockToPDS(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.docs_root = os.path.abspath(os.path.join('photometrics', 'configs', 'PDS_docs'))
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_cal.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_cal = xml_file.readlines()
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_raw.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_raw = xml_file.readlines()
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_ddp.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_ddp = xml_file.readlines()

        self.framedir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'banzai_test_frame.fits'
        self.test_file_path = os.path.join(self.framedir, self.test_file)

#        self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.test_input_dir = os.path.join(self.test_dir, 'input_testblock')
        self.test_input_daydir = os.path.join(self.test_input_dir,  '20211013')
        os.makedirs(self.test_input_daydir, exist_ok=True)
        self.test_output_dir = os.path.join(self.test_dir, 'output')
        os.makedirs(self.test_output_dir, exist_ok=True)
        self.expected_root_dir = os.path.join(self.test_output_dir, '')
        self.test_ddp_daydir = os.path.join(self.expected_root_dir, 'data_lcogtddp')
        self.test_blockdir = 'lcogt_1m0_01_fa11_20211013'
        self.test_daydir = os.path.join(self.test_ddp_daydir, self.test_blockdir)

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
                         'block_start' : datetime(2021, 10, 13, 0, 40),
                         'block_end' : datetime(2021, 10, 14, 0, 40),
                         'obstype' : Block.OPT_IMAGING,
                         'num_observed' : 1
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)
        # Second block with no frames attached
        block_params['num_observed'] = 0
        self.test_block2, created = Block.objects.get_or_create(**block_params)

        frame_params = {
                         'sitecode' : 'Z24',
                         'instrument' : 'fa11',
                         'filter' : 'ip',
                         'block' : self.test_block,
                         'frametype' : Frame.BANZAI_RED_FRAMETYPE,
                         'zeropoint' : 27.0,
                         'zeropoint_err' : 0.03,
                         'midpoint' : block_params['block_start'] + timedelta(minutes=5)
                       }

        self.test_banzai_files = []
        source_details = { 45234032 : {'mag' : 14.8447, 'err_mag' : 0.0054, 'flags' : 0},
                           45234584 : {'mag' : 14.8637, 'err_mag' : 0.0052, 'flags' : 3},
                           45235052 : {'mag' : 14.8447, 'err_mag' : 0.0051, 'flags' : 0}
                         }
        for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
            frame_params['filename'] = f"tfn1m001-fa11-20211013-{frame_num:04d}-e91.fits"
            frame_params['midpoint'] += timedelta(minutes=frame_num-65)
            frame_params['frameid'] = frameid
            frame, created = Frame.objects.get_or_create(**frame_params)
            # Create NEOX_RED_FRAMETYPE type also
            red_frame_params = frame_params.copy()
            red_frame_params['frametype'] = Frame.NEOX_RED_FRAMETYPE
            red_frame_params['filename'] = red_frame_params['filename'].replace('e91', 'e92')
            frame, created = Frame.objects.get_or_create(**red_frame_params)

            cat_source = source_details[frameid]
            source_params = { 'body' : self.test_body,
                              'frame' : frame,
                              'obs_ra' : 208.728,
                              'obs_dec' : -10.197,
                              'obs_mag' : cat_source['mag'],
                              'err_obs_ra' : 0.0003,
                              'err_obs_dec' : 0.0003,
                              'err_obs_mag' : cat_source['err_mag'],
                              'astrometric_catalog' : frame.astrometric_catalog,
                              'photometric_catalog' : frame.photometric_catalog,
                              'aperture_size' : 10*0.389,
                              'snr' : 1/cat_source['err_mag'],
                              'flags' : cat_source['flags']
                            }
            source, created = SourceMeasurement.objects.get_or_create(**source_params)
            source_params = { 'frame' : frame,
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
            for extn in ['e00', 'e92-ldac', 'e92.bkgsub', 'e92', 'e92.rms']:
                new_name = os.path.join(self.test_input_daydir, frame_params['filename'].replace('e91', extn))
                filename = shutil.copy(self.test_file_path, new_name)
                # Change object name to 65803
                with fits.open(filename) as hdulist:
                    hdulist[0].header['telescop'] = '1m0-01'
                    hdulist[0].header['instrume'] = 'fa15'
                    hdulist[0].header['object'] = '65803   '
                    half_exp = timedelta(seconds=hdulist[0].header['exptime'] / 2.0)
                    date_obs = frame_params['midpoint'] - half_exp
                    hdulist[0].header['date-obs'] = date_obs.strftime("%Y-%m-%dT%H:%M:%S")
                    utstop = frame_params['midpoint'] + half_exp + timedelta(seconds=8.77)
                    hdulist[0].header['utstop'] = utstop.strftime("%H:%M:%S.%f")[0:12]
                    hdulist.writeto(filename, overwrite=True, checksum=True)
#                    hdulist.close()
                self.test_banzai_files.append(os.path.basename(filename))

        # Make one additional copy which is renamed to an -e91 (so it shouldn't be found)
        new_name = os.path.join(self.test_input_daydir, 'tfn1m001-fa11-20211013-0065-e91.fits')
        shutil.copy(self.test_file_path, new_name)
        self.test_banzai_files.insert(1, os.path.basename(new_name))

        self.remove = True
        self.debug_print = False
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


    def update_dirs_for_fli(self):
        """Renames the output directories and updates the variables for FLI data"""
        new_test_output_dir = self.test_output_dir.replace('output', 'output_fli')
        if os.path.exists(new_test_output_dir):
            self.test_output_dir = new_test_output_dir
        else:
            self.test_output_dir = shutil.move(self.test_output_dir, new_test_output_dir)
        if self.debug_print: print("new dir=", self.test_output_dir)
        self.expected_root_dir = os.path.join(self.test_output_dir, '')
        self.test_output_ddpdir = os.path.join(self.test_output_dir, 'data_lcogt_fliddp')
        self.test_output_caldir = os.path.join(self.test_output_dir, 'data_lcogt_flical')
        self.test_output_rawdir = os.path.join(self.test_output_dir, 'data_lcogt_fliraw')
        return

    def test_create_directory_structure(self):

        block_dir = 'lcogt_1m0_01_fa11_20211013'
        expected_status = {
                            'raw_data' : os.path.join(self.expected_root_dir, 'data_lcogtraw', block_dir),
                            'cal_data' : os.path.join(self.expected_root_dir, 'data_lcogtcal', block_dir),
                            'ddp_data' : os.path.join(self.expected_root_dir, 'data_lcogtddp', block_dir),
                            'root'     : self.test_output_dir
                          }

        status = create_dart_directories(self.test_output_dir, self.test_block)

        self.assertEqual(2, Block.objects.count())
        self.assertEqual(3, Frame.objects.filter(block=self.test_block, frametype=Frame.NEOX_RED_FRAMETYPE).count())
        self.assertEqual(expected_status, status)
        check_dirs = [self.expected_root_dir, ]
        check_dirs += list(expected_status.values())
        for dir in check_dirs:
            self.assertTrue(os.path.exists(dir), f'{dir} does not exist')
            self.assertTrue(os.path.isdir(dir), f'{dir} is not a directory')

    def test_create_fli_directory_structure(self):

        # Update directories and Frame filename's for FLI data
        self.update_dirs_for_fli()
        for frame in Frame.objects.filter(block=self.test_block):
            frame.filename = frame.filename.replace("tfn1m001-fa11-20211013", "cpt1m012-ef02-20220926")
            frame.save()

        block_dir = 'lcogt_1m0_12_ef02_20220926'
        expected_status = {
                            'raw_data' : os.path.join(self.expected_root_dir, 'data_lcogt_fliraw', block_dir),
                            'cal_data' : os.path.join(self.expected_root_dir, 'data_lcogt_flical', block_dir),
                            'ddp_data' : os.path.join(self.expected_root_dir, 'data_lcogt_fliddp', block_dir),
                            'root'     : self.test_output_dir
                          }

        status = create_dart_directories(self.test_output_dir, self.test_block)

        self.assertEqual(2, Block.objects.count())
        self.assertEqual(3, Frame.objects.filter(block=self.test_block, frametype=Frame.NEOX_RED_FRAMETYPE).count())
        self.assertEqual(expected_status, status)
        check_dirs = [self.expected_root_dir, ]
        check_dirs += list(expected_status.values())
        for dir in check_dirs:
            self.assertTrue(os.path.exists(dir), f'{dir} does not exist')
            self.assertTrue(os.path.isdir(dir), f'{dir} is not a directory')

    def test_create_directory_structure_no_frames(self):

        expected_block_dir = os.path.join(self.expected_root_dir, 'lcogt_1m0_01_fa11_20211013')
        expected_status = {}

        status = create_dart_directories(self.test_output_dir, self.test_block2)

        self.assertEqual(2, Block.objects.count())
        self.assertEqual(0, Frame.objects.filter(block=self.test_block2).count())

        self.assertEqual(expected_status, status)
        # for dir in [self.expected_root_dir, expected_block_dir]:
            # self.assertTrue(os.path.exists(dir), f'{dir} does not exist')
            # self.assertTrue(os.path.isdir(dir), f'{dir} is not a directory')

    def test_find_fits_files_bad_dir(self):
        expected_files = {}

        files = find_fits_files('/foo/bar')

        self.assertEqual(expected_files, files)

    def test_find_fits_files(self):
        expected_files = {self.test_input_daydir: self.test_banzai_files}

#        print("\nExpected files=\n",expected_files)
        files = find_fits_files(self.test_input_daydir)

        self.assertEqual(expected_files, files)

    def test_find_e92_fits_files_only(self):
        expected_files = {self.test_input_daydir: [x for x in self.test_banzai_files if 'e92.fits' in x]}

        files = find_fits_files(self.test_input_daydir, '\S*e92')

        self.assertEqual(expected_files, files)

    def test_create_pds_collection_ddp(self):
        # Setup
        expected_csv_file = os.path.join(self.expected_root_dir, 'data_lcogtddp', 'collection_data_lcogtddp.csv')
        expected_xml_file = os.path.join(self.expected_root_dir, 'data_lcogtddp', 'collection_data_lcogtddp.xml')
        expected_lc_file = os.path.join(self.test_ddp_daydir, 'lcogt_tfn_fa11_20211013_12345_65803didymos_photometry.tab')
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  SExtractor_flag  aprad',
        ' tfn1m001-fa11-20211012-0073-e92.fits  2459500.3339392  14.8447  0.0397  27.1845  0.0394  -12.3397    0.0052                0  10.00',
        ' tfn1m001-fa11-20211012-0074-e92.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0288  -12.3187    0.0053                3  10.00'
        ]

        paths = create_dart_directories(self.test_output_dir, self.test_block)
        for x in self.test_banzai_files:
            if 'e92' in x:
                shutil.copy(os.path.join(self.test_input_daydir, x), paths['cal_data'])

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))
        test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))
        # Copy files to input directory, renaming log
        shutil.copy(test_lc_file, self.test_input_daydir)
        new_name = os.path.join(self.test_input_daydir, 'LOG')
        shutil.copy(test_logfile, new_name)

        dart_lc_file = create_dart_lightcurve(self.test_input_dir, paths['ddp_data'], self.test_block, '*photompipe.dat')
        lc_files = [os.path.basename(dart_lc_file),]
        expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogtddp:{os.path.splitext(x)[0]}::1.0' ) for x in lc_files]

        # Tested function
        csv_filename, xml_filename = create_pds_collection(self.expected_root_dir,
            paths['ddp_data'], lc_files, 'ddp', self.schemadir, mod_time=datetime(2021, 10, 15))

        # Tests
        for filename, expected_file in zip([csv_filename, xml_filename], [expected_csv_file, expected_xml_file]):
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
            self.assertEqual(expected_file, filename)

        table = Table.read(csv_filename, format='ascii.no_header')
        for i, line in enumerate(expected_lines):
            self.assertEqual(line[0], table[i][0])
            self.assertEqual(line[1], table[i][1])

        with open(xml_filename, 'r') as xml_file:
            xml = xml_file.readlines()

        for i, expected_line in enumerate(self.expected_xml_ddp):
            if i < len(xml):
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1) + "\n-" + expected_line.lstrip() + "\n+" + xml[i].lstrip()
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)

    def test_create_pds_collection_cal(self):
        expected_csv_file = os.path.join(self.expected_root_dir, 'data_lcogtcal', 'collection_data_lcogtcal.csv')
        expected_xml_file = os.path.join(self.expected_root_dir, 'data_lcogtcal', 'collection_data_lcogtcal.xml')
        e92_files = [x for x in self.test_banzai_files if 'e92.fits' in x]
        expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogtcal:{os.path.splitext(x)[0]}::1.0' ) for x in self.test_banzai_files if 'e92.fits' in x]
        paths = create_dart_directories(self.test_output_dir, self.test_block)
        # Copy files to output dir so incorrect (non e92) files don't get picked up
        for fits_file in e92_files:
            shutil.copy(os.path.join(self.test_input_daydir, fits_file), paths['cal_data'])

        csv_filename, xml_filename = create_pds_collection(self.expected_root_dir,
            paths['cal_data'], e92_files, 'cal', self.schemadir, mod_time=datetime(2021, 10, 15))

        for filename, expected_file in zip([csv_filename, xml_filename], [expected_csv_file, expected_xml_file]):
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
            self.assertEqual(expected_file, filename)

        table = Table.read(csv_filename, format='ascii.no_header')
        for i, line in enumerate(expected_lines):
            self.assertEqual(line[0], table[i][0])
            self.assertEqual(line[1], table[i][1])

        with open(xml_filename, 'r') as xml_file:
            xml = xml_file.readlines()

        for i, expected_line in enumerate(self.expected_xml_cal):
            if i < len(xml):
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1) + "\n-" + expected_line.lstrip() + "\n+" + xml[i].lstrip()
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)

    def test_create_pds_collection_cal_not_didymos(self):
        expected_csv_file = os.path.join(self.expected_root_dir, 'data_lcogtcal', 'collection_data_lcogtcal.csv')
        expected_xml_file = os.path.join(self.expected_root_dir, 'data_lcogtcal', 'collection_data_lcogtcal.xml')
        paths = create_dart_directories(self.test_output_dir, self.test_block)
        e92_files = []
        # Modify object in FITS headers and remove <lid_reference> to didymos from XML
        for x in self.test_banzai_files:
             if 'e92.fits' in x:
                e92_files.append(x)
                # Change object name to something other (65803) Didymos
                filename = os.path.join(self.test_input_daydir, x)
                hdulist = fits.open(filename)
                hdulist[0].header['object'] = '12923   '
                filename = os.path.join(paths['cal_data'], x)
                hdulist.writeto(filename, overwrite=True, checksum=True)
        for line_num, line in enumerate(self.expected_xml_cal):
            if line.strip() == '<type>Asteroid</type>':
                start_line = line_num+1
        expected_xml_cal = self.expected_xml_cal[:start_line-2] +\
            [self.expected_xml_cal[start_line-2:start_line-1][0].replace('(65803) Didymos', '(12923) Zephyr'), ] +\
            self.expected_xml_cal[start_line-1:start_line] +\
            self.expected_xml_cal[start_line+4:]

        expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogtcal:{os.path.splitext(x)[0]}::1.0' ) for x in self.test_banzai_files if 'e92.fits' in x]

        csv_filename, xml_filename = create_pds_collection(self.expected_root_dir,
            paths['cal_data'], e92_files, 'cal', self.schemadir, mod_time=datetime(2021, 10, 15))

        for filename, expected_file in zip([csv_filename, xml_filename], [expected_csv_file, expected_xml_file]):
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
            self.assertEqual(expected_file, filename)

        table = Table.read(csv_filename, format='ascii.no_header')
        for i, line in enumerate(expected_lines):
            self.assertEqual(line[0], table[i][0])
            self.assertEqual(line[1], table[i][1])

        with open(xml_filename, 'r') as xml_file:
            xml = xml_file.readlines()

        for i, expected_line in enumerate(expected_xml_cal):
            if i < len(xml):
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1) + "\n-" + expected_line.lstrip() + "\n+" + xml[i].lstrip()
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)

    def test_create_pds_collection_raw(self):
        expected_csv_file = os.path.join(self.expected_root_dir, 'data_lcogtraw', 'collection_data_lcogtraw.csv')
        expected_xml_file = os.path.join(self.expected_root_dir, 'data_lcogtraw', 'collection_data_lcogtraw.xml')
        e00_files = [x for x in self.test_banzai_files if 'e00' in x]
        expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogtraw:{os.path.splitext(x)[0]}::1.0' ) for x in self.test_banzai_files if 'e00' in x]
        paths = create_dart_directories(self.test_output_dir, self.test_block)
        # Copy files to output dir so incorrect (non e00) files don't get picked up
        for fits_file in e00_files:
            shutil.copy(os.path.join(self.test_input_daydir, fits_file), paths['raw_data'])

        # Tested function
        csv_filename, xml_filename = create_pds_collection(self.expected_root_dir,
            paths['raw_data'], e00_files, 'raw', self.schemadir, mod_time=datetime(2021, 10, 15))

        for filename, expected_file in zip([csv_filename, xml_filename], [expected_csv_file, expected_xml_file]):
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
            self.assertEqual(expected_file, filename)

        table = Table.read(csv_filename, format='ascii.no_header')
        for i, line in enumerate(expected_lines):
            self.assertEqual(line[0], table[i][0])
            self.assertEqual(line[1], table[i][1])

        with open(xml_filename, 'r') as xml_file:
            xml = xml_file.readlines()

        for i, expected_line in enumerate(self.expected_xml_raw):
            if i < len(xml):
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1) + "\n-" + expected_line.lstrip() + "\n+" + xml[i].lstrip()
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)

    @skipIf(True, "Needs extensive archive API mocking")
    def test_find_related_frames(self):
        expected_files = {'' : [{'filename' : 'tfn1m001-fa11-20211013-0065-e00.fits', 'url' : 'https://archive-lco-global.s3.amazonaws.com/...'},
                                {'filename' : 'tfn1m001-fa11-20211013-0095-e00.fits', 'url' : 'https://archive-lco-global.s3.amazonaws.com/...'},
                                {'filename' : 'tfn1m001-fa11-20211013-0125-e00.fits', 'url' : 'https://archive-lco-global.s3.amazonaws.com/...'}
                               ]}

        related_frames = find_related_frames(self.test_block)

        self.assertEqual(expected_files, related_frames)

    def test_create_dart_lightcurve(self):
        expected_lc_file = os.path.join(self.test_ddp_daydir, 'lcogt_tfn-PP_fa11_20211013_12345_65803didymos_photometry.tab')
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad \r\n',
        ' tfn1m001-fa11-20211012-0073-e92.fits  2459500.3339392  14.8447  0.0397  27.1845  0.0394  -12.3397    0.0052       r                0  10.00 \r\n',
        ' tfn1m001-fa11-20211012-0074-e92.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0288  -12.3187    0.0053       r                3  10.00 \r\n'
        ]

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))
        test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))
        # Copy files to input directory, renaming log
        shutil.copy(test_lc_file, self.test_input_daydir)
        new_name = os.path.join(self.test_input_daydir, 'LOG')
        shutil.copy(test_logfile, new_name)

        dart_lc_file = create_dart_lightcurve(self.test_input_dir, self.test_ddp_daydir, self.test_block, '*photompipe.dat')

        self.assertEqual(expected_lc_file, dart_lc_file)
        self.assertTrue(os.path.exists(expected_lc_file))

        # Open with `newline=''` to suppress newline conversion
        with open(dart_lc_file, 'r', newline='') as table_file:
            lines = table_file.readlines()

        self.assertEqual(63, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i])

    def test_create_dart_lightcurve_default(self):
        expected_lc_file = os.path.join(self.test_ddp_daydir, 'lcogt_tfn-PP_fa11_20211013_12345_65803didymos_photometry.tab')
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad \r\n',
        ' tfn1m001-fa11-20211012-0073-e92.fits  2459500.3339392  14.8447  0.0397  27.1845  0.0394  -12.3397    0.0052       r                0  10.00 \r\n',
        ' tfn1m001-fa11-20211012-0074-e92.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0288  -12.3187    0.0053       r                3  10.00 \r\n'
        ]

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))
        test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))
        # Copy files to input directory, renaming log
        new_name = os.path.join(self.test_input_daydir, 'photometry_65803_Didymos__1996_GT.dat')
        shutil.copy(test_lc_file, new_name)
        new_name = os.path.join(self.test_input_daydir, 'LOG')
        shutil.copy(test_logfile, new_name)

        dart_lc_file = create_dart_lightcurve(self.test_input_dir, self.test_ddp_daydir, self.test_block)

        self.assertEqual(expected_lc_file, dart_lc_file)
        self.assertTrue(os.path.exists(expected_lc_file))

        with open(dart_lc_file, 'r', newline='') as table_file:
            lines = table_file.readlines()

        self.assertEqual(63, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i])

    def test_create_dart_lightcurve_default_controlphot(self):
        expected_lc_file = os.path.join(self.test_ddp_daydir, 'lcogt_tfn-PP_fa11_20211013_12345_65803didymos_photometry.tab')
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad \r\n',
        ' tfn1m001-fa11-20211012-0073-e92.fits  2459500.3339392  14.8447  0.0397  27.1845  0.0394  -12.3397    0.0052       r                0  10.00 \r\n',
        ' tfn1m001-fa11-20211012-0074-e92.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0288  -12.3187    0.0053       r                3  10.00 \r\n'
        ]

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))
        test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))
        # Copy files to input directory, renaming log and photometry file to control star
        new_name = os.path.join(self.test_input_daydir, 'photometry_65803_Didymos__1996_GT.dat')
        shutil.copy(test_lc_file, new_name)
        new_name = os.path.join(self.test_input_daydir, 'photometry_Control_Star.dat')
        shutil.copy(test_lc_file, new_name)
        # Open "control star" photometry file, make brighter/higher SNR and re-save
        table = read_photompipe_file(new_name)
        table['mag'] -= 1.5
        table['sig'] /= 3.75
        table['in_sig'] /= 3.75
        write_photompipe_file(table, new_name)
        # Copy log and rename
        new_name = os.path.join(self.test_input_daydir, 'LOG')
        shutil.copy(test_logfile, new_name)

        dart_lc_file = create_dart_lightcurve(self.test_input_dir, self.test_ddp_daydir, self.test_block)

        self.assertEqual(expected_lc_file, dart_lc_file)
        self.assertTrue(os.path.exists(expected_lc_file))

        with open(dart_lc_file, 'r', newline='') as table_file:
            lines = table_file.readlines()

        self.assertEqual(63, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i])

    def test_create_dart_lightcurve_srcmeasures(self):
        expected_lc_file = os.path.join(self.test_ddp_daydir, 'lcogt_tfn_fa11_20211013_12345_65803didymos_photometry.tab')
        expected_lc_link = os.path.join(self.test_ddp_daydir, 'LCOGT_TFN-FA11_Lister_20211013.dat')
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad \r\n',
        ' tfn1m001-fa11-20211013-0065-e92.fits  2459500.5312500  14.8447  0.0305  27.0000  0.0300  -12.1553    0.0054      ip                0  10.00 \r\n',
        ' tfn1m001-fa11-20211013-0095-e92.fits  2459500.5520833  14.8637  0.0304  27.0000  0.0300  -12.1363    0.0052      ip                3  10.00 \r\n',
        ' tfn1m001-fa11-20211013-0125-e92.fits  2459500.5937500  14.8447  0.0304  27.0000  0.0300  -12.1553    0.0051      ip                0  10.00 \r\n'
        ]

        dart_lc_file = create_dart_lightcurve(self.test_block, self.test_ddp_daydir, self.test_block, create_symlink=True)

        self.assertEqual(expected_lc_file, dart_lc_file)
        self.assertTrue(os.path.exists(expected_lc_file))
        self.assertTrue(os.path.exists(expected_lc_link))

        with open(dart_lc_file, 'r', newline='') as table_file:
            lines = table_file.readlines()

        self.assertEqual(4, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i])

    def test_create_dart_lightcurve_multiaper(self):
        expected_lc_file = os.path.join(self.test_ddp_daydir, 'lcogt_tfn_fa11_20211013_12345_65803didymos_photometry.fits')
        expected_colnames = ['filename', 'mjd', 'obs_midpoint', 'exptime', 'filter', 'obs_ra', 'obs_dec', 'flux_radius', 'fwhm']
        for index in range(0,20):
            expected_colnames.append('mag_aperture_' + str(index))
            expected_colnames.append('mag_err_aperture_' + str(index))
        expected_lines = [
        ' tfn1m001-fa11-20211012-0073-e92.fits  2459500.3339392  14.8447  0.0397  27.1845  0.0394  -12.3397    0.0052       r                0  10.00 \r\n',
        ' tfn1m001-fa11-20211012-0074-e92.fits  2459500.3345790  14.8637  0.0293  27.1824  0.0288  -12.3187    0.0053       r                3  10.00 \r\n'
        ]

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_bintable.fits'))
        # Copy files to input directory, renaming table
        new_name = os.path.join(self.test_input_daydir, '65803_data_gp.fits')
        shutil.copy(test_lc_file, new_name)

        dart_lc_file = create_dart_lightcurve(self.test_input_dir, self.test_ddp_daydir, self.test_block, match='*_data_*.fits')

        self.assertEqual(expected_lc_file, dart_lc_file)
        self.assertTrue(os.path.exists(expected_lc_file))

        table_file = Table.read(dart_lc_file, format='fits')

        self.assertEqual(22, len(table_file))
        self.assertEqual(expected_colnames, table_file.colnames)
        # for i, expected_line in enumerate(expected_lines):
            # self.assertEqual(expected_line, table_file[i])

    def test_export_block_to_pds_no_inputdir(self):
        expected_num_files = 0

        csv_files, xml_files = export_block_to_pds([], self.test_output_dir, self.test_block, self.schemadir, self.docs_root, skip_download=True)

        self.assertEqual(expected_num_files, len(csv_files))
        self.assertEqual(expected_num_files, len(xml_files))

    def test_export_block_to_pds_no_blocks(self):
        expected_num_files = 0

        csv_files, xml_files = export_block_to_pds(self.test_input_daydir, self.test_output_dir, [], self.schemadir, self.docs_root, skip_download=True)

        self.assertEqual(expected_num_files, len(csv_files))
        self.assertEqual(expected_num_files, len(xml_files))

    def test_export_block_to_pds(self):


        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))
        test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))
        # Copy files to input directory, renaming log
        new_name = os.path.join(self.test_input_daydir, 'photometry_65803_Didymos__1996_GT.dat')
        shutil.copy(test_lc_file, new_name)
        new_name = os.path.join(self.test_input_daydir, 'LOG')
        shutil.copy(test_logfile, new_name)

        # Create example bpm frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'BPM'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        test_bpm_file = os.path.join(self.test_input_daydir, 'banzai-test--bpm-full_frame.fits')
        hdulist.writeto(test_bpm_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example bias frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'BIAS'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_bias_file = os.path.join(self.test_input_daydir, 'banzai-test-bias-bin1x1.fits')
        hdulist.writeto(test_bias_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example dark frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'DARK'
        hdulist[0].header['moltype'] = 'DARK'
        hdulist[0].header['exptime'] = 300
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_dark_file = os.path.join(self.test_input_daydir, 'banzai-test-dark-bin1x1.fits')
        hdulist.writeto(test_dark_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example flat frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'SKYFLAT'
        hdulist[0].header['moltype'] = 'SKYFLAT'
        hdulist[0].header['exptime'] = 13.876
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_skyflat_file = os.path.join(self.test_input_daydir, 'banzai-test-skyflat-bin1x1-w.fits')
        hdulist.writeto(test_skyflat_file, checksum=True, overwrite=True)
        hdulist.close()

        # Mock the @cached_property on the Block.get_blockuid
        with patch('photometrics.pds_subs.Block.get_blockuid', new_callable=PropertyMock) as mock_get_blockuid:
            mock_get_blockuid.return_value='testblock'
            export_block_to_pds(self.test_input_dir, self.test_output_dir, self.test_block, self.schemadir, self.docs_root, skip_download=True)

        for collection_type, file_type in zip(['raw', 'cal', 'ddp'], ['csv', 'xml']):
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
        for collection_type, file_type in zip(['raw', 'cal', 'ddp'], ['txt', 'xml']):
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'overview.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
        for collection_type in ['raw', 'cal']:
            filepath = os.path.join(self.expected_root_dir, 'data_lcogt' + collection_type, self.test_blockdir, '') #Null string on end so 'glob' works in directory
            fits_files = glob(filepath + "*fits")
            xml_files = glob(filepath + "*xml")
            self.assertNotEqual(len(fits_files), 0)
            self.assertNotEqual(len(xml_files), 0)
            self.assertEqual(len(fits_files), len(xml_files), msg=f"Comparison failed on {collection_type:} files in {filepath:}")
            collection_filepath = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.csv')
            t = Table.read(collection_filepath, format='ascii.csv', data_start=0)
            self.assertEqual(len(fits_files)+1, len(t), msg=f"Comparison failed on {collection_type:} lines in {collection_filepath:}")
            prod_type = 'e00'
            if collection_type == 'cal':
                prod_type = 'e92.fits'
            fits_files = [x for x in self.test_banzai_files if prod_type in x]
            expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:{os.path.splitext(x)[0]}::1.0' ) for x in self.test_banzai_files if prod_type in x]
            for fits_row in t[0:len(fits_files)]:
                self.assertEqual(expected_lines[fits_row.index][0], fits_row[0])
                self.assertEqual(expected_lines[fits_row.index][1], fits_row[1])
            self.assertEqual('P', t[-1][0])
            expected_lid = f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:collection_data_lcogt{collection_type}_overview::1.0'
            self.assertEqual(expected_lid, t[-1][1])

    def test_export_fli_block_to_pds(self):

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_bintable.fits'))
        # Copy files to input directory, renaming table
        new_name = os.path.join(self.test_input_daydir, f'{self.test_block.body.current_name()}_data_gp.fits')
        shutil.copy(test_lc_file, new_name)

        # Create example bpm frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'BPM'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        test_bpm_file = os.path.join(self.test_input_daydir, 'banzai-test-bpm-full_frame.fits')
        hdulist.writeto(test_bpm_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example bias frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['instrume'] = 'ef99'
        hdulist[0].header['obstype'] = 'BIAS'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_bias_file = os.path.join(self.test_input_daydir, 'banzai-test-bias-bin1x1.fits')
        hdulist.writeto(test_bias_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example dark frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['instrume'] = 'ef99'
        hdulist[0].header['obstype'] = 'DARK'
        hdulist[0].header['moltype'] = 'DARK'
        hdulist[0].header['exptime'] = 300
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_dark_file = os.path.join(self.test_input_daydir, 'banzai-test-dark-bin1x1.fits')
        hdulist.writeto(test_dark_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example flat frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['instrume'] = 'ef99'
        hdulist[0].header['obstype'] = 'SKYFLAT'
        hdulist[0].header['moltype'] = 'SKYFLAT'
        hdulist[0].header['exptime'] = 13.876
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_skyflat_file = os.path.join(self.test_input_daydir, 'banzai-test-skyflat-bin1x1-w.fits')
        hdulist.writeto(test_skyflat_file, checksum=True, overwrite=True)
        hdulist.close()

        # Rename/update directories for FLI data
        self.update_dirs_for_fli()
        # Mock the @cached_property on the Block.get_blockuid
        with patch('photometrics.pds_subs.Block.get_blockuid', new_callable=PropertyMock) as mock_get_blockuid:
            mock_get_blockuid.return_value='testblock'
            export_block_to_pds(self.test_input_daydir, self.test_output_dir, self.test_block, self.schemadir, self.docs_root, skip_download=True, verbose=True)

        for collection_type, file_type in zip(['_fliraw', '_flical', '_fliddp'], ['csv', 'xml']):
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
        for collection_type, file_type in zip(['_fliraw', '_flical', '_fliddp'], ['txt', 'xml']):
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'overview.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
        for collection_type in ['_fliraw', '_flical', ]:
            filepath = os.path.join(self.expected_root_dir, 'data_lcogt' + collection_type, self.test_blockdir, '') #Null string on end so 'glob' works in directory
            fits_files = glob(filepath + "*fits")
            xml_files = glob(filepath + "*xml")
            self.assertNotEqual(len(fits_files), 0)
            self.assertNotEqual(len(xml_files), 0)
            self.assertEqual(len(fits_files), len(xml_files), msg=f"Comparison failed on {collection_type:} files in {filepath:}")
            collection_filepath = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.csv')
            t = Table.read(collection_filepath, format='ascii.csv', data_start=0)
            self.assertEqual(len(fits_files)+1, len(t), msg=f"Comparison failed on {collection_type:} lines in {collection_filepath:}")
            prod_type = 'e00'
            if 'cal' in collection_type:
                prod_type = 'e92.fits'
            fits_files = [x for x in self.test_banzai_files if prod_type in x]
            expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:{os.path.splitext(x)[0]}::1.0' ) for x in self.test_banzai_files if prod_type in x]
            for fits_row in t[0:len(fits_files)]:
                self.assertEqual(expected_lines[fits_row.index][0], fits_row[0])
                self.assertEqual(expected_lines[fits_row.index][1], fits_row[1])
            self.assertEqual('P', t[-1][0])
            expected_lid = f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:collection_data_lcogt{collection_type}_overview::1.0'
            self.assertEqual(expected_lid, t[-1][1])


    def test_export_block_to_pds_photpipe_data(self):

        test_externscamp_TPV_headfile = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.head')
        tpv_header = fits.Header.fromtextfile(test_externscamp_TPV_headfile)

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))
        test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))
        # Copy files to input directory, renaming log
        new_name = os.path.join(self.test_input_daydir, 'photometry_65803_Didymos__1996_GT.dat')
        shutil.copy(test_lc_file, new_name)
        new_name = os.path.join(self.test_input_daydir, 'LOG')
        shutil.copy(test_logfile, new_name)

        # Create example bpm frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'BPM'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        test_bpm_file = os.path.join(self.test_input_daydir, 'banzai-test-bpm-full_frame.fits')
        hdulist.writeto(test_bpm_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example bias frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'BIAS'
        hdulist[0].header['moltype'] = 'BIAS'
        hdulist[0].header['exptime'] = 0
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_bias_file = os.path.join(self.test_input_daydir, 'banzai-test-bias-bin1x1.fits')
        hdulist.writeto(test_bias_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example dark frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'DARK'
        hdulist[0].header['moltype'] = 'DARK'
        hdulist[0].header['exptime'] = 300
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_dark_file = os.path.join(self.test_input_daydir, 'banzai-test-dark-bin1x1.fits')
        hdulist.writeto(test_dark_file, checksum=True, overwrite=True)
        hdulist.close()

        # Create example flat frame
        hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
        hdulist[0].header['obstype'] = 'SKYFLAT'
        hdulist[0].header['moltype'] = 'SKYFLAT'
        hdulist[0].header['exptime'] = 13.876
        hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
        test_skyflat_file = os.path.join(self.test_input_daydir, 'banzai-test-skyflat-bin1x1-w.fits')
        hdulist.writeto(test_skyflat_file, checksum=True, overwrite=True)
        hdulist.close()

        block_params = {
                         'block_start' : datetime(2021, 10, 13, 0, 40),
                       }
        frame_params = {
                         'block' : self.test_block,
                         'midpoint' : block_params['block_start'] + timedelta(minutes=5)
                       }
        self.test_banzai_files = []
        for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
            frame_params['filename'] = f"tfn1m001-fa11-20211013-{frame_num:04d}-e91.fits"
            frame_params['midpoint'] += timedelta(minutes=frame_num-65)
            frame_params['frameid'] = frameid
            for extn in ['e92.bkgsub', 'e92-ldac', 'e92.rms']:
                new_name = os.path.join(self.test_input_daydir, frame_params['filename'].replace('e91', extn))
                os.remove(new_name)
            for extn in ['e92', ]:
                old_name = os.path.join(self.test_input_daydir, frame_params['filename'].replace('e91', extn))
                new_name = os.path.join(self.test_input_daydir, frame_params['filename'].replace(extn, 'e91'))
                print("old,new", os.path.basename(old_name), os.path.basename(new_name))
                with fits.open(old_name) as hdulist:
                    hdulist[0].header.insert('l1pubdat', ('l1filter', hdulist[0].header['filter'], 'Copy of FILTER for SCAMP'), after=True)
                    # Mangle header ala photpipe
                    update = False
                    insert = False
                    for key, new_value, new_comment in tpv_header.cards:
                        if key == 'CTYPE1':
                            update = True
                        elif key == 'PV1_0':
                            update = False
                            insert = True
                            prev_keyword = 'CD2_2'
                        elif key == 'FGROUPNO':
                            update = False
                            insert = True
                            prev_keyword = 'L1FILTER'
                        if update:
                            hdulist[0].header.set(key, value=str(new_value), comment=new_comment)
                        elif insert:
                             hdulist[0].header.insert(prev_keyword,(key, new_value, new_comment), after=True)
                             prev_keyword = key
                    hdulist.writeto(new_name, overwrite=True, checksum=True)
                os.remove(old_name)
                self.test_banzai_files.append(os.path.basename(new_name))
                Path(new_name.replace('e91.fits', 'e91_cal.dat')).touch()

        # Mock the @cached_property on the Block.get_blockuid
        with patch('photometrics.pds_subs.Block.get_blockuid', new_callable=PropertyMock) as mock_get_blockuid:
            mock_get_blockuid.return_value='testblock'
            export_block_to_pds(self.test_input_daydir, self.test_output_dir, self.test_block, self.schemadir, self.docs_root, skip_download=True)

        for collection_type, file_type in zip(['raw', 'cal', 'ddp'], ['csv', 'xml']):
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
        for collection_type, file_type in zip(['raw', 'cal', 'ddp'], ['txt', 'xml']):
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'overview.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
        for collection_type in ['raw', 'cal']:
            filepath = os.path.join(self.expected_root_dir, 'data_lcogt' + collection_type, self.test_blockdir, '') #Null string on end so 'glob' works in directory
            fits_files = glob(filepath + "*fits")
            xml_files = glob(filepath + "*xml")
            self.assertNotEqual(len(fits_files), 0)
            self.assertNotEqual(len(xml_files), 0)
            self.assertEqual(len(fits_files), len(xml_files), msg=f"Comparison failed on {collection_type:} files in {filepath:}")
            collection_filepath = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.csv')
            t = Table.read(collection_filepath, format='ascii.csv', data_start=0)
            self.assertEqual(len(fits_files)+1, len(t), msg=f"Comparison failed on {collection_type:} lines in {collection_filepath:}")
            prod_type = 'e00'
            if collection_type == 'cal':
                prod_type = 'e92.fits'
            fits_files = [x for x in self.test_banzai_files if prod_type in x]
            expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:{os.path.splitext(x)[0]}::1.0' ) for x in self.test_banzai_files if prod_type in x]
            for fits_row in t[0:len(fits_files)]:
                self.assertEqual(expected_lines[fits_row.index][0], fits_row[0])
                self.assertEqual(expected_lines[fits_row.index][1], fits_row[1])
            self.assertEqual('P', t[-1][0])
            expected_lid = f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:collection_data_lcogt{collection_type}_overview::1.0'
            self.assertEqual(expected_lid, t[-1][1])

    def test_export_multiple_blocks_to_pds(self):
        verbose = False
        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe.dat'))
        test_logfile = os.path.abspath(os.path.join('photometrics', 'tests', 'example_photompipe_log'))
        # Make 2nd day of data
        self.test_input_daydir2 = os.path.join(self.test_input_dir, '20211015')
        os.makedirs(self.test_input_daydir2, exist_ok=True)

        # Update 2nd Block to reflect 2nd night of obs.
        self.test_blockdir2 = 'lcogt_1m0_12_fa16_20211015'

        self.test_block2.num_observed = 1
        self.test_block2.request_number = '12420'
        self.test_block2.block_start += timedelta(days=2)
        self.test_block2.block_end += timedelta(days=1, seconds=10*3600)
        self.test_block2.save()
        frame_params = {
                         'sitecode' : 'K91',
                         'instrument' : 'fa16',
                         'filter' : 'ip',
                         'block' : self.test_block2,
                         'frametype' : Frame.BANZAI_RED_FRAMETYPE,
                         'zeropoint' : 26.8,
                         'zeropoint_err' : 0.04,
                         'midpoint' : self.test_block2.block_start + timedelta(minutes=5)
                       }

        for frame_num, frameid in zip(range(45,106,30),[45244042, 45244594, 45245062]):
            frame_params['filename'] = f"cpt1m012-fa16-20211015-{frame_num:04d}-e91.fits"
            frame_params['midpoint'] += timedelta(minutes=frame_num-45)
            frame_params['frameid'] = frameid
            frame, created = Frame.objects.get_or_create(**frame_params)
            for extn in ['e00', 'e92']:
                new_name = os.path.join(self.test_input_daydir2, frame_params['filename'].replace('e91', extn))
                filename = shutil.copy(self.test_file_path, new_name)
                # Change object name to 65803
                hdulist = fits.open(filename)
                hdulist[0].header['object'] = '65803   '
                hdulist[0].header['instrume'] = 'fa15'
                hdulist[0].header['telescop'] = '1m0-12'
                half_exp = timedelta(seconds=hdulist[0].header['exptime'] / 2.0)
                date_obs = frame_params['midpoint'] - half_exp
                hdulist[0].header['date-obs'] = date_obs.strftime("%Y-%m-%dT%H:%M:%S")
                utstop = frame_params['midpoint'] + half_exp + timedelta(seconds=8.77)
                hdulist[0].header['utstop'] = utstop.strftime("%H:%M:%S.%f")[0:12]
                hdulist.writeto(filename, overwrite=True, checksum=True)
                self.test_banzai_files.append(os.path.basename(filename))

        input_daydirs_list = [self.test_input_daydir, self.test_input_daydir2]
        for test_input_daydir in input_daydirs_list:
            # Copy files to input directories, renaming log
            new_name = os.path.join(test_input_daydir, 'photometry_65803_Didymos__1996_GT.dat')
            shutil.copy(test_lc_file, new_name)
            new_name = os.path.join(test_input_daydir, 'LOG')
            shutil.copy(test_logfile, new_name)

            daydir = os.path.basename(test_input_daydir)
            # Create example bpm frame
            hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
            hdulist[0].header['obstype'] = 'BPM'
            hdulist[0].header['moltype'] = 'BIAS'
            hdulist[0].header['exptime'] = 0
            test_bpm_file = os.path.join(test_input_daydir, f'banzai-test-bpm-{daydir}-full_frame.fits')
            hdulist.writeto(test_bpm_file, checksum=True, overwrite=True)
            hdulist.close()
            self.test_banzai_files.append(os.path.basename(test_bpm_file))

            # Create example bias frame
            hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
            hdulist[0].header['obstype'] = 'BIAS'
            hdulist[0].header['moltype'] = 'BIAS'
            hdulist[0].header['exptime'] = 0
            hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
            test_bias_file = os.path.join(test_input_daydir, f'banzai-test-bias-{daydir}-bin1x1.fits')
            hdulist.writeto(test_bias_file, checksum=True, overwrite=True)
            hdulist.close()
            self.test_banzai_files.append(os.path.basename(test_bias_file))

            # Create example dark frame
            hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
            hdulist[0].header['obstype'] = 'DARK'
            hdulist[0].header['moltype'] = 'DARK'
            hdulist[0].header['exptime'] = 300
            hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
            test_dark_file = os.path.join(test_input_daydir, f'banzai-test-{daydir}-dark-bin1x1.fits')
            hdulist.writeto(test_dark_file, checksum=True, overwrite=True)
            hdulist.close()
            self.test_banzai_files.append(os.path.basename(test_dark_file))

            # Create example flat frame
            hdulist = fits.open(os.path.join(self.test_input_daydir, self.test_banzai_files[0]))
            hdulist[0].header['obstype'] = 'SKYFLAT'
            hdulist[0].header['moltype'] = 'SKYFLAT'
            hdulist[0].header['exptime'] = 13.876
            hdulist[0].header.insert('l1pubdat', ('ismaster', True, 'Is this a master calibration frame'), after=True)
            test_skyflat_file = os.path.join(test_input_daydir, f'banzai-test-skyflat-{daydir}-bin1x1-w.fits')
            hdulist.writeto(test_skyflat_file, checksum=True, overwrite=True)
            hdulist.close()
            self.test_banzai_files.append(os.path.basename(test_skyflat_file))

        # Mock the @cached_property on the Block.get_blockuid
        with patch('photometrics.pds_subs.Block.get_blockuid', new_callable=PropertyMock) as mock_get_blockuid:
            mock_get_blockuid.return_value='testblock'
            export_block_to_pds(input_daydirs_list, self.test_output_dir, [self.test_block, self.test_block2], self.schemadir, self.docs_root, skip_download=True, verbose=verbose)

        for collection_type, file_type in [(a,b) for a in ['raw', 'cal', 'ddp'] for b in ['csv', 'xml']]:
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.{file_type}')
            self.assertTrue(os.path.exists(expected_file), msg=f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), msg=f'{expected_file} is not a file')
        for collection_type, file_type in [(a,b) for a in ['raw', 'cal', 'ddp'] for b in ['txt', 'xml']]:
            expected_file = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'overview.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
        for collection_type in ['raw', 'cal',]:
            if verbose: print(f" {collection_type}\n=====")
            all_fits_files = []
            for block_dir in [self.test_blockdir, self.test_blockdir2]:
                filepath = os.path.join(self.expected_root_dir, 'data_lcogt' + collection_type, block_dir, '') #Null string on end so 'glob' works in directory
                fits_files = sorted(glob(filepath + "tfn*fits")) +  sorted(glob(filepath + "cpt*fits")) + sorted(glob(filepath + "banzai*fits"))
                all_fits_files += fits_files
                xml_files = glob(filepath + "*xml")
                self.assertEqual(len(fits_files), len(xml_files), msg=f"Comparison failed on {collection_type:} files in {filepath:}")
            collection_filepath = os.path.join(self.expected_root_dir, f'data_lcogt{collection_type}', f'collection_data_lcogt{collection_type}.csv')
            t = Table.read(collection_filepath, format='ascii.csv', data_start=0, names=('P/S', 'lidvid'))
            self.assertEqual(len(all_fits_files), len(t)-1, msg=f"Failed on {collection_type}") # -1 due to extra overview file at the end
            prod_type = 'e00'
            fits_files = [x for x in self.test_banzai_files if prod_type in x]
            if collection_type == 'cal':
                fits_files = [os.path.basename(x) for x in all_fits_files] #[x for x in self.test_banzai_files if prod_type not in x and 'e91' not in x]

            expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:{os.path.splitext(x)[0]}::1.0' ) for x in fits_files]
            if verbose: print("expected_lines:")
            if verbose: print("\n".join([f"  {x[0]} {x[1]}" for x in expected_lines]))
            if verbose: print
            if verbose: print(t[0:len(fits_files)])
            for fits_row in t[0:len(fits_files)]:
                self.assertEqual(expected_lines[fits_row.index][0], fits_row[0])
                self.assertEqual(expected_lines[fits_row.index][1], fits_row[1])
            self.assertEqual('P', t[-1][0])
            expected_lid = f'urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:collection_data_lcogt{collection_type}_overview::1.0'
            self.assertEqual(expected_lid, t[-1][1])


class TestTransferFiles(SimpleTestCase):
    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.test_input_dir = os.path.join(self.test_dir, 'input')
        self.test_input_daydir = os.path.join(self.test_dir, 'input', '20211013')
        os.makedirs(self.test_input_daydir, exist_ok=True)

        # Example input FITS files and header mods
        self.framedir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'banzai_test_frame.fits'
        self.test_file_path = os.path.join(self.framedir, self.test_file)
        test_externscamp_TPV_headfile = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.head')
        test_externcat_TPV_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.xml')
        tpv_header = fits.Header.fromtextfile(test_externscamp_TPV_headfile)

        self.test_output_dir = os.path.join(self.test_dir, 'output')
        os.makedirs(self.test_output_dir, exist_ok=True)
        self.expected_root_dir = os.path.join(self.test_output_dir, '')
        self.test_ddp_daydir = os.path.join(self.expected_root_dir, 'data_lcogtddp')
        self.test_blockdir = 'lcogt_1m0_01_fa11_20211013'
        self.test_daydir = os.path.join(self.test_ddp_daydir, self.test_blockdir)
        self.test_output_rawdir = os.path.join(self.expected_root_dir, 'data_lcogtraw')
        self.test_output_rawblockdir = os.path.join(self.test_output_rawdir, self.test_blockdir)
        os.makedirs(self.test_output_rawblockdir, exist_ok=True)
        self.test_output_caldir = os.path.join(self.expected_root_dir, 'data_lcogtcal')
        self.test_output_calblockdir = os.path.join(self.test_output_caldir, self.test_blockdir)
        os.makedirs(self.test_output_calblockdir, exist_ok=True)

        frame_params = {
                         'sitecode' : 'Z24',
                         'instrument' : 'fa11',
                         'filter' : 'ip',
                         'block' : 4242,
                         'frametype' : Frame.BANZAI_RED_FRAMETYPE,
                         'zeropoint' : 27.0,
                         'zeropoint_err' : 0.03,
                         'midpoint' : datetime(2021, 10, 13, 0, 40) + timedelta(minutes=5)
                       }

        self.test_banzai_files = []
        for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
            frame_params['filename'] = f"tfn1m001-fa11-20211013-{frame_num:04d}-e91.fits"
            frame_params['midpoint'] += timedelta(minutes=frame_num-65)
            frame_params['frameid'] = frameid
            for extn in ['e00', 'e91', 'e92']:
                new_name = os.path.join(self.test_input_daydir, frame_params['filename'].replace('e91', extn))
                filename = shutil.copy(self.test_file_path, new_name)
                # Change object name to 65803
                with fits.open(filename) as hdulist:
                    hdulist[0].header['telescop'] = '1m0-01'
                    hdulist[0].header['object'] = '65803   '
                    half_exp = timedelta(seconds=hdulist[0].header['exptime'] / 2.0)
                    date_obs = frame_params['midpoint'] - half_exp
                    hdulist[0].header['date-obs'] = date_obs.strftime("%Y-%m-%dT%H:%M:%S")
                    utstop = frame_params['midpoint'] + half_exp + timedelta(seconds=8.77)
                    hdulist[0].header['utstop'] = utstop.strftime("%H:%M:%S.%f")[0:12]
                    hdulist[0].header.insert('l1pubdat', ('l1filter', hdulist[0].header['filter'], 'Copy of FILTER for SCAMP'), after=True)
                    hdulist.writeto(filename, overwrite=True, checksum=True)
#                    hdulist.close()
                self.test_banzai_files.append(os.path.basename(filename))
                if extn == 'e91':
                    Path(new_name.replace('e91.fits', 'e91_cal.dat')).touch()

        self.remove = True
        self.debug_print = False
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

    def test_e00_files(self):
        verbose = False
        expected_files = [x for x in self.test_banzai_files if 'e00' in x]

        raw_files = find_fits_files(self.test_input_daydir, '\S*e00')
        print("Transferring raw frames")
        for root, files in raw_files.items():
            raw_sent_files, copied_files = transfer_files(root, files, self.test_output_rawblockdir, dbg=verbose)

        self.assertEqual(expected_files, raw_sent_files)
        self.assertEqual(expected_files, copied_files)
        for raw_file in raw_sent_files:
            file_path = os.path.join(self.test_output_rawblockdir, raw_file)
            self.assertTrue(os.path.exists(file_path))

    def test_e00_files_already_present(self):
        verbose = False
        expected_files = [x for x in self.test_banzai_files if 'e00' in x]
        # Copy files to output raw directory
        for raw_file in expected_files:
            print(raw_file)
            file_path = os.path.join(self.test_input_daydir, raw_file)
            new_file_path = os.path.join(self.test_output_rawblockdir, raw_file)
            filename = shutil.copy(file_path, new_file_path)
        # Check copy worked
        for raw_file in expected_files:
            file_path = os.path.join(self.test_output_rawblockdir, raw_file)
            self.assertTrue(os.path.exists(file_path))

        raw_files = find_fits_files(self.test_input_daydir, '\S*e00')
        if verbose: print("Transferring raw frames")
        for root, files in raw_files.items():
            raw_sent_files, copied_files = transfer_files(root, files, self.test_output_rawblockdir, dbg=verbose)

        self.assertEqual(expected_files, raw_sent_files)
        self.assertEqual(0, len(copied_files))
        for raw_file in raw_sent_files:
            file_path = os.path.join(self.test_output_rawblockdir, raw_file)
            self.assertTrue(os.path.exists(file_path))

    def test_e91photpipe_files(self):
        verbose = False
        expected_files = [x for x in self.test_banzai_files if 'e91' in x]

        cal_files = find_fits_files(self.test_input_daydir, '\S*e91')
        print("Transferring calibrated frames")
        for root, files in cal_files.items():
            cal_sent_files, copied_files= transfer_files(root, files, self.test_output_calblockdir, dbg=verbose)

        self.assertEqual(expected_files, cal_sent_files)
        self.assertEqual(expected_files, copied_files)
        for cal_file in cal_sent_files:
            file_path = os.path.join(self.test_output_calblockdir, cal_file)
            self.assertTrue(os.path.exists(file_path))

    def test_e91photpipe_files_norecopy(self):
        verbose = False
        expected_e91_files = [x for x in self.test_banzai_files if 'e91' in x]
        expected_files = [x.replace('e91', 'e92') for x in self.test_banzai_files if 'e91' in x]
        expected_num_files = 3

        cal_files = find_fits_files(self.test_input_daydir, '\S*e91')
        if verbose: print("Transferring PP calibrated frames")
        for root, files in cal_files.items():
            cal_sent_files, copied_files = transfer_files(root, files, self.test_output_calblockdir, dbg=verbose)
        self.assertEqual(expected_e91_files, cal_sent_files)
        self.assertEqual(expected_e91_files, copied_files)
        for trans_file in cal_sent_files:
            e91_filepath = os.path.join(self.test_output_calblockdir, trans_file)
            os.rename(e91_filepath, e91_filepath.replace('e91', 'e92'))
        files = glob(self.test_output_calblockdir + '/*.fits')
        if verbose: print("\nContents of output:\n",files)
        self.assertEqual(expected_num_files, len(files))
        # Retransfer (in theory nothing)
        for root, files in cal_files.items():
            new_cal_sent_files, new_copied_files = transfer_files(root, files, self.test_output_calblockdir, dbg=verbose)
            cal_sent_files += new_cal_sent_files
            copied_files += new_copied_files
        files = glob(self.test_output_calblockdir + '/*.fits')
        if verbose: print("\nContents of output v2:\n",files)
        self.assertEqual(expected_num_files*2, len(cal_sent_files))
        self.assertEqual(expected_num_files, len(copied_files))
        self.assertEqual(0, len(new_copied_files))
        self.assertEqual(expected_num_files, len(files))
        self.assertEqual(expected_e91_files, new_cal_sent_files)
        for cal_file in new_cal_sent_files:
            file_path = os.path.join(self.test_output_calblockdir, cal_file.replace('e91', 'e92'))
            self.assertTrue(os.path.exists(file_path))

    def test_e92_files(self):
        verbose = False
        expected_files = [x for x in self.test_banzai_files if 'e92.fits' in x]

        cal_files = find_fits_files(self.test_input_daydir, '\S*e92')
        print("Transferring NEOX calibrated frames")
        for root, files in cal_files.items():
            cal_sent_files, copied_files = transfer_files(root, files, self.test_output_calblockdir, dbg=verbose)

        self.assertEqual(expected_files, cal_sent_files)
        self.assertEqual(expected_files, copied_files)
        for cal_file in cal_sent_files:
            file_path = os.path.join(self.test_output_calblockdir, cal_file)
            self.assertTrue(os.path.exists(file_path))

    def test_e92_files_norecopy(self):
        verbose = False
        expected_files = [x.replace('e91', 'e92') for x in self.test_banzai_files if 'e91' in x]
        expected_num_files = 3

        cal_files = find_fits_files(self.test_input_daydir, '\S*e92')
        print("Transferring NEOX calibrated frames")
        for root, files in cal_files.items():
            cal_sent_files, copied_files = transfer_files(root, files, self.test_output_calblockdir, dbg=verbose)
        self.assertEqual(expected_files, cal_sent_files)
        self.assertEqual(expected_files, copied_files)
        for trans_file in cal_sent_files:
            e91_filepath = os.path.join(self.test_output_calblockdir, trans_file)
            os.rename(e91_filepath, e91_filepath.replace('e91', 'e92'))
        files = glob(self.test_output_calblockdir + '/*.fits')
        self.assertEqual(expected_num_files, len(files))
        # Retransfer (in theory nothing)
        for root, files in cal_files.items():
            new_cal_sent_files, new_copied_files = transfer_files(root, files, self.test_output_calblockdir, dbg=verbose)
            cal_sent_files += new_cal_sent_files
            copied_files += new_copied_files
        self.assertEqual(expected_num_files*2, len(cal_sent_files))
        self.assertEqual(expected_num_files, len(copied_files))
        self.assertEqual(0, len(new_copied_files))
        files = glob(self.test_output_calblockdir + '/*.fits')
        self.assertEqual(expected_num_files, len(files))
        for cal_file in cal_sent_files:
            file_path = os.path.join(self.test_output_calblockdir, cal_file)
            self.assertTrue(os.path.exists(file_path))


class TestTransferReformat(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.docs_root = os.path.abspath(os.path.join('photometrics', 'configs', 'PDS_docs'))
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_cal.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_cal = xml_file.readlines()
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_raw.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_raw = xml_file.readlines()
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_ddp.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_ddp = xml_file.readlines()

        self.framedir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'banzai_test_frame.fits'
        self.test_file_path = os.path.join(self.framedir, self.test_file)
        test_externscamp_TPV_headfile = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.head')
        test_externcat_TPV_xml = os.path.join('photometrics', 'tests', 'example_externcat_scamp_tpv.xml')
        tpv_header = fits.Header.fromtextfile(test_externscamp_TPV_headfile)

#        self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.test_input_dir = os.path.join(self.test_dir, 'input')
        self.test_input_daydir = os.path.join(self.test_dir, 'input', '20211013')
        os.makedirs(self.test_input_daydir, exist_ok=True)

        self.test_output_dir = os.path.join(self.test_dir, 'output')
        os.makedirs(self.test_output_dir, exist_ok=True)
        self.expected_root_dir = os.path.join(self.test_output_dir, '')
        self.test_ddp_daydir = os.path.join(self.expected_root_dir, 'data_lcogtddp')
        self.test_blockdir = 'lcogt_1m0_01_fa11_20211013'
        self.test_daydir = os.path.join(self.test_ddp_daydir, self.test_blockdir)
        self.test_output_caldir = os.path.join(self.expected_root_dir, 'data_lcogtcal')
        self.test_output_calblockdir = os.path.join(self.test_output_caldir, self.test_blockdir)

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
                         'block_start' : datetime(2021, 10, 13, 0, 40),
                         'block_end' : datetime(2021, 10, 14, 0, 40),
                         'obstype' : Block.OPT_IMAGING,
                         'num_observed' : 1
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)
        # Second block with no frames attached
        block_params['num_observed'] = 0
        self.test_block2, created = Block.objects.get_or_create(**block_params)

        frame_params = {
                         'sitecode' : 'Z24',
                         'instrument' : 'fa11',
                         'filter' : 'ip',
                         'block' : self.test_block,
                         'frametype' : Frame.BANZAI_RED_FRAMETYPE,
                         'zeropoint' : 27.0,
                         'zeropoint_err' : 0.03,
                         'midpoint' : block_params['block_start'] + timedelta(minutes=5)
                       }

        self.test_banzai_files = []
        for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
            frame_params['filename'] = f"tfn1m001-fa11-20211013-{frame_num:04d}-e91.fits"
            frame_params['midpoint'] += timedelta(minutes=frame_num-65)
            frame_params['frameid'] = frameid
            frame, created = Frame.objects.get_or_create(**frame_params)
            for extn in ['e00', 'e91']:
                new_name = os.path.join(self.test_input_daydir, frame_params['filename'].replace('e91', extn))
                filename = shutil.copy(self.test_file_path, new_name)
                # Change object name to 65803
                with fits.open(filename) as hdulist:
                    hdulist[0].header['telescop'] = '1m0-01'
                    hdulist[0].header['instrume'] = 'fa15'
                    hdulist[0].header['object'] = '65803   '
                    half_exp = timedelta(seconds=hdulist[0].header['exptime'] / 2.0)
                    date_obs = frame_params['midpoint'] - half_exp
                    hdulist[0].header['date-obs'] = date_obs.strftime("%Y-%m-%dT%H:%M:%S")
                    utstop = frame_params['midpoint'] + half_exp + timedelta(seconds=8.77)
                    hdulist[0].header['utstop'] = utstop.strftime("%H:%M:%S.%f")[0:12]
                    hdulist[0].header.insert('l1pubdat', ('l1filter', hdulist[0].header['filter'], 'Copy of FILTER for SCAMP'), after=True)
                    # Mangle header ala photpipe
                    update = False
                    insert = False
                    for key, new_value, new_comment in tpv_header.cards:
                        if key == 'CTYPE1':
                            update = True
                        elif key == 'PV1_0':
                            update = False
                            insert = True
                            prev_keyword = 'CD2_2'
                        elif key == 'FGROUPNO':
                            update = False
                            insert = True
                            prev_keyword = 'L1FILTER'
                        if update:
                            hdulist[0].header.set(key, value=str(new_value), comment=new_comment)
                        elif insert:
                             hdulist[0].header.insert(prev_keyword,(key, new_value, new_comment), after=True)
                             prev_keyword = key
                    hdulist.writeto(filename, overwrite=True, checksum=True)
                self.test_banzai_files.append(os.path.basename(filename))
                if extn == 'e91':
                    Path(new_name.replace('e91.fits', 'e91_cal.dat')).touch()

        self.remove = True
        self.debug_print = False
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

    def transfer_cal_files(self, input_dirs, blocks, verbose=True):

        schema_root = self.schemadir
        csv_files = []
        xml_files = []

        if type(blocks) != list and hasattr(blocks, "model") is False:
            blocks = [blocks, ]
        if type(input_dirs) != list:
            input_dirs = [input_dirs, ]

        raw_sent_files = []
        cal_sent_files = []
        lc_files = []
        for input_dir, block in zip(input_dirs, blocks):
            paths = create_dart_directories(self.test_output_dir, block)
            # transfer cal data
            # Set pattern to '<any # of chars>e92 to avoid picking up e92-ldac files
            cal_files = find_fits_files(input_dir, '\S*e92')
            pp_phot = False
            if len(cal_files) == 0:
                if verbose: print("Looking for cals. input_dir=",input_dir)
                if verbose: print("No cal files found, trying for e91 photpipe files")
                cal_dat_files = glob(input_dir+'/*e91_cal.dat')
                if len(cal_dat_files) > 0:
                    pp_phot = True
                    cal_files = find_fits_files(input_dir, '\S*e91')
                else:
                    return [], []
            if verbose: print("Transferring calibrated frames")
            print(cal_files)
            for root, files in cal_files.items():
                sent_files, copied_files = transfer_files(root, files, paths['cal_data'], dbg=verbose)
                cal_sent_files += sent_files
            if pp_phot is True:
                # Use cal_files not cal_sent_files as we only files from this Block not all of them
                for directory, e91_files in cal_files.items():
                    for e91_file in e91_files:
                        old_filename = os.path.join(paths['cal_data'], e91_file)
                        new_filename = old_filename.replace('e91', 'e92')
                        if os.path.exists(new_filename) is False:
                            if verbose: print(f"Changing {e91_file} -> {os.path.basename(new_filename)}")
                            hdulist = fits.open(os.path.join(paths['cal_data'], e91_file))
                            data = hdulist[0].data
                            new_header = reformat_header(hdulist[0].header)
                            new_header.remove("BSCALE", ignore_missing=True)
                            new_header.insert("NAXIS2", ("BSCALE", 1.0), after=True)
                            new_header.remove("BZERO", ignore_missing=True)
                            new_header.insert("BSCALE", ("BZERO", 0.0), after=True)
                            new_hdulist = fits.PrimaryHDU(data, new_header)
                            new_hdulist._bscale = 1.0
                            new_hdulist._bzero = 0.0

                            new_hdulist.writeto(new_filename, checksum=True, overwrite=True)
                            hdulist.close()
                        else:
                            if verbose: print(f"{os.path.basename(new_filename)} already exists")
                        if os.path.isdir(old_filename) is False:
                            if os.path.exists(old_filename):
                                os.remove(old_filename)
                                if verbose: print("Removed", old_filename)
                            # Replace old e91 file name with new one
                            try:
                                index = cal_sent_files.index(e91_file)
                                cal_sent_files[index] = os.path.basename(new_filename)
                            except ValueError:
                                if verbose: (f"{old_filename} not found in list of sent cal frames")
        # Create PDS labels for cal data
        if verbose: print("Creating cal PDS labels")
        xml_labels = create_pds_labels(paths['cal_data'], schema_root, match='.*[bpm|bias|dark|flat|e92]*')

        # create PDS products for cal data
        if verbose: print("Creating cal PDS collection")
        path_to_all_cals = os.path.join(os.path.dirname(paths['cal_data']), '')
        cal_csv_filename, cal_xml_filename = create_pds_collection(paths['root'], path_to_all_cals, cal_sent_files, 'cal', schema_root, mod_time=datetime(2021,10,15))
        # Convert csv file to CRLF endings required by PDS
        status = convert_file_to_crlf(cal_csv_filename)
        csv_files.append(cal_csv_filename)
        xml_files.append(cal_xml_filename)

        return xml_labels, cal_sent_files

    def test_single_block(self):
        expected_num_xml = 3
        expected_cal_files = [
                                'tfn1m001-fa11-20211013-0065-e92.fits',
                                'tfn1m001-fa11-20211013-0095-e92.fits',
                                'tfn1m001-fa11-20211013-0125-e92.fits',
                             ]
        expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:data_lcogtcal:{os.path.splitext(x)[0]}::1.0' ) for x in self.test_banzai_files if 'e92' in x]
        expected_csv_filename = os.path.join(self.test_output_caldir, 'collection_data_lcogtcal.csv')
        expected_xml_filename = os.path.join(self.test_output_caldir, 'collection_data_lcogtcal.xml')

        xml_files, sent_cal_files = self.transfer_cal_files(self.test_input_daydir, self.test_block)

        self.assertEqual(expected_num_xml, len(xml_files))
        for e92_file in expected_cal_files:
            self.assertTrue(os.path.exists(os.path.join(self.test_output_calblockdir, e92_file)))
            self.assertFalse(os.path.exists(os.path.join(self.test_output_calblockdir, e92_file.replace('e92', 'e91'))))
        self.assertEqual(len(expected_cal_files), len(sent_cal_files))
        self.assertEqual(expected_cal_files, sent_cal_files)

        table = Table.read(expected_csv_filename, format='ascii.no_header')
        for i, line in enumerate(expected_lines):
            self.assertEqual(line[0], table[i][0])
            self.assertEqual(line[1], table[i][1])

        with open(expected_xml_filename, 'r') as xml_file:
            xml = xml_file.readlines()

        for i, expected_line in enumerate(self.expected_xml_cal):
            if i < len(xml):
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1) + "\n-" + expected_line.lstrip() + "\n+" + xml[i].lstrip()
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)


class TestCopyDocs(SimpleTestCase):

    def setUp(self):
        self.docs_dir = os.path.abspath(os.path.join('photometrics', 'configs', 'PDS_docs', ''))

#        self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.test_output_dir = os.path.join(self.test_dir, 'output')
        self.test_output_rawdir = os.path.join(self.test_output_dir, 'data_lcogtraw')
        os.makedirs(self.test_output_rawdir, exist_ok=True)
        self.test_output_caldir = os.path.join(self.test_output_dir, 'data_lcogtcal')
        os.makedirs(self.test_output_caldir, exist_ok=True)
        self.test_output_ddpdir = os.path.join(self.test_output_dir, 'data_lcogtddp')
        os.makedirs(self.test_output_ddpdir, exist_ok=True)

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

    def update_dirs_for_fli(self):
        """Renames the output directories and updates the variables for FLI data"""
        new_test_output_dir = self.test_output_dir.replace('output', 'output_fli')
        if os.path.exists(new_test_output_dir):
            self.test_output_dir = new_test_output_dir
        else:
            self.test_output_dir = shutil.move(self.test_output_dir, new_test_output_dir)
        if self.debug_print: print("new dir=", self.test_output_dir)

        new_output_dir = os.path.join(self.test_output_dir, 'data_lcogt_fliddp')
        self.test_output_ddpdir = shutil.move(self.test_output_ddpdir.replace('output', 'output_fli'), new_output_dir)

        new_output_dir = os.path.join(self.test_output_dir, 'data_lcogt_flical')
        self.test_output_caldir = shutil.move(self.test_output_caldir.replace('output', 'output_fli'), new_output_dir)

        new_output_dir = os.path.join(self.test_output_dir, 'data_lcogt_fliraw')
        self.test_output_rawdir = shutil.move(self.test_output_rawdir.replace('output', 'output_fli'), new_output_dir)

        return

    def test_raw(self):

        expected_xml_labels = ['collection_data_lcogtraw_overview', ]

        xml_labels = copy_docs(self.test_output_dir, 'raw', self.docs_dir, verbose=True)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for extn in ['txt', 'xml']:
            self.assertListEqual(
                list(io.open(os.path.join(self.docs_dir, f'collection_data_lcogtraw_overview.{extn}'))),
                list(io.open(os.path.join(self.test_output_rawdir, f'overview.{extn}')))
                )

    def test_raw_fli(self):

        self.update_dirs_for_fli()
        expected_xml_labels = ['collection_data_lcogt_fliraw_overview',  ]

        xml_labels = copy_docs(self.test_output_dir, 'raw', self.docs_dir, verbose=False)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for extn in ['txt', 'xml']:
            self.assertListEqual(
                list(io.open(os.path.join(self.docs_dir, f'collection_data_lcogt_fliraw_overview.{extn}'))),
                list(io.open(os.path.join(self.test_output_rawdir, f'overview.{extn}')))
                )

    def test_cal(self):

        expected_xml_labels = ['collection_data_lcogtcal_overview', ]

        xml_labels = copy_docs(self.test_output_dir, 'cal', self.docs_dir, verbose=False)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for extn in ['txt', 'xml']:
            self.assertListEqual(
                list(io.open(os.path.join(self.docs_dir, f'collection_data_lcogtcal_overview.{extn}'))),
                list(io.open(os.path.join(self.test_output_caldir, f'overview.{extn}')))
                )

    def test_cal_fli(self):

        self.update_dirs_for_fli()
        expected_xml_labels = ['collection_data_lcogt_flical_overview',  ]

        xml_labels = copy_docs(self.test_output_dir, 'cal', self.docs_dir, verbose=False)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for extn in ['txt', 'xml']:
            self.assertListEqual(
                list(io.open(os.path.join(self.docs_dir, f'collection_data_lcogt_flical_overview.{extn}'))),
                list(io.open(os.path.join(self.test_output_caldir, f'overview.{extn}')))
                )

    def test_ddp(self):

        expected_xml_labels = ['collection_data_lcogtddp_overview', ]

        xml_labels = copy_docs(self.test_output_dir, 'ddp', self.docs_dir, verbose=False)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for extn in ['txt', 'xml']:
            self.assertListEqual(
                list(io.open(os.path.join(self.docs_dir, f'collection_data_lcogtddp_overview.{extn}'))),
                list(io.open(os.path.join(self.test_output_ddpdir, f'overview.{extn}')))
                )

    def test_ddp_fli(self):

        self.update_dirs_for_fli()
        expected_xml_labels = ['collection_data_lcogt_fliddp_overview',  ]

        xml_labels = copy_docs(self.test_output_dir, 'ddp', self.docs_dir, verbose=False)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)
        for extn in ['txt', 'xml']:
            self.assertListEqual(
                list(io.open(os.path.join(self.docs_dir, f'collection_data_lcogt_fliddp_overview.{extn}'))),
                list(io.open(os.path.join(self.test_output_ddpdir, f'overview.{extn}')))
                )
