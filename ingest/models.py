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
from datetime import datetime
from django.utils.translation import ugettext as _
from astropy.time import Time
import reversion

OBJECT_TYPES = (
                ('N','NEO'),
                ('A','Asteroid'),
                ('C','Comet'),
                ('K','KBO'),
                ('E','Centaur'),
                ('T','Trojan'),
                ('U','Unknown/NEO Candidate'),
                ('X','Did not exist'),
                ('W','Was not interesting')
            )

ELEMENTS_TYPES = (('MPC_MINOR_PLANET','MPC Minor Planet'),('MPC_COMET','MPC Comet'))

ORIGINS = (
            ('M','MPC'),
            ('N','NASA ARM'),
            ('S','Spaceguard'),
            ('D','NEODSYS'),
            ('G','Goldstone'),
            ('A','Arecibo')
            )

TELESCOPE_CHOICES = (
                        ('1m0','1-meter'),
                        ('2m0','2-meter'),
                        ('0m4','0.4-meter')
                    )

def check_object_exists(objname,dbg=False):

    try:
        block_id = Body.objects.get(provisional_name__contains=objname)
    except Body.MultipleObjectsReturned:
        if dbg: print "Multiple bodies found"
        return 2
    except Body.DoesNotExist:
        if dbg: print "Body not found"
        return 0
    else:
        if dbg: print "Body found"
        return 1


class Proposal(models.Model):
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=255)

    def __unicode__(self):
        if len(self.title)>=10:
            title = "%s..." % self.title[0:9]
        else:
            title = self.title[0:10]
        return "%s %s"  % (code, title)


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
    ingest              = models.DateTimeField(default=datetime.now())

    def epochofel_mjd(self):
        t = Time(self.epochofel.isoformat(), format='isot', scale='tt')
        return t.mjd

    def epochofperih_mjd(self):
        t = Time(self.epochofperih.isoformat(), format='isot', scale='tt')
        return t.mjd

    class Meta:
        verbose_name = _('Minor Body')
        verbose_name_plural = _('Minor Bodies')

    def __unicode__(self):
        if self.active:
            text = ''
        else:
            text = 'not '
        return_name = self.provisional_name
        if self.provisional_name == None and self.name != None:
            return_name = self.name
        return u'%s is %sactive' % (return_name,text)
reversion.register(Body)


class Block(models.Model):
    telclass = models.CharField(max_length=3, null=False, blank=False, default='1m0', choices=TELESCOPE_CHOICES)
    site = models.CharField(max_length=3)
    body = models.ForeignKey(Body)
    proposal = models.ForeignKey(Proposal)
    block_start =  models.DateTimeField(null=True, blank=True)
    block_end =  models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=10,null=True, blank=True)
    when_observed =  models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Observation Block')
        verbose_name_plural = _('Observation Blocks')

    def __unicode__(self):
        pass

    
class Record(models.Model):
    ''' Log of observations successfully made and filename of data which resulted
    '''
    site    = models.CharField('3-letter site code', max_length=3)
    instrument = models.CharField('instrument code', max_length=4)
    filter = models.CharField('filter class', max_length=15)
    filename = models.CharField(max_length=31)
    exp = models.FloatField('exposure time in seconds')
    whentaken = models.DateTimeField()
    block = models.ForeignKey(Block)

    class Meta:
        verbose_name = _('Observation Record')
        verbose_name_plural = _('Observation Records')

    def __unicode__(self):
        if self.active:
                text = ''
        else:
                text = 'not '
        return u'%s is %sactive' % (self.provisional_name,text)
