#the goal of this code it to determind albedo and the diameter based on the albedo

import numpy as np
import matplotlib.pyplot as plt
from astropy.modeling import models, fitting 
import random

#this will generate the x-axis number
def albedo(x):

    x = random.random()
    y = random.random()
    
    f = 0.253
    bright = 0.0168
    dark = 0.03  
    
    if x < f:
        t = dark

    else:
        t = bright

    a = t * math.sqrt(-2 * math.log1p(1 - y))
    return a

print a

#this is the start of the plot for the random data generated in the function above (using astropy.modeling)
gg_init = models.Gaussian1D(2.5,0.15,0.1) + models.Gaussian1D(6,0.05,0.1)
fitter = fitting.SLSQPLSQFitter()
gg_fit = fitter(gg_init, x, y)

plt.figure(figsize=(8,7))
plt.plot(x, y, 'ko')
plt.plot(x, gg_fit(x))
plt.xlabel('Pv')
plt.ylabel('P(Pv)')


def diameter
