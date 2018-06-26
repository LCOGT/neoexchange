"""
convert 1D fits spectra into a readable plot
Written by Adam Tedeschi
Date: 6/25/2018
for NeoExchange
"""

from astropy.io import fits
from astropy.convolution import convolve, Box1DKernel
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

def smooth(indata, window):
	#Do error handling later
	smoothed_outdata = convolve(indata, Box1DKernel(window))
	#Is this the same size? I'll figure that out tomorrow

