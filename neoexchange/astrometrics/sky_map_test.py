import os
from sys import exit
from datetime import datetime
from math import degrees, radians

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict
import pyslalib.slalib as S
from aitoff_hammer_projection import HammerAxes
import matplotlib.pyplot as plt
from astropy.wcs import WCS
from astropy import units as u
from astropy.coordinates import SkyCoord
import astropy.coordinates as coord
from matplotlib.dates import HourLocator, DateFormatter
from matplotlib.projections import register_projection
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import matplotlib.colors as colors

def untangle_lines(x_coords, y_coords):
    ''' Remove the crossover from one side of the plot to the other by sorting the datapoints 
    that define lines within the window of a specific reference frame.'''

    out_y = [y for _,y in sorted(zip(x_coords,y_coords), key = lambda pair: pair[0])]
    out_x = sorted(x_coords)
    #padd either end to make line go off window.
    out_x = [out_x[0] - (out_x[1] - out_x[0])] + out_x + [out_x[-1] + (out_x[-1] - out_x[-2])]
    out_y = [out_y[-1]] + out_y + [out_y[0]]
    return out_x, out_y

def convert_coordinates(coordinates, ref_frame, x_ref, y_ref, line=False):
    ''' Take care of coordinate transformation and split SkyCoods into X and Y components'''
    try:
        coord_trans = getattr(coordinates,ref_frame)
    except ValueError:
        print "Incorrect reference frame: %s" % ref_frame
    try:
        coord_trans_x = getattr(coord_trans,x_ref)
        coord_trans_y = getattr(coord_trans,y_ref)
    except ValueError:
        print "Incorrect x/y axis name: %s/%s" % x_ref,y_ref
    coord_trans_x = coord.Angle(coord_trans_x)
    coord_trans_x = coord_trans_x.wrap_at(180*u.degree)
    if line:
        out_x, out_y = untangle_lines(coord_trans_x.radian, coord_trans_y.radian)
    else:
        out_x, out_y = coord_trans_x.radian, coord_trans_y.radian
    return out_x, out_y

def plot_skymap( c_radec, obs_len, colors='r', title=''):
    #convert exposure times into minutes
    obs_len = [x / 60. for x in obs_len]

    #define important lines
    ys=[0]*100
    xs=[i / 100. * 360. for i in xrange(100)]
    ecliptic=SkyCoord(lon=xs*u.degree, lat=ys*u.degree, frame='barycentrictrueecliptic')
    galaxy=SkyCoord(l=xs*u.degree, b=ys*u.degree, frame='galactic')
    equator=SkyCoord(ra=xs*u.degree, dec=ys*u.degree, frame='icrs')
    center=SkyCoord(ra=0*u.degree, dec=0*u.degree, frame='icrs')

    #Register the Aitoff_Hammer projection
    register_projection(HammerAxes)

    #Set up 1st plot in Equatorial Space
    fig = plt.figure(figsize=(10,15))
#    ax = fig.add_subplot(411, projection="mollweide")
    ax = fig.add_subplot(311, projection="custom_hammer")
    ax.set_autoscale_on(False)
    plt.title("Equatorial")
    ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])
    frame_name, frame_x, frame_y = 'icrs','ra','dec'
    ecliptic_icrs_ra, ecliptic_icrs_dec = convert_coordinates(ecliptic, frame_name, frame_x, frame_y, True)
    ax.plot(ecliptic_icrs_ra, ecliptic_icrs_dec, "-", color='r', label='Ecliptic')
    galaxy_icrs_ra, galaxy_icrs_dec = convert_coordinates(galaxy, frame_name, frame_x, frame_y, True)
    ax.plot(galaxy_icrs_ra, galaxy_icrs_dec, "-", color='g', label='Galactic Plane')
    equator_ra, equator_dec = convert_coordinates(equator, frame_name, frame_x, frame_y, True)
    ax.plot(equator_ra, equator_dec, "-", color='b', label='Equator')
    c_radec_ra, c_radec_dec = convert_coordinates(c_radec, frame_name, frame_x, frame_y)
    ax.grid(True)
    ax.scatter(c_radec_ra, c_radec_dec, c=obs_len, cmap='binary', edgecolors='black', marker = 's', zorder=10)

    #Set up 2nd plot in Galactic Space
    ax3 = fig.add_subplot(312, projection="custom_hammer")
    ax3.set_autoscale_on(False)
    plt.title("Galactic")
    ax3.set_xticklabels(['$150^\circ$','$120^\circ$','$90^\circ$','$60^\circ$','$30^\circ$','$360^\circ$','$330^\circ$','$300^\circ$','$270^\circ$','$240^\circ$','$210^\circ$'])
    frame_name, frame_x, frame_y = 'galactic','l','b'
    ecliptic_galactic_l, ecliptic_galactic_b = convert_coordinates(ecliptic, frame_name, frame_x, frame_y, True)
    ecliptic_galactic_l = [-x for x in ecliptic_galactic_l]
    ax3.plot(ecliptic_galactic_l, ecliptic_galactic_b,"-",color='r')
    galaxy_l, galaxy_b = convert_coordinates(galaxy, frame_name, frame_x, frame_y, True)
    galaxy_l = [-x for x in galaxy_l]
    ax3.plot(galaxy_l, galaxy_b,"-",color='g')
    equator_galactic_l, equator_galactic_b = convert_coordinates(equator, frame_name, frame_x, frame_y, True)
    equator_galactic_l = [-x for x in equator_galactic_l]
    ax3.plot(equator_galactic_l, equator_galactic_b, "-", color='b')
    c_galactic_l, c_galactic_b = convert_coordinates(c_radec, frame_name, frame_x, frame_y)
    c_galactic_l=[-x for x in c_galactic_l]
    im = ax3.scatter(c_galactic_l, c_galactic_b, c=obs_len, cmap='binary', edgecolors='black', marker = 's', zorder=10)
    ax3.grid(True)

    #Set up final plot in Equatorial Space
    ax4 = fig.add_subplot(313, projection="custom_hammer")
    ax4.set_autoscale_on(False)
    plt.title("Ecliptic")
    ax4.set_xticklabels(['$210^\circ$','$240^\circ$','$270^\circ$','$300^\circ$','$330^\circ$','$0^\circ$','$30^\circ$','$60^\circ$','$90^\circ$','$120^\circ$','$150^\circ$'])
    frame_name, frame_x, frame_y = 'barycentrictrueecliptic','lon','lat'
    ecliptic_lon, ecliptic_lat = convert_coordinates(ecliptic, frame_name, frame_x, frame_y, True)
    ax4.plot(ecliptic_lon, ecliptic_lat,"-",color='r')
    galaxy_ecliptic_lon, galaxy_ecliptic_lat = convert_coordinates(galaxy, frame_name, frame_x, frame_y, True)
    ax4.plot(galaxy_ecliptic_lon, galaxy_ecliptic_lat,"-",color='g')
    equator_ecliptic_lon, equator_ecliptic_lat = convert_coordinates(equator, frame_name, frame_x, frame_y, True)
    ax4.plot(equator_ecliptic_lon, equator_ecliptic_lat, "-", color='b')
    c_ecliptic_lon, c_ecliptic_lat = convert_coordinates(c_radec, frame_name, frame_x, frame_y)
    ax4.scatter(c_ecliptic_lon, c_ecliptic_lat, c=obs_len, cmap='binary', edgecolors='black', marker = 's', zorder=10)
    ax4.grid(True)

    #set up color bar
    axins = inset_axes(ax3,
                       width="5%",  # width = 10% of parent_bbox width
                       height="100%",  # height : 50%
                       loc=3,
                       bbox_to_anchor=(1.02, 0., 1, 1),
                       bbox_transform=ax3.transAxes,
                       borderpad=0,
                       )
    cbar=plt.colorbar(im, cax=axins)
    cbar.set_label('(min)')

    #set up Legend
    ax.legend(bbox_to_anchor=(-0.1, -0), loc=2, borderaxespad=0.)
    
    #Save and plot figure
    if title:
        fig.savefig(title)
    plt.show()

    return


def frame_stacker(coords, obs_len):
    ''' Test function for stacking frames. '''
    sep_limit = 1.0 / 6.
    ra_out = []
    dec_out= []
    obs_len_out = []
    i=1
    for coord in coords:
        k=i
        for coo in coords[i:]:
            if coord.separation(coo).degree < sep_limit:
                obs_len[k]+=obs_len[i-1]
                break
            k+=1
        if k == len(obs_len):
            ra_out.append(coord.ra.degree)
            dec_out.append(coord.dec.degree)
            obs_len_out.append(obs_len[i-1])
        i+=1
    coord_out=SkyCoord(ra=ra_out*u.degree, dec=dec_out*u.degree)
    return coord_out, obs_len_out


if __name__ == '__main__':
    test_ra=[0,100,260,0,100,0]
    test_dec=[0,0,0,0,0,0]
    obs_len=[60,60,60,60,60,60]
    c_radec=SkyCoord(ra=test_ra*u.degree, dec=test_dec*u.degree)
    c_radec2, obs_len2 = frame_stacker(c_radec, obs_len)
    print c_radec2, obs_len2
    plot_skymap(c_radec2, obs_len2, title='test')
