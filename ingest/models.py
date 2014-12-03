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

OBJECT_TYPES = (
				('N','NEO'),
				('A','Asteroid'),
				('C','Comet'),
				('T','TNO'),
			)

class Source(models.Model):
	provisional_name 	= models.CharField('Provisional MPC designation',max_length=15)
	provisional_packed 	= models.CharField('MPC name in packed format', max_length=7)
	name 				= models.CharField('Designation',max_length=15, blank=True, null=True)
	source_type 		= models.CharField('Type of object',max_length=1,choices=OBJECT_TYPES)
	active 				= models.BooleanField('Actively following?', default=False)
	fast_moving 		= models.BooleanField('Is this object fast?', default=False)
	urgency				= models.IntegerField(help_text='how urgent is this?', blank=True, null=True)
    epochofel 			= models.FloatField('Epoch of elements in MJD')
    orbinc 				= models.FloatField('Orbital inclination in deg')
    longascnode 		= models.FloatField('Longitude of Ascending Node (deg)')
    argofperih 			= models.FloatField('Arg of perihelion (deg)')
    eccentricity 		= models.FloatField('Eccentricity')
    meandist 			= models.FloatField('Mean distance (AU)', blank=True, null=True, help_text='for comets')
    meananom 			= models.FloatField('Mean Anomoly (deg)', blank=True, null=True, help_text='for comets')
    perihdist 			= models.FloatField('Perihelion distance (AU)', blank=True, null=True, help_text='for asteroids')
    epochofperih 		= models.FloatField('Epoch of perihelion (MJD)', blank=True, null=True, help_text='for asteroids')
    ingest 				= models.DateTimeField(default=datetime.now())

    class Meta:
        verbose_name = _('Minor Body')
        verbose_name_plural = _('Minor Bodies')

    def __unicode__(self):
    	if self.active:
    		text = ''
    	else:
    		text = 'not '
        return u'%s is %sactive' % (self.provisional_name,text)

class ObservedBlock(models.Model):

    class Meta:
        verbose_name = _('ObservedBlock')
        verbose_name_plural = _('ObservedBlocks')

    def __unicode__(self):
        pass
    
    
