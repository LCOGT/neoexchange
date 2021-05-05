import os
from glob import glob

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
