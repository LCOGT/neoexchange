""" 
Generates a scatter plot of the positions 
of spectral Solar Anlogs accross the sky.
Author: Adam Tedeschi
for NeoExchange
"""

import os
from astropy.coordinates import SkyCoord, Galactic
from astropy import coordinates
from astropy import units as u
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from core.models import StaticSource

def readFile(path): #reading file
    f = open(path)
    lines = f.readlines()
    return lines

def readSources(standard='Solar'):
    if standard is 'Solar':
        coords = np.array([])
        for body in StaticSource.objects.filter(source_type=StaticSource.SOLAR_STANDARD):
            coords = np.append(coords, SkyCoord(body.ra,body.dec,unit=(u.deg,u.deg)))
    elif standard is 'Flux':
        coords = np.array([])
        for body in StaticSource.objects.filter(source_type=StaticSource.FLUX_STANDARD):
            coords = np.append(coords, SkyCoord(body.ra,body.dec,unit=(u.deg,u.deg)))
    else:
        raise KeyError()
    return coords

def readCoords(lines):  #parsing coordinates from file
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
    galcoords = Galactic(l=np.arange(0,360,1)*u.deg,b=np.zeros(360)*u.deg)   
    galicrs = galcoords.transform_to(coordinates.ICRS)
    galicrs.dec[117]=np.nan*u.deg
    return galicrs

def plotScatter(ax,coords,galcoords,style='b.'):
    for coord in coords: #stars
        ax.plot(coord.ra.hour,coord.dec,style)
    ax.plot(24*np.arange(0,1,.01),23.4*np.sin(np.arange(0,2*np.pi,2*np.pi/100)),'r-') #ecliptic (approx)
    ax.plot(galcoords.ra.hour,galcoords.dec,'y-') #galactic plane (exact)
    ax.set_ylabel("Dec (Degrees)")
    ax.set_xlabel("RA (Hours)")
    plt.xlim(24,0)
    plt.ylim(-90,90)
    plt.xticks(np.arange(24,0,-2))
    plt.yticks(np.arange(-90,90,15))

    ax.legend(handles=[mpatches.Patch(color='blue',label='Solar Standard'),mpatches.Patch(color='green',label='Flux Standard')])

    plt.title("Solar Analog Distribution")
    
    plt.grid(True)
    
if __name__== "__main__":
    lines = readFile(os.path.join(os.getcwd(),'photometrics/data/Solar_Standards'))
    scoords = readSources('Solar')
    #coords = readCoords(lines)
    galcoords = genGalPlane()
    ax = plt.figure().gca()
    plotScatter(ax,scoords,galcoords)
    plt.show()


