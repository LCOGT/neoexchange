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
from datetime import datetime, timedelta
from math import degrees
import logging

from astropy.time import Time
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.forms.models import model_to_dict

from astrometrics.ephem_subs import compute_ephem, comp_FOM, comp_sep
from astrometrics.albedo import asteroid_diameter


OBJECT_TYPES = (
                ('N', 'NEO'),
                ('A', 'Asteroid'),
                ('C', 'Comet'),
                ('K', 'TNO'),
                ('E', 'Centaur'),
                ('T', 'Trojan'),
                ('U', 'Candidate'),
                ('X', 'Did not exist'),
                ('W', 'Was not interesting'),
                ('D', 'Discovery, non NEO'),
                ('J', 'Artificial satellite'),
                ('M', 'Natural Satellite'),
                ('P', 'Major Planet')
            )

OBJECT_SUBTYPES = (
                ('N', 'NEO'),
                ('N1', 'Atira'),             # Q<1AU
                ('N2', 'Aten'),              # a<1AU<Q
                ('N3', 'Apollo'),            # q<1AU<a
                ('N4', 'Amor'),              # 1AU<q<1.3AU
                ('PH', 'PHA'),
                ('MI', 'Inner Main-Belt'),   # a < 2.0 au; q > 1.666 au
                ('M', 'Main-Belt'),
                ('MO', 'Outer Main-Belt'),   # 3.2 au < a < 4.6 au
                ('A', 'Active'),
                ('MH', 'Hilda'),             # 3/2 resonance w/ Jupiter
                ('T4', 'L4'),
                ('T5', 'L5'),
                ('P1', 'Mercury'),
                ('P2', 'Venus'),
                ('P3', 'Earth'),
                ('P4', 'Mars'),
                ('P5', 'Jupiter'),
                ('P6', 'Saturn'),
                ('P7', 'Uranus'),
                ('P8', 'Neptune'),
                ('P9', 'Pluto'),
                ('PL', 'Plutino'),
                ('K', 'Classical KBO'),
                ('S', 'SDO'),
                ('H', 'Hyperbolic'),
                ('PA', 'Parabolic'),
                ('JF', 'Jupiter Family'),   # P < 20 y
                ('HT', 'Halley-Type'),      # 20 y < P < 200 y
                ('LP', 'Long Period'),      # P > 200 y
                ('DN', 'Dynamically New'),  # Dynamically New Comet
                ('DO', 'Dynamically Old')   # Dynamically Old Comet
            )


ELEMENTS_TYPES = (('MPC_MINOR_PLANET', 'MPC Minor Planet'), ('MPC_COMET', 'MPC Comet'))

ORIGINS = (
            ('M', 'Minor Planet Center'),
            ('N', 'NASA'),
            ('S', 'Spaceguard'),
            ('D', 'NEODSYS'),
            ('G', 'Goldstone'),
            ('A', 'Arecibo'),
            ('R', 'Goldstone & Arecibo'),
            ('L', 'LCOGT'),
            ('Y', 'Yarkovsky'),
            ('T', 'Trojan'),
            ('O', 'LOOK Project')
            )

DESIG_CHOICES = (
                ('N', 'Name'),
                ('#', 'Number'),
                ('P', 'Provisional Designation'),
                ('C', 'NEO Candidate Designation'),
                ('T', 'Temporary Designation')
                )

PARAM_CHOICES = (
                ('H', 'Absolute Magnitude'),
                ('G', 'Phase Slope'),
                ('D', 'Diameter'),
                ('R', 'Density'),
                ('P', 'Rotation Period'),
                ('A', 'LC Amplitude'),
                ('O', 'Pole Orientation'),
                ('ab', 'Albedo'),
                ('Y', 'Yarkovsky Drift'),
                ('E', 'Coma Extent'),
                ('M', 'Mass'),
                ('/a', 'Reciprocal of semimajor axis')
                )

STATUS_CHOICES = (
                ('0', 'No Analysis Done'),
                ('1', 'Light Curve Analysis Done'),
                ('2', 'Spectroscopic Analysis Done'),
                ('3', 'LC & Spec Analysis Done'),
                ('10', 'More Observations Needed'),
                ('20', 'Published'),
                ('99', 'No usable Data')
                )

logger = logging.getLogger(__name__)


class Body(models.Model):
    provisional_name    = models.CharField('Provisional MPC designation', max_length=15, blank=True, null=True, db_index=True)
    provisional_packed  = models.CharField('MPC name in packed format', max_length=7, blank=True, null=True, db_index=True)
    name                = models.CharField('Designation', max_length=15, blank=True, null=True, db_index=True)
    origin              = models.CharField('Where did this target come from?', max_length=1, choices=ORIGINS, default="M", blank=True, null=True)
    source_type         = models.CharField('Type of object', max_length=1, choices=OBJECT_TYPES, blank=True, null=True)
    source_subtype_1    = models.CharField('Subtype of object', max_length=2, choices=OBJECT_SUBTYPES, blank=True, null=True)
    source_subtype_2    = models.CharField('Subtype of object', max_length=2, choices=OBJECT_SUBTYPES, blank=True, null=True)
    elements_type       = models.CharField('Elements type', max_length=16, choices=ELEMENTS_TYPES, blank=True, null=True)
    active              = models.BooleanField('Actively following?', default=False)
    fast_moving         = models.BooleanField('Is this object fast?', default=False)
    urgency             = models.IntegerField(help_text='how urgent is this?', blank=True, null=True)
    epochofel           = models.DateTimeField('Epoch of elements', blank=True, null=True)
    orbit_rms           = models.FloatField('Orbit quality of fit', blank=True, null=True, default=99.0)
    orbinc              = models.FloatField('Orbital inclination in deg', blank=True, null=True)
    longascnode         = models.FloatField('Longitude of Ascending Node (deg)', blank=True, null=True)
    argofperih          = models.FloatField('Arg of perihelion (deg)', blank=True, null=True)
    eccentricity        = models.FloatField('Eccentricity', blank=True, null=True)
    meandist            = models.FloatField('Mean distance (AU)', blank=True, null=True, help_text='for asteroids')
    meananom            = models.FloatField('Mean Anomaly (deg)', blank=True, null=True, help_text='for asteroids')
    perihdist           = models.FloatField('Perihelion distance (AU)', blank=True, null=True, help_text='for comets')
    epochofperih        = models.DateTimeField('Epoch of perihelion', blank=True, null=True, help_text='for comets')
    abs_mag             = models.FloatField('H - absolute magnitude', blank=True, null=True)
    slope               = models.FloatField('G - slope parameter', blank=True, null=True)
    score               = models.IntegerField(help_text='NEOCP digest2 score', blank=True, null=True)
    discovery_date      = models.DateTimeField(blank=True, null=True)
    num_obs             = models.IntegerField('Number of observations', blank=True, null=True)
    arc_length          = models.FloatField('Length of observed arc (days)', blank=True, null=True)
    not_seen            = models.FloatField('Time since last observation (days)', blank=True, null=True)
    updated             = models.BooleanField('Has this object been updated?', default=False)
    ingest              = models.DateTimeField(default=datetime.utcnow, db_index=True)
    update_time         = models.DateTimeField(blank=True, null=True, db_index=True)
    analysis_status     = models.CharField('Current Analysis Status', max_length=2, choices=STATUS_CHOICES, db_index=True, default='0')
    as_updated          = models.DateTimeField(blank=True, null=True, db_index=True)

    def _compute_period(self):
        period = None
        if self.eccentricity:
            period = 1e99
            if self.eccentricity < 1.0:
                if self.perihdist:
                    a_au = self.perihdist / (1.0 - self.eccentricity)
                else:
                    a_au = self.meandist
                period = pow(a_au, (3.0/2.0))
        return period

    def _compute_one_over_a(self):
        # Returns the reciprocal semi-major axis (1/a) from the PhysicalProperties if present
        recip_a = None
        try:
            recip_a_par = PhysicalParameters.objects.get(body=self.id, parameter_type='/a', preferred=True, value__isnull=False)
            recip_a = recip_a_par.value
        except PhysicalParameters.DoesNotExist:
            recip_a = None
        except PhysicalParameters.MultipleObjectsReturned:
            logger.warning("Multiple preferred values exist for 1/a parameter for %s", self.current_name())
            recip_a = None
        return recip_a

    period = property(_compute_period)
    recip_a = property(_compute_one_over_a)
    one_over_a  = property(_compute_one_over_a)

    def characterization_target(self):
        # If we change the definition of Characterization Target,
        # also update views.get_characterization_targets
        if self.active is True and self.origin != 'M' and self.source_type != 'U':
            return True
        else:
            return False

    def radar_target(self):
        # Returns True if the object is a radar target
        if self.active is True and (self.origin == 'A' or self.origin == 'G' or self.origin == 'R'):
            return True
        else:
            return False

    def diameter(self):
        m = self.abs_mag
        avg = 0.167
        d_avg = asteroid_diameter(avg, m)
        return d_avg

    def diameter_range(self):
        m = self.abs_mag
        mn = 0.01
        mx = 0.6
        d_max = asteroid_diameter(mn, m)
        d_min = asteroid_diameter(mx, m)
        return d_min, d_max

    def epochofel_mjd(self):
        mjd = None
        try:
            t = Time(self.epochofel.isoformat(), format='isot', scale='tt')
            mjd = t.mjd
        except:
            pass
        return mjd

    def epochofperih_mjd(self):
        mjd = None
        try:
            t = Time(self.epochofperih.isoformat(), format='isot', scale='tt')
            mjd = t.mjd
        except:
            pass
        return mjd

    def current_name(self):
        if self.name:
            return self.name
        elif self.provisional_name:
            return self.provisional_name
        else:
            return "Unknown"

    def full_name(self):
        name = Designations.objects.filter(body=self.id).filter(desig_type='N').filter(preferred=True)
        num = Designations.objects.filter(body=self.id).filter(desig_type='#').filter(preferred=True)
        prov_dev = Designations.objects.filter(body=self.id).filter(desig_type='P').filter(preferred=True)
        fname = ''
        if num:
            fname += num[0].value
            if not fname.isdigit() and name:
                fname += '/'
        if name:
            if fname and fname.isdigit():
                fname += ' '
            fname += name[0].value
        if fname and prov_dev:
            fname += ' ({})'.format(prov_dev[0].value)
        elif prov_dev:
            fname += prov_dev[0].value
        if not fname:
            fname = self.current_name()

        return fname

    def old_name(self):
        if self.provisional_name and self.name:
            return self.provisional_name
        else:
            return False

    def compute_position(self, d=None):
        d = d or datetime.utcnow()
        if self.epochofel:
            orbelems = model_to_dict(self)
            sitecode = '500'
            emp_line = compute_ephem(d, orbelems, sitecode, dbg=False, perturb=False, display=False)
            if not emp_line:
                return False
            else:
                # Return just numerical values
                return emp_line['ra'], emp_line['dec'], emp_line['mag'], emp_line['southpole_sep'], emp_line['sky_motion'], emp_line['sky_motion_pa']
        else:
            # Catch the case where there is no Epoch
            return False

    def compute_distances(self, d=None):
        d = d or datetime.utcnow()
        if self.epochofel:
            orbelems = model_to_dict(self)
            sitecode = '500'
            emp_line = compute_ephem(d, orbelems, sitecode, dbg=False, perturb=False, display=False)
            if not emp_line:
                return False
            else:
                # Return just distance values
                return emp_line['earth_obj_dist'], emp_line['sun_obj_dist']
        else:
            # Catch the case where there is no Epoch
            return False

    def compute_obs_window(self, d=None, dbg=False):
        """
        Compute rough window during which target may be observable based on when it is brighter than a
        given mag_limit amd further from the sun than sep_limit.
        """
        if not isinstance(d, datetime):
            d = datetime.utcnow()
        d0 = d
        df = 90  # days to look forward
        delta_t = 10  # size of steps in days
        mag_limit = 18
        sep_limit = 45  # degrees away from Sun
        i = 0
        dstart = ''
        dend = ''
        if self.epochofel:
            if dbg:
                logger.debug('Body: {}'.format(self.name))
            orbelems = model_to_dict(self)
            sitecode = '500'
            # calculate the ephemeris for each step (delta_t) within the time span df.
            while i <= df / delta_t + 1:

                ephem_out = compute_ephem(d, orbelems, sitecode, dbg=False, perturb=False, display=False)
                mag_dot = ephem_out['mag_dot']
                separation = ephem_out['sun_sep']
                vmag = ephem_out['mag']

                # Eliminate bad magnitudes
                if vmag < 0:
                    return dstart, dend, d0

                # Calculate time since/until reaching Magnitude limit
                t_diff = (mag_limit - vmag) / mag_dot
                if abs(t_diff) > 10000:
                    t_diff = 10000*t_diff/abs(t_diff)

                # create separation test.
                sep_test = degrees(separation) > sep_limit

                # Filter likely results based on Mag/mag_dot to speed results.
                # Cuts load time by 60% will occasionally and temporarily miss
                # objects with either really short windows or unusual behavior
                # at the edges. These objects will be found as the date changes.

                # Check first and last dates first
                if d == d0 + timedelta(days=df) and i == 1:
                    # if Valid for beginning and end of window, assume valid for window
                    if vmag <= mag_limit and dstart and sep_test:
                        if dbg:
                            logger.debug("good at begining and end, mag: {}, sep {}".format(vmag, sep_test))
                        return dstart, dend, d0
                    elif not dstart:
                        # If not valid for beginning of window or end of window, check if Change in mag implies it will ever be good.
                        if d + timedelta(days=t_diff) < d0 or d + timedelta(days=t_diff) > d0 + timedelta(days=df):
                            if dbg:
                                logger.debug("bad at begining and end, Delta Mag no good, mag:{}, sep: {}".format(vmag, sep_test))
                            return dstart, dend, d0
                        else:
                            d = d0 + timedelta(days=delta_t)
                    else:
                        d = d0 + timedelta(days=delta_t)
                # if a valid start has been found, check if we are now invalid. Exit if so.
                elif (vmag > mag_limit or not sep_test) and dstart:
                    dend = d
                    if dbg:
                        logger.debug("Ended at {}, mag: {}, sep: {}".format(i, vmag, sep_test))
                    return dstart, dend, d0
                # If no start date, and we are valid, set start date
                elif vmag <= mag_limit and not dstart and sep_test:
                    dstart = d
                    if dbg:
                        logger.debug("started at {}, mag: {}, sep: {}".format(i, vmag, sep_test))
                    # if this is our first iteration (i.e. we started valid) test end date
                    if i == 0:
                        d += timedelta(days=df)
                    # otherwise step forward
                    else:
                        d += timedelta(days=delta_t)
                # if we are not valid from the start, check if we might be valid in middle. Otherwise, check end.
                elif vmag > mag_limit and i == 0:
                    if d + timedelta(days=t_diff) < d0 or d + timedelta(days=t_diff) > d0 + timedelta(days=df):
                        d += timedelta(days=df)
                    else:
                        d += timedelta(days=delta_t)
                # if nothing has changed, step forward.
                else:
                    d += timedelta(days=delta_t)
#                d += timedelta(days=delta_t)
                i += 1
            # Return dates
            if dbg:
                logger.debug("no end change, mag: {}, sep: {}".format(vmag, sep_test))
            return dstart, dend, d0
        else:
            # Catch the case where there is no Epoch
            return False

    def compute_FOM(self):
        d = datetime.utcnow()
        if self.epochofel:
            orbelems = model_to_dict(self)
            sitecode = '500'
            emp_line = compute_ephem(d, orbelems, sitecode, dbg=False, perturb=False, display=False)
            if 'U' in orbelems['source_type'] and orbelems['not_seen'] is not None and orbelems['arc_length'] is not None and orbelems['score'] is not None:
                FOM = comp_FOM(orbelems, emp_line)
                return FOM
            else:
                return None
        # Catch the case where there is no Epoch
        else:
            return None

    def get_block_info(self):
        blocks = self.block_set.all()
        num_blocks = blocks.count()
        if num_blocks > 0:
            num_blocks_observed = blocks.filter(num_observed__gte=1).count()
            num_blocks_reported = blocks.filter(reported=True).count()
            observed = "%d/%d" % (num_blocks_observed, num_blocks)
            reported = "%d/%d" % (num_blocks_reported, num_blocks)
        else:
            observed = 'Not yet'
            reported = 'Not yet'
        return observed, reported

    def get_cadence_info(self):
        cad_blocks = self.superblock_set.filter(cadence=True)
        num_cad_blocks = cad_blocks.count()
        if num_cad_blocks > 0:
            active_sblocks = cad_blocks.filter(active=True)
            prefix = "Division by cucumber"
            if active_sblocks.count() > 0:
                last_sblock = active_sblocks.latest('block_end')
                prefix = "Active until"
                if datetime.utcnow() > last_sblock.block_end:
                    prefix = "Inactive since"
                block_time = last_sblock.block_end.strftime("%m/%d")
            else:
                # There are SBlocks but none are active
                last_sblock = cad_blocks.filter(active=False).latest('block_end')
                prefix = "Inactive"
                block_time = ""
                if datetime.utcnow() > last_sblock.block_end:
                    prefix = "Inactive since"
                    block_time = last_sblock.block_end.strftime("%m/%d")

            scheduled = "{} {}".format(prefix, block_time)
            scheduled = scheduled.rstrip()
        else:
            scheduled = 'Nothing scheduled'

        return scheduled

    def get_physical_parameters(self, param_type=None, return_all=True):
        phys_params = PhysicalParameters.objects.filter(body=self.id)
        color_params = ColorValues.objects.filter(body=self.id)
        out_params = []
        for param in phys_params:
            if (param.preferred or return_all) and (not param_type or param.parameter_type == param_type or param.get_parameter_type_display().upper() == param_type.upper()):
                param_dict = model_to_dict(param)
                param_dict['type_display'] = param.get_parameter_type_display()
                out_params.append(param_dict)
        for param in color_params:
            if (param.preferred or return_all) and (not param_type or param.color_band == param_type or 'COLOR' in param_type.upper()):
                param_dict = model_to_dict(param)
                param_dict['type_display'] = param.color_band
                out_params.append(param_dict)
        return out_params

    def save_physical_parameters(self, kwargs):
        """Takes a dictionary of arguments. Dictionary specifics depend on what parameters are being added."""
        overwrite = False
        if 'color_band' in kwargs.keys():
            model = ColorValues
            type_key = 'color_band'
        elif 'desig_type' in kwargs.keys():
            model = Designations
            type_key = 'desig_type'
        elif 'tax_scheme' in kwargs.keys():
            model = SpectralInfo
            type_key = 'tax_scheme'
        else:
            model = PhysicalParameters
            type_key = 'parameter_type'
        if 'reference' in kwargs.keys() and kwargs['reference'] == 'MPC Default':
            overwrite = True

        # Don't save empty values
        if not kwargs['value']:
            return False
        if 'preferred' not in kwargs:
            kwargs['preferred'] = False

        current_params = model.objects.filter(body=self.id)
        new_param = True
        new_type = True
        if current_params:
            for param in current_params:
                param_dict = model_to_dict(param)
                if param_dict[type_key] == kwargs[type_key]:
                    if param_dict['preferred'] is not False:
                        new_type = False
                    diff_values = {k: kwargs[k] for k in kwargs if k in param_dict and kwargs[k] != param_dict[k] and k not in ['body', 'update_time']}
                    if len(diff_values) == 0:
                        new_param = False
                        break
                    if kwargs['preferred'] and param_dict['preferred'] and not overwrite:
                        param.preferred = False
                        param.save()
                    if overwrite:
                        if param_dict['reference'] == 'MPC Default':
                            param.delete()
                        else:
                            kwargs['preferred'] = False
                    elif param_dict['value'] == kwargs['value']:
                        if "units" not in diff_values:
                            for value in diff_values:
                                if kwargs[value] is None:
                                    kwargs[value] = param_dict[value]
                            param.delete()

        if new_type is True:
            kwargs['preferred'] = True
        if new_param is True:
            kwargs['body'] = self
            kwargs['update_time'] = datetime.utcnow()
            try:
                model.objects.create(**kwargs)
            except TypeError:
                logger.warning("Input dictionary contains invalid keywords")
                new_param = False

        return new_param

    def get_latest_update(self):

        update_type = 'Ingest Time'
        update_time = self.ingest
        if self.update_time and (self.update_time > self.ingest):
            update_type = 'Last Update'
            update_time = self.update_time

        # See if there is a later SourceMeasurement
        try:
            last_sm = self.sourcemeasurement_set.all().latest('frame__midpoint')
            if last_sm and last_sm.frame.midpoint > update_time:
                update_time = last_sm.frame.midpoint
                update_type = 'Last Measurement'
        except models.ObjectDoesNotExist:
            pass

        return update_type, update_time

    class Meta:
        verbose_name = _('Minor Body')
        verbose_name_plural = _('Minor Bodies')
        db_table = 'ingest_body'
        ordering = ['-ingest', '-active']

    def __str__(self):
        if self.active:
            text = ''
        else:
            text = 'not '
        return_name = self.provisional_name
        if (self.provisional_name is None or self.provisional_name == u'')\
                and self.name is not None and self.name != u'':
            return_name = self.name
        return u'%s is %sactive' % (return_name, text)


class Designations(models.Model):
    body        = models.ForeignKey(Body, on_delete=models.CASCADE)
    value       = models.CharField('Designation', blank=True, null=True, max_length=30, db_index=True)
    desig_type  = models.CharField('Designation Type', blank=True, choices=DESIG_CHOICES, null=True, max_length=1)
    preferred    = models.BooleanField('Is this the preferred designation of this type?', default=False)
    packed      = models.BooleanField('Is this a packed designation?', default=False)
    notes       = models.CharField('Notes on Nomenclature', max_length=30, blank=True, null=True)
    update_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _('Object Designation')
        verbose_name_plural = _('Object Designations')
        db_table = 'ingest_names'

    def __str__(self):
        return "%s is a designation for %s (pk=%s)" % (self.value, self.body.full_name(), self.body.id)


class PhysicalParameters(models.Model):
    body           = models.ForeignKey(Body, on_delete=models.CASCADE)
    parameter_type = models.CharField('Physical Parameter Type', blank=True, null=True, choices=PARAM_CHOICES, max_length=2)
    value          = models.FloatField('Physical Parameter Value', blank=True, null=True, db_index=True)
    error          = models.FloatField('Physical Parameter Error', blank=True, null=True)
    value2         = models.FloatField('2nd component of Physical Parameter', blank=True, null=True)
    error2         = models.FloatField('Error for 2nd component of Physical Parameter', blank=True, null=True)
    units          = models.CharField('Physical Parameter Units', blank=True, null=True, max_length=30)
    quality        = models.CharField('Physical Parameter Quality Designation', blank=True, null=True, max_length=10)
    preferred      = models.BooleanField('Is this the preferred value for this type of parameter?', default=False)
    reference      = models.TextField('Reference for this value', blank=True, null=True)
    notes          = models.TextField('Notes on this value', blank=True, null=True)
    update_time    = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        verbose_name = _('Physical Parameter')
        verbose_name_plural = _('Physical Parameters')
        db_table = 'ingest_physical_parameters'

    def __str__(self):
        if self.value2:
            return "({}, {}) is the {} for {} (pk={})".format(self.value, self.value2, self.get_parameter_type_display(), self.body.full_name(), self.body.id)
        elif self.units:
            return "{}{} is the {} for {} (pk={})".format(self.value, self.units, self.get_parameter_type_display(), self.body.full_name(), self.body.id)
        else:
            return "{} is the {} for {} (pk={})".format(self.value, self.get_parameter_type_display(), self.body.full_name(), self.body.id)


class ColorValues(models.Model):
    body          = models.ForeignKey(Body, on_delete=models.CASCADE)
    color_band    = models.CharField('X-X filter combination', blank=True, null=True, max_length=30)
    value         = models.FloatField('Color Value', blank=True, null=True, db_index=True)
    error         = models.FloatField('Color error', blank=True, null=True)
    units         = models.CharField('Color Units', blank=True, null=True, max_length=30)
    quality       = models.CharField('Color Quality Designation', blank=True, null=True, max_length=10)
    preferred     = models.BooleanField('Is this the preferred value for this color band?', default=False)
    reference     = models.TextField('Reference for this value', blank=True, null=True)
    notes         = models.TextField('Notes on this value', blank=True, null=True)
    update_time   = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        verbose_name = _('Color Value')
        verbose_name_plural = _('Color Values')
        db_table = 'ingest_colors'

    def __str__(self):
        return "{} is the {} color for {} (pk={})".format(self.value, self.color_band, self.body.name, self.body.id)
