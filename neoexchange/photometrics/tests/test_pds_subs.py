import os
import shutil
import tempfile
from glob import glob
from lxml import etree
from lxml import objectify
from datetime import datetime
from collections import OrderedDict
from mock import patch, MagicMock, PropertyMock

from astropy.io import fits

from core.models import Body, Designations, CatalogSources, SourceMeasurement,\
    Proposal, SuperBlock, Block, Frame
from photometrics.pds_subs import *
from photometrics.lightcurve_subs import read_photompipe_file, write_photompipe_file

from unittest import skipIf
from django.test import SimpleTestCase, TestCase

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


class TestCreateObsArea(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        test_xml_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label.xml'))
        with open(test_xml_cat, 'r') as xml_file:
            self.expected_xml = xml_file.readlines()
        self.test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        self.test_banzai_header, table, cattype = open_fits_catalog(self.test_banzai_file, header_only=True)
        self.test_banzai_header['INSTRUME'] = 'fa14'
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
        expect = etree.tostring(obj1, pretty_print=True).decode()
        result = etree.tostring(xml_element, pretty_print=True).decode()

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
               <offset unit="byte">0</offset>
               <object_length unit="byte">2880</object_length>
               <parsing_standard_id>FITS 3.0</parsing_standard_id>
             </Header>
             <Table_Binary>
              <offset unit="byte">2880</offset>
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
        self.test_xml_bpm_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_bpm.xml'))
        self.test_xml_bias_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_bias.xml'))
        self.test_xml_dark_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_dark.xml'))
        self.test_xml_flat_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_flat.xml'))

        test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        self.test_raw_file = os.path.abspath(os.path.join('photometrics', 'tests', 'mef_raw_test_frame.fits'))

        test_lc_file = os.path.abspath(os.path.join('photometrics', 'tests', 'example_dartphotom.dat'))
        # Copy files to input directory, renaming lc file
        self.test_lc_file = os.path.join(self.test_dir, 'lcogt_1m0_01_fa11_20211013_65803didymos_photometry.tab')
        shutil.copy(test_lc_file, self.test_lc_file)
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

class TestExportBlockToPDS(TestCase):

    def setUp(self):
        # self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        # self.docs_root = os.path.abspath(os.path.join('photometrics', 'configs', 'PDS_docs'))
        # test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_cal.xml'))
        # with open(test_xml_collection, 'r') as xml_file:
            # self.expected_xml_cal = xml_file.readlines()
        # test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_raw.xml'))
        # with open(test_xml_collection, 'r') as xml_file:
            # self.expected_xml_raw = xml_file.readlines()
        # test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_ddp.xml'))
        # with open(test_xml_collection, 'r') as xml_file:
            # self.expected_xml_ddp = xml_file.readlines()

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
        block_params['request_number'] = '12346'
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

class TestCreateDartLightcurve(TestCase):
    """This is a cutdown version of the above TestExportBlockToPDS which only
    tests the create_dart_lightcurve part (and only for the DIA-subtracted
    subcase)"""

    def setUp(self):

#        self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.test_output_dir = os.path.join(self.test_dir, 'output')
        os.makedirs(self.test_output_dir, exist_ok=True)

        body_params = {
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

        # Create test proposal
        neo_proposal_params = { 'code'  : 'LCO2024A-999',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        # Create test superblock and block
        sblock_params = {
                         'body'     : self.test_body,
                         'proposal' : self.neo_proposal,
                         'groupid'  : self.test_body.current_name() + '_COJ-20240610',
                         'block_start' : '2024-06-10 10:05:00',
                         'block_end'   : '2024-06-10 19:22:36',
                         'tracking_number' : '0000123456',
                         'active'   : False
                       }
        self.test_sblock = SuperBlock.objects.create(**sblock_params)
        block_params = {
                         'body' : self.test_body,
                         'superblock' : self.test_sblock,
                         'request_number' :  '424242',
                         'block_start' : datetime(2024, 6, 10, 10, 0, 0),
                         'block_end' : datetime(2024, 6, 10, 19, 0, 0),
                         'obstype' : Block.OPT_IMAGING,
                         'num_observed' : 1
                        }
        self.test_block_dia, created = Block.objects.get_or_create(**block_params)
        # Second block with no frames attached
        block_params['request_number'] = '12346'
        block_params['num_observed'] = 0
        self.test_block2, created = Block.objects.get_or_create(**block_params)


        # Create test Frames from rows of table. Set common unchanging parameters here
        frame_params = {    'sitecode': 'E10',
                            'instrument': 'ep07',
                            'filter': 'rp',
                            'exptime': 170.0,
                            'midpoint': datetime(2024, 6, 10, 11, 17, 10),
                            'block': self.test_block_dia,
                            'rms_of_fit': 0.1314,
                            'nstars_in_fit': 2004,
                            'astrometric_catalog': 'GAIA-DR2',
                            'photometric_catalog': 'PS1'
                        }

        source_details = { 0 : {'mag' : 18.8447, 'err_mag' : 0.0054, 'fwhm' : 1.23, 'zp' : 23.70, 'zp_err' : 0.03},
                           1 : {'mag' : 18.8637, 'err_mag' : 0.0052, 'fwhm' : 1.21, 'zp' : 23.72, 'zp_err' : 0.03},
                           2 : {'mag' : 18.8447, 'err_mag' : 0.0051, 'fwhm' : 1.25, 'zp' : 23.69, 'zp_err' : 0.03}
                         }
        for frameid, frame_num in enumerate(range(93, 96, 1)):
            frame_params['midpoint'] += timedelta(minutes=frameid * 3)
            # print(Time(frame_params['midpoint'], format='datetime').jd)
            for frametype in [Frame.BANZAI_RED_FRAMETYPE, Frame.NEOX_RED_FRAMETYPE, Frame.NEOX_SUB_FRAMETYPE]:
                sm = source_details[frameid]
                frame_params['filename'] = f"coj2m002-ep07-20240610-{frame_num:04d}-e{frametype}.fits"
                frame_params['frametype'] = frametype
                frame_params['fwhm'] = sm['fwhm']
                frame_params['zeropoint'] = sm['zp']
                frame_params['zeropoint_err'] = sm['zp_err']
                frame, created = Frame.objects.get_or_create(**frame_params)

                if frametype == Frame.NEOX_SUB_FRAMETYPE:
                    source_params = { 'body' : self.test_body,
                                      'frame' : frame,
                                      'obs_ra' : 208.728,
                                      'obs_dec' : -10.197,
                                      'obs_mag' : sm['mag'],
                                      'err_obs_ra' : None,
                                      'err_obs_dec' : None,
                                      'err_obs_mag' : sm['err_mag'],
                                      'astrometric_catalog' : frame.astrometric_catalog,
                                      'photometric_catalog' : frame.photometric_catalog,
                                      'aperture_size' : 3.0, # arcsec
                                      'snr' : 1.0 / sm['err_mag'],
                                      'flags' : ' '
                                    }
                    source, created = SourceMeasurement.objects.get_or_create(**source_params)

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

    def test_basics(self):
        self.assertEqual(1, Body.objects.count())
        self.assertEqual(1, SuperBlock.objects.count())
        self.assertEqual(2, Block.objects.count())
        frames = Frame.objects.all()
        self.assertEqual(9, frames.count())
        self.assertEqual(3, frames.filter(frametype=Frame.BANZAI_RED_FRAMETYPE).count())
        self.assertEqual(3, frames.filter(frametype=Frame.NEOX_RED_FRAMETYPE).count())
        self.assertEqual(3, frames.filter(frametype=Frame.NEOX_SUB_FRAMETYPE).count())
        self.assertEqual(3, SourceMeasurement.objects.count())

    def test_create_dart_lightcurve_srcmeasures(self):
        expected_lc_file = os.path.join(self.test_output_dir, 'lcogt_coj_ep07_20240610_424242_65803didymos_photometry.tab')
        expected_lc_link = os.path.join(self.test_output_dir, 'LCOGT_COJ-EP07_Lister_20240610.dat')
        expected_lines = [
        '                                 file      julian_date      mag     sig       ZP  ZP_sig  inst_mag  inst_sig  filter  SExtractor_flag  aprad \r\n',
        ' coj2m002-ep07-20240610-0093-e93.fits  2460471.9702546  18.8447  0.0305  23.7000  0.0300   -4.8553    0.0054      rp                0  11.11 \r\n',
        ' coj2m002-ep07-20240610-0094-e93.fits  2460471.9723380  18.8637  0.0304  23.7200  0.0300   -4.8563    0.0052      rp                0  11.11 \r\n',
        ' coj2m002-ep07-20240610-0095-e93.fits  2460471.9765046  18.8447  0.0304  23.6900  0.0300   -4.8453    0.0051      rp                0  11.11 \r\n'
        ]

        dart_lc_file = create_dart_lightcurve(self.test_block_dia, self.test_output_dir, self.test_block_dia, create_symlink=True)

        self.assertEqual(expected_lc_file, dart_lc_file)
        self.assertTrue(os.path.exists(expected_lc_file))
        self.assertTrue(os.path.exists(expected_lc_link))

        with open(dart_lc_file, 'r', newline='') as table_file:
            lines = table_file.readlines()

        self.assertEqual(4, len(lines))
        for i, expected_line in enumerate(expected_lines):
            self.assertEqual(expected_line, lines[i])

    def test_create_dart_lightcurve_noframes(self):
        expected_lc_file = None

        dart_lc_file = create_dart_lightcurve(self.test_block2, self.test_output_dir, self.test_block2)

        self.assertEqual(expected_lc_file, dart_lc_file)
