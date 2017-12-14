'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2017 LCO

photometry_subs.py -- Code for photometric transformations.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

def transform_Vmag(mag_V, passband, taxonomy='Mean'):
    '''
    Table 2. Asteroid magnitude transformations from Pan-STARRS1 AB filter magnitudes to the
    Johnson-Cousin V system based on Tonry et al. (2012). Solar colors are also included for
    reference.
    Taxonomy	V-gP1	V-rP1	V-iP1	V-zP1	V-yP1	V-wP1
    Sun	        -0.217	0.183	0.293	0.311	0.311	0.114
    Q	        -0.312  0.252   0.379   0.238   0.158   0.156
    S	        -0.325  0.275   0.470   0.416   0.411   0.199
    C	        -0.238  0.194   0.308   0.320   0.316   0.120
    D	        -0.281  0.246   0.460   0.551   0.627   0.191
    X	        -0.247  0.207   0.367   0.419   0.450   0.146

    Mean (S + C)	-0.28	0.23	0.39	0.37	0.36	0.16
    '''

    delta_mag = 0.23
    new_mag = mag_V - delta_mag

    return new_mag
