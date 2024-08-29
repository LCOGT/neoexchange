"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
from astropy.wcs import WCS
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_str
try:
    # cpython 2.x
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps
from base64 import b64decode, b64encode

class WCSField(models.Field):

    description = "Store astropy.wcs objects"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('editable', False)
        kwargs['editable'] = False
        super(WCSField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(WCSField, self).deconstruct()
        del kwargs["editable"]
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return unpickle_wcs(value)

    def to_python(self, value):
        if isinstance(value, WCS):
            return value

        if value is None:
            return value

        return unpickle_wcs(value)

    def get_prep_value(self, value):
        return pickle_wcs(value)

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if value is not None:
            value = force_str(pickle_wcs(value))
        return value

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_db_prep_value(value)

    def get_internal_type(self):
        return 'TextField'


class Frame(models.Model):
    """ Model to represent (FITS) frames of data from observations successfully
    made and filename of data which resulted.
    """
    SINGLE_FRAMETYPE = 0
    STACK_FRAMETYPE = 1
    NONLCO_FRAMETYPE = 2
    SATELLITE_FRAMETYPE = 3
    SPECTRUM_FRAMETYPE = 4
    FITS_LDAC_CATALOG = 5
    BANZAI_LDAC_CATALOG = 6
    ORACDR_QL_FRAMETYPE = 10
    BANZAI_QL_FRAMETYPE = 11
    MRO_RAW_FRAMETYPE = 60
    MRO_RED_FRAMETYPE = 61
    SWOPE_RAW_FRAMETYPE = 70
    SWOPE_RED_FRAMETYPE = 71
    REFERENCE_FRAMETYPE = 80
    ORACDR_RED_FRAMETYPE = 90
    BANZAI_RED_FRAMETYPE = 91
    NEOX_RED_FRAMETYPE = 92
    NEOX_SUB_FRAMETYPE = 93
    FRAMETYPE_CHOICES = (
                        (SINGLE_FRAMETYPE, 'Single frame'),
                        (STACK_FRAMETYPE, 'Stack of frames'),
                        (NONLCO_FRAMETYPE, 'Non-LCOGT data'),
                        (SATELLITE_FRAMETYPE, 'Satellite data'),
                        (SPECTRUM_FRAMETYPE, 'Spectrum'),
                        (FITS_LDAC_CATALOG,    'FITS LDAC catalog'),
                        (BANZAI_LDAC_CATALOG,  'BANZAI LDAC catalog'),
                        (ORACDR_QL_FRAMETYPE,  'ORACDR QL frame'),
                        (BANZAI_QL_FRAMETYPE,  'BANZAI QL frame'),
                        (MRO_RAW_FRAMETYPE,  'MRO raw frame'),
                        (MRO_RED_FRAMETYPE,  'MRO reduced frame'),
                        (SWOPE_RAW_FRAMETYPE,  'Swope raw frame'),
                        (SWOPE_RED_FRAMETYPE,  'Swope reduced frame'),
                        (REFERENCE_FRAMETYPE,  'Reference frame'),
                        (ORACDR_RED_FRAMETYPE, 'ORACDR reduced frame'),
                        (BANZAI_RED_FRAMETYPE, 'BANZAI reduced frame'),
                        (NEOX_RED_FRAMETYPE, 'NEOexchange reduced frame'),
                        (NEOX_SUB_FRAMETYPE, 'NEOexchange DIA subtracted frame'),

                    )
    QUALITY_GOOD = ' '
    QUALITY_BADSUBTRACTION = 'B'
    QUALITY_INVOLVED_WITH_STAR = 'I'

    sitecode    = models.CharField('MPC site code', max_length=4, blank=False)
    instrument  = models.CharField('instrument code', max_length=4, blank=True, null=True)
    filter      = models.CharField('filter class', max_length=15, blank=False, default="B")
    filename    = models.CharField('FITS filename', max_length=50, blank=True, null=True, db_index=True)
    exptime     = models.FloatField('Exposure time in seconds', null=True, blank=True)
    midpoint    = models.DateTimeField('UTC date/time of frame midpoint', null=False, blank=False, db_index=True)
    block       = models.ForeignKey("core.Block", null=True, blank=True, on_delete=models.CASCADE)
    quality     = models.CharField('Frame Quality flags', help_text='Comma separated list of frame/condition flags', max_length=40, blank=True, default=' ')
    zeropoint   = models.FloatField('Frame zeropoint (mag.)', null=True, blank=True)
    zeropoint_err = models.FloatField('Error on Frame zeropoint (mag.)', null=True, blank=True)
    zeropoint_src = models.TextField('Source of Frame zeropoint', null=True, blank=True)
    color_used   = models.CharField('Color used for calibration', max_length=15, null=True, blank=True, default='')
    color        = models.FloatField('Color coefficient (mag.)', null=True, blank=True)
    color_err    = models.FloatField('Error on color coefficient (mag.)', null=True, blank=True)
    fwhm        = models.FloatField('Full width at half maximum (FWHM; arcsec)', null=True, blank=True)
    frametype   = models.SmallIntegerField('Frame Type', null=False, blank=False, default=0, choices=FRAMETYPE_CHOICES)
    extrainfo   = models.TextField(blank=True, null=True)
    rms_of_fit  = models.FloatField('RMS of astrometric fit (arcsec)', null=True, blank=True)
    nstars_in_fit  = models.FloatField('No. of stars used in astrometric fit', null=True, blank=True)
    time_uncertainty = models.FloatField('Time uncertainty (seconds)', null=True, blank=True)
    frameid     = models.IntegerField('Archive ID', null=True, blank=True)
    wcs         = WCSField('WCS info', blank=True, null=True, editable=False)
    astrometric_catalog = models.CharField('Astrometric catalog used', max_length=40, default=' ')
    photometric_catalog = models.CharField('Photometric catalog used', max_length=40, default=' ')

    def get_x_size(self):
        x_size = None
        try:
            x_size = self.wcs.pixel_shape[0]
        except AttributeError:
            pass
        return x_size

    def get_y_size(self):
        y_size = None
        try:
            y_size = self.wcs.pixel_shape[1]
        except AttributeError:
            pass
        return y_size

    def is_catalog(self):
        is_catalog = False
        if self.frametype == self.FITS_LDAC_CATALOG or self.frametype == self.BANZAI_LDAC_CATALOG:
            is_catalog = True
        return is_catalog

    def is_quicklook(self):
        is_quicklook = False
        if self.frametype == self.ORACDR_QL_FRAMETYPE or self.frametype == self.BANZAI_QL_FRAMETYPE:
            is_quicklook = True
        return is_quicklook

    def is_reduced(self):
        is_reduced = False
        if self.frametype == self.ORACDR_RED_FRAMETYPE or self.frametype == self.BANZAI_RED_FRAMETYPE:
            is_reduced = True
        return is_reduced

    def is_processed(self):
        is_processed = False
        if self.is_quicklook() or self.is_reduced():
            is_processed = True
        return is_processed

    def reduced_frames(self, include_oracdr=False):
        frametypes = (self.BANZAI_QL_FRAMETYPE, self.BANZAI_RED_FRAMETYPE)
        if include_oracdr:
            frametypes = (self.BANZAI_QL_FRAMETYPE, self.BANZAI_RED_FRAMETYPE, self.ORACDR_QL_FRAMETYPE, self.ORACDR_RED_FRAMETYPE)

        return frametypes

    def return_site_string(self):
        site_strings = {
                        'K91' : 'LCO CPT Node 1m0 Dome A at Sutherland, South Africa',
                        'K92' : 'LCO CPT Node 1m0 Dome B at Sutherland, South Africa',
                        'K93' : 'LCO CPT Node 1m0 Dome C at Sutherland, South Africa',
                        'W85' : 'LCO LSC Node 1m0 Dome A at Cerro Tololo, Chile',
                        'W86' : 'LCO LSC Node 1m0 Dome B at Cerro Tololo, Chile',
                        'W87' : 'LCO LSC Node 1m0 Dome C at Cerro Tololo, Chile',
                        'V37' : 'LCO ELP Node 1m0 Dome A at McDonald Observatory, Texas',
                        'V39' : 'LCO ELP Node 1m0 Dome B at McDonald Observatory, Texas',
                        'Z31' : 'LCO TFN Node 1m0 Dome A at Tenerife, Spain',
                        'Z24' : 'LCO TFN Node 1m0 Dome B at Tenerife, Spain',
                        'Z21' : 'LCO TFN Node Aqawan A 0m4a at Tenerife, Spain',
                        'Z17' : 'LCO TFN Node Aqawan A 0m4b at Tenerife, Spain',
                        'Q58' : 'LCO COJ Node 0m4a at Siding Spring, Australia',
                        'Q59' : 'LCO COJ Node 0m4b at Siding Spring, Australia',
                        'Q63' : 'LCO COJ Node 1m0 Dome A at Siding Spring, Australia',
                        'Q64' : 'LCO COJ Node 1m0 Dome B at Siding Spring, Australia',
                        'E10' : 'LCO COJ Node 2m0 FTS at Siding Spring, Australia',
                        'F65' : 'LCO OGG Node 2m0 FTN at Haleakala, Maui',
                        'T04' : 'LCO OGG Node 0m4b at Haleakala, Maui',
                        'T03' : 'LCO OGG Node 0m4c at Haleakala, Maui',
                        'W89' : 'LCO LSC Node Aqawan A 0m4a at Cerro Tololo, Chile',
                        'W79' : 'LCO LSC Node Aqawan B 0m4a at Cerro Tololo, Chile',
                        'V38' : 'LCO ELP Node Aqawan A 0m4a at McDonald Observatory, Texas',
                        'L09' : 'LCO CPT Node Aqawan A 0m4a at Sutherland, South Africa',
                        'G51' : 'LCO Byrne Observatory at Sedgwick Reserve'
                        }
        return site_strings.get(self.sitecode, 'Unknown LCO site')

    def return_tel_string(self):

        detector = 'CCD'
        point4m_aperture = 0.4
        point4m_fRatio = 8.0
        point4m_design = 'Schmidt-Cassegrain'
        point4m_string = '{:.1f}-m f/{:1d} {} + {}'.format(point4m_aperture, int(point4m_fRatio), point4m_design, detector)
        point4m_dict = {'full' : point4m_string, 'design' : point4m_design,
                     'aperture' : point4m_aperture, 'fRatio' : point4m_fRatio, 'detector' : detector }

        onem_aperture = 1.0
        onem_fRatio = 8.0
        onem_design = 'Ritchey-Chretien'
        onem_string = '{:.1f}-m f/{:1d} {} + {}'.format(onem_aperture, int(onem_fRatio), onem_design, detector)
        onem_dict = {'full' : onem_string, 'design' : onem_design,
                     'aperture' : onem_aperture, 'fRatio' : onem_fRatio, 'detector' : detector }

        twom_aperture = 2.0
        twom_fRatio = 10.0
        twom_design = 'Ritchey-Chretien'
        twom_string = '{:.1f}-m f/{:2d} {} + {}'.format(twom_aperture, int(twom_fRatio), twom_design, detector)
        twom_dict = {'full' : twom_string, 'design' : twom_design,
                     'aperture' : twom_aperture, 'fRatio' : twom_fRatio, 'detector' : detector }

        tels_strings = {
                        'K91' : onem_dict,
                        'K92' : onem_dict,
                        'K93' : onem_dict,
                        'W85' : onem_dict,
                        'W86' : onem_dict,
                        'W87' : onem_dict,
                        'V37' : onem_dict,
                        'V39' : onem_dict,
                        'Z31' : onem_dict,
                        'Z24' : onem_dict,
                        'Z21' : point4m_dict,
                        'Z17' : point4m_dict,
                        'Q58' : point4m_dict,
                        'Q59' : point4m_dict,
                        'Q63' : onem_dict,
                        'Q64' : onem_dict,
                        'E10' : twom_dict,
                        'F65' : twom_dict,
                        'T04' : point4m_dict,
                        'T03' : point4m_dict,
                        'W89' : point4m_dict,
                        'W79' : point4m_dict,
                        'V38' : point4m_dict,
                        'L09' : point4m_dict,
                        }
        tel_string = tels_strings.get(self.sitecode, {'full:' : 'Unknown LCO telescope'})

        return tel_string

    def map_filter(self):
        """Maps somewhat odd observed filters (e.g. 'solar') into the filter
        (e.g. 'R') that would be used for the photometric calibration"""

        new_filter = self.filter
        # Don't perform any mapping if it's not LCO data
        if self.frametype not in [self.NONLCO_FRAMETYPE, self.SATELLITE_FRAMETYPE]:
            if self.filter == 'solar' or self.filter == 'w' or self.filter == 'LL':
                new_filter = 'R'
            if self.photometric_catalog in ['GAIA-DR1', 'GAIA-DR2']:
                new_filter = 'G'
        return new_filter

    def ALCDEF_filter_format(self):
        """Formats current filter into acceptable name for printing in ALCDEF output."""
        new_filt = self.filter
        if len(new_filt) > 1 and new_filt[1] == 'p':
            new_filt = 's'+new_filt[0]
        return new_filt.upper()

    def set_quality(self, quality_flags):
        # TBD handle case where quality_flags is a list
        if quality_flags is not None:
            if quality_flags != self.QUALITY_GOOD:
                if quality_flags not in self.quality:
                    if self.quality != ' ':
                        flags = self.quality.replace(' ', '').split(",")
                        flags.append(quality_flags)
                        self.quality = ",".join(flags)
                    else:
                        self.quality = quality_flags
            else:
                # Reset to good
                self.quality = self.QUALITY_GOOD
        return self.quality

    class Meta:
        verbose_name = _('Observed Frame')
        verbose_name_plural = _('Observed Frames')
        db_table = 'ingest_frame'

    def __str__(self):

        if self.filename:
            name = self.filename
        else:
            name = "%s@%s" % ( self.midpoint, self.sitecode.rstrip())
        return name

def unpickle_wcs(wcs_string):
    """Takes a pickled string and turns into an astropy WCS object"""
    wcs_bytes = wcs_string.encode()     # encode str to bytes
    wcs_bytes = b64decode(wcs_bytes)
    wcs_header = loads(wcs_bytes)
    return WCS(wcs_header)


def pickle_wcs(wcs_object):
    """Turn out base64encoded string from astropy WCS object. This does
    not use the inbuilt pickle/__reduce__ which loses needed information"""
    pickle_protocol = 2

    if wcs_object is not None and isinstance(wcs_object, WCS):
        wcs_header = wcs_object.to_header()
        # Add back missing NAXIS keywords, change back to CD matrix
        wcs_header.insert(0, ("NAXIS", 2, "number of array dimensions"))
        naxis1 = 0
        naxis2 = 0
        if wcs_object.pixel_shape is not None and wcs_object.naxis == 2:
            naxis1 = wcs_object.pixel_shape[0]
            naxis2 = wcs_object.pixel_shape[1]
        wcs_header.insert(1, ("NAXIS1", naxis1, ""))
        wcs_header.insert(2, ("NAXIS2", naxis2, ""))
        wcs_header.remove("CDELT1")
        wcs_header.remove("CDELT2")
        # Some of these may be missing depending on whether there was any rotation
        num_missing = 0
        for pc in ['PC1_1', 'PC1_2', 'PC2_1', 'PC2_2']:
            if pc in wcs_header:
                wcs_header.rename_keyword(pc, pc.replace("PC", "CD"))
            else:
                num_missing += 1
        # Check if there was no PC matrix at all, insert a unity CD matrix
        if num_missing == 4:
            cd_comment = "Coordinate transformation matrix element"
            wcs_header.insert("CRVAL2", ("CD1_1", 1.0, cd_comment), after=True)
            wcs_header.insert( "CD1_1", ("CD1_2", 0.0, cd_comment), after=True)
            wcs_header.insert( "CD1_2", ("CD2_1", 0.0, cd_comment), after=True)
            wcs_header.insert( "CD2_1", ("CD2_2", 1.0, cd_comment), after=True)

        value = dumps(wcs_header, protocol=pickle_protocol)
        value = b64encode(value).decode()
    else:
        value = wcs_object
    return value
