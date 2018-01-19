import os
from sys import exit
from datetime import datetime
from math import degrees, radians

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
import pyslalib.slalib as S
from astrometrics.sky_map_test import plot_skymap
import matplotlib.pyplot as plt
from astropy.wcs import WCS
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, get_sun
from matplotlib.dates import HourLocator, DateFormatter
from core.models import Block, Frame, Body, WCSField
import astropy.coordinates as coord


class Command(BaseCommand):

    help = 'Create map of neo_exchange pointing locations'

    def handle(self, *args, **options):
        frames=[]
#        frames = Frame.objects.exclude(block__body__origin = 'M').filter(frametype = 91).exclude(wcs=None)
        frames = Frame.objects.filter(frametype = 91).exclude(wcs=None)
        self.stdout.write("Found %d frames" % (len(frames)))

        lambda_flag=1
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
                time = frame.midpoint
                on_sky=SkyCoord(ra=ra_temp*u.degree,dec=dec_temp*u.degree, frame='gcrs', obstime=time, equinox=time)
                if lambda_flag:
                    time = Time(time)
                    obj_lon = on_sky.geocentrictrueecliptic.lon.degree
                    obj_lat = on_sky.geocentrictrueecliptic.lat.degree
                    sun_pos = get_sun(time)
                    sun_lon = sun_pos.transform_to(coord.GeocentricTrueEcliptic(equinox=time)).lon.degree
                    new_lon = obj_lon-sun_lon
                    on_sky2 = SkyCoord(lon=(new_lon)*u.degree, lat=obj_lat*u.degree, frame='geocentrictrueecliptic', equinox=time)
                    for spot in ra:
                        if abs(spot-new_lon) < sep_limit:
                            test_spot = SkyCoord(lon=spot*u.degree,lat=dec[k]*u.degree, frame='geocentrictrueecliptic', equinox=time)
                            if on_sky2.separation(test_spot).degree < sep_limit:
                                obs_len[k]+=frame.exptime
                                break
                        k+=1
                    if k == len(obs_len):
                        ra.append(obj_lon-sun_lon)
                        dec.append(obj_lat)
                        obs_len.append(frame.exptime)
                        print "New position %i: (%d,%d)" % (k+1, new_lon, obj_lat)
#                        print "Old position %i: (%d,%d)" % (k+1, obj_lon, obj_lat)
#                        print sun_pos.barycentrictrueecliptic
                        if abs(new_lon) < 10:
                            print '------------------------------'
#                            print "New position %i: (%d,%d)" % (k+1, new_lon, obj_lat)
                            print obj_lon, obj_lat
                            print sun_pos.transform_to(coord.GeocentricTrueEcliptic(equinox=time)).lon.degree, sun_pos.transform_to(coord.GeocentricTrueEcliptic(equinox=time)).lat.degree
                            print on_sky
                            print sun_pos
                            print on_sky.separation(sun_pos)
                else:
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
            if lambda_flag:
                c_lonlat=SkyCoord(lon=ra*u.degree, lat=dec*u.degree, frame='barycentrictrueecliptic')
                plot_skymap(c_lonlat, obs_len, title='test', lambda_flag=lambda_flag)
            else:
                c_radec=SkyCoord(ra=ra*u.degree,dec=dec*u.degree)
                plot_skymap(c_radec, obs_len, title='')
        else:
            test_ra=[0,100,260]
            test_dec=[0,0,0]
            c_radec=SkyCoord(ra=test_ra*u.degree, dec=test_dec*u.degree)
            obs_len=[1,1,1]
            plot_skymap(c_radec, obs_len, title='')


