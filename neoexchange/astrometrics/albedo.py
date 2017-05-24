#the goal of this code it to determind albedo and the diameter based on the albedo

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from astropy.modeling import models, fitting
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

#this is the x and y numbers to be plot. the equation was two fractions so I typed out the numerators to make things easier later and the inside of the sqrt
    inside = -2.0 * (math.log(1.0 - y)) 
    a = t * math.sqrt(inside)
    return a
	
	
a_data = []
#this will generate the x-axis number

for i in range(0, 50000):
    a = albedo()
    a_data.append(a)


#this should plot the points
mu = 1.5
sigma = 0.027

num_bins = 100
fig, ax = plt.subplots()

n, bins, patches = ax.hist(a_data, num_bins)

ax.set_xlabel('Pv')
ax.set_ylabel('P(Pv)')
ax.set_title(r'Near Earth Asteroid Albedo Distribution') 

fig.tight_layout()
plt.show()
		
