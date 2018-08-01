'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2018-2018 LCO

calib_subs.py -- Code for photometric calibrations.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
import os

import synphot as syn

class BandPassSet(object):
    def __init__(self):
        """Initialize the class but don't do anything yet."""

        self.bandpass_int = {}
        self.filterlist = []

        return

    def setBandpassSet(self, bpDict, bpDictlist=('U', 'B', 'V', 'R', 'I', 'up', 'gp,', 'rp', 'ip', 'zs'), verbose=True):
        """Simply set throughputs from a pre-made dictionary."""
        if len(bpDictlist) != len(list(bpDict.keys())):
            bpDictList = list(bpDict.keys())
        self.bandpass = copy.deepcopy(bpDict)
        self.filterlist = copy.deepcopy(bpDictlist)
        return

    def setThroughputs(self, filterlist=('U', 'B', 'V', 'R', 'I', 'up', 'gp', 'rp', 'ip', 'zs'),
        rootdir="./", rootsuffix=".txt", verbose=True):
        bandpass = {}
        for f in filterlist:
            if f.isupper():
                filt_root = 'bssl-'
                filt_suffix = 'x'
                filt = f.lower()
            elif f.islower():
                filt_root = 'SDSS.'
                filt_suffix = ''
                filt = f
                if f == 'zs':
                    filt_root = 'PSTR-'
                    filt_suffix = '-avg'
                    filt = f.upper()
            filt_name = filt_root + filt + filt_suffix + rootsuffix
            filter_file = os.path.join(rootdir, filt_name)
            if verbose:
                print("Reading throughput file %s" %(filter_file))
            bandpass[f] = syn.SpectralElement.from_file(filter_file, wave_unit=syn.units.u.nm, flux_unit=syn.units.THROUGHPUT)
        # Set data in self.
        self.bandpass = bandpass
        self.filterlist = filterlist
        return

    def calcPassbandIntegral(self):
        """Calculate the integral with wavelength over the passband.
        This is equation 6 in Burke et al. 2018:
        :math:`\\mathbb{I}_0^{obs}(obs) \\equiv \\int_{0}^{\\inf} S_{b}^{obs}(\\lambda) \\lambda^{-1} d\\lambda`
        """

        for f in self.filterlist:
            if self.bandpass_int.get(f, None) is None:
                self.bandpass_int[f] = self.bandpass[f].efficiency()

        return self.bandpass_int

    def PassbandIntegral(self, filt):
        """Returns the passband integral for the passed filter <filt>.
        If the integral is not available, then they are calculated by calling
        self.calcPassbandIntegral()"""

        if filt in self.filterlist:
            if self.bandpass_int.get(filt, None) is None:
                bandpass_int = self.calcPassbandIntegral()
            return self.bandpass_int[filt]
        else:
            print("'{}' not found in filterlist {}".format(filt, self.filterlist))
        return
