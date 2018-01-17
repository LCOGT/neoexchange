import os
from sys import exit
from datetime import datetime
from math import degrees, radians

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
import pyslalib.slalib as S
from astrometrics.sky_map_test import plot_skymap, frame_stacker
import matplotlib.pyplot as plt
from astropy.wcs import WCS
from astropy import units as u
from astropy.coordinates import SkyCoord
from matplotlib.dates import HourLocator, DateFormatter
from core.models import Block, Frame, Body, WCSField

class Command(BaseCommand):

    help = 'Create map of neo_exchange pointing locations'

    def handle(self, *args, **options):
        frames=[]
        frames = Frame.objects.exclude(block__body__origin = 'M').filter(frametype = 91).exclude(wcs=None)
#        frames = Frame.objects.filter(frametype = 91).exclude(wcs=None)
        self.stdout.write("Found %d frames" % (len(frames)))

        if len(frames) != 0:
            obs_len = []
            ra = []
            dec = []
            sep_limit = 1.0 
            for frame in frames:
                wcs = frame.wcs
                k=0
                ra_temp = wcs.wcs.crval[0]
                dec_temp = wcs.wcs.crval[1]
                on_sky=SkyCoord(ra=ra_temp*u.degree,dec=dec_temp*u.degree)
                for spot in ra:
                    if abs(spot-ra_temp) < sep_limit:
                        test_spot = SkyCoord(ra=spot*u.degree,dec=dec[k]*u.degree)
                        if on_sky.separation(test_spot).degree < sep_limit:
                            obs_len[k]+=frame.exptime
                            break
                    k+=1
                if k == len(obs_len):
                    ra.append(ra_temp)
                    dec.append(dec_temp)
                    obs_len.append(frame.exptime)
                    print "New position %i: (%d,%d)" % (k+1, ra_temp, dec_temp)
            c_radec=SkyCoord(ra=ra*u.degree,dec=dec*u.degree)
            plot_skymap(c_radec, obs_len, title='')
        else:
            test_ra=[0,100,260]
            test_dec=[0,0,0]
            c_radec=SkyCoord(ra=test_ra*u.degree, dec=test_dec*u.degree)
            obs_len=[1,1,1]
            plot_skymap(c_radec, obs_len, title='')

            
              

