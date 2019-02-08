"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

The goal of this code it to determine albedo and the diameter based on the albedo
"""

import numpy as np
from astropy.modeling import models
from astropy.modeling import fitting
import random
import math
import logging

logger = logging.getLogger(__name__)


def asteroid_albedo(f=0.253, bright=0.168, dark=0.03):
    """This function generates a single albedo. It takes a dark fraction(f),
     a dark peak(dark), and a bright peak(bright) and returns a value of albedo
     for the given numbers.
     See Wright et al. The Astronomical Journal, 2016, 152, 79"""

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
    """This function generates a single albedo distribution. It takes a dark
    fraction(f), a dark peak(dark), a bright peak(bright), and an albedo(a) and
    returns a value of albedo for the given numbers. Note that to use the default
    you must also use the method 'albedo' which will generate a random albedo.
    See Wright et al. The Astronomical Journal, 2016, 152, 79"""
    if 0.00 <= a <= 1:
        top1 = a * math.exp((-a ** 2) / (2 * dark ** 2))
        top2 = a * math.exp((-a ** 2) / (2 * bright ** 2))
        prr = f * (top1 / dark ** 2) + (1 - f) * (top2 / bright ** 2)
        return prr
    else:
        logger.debug("Check your albedo")
        return False


def asteroid_diameter(a=asteroid_albedo(), h=7):
    """This function calculates the diameter of an asteroid. It takes an albedo(a)
    and a H magnitude(h). Note that to use the default you must also use the
    method 'albedo' which generates a random albedo. Also note that the diameter
    returned is in meters.
    See Wright et al. The Astronomical Journal, 2016, 152, 79"""

    try:
        h = float(h)
    except (TypeError, ValueError):
        logger.warning("Could not convert H magnitude to a float")
        return None

    if a <= 0.00:
        logger.debug("You cannot have a negative albedo")
        return False
    elif h < -90:
        logger.warning('Nothing brighter than -90, must be a flag.')
        return None
    else:
        try:
            diameter = 1329000 * math.sqrt((10 ** (-0.4 * h)) / a)
            return diameter
        except (TypeError, ValueError):
            return None
