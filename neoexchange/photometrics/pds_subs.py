import os
import re
import shutil
import warnings
from glob import glob
from math import ceil
from collections import OrderedDict
from datetime import datetime, timedelta

from lxml import etree
import astropy.units as u
from astropy.time import Time
from astropy.table import Column, Table
from astropy.wcs import FITSFixedWarning

from core.models import Body, Frame, Block, ExportedBlock, SourceMeasurement
from astrometrics.ast_subs import normal_to_packed
from photometrics.lightcurve_subs import *
from photometrics.catalog_subs import open_fits_catalog
from photometrics.external_codes import convert_file_to_crlf
from photometrics.photometry_subs import map_filter_to_wavelength, map_filter_to_bandwidth

def get_namespace(schema_filepath):
    """Parse the specified XSD schema file at <schema_filepath> to extract the
    namespace, version and location.
    """

    tree = etree.parse(schema_filepath)
    root = tree.getroot()
    target_namespace = root.attrib.get('targetNamespace', '')
    namespace = { 'namespace' : target_namespace,
                  'version' : root.attrib.get('version', '')
                }

    namespace['location'] = target_namespace.replace('http://', 'https://') + '/' + os.path.basename(schema_filepath)

    return namespace

def pds_schema_mappings(schema_root, match_pattern='*.sch'):
    """Search for schema files matching [match_pattern] (defaults to '*.sch')
    in <schema_root>.
    Returns a dict of schema mappings indexed by a colon-separated key extracted
    from the first two parts of the filenames (e.g. 'PDS4::DISP'). Value is a dict
    consisting of `filename`, and for XSD schemas, `namespace`, `version` and
    `location` keys extracted from the XSD file e.g.
    {'PDS4::DISP': { 'filename': 'photometrics/configs/PDS_schemas/PDS4_DISP_1F00_1500.xsd',
                     'namespace': 'http://pds.nasa.gov/pds4/disp/v1',
                     'version': '1.5.0.0',
                     'location': 'https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.xsd'},
    }
    """

    schema_files = sorted(glob(os.path.join(schema_root, match_pattern)))
    schemas = {}
    for schema_filepath in schema_files:
        schema_file = os.path.basename(schema_filepath)
        chunks = schema_file.split('_')
        if len(chunks) == 3 or len(chunks) == 4:
            key = "{}::{}".format(chunks[0], chunks[1])
            schema_dict = {'filename' : schema_filepath }
            if os.path.splitext(schema_file)[1] == '.xsd':
                # Schema file extra namespace
                namespace = get_namespace(schema_filepath)
                for k,v in namespace.items():
                    schema_dict[k] = v
            schemas[key] = schema_dict
        else:
            print("Unrecognized schema", schema_file)
    return schemas

def create_obs_product(schema_mappings):
    """Create a namespace mapping from the passed dict of schemas in
    <schema_mappings>. Returns a lxml.etree.Element of Product_Observational"""

    NS_map = {None: schema_mappings['PDS4::PDS']['namespace']}
    XSI_map = ''
    for key in schema_mappings.keys():
        ns_key = None
        if key != 'PDS4::PDS':
            ns_key = key.split('::')[1].lower()
            NS_map[ns_key] = schema_mappings[key]['namespace']
        XSI_map += schema_mappings[key]['namespace'] + ' ' + schema_mappings[key]['location'] + '    '
    XSI_map = XSI_map.rstrip()

    # Add namespace for XMLSchema-instance
    NS_map['xsi'] = "http://www.w3.org/2001/XMLSchema-instance"

    qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
    obs_product = etree.Element('Product_Observational', {qname: XSI_map}, nsmap=NS_map)

    return obs_product

def create_id_area(filename, model_version='1.15.0.0', mod_time=None):
    """Create a Identification Area from the passed <filename> (which is
    appended to the fixed 'urn:nasa:pds:dart_teleobs:lcogt_cal:' URI), the
    [model_version] (defaults to current '1.15.0.0') which is the schema version
    from the PDS schema containing `Identification_Area` (e.g. PDS4_PDS_1F00.xsd)
    and an optional modification time [mod_time] (defaults to UTC "now")
    Returns an etree.Element.
    Some information on filling this out taken from:
    https://sbnwiki.astro.umd.edu/wiki/Filling_Out_the_Identification_Area_Class
    """

    mod_time = mod_time or datetime.utcnow()
    id_area = etree.Element("Identification_Area")
    xml_elements = {'logical_identifier' : 'urn:nasa:pds:dart_teleobs:lcogt_cal:' + filename,
                    'version_id' : '1.0',
                    'title' : 'Las Cumbres Observatory Calibrated Image',
                    'information_model_version' : model_version,
                    'product_class' : 'Product_Observational'
                    }
    for k,v in xml_elements.items():
        etree.SubElement(id_area, k).text = v

    # Add a Modification_History and a Modification_Detail inside that
    mod_history = etree.SubElement(id_area, "Modification_History")
    mod_detail = etree.SubElement(mod_history, "Modification_Detail")
    xml_elements = {'modification_date' : mod_time.strftime("%Y-%m-%d"),
                    'version_id' : '1.0',
                    'description' : 'initial version',
                    }
    for k,v in xml_elements.items():
        etree.SubElement(mod_detail, k).text =v

    return id_area

def get_shutter_open_close(params):
    shutter_open = params.get('DATE-OBS', None)
    shutter_close = params.get('UTSTOP', None)
    if shutter_open and shutter_close:
        # start by assuming shutter closed on the same day it opened.
        shutter_close = shutter_open.split('T')[0] + 'T' + shutter_close
        # convert to datetime object
        try:
            shutter_open = datetime.strptime(shutter_open, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            shutter_open = datetime.strptime(shutter_open, "%Y-%m-%dT%H:%M:%S")
        try:
            shutter_close = datetime.strptime(shutter_close, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            shutter_close = datetime.strptime(shutter_close, "%Y-%m-%dT%H:%M:%S")
        # Increment close-time by 1 day if close happened before open
        if shutter_close < shutter_open:
            shutter_close = shutter_close + timedelta(days=1)
    return shutter_open, shutter_close

def create_discipline_area(header, filename, nsmap):
    """Creates a Discipline_Area element to be contained in an Observation_Area
    from the passed FITS header <header>, <filename> and schema/namespace mappings
    dict <nsmap> (from pds_schema_mappings())
    This contains disp:Display_Settings, img:Exposure, img:Optical_Filter and geom:Geometry
    SubElements so these schemas need to be in <nsmap>
    Returns an etree.Element for the Discipline Area.
    """
    discp_area = etree.Element("Discipline_Area")

    # Create Display Settings discipline area
    disp_settings = create_display_settings(filename, nsmap)
    # Create Display Direction discipline area
    disp_direction = create_display_direction(nsmap, 'PDS4::DISP')
    disp_settings.append(disp_direction)
    discp_area.append(disp_settings)
    # Create Image Exposure and Optical Filter sections
    img_exposure = create_image_exposure(header, nsmap)
    discp_area.append(img_exposure)
    img_filter = create_image_filter(header, nsmap)
    discp_area.append(img_filter)
    # Create Geometry area
    geom = create_geometry(filename, nsmap)
    img_disp = create_imgdisp_geometry(filename, nsmap)
    geom.append(img_disp)    
    # Create Display Direction discipline area
    disp_direction = create_display_direction(nsmap, 'PDS4::GEOM')
    img_disp.append(disp_direction)

    # Create Object Orientation
    obj_orient = create_obj_orient(header, nsmap)
    img_disp.append(obj_orient)
    # Add the whole Geometry subclass to the Discipline Area
    discp_area.append(geom)

    return discp_area

def create_display_settings(filename, nsmap):

    etree.register_namespace("disp", nsmap['PDS4::DISP']['namespace'])
    disp_settings = etree.Element(etree.QName(nsmap['PDS4::DISP']['namespace'],"Display_Settings"))
    lir = etree.SubElement(disp_settings, "Local_Internal_Reference")
    etree.SubElement(lir, "local_identifier_reference").text = os.path.splitext(filename)[0]
    etree.SubElement(lir, "local_reference_type").text = "display_settings_to_array"

    return disp_settings

def create_display_direction(nsmap, namespace):

    disp_ns = nsmap[namespace]['namespace']
    ns_shortname = namespace.split('::')[1].lower()
    etree.register_namespace(ns_shortname, disp_ns)
    disp_direction = etree.Element(etree.QName(disp_ns,"Display_Direction"))
    etree.SubElement(disp_direction, etree.QName(disp_ns, "horizontal_display_axis")).text = "Sample"
    etree.SubElement(disp_direction, etree.QName(disp_ns, "horizontal_display_direction")).text = "Left to Right"
    etree.SubElement(disp_direction, etree.QName(disp_ns, "vertical_display_axis")).text = "Line"
    etree.SubElement(disp_direction, etree.QName(disp_ns, "vertical_display_direction")).text = "Bottom to Top"

    return disp_direction

def create_image_exposure(header, nsmap):

    img_ns = nsmap['PDS4::IMG']['namespace']
    etree.register_namespace("img", img_ns)
    img_exposure = etree.Element(etree.QName(img_ns,"Exposure"))
    exposure_time = "{:.3f}".format(header.get('EXPTIME', 0.0))
    etree.SubElement(img_exposure, etree.QName(img_ns, "exposure_duration"), attrib={'unit' : 's'}).text = exposure_time

    return img_exposure

def create_image_filter(header, nsmap):

    img_ns = nsmap['PDS4::IMG']['namespace']
    etree.register_namespace("img", img_ns)
    optical_filter = etree.Element(etree.QName(img_ns,"Optical_Filter"))
    obs_filter = header.get('FILTER', 'w')
    etree.SubElement(optical_filter, etree.QName(img_ns, "filter_name")).text = obs_filter

    obs_filter_bwidth = map_filter_to_bandwidth(obs_filter)
    obs_filter_bwidth_str = "{:.1f}".format(obs_filter_bwidth.value)
    obs_filter_bwidth_unit = str(obs_filter_bwidth.unit)
    etree.SubElement(optical_filter, etree.QName(img_ns, "bandwidth"), attrib={'unit' : obs_filter_bwidth_unit}).text = obs_filter_bwidth_str

    obs_filter_cwave = map_filter_to_wavelength(obs_filter)
    obs_filter_cwave_str = "{:.1f}".format(obs_filter_cwave.value)
    obs_filter_cwave_unit = str(obs_filter_cwave.unit)
    etree.SubElement(optical_filter, etree.QName(img_ns, "center_filter_wavelength"), attrib={'unit' : obs_filter_cwave_unit}).text = obs_filter_cwave_str

    return optical_filter

def create_geometry(filename, nsmap):

    geom_ns = nsmap['PDS4::GEOM']['namespace']
    etree.register_namespace("geom", geom_ns)
    geometry = etree.Element(etree.QName(geom_ns, "Geometry"))

    return geometry

def create_imgdisp_geometry(filename, nsmap):

    geom_ns = nsmap['PDS4::GEOM']['namespace']
    etree.register_namespace("geom", geom_ns)
    img_disp_geometry = etree.Element(etree.QName(geom_ns, "Image_Display_Geometry"))
    lir = etree.SubElement(img_disp_geometry, "Local_Internal_Reference")
    etree.SubElement(lir, "local_identifier_reference").text = os.path.splitext(filename)[0]
    etree.SubElement(lir, "local_reference_type").text = "display_to_data_object"

    return img_disp_geometry

def create_obj_orient(header, nsmap):

    geom_ns = nsmap['PDS4::GEOM']['namespace']
    etree.register_namespace("geom", geom_ns)
    obj_orient = etree.Element(etree.QName(geom_ns, "Object_Orientation_RA_Dec"))
    ra_str = "{:.6f}".format(header['CRVAL1'])
    etree.SubElement(obj_orient, etree.QName(geom_ns, "right_ascension_angle"), attrib={'unit' : "deg"}).text = ra_str

    dec_str = "{:.6f}".format(header['CRVAL2'])
    etree.SubElement(obj_orient, etree.QName(geom_ns, "declination_angle"), attrib={'unit' : "deg"}).text = dec_str

    rotangle_str = "{:.1f}".format(0.0)
    etree.SubElement(obj_orient, etree.QName(geom_ns, "celestial_north_clock_angle"), attrib={'unit' : "deg"}).text = rotangle_str

    # Create Reference_Frame_Identification
    ref_frame = etree.SubElement(obj_orient, etree.QName(geom_ns, "Reference_Frame_Identification"))
    etree.SubElement(ref_frame, etree.QName(geom_ns, "name")).text = "J2000"
    etree.SubElement(ref_frame, etree.QName(geom_ns, "comment")).text = "equinox of RA and DEC"
    

    return obj_orient

def create_obs_area(header, filename):
    """Creates the Observation Area set of classes and returns an etree.Element with it.
    Documentation on filling this out taken from
    https://sbnwiki.astro.umd.edu/wiki/Filling_Out_the_Observation_Area_Classes
    """

    obs_area = etree.Element("Observation_Area")

    # Create Time_Coordinates sub element
    time_coords = etree.SubElement(obs_area, "Time_Coordinates")
    shutter_open, shutter_close = get_shutter_open_close(header)
    etree.SubElement(time_coords, "start_date_time").text = shutter_open.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    etree.SubElement(time_coords, "stop_date_time").text = shutter_close.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    invest_area = etree.SubElement(obs_area, "Investigation_Area")
    etree.SubElement(invest_area, "name").text = "Double Asteroid Redirection Test"
    etree.SubElement(invest_area, "type").text = "Mission"
    # Create Internal Reference subclass of Investigation Area
    int_reference = etree.SubElement(invest_area, "Internal_Reference")
    etree.SubElement(int_reference, "lid_reference").text = "urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test"
    etree.SubElement(int_reference, "reference_type").text = "data_to_investigation"
    # Create Observing System subclass of Observation Area
    obs_system = etree.SubElement(obs_area, "Observing_System")
    obs_components = {  'Instrument' : 'Sinistro',
                        'Observatory' : 'Las Cumbres Observatory (LCOGT)',
                        'Telescope' : 'LCOGT ' + header.get('TELESCOP','') + ' Telescope'
                     }
    for component in obs_components:
        comp = etree.SubElement(obs_system, "Observing_System_Component")
        etree.SubElement(comp, "name").text = obs_components[component]
        etree.SubElement(comp, "type").text = component
        description = "The description for the {} can be found in the document collection for this bundle.".format(component.lower())
        etree.SubElement(comp, "description").text = description

    # Create Target Identification subclass
    target_id = etree.SubElement(obs_area, "Target_Identification")
    target_type = {'MINORPLANET' : 'Asteroid', 'COMET' : 'Comet' }
    etree.SubElement(target_id, "name").text = header.get('object', '')
    etree.SubElement(target_id, "type").text = target_type.get(header.get('srctype',''), 'Unknown')

    return obs_area

def create_file_area_obs(header, filename):
    """Creates the File Area Observational set of classes and returns an etree.Element with it.
    """

    # Mapping from BITPIX to PDS4 types
    PDS_types = {  8 : "UnsignedByte",
                  16 : "SignedMSB2",
                  32 : "SignedMSB4",
                 -32 : "IEEE754MSBSingle",
                  64 : "SignedMSB8",
                 -64 : "IEEE754MSBDouble"
                }

    file_area_obs = etree.Element("File_Area_Observational")
    file_element = etree.SubElement(file_area_obs, "File")
    etree.SubElement(file_element, "file_name").text = filename
    etree.SubElement(file_element, "comment").text = "Calibrated LCOGT image file"

    # XXX Check NAXIS=2 before this
    array_2d = etree.SubElement(file_area_obs, "Array_2D_Image")
    etree.SubElement(array_2d, "local_identifier").text = os.path.splitext(filename)[0]

    # Compute size of header from list length+1 (missing END card)
    header_size_bytes = (len(header)+1)*80
    # Actual size is rounded to nearest multiple of FITS block size (2880 bytes)
    header_size_blocks = ceil(header_size_bytes/2800.0) * 2800
    header_size = "{:d}".format(header_size_blocks)

    etree.SubElement(array_2d, "offset", attrib={"unit" : "byte"}).text = header_size
    etree.SubElement(array_2d, "axes").text = str(header.get('NAXIS', 2))
    etree.SubElement(array_2d, "axis_index_order").text = "Last Index Fastest"
    elem_array = etree.SubElement(array_2d, "Element_Array")
    etree.SubElement(elem_array, "data_type").text = PDS_types.get(header['BITPIX'])

    axis_mapping = {'Line' : 'NAXIS2', 'Sample' : 'NAXIS2'}
    for sequence_number, axis_name in enumerate(axis_mapping, start=1):
        axis_array = etree.SubElement(array_2d, "Axis_Array")
        etree.SubElement(axis_array, "axis_name").text = axis_name
        etree.SubElement(axis_array, "elements").text = str(header[axis_mapping[axis_name]])
        etree.SubElement(axis_array, "sequence_number").text = str(sequence_number)

    return file_area_obs

def create_file_area_inv(filename, mod_time=None):
    """Creates the File Area Inventory set of classes and returns an etree.Element with it.
    """

    mod_time = mod_time or datetime.fromtimestamp(os.path.getmtime(filename))
    file_area_inv = etree.Element("File_Area_Inventory")
    file_element = etree.SubElement(file_area_inv, "File")
    etree.SubElement(file_element, "file_name").text = os.path.basename(filename)
    etree.SubElement(file_element, "creation_date_time").text = mod_time.strftime("%Y-%m-%d")

    # Count lines in CSV file for number of records
    num_records = 0
    with open(filename, 'r') as csv_fh:
        lines = csv_fh.readlines()
        num_records = len(lines)
    inventory = etree.SubElement(file_area_inv, "Inventory")
    etree.SubElement(inventory, "offset", attrib={"unit" : "byte"}).text = '0'
    etree.SubElement(inventory, "parsing_standard_id").text = "PDS DSV 1"
    etree.SubElement(inventory, "records").text = str(num_records)
    etree.SubElement(inventory, "record_delimiter").text = "Carriage-Return Line-Feed"
    etree.SubElement(inventory, "field_delimiter").text = "Comma"

    record_delim = etree.SubElement(inventory, "Record_Delimited")
    etree.SubElement(record_delim, "fields").text = "2"
    etree.SubElement(record_delim, "groups").text = "0"
    field_delim = etree.SubElement(record_delim, "Field_Delimited")

    etree.SubElement(field_delim, "name").text = "Member Status"
    etree.SubElement(field_delim, "field_number").text = "1"
    etree.SubElement(field_delim, "data_type").text = "ASCII_String"
    etree.SubElement(field_delim, "maximum_field_length", attrib={"unit" : "byte"}).text = "1"
    etree.SubElement(field_delim, "description").text = '''
            P indicates primary member of the collection
            S indicates secondary member of the collection
          '''
    field_delim2 = etree.SubElement(record_delim, "Field_Delimited")
    etree.SubElement(field_delim2, "name").text = "LIDVID_LID"
    etree.SubElement(field_delim2, "field_number").text = "2"
    etree.SubElement(field_delim2, "data_type").text = "ASCII_LIDVID_LID"
    etree.SubElement(field_delim2, "maximum_field_length", attrib={"unit" : "byte"}).text = "255"
    etree.SubElement(field_delim2, "description").text = "\n            The LID or LIDVID of a product that is a member of the collection.\n          "
    etree.SubElement(inventory, "reference_type").text = "inventory_has_member_product"

    return file_area_inv

def create_file_area_table(filename):

    fields = {'validity_flag'  : { 'field_location' : 1, 'data_type' : 'ASCII_String', 'field_length' : 1, 'description' : 'Flag whether this is a valid photometric datapoint, # indicates probably invalid blended data due to asteroid interference with the star.' },
              'file' : { 'field_location' : 2, 'data_type' : 'ASCII_String', 'field_length' : 36, 'description' : 'File name of the calibrated image where data were measured.' },
              'julian_date' : { 'field_location' : 40, 'data_type' : 'ASCII_Real', 'field_length' : 15, 'description' : 'UTC Julian date of the exposure midtime' },
              'mag' : { 'field_location' : 56, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : 'Calibrated PanSTARRs r-band apparent magnitude of asteroid' },
              'sig' : { 'field_location' : 66, 'data_type' : 'ASCII_Real', 'field_length' : 6, 'description' : '1-sigma error on the apparent magnitude' },
              'ZP'  : { 'field_location' : 73, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : 'Calibrated zero point magnitude in PanSTARRs r-band' },
              'ZP_sig' : { 'field_location' : 83, 'data_type' : 'ASCII_Real', 'field_length' : 6, 'description' : '1-sigma error on the zero point magnitude' },
              'inst_mag' : { 'field_location' : 91, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : 'instrumental magnitude of asteroid' },
              'inst_sig' : { 'field_location' : 101, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : '1-sigma error on the instrumental magnitude' },
              'filter' : { 'field_location' : 111, 'data_type' : 'ASCII_String', 'field_length' : 6, 'description' : 'Transformed filter used for calibration.' },
              'SExtractor_flag' : { 'field_location' : 119, 'data_type' : 'ASCII_Integer', 'field_length' : 15, 'description' : 'Flags associated with the Source Extractor photometry measurements. See source_extractor_flags.txt in the documents folder for this archive for more detailed description.' },
              'aprad' : { 'field_location' : 136, 'data_type' : 'ASCII_Real', 'field_length' : 5, 'description' : 'radius in pixels of the aperture used for the photometry measurement' }
              }
    file_area_table = etree.Element("File_Area_Observational")
    file_element = etree.SubElement(file_area_table, "File")
    etree.SubElement(file_element, "file_name").text = os.path.basename(filename)
    etree.SubElement(file_element, "comment").text = 'photometry summary table'

    with open(filename, 'rb') as table_fh:
        # Read lines, skipping blank lines
        table = [line for line in table_fh.readlines() if line.strip()]
    header_element = etree.SubElement(file_area_table, "Header")
    # Compute size of header from first row
    header_size_bytes = len(table[0])
    header_size = "{:d}".format(header_size_bytes)

    etree.SubElement(header_element, "offset", attrib={"unit" : "byte"}).text = "0"
    etree.SubElement(header_element, "object_length", attrib={"unit" : "byte"}).text = header_size
    etree.SubElement(header_element, "parsing_standard_id").text = "UTF-8 Text"

    table_element = etree.SubElement(file_area_table, "Table_Character")
    etree.SubElement(table_element, "offset", attrib={"unit" : "byte"}).text = header_size
    etree.SubElement(table_element, "records").text = str(len(table)-1)
    etree.SubElement(table_element, "record_delimiter").text = "Carriage-Return Line-Feed"

    record_element = etree.SubElement(table_element, "Record_Character")
    etree.SubElement(record_element, "fields").text = str(len(fields))
    etree.SubElement(record_element, "groups").text = str(0)
    etree.SubElement(record_element, "record_length", attrib={"unit" : "byte"}).text = header_size

    field_num = 1
    for tab_field, field_data in fields.items():
        field_element = etree.SubElement(record_element, "Field_Character")
        etree.SubElement(field_element, "name").text = tab_field
        etree.SubElement(field_element, "field_number"). text = str(field_num)
        etree.SubElement(field_element, "field_location", attrib={"unit" : "byte"}).text = str(field_data['field_location'])
        etree.SubElement(field_element, "data_type").text = field_data['data_type']
        etree.SubElement(field_element, "field_length", attrib={"unit" : "byte"}).text = str(field_data['field_length'])
        etree.SubElement(field_element, "description").text = field_data['description']
        field_num += 1
    return file_area_table

def ordinal(num):
    """
      Returns ordinal number string from int, e.g. 1, 2, 3 becomes 1st, 2nd, 3rd, etc.
    """
    SUFFIXES = {1: 'st', 2: 'nd', 3: 'rd'}
    # I'm checking for 10-20 because those are the digits that
    # don't follow the normal counting scheme.
    if 10 <= num % 100 <= 20:
        suffix = 'th'
    else:
        # the second parameter is a default.
        suffix = SUFFIXES.get(num % 10, 'th')
    return str(num) + suffix

def create_file_area_bintable(filename):

    fields = {'filename' : { 'field_location' : 1, 'data_type' : 'ASCII_String', 'field_length' : 36, 'description' : 'Filename of the calibrated image where data were measured.' },
              'mjd' : { 'field_location' : 37, 'data_type' : 'IEEE754MSBDouble', 'field_length' : 8, 'description' : 'UTC Modified Julian Date of the exposure midtime' },
              'obs_midpoint' : { 'field_location' : 45, 'data_type' : 'ASCII_String', 'field_length' : 36, 'description' : 'UTC datetime string of the exposure midtime' },
              'exptime' : { 'field_location' : 81, 'data_type' : 'IEEE754MSBDouble', 'field_length' : 8, 'description' : 'Exposure time in seconds' },
              'filter' : { 'field_location' : 89, 'data_type' : 'ASCII_String', 'field_length' : 36, 'description' : 'Name of the filter used' },
              'obs_ra'  : { 'field_location' : 125, 'data_type' : 'IEEE754MSBDouble', 'field_length' : 8, 'description' : 'Right ascension of the asteroid' },
              'obs_dec' : { 'field_location' : 133, 'data_type' : 'IEEE754MSBDouble', 'field_length' : 8, 'description' : 'Declination of the asteroid' },
              'flux_radius' : { 'field_location' : 141, 'data_type' : 'IEEE754MSBDouble', 'field_length' : 8, 'description' : 'Flux radius' },
              'fwhm' : { 'field_location' : 149, 'data_type' : 'IEEE754MSBDouble', 'field_length' : 8, 'description' : 'Full Width Half Maximum of the frame' },
              }
    file_area_table = etree.Element("File_Area_Observational")
    file_element = etree.SubElement(file_area_table, "File")
    etree.SubElement(file_element, "file_name").text = os.path.basename(filename)
    etree.SubElement(file_element, "comment").text = 'multi-aperture photometry summary table'

    table = Table.read(filename)
    header_element = etree.SubElement(file_area_table, "Header")
    # Compute size of header from first row
    header_size_bytes = 2880
    header_size = "{:d}".format(header_size_bytes)

    etree.SubElement(header_element, "offset", attrib={"unit" : "byte"}).text = "0"
    etree.SubElement(header_element, "object_length", attrib={"unit" : "byte"}).text = header_size
    etree.SubElement(header_element, "parsing_standard_id").text = "FITS 3.0"

    table_element = etree.SubElement(file_area_table, "Table_Binary")
    etree.SubElement(table_element, "offset", attrib={"unit" : "byte"}).text = header_size
    etree.SubElement(table_element, "records").text = str(len(table))

    record_element = etree.SubElement(table_element, "Record_Binary")
    etree.SubElement(record_element, "fields").text = str(len(table.colnames))
    etree.SubElement(record_element, "groups").text = str(0)
    # Feels like there has to be an easier way...
    record_size = sum([table[c].dtype.itemsize for c in table.colnames])
    etree.SubElement(record_element, "record_length", attrib={"unit" : "byte"}).text = str(record_size)

    field_num = 1
    for tab_field, field_data in fields.items():
        field_element = etree.SubElement(record_element, "Field_Binary")
        etree.SubElement(field_element, "name").text = tab_field
        etree.SubElement(field_element, "field_number"). text = str(field_num)
        etree.SubElement(field_element, "field_location", attrib={"unit" : "byte"}).text = str(field_data['field_location'])
        etree.SubElement(field_element, "data_type").text = field_data['data_type']
        etree.SubElement(field_element, "field_length", attrib={"unit" : "byte"}).text = str(field_data['field_length'])
        etree.SubElement(field_element, "description").text = field_data['description']
        field_num += 1
    # Write the 20 magnitude and magnitude error columns
    start = field_data['field_location'] + field_data['field_length']
    index = 0
    for tab_field in table.colnames[len(fields):]:
        field_element = etree.SubElement(record_element, "Field_Binary")
        etree.SubElement(field_element, "name").text = tab_field
        etree.SubElement(field_element, "field_number"). text = str(field_num)
        etree.SubElement(field_element, "field_location", attrib={"unit" : "byte"}).text = str(start)
        etree.SubElement(field_element, "data_type").text = field_data['data_type']
        field_length = table[tab_field].dtype.itemsize
        etree.SubElement(field_element, "field_length", attrib={"unit" : "byte"}).text = str(field_length)
        error_string = ''
        if 'err_' in tab_field:
            error_string = 'error '
        description = f"Magnitude {error_string}in the {ordinal(index)} index aperture"
        etree.SubElement(field_element, "description").text = description
        field_num += 1
        start += field_length
        if 'err_' in tab_field:
            index += 1

    return file_area_table

def create_reference_list(collection_type):
    """Create a Reference List section
    """

    reference_list = etree.Element("Reference_List")
    # Create Internal Reference subclass of Target Area
    int_reference = etree.SubElement(reference_list, "Internal_Reference")
    etree.SubElement(int_reference, "lid_reference").text = "urn:nasa:pds:dart_teleobs:documentation_lcogt:las_cumbres_dart_uncalibrated_calibrated_sis"
    etree.SubElement(int_reference, "reference_type").text = "collection_to_document"
    etree.SubElement(int_reference, "comment").text = "Reference is to the Las Cumbres DART Uncalibrated, Calibrated SIS document which describes the data products in this collection."
    # Create Internal Reference to the <collection_type>'s overview
    int_reference = etree.SubElement(reference_list, "Internal_Reference")
    etree.SubElement(int_reference, "lid_reference").text = f"urn:nasa:pds:dart_teleobs:data_lcogt{collection_type}:overview"
    etree.SubElement(int_reference, "reference_type").text = "collection_to_document"
    etree.SubElement(int_reference, "comment").text = f"Reference is to the text file which gives an overview of the LCOGT {collection_type} Data Collection."

    return reference_list

def preamble_mapping(schema_mappings):
    """Return a OrderedDict mapping from PDS schemas to the XML strings
    for the XML label preamble. Supports multiple versions based on the
    'version' key of the schema's mapping dict e.g.
    schema_mappings[schema]['version']
    """

    mapping = OrderedDict([
                            ('PDS4::PDS',  {'1.15.0.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1F00.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>''',
                                            '1.19.0.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1J00.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>'''}),
                            ('PDS4::DISP', {'1.5.0.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>''',
                                            '1.5.1.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1J00_1510.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>'''}),
                            ('PDS4::IMG',  {'1.8.1.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1F00_1810.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>''',
                                            '1.8.7.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1J00_1870.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>'''}),
                            ('PDS4::GEOM', {'1.9.1.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1F00_1910.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>''',
                                            '1.9.6.0' : b'''<?xml-model href="https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1J00_1960.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>'''})
                        ])

    output_mapping = OrderedDict()
    for key in mapping.keys():
        if key in schema_mappings:
            version = schema_mappings[key]['version']
            output_mapping[key] = mapping[key][version]

    return output_mapping

def write_product_label_xml(filepath, xml_file, schema_root, mod_time=None):
    """Create a PDS4 XML product label in <xml_file> from the FITS file
    pointed at by <filepath>. This used the PDS XSD and Schematron schemas located
    in <schema_root> directory. Optionally a different modification `datetime` [mod_time]
    can be passed which is used in `create_id_area()`
    <schema_root> should contain the main PDS common and Display, Imaging and
    Geometry Discipline Dictionaries (although this is not checked for)
    """

    xmlEncoding = "UTF-8"
    schema_mappings = pds_schema_mappings(schema_root, '*.xsd')

    processedImage = create_obs_product(schema_mappings)

    header, table, cattype = open_fits_catalog(filepath)
    filename = os.path.basename(filepath)

    id_area = create_id_area(filename, schema_mappings['PDS4::PDS']['version'], mod_time)
    processedImage.append(id_area)

    # Add the Observation_Area
    obs_area = create_obs_area(header, filename)

    # Add Discipline Area
    discipline_area = create_discipline_area(header, filename, schema_mappings)
    obs_area.append(discipline_area)
    processedImage.append(obs_area)

    # Create File_Area_Observational
    file_area = create_file_area_obs(header, filename)
    processedImage.append(file_area)

    # Wrap in ElementTree to write out to XML file
    preamble = b'''<?xml-model href="https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1F00.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>
    <?xml-model href="https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>
    <?xml-model href="https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1F00_1810.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>
    <?xml-model href="https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1F00_1910.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>'''

    doc = preamble + etree.tostring(processedImage)
    tree = etree.ElementTree(etree.fromstring(doc))
    tree.write(xml_file, pretty_print=True, standalone=None,
                xml_declaration=True, encoding=xmlEncoding)

    return

def create_pds_labels(procdir, schema_root):
    """Create PDS4 product labels for all processed (e92) FITS fils in <procdir>
    The PDS4 schematron and XSD files in <schema_root> are used in generating
    the XML file.
    A list of created PDS4 label filenames (with paths) is returned; this list
    may be zero length.
    """

    xml_labels = []
    full_procdir = os.path.abspath(os.path.expandvars(procdir))
    files_to_process = sorted(glob(os.path.join(full_procdir, '*-e92.fits')))

    for fits_file in files_to_process:
        xml_file = fits_file.replace('.fits', '.xml')
        write_product_label_xml(fits_file, xml_file, schema_root)
        if os.path.exists(xml_file):
            xml_labels.append(xml_file)

    return xml_labels

def split_filename(filename):
    """Splits an LCO filename <filename> into component parts
    Returns a dict of components"""

    name_parts = {}
    fileroot, name_parts['extension'] = os.path.splitext(filename)
    if len(fileroot) >= 31:
        chunks = fileroot.split('-')
        name_parts['site'] = chunks[0][0:3]
        name_parts['tel_class'] = chunks[0][3:6]
        name_parts['tel_serial'] = chunks[0][6:8]
        name_parts['instrument'] = chunks[1]
        name_parts['dayobs'] = chunks[2]
        name_parts['frame_num'] = chunks[3]
        name_parts['frame_type'] = chunks[4]
    elif len(fileroot) == 8 and fileroot.startswith('rccd'):
        # Swope, need to make up many things....
        name_parts['site'] = 'lco'
        name_parts['tel_class'] = '1m0'
        name_parts['tel_serial'] = '01'
        name_parts['instrument'] = 'Direct4Kx4K-4'
        name_parts['dayobs'] = '20220925'
        name_parts['frame_num'] = fileroot[4:9]
        name_parts['frame_type'] = 'e72'
    elif len(fileroot) == 18 and fileroot.startswith('rccd'):
        # Swope, need to make up many things....
        chunks = fileroot.split('-')
        name_parts['site'] = 'lco'
        name_parts['tel_class'] = '1m0'
        name_parts['tel_serial'] = '01'
        name_parts['instrument'] = 'Direct4Kx4K-4'
        name_parts['dayobs'] = chunks[1]
        name_parts['frame_num'] = chunks[2]
        name_parts['frame_type'] = 'e72'
    elif len(fileroot) == 20 and fileroot.startswith('ccd'):
        # Swope, need to make up many things....
        chunks = fileroot.split('-')
        name_parts['site'] = 'lco'
        name_parts['tel_class'] = '1m0'
        name_parts['tel_serial'] = '01'
        name_parts['instrument'] = 'Direct4Kx4K-4'
        name_parts['dayobs'] = chunks[1]
        name_parts['frame_num'] = chunks[0][-4:]
        name_parts['frame_type'] = 'e72'

    return name_parts

def make_pds_asteroid_name(body_or_bodyname):

    filename = pds_name = None
    if isinstance(body_or_bodyname, Body):
        bodyname = body_or_bodyname.full_name()
    else:
        bodyname = body_or_bodyname

    if body_or_bodyname is not None and body_or_bodyname != '':
        paren_loc = bodyname.rfind('(')
        if paren_loc > 0:
            bodyname = bodyname[0:paren_loc].rstrip()

        # Filename and therefore the logical_identifier can only contain lowercase
        # letters.
        filename = bodyname.replace(' ', '').lower()
        chunks = bodyname.split(' ')
        _, conv_status = normal_to_packed(bodyname)
        if len(chunks) == 2 and chunks[0].isdigit() and conv_status == -1:
            pds_name = f"({chunks[0]}) {chunks[1]}"
        else:
            pds_name = bodyname

    return filename, pds_name

def create_dart_lightcurve(input_dir_or_block, output_dir, block, match='photometry_*.dat', create_symlink=False):
    """Creates a DART-format lightcurve file from either:
    1) the photometry file and LOG in <input_dir_or_block>. or,
    2) the SourceMeasurements belonging to the Block passed as <input_dir_or_block>
    outputting to <output_dir>. Block <block> is used find the directory
    for the photometry file.
    The file is converted to CRLF line endings for PDS archiving
    """

    warnings.simplefilter('ignore', FITSFixedWarning)
    output_lc_filepath = None
    #frames = Frame.objects.filter(block=block, frametype__in=[Frame.BANZAI_RED_FRAMETYPE, Frame.SWOPE_RED_FRAMETYPE])
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_RED_FRAMETYPE)
    if frames.count() > 0:
        first_frame = frames.earliest('midpoint')
        first_filename = first_frame.filename
        file_parts = split_filename(first_filename)
        if len(file_parts) == 8:
            if hasattr(input_dir_or_block, 'request_number') is False:
                # Directory path passed
                root_dir = input_dir_or_block
                photometry_files = sorted(glob(os.path.join(root_dir, match)))
                # Weed out Control_Star photometry files
                photometry_files = [x for x in photometry_files if 'Control_Star' not in x]
                # No matches, retry with dayobs added onto the path
                if len(photometry_files) == 0:
                    root_dir = os.path.join(input_dir_or_block, file_parts['dayobs'])
                    photometry_files = sorted(glob(os.path.join(root_dir, match)))
                    # Weed out Control_Star photometry files
                    photometry_files = [x for x in photometry_files if 'Control_Star' not in x]
            else:
                # Assuming Block passed
                num_srcs = SourceMeasurement.objects.filter(frame__block=input_dir_or_block, frame__frametype__in=[Frame.NEOX_RED_FRAMETYPE, Frame.NEOX_SUB_FRAMETYPE]).count()
                if num_srcs > 0:
                    photometry_files = [input_dir_or_block, ]
                else:
                    logger.warning(f"No SourceMeasurements found for reduced e92 frames for Block id {input_dir_or_block.id}")
                    photometry_files = []
            for photometry_file in photometry_files:
                fits_bintable = False
                if type(photometry_file) != Block:
                    if photometry_file.endswith('.fits') is True:
                        print("Multi-aperture FITS BINTABLE")
                        fits_bintable = True
                        table = photometry_file
                        aper_radius = -1
                    else:
                        print("Table from PHOTPIPE output + LOG")
                        log_file = os.path.join(os.path.dirname(photometry_file), 'LOG')
                        table = read_photompipe_file(photometry_file)
                        aper_radius = extract_photompipe_aperradius(log_file)
                        if '-PP' not in file_parts['site']:
                            file_parts['site'] += '-PP'
                else:
                    print("Table from SourceMeasurements")
                    table = create_table_from_srcmeasures(input_dir_or_block)
                    aper_radius = table['aprad'].mean()
#                    file_parts['site'] += '-Src'
#                print(len(table), aper_radius)
                if table and aper_radius:
                    phot_filename, pds_name = make_pds_asteroid_name(block.body)
                    # Format for LC files: '<origin>_<site>_<inst.>_<YYYYMMDD>_<request #>_<astname#>_photometry.txt'
                    file_parts['dayobs'] = first_frame.midpoint.strftime("%Y%m%d")
                    origin = 'lcogt'
                    observer = 'Lister'
                    if file_parts['site'].startswith('lco'):
                        origin = 'lco'
                        observer = 'Osip'
                    extn = 'tab'
                    if fits_bintable is True:
                        extn = 'fits'
                    output_lc_file = f"{origin.lower()}_{file_parts['site']}_{file_parts['instrument']}_{file_parts['dayobs']}_{block.request_number}_{phot_filename}_photometry.{extn}"
                    output_lc_filepath = os.path.join(output_dir, output_lc_file)
                    if fits_bintable is True and type(table) == str:
                        # Create directory path if it doesn't exist
                        filepath_dir = os.path.dirname(output_lc_filepath)
                        if os.path.exists(filepath_dir) is False:
                            os.makedirs(filepath_dir)
                        # FITS binary table, just copy input `photometry_file`
                        # filepath to output filename
                        shutil.copy(photometry_file, output_lc_filepath)
                    else:
                        write_dartformat_file(table, output_lc_filepath, aper_radius)
                        # Convert lc file to CRLF endings required by PDS
                        status = convert_file_to_crlf(output_lc_filepath)
                    # Create DART upload format symlink
                    if create_symlink:
                        symlink_lc_file = f"{origin.upper()}_{file_parts['site'].upper()}-{file_parts['instrument'].upper()}_{observer}_{file_parts['dayobs']}.dat"
                        dir_fh = os.open(output_dir, os.O_RDONLY)
                        if os.path.exists(os.path.join(output_dir, symlink_lc_file)):
                            os.remove(os.path.join(output_dir, symlink_lc_file))
                        os.symlink(output_lc_file, symlink_lc_file, dir_fd=dir_fh)
                else:
                    if table:
                        logger.error("Couldn't extract aperture radius from LOG")
                    else:
                        logger.error("Couldn't extract table")
        else:
            logger.warning(f"Could not decode filename: {first_filename}")
    else:
        logger.warning("Could not find any reduced Frames")

    return output_lc_filepath
