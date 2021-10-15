import os
import re
from glob import glob
from math import ceil
from datetime import datetime, timedelta

from lxml import etree

from core.models import Frame
from photometrics.catalog_subs import open_fits_catalog
from photometrics.photometry_subs import map_filter_to_wavelength, map_filter_to_bandwidth

import logging
logger = logging.getLogger(__name__)

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

def write_xml(filepath, xml_file, schema_root, mod_time=None):
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
        write_xml(fits_file, xml_file, schema_root)
        if os.path.exists(xml_file):
            xml_labels.append(xml_file)

    return xml_labels

def split_filename(filename):
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

    return name_parts

def create_dart_directories(output_dir, block):
    """Creates the directory structures in <output_dir> needed for exporting a
    Block <block> of light curve data to DART. Creates a directory tree as follows:
    └── <output_dir>
        └── lcogt_data
            └── lcogt_1m0_01_fa11_20211013
                ├── cal_data
                ├── ddp_data
                └── raw_data
    """
    status = {}

    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_RED_FRAMETYPE)
    if frames.count() > 0:
        first_filename = frames.first().filename
        file_parts = split_filename(first_filename)
        if len(file_parts) == 8:
            root_dir = f"lcogt_{file_parts['tel_class']}_{file_parts['tel_serial']}_{file_parts['instrument']}_{file_parts['dayobs']}"
            logger.debug(f"Creating root directory {root_dir} and sub directories")
            for dir_name in ['', 'raw_data', 'cal_data', 'ddp_data']:
                dir_path = os.path.join(output_dir, 'lcogt_data', root_dir, dir_name)
                os.makedirs(dir_path, exist_ok=True)
                status[dir_name] = dir_path
        else:
            logger.warning(f"Could not decode filename: {first_filename}")
    return status

def find_fits_files(dirpath, prefix=None):

    if prefix is None:
        prefix = ''
    regex = re.compile('^'+prefix+'.*[fits|FITS|fit|FIT|Fits|fts|FTS|fits.fz]$')

    fits_files = {}
    # walk through directories underneath
    for root, dirs, files in os.walk(dirpath):

        # ignore .diagnostics directories
        if '.diagnostics' in root:
            continue

        # identify data frames
        filenames = sorted([s for s in files if re.match(regex, s)])

        if len(filenames) > 0:
            fits_files[root] = filenames

    return fits_files

def export_block_to_pds(input_dir, output_dir, block):

    status = create_dart_directories(output_dir, block)

    # transfer raw data
    # create PDS products for raw data
    # transfer cal data
    # create PDS products for cal data
    # transfer ddp data
    # create PDS products for ddp data
    return
