"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2019 LCO

Generates a scatter plot of the positions
of Stellar Spectral Standards and Solar Analogs
accross a sky map.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
from astropy.coordinates import SkyCoord, Galactic
from astropy import coordinates
from astropy import units as u
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from core.models import StaticSource

def readFile(path): #reading file
    """ reads a path file if given
    input: <path> file path
    output: lines
    """
    f = open(path)
    lines = f.readlines()
    return lines

def readSources(standard='Solar'):
    """reads in spectral standards from StaticSource model
       outputs coordinates of each standard
       input: [standard] standard option
       output: coords
   """
    if standard == 'Solar':
        coords = np.array([])
        for body in StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD):
            coords = np.append(coords, SkyCoord(body.ra,body.dec,unit=(u.deg,u.deg)))
    elif standard == 'Flux':
        coords = np.array([])
        for body in StaticSource.objects.filter(source_type=StaticSource.FLUX_STANDARD):
            coords = np.append(coords, SkyCoord(body.ra,body.dec,unit=(u.deg,u.deg)))
    else:
        raise KeyError()
    return coords

def readCoords(lines):  #parsing coordinates from file
    """Builds list of coordinates of standards from lines given by readFile()
       input: <lines>
       output: coords ndarray(SkyCoord)
    """
    coords = np.array([])
    for line in lines:
        parts = line.split()
        for n in range(1,len(parts)):
            try:
                if ':' in parts[n]:
                    coords = np.append(coords, SkyCoord(parts[n],parts[n+1],unit=(u.hourangle, u.deg)))
                    break
            except ValueError:
                continue
    return coords

def genGalPlane(): #building galactic plane in ICRS coordinates
    """Generates galactic plane line to plot on sky map
       output: galicrs ndarray(SkyCoord)
    """
    galcoords = Galactic(l=np.arange(0,360,1)*u.deg,b=np.zeros(360)*u.deg)
    galicrs = galcoords.transform_to(coordinates.ICRS)
    galicrs.dec[117]=np.nan*u.deg
    return galicrs

def plotScatter(ax,coords,style='b.'):
    """Plots standards coords onto skymap plot
       inputs: <ax> plot axis
               <coords> standard coords
               [style] style of marker
    """
    for coord in coords: #stars
        ax.plot(coord.ra.hour,coord.dec,style)

def plotFormat(ax,solar=0):
    """Formats plot, plots reference ecliptic and galactic plane
       inputs: <ax> plot axis
       Set solar=0 to plot both solar and flux standards, 1 for just solar
       standards and 2 for just flux standards
    """
    ax.plot(24*np.arange(0,1,.01),23.4*np.sin(np.arange(0,2*np.pi,2*np.pi/100)),'r-') #ecliptic (approx)
    ax.plot(genGalPlane().ra.hour,genGalPlane().dec,'y-') #galactic plane (exact)
    ax.set_ylabel("Dec (Degrees)")
    ax.set_xlabel("RA (Hours)")
    plt.xlim(24,0)
    plt.ylim(-90,90)
    plt.xticks(np.arange(24,0,-2))
    plt.yticks(np.arange(-90,90,15))
    if not solar:
        leg = ax.legend(loc='best',
            handles=[mpatches.Patch(color='blue',label='Solar Standard'),
            mpatches.Patch(color='green',label='Flux Standard')])
    elif solar == 2:
         leg = ax.legend(loc='best',
            handles=[mpatches.Patch(color='green',label='Flux Standard'),])
    else:
        leg = ax.legend(loc='best',
            handles=[mpatches.Patch(color='blue',label='Solar Standard')])
    leg.get_frame().set_alpha(.5)
    plt.text(24,55,'Galactic Plane',fontsize=7,rotation=-25,color='#938200')
    plt.text(9.5,16,'Ecliptic',fontsize=7,rotation=25,color='r')
    plt.title("Stellar Standards Distribution")

    plt.grid(True)



if __name__== "__main__":
    lines = readFile(os.path.join(os.getcwd(),'photometrics/data/Solar_Standards'))
    scoords = readSources('Solar')
    #coords = readCoords(lines)
    galcoords = genGalPlane()
    ax = plt.figure().gca()
    plotScatter(ax,scoords)
    plotFormat(ax,galcoords)
    plt.show()
