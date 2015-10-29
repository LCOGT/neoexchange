'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict
from astrometrics.ephem_subs import compute_ephem, comp_FOM
from astropy.time import Time
from datetime import datetime
import reversion

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

FRAMETYPE_CHOICES = (
                        (0, 'Single frame'),
                        (1, 'Stack of frames'),
                        (2, 'Non-LCOGT data'),
                        (3, 'Satellite data'),
                        (4, 'Spectrum')
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
reversion.register(Body)


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


class Frame(models.Model):
    ''' Model to represent (FITS) frames of data from observations successfully 
    made and filename of data which resulted.
    '''
    sitecode    = models.CharField('MPC site code', max_length=4)
    instrument  = models.CharField('instrument code', max_length=4, blank=True)
    filter      = models.CharField('filter class', max_length=15)
    filename    = models.CharField('FITS filename', max_length=40, blank=True)
    exptime     = models.FloatField('Exposure time in seconds', null=True, blank=True)
    midpoint    = models.DateTimeField('UTC date/time of frame midpoint', null=False, blank=False)
    block       = models.ForeignKey(Block, null=True, blank=True)
    quality     = models.IntegerField('Frame Quality', help_text='Frame Quality (-1: unassessed)', default=-1)
    zeropoint   = models.FloatField('Frame zeropoint (mag.)', null=True, blank=True)
    zeropoint_err = models.FloatField('Error on Frame zeropoint (mag.)', null=True, blank=True)
    fwhm        = models.FloatField('Frame zeropoint (mag.)', null=True, blank=True)
    frametype   = models.SmallIntegerField('Frame Type', null=False, blank=False, default=0, choices=FRAMETYPE_CHOICES)
    extrainfo   = models.TextField(blank=True)
    rms_of_fit  = models.FloatField('RMS of astrometric fit (arcsec)', null=True, blank=True)
    nstars_in_fit  = models.FloatField('No. of stars used in astrometric fit', null=True, blank=True)
    time_uncertainty = models.FloatField('Time uncertainty (seconds)', null=True, blank=True)

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
