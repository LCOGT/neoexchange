"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""
import logging
from math import pi, log10, sqrt, cos, ceil

from django.db import models
from django.utils.translation import gettext_lazy as _

from astrometrics.ast_subs import normal_to_packed
from astrometrics.ephem_subs import get_sitecam_params
from astrometrics.time_subs import dttodecimalday, degreestohms, degreestodms
from astrometrics.sources_subs import translate_catalog_code, psv_padding

from core.models.body import Body
from core.models.frame import Frame

logger = logging.getLogger(__name__)


class SourceMeasurement(models.Model):
    """Class to represent the measurements (RA, Dec, Magnitude and errors)
    performed on a Frame (having site code, date/time etc.).
    These will provide the way of storing past measurements of an object and
    any new measurements performed on data from the LCOGT NEO Follow-up Network
    """

    body = models.ForeignKey(Body, on_delete=models.CASCADE)
    frame = models.ForeignKey(Frame, on_delete=models.CASCADE)
    obs_ra = models.FloatField('Observed RA', blank=True, null=True, db_index=True)
    obs_dec = models.FloatField('Observed Dec', blank=True, null=True, db_index=True)
    obs_mag = models.FloatField('Observed Magnitude', blank=True, null=True, db_index=True)
    err_obs_ra = models.FloatField('Error on Observed RA', blank=True, null=True)
    err_obs_dec = models.FloatField('Error on Observed Dec', blank=True, null=True)
    err_obs_mag = models.FloatField('Error on Observed Magnitude', blank=True, null=True)
    astrometric_catalog = models.CharField('Astrometric catalog used', max_length=40, default=' ')
    photometric_catalog = models.CharField('Photometric catalog used', max_length=40, default=' ')
    aperture_size = models.FloatField('Size of aperture (arcsec)', blank=True, null=True)
    snr = models.FloatField('Size of aperture (arcsec)', blank=True, null=True)
    flags = models.CharField('Frame Quality flags', help_text='Comma separated list of frame/condition flags', max_length=40, blank=True, default=' ')

    def format_mpc_line(self, include_catcode=False):
        """Format the contents of 'self' (a SourceMeasurement i.e. the confirmed
        measurement of an object on a particular frame) into MPC 1992 80 column
        format. This handles the discovery asterisk in column 12, some of the mapping
        from flags into the MPC codes in column 14, mapping of non-standard
        filters and potentially inclusion of the catalog code in column 72 (if
        [include_catcode] is True; catalog code should not be included in new
        submissions to the MPC)"""

        if self.body.name:
            name, status = normal_to_packed(self.body.name)
            if status != 0:
                name = "%5s       " % self.body.name
        else:
            name = "     %7s" % self.body.provisional_name

        try:
            mag = "%4.1f" % self.obs_mag
        except TypeError:
            mag = "    "

        microday = True

        valid_MPC_notes = ['A', 'P', 'e', 'C', 'B', 'T', 'M', 'V', 'v', 'R', 'r', 'S', 's',\
            'c', 'E', 'O', 'H', 'N', 'n', 'D', 'Z', 'W', 'w', 'Q', 'q', 'T', 't']
        if self.frame.extrainfo in valid_MPC_notes:
            obs_type = self.frame.extrainfo
            if obs_type == 'A':
                microday = False
        else:
            obs_type = 'C'

        if self.frame.frametype == Frame.SATELLITE_FRAMETYPE:
            obs_type = 'S'
            microday = False
        flags = self.flags
        num_flags = flags.split(',')
        if len(num_flags) == 1:
            if num_flags[0] == '*':
                # Discovery asterisk needs to go into column 13
                flags = '* '
            else:
                flags = ' ' + num_flags[0]
        elif len(num_flags) == 2:
            if '*' in num_flags:
                asterisk_index = num_flags.index('*')
                flags = '*' + num_flags[1-asterisk_index]
            else:
                logger.warning("Flags longer than will fit into field - needs mapper")
                flags = ' ' + num_flags[0]
        else:
            logger.warning("Flags longer than will fit into field - needs mapper")
            if '*' in num_flags:
                num_flags.remove('*')
                flags = '*' + num_flags[0]
            else:
                flags = ' ' + num_flags[0]

        # Catalog code for column 72 (if desired)
        catalog_code = ' '
        if include_catcode is True:
            catalog_code = translate_catalog_code(self.astrometric_catalog)
        mpc_line = "%12s%2s%1s%16s%11s %11s          %4s %1s%1s     %3s" % (name,
            flags, obs_type, dttodecimalday(self.frame.midpoint, microday),
            degreestohms(self.obs_ra, ' '), degreestodms(self.obs_dec, ' '),
            mag, self.frame.map_filter(), catalog_code, self.frame.sitecode)
        if self.frame.frametype == Frame.SATELLITE_FRAMETYPE:
            extrainfo = self.frame.extrainfo
            if extrainfo:
                if self.body.name:
                    name, status = normal_to_packed(self.body.name)
                    if status == 0:
                        extrainfo = name + extrainfo[12:]
            else:
                extrainfo = ''
            mpc_line = mpc_line + '\n' + extrainfo
        return mpc_line

    def _numdp(self, value):
        """Calculate number of d.p. following prescription in Figure 1 of
        ADES description (https://github.com/IAU-ADES/ADES-Master/blob/master/ADES_Description.pdf)
        """

        num_dp = 1
        if value is not None and value > 0:
            num_dp = ceil(1-log10(value))
        return num_dp

    def format_psv_header(self):

        tbl_hdr = ""
        rms_available = False
        if self.err_obs_ra and self.err_obs_dec and self.err_obs_mag:
            rms_available = True
            rms_tbl_fmt = '%-7s|%-11s|%-8s|%-4s|%-4s|%-23s|%-11s|%-11s|%-5s|%-6s|%-8s|%-5s|%-6s|%-4s|%-8s|%-6s|%-6s|%-6s|%-5s|%-s'
            tbl_hdr = rms_tbl_fmt % ('permID ', 'provID', 'trkSub  ', 'mode', 'stn', 'obsTime', \
                'ra', 'dec', 'rmsRA', 'rmsDec', 'astCat', 'mag', 'rmsMag', 'band', 'photCat', \
                'photAp', 'logSNR', 'seeing', 'notes', 'remarks')
        else:
            tbl_fmt = '%-7s|%-11s|%-8s|%-4s|%-4s|%-23s|%-11s|%-11s|%-8s|%-5s|%-4s|%-8s|%-5s|%-s'
            tbl_hdr = tbl_fmt % ('permID ', 'provID', 'trkSub  ', 'mode', 'stn', 'obsTime', \
                'ra'.ljust(11), 'dec'.ljust(11), 'astCat', 'mag', 'band', 'photCat', 'notes', 'remarks')
        return tbl_hdr

    def format_psv_line(self):
        psv_line = ""

        rms_available = False
        if self.err_obs_ra and self.err_obs_dec and self.err_obs_mag:
            rms_available = True
            # Add RMS of Frame astrometric fit (in arcsec) to stored source
            # standard deviations (in deg; already converted from SExtractor
            # variances->standard deviations in get_catalog_items() & convert_value())
            if self.frame.rms_of_fit:
                err_obs_ra = sqrt(self.err_obs_ra**2 + ((self.frame.rms_of_fit/3600.0)**2))
                err_obs_dec = sqrt(self.err_obs_dec**2 + ((self.frame.rms_of_fit/3600.0)**2))
            else:
                err_obs_ra = self.err_obs_ra
                err_obs_dec = self.err_obs_dec

        if self.body.name:
            if len(self.body.name) > 4 and self.body.name[0:4].isdigit():
                provisional_name = self.body.name
                body_name = ''
            else:
                body_name = self.body.name
                provisional_name = ''
            tracklet_name = ''
        else:
            tracklet_name = self.body.provisional_name
            provisional_name = ''
            body_name = ''
        obs_type = 'CCD'
        remarks = ''

        obsTime = self.frame.midpoint
        obsTime = obsTime.strftime("%Y-%m-%dT%H:%M:%S")
        frac_time = "{:.2f}Z".format(self.frame.midpoint.microsecond / 1e6)
        obsTime = obsTime + frac_time[1:]
        ast_catalog_code = translate_catalog_code(self.frame.astrometric_catalog, ades_code=True)
        if (self.frame.astrometric_catalog is None or self.frame.astrometric_catalog.strip() == '')\
            and self.astrometric_catalog is not None:
            ast_catalog_code = translate_catalog_code(self.astrometric_catalog, ades_code=True)
        phot_catalog_code = translate_catalog_code(self.frame.photometric_catalog, ades_code=True)
        if (self.frame.photometric_catalog is None or self.frame.photometric_catalog.strip() == '')\
            and self.photometric_catalog is not None:
            phot_catalog_code = translate_catalog_code(self.photometric_catalog, ades_code=True)
        if phot_catalog_code == '' and ast_catalog_code != '':
            phot_catalog_code = ast_catalog_code

        prec = 6
        if self.err_obs_ra:
            prec = self._numdp(err_obs_ra)
        fmt_ra = "{ra:.{prec}f}".format(prec=prec, ra=self.obs_ra)
        fmt_ra, width, dpos = psv_padding(fmt_ra, 11, 'D', 4)
        prec = 6
        if self.err_obs_dec:
            prec = self._numdp(err_obs_dec)
        fmt_dec = "{dec:.{prec}f}".format(prec=prec, dec=self.obs_dec)
        fmt_dec, width, dpos = psv_padding(fmt_dec, 11, 'D', 4)
        fmt_filter = " "
        if self.obs_mag is not None:
            fmt_mag = "{:4.1f}".format(float(self.obs_mag))
            fmt_filter = self.frame.map_filter()
        else:
            fmt_mag = " "*5
            phot_catalog_code = " "

        tbl_fmt     = '%7s|%-11s|%8s|%4s|%-4s|%-23s|%11s|%11s|%8s|%-5s|%4s|%8s|%-5s|%-s'
        rms_tbl_fmt = '%7s|%-11s|%8s|%4s|%-4s|%-23s|%11s|%11s|%5s|%6s|%8s|%-5s|%6s|%4s|%8s|%6s|%6s|%6s|%-5s|%-s'
        if rms_available:
            rms_ra = "{value:.{prec}f}".format(prec=self._numdp(err_obs_ra * 3600.0), value=err_obs_ra * 3600.0)
            rms_dec = "{value:.{prec}f}".format(prec=self._numdp(err_obs_dec * 3600.0), value=err_obs_dec * 3600.0)
            if self.obs_mag is not None:
                rms_mag = "{value:.{prec}f}".format(prec=self._numdp(self.err_obs_mag), value=self.err_obs_mag)
                rms_mag, width, dpos = psv_padding(rms_mag, 6, 'D', 2)
            else:
                rms_mag = " "

            phot_ap = " "*6
            if self.aperture_size:
                phot_ap = "{:6.2f}".format(self.aperture_size)
            log_snr = " "*6
            if self.snr and self.snr > 0:
                log_snr = "{:6.4f}".format(log10(self.snr))
            fwhm = " "*6
            if self.frame.fwhm:
                fwhm = "{:6.4f}".format(self.frame.fwhm)

            psv_line = rms_tbl_fmt % (body_name, provisional_name, tracklet_name, obs_type, self.frame.sitecode, \
                obsTime, fmt_ra, fmt_dec, rms_ra, rms_dec,\
                ast_catalog_code, fmt_mag, rms_mag, fmt_filter, \
                phot_catalog_code, phot_ap, log_snr, fwhm, self.flags, remarks)
        else:
            psv_line = tbl_fmt % (body_name, provisional_name, tracklet_name, obs_type, self.frame.sitecode, \
                obsTime, fmt_ra, fmt_dec, ast_catalog_code,\
                fmt_mag, fmt_filter, phot_catalog_code, self.flags, remarks)
        return psv_line

    class Meta:
        verbose_name = _('Source Measurement')
        verbose_name_plural = _('Source Measurements')
        db_table = 'source_measurement'


class CatalogSources(models.Model):
    """Class to represent the measurements (X, Y, RA, Dec, Magnitude, shape and
    errors) extracted from a catalog extraction performed on a Frame (having
    site code, date/time etc.). These will allow the storage of information for
    reference stars and candidate objects, allowing the display and measurement
    of objects.
    """

    frame = models.ForeignKey(Frame, on_delete=models.CASCADE)
    obs_x = models.FloatField('CCD X co-ordinate', db_index=True)
    obs_y = models.FloatField('CCD Y co-ordinate', db_index=True)
    obs_ra = models.FloatField('Observed RA', db_index=True)
    obs_dec = models.FloatField('Observed Dec', db_index=True)
    obs_mag = models.FloatField('Observed Magnitude', blank=True, null=True)
    err_obs_ra = models.FloatField('Error on Observed RA', blank=True, null=True)
    err_obs_dec = models.FloatField('Error on Observed Dec', blank=True, null=True)
    err_obs_mag = models.FloatField('Error on Observed Magnitude', blank=True, null=True)
    background = models.FloatField('Background')
    major_axis = models.FloatField('Ellipse major axis')
    minor_axis = models.FloatField('Ellipse minor axis')
    position_angle = models.FloatField('Ellipse position angle')
    ellipticity = models.FloatField('Ellipticity')
    aperture_size = models.FloatField('Size of aperture (arcsec)', blank=True, null=True)
    flags = models.IntegerField('Source flags', help_text='Bitmask of flags', default=0)
    flux_max = models.FloatField('Peak flux above background', blank=True, null=True)
    threshold = models.FloatField('Detection threshold above background', blank=True, null=True)

    class Meta:
        verbose_name = _('Catalog Source')
        verbose_name_plural = _('Catalog Sources')
        db_table = 'catalog_source'

    def make_elongation(self):
        elongation = self.major_axis/self.minor_axis
        return elongation

    def make_fwhm(self):
        fwhm = ((self.major_axis+self.minor_axis)/2)*2
        return fwhm

    def make_mu_max(self):
        pixel_scale = get_sitecam_params(self.frame.sitecode)['pixel_scale']
        mu_max = 0.0
        if self.flux_max > 0.0:
            mu_max = (-2.5*log10(self.flux_max/pixel_scale**2))+self.frame.zeropoint
        return mu_max

    def make_mu_threshold(self):
        pixel_scale = get_sitecam_params(self.frame.sitecode)['pixel_scale']
        mu_threshold = 0.0
        if self.threshold > 0.0:
            mu_threshold = (-2.5*log10(self.threshold/pixel_scale**2))+self.frame.zeropoint
        return mu_threshold

    def make_flux(self):
        flux = 10.0**((self.obs_mag-self.frame.zeropoint)/-2.5)
        return flux

    def make_area(self):
        area = pi*self.major_axis*self.minor_axis
        return area

    def make_snr(self):
        snr = None
        if self.obs_mag > 0.0 and self.err_obs_mag > 0.0:
            snr = 1.0 / self.err_obs_mag
        return snr

    def map_numeric_to_mpc_flags(self):
        """Maps SExtractor numeric flags to MPC character flags
        FLAGS contains, coded in decimal, all the extraction flags as a sum
        of powers of 2:
        1:  The object has neighbours, bright and close enough to significantly
            bias the MAG_AUTO photometry, or bad pixels (more than 10% of the
            integrated area affected),
        2:  The object was originally blended with another one,
        4:  At least one pixel of the object is saturated (or very close to),
        8:  The object is truncated (too close to an image boundary),
        16: Object's aperture data are incomplete or corrupted,
        32: Object's isophotal data are incomplete or corrupted (SExtractor V1 compat; no consequence),
        64: A memory overflow occurred during deblending,
        128:A memory overflow occurred during extraction.
        """

        flag = ' '
        if 1 <= self.flags <= 3:
            # Set 'Involved with star'
            flag = 'I'
        elif self.flags >= 8:
            # Set 'close to Edge'
            flag = 'E'
        return flag


class StaticSource(models.Model):
    """
    Class for static (sidereal) sources, normally calibration sources (solar
    standards, RV standards, flux standards etc)
    """
    UNKNOWN_SOURCE = 0
    FLUX_STANDARD = 1
    RV_STANDARD = 2
    SOLAR_STANDARD = 4
    SPECTRAL_STANDARD = 8
    REFERENCE_FIELD = 16
    SOURCETYPE_CHOICES = [
                            (UNKNOWN_SOURCE, 'Unknown source type'),
                            (FLUX_STANDARD, 'Spectrophotometric standard'),
                            (RV_STANDARD, 'Radial velocity standard'),
                            (SOLAR_STANDARD, 'Solar spectrum standard'),
                            (SPECTRAL_STANDARD, 'Spectral standard'),
                            (REFERENCE_FIELD, 'Reference field')
                         ]

    name = models.CharField('Name of calibration source', max_length=55, db_index=True)
    ra = models.FloatField('RA of source (degrees)', db_index=True)
    dec = models.FloatField('Dec of source (degrees)', db_index=True)
    pm_ra = models.FloatField('Proper motion in RA of source (pmra*cos(dec); mas/yr)', default=0.0)
    pm_dec = models.FloatField('Proper motion in Dec of source (mas/yr)', default=0.0)
    parallax = models.FloatField('Parallax (mas)', default=0.0)
    vmag = models.FloatField('V magnitude')
    spectral_type = models.CharField('Spectral type of source', max_length=10, blank=True)
    source_type = models.IntegerField('Source Type', null=False, blank=False, default=0, choices=SOURCETYPE_CHOICES)
    notes = models.TextField(blank=True)
    quality = models.SmallIntegerField('Source quality', default=0, blank=True, null=True)
    reference = models.CharField('Reference for the source', max_length=255, blank=True)

    def return_source_type(self):
        srctype_name = "Undefined type"
        srctype = [x[1] for x in self.SOURCETYPE_CHOICES if x[0] == self.source_type]
        if len(srctype) == 1:
            srctype_name = srctype[0]
        return srctype_name

    def current_name(self):
        return self.name

    def full_name(self):
        return self.name

    class Meta:
        verbose_name = _('Static Source')
        verbose_name_plural = _('Static Sources')
        db_table = 'ingest_staticsource'

    def __str__(self):
        return "{} ({})".format(self.name, self.return_source_type())
