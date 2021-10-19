import os
import shutil
import tempfile
from glob import glob
from lxml import etree, objectify
from datetime import datetime

from astropy.io import fits

from core.models import SuperBlock, Block, Frame
from photometrics.pds_subs import *

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
              <object_length unit="byte">17498880</object_length>
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
              <object_length unit="byte">17498880</object_length>
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
              <object_length unit="byte">17498880</object_length>
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
              <object_length unit="byte">17498880</object_length>
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
              <object_length unit="byte">570240</object_length>
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
              <object_length unit="byte">570240</object_length>
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
              <object_length unit="byte">570240</object_length>
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
              <object_length unit="byte">570240</object_length>
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


class TestCreateDisciplineArea(SimpleTestCase):

    def setUp(self):
        schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))

        self.schema_mappings = pds_schema_mappings(schemadir, '*.xsd')

        tests_path = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_raw_filename = os.path.join(tests_path, 'mef_raw_test_frame.fits')
        self.test_raw_header, table, cattype = open_fits_catalog(self.test_raw_filename)
        test_proc_header = os.path.join(tests_path, 'example_lco_proc_hdr')
        self.test_proc_header = fits.Header.fromtextfile(os.path.join(tests_path, test_proc_header))
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
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>ccd2_image</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>ccd3_image</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
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
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>amp2_image</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
                  <local_identifier_reference>amp3_image</local_identifier_reference>
                  <local_reference_type>display_settings_to_array</local_reference_type>
                </Local_Internal_Reference>
                <disp:Display_Direction>
                  <disp:horizontal_display_axis>Sample</disp:horizontal_display_axis>
                  <disp:horizontal_display_direction>Left to Right</disp:horizontal_display_direction>
                  <disp:vertical_display_axis>Line</disp:vertical_display_axis>
                  <disp:vertical_display_direction>Bottom to Top</disp:vertical_display_direction>
                </disp:Display_Direction>
              </disp:Display_Settings>
              <disp:Display_Settings xmlns:disp="http://pds.nasa.gov/pds4/disp/v1">
                <Local_Internal_Reference>
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


class TestWritePDSLabel(SimpleTestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        self.test_xml_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label.xml'))
        self.test_xml_raw_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_raw.xml'))
        self.test_xml_bias_cat = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_label_bias.xml'))

        self.test_banzai_file = os.path.abspath(os.path.join('photometrics', 'tests', 'banzai_test_frame.fits'))
        self.test_raw_file = os.path.abspath(os.path.join('photometrics', 'tests', 'mef_raw_test_frame.fits'))

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


    def compare_xml_files(self, expected_xml_file, xml_file):
        """Compare the expected XML in <expected_xml_file> with that in the passed
        <xml_file>
        """

        obj1 = etree.parse(expected_xml_file)
        expect = etree.tostring(obj1, pretty_print=True)
        obj2 = etree.parse(xml_file)
        result = etree.tostring(obj2, pretty_print=True)

        self.assertEquals(expect.decode("utf-8"), result.decode("utf-8"))

    def test_write_proc_label(self):

        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(self.test_banzai_file, output_xml_file, self.schemadir, mod_time=datetime(2021,5,4))

        self.compare_xml_files(self.test_xml_cat, output_xml_file)

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

    def test_write_raw_label(self):


        output_xml_file = os.path.join(self.test_dir, 'test_example_label.xml')

        status = write_product_label_xml(self.test_raw_file, output_xml_file, self.schemadir, mod_time=datetime(2021,10,15))

        self.compare_xml_files(self.test_xml_raw_cat, output_xml_file)


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
        else:
            if self.debug_print:
                print("Not removing temporary test directory", self.test_dir)

    def test_generate_e92(self):

        expected_xml_labels = [self.test_banzai_file.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir)

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)

    def test_generate_e92_specified_match(self):

        expected_xml_labels = [self.test_banzai_file.replace('.fits', '.xml'),]

        xml_labels = create_pds_labels(self.test_dir, self.schemadir, '\S*e92')

        self.assertEqual(len(expected_xml_labels), len(xml_labels))
        self.assertEqual(expected_xml_labels, xml_labels)

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


class TestExportBlockToPDS(TestCase):

    def setUp(self):
        self.schemadir = os.path.abspath(os.path.join('photometrics', 'tests', 'test_schemas'))
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_cal.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_cal = xml_file.readlines()
        test_xml_collection = os.path.abspath(os.path.join('photometrics', 'tests', 'example_pds4_collection_raw.xml'))
        with open(test_xml_collection, 'r') as xml_file:
            self.expected_xml_raw = xml_file.readlines()

        self.framedir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'banzai_test_frame.fits'
        test_file_path = os.path.join(self.framedir, self.test_file)

#        self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir = tempfile.mkdtemp(prefix='tmp_neox_')
        self.test_input_dir = os.path.join(self.test_dir, 'input')
        os.makedirs(self.test_input_dir, exist_ok=True)
        self.test_output_dir = os.path.join(self.test_dir, 'output')
        os.makedirs(self.test_output_dir, exist_ok=True)
        self.expected_root_dir = os.path.join(self.test_output_dir, 'lcogt_data')
        self.test_daydir = os.path.join(self.expected_root_dir, 'lcogt_1m0_01_fa11_20211013')

        block_params = {
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
            for extn in ['e00', 'e92']:
                new_name = os.path.join(self.test_input_dir, frame_params['filename'].replace('e91', extn))
                filename = shutil.copy(test_file_path, new_name)
                self.test_banzai_files.append(os.path.basename(filename))

        # Make one additional copy which is renamed to an -e91 (so it shouldn't be found)
        new_name = os.path.join(self.test_input_dir, 'tfn1m001-fa11-20211013-0065-e91.fits')
        shutil.copy(test_file_path, new_name)
        self.test_banzai_files.insert(1, os.path.basename(new_name))

        self.remove = True
        self.debug_print = False
        self.maxDiff = None

    def tearDown(self):
        if self.remove:
            extra_dirs = [os.path.join(self.test_daydir, x+'_data') for x in ['cal', 'ddp', 'raw']]
            for test_dir in extra_dirs + [self.test_daydir, self.expected_root_dir, self.test_output_dir, self.test_input_dir, self.test_dir]:
                try:
                    files_to_remove = glob(os.path.join(test_dir, '*'))
                    for file_to_rm in files_to_remove:
                        os.remove(file_to_rm)
                except OSError:
                    print("Error removing files in temporary test directory", test_dir)
                try:
                    os.rmdir(test_dir)
                    if self.debug_print:
                        print("Removed", test_dir)
                except OSError:
                    print("Error removing temporary test directory", test_dir)

    def test_create_directory_structure(self):

        expected_block_dir = os.path.join(self.expected_root_dir, 'lcogt_1m0_01_fa11_20211013')
        expected_status = {
                            ''         : os.path.join(expected_block_dir, ''),
                            'raw_data' : os.path.join(expected_block_dir, 'raw_data'),
                            'cal_data' : os.path.join(expected_block_dir, 'cal_data'),
                            'ddp_data' : os.path.join(expected_block_dir, 'ddp_data'),
                            'root'     : os.path.join(self.test_output_dir, 'lcogt_data')
                          }

        status = create_dart_directories(self.test_output_dir, self.test_block)

        self.assertEqual(2, Block.objects.count())
        self.assertEqual(3, Frame.objects.filter(block=self.test_block).count())
        self.assertEqual(expected_status, status)
        check_dirs = [self.expected_root_dir, expected_block_dir]
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
        expected_files = {self.test_input_dir: self.test_banzai_files}

        files = find_fits_files(self.test_input_dir)

        self.assertEqual(expected_files, files)

    def test_find_e92_fits_files(self):
        expected_files = {self.test_input_dir: [x for x in self.test_banzai_files if 'e92' in x]}

        files = find_fits_files(self.test_input_dir, '\S*e92')

        self.assertEqual(expected_files, files)

    def test_create_pds_collection_cal(self):
        expected_csv_file = os.path.join(self.expected_root_dir, 'collection_cal.csv')
        expected_xml_file = os.path.join(self.expected_root_dir, 'collection_cal.xml')
        e92_files = [x for x in self.test_banzai_files if 'e92' in x]
        expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:lcogt_cal:{x}::1.0' ) for x in self.test_banzai_files if 'e92' in x]
        paths = create_dart_directories(self.test_output_dir, self.test_block)

        csv_filename, xml_filename = create_pds_collection(self.expected_root_dir,
            self.test_input_dir, e92_files, 'cal', self.schemadir, mod_time=datetime(2021, 10, 15))

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
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1) + "\n" + expected_line.lstrip() + "\n" + xml[i].lstrip()
            else:
                assert expected_line.lstrip() == None, "Failed on line: " + str(i+1)

    def test_create_pds_collection_raw(self):
        expected_csv_file = os.path.join(self.expected_root_dir, 'collection_raw.csv')
        expected_xml_file = os.path.join(self.expected_root_dir, 'collection_raw.xml')
        e00_files = [x for x in self.test_banzai_files if 'e00' in x]
        expected_lines = [('P', f'urn:nasa:pds:dart_teleobs:lcogt_raw:{x}::1.0' ) for x in self.test_banzai_files if 'e00' in x]
        paths = create_dart_directories(self.test_output_dir, self.test_block)

        csv_filename, xml_filename = create_pds_collection(self.expected_root_dir,
            self.test_input_dir, e00_files, 'raw', self.schemadir, mod_time=datetime(2021, 10, 15))

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
                assert expected_line.lstrip() == xml[i].lstrip(), "Failed on line: " + str(i+1)
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

    def test_export_block_to_pds(self):

        export_block_to_pds(self.test_input_dir, self.test_output_dir, self.test_block, self.schemadir, skip_download=True)

        for collection_type, file_type in zip(['raw', 'cal', 'ddp'], ['csv', 'xml']):
            expected_file = os.path.join(self.expected_root_dir, f'collection_{collection_type}.{file_type}')
            self.assertTrue(os.path.exists(expected_file), f'{expected_file} does not exist')
            self.assertTrue(os.path.isfile(expected_file), f'{expected_file} is not a file')
