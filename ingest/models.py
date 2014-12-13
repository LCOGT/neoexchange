'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014 LCOGT

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


OBJECT_TYPES = (
                ('N','NEO'),
                ('A','Asteroid'),
                ('C','Comet'),
                ('T','TNO'),
                ('E','Centaur'),
                ('R','Trojan')
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
    origin              = models.CharField('Where did this target come from?',max_length=1, choices=ORIGINS, default="M")
    source_type         = models.CharField('Type of object',max_length=1,choices=OBJECT_TYPES)
    elements_type       = models.CharField('Elements type', max_length=1, choices=ELEMENTS_TYPES)
    active              = models.BooleanField('Actively following?', default=False)
    fast_moving         = models.BooleanField('Is this object fast?', default=False)
    urgency             = models.IntegerField(help_text='how urgent is this?', blank=True, null=True)
    epochofel           = models.FloatField('Epoch of elements in MJD')
    orbinc              = models.FloatField('Orbital inclination in deg')
    longascnode         = models.FloatField('Longitude of Ascending Node (deg)')
    argofperih          = models.FloatField('Arg of perihelion (deg)')
    eccentricity        = models.FloatField('Eccentricity')
    meandist            = models.FloatField('Mean distance (AU)', blank=True, null=True, help_text='for asteroids')
    meananom            = models.FloatField('Mean Anomoly (deg)', blank=True, null=True, help_text='for asteroids')
    perihdist           = models.FloatField('Perihelion distance (AU)', blank=True, null=True, help_text='for comets')
    epochofperih        = models.FloatField('Epoch of perihelion (MJD)', blank=True, null=True, help_text='for comets')
    ingest              = models.DateTimeField(default=datetime.now())

    class Meta:
        verbose_name = _('Minor Body')
        verbose_name_plural = _('Minor Bodies')

    def __unicode__(self):
        if self.active:
            text = ''
        else:
            text = 'not '
        return u'%s is %sactive' % (self.provisional_name,text)



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
