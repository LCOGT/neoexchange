#the goal of this code it to determind albedo and the diameter based on the albedo

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from astropy.modeling import models
from astropy.modeling import fitting
import random
import math

def albedo(f=0.253, bright=0.168, dark=0.03):
    '''This function generates a single albedo. It takes a dark fraction(f),      
     a dark peak(dark), and a bright peak(bright) and returns a value of albedo    
     for the given numbers.
     See Wright et al. The Astronomical Journal, 2016, 152, 79'''

    x = random.random()
    y = random.random() 

    if x < f:
        t = dark

    else:
        t = bright

    inside = -2.0 * (math.log(1.0 - y)) 
    a = t * math.sqrt(inside)
    return a


def albedo_distribution(f=0.253, bright=0.168, dark=0.03, a=albedo()):
    '''This function generates a single albedo distribution. It takes a dark 
    fraction(f), a dark peak(dark), a bright peak(bright), and an albedo(a) and 
    returns a value of albedo for the given numbers. Note that to use the default 
    you must also use the method 'albedo' which will generate a random albedo.
    See Wright et al. The Astronomical Journal, 2016, 152, 79'''
    
    top1 = a * math.exp((-a ** 2) / (2 * dark ** 2))
    top2 = a * math.exp((-a ** 2) / (2 * bright **2))
    prr = f * (top1 / dark ** 2) + (1 - f) * (top2 / bright ** 2)
    return prr


def asteroid_diameter(a=albedo(), h=7):
    '''This function calculates the diameter of an asteroid. It takes an albedo(a) 
    and a H magnitude(h). Note that to use the default you must also use the 
    method 'albedo' which generates a random albedo. Also note that the diameter 
    returned is in kilometers. 
    See Wright et al. The Astronomical Journal, 2016, 152, 79'''
    
    d = 1329 * math.sqrt(10 ** (-0.4 * h) / a)
    return d

#this is the x and y numbers to be plot. the equation was two fractions so I typed out the numerators to make things easier later and the inside of the sqrt	
#this will generate the x-axis number
a_data = []
prr_data = []
dia_data = []
fig, ax = plt.subplots()

for i in range(0, 5000):
    a1 = albedo()
    a_data.append(a1)
    prr = albedo_distribution(a=a1)
    prr_data.append(prr)
    di = asteroid_diameter(a=a1, h=20)
    dia_data.append(di)

#this should plot the points
num_bins = 100

n, bins, patches = ax.hist(a_data, num_bins, normed=1)
#n, bins, patches = ax.hist(dia_data, num_bins, normed=1)
for i in range(0, 5000):
    plt.plot(a_data[i], prr_data[i],'ko')
    

ax.set_xlabel('Pv')
ax.set_ylabel('P(Pv)')
ax.set_title(r'Near Earth Asteroid Albedo Distribution') 

fig.tight_layout()
plt.show()


#dia = asteroid_diameter(h=20)
#print dia 

