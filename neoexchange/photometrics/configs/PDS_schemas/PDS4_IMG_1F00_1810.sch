<?xml version="1.0" encoding="UTF-8"?>
  <!-- PDS4 Schematron for Name Space Id:img  Version:1.8.1.0 - Wed Oct 14 02:55:04 UTC 2020 -->
  <!-- Generated from the PDS4 Information Model Version 1.15.0.0 - System Build 11a -->
  <!-- *** This PDS4 schematron file is an operational deliverable. *** -->
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt2">

  <sch:title>Schematron using XPath 2.0</sch:title>

  <sch:ns uri="http://www.w3.org/2001/XMLSchema-instance" prefix="xsi"/>
  <sch:ns uri="http://pds.nasa.gov/pds4/pds/v1" prefix="pds"/>
  <sch:ns uri="http://pds.nasa.gov/pds4/img/v1" prefix="img"/>

		   <!-- ================================================ -->
		   <!-- NOTE:  There are two types of schematron rules.  -->
		   <!--        One type includes rules written for       -->
		   <!--        specific situations. The other type are   -->
		   <!--        generated to validate enumerated value    -->
		   <!--        lists. These two types of rules have been -->
		   <!--        merged together in the rules below.       -->
		   <!-- ================================================ -->
  <sch:pattern>
    <sch:rule context="//img:Color_Filter_Array">
      <sch:assert test="img:color_filter_array_state = ('Encoded', 'Decoded', 'No CFA')">
        IMG:error:img:color_filter_array_state_check: img:color_filter_array_state must be equal to one of the following values: 
        'Encoded', 'Decoded', 'No CFA'.
      </sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Color_Processing">
      <sch:assert test="count(child::*) > 0">
        IMG:error:color_processing_child_check: img:color must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Commanded_Parameters">
      <sch:assert test="count(child::*) > 0">
        IMG:error:commanded_params_child_check: img:Commanded_Parameters must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Detector">
      <sch:assert test="count(child::*) > 0">
        IMG:error:detector_params_child_check: img:Detector must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Downsampling">
      <sch:assert test="count(child::*) > 0">
        IMG:error:downsampling_child_check: img:Downsampling must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Exposure">
      <sch:assert test="count(child::*) > 0">
        IMG:error:exposure_child_check: img:Exposure must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Focus">
      <sch:assert test="count(child::*) > 0">
        IMG:error:focus_child_check: img:Focus must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Focus_Stack">
      <sch:assert test="count(child::*) > 0">
        IMG:error:focus_stack_child_check: img:Focus_Stack must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Frame">
      <sch:assert test="count(child::*) > 0">
        IMG:error:frame_child_check: img:Frame must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:ICER_Parameters">
      <sch:assert test="(count(img:Image_Compression_Segment) = img:segment_count) or (count(img:Image_Compression_Segment) = 0)">
        IMG:error:icer_comprs_segment_check: img:ICER_Parameters/img:segment_count must match the number of img:Image_Compression_Segment classes.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:ICER_Parameters">
      <sch:assert test="count(child::*) > 0">
        IMG:error:icer_params_child_check: img:ICER_Parameters must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Imaging">
      <sch:assert test="count(child::*) > 0">
        IMG:error:imaging_child_check: img:Imaging class must contain at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Color_Filter_Array">
      <sch:assert test="if (img:active_flag) then img:active_flag = ('true', 'false') else true()">
        The attribute img:active_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Color_Filter_Array/img:color_filter_array_state">
      <sch:assert test=". = ('Decoded', 'Encoded', 'No CFA')">
        The attribute img:color_filter_array_state must be equal to one of the following values 'Decoded', 'Encoded', 'No CFA'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Color_Filter_Array/img:color_filter_array_type">
      <sch:assert test=". = ('Bayer RGGB', 'None')">
        The attribute img:color_filter_array_type must be equal to one of the following values 'Bayer RGGB', 'None'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Companding">
      <sch:assert test="if (img:active_flag) then img:active_flag = ('true', 'false') else true()">
        The attribute img:active_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
      <sch:assert test="if (img:early_scaling) then img:early_scaling = ('true', 'false') else true()">
        The attribute img:early_scaling must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Companding/img:companding_state">
      <sch:assert test=". = ('Companded', 'Expanded', 'None')">
        The attribute img:companding_state must be equal to one of the following values 'Companded', 'Expanded', 'None'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Detector">
      <sch:assert test="if (img:bad_pixel_replacement_flag) then img:bad_pixel_replacement_flag = ('true', 'false') else true()">
        The attribute img:bad_pixel_replacement_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
      <sch:assert test="if (img:early_image_return) then img:early_image_return = ('true', 'false') else true()">
        The attribute img:early_image_return must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Detector/img:detector_to_image_flip">
      <sch:assert test=". = ('Horizontal', 'None', 'Vertical')">
        The attribute img:detector_to_image_flip must be equal to one of the following values 'Horizontal', 'None', 'Vertical'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Detector/img:detector_to_image_rotation">
      <sch:assert test="@unit = ('arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad')">
        The attribute @unit must be equal to one of the following values 'arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Detector/img:instrument_idle_timeout">
      <sch:assert test="@unit = ('day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr')">
        The attribute @unit must be equal to one of the following values 'day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Detector/img:readout_rate">
      <sch:assert test="@unit = ('GHz', 'Hz', 'MHz', 'THz', 'kHz', 'mHz')">
        The attribute @unit must be equal to one of the following values 'GHz', 'Hz', 'MHz', 'THz', 'kHz', 'mHz'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Device_Current/img:current_value">
      <sch:assert test="@unit = ('A', 'mA')">
        The attribute @unit must be equal to one of the following values 'A', 'mA'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Device_Temperature/img:temperature_value">
      <sch:assert test="@unit = ('K', 'degC')">
        The attribute @unit must be equal to one of the following values 'K', 'degC'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Device_Voltage/img:voltage_value">
      <sch:assert test="@unit = ('V', 'mV')">
        The attribute @unit must be equal to one of the following values 'V', 'mV'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Exposure/img:exposure_duration">
      <sch:assert test="@unit = ('day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr')">
        The attribute @unit must be equal to one of the following values 'day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Exposure/img:exposure_type">
      <sch:assert test=". = ('Auto', 'Auto Last', 'Manual', 'Manual Last', 'None', 'Test')">
        The attribute img:exposure_type must be equal to one of the following values 'Auto', 'Auto Last', 'Manual', 'Manual Last', 'None', 'Test'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Focus/img:best_focus_distance">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Focus/img:focus_distance">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Focus/img:maximum_focus_distance">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Focus/img:minimum_focus_distance">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Frame">
      <sch:assert test="if (img:product_flag) then img:product_flag = ('true', 'false') else true()">
        The attribute img:product_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Frame/img:frame_id">
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Frame/img:frame_type_name">
      <sch:assert test=". = ('Mono', 'Stereo')">
        The attribute img:frame_type_name must be equal to one of the following values 'Mono', 'Stereo'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:High_Dynamic_Range">
      <sch:assert test="if (img:active_flag) then img:active_flag = ('true', 'false') else true()">
        The attribute img:active_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:High_Dynamic_Range/img:hdr_acquisition_mode">
      <sch:assert test=". = ('Multiframe', 'None', 'Piecewise', 'Single')">
        The attribute img:hdr_acquisition_mode must be equal to one of the following values 'Multiframe', 'None', 'Piecewise', 'Single'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:High_Dynamic_Range_Exposure/img:exposure_duration">
      <sch:assert test="@unit = ('day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr')">
        The attribute @unit must be equal to one of the following values 'day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:High_Dynamic_Range_Exposure/img:exposure_time_delta">
      <sch:assert test="@unit = ('day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr')">
        The attribute @unit must be equal to one of the following values 'day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Filter/img:filter_window_line">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Filter/img:filter_window_sample">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Filter/img:max_filter_window_line">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Filter/img:max_filter_window_sample">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Filter/img:min_filter_window_line">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Filter/img:min_filter_window_sample">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Mask_File/img:horizon_mask_elevation">
      <sch:assert test="@unit = ('arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad')">
        The attribute @unit must be equal to one of the following values 'arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Image_Mask_File/img:mask_type">
      <sch:assert test=". = ('description', 'image')">
        The attribute img:mask_type must be equal to one of the following values 'description', 'image'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:JPEG_Parameters/img:color_subsampling_mode">
      <sch:assert test=". = ('4:2:2', '4:4:4', 'Grayscale')">
        The attribute img:color_subsampling_mode must be equal to one of the following values '4:2:2', '4:4:4', 'Grayscale'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:JPEG_Progressive_Parameters/img:color_subsampling_mode">
      <sch:assert test=". = ('4:2:2', '4:4:4', 'Grayscale')">
        The attribute img:color_subsampling_mode must be equal to one of the following values '4:2:2', '4:4:4', 'Grayscale'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:LED_Illumination_Source/img:illumination_state">
      <sch:assert test=". = ('Off', 'On')">
        The attribute img:illumination_state must be equal to one of the following values 'Off', 'On'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:LED_Illumination_Source/img:illumination_wavelength">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Onboard_Compression">
      <sch:assert test="if (img:deferred_flag) then img:deferred_flag = ('true', 'false') else true()">
        The attribute img:deferred_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Onboard_Compression/img:onboard_compression_class">
      <sch:assert test=". = ('Lossless', 'Lossy', 'Uncompressed')">
        The attribute img:onboard_compression_class must be equal to one of the following values 'Lossless', 'Lossy', 'Uncompressed'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Onboard_Compression/img:onboard_compression_type">
      <sch:assert test=". = ('GZIP', 'ICER', 'ICT', 'JPEG', 'JPEG Progressive', 'LOCO', 'LZO', 'Lossless', 'MSSS Lossless', 'None')">
        The attribute img:onboard_compression_type must be equal to one of the following values 'GZIP', 'ICER', 'ICT', 'JPEG', 'JPEG Progressive', 'LOCO', 'LZO', 'Lossless', 'MSSS Lossless', 'None'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Onboard_Compression/img:onboard_compression_venue">
      <sch:assert test=". = ('Hardware', 'Software')">
        The attribute img:onboard_compression_venue must be equal to one of the following values 'Hardware', 'Software'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Optical_Filter/img:bandwidth">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Optical_Filter/img:center_filter_wavelength">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Optical_Properties/img:f_number">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Optical_Properties/img:focal_length">
      <sch:assert test="@unit = ('AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm')">
        The attribute @unit must be equal to one of the following values 'AU', 'Angstrom', 'cm', 'km', 'm', 'micrometer', 'mm', 'nm'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Pixel_Averaging_Dimensions/img:height_pixels">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Pixel_Averaging_Dimensions/img:width_pixels">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Radial_Flat_Field_Function/img:x_center">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Radial_Flat_Field_Function/img:y_center">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Radiometric_Correction">
      <sch:assert test="if (img:active_flag) then img:active_flag = ('true', 'false') else true()">
        The attribute img:active_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Radiometric_Correction/img:radiometric_type">
      <sch:assert test=". = ('No CFA', 'Scaled Spectral Radiance', 'Spectral Radiance')">
        The attribute img:radiometric_type must be equal to one of the following values 'No CFA', 'Scaled Spectral Radiance', 'Spectral Radiance'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Shutter_Subtraction">
      <sch:assert test="if (img:active_flag) then img:active_flag = ('true', 'false') else true()">
        The attribute img:active_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Shutter_Subtraction/img:shutter_subtraction_mode">
      <sch:assert test=". = ('Conditional', 'True')">
        The attribute img:shutter_subtraction_mode must be equal to one of the following values 'Conditional', 'True'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Spatial_Filter/img:filter_window_line">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Spatial_Filter/img:filter_window_sample">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Spatial_Filter/img:max_filter_window_line">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Spatial_Filter/img:max_filter_window_sample">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Spatial_Filter/img:min_filter_window_line">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Spatial_Filter/img:min_filter_window_sample">
      <sch:assert test="@unit = ('DN', 'electron/DN', 'pixel')">
        The attribute @unit must be equal to one of the following values 'DN', 'electron/DN', 'pixel'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Subframe/img:line_fov">
      <sch:assert test="@unit = ('arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad')">
        The attribute @unit must be equal to one of the following values 'arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Subframe/img:sample_fov">
      <sch:assert test="@unit = ('arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad')">
        The attribute @unit must be equal to one of the following values 'arcmin', 'arcsec', 'deg', 'hr', 'mrad', 'rad'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Subframe/img:subframe_type">
      <sch:assert test=". = ('Hardware Compatible', 'Hardware Else Software', 'None', 'Software Only', 'Subframe Around Sun', 'Sun Subframe Or Full')">
        The attribute img:subframe_type must be equal to one of the following values 'Hardware Compatible', 'Hardware Else Software', 'None', 'Software Only', 'Subframe Around Sun', 'Sun Subframe Or Full'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Thumbnail">
      <sch:assert test="if (img:product_flag) then img:product_flag = ('true', 'false') else true()">
        The attribute img:product_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Thumbnail/img:frame_id">
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Thumbnail/img:frame_type_name">
      <sch:assert test=". = ('Mono', 'Stereo')">
        The attribute img:frame_type_name must be equal to one of the following values 'Mono', 'Stereo'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Video">
      <sch:assert test="if (img:video_flag) then img:video_flag = ('true', 'false') else true()">
        The attribute img:video_flag must be equal to one of the following values 'true', 'false'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Video/img:frame_interval">
      <sch:assert test="@unit = ('day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr')">
        The attribute @unit must be equal to one of the following values 'day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Video/img:frame_rate">
      <sch:assert test="@unit = ('frames/s')">
        The attribute @unit must be equal to one of the following values 'frames/s'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Video/img:interframe_delay">
      <sch:assert test="@unit = ('day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr')">
        The attribute @unit must be equal to one of the following values 'day', 'hr', 'julian day', 'microseconds', 'min', 'ms', 's', 'yr'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Instrument_State">
      <sch:assert test="count(child::*) > 0">
        IMG:error:inst_state_child_check: img:Instrument_State must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:JPEG_Parameters">
      <sch:assert test="count(child::*) > 0">
        IMG:error:jpeg_params_child_check: img:JPEG_Parameters must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Imaging/pds:Local_Internal_Reference">
      <sch:assert test="pds:local_reference_type = 'imaging_parameters_to_image_object'">
        In img:Imaging, Local_Internal_Reference.local_reference_type must be equal to 'imaging_parameters_to_image_object'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Optical_Filter/pds:Local_Internal_Reference">
      <sch:assert test="pds:local_reference_type = 'data_to_optical_filter'">
        In img:Optical_Filter, Local_Internal_Reference.local_reference_type must be equal to 'data_to_optical_filter'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:LOCO_Parameters">
      <sch:assert test="count(child::*) > 0">
        IMG:error:loco_params_child_check: img:LOCO_Parameters must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Onboard_Compression">
      <sch:assert test="count(child::*) > 0">
        IMG:error:onboard_compression_child_check: img:Onboard_Compression must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Optical_Filter">
      <sch:assert test="count(child::*) > 0">
        IMG:error:optical_filter_child_check: img:Optical_Filter must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Brightness_Correction_Image/pds:Internal_Reference">
      <sch:assert test="pds:reference_type = 'data_to_brightness_correction'">
        In img:Brightness_Correction_Image, Internal_Reference.reference_type must be equal to 'data_to_brightness_correction'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:Detector/pds:Internal_Reference">
      <sch:assert test="pds:reference_type = 'data_to_raw_source_product'">
        In img:Detector, Internal_Reference.reference_type must be equal to 'data_to_raw_source_product'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="img:High_Dynamic_Range_Exposure/pds:Internal_Reference">
      <sch:assert test="pds:reference_type = 'data_to_raw_source_product'">
        In img:High_Dynamic_Range_Exposure, Internal_Reference.reference_type must be equal to 'data_to_raw_source_product'.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Sampling">
      <sch:assert test="count(child::*) > 0">
        IMG:error:sampling_child_check: img:Sampling must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Shutter_Subtraction">
      <sch:assert test="(img:shutter_subtraction_mode != 'Conditional') or (img:shutter_subtraction_mode = 'Conditional' and exists(img:exposure_duration_threshold_count))">
        IMG:error:shutter_subtraction_check: if img:shutter_subtraction_mode = 'Conditional', then img:exposure_duration_threshold_count must exist.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Subframe">
      <sch:assert test="count(child::*) > 0">
        IMG:error:subframe_child_check: img:Subframe must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern>
    <sch:rule context="//img:Video">
      <sch:assert test="count(child::*) > 0">
        IMG:error:video_child_check: img:Video must have at least 1 attribute or class specified.</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
