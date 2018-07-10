from astropy.coordinates import SkyCoord, Galactic
from astropy import coordinates
from astropy import units as u
import numpy as np
import matplotlib.pyplot as plt

def readFile(path):
    f = open(path)
    lines = f.readlines()
    return lines

def readCoords(lines):
    coords = np.array([])
    for line in lines:
        parts = line.split()
        for n in range(len(parts)):
            try: 
                if ':' in parts[n]:
                    coords = np.append(coords, SkyCoord(parts[n],parts[n+1],unit=(u.hourangle, u.deg)))
                    break
            except ValueError:
                continue
    return coords

def genGalPlane():
    galcoords = np.array([]) #making line in galactic coords
    for c in np.arange(0.0,360.0,1)*u.deg:
        galcoords = np.append(galcoords,Galactic(l=c.to(u.rad),b=0*u.rad))
    #galcoords = Galactic(np.arange(0,360,1)*u.rad,np.zeros(360)*u.rad)
    galplanera = np.array([])
    galplanedec= np.array([])
    for gcoord in galcoords: #converting to icrs
        galICRS = gcoord.transform_to(coordinates.ICRS)
        galplanera = np.append(galplanera,galICRS.ra.hour)
        galplanedec = np.append(galplanedec,galICRS.dec*u.rad)

    galplanedec[117]=np.nan
    return galplanera, galplanedec
    #galicrs = galcoords.transform_to(coordinates.ICRS)
    #return galicrs

#def plotScatter(coords,galcoords):
def plotScatter(coords,galplanera,galplanedec):

    plt.figure()
    for coord in coords: #stars
        plt.plot(coord.ra.hour,coord.dec,'b.')
    plt.plot(24*np.arange(0,1,.01),23.4*np.sin(np.arange(0,2*np.pi,2*np.pi/100)),'r-') #ecliptic (approx)
    plt.plot(galplanera,galplanedec,'y-') #galacticplane (exact)
    #plt.plot(galcoords.ra.hour,galcoords.dec,'y-')
    plt.ylabel("Dec (Degrees)")
    plt.xlabel("RA (Hours)")
    plt.xlim(24,0)
    plt.ylim(-90,90)
    plt.xticks(np.arange(24,0,-2))
    plt.yticks(np.arange(-90,90,15))
    plt.title("Solar Analog Distribution")
    plt.grid(True)
    #plt.savefig('SA_Plot.png')
    plt.show()

if __name__== "__main__":
    lines = readFile('/home/atedeschi/SAf.txt')
    coords = readCoords(lines)
    galplanera, galplanedec = genGalPlane()
    plotScatter(coords, galplanera,galplanedec)
    #galcoords = genGalPlane()
    #plotScatter(coords,galcoords)



