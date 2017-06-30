#the goal of this code it to determind albedo and the diameter based on the albedo

import numpy as np
from astropy.modeling import models
from astropy.modeling import fitting
import random
import math

def asteroid_albedo(f=0.253, bright=0.168, dark=0.03):
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
    albedo = t * math.sqrt(inside)
    return albedo


def albedo_distribution(f=0.253, bright=0.168, dark=0.03, a=asteroid_albedo()):
    '''This function generates a single albedo distribution. It takes a dark
    fraction(f), a dark peak(dark), a bright peak(bright), and an albedo(a) and
    returns a value of albedo for the given numbers. Note that to use the default
    you must also use the method 'albedo' which will generate a random albedo.
    See Wright et al. The Astronomical Journal, 2016, 152, 79'''
    if a >= 0.00 and a <= 1:
        top1 = a * math.exp((-a ** 2) / (2 * dark ** 2))
        top2 = a * math.exp((-a ** 2) / (2 * bright **2))
        prr = f * (top1 / dark ** 2) + (1 - f) * (top2 / bright ** 2)
        return prr
    else:
        logger.debug("Check your albedo")
        return False

def asteroid_diameter(a=asteroid_albedo(), h=7):
    '''This function calculates the diameter of an asteroid. It takes an albedo(a)
    and a H magnitude(h). Note that to use the default you must also use the
    method 'albedo' which generates a random albedo. Also note that the diameter
    returned is in meters.
    See Wright et al. The Astronomical Journal, 2016, 152, 79'''

    if a <= 0.00:
        logger.debut("You cannot have a negative albedo")
        return False
    else:
        diameter = 1329000 * math.sqrt((10 ** (-0.4 * h)) / a)
        return diameter
