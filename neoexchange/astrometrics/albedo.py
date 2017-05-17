#the goal of this code it to determind albedo and the diameter based on the albedo
#import warnings
#import numpy as np
#import matplotlib.pyplot as plt
#from astropy.modeling import models, fitting 
import random


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
    print a



