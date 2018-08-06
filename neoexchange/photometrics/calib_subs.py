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
from math import log10

import numpy as np
import astropy.units as u
import synphot as syn

from photometrics.photometry_subs import compute_ab_zpt, construct_tic_params
from astrometrics.site_config import camtypes

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

def transform_magnitudes(mag_in, color, desired_filter):
    """Transform from GAIA-DR2 to Johnson magnitudes:
    Johnson-Cousins relationships.
    From Table 5.8 on
    https://gea.esac.esa.int/archive/documentation/GDR2/Data_processing/chap_cu5pho/sec_cu5pho_calibr/ssec_cu5pho_PhotTransf.html

                         V−I         (V−I)2    (V−I)3            σ
    G−V     -0.01746    0.008092    -0.2810     0.03655         0.04670
    GBP−V   -0.05204    0.4830      -0.2001     0.02186         0.04483
    GRP−V    0.0002428 -0.8675      -0.02866                    0.04474
    GBP−GRP -0.04212    1.286       -0.09494                    0.02366

                        GBP−GRP     (GBP−GRP)2                   σ
    G−V     -0.01760   -0.006860    -0.1732                     0.045858
    G−R     -0.003226   0.3833      -0.1345                     0.04840
    G−I      0.02085    0.7419      -0.09631                    0.04956
    """

    if desired_filter == 'V':
        mag_out = mag_in + 0.01746 - (0.008092*color) + (0.2810*color**2) - (0.03655*color**3)
    return mag_out

def compute_mb_obs(img_header, img_table, bpset):

    filt = img_header.get('filter', None)
    exptime = img_header.get('exptime', None)
    inst_type = camtypes.get(img_header.get('instrument', None), None)
    if filt and exptime and inst_type:
        tic_params = construct_tic_params(inst_type, filt)

        zpt_ab = compute_ab_zpt(tic_params)
        bp_integ = bpset.PassbandIntegral(filt)
        time_term = 2.5 * log10(exptime)
        bp_term = 2.5 * log10(bp_integ)
        print(filt,exptime,inst_type, tic_params, zpt_ab, bp_integ)

        mb_obs_column = []
        for source in img_table:
            mb_obs = -2.5 * log10(source['flux']) + time_term + bp_term + zpt_ab
            mb_obs_column.append(mb_obs)
        img_table['mb_obs'] = mb_obs_column * u.mag
    return img_table
