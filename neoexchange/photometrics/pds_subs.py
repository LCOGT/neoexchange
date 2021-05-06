import os
from glob import glob
from datetime import datetime, timedelta

from lxml import etree

from photometrics.catalog_subs import open_fits_catalog

def get_namespace(schema_filepath):

    tree = etree.parse(schema_filepath)
    root = tree.getroot()
    namespace = root.attrib.get('targetNamespace', '')

    return namespace

def pds_schema_mappings(schema_root, match_pattern='*.sch'):

    schema_files = glob(os.path.join(schema_root, match_pattern))
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
               schema_dict['namespace'] = namespace
           schemas[key] = schema_dict
        else:
            print("Unrecognized schema", schema_file)
    return schemas

def create_obs_product(schema_mappings):
    """Create a namespace mapping from the passed dict of schemas in
    <schema_mappings>. Returns a lxml.etree.Element of Product_Observational"""

    NS_map = {None: schema_mappings['PDS4::PDS']['namespace']}
    for key in schema_mappings.keys():
        ns_key = None
        if key != 'PDS4::PDS':
            ns_key = key.split('::')[1].lower()
            NS_map[ns_key] = schema_mappings[key]['namespace']

    obs_product = etree.Element('Product_Observational', nsmap=NS_map)

    return obs_product

def create_id_area(filename, mod_time=None):

    mod_time = mod_time or datetime.utcnow()
    id_area = etree.Element("Identification_Area")
    xml_elements = {'logical_identifier' : 'urn:nasa:pds:dart_teleobs:lcogt_cal:' + filename,
                    'version_id' : '1.0',
                    'title' : 'Las Cumbres Observatory Calibrated Image',
                    'information_model_version' : '1.15.0.0',  #XXX read from schema doc
                    'product_class' : 'Product_Observational'
                    }
    for k,v in xml_elements.items():
        etree.SubElement(id_area, k).text =v

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

    discp_area = etree.Element("Discipline_Area")

    # Create Display Settings discipline area
    disp_settings = create_display_settings(filename, nsmap)
    # Create Display Direction discipline area
    disp_dir = create_display_direction(nsmap)
    disp_settings.append(disp_dir)
    discp_area.append(disp_settings)

    return discp_area

def create_display_settings(filename, nsmap):

    etree.register_namespace("disp", nsmap['PDS4::DISP']['namespace'])
    disp_settings = etree.Element(etree.QName(nsmap['PDS4::DISP']['namespace'],"Display_Settings"))
    lir = etree.SubElement(disp_settings, "Local_Internal_Reference")
    etree.SubElement(lir, "local_identifier_reference").text = os.path.splitext(filename)[0]
    etree.SubElement(lir, "local_reference_type").text = "display_settings_to_array"

    return disp_settings

def create_display_direction(nsmap):

    disp_ns = nsmap['PDS4::DISP']['namespace']
    etree.register_namespace("disp", disp_ns)
    disp_direction = etree.Element(etree.QName(disp_ns,"Display_Direction"))
    etree.SubElement(disp_direction, etree.QName(disp_ns, "horizontal_display_axis")).text = "Sample"
    etree.SubElement(disp_direction, etree.QName(disp_ns, "horizontal_display_direction")).text = "Left to Right"
    etree.SubElement(disp_direction, etree.QName(disp_ns, "vertical_display_axis")).text = "Line"
    etree.SubElement(disp_direction, etree.QName(disp_ns, "vertical_display_direction")).text = "Bottom to Top"

    return disp_direction

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

def write_xml(filepath, xml_file, schema_root, mod_time=None):

    xmlEncoding = "UTF-8"
    schema_mappings = pds_schema_mappings(schema_root, '*.xsd')

    processedImage = create_obs_product(schema_mappings)

    header, table, cattype = open_fits_catalog(filepath)
    filename = os.path.basename(filepath)

    id_area = create_id_area(filename, mod_time)
    processedImage.append(id_area)

    # Add the Observation_Area
    obs_area = create_obs_area(header, filename)

    # Add Discipline Area
    discipline_area = create_discipline_area(header, filename, schema_mappings)
    obs_area.append(discipline_area)
    processedImage.append(obs_area)

    # Wrap in ElementTree to write out to XML file
    doc = etree.ElementTree(processedImage)
    doc.write(xml_file, pretty_print=True, standalone=None,
                xml_declaration=True, encoding=xmlEncoding)

    return
