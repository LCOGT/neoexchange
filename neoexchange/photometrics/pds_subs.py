import os
from glob import glob
from datetime import datetime

from lxml import etree

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

def write_xml(filename, xml_file, schema_root, mod_time=None):

    xmlEncoding = "UTF-8"
    schema_mappings = pds_schema_mappings(schema_root, '*.xsd')
    processedImage = create_obs_product(schema_mappings)

    id_area = create_id_area(filename, mod_time)

    processedImage.append(id_area)

    # Wrap in ElementTree to write out to XML file
    doc = etree.ElementTree(processedImage)
    doc.write(xml_file, pretty_print=True, standalone=None,
                xml_declaration=True, encoding=xmlEncoding)

    return
