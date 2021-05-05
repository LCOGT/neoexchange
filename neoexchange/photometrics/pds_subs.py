import os
from glob import glob

def pds_schema_mappings(schema_root):

    schema_files = glob(os.path.join(schema_root, '*.sch'))
    schemas = {}
    for schema_filepath in schema_files:
        schema_file = os.path.basename(schema_filepath)
        chunks = schema_file.split('_')
        if len(chunks) == 3 or len(chunks) == 4:
           key = "{}::{}".format(chunks[0], chunks[1])
           schemas[key] = schema_filepath
        else:
            print("Unrecognized schema", schema_file)
    return schemas
