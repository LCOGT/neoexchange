import os
import re
import shutil
from glob import glob
from math import ceil
from datetime import datetime, timedelta

from lxml import etree
import astropy.units as u
from astropy.time import Time
from astropy.table import Column, Table
from astropy.coordinates import SkyCoord
from astropy.io.ascii.core import InconsistentTableError
from django.conf import settings

from core.models import Body, Frame
from core.archive_subs import lco_api_call, download_files
from astrometrics.ephem_subs import LCOGT_telserial_to_site_codes, LCOGT_domes_to_site_codes, get_sitepos
from photometrics.lightcurve_subs import *
from photometrics.catalog_subs import open_fits_catalog
from photometrics.external_codes import convert_file_to_crlf, funpack_file
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
            logger.warning("Unrecognized schema", schema_file)
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

def create_product_collection(schema_mappings):
    """Create a namespace mapping from the passed dict of schemas in
    <schema_mappings>. Returns a lxml.etree.Element of Product_Collection"""

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
    product_collection = etree.Element('Product_Collection', {qname: XSI_map}, nsmap=NS_map)

    return product_collection

def create_id_area(filename, model_version='1.15.0.0', collection_type='cal', mod_time=None):
    """Create a Identification Area from the passed <filename> (which is
    appended to the fixed 'urn:nasa:pds:dart_teleobs:lcogt_xyz:' URI), with
    'xyz' corresponding to the <collection_type> (one of 'cal (default), 'raw', 'ddp').
    The [model_version] (defaults to current '1.15.0.0') which is the schema version
    from the PDS schema containing `Identification_Area` (e.g. PDS4_PDS_1F00.xsd)
    and an optional modification time [mod_time] (defaults to UTC "now")
    Returns an etree.Element.
    Some information on filling this out taken from:
    https://sbnwiki.astro.umd.edu/wiki/Filling_Out_the_Identification_Area_Class
    """

    mod_time = mod_time or datetime.utcnow()

    proc_levels = { 'cal' : {'title' : 'Calibrated', 'level' : 'cal'},
                    'raw' : {'title' : 'Raw', 'level' : 'raw'},
                    'ddp' : {'title' : 'Derived Data Product', 'level' : 'ddp'},
                    'mbias' : {'title' : 'Master Bias', 'level' : 'cal'},
                    'mdark' : {'title' : 'Master Dark', 'level' : 'cal'},
                    'mflat' : {'title' : 'Master Flat', 'level' : 'cal'}
                  }

    id_area = etree.Element("Identification_Area")
    if filename is None:
        filename = ''
        product_type = 'Product_Collection'
        product_title = f'DART Telescopic Observations, Las Cumbres Observatory Network, Las Cumbres Observatory {proc_levels[collection_type]["title"]} Data Collection'
    else:
        filename = ':' + filename
        product_type = 'Product_Observational'
        suffix = ' Image'
        if collection_type == 'ddp':
            suffix = ''
        product_title = f'Las Cumbres Observatory {proc_levels[collection_type]["title"]}{suffix}'

    xml_elements = {'logical_identifier' : 'urn:nasa:pds:dart_teleobs:data_lcogt_' + proc_levels[collection_type]['level'] + filename,
                    'version_id' : '1.0',
                    'title' : product_title,
                    'information_model_version' : model_version,
                    'product_class' : product_type
                    }
    for k,v in xml_elements.items():
        etree.SubElement(id_area, k).text = v

    # If it's Product_Collection, add a Citation block
    if product_type == 'Product_Collection':
        citation_info = etree.SubElement(id_area, "Citation_Information")
        xml_elements = {'author_list' : 'T. Lister',
                        'publication_year' : mod_time.strftime("%Y"),
                        'keyword' : 'Las Cumbres',
                        'description' : f'DART Telescopic Observation Bundle, Las Cumbres Observatory {proc_levels[collection_type]["title"]} Data Collection'
                        }
        for k,v in xml_elements.items():
            etree.SubElement(citation_info, k).text = v

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


    if type(header) != list:
        headers = [header, ]
    else:
        headers = header

    discp_area = etree.Element("Discipline_Area")

    origin = headers[0].get('origin', '').rstrip()
    array_name_prefix = 'ccd'
    if origin == 'LCOGT':
        array_name_prefix = 'amp'
    for extn, extn_header in enumerate(headers):

        area_name = os.path.basename(filename)
        if len(headers) > 1:
            area_name = f"{array_name_prefix}{extn}_image"

        naxis = extn_header.get("naxis", 0)
        naxis1 = extn_header.get('naxis1', 0)
        naxis2 = extn_header.get('naxis2', 0)
        if naxis == 2 and naxis1 > 0 and naxis2 > 0:
            # Create Display Settings discipline area
            disp_settings = create_display_settings(area_name, nsmap)
            # Create Display Direction discipline area
            disp_direction = create_display_direction(nsmap, 'PDS4::DISP')
            disp_settings.append(disp_direction)
            discp_area.append(disp_settings)

    # Create Imaging area
    area_name = filename
    if len(headers) > 1:
        extn = 1
        area_name = f"{array_name_prefix}{extn}_image"
    img_area = create_image_area(headers[0], area_name, nsmap)
    discp_area.append(img_area)
    # Create Geometry area
    geom = create_geometry(area_name, nsmap)
    img_disp = create_imgdisp_geometry(area_name, nsmap)
    geom.append(img_disp)    
    # Create Display Direction discipline area
    disp_direction = create_display_direction(nsmap, 'PDS4::GEOM')
    img_disp.append(disp_direction)

    # Create Object Orientation
    obj_orient = create_obj_orient(headers[0], nsmap)
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

def create_image_area(header, filename, nsmap):
    """Create an img:Imaging area with img:Exposure and img:Optical_Filter
    subareas. The new area XML Element is returned"""

    img_ns = nsmap['PDS4::IMG']['namespace']
    etree.register_namespace("img", img_ns)
    img_area = etree.Element(etree.QName(img_ns,"Imaging"))
    lir = etree.SubElement(img_area, "Local_Internal_Reference")
    etree.SubElement(lir, "local_identifier_reference").text = os.path.splitext(filename)[0]
    etree.SubElement(lir, "local_reference_type").text = "imaging_parameters_to_image_object"
    # Create Image Exposure and Optical Filter sections
    img_exposure = create_image_exposure(header, nsmap)
    img_area.append(img_exposure)
    img_filter = create_image_filter(header, nsmap)
    img_area.append(img_filter)

    return img_area

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
    if obs_filter_bwidth:
        obs_filter_bwidth_str = "{:.1f}".format(obs_filter_bwidth.value)
        obs_filter_bwidth_unit = str(obs_filter_bwidth.unit)
        etree.SubElement(optical_filter, etree.QName(img_ns, "bandwidth"), attrib={'unit' : obs_filter_bwidth_unit}).text = obs_filter_bwidth_str

    obs_filter_cwave = map_filter_to_wavelength(obs_filter)
    if obs_filter_cwave:
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
    ra_val = header.get('CRVAL1', None)
    dec_val = header.get('CRVAL2', None)
    if not ra_val or not dec_val:
        # No WCS in primary header, try from RA/DEC
        try:
            center = SkyCoord(header['RA'], header['DEC'], unit=(u.hourangle, u.deg))
            ra_val = center.ra.deg
            dec_val = center.dec.deg
        except (ValueError, KeyError):
            logger.error("No WCS present and couldn't extract pointing from RA/DEC keywords (or not present")

    ra_str = "{:.6f}".format(ra_val)
    etree.SubElement(obj_orient, etree.QName(geom_ns, "right_ascension_angle"), attrib={'unit' : "deg"}).text = ra_str

    dec_str = "{:.6f}".format(dec_val)
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
    etree.SubElement(time_coords, "start_date_time").text = f'{shutter_open.strftime("%Y-%m-%dT%H:%M:%S.%f"):22.22s}Z'
    etree.SubElement(time_coords, "stop_date_time").text = f'{shutter_close.strftime("%Y-%m-%dT%H:%M:%S.%f"):22.22s}Z'

    invest_area = etree.SubElement(obs_area, "Investigation_Area")
    etree.SubElement(invest_area, "name").text = "Double Asteroid Redirection Test"
    etree.SubElement(invest_area, "type").text = "Mission"
    # Create Internal Reference subclass of Investigation Area
    int_reference = etree.SubElement(invest_area, "Internal_Reference")
    etree.SubElement(int_reference, "lid_reference").text = "urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test"
    etree.SubElement(int_reference, "reference_type").text = "data_to_investigation"
    # Create Observing System subclass of Observation Area
    tel_class = header.get('TELESCOP', 'XXX')[0:3]
    tel_class_descrip = tel_class.replace("m0", "m").replace("0m4", "0.4m")
    obs_system = etree.SubElement(obs_area, "Observing_System")
    obs_components = {
                        'Host' : { 'name' : 'Las Cumbres Observatory (LCOGT)',
                                   'lid_reference' : 'urn:nasa:pds:context:facility:observatory.las_cumbres',
                                   'reference_type' : 'is_facility'
                                 },
                        'Telescope' : { 'name' : f'Las Cumbres Global Telescope Network - {tel_class_descrip:} Telescopes',
                                        'lid_reference' : f"urn:nasa:pds:context:instrument_host:las_cumbres.{tel_class:}_telescopes",
                                        'reference_type' : 'is_telescope'
                                      },
                        'Instrument' : { 'name' : f'Las Cumbres {tel_class_descrip:} Telescopes - Sinistro Camera',
                                         'lid_reference' : f"urn:nasa:pds:context:instrument:las_cumbres.{tel_class:}_telescopes.sinistro",
                                         'reference_type' : 'is_instrument'
                                       }
                     }
    for component in obs_components:
        comp = etree.SubElement(obs_system, "Observing_System_Component")
        etree.SubElement(comp, "name").text = obs_components[component]['name']
        etree.SubElement(comp, "type").text = component
        description = f"The description for the {component.lower():} can be found in the document collection for this bundle."
        if component == 'Telescope':
            site_code = header.get('MPCCODE', None)
            if site_code is None:
                site_code = LCOGT_domes_to_site_codes(header.get('siteid', ''), header.get('encid', ''),  header.get('telid', ''))
            site_name = get_sitepos(site_code)[0]
            description = f"\n          LCOGT {header.get('TELESCOP',''):} Telescope\n          {site_name.replace('LCO', 'LCOGT'):}\n          {description:}"
        etree.SubElement(comp, "description").text = description
        int_reference = etree.SubElement(comp, "Internal_Reference")
        etree.SubElement(int_reference, "lid_reference").text = obs_components[component]['lid_reference']
        etree.SubElement(int_reference, "reference_type").text = obs_components[component]['reference_type']

    # Create Target Identification subclass
    target_id = etree.SubElement(obs_area, "Target_Identification")
    target_types = {'MINORPLANET' : 'Asteroid', 'COMET' : 'Comet' }
    target_name = header.get('object', '')
    # Try and find the Body associated with the name
    try:
        body = Body.objects.get(name=target_name)
        _, target_name = make_pds_asteroid_name(body)
    except Body.DoesNotExist:
        logger.warning(f"Body with name {target_name} does not exist")
    except Body.MultipleObjectsReturned:
        logger.warning(f"Multiple Bodies with name {target_name} exist")

    obstype = header.get('obstype', '').upper()
    target_type = target_types.get(header.get('srctype',''), 'Unknown')
    #                       OBSTYPE PDS NAME
    target_type_mapping = { 'BIAS' : 'BIAS',
                            'SKYFLAT' : 'FLAT FIELD',
                            'DARK' : 'DARK',
                            'BPM' : 'BPM'
                          }
    if obstype == 'BIAS' or obstype == 'DARK' or obstype == 'SKYFLAT' or obstype == 'BPM':
        target_name = target_type_mapping[obstype]
        target_type = 'Calibrator'
    etree.SubElement(target_id, "name").text = target_name
    etree.SubElement(target_id, "type").text = target_type

    return obs_area

def determine_first_last_times(filepath):
    """Iterates through all the FITS files in <filepath> to determine the
    times of the first and last frames, which are returned"""

    fits_files = find_fits_files(filepath)
    first_frame = datetime.max
    last_frame = datetime.min
    for directory, files  in fits_files.items():
        for fits_file in files:
            fits_filepath = os.path.join(directory, fits_file)
            header, table, cattype = open_fits_catalog(fits_filepath, header_only=True)
#            print(f"{fits_file}: {len(header)} {cattype}")
            if header:
                # Check if MEF header and only take primary header if so
                if 'MEF' in cattype:
                    index = 0
                    if 'RAW_MEF' not in cattype and fits_filepath.endswith('.fz'):
                        index = 1
                    header = header[index]
                start, stop = get_shutter_open_close(header)
                first_frame = min(first_frame, start)
                last_frame = max(last_frame, stop)

    return first_frame, last_frame

def determine_first_last_times_from_table(filepath, match_pattern='*_photometry.tab'):
    """Iterates through all the tables in <filepath> that match [match_pattern]
    to determine the times of the first and last frames, which are returned"""

    first_frame = last_frame = None
    photometry_files = sorted(glob(os.path.join(filepath, match_pattern)))
    if len(photometry_files) > 0:
        first_frame = datetime.max
        last_frame = datetime.min
        for table_file in photometry_files:
            try:
                table = Table.read(table_file, format='ascii', header_start=0, data_start=1)
            except InconsistentTableError:
                pass
            if table:
                first_frame = Time(table['julian_date'].min(), format='jd')
                first_frame = first_frame.datetime
                last_frame = Time(table['julian_date'].max(), format='jd')
                last_frame = last_frame.datetime

    return first_frame, last_frame

def determine_filename_from_table(table_file):

    filename = None
    if table_file and os.path.exists(table_file):
        try:
            table = Table.read(table_file, format='ascii', header_start=0, data_start=1)
        except InconsistentTableError:
            pass
        if table:
            filename = table['file'][0]

    return filename

def create_context_area(filepath, collection_type):
    """Creates the Context Area set of classes and returns an etree.Element with it.
    Documentation on filling this out taken from
    https://sbnwiki.astro.umd.edu/wiki/Filling_Out_the_Observation_Area_Classes
    """

    proc_levels = { 'cal' : 'Calibrated',
                    'raw' : 'Raw',
                    'ddp' : 'Derived'
                  }

    context_area = etree.Element("Context_Area")

    if collection_type == 'ddp':
        first_frametime, last_frametime = determine_first_last_times_from_table(filepath)
    else:
        first_frametime, last_frametime = determine_first_last_times(filepath)
    # Create Time_Coordinates sub element
    time_coords = etree.SubElement(context_area, "Time_Coordinates")
    etree.SubElement(time_coords, "start_date_time").text = f'{first_frametime.strftime("%Y-%m-%dT%H:%M:%S.%f"):22.22s}Z'
    etree.SubElement(time_coords, "stop_date_time").text = f'{last_frametime.strftime("%Y-%m-%dT%H:%M:%S.%f"):22.22s}Z'

    summary = etree.SubElement(context_area, "Primary_Result_Summary")
    etree.SubElement(summary, "purpose").text = "Science"
    etree.SubElement(summary, "processing_level").text = proc_levels.get(collection_type, "Unknown")

    invest_area = etree.SubElement(context_area, "Investigation_Area")
    etree.SubElement(invest_area, "name").text = "Double Asteroid Redirection Test"
    etree.SubElement(invest_area, "type").text = "Mission"
    # Create Internal Reference subclass of Investigation Area
    int_reference = etree.SubElement(invest_area, "Internal_Reference")
    etree.SubElement(int_reference, "lid_reference").text = "urn:nasa:pds:context:investigation:mission.double_asteroid_redirection_test"
    etree.SubElement(int_reference, "reference_type").text = "collection_to_investigation"

    frames_filepath = filepath
    prefix = '\S*e92'
    if collection_type == 'ddp':
        block_dir = os.path.basename(filepath)
        frames_filepath = os.path.realpath(os.path.join(filepath, '..', '..', 'data_lcogt_cal', block_dir))
    elif collection_type == 'raw':
        prefix = '\S*e00'
    fits_files = find_fits_files(frames_filepath, prefix)
    fits_filepath = os.path.join(frames_filepath, fits_files[frames_filepath][0])
    header, table, cattype = open_fits_catalog(fits_filepath, header_only=True)
    if type(header) != list:
        headers = [header, ]
    else:
        headers = header

    # Create Observing System subclass of Observation Area
    obs_system = etree.SubElement(context_area, "Observing_System")
    obs_components = {
                        'Host' : 'Las Cumbres Observatory (LCOGT)',
                        'Telescope' : 'LCOGT ' + headers[0].get('TELESCOP','') + ' Telescope',
                        'Instrument' : 'Sinistro Imager',
                     }
    for component in obs_components:
        comp = etree.SubElement(obs_system, "Observing_System_Component")
        etree.SubElement(comp, "name").text = obs_components[component]
        etree.SubElement(comp, "type").text = component
        description = f"The description for the {obs_components[component]} can be found in the document collection for this bundle."
        etree.SubElement(comp, "description").text = description

    # Create Target Identification subclass
    target_id = etree.SubElement(context_area, "Target_Identification")
    target_type = {'MINORPLANET' : 'Asteroid', 'COMET' : 'Comet' }
    etree.SubElement(target_id, "name").text = headers[0].get('object', '')
    etree.SubElement(target_id, "type").text = target_type.get(headers[0].get('srctype',''), 'Unknown')
    # Create Internal Reference subclass of Target Area
    int_reference = etree.SubElement(target_id, "Internal_Reference")
    etree.SubElement(int_reference, "lid_reference").text = "urn:nasa:pds:context:target:asteroid.didymos"
    etree.SubElement(int_reference, "reference_type").text = "collection_to_target"

    return context_area

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
    fits_block_size = 2880.0

    if type(header) != list:
        headers = [header, ]
    else:
        headers = header

    file_area_obs = etree.Element("File_Area_Observational")
    file_element = etree.SubElement(file_area_obs, "File")
    etree.SubElement(file_element, "file_name").text = os.path.basename(filename)
    obstype = headers[0].get('obstype', 'expose').upper()
    comment = "Calibrated LCOGT image file"
    if obstype == 'BIAS' or obstype == 'DARK' or obstype == 'SKYFLAT':
        comment = f"Median combined stack of {obstype.lower()} images. Used in calibration pipeline to generate the calibrated image data."
    elif obstype == 'BPM':
         comment = f"Bad Pixel Mask image. Used in calibration pipeline to generate the calibrated image data."
    elif obstype == "EXPOSE" and headers[0].get('rlevel', 0) == 0:
        comment = "Raw LCOGT image file"

    origin = headers[0].get('origin', '').rstrip()
    array_name_prefix = 'ccd'
    if origin == 'LCOGT':
        etree.SubElement(file_element, "comment").text = comment
        array_name_prefix = 'amp'

    header_offset = 0
    for extn, extn_header in enumerate(headers):
        logger.debug(f"Extn #{extn}, {len(extn_header)} records", end='')
        header_element = etree.SubElement(file_area_obs, "Header")
        # Compute size of header from list length+1 (missing END card)
        header_size_bytes = (len(extn_header)+1)*80
        # Actual size is rounded to nearest multiple of FITS block size (2880 bytes)
        header_size_blocks = int(ceil(header_size_bytes/fits_block_size) * fits_block_size)
        header_size = "{:d}".format(header_size_blocks)

        image_size_bytes = extn_header.get('naxis1', 0) * extn_header.get('naxis2', 0) * int(abs(extn_header['bitpix'])/8)
        image_size_blocks = int(ceil(image_size_bytes/fits_block_size) * fits_block_size)
        image_size = "{:d}".format(max(header_size_blocks,image_size_blocks))

        logger.debug(f"   header_size={header_size_blocks} image_size={image_size_blocks}")
        header_name = "main_header"
        if extn >= 1:
            header_name = f"{array_name_prefix}{extn}_header"

        etree.SubElement(header_element, "name").text = header_name
        etree.SubElement(header_element, "offset", attrib={"unit" : "byte"}).text = str(header_offset)
        etree.SubElement(header_element, "object_length", attrib={"unit" : "byte"}).text = image_size
        etree.SubElement(header_element, "parsing_standard_id").text = "FITS 3.0"

        header_offset += header_size_blocks

        naxis = extn_header.get("naxis", 0)
        naxis1 = extn_header.get('naxis1', 0)
        naxis2 = extn_header.get('naxis2', 0)
        if naxis == 2 and naxis1 > 0 and naxis2 > 0:
            array_2d = etree.SubElement(file_area_obs, "Array_2D_Image")
            local_id = os.path.splitext(filename)[0]
            if extn >= 1:
                local_id = f"{array_name_prefix}{extn}_image"
            etree.SubElement(array_2d, "local_identifier").text = local_id

            # Compute size of header from list length+1 (missing END card)
            header_size_bytes = (len(extn_header)+1)*80
            # Actual size is rounded to nearest multiple of FITS block size (2880 bytes)
            header_size_blocks = int(ceil(header_size_bytes/fits_block_size) * fits_block_size)
            header_size = "{:d}".format(header_size_blocks)

            image_size_bytes = naxis1 * naxis2 * int(abs(extn_header['bitpix'])/8)
            image_size_blocks = int(ceil(image_size_bytes/fits_block_size) * fits_block_size)
            image_size = "{:d}".format(image_size_blocks)

            etree.SubElement(array_2d, "offset", attrib={"unit" : "byte"}).text = str(header_offset)
            etree.SubElement(array_2d, "axes").text = str(naxis)
            etree.SubElement(array_2d, "axis_index_order").text = "Last Index Fastest"
            header_offset += image_size_blocks

            elem_array = etree.SubElement(array_2d, "Element_Array")
            etree.SubElement(elem_array, "data_type").text = PDS_types.get(extn_header['BITPIX'])
            # Add scaling_factor and value_offset if BSCALE and BZERO are present
            bscale = extn_header.get('bscale', 1)
            bzero = extn_header.get('bzero', None)
            if bscale and bzero:
                etree.SubElement(elem_array, "scaling_factor").text = str(bscale)
                etree.SubElement(elem_array, "value_offset").text = str(bzero)

            axis_mapping = {'Line' : 'NAXIS2', 'Sample' : 'NAXIS1'}
            for sequence_number, axis_name in enumerate(axis_mapping, start=1):
                axis_array = etree.SubElement(array_2d, "Axis_Array")
                etree.SubElement(axis_array, "axis_name").text = axis_name
                etree.SubElement(axis_array, "elements").text = str(extn_header[axis_mapping[axis_name]])
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

    fields = {'file' : { 'field_location' : 2, 'data_type' : 'ASCII_String', 'field_length' : 36, 'description' : 'File name of the calibrated image where data were measured.' },
              'julian_date' : { 'field_location' : 40, 'data_type' : 'ASCII_Real', 'field_length' : 15, 'description' : 'UTC Julian date of the exposure midtime' },
              'mag' : { 'field_location' : 56, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : 'Calibrated PanSTARRs r-band apparent magnitude of asteroid' },
              'sig' : { 'field_location' : 66, 'data_type' : 'ASCII_Real', 'field_length' : 6, 'description' : '1-sigma error on the apparent magnitude' },
              'ZP'  : { 'field_location' : 73, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : 'Calibrated zero point magnitude in PanSTARRs r-band' },
              'ZP_sig' : { 'field_location' : 83, 'data_type' : 'ASCII_Real', 'field_length' : 6, 'description' : '1-sigma error on the zero point magnitude' },
              'inst_mag' : { 'field_location' : 91, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : 'instrumental magnitude of asteroid' },
              'inst_sig' : { 'field_location' : 101, 'data_type' : 'ASCII_Real', 'field_length' : 8, 'description' : '1-sigma error on the instrumental magnitude' },
              'SExtractor_flag' : { 'field_location' : 111, 'data_type' : 'ASCII_Integer', 'field_length' : 15, 'description' : 'Flags associated with the Source Extractor photometry measurements. See source_extractor_flags.txt in the documents folder for this archive for more detailed description.' },
              'aprad' : { 'field_location' : 127, 'data_type' : 'ASCII_Real', 'field_length' : 6, 'description' : 'radius in pixels of the aperture used for the photometry measurement' }
              }
    file_area_table = etree.Element("File_Area_Observational")
    file_element = etree.SubElement(file_area_table, "File")
    etree.SubElement(file_element, "file_name").text = os.path.basename(filename)
    etree.SubElement(file_element, "comment").text = 'photometry summary table'

    with open(filename, 'rb') as table_fh:
        table = table_fh.readlines()
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
    etree.SubElement(record_element, "fields").text = str(10)
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

def create_reference_list(collection_type):
    """Create a Reference List section
    """

    reference_list = etree.Element("Reference_List")
    # Create Internal Reference subclass of Target Area
    int_reference = etree.SubElement(reference_list, "Internal_Reference")
    etree.SubElement(int_reference, "lid_reference").text = "urn:nasa:pds:dart_teleobs:documentation_lcogt:las_cumbres_dart_uncalibrated_calibrated_sis"
    etree.SubElement(int_reference, "reference_type").text = "collection_to_document"
    etree.SubElement(int_reference, "comment").text = "Reference is to the Las Cumbres DART Uncalibrated, Calibrated SIS document which describes the data products in this collection."

    return reference_list

def write_product_label_xml(filepath, xml_file, schema_root, mod_time=None):
    """Create a PDS4 XML product label in <xml_file> from the FITS file
    pointed at by <filepath>. This used the PDS XSD and Schematron schemas located
    in <schema_root> directory. Optionally a different modification `datetime` [mod_time]
    can be passed which is used in `create_id_area()`
    <schema_root> should contain the main PDS common and Display, Imaging and
    Geometry Discipline Dictionaries (although this is not checked for)
    """

    proc_levels = { 'EXPOSE' : 'cal',
                    'BIAS' : 'mbias',
                    'DARK' : 'mdark',
                    'SKYFLAT' : 'mflat'
                  }

    xmlEncoding = "UTF-8"
    proc_level = ''
    if '.fit' not in filepath and 'photometry' in filepath:
        proc_level = 'ddp'

    schemas_needed = '*.xsd'
    if proc_level == 'ddp':
        # DDP/ASCII photometry files only need base schema
        schemas_needed = 'PDS4_PDS*.xsd'
    schema_mappings = pds_schema_mappings(schema_root, schemas_needed)

    processedImage = create_obs_product(schema_mappings)

    if proc_level == 'ddp':
        filename = os.path.basename(filepath)
        chunks = filename.split('_')
        tel_class = chunks[1]
        tel_serialnum = chunks[2]
        site_code = ''
        name_mapping = {'didymos' : '65803 Didymos'}
        first_frame, last_frame = determine_first_last_times_from_table(os.path.dirname(filepath))
        first_filename = determine_filename_from_table(filepath)
        if first_filename:
            tel_class = first_filename[3:6]
            tel_serialnum = first_filename[6:8]
            site_code = LCOGT_telserial_to_site_codes(tel_class+tel_serialnum)
        headers = [{ 'TELESCOP' : tel_class + '-' + tel_serialnum,
                     'MPCCODE'  : site_code,
                     'object'   : name_mapping.get(chunks[5], chunks[5]),
                     'srctype'  : 'MINORPLANET',
                     'DATE-OBS' : first_frame.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                     'UTSTOP'   : last_frame.strftime("%H:%M:%S.%f")
                 },]

    else:
        header, table, cattype = open_fits_catalog(filepath)
        filename = os.path.basename(filepath)
        if type(header) != list:
            headers = [header, ]
        else:
            headers = header

        proc_level = proc_levels.get(headers[0].get('obstype', 'expose').upper(), 'cal')
        if headers[0].get('rlevel', 0) == 0:
            proc_level = 'raw'
    id_area = create_id_area(filename, schema_mappings['PDS4::PDS']['version'], proc_level, mod_time)
    processedImage.append(id_area)

    # Add the Observation_Area
    obs_area = create_obs_area(headers[0], filename)

    if proc_level != 'ddp':
        # Add Discipline Area
        discipline_area = create_discipline_area(headers, filename, schema_mappings)
        obs_area.append(discipline_area)
    processedImage.append(obs_area)

    # Create File_Area_Observational
    if proc_level == 'ddp':
        file_area = create_file_area_table(filepath)
    else:
        file_area = create_file_area_obs(headers, filename)
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
    if proc_level == 'ddp':
        preamble = b'''<?xml-model href="https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1F00.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>'''

    doc = preamble + etree.tostring(processedImage)
    tree = etree.ElementTree(etree.fromstring(doc))
    tree.write(xml_file, pretty_print=True, standalone=None,
                xml_declaration=True, encoding=xmlEncoding)

    return

def write_product_collection_xml(filepath, xml_file, schema_root, mod_time=None):
    """Create a PDS4 XML product collection in <xml_file> from the FITS files
    pointed at by <filepath>. This used the PDS XSD and Schematron schemas located
    in <schema_root> directory. Optionally a different modification `datetime` [mod_time]
    can be passed which is used in `create_id_area()`
    <schema_root> should contain the main PDS common Discipline Dictionaries
    (although this is not checked for)
    """

    xmlEncoding = "UTF-8"
    schema_mappings = pds_schema_mappings(schema_root, '*.xsd')

    schemas_needed = {'PDS4::PDS' : schema_mappings['PDS4::PDS']}
    productCollection = create_product_collection(schemas_needed)


    if '_cal' in xml_file:
        collection_type = 'cal'
    elif '_raw' in xml_file:
        collection_type = 'raw'
    elif '_ddp' in xml_file:
        collection_type = 'ddp'
    else:
        logger.error("Unknown collection type")
        return False

    id_area = create_id_area(None, schema_mappings['PDS4::PDS']['version'], collection_type, mod_time)
    productCollection.append(id_area)

    # Add Context Area
    context_area = create_context_area(filepath, collection_type)
    productCollection.append(context_area)

    # Add Reference List
    ref_list = create_reference_list(collection_type)
    productCollection.append(ref_list)

    # Add Collection
    collection = etree.SubElement(productCollection, "Collection")
    etree.SubElement(collection, "collection_type").text = "Data"

    # Create File_Area_Inventory
    file_area = create_file_area_inv(xml_file.replace('.xml', '.csv'), mod_time)
    productCollection.append(file_area)

    # Wrap in ElementTree to write out to XML file
    preambles = {'PDS4::PDS' : b'''<?xml-model href="https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1F00.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>''',
                'PDS4::DISP' : b'''<?xml-model href="https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1F00_1500.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>''',
                'PDS4::IMG' : b'''<?xml-model href="https://pds.nasa.gov/pds4/img/v1/PDS4_IMG_1F00_1810.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>''',
                'PDS4::GEOM' : b'''<?xml-model href="https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1F00_1910.sch"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>'''
                }
    preamble = b''
    for schema in schemas_needed.keys():
        preamble += preambles[schema] + b'\n'
    doc = preamble + etree.tostring(productCollection)
    tree = etree.ElementTree(etree.fromstring(doc))
    tree.write(xml_file, pretty_print=True, standalone=None,
                xml_declaration=True, encoding=xmlEncoding)

    return True

def create_pds_labels(procdir, schema_root, match='.*e92'):
    """Create PDS4 product labels for all frames matching the [match] regexp pattern
    (defaults to processed (e92) FITS files) in <procdir>. To search for and
    process ASCII photometry files, use `match='*photometry.tab'`
    The PDS4 schematron and XSD files in <schema_root> are used in generating
    the XML file.
    A list of created PDS4 label filenames (with paths) is returned; this list
    may be zero length.
    """

    xml_labels = []
    full_procdir = os.path.abspath(os.path.expandvars(procdir))
    if 'photometry.tab' in match:
        photometry_files = sorted(glob(os.path.join(full_procdir, match)))
        files_to_process = {full_procdir : photometry_files}
    else:
        files_to_process = find_fits_files(procdir, match)

    for directory, fits_files in files_to_process.items():
        for fits_file in fits_files:
            fits_filepath = os.path.join(directory, fits_file)
            extn = os.path.splitext(fits_file)[1]
            if extn == '.fz':
                extn = os.path.splitext(os.path.splitext(fits_file)[0])
            xml_file = fits_filepath.replace(extn, '.xml').replace('.fz', '')
            write_product_label_xml(fits_filepath, xml_file, schema_root)
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

    return name_parts

def create_dart_directories(output_dir, block):
    """Creates the directory structures in <output_dir> needed for exporting a
    Block <block> of light curve data to DART. Creates a directory tree as follows:
    └── <output_dir>
        └── lcogt_data
            ├── data_lcogt_cal
            │   └── lcogt_1m0_01_fa11_20211013
            ├── data_lcogt_ddp
            │   └── lcogt_1m0_01_fa11_20211013
            ├── data_lcogt_raw
            │   └── lcogt_1m0_01_fa11_20211013
    """
    status = {}

    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_RED_FRAMETYPE)
    if frames.count() > 0:
        first_filename = frames.last().filename
        file_parts = split_filename(first_filename)
        if len(file_parts) == 8:
            block_dir = f"lcogt_{file_parts['tel_class']}_{file_parts['tel_serial']}_{file_parts['instrument']}_{file_parts['dayobs']}"
            logger.debug(f"Creating root directories and  {block_dir} sub directories")
            for dir_key, dir_name in zip(['raw_data', 'cal_data', 'ddp_data'], ['data_lcogt_raw', 'data_lcogt_cal', 'data_lcogt_ddp']):
                dir_path = os.path.join(output_dir, dir_name, block_dir)
                os.makedirs(dir_path, exist_ok=True)
                status[dir_key] = dir_path
            status['root'] = output_dir
        else:
            logger.warning(f"Could not decode filename: {first_filename}")
    return status

def find_fits_files(dirpath, prefix=None):
    """Recursively searches directories in <dirpath> for FITS files.
    [prefix] is added into the regexp, matching from the start so to look for
    e.g. just 'e92' files, set prefix='\S*e92' to match any amount of characters
    and then 'e92'
    Returns a dict of paths as the key with a list of FITS files as the value for
    that key. Directories or sub-directories with no FITS files are not included
    in the returned dict."""

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

def find_related_frames(block):
    """Finds the unique set of related frames (raw and calibrations) for the Frames
    belonging to the passed Block <block>.
    Returns a dictionary with a reduction level key of `''` and then a list of
    dictionaries of the response from LCO Science Archive. (This is of a form
    suitable to given to core.archive_subs.download_files()
    """

    related_frames = {'': []}
    red_frame_ids = Frame.objects.filter(block=block, filename__contains='1m0', frametype=Frame.BANZAI_RED_FRAMETYPE).values_list('frameid', flat=True)
    # List for frame id's seen
    frame_ids = []
    for red_frame_id in red_frame_ids:
        archive_url = f"{settings.ARCHIVE_API_URL}frames/{str(red_frame_id)}/related/"
        data = lco_api_call(archive_url)
        for frame in data:
            logger.debug(f"{frame['id']}: {frame['filename']}")
            if frame['id'] not in frame_ids:
                logger.debug("New frame")
                frame_ids.append(frame['id'])
                related_frames[''].append(frame)
            else:
                logger.debug("Already know this frame")

    return related_frames

def transfer_files(input_dir, files, output_dir, dbg=False):
    files_copied = []

    for file in files:
        action = 'Copying'
        if 'e00' in file:
            action = 'Downloading'
            #input_dir = 'Science Archive'

        if dbg: print(f"{action} {file} from {input_dir} -> {output_dir}")
        input_filepath = os.path.join(input_dir, file)
        output_filepath = os.path.join(output_dir, file)
        if os.path.exists(input_filepath):
            if os.path.exists(output_filepath) is False and os.path.exists(output_filepath.replace('.fz', '')) is False:
                filename = shutil.copy(input_filepath, output_filepath)
                if output_filepath.endswith('.fz'):
                    if dbg: print("funpack file")
                    status = funpack_file(output_filepath)
                if dbg: print(action, filename)
            else:
                if dbg: print("Already exists")
            files_copied.append(file.replace('.fz', ''))
        else:
            logger.error(f"Input file {file} in {input_dir} not readable")

    return files_copied

def create_pds_collection(output_dir, input_dir, files, collection_type, schema_root, mod_time=None):
    """Creates a PDS Collection (.csv and .xml) files with the names
    'collection_<collection_type>.{csv,xml}' in <output_dir> from the list
    of files (without paths) passed as [files] which are located in <input_dir>
    <collection_type> should be one of:
    * 'cal' (calibrated)
    * 'raw'
    * 'ddp (derived data product)
    CSV file entries are of the form:
    P,urn:nasa:pds:dart_teleobs:data_lcogt_<collection_type>:[filename]::1.0
    """

    # PDS4 Agency identifier
    prefix = 'urn:nasa:pds'
    # PDS4 Bundle id
    bundle_id = 'dart_teleobs'
    # PDS4 Collection id
    collection_id = f'data_lcogt_{collection_type}'
    product_version = '1.0'
    product_column = Column(['P'] * len(files))
    urns = [f'{prefix}:{bundle_id}:{collection_id}:{x}::{product_version}' for x in files]
    urns_column = Column(urns)
    csv_table = Table([product_column, urns_column])
    csv_filename = os.path.join(output_dir, collection_id, f'collection_data_lcogt_{collection_type}.csv')
    # Have to use the 'no_header' Table type rather than 'csv' as there seems
    # to be no way to suppress the header
    csv_table.write(csv_filename, format='ascii.no_header', delimiter=',')

    # Write XML file after CSV file is generated (need to count records)
    xml_filename = csv_filename.replace('.csv', '.xml')
    print(xml_filename)
    status = write_product_collection_xml(input_dir, xml_filename, schema_root, mod_time)

    return csv_filename, xml_filename

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
        if len(chunks) == 2 and chunks[0].isdigit():
            pds_name = f"({chunks[0]}) {chunks[1]}"
        else:
            pds_name = bodyname

    return filename, pds_name

def create_dart_lightcurve(input_dir, output_dir, block, match='photometry_*.dat'):
    """Creates a DART-format lightcurve file from the photometry file and LOG in
    <input_dir>, outputting to <output_dir>. Block <block> is used find the directory
    for the photometry file
    """

    output_lc_filepath = None
    frames = Frame.objects.filter(block=block, frametype=Frame.BANZAI_RED_FRAMETYPE)
    if frames.count() > 0:
        first_frame = frames.last()
        first_filename = first_frame.filename
        file_parts = split_filename(first_filename)
        if len(file_parts) == 8:
            root_dir = input_dir
            photometry_files = sorted(glob(os.path.join(root_dir, match)))
            if len(photometry_files) == 0:
                root_dir = os.path.join(input_dir, file_parts['dayobs'])
                photometry_files = sorted(glob(os.path.join(root_dir, match)))
            for photometry_file in photometry_files:
                log_file = os.path.join(os.path.dirname(photometry_file), 'LOG')
                table = read_photompipe_file(photometry_file)
                aper_radius = extract_photompipe_aperradius(log_file)
                if table and aper_radius:
                    phot_filename, pds_name = make_pds_asteroid_name(block.body)
                    # Format for LC files: 'lcogt_<site>_<inst.>_<YYYYMMDD>_<request #>_<astname#>_photometry.txt'
                    output_lc_file = f"lcogt_{file_parts['site']}_{file_parts['instrument']}_{file_parts['dayobs']}_{block.request_number}_{phot_filename}_photometry.tab"
                    output_lc_filepath = os.path.join(output_dir, output_lc_file)
                    write_dartformat_file(table, output_lc_filepath, aper_radius)
        else:
            logger.warning(f"Could not decode filename: {first_filename}")

    return output_lc_filepath

def export_block_to_pds(input_dir, output_dir, block, schema_root, skip_download=False, verbose=True):

    csv_files = []
    xml_files = []
    paths = create_dart_directories(output_dir, block)
    if verbose: print("input_dir ", input_dir)
    if verbose: print("output_dir", output_dir)
    for k,v in paths.items():
        if verbose: print(f"{k:>8s}:  {v}")

    # Find and download related frames (raw and calibration frames)
    if skip_download is True:
        pass
    else:
        if verbose: print("Find and downloading related frames")
        related_frames = find_related_frames(block)
        dl_frames = download_files(related_frames, input_dir, verbose)

    # transfer raw data
    if verbose: print("Finding raw frames")
    raw_files = find_fits_files(input_dir, '\S*e00')
    if len(raw_files) == 0:
        logger.error("No raw files found")
        return [], []
    # create PDS products for raw data
    if verbose: print("Transferring/uncompressing raw frames")
    for root, files in raw_files.items():
        sent_files = transfer_files(root, files, paths['raw_data'])

    if verbose: print("Creating raw PDS collection")
    raw_csv_filename, raw_xml_filename = create_pds_collection(paths['root'], paths['raw_data'], sent_files, 'raw', schema_root)
    # Convert csv file to CRLF endings required by PDS
    status = convert_file_to_crlf(raw_csv_filename)
    csv_files.append(raw_csv_filename)
    xml_files.append(raw_xml_filename)
    # Create PDS labels for raw data
    if verbose: print("Creating raw PDS labels")
    xml_labels = create_pds_labels(paths['raw_data'], schema_root, match='\S*e00')
    xml_files += xml_labels

    # transfer cal data
    # Set pattern to '<any # of chars>e92.' (literal '.' rather than normal regexp
    # meaning of "any character") to avoid picking up e92-ldac files
    cal_files = find_fits_files(input_dir, '\S*e92\.')
    if len(cal_files) == 0:
        logger.error("No cal files found")
        return [], []
    if verbose: print("Transferring calibrated frames")
    for root, files in cal_files.items():
        sent_files = transfer_files(root, files, paths['cal_data'], dbg=verbose)
    # transfer master calibration files
    if verbose: print("Transferring master calibration frames")
    calib_files = find_fits_files(input_dir, '\S*-(bias|bpm|dark|skyflat)')
    for root, files in calib_files.items():
        sent_files += transfer_files(root, files, paths['cal_data'], dbg=verbose)
    # create PDS products for cal data
    if verbose: print("Creating cal PDS collection")
    cal_csv_filename, cal_xml_filename = create_pds_collection(paths['root'], paths['cal_data'], sent_files, 'cal', schema_root)
    # Convert csv file to CRLF endings required by PDS
    status = convert_file_to_crlf(cal_csv_filename)
    csv_files.append(cal_csv_filename)
    xml_files.append(cal_xml_filename)

    # Create PDS labels for cal data
    if verbose: print("Creating cal PDS labels")
    xml_labels = create_pds_labels(paths['cal_data'], schema_root, match='.*[bpm|bias|dark|flat|e92]*')
    xml_files += xml_labels

    # transfer ddp data
    dart_lc_file = create_dart_lightcurve(input_dir, paths['ddp_data'], block)
    if dart_lc_file is None:
        logger.error("No light curve file found")
        return [], []
    lc_files = [os.path.basename(dart_lc_file),]
    # Convert csv file to CRLF endings required by PDS
    status = convert_file_to_crlf(dart_lc_file)
    # create PDS products for ddp data
    ddp_csv_filename, ddp_xml_filename = create_pds_collection(paths['root'], paths['ddp_data'], lc_files, 'ddp', schema_root)
    # Convert csv file to CRLF endings required by PDS
    status = convert_file_to_crlf(ddp_csv_filename)
    csv_files.append(ddp_csv_filename)
    xml_files.append(ddp_xml_filename)

    # Create PDS labels for ddp data
    if verbose: print("Creating ddp PDS labels")
    xml_labels = create_pds_labels(paths['ddp_data'], schema_root, match='*photometry.tab')
    xml_files += xml_labels

    return csv_files, xml_files
