'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from datetime import datetime
from math import pi, log10
import reversion

from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text
from django.forms.models import model_to_dict
from astropy.time import Time
from astropy.wcs import WCS
from numpy import fromstring
try:
    # cpython 2.x
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps
from base64 import b64decode, b64encode

from astrometrics.ast_subs import normal_to_packed
from astrometrics.ephem_subs import compute_ephem, comp_FOM, get_sitecam_params, comp_sep
from astrometrics.sources_subs import translate_catalog_code
from astrometrics.time_subs import dttodecimalday, degreestohms, degreestodms


OBJECT_TYPES = (
                ('N','NEO'),
                ('A','Asteroid'),
                ('C','Comet'),
                ('K','KBO'),
                ('E','Centaur'),
                ('T','Trojan'),
                ('U','Candidate'),
                ('X','Did not exist'),
                ('W','Was not interesting'),
                ('D','Discovery, non NEO'),
                ('J','Artificial satellite')
            )

ELEMENTS_TYPES = (('MPC_MINOR_PLANET','MPC Minor Planet'),('MPC_COMET','MPC Comet'))

ORIGINS = (
            ('M','Minor Planet Center'),
            ('N','NASA ARM'),
            ('S','Spaceguard'),
            ('D','NEODSYS'),
            ('G','Goldstone'),
            ('A','Arecibo'),
            ('R','Goldstone & Arecibo'),
            ('L','LCOGT')
            )

TELESCOPE_CHOICES = (
                        ('1m0','1-meter'),
                        ('2m0','2-meter'),
                        ('0m4','0.4-meter')
                    )

SITE_CHOICES = (
                    ('ogg','Haleakala'),
                    ('coj','Siding Spring'),
                    ('lsc','Cerro Tololo'),
                    ('elp','McDonald'),
                    ('cpt','Sutherland'),
                    ('tfn','Tenerife'),
                    ('sbg','SBIG cameras'),
                    ('sin','Sinistro cameras')
    )

class Proposal(models.Model):
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    pi = models.CharField("PI", max_length=50, default='', help_text='Principal Investigator (PI)')
    tag = models.CharField(max_length=10, default='LCOGT')
    active = models.BooleanField('Proposal active?', default=True)

    class Meta:
        db_table = 'ingest_proposal'

    def __unicode__(self):
        if len(self.title)>=10:
            title = "%s..." % self.title[0:9]
        else:
            title = self.title[0:10]
        return "%s %s"  % (self.code, title)


class Body(models.Model):
    provisional_name    = models.CharField('Provisional MPC designation',max_length=15,blank=True, null=True)
    provisional_packed  = models.CharField('MPC name in packed format', max_length=7,blank=True, null=True)
    name                = models.CharField('Designation',max_length=15, blank=True, null=True)
    origin              = models.CharField('Where did this target come from?',max_length=1, choices=ORIGINS, default="M",blank=True, null=True)
    source_type         = models.CharField('Type of object',max_length=1,choices=OBJECT_TYPES,blank=True, null=True)
    elements_type       = models.CharField('Elements type', max_length=16, choices=ELEMENTS_TYPES,blank=True, null=True)
    active              = models.BooleanField('Actively following?', default=False)
    fast_moving         = models.BooleanField('Is this object fast?', default=False)
    urgency             = models.IntegerField(help_text='how urgent is this?', blank=True, null=True)
    epochofel           = models.DateTimeField('Epoch of elements',blank=True, null=True)
    orbinc              = models.FloatField('Orbital inclination in deg',blank=True, null=True)
    longascnode         = models.FloatField('Longitude of Ascending Node (deg)',blank=True, null=True)
    argofperih          = models.FloatField('Arg of perihelion (deg)',blank=True, null=True)
    eccentricity        = models.FloatField('Eccentricity',blank=True, null=True)
    meandist            = models.FloatField('Mean distance (AU)', blank=True, null=True, help_text='for asteroids')
    meananom            = models.FloatField('Mean Anomaly (deg)', blank=True, null=True, help_text='for asteroids')
    perihdist           = models.FloatField('Perihelion distance (AU)', blank=True, null=True, help_text='for comets')
    epochofperih        = models.DateTimeField('Epoch of perihelion', blank=True, null=True, help_text='for comets')
    abs_mag             = models.FloatField('H - absolute magnitude', blank=True, null=True)
    slope               = models.FloatField('G - slope parameter', blank=True, null=True)
    score               = models.IntegerField(help_text='NEOCP digest2 score', blank=True, null=True)
    discovery_date      = models.DateTimeField(blank=True, null=True)
    num_obs             = models.IntegerField('Number of observations', blank=True, null=True)
    arc_length          = models.FloatField('Length of observed arc (days)', blank=True, null=True)
    not_seen            = models.FloatField('Time since last observation (days)', blank=True, null=True)
    updated             = models.BooleanField('Has this object been updated?', default=False)
    ingest              = models.DateTimeField(default=now)
    update_time         = models.DateTimeField(blank=True, null=True)

    def epochofel_mjd(self):
        mjd = None
        try:
            t = Time(self.epochofel.isoformat(), format='isot', scale='tt')
            mjd = t.mjd
        except:
            pass
        return mjd

    def epochofperih_mjd(self):
        mjd = None
        try:
            t = Time(self.epochofperih.isoformat(), format='isot', scale='tt')
            mjd = t.mjd
        except:
            pass
        return mjd

    def current_name(self):
        if self.name:
            return self.name
        elif self.provisional_name:
            return self.provisional_name
        else:
            return "Unknown"

    def old_name(self):
        if self.provisional_name and self.name:
            return self.provisional_name
        else:
            return False

    def compute_position(self):
        d = datetime.utcnow()
        if self.epochofel:
            orbelems = model_to_dict(self)
            sitecode = '500'
            emp_line = compute_ephem(d, orbelems, sitecode, dbg=False, perturb=False, display=False)
            # Return just numerical values
            return (emp_line[1], emp_line[2], emp_line[3], emp_line[6])
        else:
            # Catch the case where there is no Epoch
            return False


    def compute_FOM(self):
        d = datetime.utcnow()
        if self.epochofel:
            orbelems = model_to_dict(self)
            sitecode = '500'
            emp_line = compute_ephem(d, orbelems, sitecode, dbg=False, perturb=False, display=False)
            if 'U' in orbelems['source_type'] and orbelems['not_seen']!=None and orbelems['arc_length']!=None and orbelems['score']!=None:
                FOM = comp_FOM(orbelems, emp_line)
                return FOM
            else:
                return None
           # Catch the case where there is no Epoch
        else:
            return None

    def get_block_info(self):
        blocks = Block.objects.filter(body=self.id)
        num_blocks = blocks.count()
        if num_blocks > 0:
            num_blocks_observed = blocks.filter(num_observed__gte=1).count()
            num_blocks_reported = blocks.filter(reported=True).count()
            observed = "%d/%d" % (num_blocks_observed, num_blocks)
            reported = "%d/%d" % (num_blocks_reported, num_blocks)
        else:
            observed = 'Not yet'
            reported = 'Not yet'
        return (observed, reported)

    class Meta:
        verbose_name = _('Minor Body')
        verbose_name_plural = _('Minor Bodies')
        db_table = 'ingest_body'
        ordering = ['-ingest', '-active']

    def __unicode__(self):
        if self.active:
            text = ''
        else:
            text = 'not '
        return_name = self.provisional_name
        if (self.provisional_name == None or self.provisional_name == u'') \
            and self.name != None and self.name != u'':
            return_name = self.name
        return u'%s is %sactive' % (return_name,text)


class Block(models.Model):
    telclass        = models.CharField(max_length=3, null=False, blank=False, default='1m0', choices=TELESCOPE_CHOICES)
    site            = models.CharField(max_length=3, choices=SITE_CHOICES)
    body            = models.ForeignKey(Body)
    proposal        = models.ForeignKey(Proposal)
    groupid         = models.CharField(max_length=55, null=True, blank=True)
    block_start     = models.DateTimeField(null=True, blank=True)
    block_end       = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=10, null=True, blank=True)
    num_exposures   = models.IntegerField(null=True, blank=True)
    exp_length      = models.FloatField('Exposure length in seconds', null=True, blank=True)
    num_observed    = models.IntegerField(help_text='No. of scheduler blocks executed', null=True, blank=True)
    when_observed   = models.DateTimeField(help_text='Date/time of latest frame', null=True, blank=True)
    active          = models.BooleanField(default=False)
    reported        = models.BooleanField(default=False)
    when_reported   = models.DateTimeField(null=True, blank=True)

    def make_obsblock_link(self):
        url = ''
        point_at_reqdb = False
        if self.tracking_number != None and self.tracking_number != '':
            url = 'http://lcogt.net/observe/request/%s/' % (self.tracking_number)
            if point_at_reqdb:
                url = 'http://scheduler1.lco.gtn/requestdb/admin/requestdb/userrequests/'
# Strip off leading zeros
                url = url + self.tracking_number.lstrip('0') + '/'
        return url

    class Meta:
        verbose_name = _('Observation Block')
        verbose_name_plural = _('Observation Blocks')
        db_table = 'ingest_block'

    def __unicode__(self):
        if self.active:
            text = ''
        else:
            text = 'not '

        return u'%s is %sactive' % (self.tracking_number,text)

def unpickle_wcs(wcs_string):
    '''Takes a pickled string and turns into an astropy WCS object'''
    wcs_bytes = wcs_string.encode()     # encode str to bytes
    wcs_bytes = b64decode(wcs_bytes)
    wcs_header = loads(wcs_bytes)
    return WCS(wcs_header)

def pickle_wcs(wcs_object):
    '''Turn out base64encoded string from astropy WCS object. This does
    not use the inbuilt pickle/__reduce__ which loses needed information'''
    pickle_protocol = 2

    if wcs_object is not None and isinstance(wcs_object, WCS):
        wcs_header = wcs_object.to_header()
        # Add back missing NAXIS keywords, change back to CD matrix
        wcs_header.insert(0, ("NAXIS", 2, "number of array dimensions"))
        wcs_header.insert(1, ("NAXIS1", wcs_object._naxis1, ""))
        wcs_header.insert(2, ("NAXIS2", wcs_object._naxis2, ""))
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

    def from_db_value(self, value, expression, connection, context):
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
            value = force_text(pickle_wcs(value))
        return value

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_db_prep_value(value)

    def get_internal_type(self):
        return 'TextField'

class Frame(models.Model):
    ''' Model to represent (FITS) frames of data from observations successfully
    made and filename of data which resulted.
    '''
    SINGLE_FRAMETYPE = 0
    STACK_FRAMETYPE = 1
    NONLCO_FRAMETYPE = 2
    SATELLITE_FRAMETYPE = 3
    SPECTRUM_FRAMETYPE = 4
    FRAMETYPE_CHOICES = (
                        (SINGLE_FRAMETYPE, 'Single frame'),
                        (STACK_FRAMETYPE, 'Stack of frames'),
                        (NONLCO_FRAMETYPE, 'Non-LCOGT data'),
                        (SATELLITE_FRAMETYPE, 'Satellite data'),
                        (SPECTRUM_FRAMETYPE, 'Spectrum')
                    )
    sitecode    = models.CharField('MPC site code', max_length=4, blank=False)
    instrument  = models.CharField('instrument code', max_length=4, blank=True, null=True)
    filter      = models.CharField('filter class', max_length=15, blank=False, default="B")
    filename    = models.CharField('FITS filename', max_length=40, blank=True, null=True)
    exptime     = models.FloatField('Exposure time in seconds', null=True, blank=True)
    midpoint    = models.DateTimeField('UTC date/time of frame midpoint', null=False, blank=False)
    block       = models.ForeignKey(Block, null=True, blank=True)
    quality     = models.CharField('Frame Quality flags', help_text='Comma separated list of frame/condition flags', max_length=40, blank=True, default=' ')
    zeropoint   = models.FloatField('Frame zeropoint (mag.)', null=True, blank=True)
    zeropoint_err = models.FloatField('Error on Frame zeropoint (mag.)', null=True, blank=True)
    fwhm        = models.FloatField('Full width at half maximum (FWHM; arcsec)', null=True, blank=True)
    frametype   = models.SmallIntegerField('Frame Type', null=False, blank=False, default=0, choices=FRAMETYPE_CHOICES)
    extrainfo   = models.TextField(blank=True, null=True)
    rms_of_fit  = models.FloatField('RMS of astrometric fit (arcsec)', null=True, blank=True)
    nstars_in_fit  = models.FloatField('No. of stars used in astrometric fit', null=True, blank=True)
    time_uncertainty = models.FloatField('Time uncertainty (seconds)', null=True, blank=True)
    frameid     = models.IntegerField('Archive ID', null=True, blank=True)
    wcs         = WCSField('WCS info', blank=True, null=True, editable=False)


    def get_x_size(self):
        x_size = None
        try:
            x_size = self.wcs._naxis1
        except AttributeError:
            pass
        return x_size

    def get_y_size(self):
        y_size = None
        try:
            y_size = self.wcs._naxis2
        except AttributeError:
            pass
        return y_size

    class Meta:
        verbose_name = _('Observed Frame')
        verbose_name_plural = _('Observed Frames')
        db_table = 'ingest_frame'

    def __unicode__(self):

        if self.filename:
            name= self.filename
        else:
            name = "%s@%s" % ( self.midpoint, self.sitecode.rstrip() )
        return name

class SourceMeasurement(models.Model):
    '''Class to represent the measurements (RA, Dec, Magnitude and errors)
    performed on a Frame (having site code, date/time etc.).
    These will provide the way of storing past measurements of an object and
    any new measurements performed on data from the LCOGT NEO Follow-up Network
    '''

    body = models.ForeignKey(Body)
    frame = models.ForeignKey(Frame)
    obs_ra = models.FloatField('Observed RA')
    obs_dec = models.FloatField('Observed Dec')
    obs_mag = models.FloatField('Observed Magnitude', blank=True, null=True)
    err_obs_ra = models.FloatField('Error on Observed RA', blank=True, null=True)
    err_obs_dec = models.FloatField('Error on Observed Dec', blank=True, null=True)
    err_obs_mag = models.FloatField('Error on Observed Magnitude', blank=True, null=True)
    astrometric_catalog = models.CharField('Astrometric catalog used', max_length=40, default=' ')
    photometric_catalog = models.CharField('Photometric catalog used', max_length=40, default=' ')
    aperture_size = models.FloatField('Size of aperture (arcsec)', blank=True, null=True)
    snr = models.FloatField('Size of aperture (arcsec)', blank=True, null=True)
    flags = models.CharField('Frame Quality flags', help_text='Comma separated list of frame/condition flags', max_length=40, blank=True, default=' ')

    def format_mpc_line(self):

        if self.body.name:
            name, status = normal_to_packed(self.body.name)
            if status != 0:
                name = "%5s       " % self.body.name
        else:
            name = "     %7s" % self.body.provisional_name

        try:
            mag = "%4.1f" % self.obs_mag
        except TypeError:
            mag = "    "

        obs_type = 'C'
        microday = True
        if self.frame.frametype == Frame.SATELLITE_FRAMETYPE:
            obs_type = 'S'
            microday = False
        mpc_line = "%12s %1s%1s%16s%11s %11s          %4s %1s%1s     %3s" % (name,
            self.flags, obs_type, dttodecimalday(self.frame.midpoint, microday),
            degreestohms(self.obs_ra, ' '), degreestodms(self.obs_dec, ' '),
            mag, self.frame.filter, translate_catalog_code(self.astrometric_catalog),self.frame.sitecode)
        if self.frame.frametype == Frame.SATELLITE_FRAMETYPE:
            extrainfo = self.frame.extrainfo
            if self.body.name:
                name, status = normal_to_packed(self.body.name)
                if status == 0:
                    extrainfo = name + extrainfo[12:]
            mpc_line = mpc_line + '\n' + extrainfo
        return mpc_line

    class Meta:
        verbose_name = _('Source Measurement')
        verbose_name_plural = _('Source Measurements')
        db_table = 'source_measurement'

class CatalogSources(models.Model):
    '''Class to represent the measurements (X, Y, RA, Dec, Magnitude, shape and
    errors) extracted from a catalog extraction performed on a Frame (having
    site code, date/time etc.). These will allow the storage of information for
    reference stars and candidate objects, allowing the display and measurement
    of objects.
    '''

    frame = models.ForeignKey(Frame)
    obs_x = models.FloatField('CCD X co-ordinate')
    obs_y = models.FloatField('CCD Y co-ordinate')
    obs_ra = models.FloatField('Observed RA')
    obs_dec = models.FloatField('Observed Dec')
    obs_mag = models.FloatField('Observed Magnitude', blank=True, null=True)
    err_obs_ra = models.FloatField('Error on Observed RA', blank=True, null=True)
    err_obs_dec = models.FloatField('Error on Observed Dec', blank=True, null=True)
    err_obs_mag = models.FloatField('Error on Observed Magnitude', blank=True, null=True)
    background = models.FloatField('Background')
    major_axis = models.FloatField('Ellipse major axis')
    minor_axis = models.FloatField('Ellipse minor axis')
    position_angle = models.FloatField('Ellipse position angle')
    ellipticity = models.FloatField('Ellipticity')
    aperture_size = models.FloatField('Size of aperture (arcsec)', blank=True, null=True)
    flags = models.IntegerField('Source flags', help_text='Bitmask of flags', default=0)
    flux_max = models.FloatField('Peak flux above background', blank=True, null=True)
    threshold = models.FloatField('Detection threshold above background', blank=True, null=True)

    class Meta:
        verbose_name = _('Catalog Source')
        verbose_name_plural = _('Catalog Sources')
        db_table = 'catalog_source'

    def make_elongation(self):
        elongation = self.major_axis/self.minor_axis
        return elongation

    def make_fwhm(self):
        fwhm = ((self.major_axis+self.minor_axis)/2)*2
        return fwhm

    def make_mu_max(self):
        pixel_scale = get_sitecam_params(self.frame.sitecode)[3]
        mu_max = (-2.5*log10(self.flux_max/pixel_scale**2))+self.frame.zeropoint
        return mu_max

    def make_mu_threshold(self):
        pixel_scale = get_sitecam_params(self.frame.sitecode)[3]
        mu_threshold = (-2.5*log10(self.threshold/pixel_scale**2))+self.frame.zeropoint
        return mu_threshold

    def make_flux(self):
        flux = 10.0**((self.obs_mag-self.frame.zeropoint)/-2.5)
        return flux

    def make_area(self):
        area = pi*self.major_axis*self.minor_axis
        return area

def detections_array_dtypes():
    '''Declare the columns and types of the structured numpy array for holding
    the per-frame detections from the mtdlink moving object code'''

    dtypes = {  'names' : ('det_number', 'frame_number', 'sext_number', 'jd_obs', 'ra', 'dec', 'x', 'y', 'mag', 'fwhm', 'elong', 'theta', 'rmserr', 'deltamu', 'area', 'score', 'velocity', 'sky_pos_angle', 'pixels_frame', 'streak_length'),
                'formats' : ('i4',       'i1',           'i4',          'f8',     'f8', 'f8', 'f4', 'f4', 'f4', 'f4',   'f4',    'f4',    'f4',     'f4',       'i4',   'f4',   'f4',       'f4',        'f4',           'f4' )
             }

    return dtypes

class Candidate(models.Model):
    '''Class to hold candidate moving object detections found by the moving
    object code'''

    block = models.ForeignKey(Block)
    cand_id = models.PositiveIntegerField('Candidate Id')
    score = models.FloatField('Candidate Score')
    avg_midpoint = models.DateTimeField('Average UTC midpoint')
    avg_x = models.FloatField('Average CCD X co-ordinate')
    avg_y = models.FloatField('Average CCD Y co-ordinate')
    avg_ra = models.FloatField('Average Observed RA (degrees)')
    avg_dec = models.FloatField('Average Observed Dec (degrees)')
    avg_mag = models.FloatField('Average Observed Magnitude', blank=True, null=True)
    speed = models.FloatField('Speed (degrees/day)')
    sky_motion_pa = models.FloatField('Position angle of motion on the sky (degrees)')
    detections = models.BinaryField('Detections array', blank=True, null=True, editable=False)

    def convert_speed(self):
        '''Convert speed in degrees/day into arcsec/min'''
        new_speed = (self.speed*3600.0)/(24.0*60.0)
        return new_speed

    def unpack_dets(self):
        '''Unpacks the binary BLOB from the detections field into a numpy
        structured array'''
        dtypes = detections_array_dtypes()
        dets = fromstring(self.detections, dtype=dtypes)
        return dets

    def compute_separation(self, body=None, time=None):
        '''Computes the separation between the Candidate's avg_ra and avg_dec
        and the RA, Dec of the body at a time of avg_midpoint'''
        if body == None or type(body) != 'core.models.Body':
            body = self.block.body
        if time == None:
            time = self.avg_midpoint

        try:
            elements = model_to_dict(body)
            emp_line = compute_ephem(time, elements, self.block.site)
            separation = comp_sep(self.avg_ra, self.avg_dec, emp_line[1], emp_line[2])
        except AttributeError:
            separation = None

        return separation

    class Meta:
        verbose_name = _('Candidate')

    def __unicode__(self):
        return "%s#%04d" % (self.block.tracking_number, self.cand_id)

class ProposalPermission(models.Model):
    '''
    Linking a user to proposals in NEOx to control their access
    '''
    proposal = models.ForeignKey(Proposal)
    user = models.ForeignKey(User)

    class Meta:
        verbose_name = _('Proposal Permission')

    def __unicode__(self):
        return "%s is a member of %s" % (self.user, self.proposal)
