'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

ephem_subs.py -- Asteroid ephemeris related routines.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from datetime import datetime, timedelta, time
import slalib as S
from math import sin, cos, tan, asin, acos, atan2, degrees, radians, pi, sqrt, fabs, exp, log10
from numpy import array, concatenate, zeros

# Local imports
from astrometrics.time_subs import datetime2mjd_utc, datetime2mjd_tdb, mjd_utc2mjd_tt, ut1_minus_utc, round_datetime
#from astsubs import mpc_8lineformat

import logging

logger = logging.getLogger(__name__)


def compute_phase_angle(r, delta, es_Rsq, dbg=False):
    '''Method to compute the phase angle (beta), trapping bad values'''
    # Compute phase angle, beta (Sun-Target-Earth angle)
    logger.debug("r(%s), r^2 (%s),delta (%s),delta^2 (%s), es_Rsq (%s)" % (r,r*r,delta,delta*delta,es_Rsq))
    arg = (r*r+delta*delta-es_Rsq)/(2.0*r*delta)
    logger.debug("arg=%s" % arg)

    if arg >= 1.0:
        beta = 0.0
    elif arg <= -1.0:
        beta = pi
    else:
        beta = acos(arg)

    logger.debug("Phase angle, beta (deg)=%s %s" % (beta, degrees(beta)))
    return beta

def compute_ephem(d, orbelems, sitecode, dbg=False, perturb=True, display=False):
    '''Routine to compute the geocentric or topocentric position, magnitude,
    motion and altitude of an asteroid or comet for a specific date and time
    from a dictionary of orbital elements.

    <orbelems> can be in one of two forms, so called "Eric format" as produced
    by rise_set.moving_objects.read_neocp_orbit and used in the scheduler/RequestDB
    or the format used by NEO exchange. Selection is automatically handled based on
    whether the epoch of the elements dictionary key is 'epoch' (Eric format) or
    'epochofel' (NEO exchange format)
    '''

# Light travel time for 1 AU (in sec)
    tau = 499.004783806

# Compute MJD for UTC
    mjd_utc = datetime2mjd_utc(d)

# Compute epoch of the elements as a MJD
    ericformat = False
    if orbelems.has_key('epoch'): ericformat = True
    if ericformat == False:
        try:
            epochofel = datetime.strptime(orbelems['epochofel'], '%Y-%m-%d %H:%M:%S')
        except TypeError:
            epochofel = orbelems['epochofel']
        epoch_mjd = datetime2mjd_utc(epochofel)
    else:
        epoch_mjd = orbelems['epoch']

    logger.debug('Element Epoch= %.1f' % (epoch_mjd))
    logger.debug('MJD(UTC) =   %.15f' % (mjd_utc))
    logger.debug(' JD(UTC) = %.8f' % (mjd_utc + 2400000.5))

# Convert MJD(UTC) to MJD(TT)
    mjd_tt = mjd_utc2mjd_tt(mjd_utc)
    logger.debug('MJD(TT)  =   %.15f' % (mjd_tt))

# Compute UT1-UTC

    dut = ut1_minus_utc(mjd_utc)
    logger.debug("UT1-UTC  = %.15f" % (dut))

# Obtain precession-nutation 3x3 rotation matrix
# Should really be TDB but "TT will do" says The Wallace...

    rmat = S.sla_prenut(2000.0, mjd_tt)

    logger.debug(rmat)

# Obtain latitude, longitude of the observing site.
# Reverse longitude to get the more normal East-positive convention
#    (site_num, site_name, site_long, site_lat, site_hgt) = S.sla_obs(0, 'SAAO74')
#    site_long = -site_long
    (site_name, site_long, site_lat, site_hgt) = get_sitepos(sitecode)
    logger.debug("Site code/name, lat/long/height=%s %s %f %f %.1f" % (sitecode, site_name, site_long, site_lat, site_hgt))

# Compute local apparent sidereal time
# Do GMST first which takes UT1 and then add East longitiude and the equation of the equinoxes
# (which takes TDB; but we use TT here)
#
    gmst = S.sla_gmst(mjd_utc+(dut/86400.0))
    stl = gmst + site_long + S.sla_eqeqx(mjd_tt)
    logger.debug('GMST, LAST, EQEQX, GAST, long= %.17f %.17f %E %.17f %.17f' % (gmst, stl, S.sla_eqeqx(mjd_tt), gmst+S.sla_eqeqx(mjd_tt), site_long))
    pvobs = S.sla_pvobs(site_lat, site_hgt, stl)

    if site_name == '?':
        logger.debug("WARN: No site co-ordinates found, computing for geocenter")
        pvobs = pvobs * 0.0

    logger.debug("PVobs(orig)=%s\n            %s" % (pvobs[0:3],pvobs[3:6]*86400.0))

# Apply transpose of precession/nutation matrix to pv vector to go from
# true equator and equinox of date to J2000.0 mean equator and equinox (to
# match the reference system of sla_epv)
#
    pos_new = S.sla_dimxv(rmat, pvobs[0:3])
    vel_new = S.sla_dimxv(rmat, pvobs[3:6])
    pvobs_new = concatenate([pos_new, vel_new])
    logger.debug("PVobs(new)=%s\n            %s" % (pvobs_new[0:3],pvobs_new[3:6]*86400.0))

# Earth position and velocity

# Moderate precision/speed version. N.B different order of bary vs. heliocentric!
#(vel_bar, pos_bar, e_vel_hel, e_pos_hel) = S.sla_evp(mjd_tt, 2000.0)

# High precision/slowest version. N.B different order of bary vs. heliocentric sets
# and position vs velocity!
# N.B. velocities are AU/day not AU/sec !
# Also N.B. ! Must use heliocentric positions, not barycentric as normal as
# asteroid position from sla_planel is also heliocentric.
    (e_pos_hel, e_vel_hel, e_pos_bar, e_vel_bar) = S.sla_epv(mjd_tt)
# Uncomment the lines below to use JPL DE430 ephemeris. This, and the
# associated code, needs to be installed...
#    ephem = Ephemeris(430)
#    (e_pos_hel, e_vel_hel, e_pos_bar, e_vel_bar ) = ephem.epv(mjd_tt)
    e_vel_hel = e_vel_hel/86400.0

    logger.debug("Sun->Earth [X, Y, Z]=%s" % e_pos_hel)
    logger.debug("Sun->Earth [X, Y, Z]= %20.15E %20.15E %20.15E" % (e_pos_hel[0], e_pos_hel[1], e_pos_hel[2]))
    logger.debug("Sun->Earth [Xdot, Ydot, Zdot]=%s" % e_vel_hel)
    logger.debug("Sun->Earth [Xdot, Ydot, Zdot]= %20.15E %20.15E %20.15E" % (e_vel_hel[0]*86400.0, e_vel_hel[1]*86400.0, e_vel_hel[2]*86400.0))

# Add topocentric offset in position and velocity
    e_pos_hel = e_pos_hel + pvobs_new[0:3]
    e_vel_hel = e_vel_hel + pvobs_new[3:6]
    logger.debug("Sun->Obsvr [X, Y, Z]=%s" % e_pos_hel)
    logger.debug("Sun->Obsvr [Xdot, Ydot, Zdot]=%s" % e_vel_hel)

# Asteroid position (and velocity)

    comet = False
    if 'type' in orbelems and orbelems['type'].upper() == 'MPC_COMET':
        comet = True

# Perturb elements
    if ericformat == True:
        if comet == True:
            p_orbelems = {'LongNode' : orbelems['long_node'].in_radians(),
                          'Inc' : orbelems['inclination'].in_radians(),
                          'ArgPeri' : orbelems['arg_perihelion'].in_radians(),
                          'SemiAxisOrQ' : orbelems['semi_axis'],
                          'Ecc' : orbelems['eccentricity']
                         }
        else:
            p_orbelems = {'LongNode' : orbelems['long_node'].in_radians(),
                          'Inc' : orbelems['inclination'].in_radians(),
                          'ArgPeri' : orbelems['arg_perihelion'].in_radians(),
                          'MeanAnom' : orbelems['mean_anomaly'].in_radians(),
                          'SemiAxis' : orbelems['semi_axis'],
                          'Ecc' : orbelems['eccentricity']
                         }
        p_orbelems['H'] = orbelems['H']
        p_orbelems['G'] = orbelems['G']
        if perturb == True:
            if comet == True:
                (p_epoch_mjd, p_orbelems['Inc'], p_orbelems['LongNode'], p_orbelems['ArgPeri'],
                  p_orbelems['SemiAxisOrQ'], p_orbelems['Ecc'], p_orbelems['MeanAnom'], j) = S.sla_pertel(3, epoch_mjd,
                            mjd_tt, epoch_mjd, orbelems['inclination'].in_radians(), orbelems['long_node'].in_radians(),
                            orbelems['arg_perihelion'].in_radians(), orbelems['perihdist'], orbelems['eccentricity'],
                            0.0)
                p_epoch_mjd = orbelems['epochofperih']
            else:
                (p_epoch_mjd, p_orbelems['Inc'], p_orbelems['LongNode'], p_orbelems['ArgPeri'],
                  p_orbelems['SemiAxis'], p_orbelems['Ecc'], p_orbelems['MeanAnom'], j) = S.sla_pertel(2, epoch_mjd,
                            mjd_tt, epoch_mjd, orbelems['inclination'].in_radians(), orbelems['long_node'].in_radians(),
                            orbelems['arg_perihelion'].in_radians(), orbelems['semi_axis'], orbelems['eccentricity'],
                            orbelems['mean_anomaly'].in_radians())
        else:
            logger.debug("Not perturbing")
            p_epoch_mjd = epoch_mjd
            j = 0
    else:
        # NEO exchange format

        if comet == True:
            p_orbelems = {'LongNode' : radians(orbelems['longascnode']),
                          'Inc' : radians(orbelems['orbinc']),
                          'ArgPeri' : radians(orbelems['argofperih']),
                          'SemiAxisOrQ' : orbelems['perihdist'],
                          'Ecc' : orbelems['eccentricity'],
                         }
        else:
            p_orbelems = {'LongNode' : radians(orbelems['longascnode']),
                          'Inc' : radians(orbelems['orbinc']),
                          'ArgPeri' : radians(orbelems['argofperih']),
                          'MeanAnom' : radians(orbelems['meananom']),
                          'SemiAxis' : orbelems['meandist'],
                          'Ecc' : orbelems['eccentricity']
                         }
        p_orbelems['H'] = orbelems['abs_mag']
        p_orbelems['G'] = orbelems['slope']
        if perturb == True:
            (p_epoch_mjd, p_orbelems['Inc'], p_orbelems['LongNode'], p_orbelems['ArgPeri'],
              p_orbelems['SemiAxis'], p_orbelems['Ecc'], p_orbelems['MeanAnom'], j) = S.sla_pertel( 2, epoch_mjd, mjd_tt, epoch_mjd, radians(orbelems['orbinc']), radians(orbelems['longascnode']),
                        radians(orbelems['argofperih']), orbelems['meandist'], orbelems['eccentricity'],
                        radians(orbelems['meananom']))
        else:
            p_epoch_mjd = epoch_mjd
            j = 0

    if j != 0:
        print "Perturbing error=%s" % j


    r3 = -100.
    delta = 0.0
    ltt = 0.0
    pos = zeros(3)
    vel = zeros(3)
    #rel_pos= [0.0, 0.0, 0.0]

    while (fabs(delta - r3) > .01):
        r3 = delta
        if comet == True:
            (pv, status) = S.sla_planel(mjd_tt - (ltt/86400.0), 3, p_epoch_mjd,
                            p_orbelems['Inc'], p_orbelems['LongNode'],
                            p_orbelems['ArgPeri'], p_orbelems['SemiAxisOrQ'], p_orbelems['Ecc'],
                            0.0, 0.0)
        else:
            (pv, status) = S.sla_planel(mjd_tt - (ltt/86400.0), 2, p_epoch_mjd,
                            p_orbelems['Inc'], p_orbelems['LongNode'],
                            p_orbelems['ArgPeri'], p_orbelems['SemiAxis'], p_orbelems['Ecc'],
                            p_orbelems['MeanAnom'], 0.0)


        logger.debug("Sun->Asteroid [x,y,z]=%s %s" % (pv[0:3], status))
        logger.debug("Sun->Asteroid [xdot,ydot,zdot]=%s %s" % (pv[3:6], status))

        for i, e_pos in enumerate(e_pos_hel):
            pos[i] = pv[i] - e_pos

        for i, e_vel in enumerate(e_vel_hel):
            vel[i] = pv[i+3] - e_vel

        logger.debug("Earth->Asteroid [x,y,z]=%s" % pos)
        logger.debug("Earth->Asteroid [xdot,ydot,zdot]=%s" % vel)

# geometric distance, delta (AU)
        delta = sqrt(pos[0]*pos[0] + pos[1]*pos[1] + pos[2]*pos[2])

        logger.debug("Geometric distance, delta (AU)=%s" % delta)

# Light travel time to asteroid
        ltt = tau * delta
        logger.debug("Light travel time (sec, min, days)=%s %s %s" % (ltt, ltt/60.0, ltt/86400.0))

# Correct position for planetary aberration
    for i, a_pos in enumerate(pos):
        pos[i] = a_pos - (ltt * vel[i])

    logger.debug("Earth->Asteroid [x,y,z]=%s" % pos)
    logger.debug("Earth->Asteroid [x,y,z]= %20.15E %20.15E %20.15E" % (pos[0], pos[1], pos[2]))
    logger.debug("Earth->Asteroid [xdot,ydot,zdot]=%s %s %s" % (vel[0]*86400.0,vel[1]*86400.0,vel[2]*86400.0))

# Convert Cartesian to RA, Dec
    (ra, dec) = S.sla_dcc2s(pos)
    logger.debug("ra,dec=%s %s" % (ra, dec))
    ra = S.sla_dranrm(ra)
    logger.debug("ra,dec=%s %s" % (ra, dec))
    (rsign, ra_geo_deg) = S.sla_dr2tf(2, ra)
    (dsign, dec_geo_deg) = S.sla_dr2af(1, dec)

# Compute r, the Sun-Target distance. Correct for light travel time first
    cposx = pv[0] - (ltt * pv[3])
    cposy = pv[1] - (ltt * pv[4])
    cposz = pv[2] - (ltt * pv[5])
    r = sqrt(cposx*cposx + cposy*cposy + cposz*cposz)

    logger.debug("r (AU) =%s" % r)

# Compute R, the Earth-Sun distance. (Only actually need R^2 for the mag. formula)
    es_Rsq = (e_pos_hel[0]*e_pos_hel[0] + e_pos_hel[1]*e_pos_hel[1] + e_pos_hel[2]*e_pos_hel[2])

    logger.debug("R (AU) =%s" % sqrt(es_Rsq))
    logger.debug("delta (AU)=%s" % delta)

# Compute sky motion

    sky_vel = compute_relative_velocity_vectors(e_pos_hel, e_vel_hel, pos, vel, delta, dbg)
    logger.debug("vel1, vel2, r= %15.10lf %15.10lf %15.10lf" % (sky_vel[1], sky_vel[2], delta))
    logger.debug("vel1, vel2, r= %15.10e %15.10e %15.10lf\n" % (sky_vel[1], sky_vel[2], delta))

    total_motion, sky_pa, ra_motion, dec_motion = compute_sky_motion(sky_vel, delta, dbg)

    if comet == True:
    # Calculate magnitude of comet
    # Here 'H' is the absolute magnitude, 'kappa' the slope parameter defined in Meeus
    # _Astronomical Algorithms_ p. 231, is equal to 2.5 times the 'G' read from the
        mag = p_orbelems['H'] + 5.0 * log10(delta) + 2.5 * p_orbelems['G'] * log10(r)

    else:
    # Compute phase angle, beta (Sun-Target-Earth angle)
        beta = compute_phase_angle(r, delta, es_Rsq)

        phi1 = exp(-3.33 * (tan(beta/2.0))**0.63)
        phi2 = exp(-1.87 * (tan(beta/2.0))**1.22)

    #    logger.debug("Phi1, phi2=%s" % phi1,phi2)

    # Calculate magnitude of object
        mag = p_orbelems['H'] + 5.0 * log10(r * delta) - \
            (2.5 * log10((1.0 - p_orbelems['G'])*phi1 + p_orbelems['G']*phi2))

    az_rad, alt_rad = moon_alt_az(d, ra, dec, site_long, site_lat, site_hgt)
    airmass = S.sla_airmas((pi/2.0)-alt_rad)
    alt_deg = degrees(alt_rad)

#    if display: print "  %02.2dh %02.2dm %02.2d.%02.2ds %s%02.2dd %02.2d\' %02.2d.%01.1d\"  V=%.1f  %5.2f %.1f % 7.3f %8.4f" % ( ra_geo_deg[0],
    if display: print "  %02.2d %02.2d %02.2d.%02.2d %s%02.2d %02.2d %02.2d.%01.1d  V=%.1f  %5.2f %.1f % 7.3f %8.4f" % ( ra_geo_deg[0],
        ra_geo_deg[1], ra_geo_deg[2], ra_geo_deg[3],
        dsign, dec_geo_deg[0], dec_geo_deg[1], dec_geo_deg[2], dec_geo_deg[3],
        mag, total_motion, sky_pa, alt_deg, airmass )

    emp_line = (d, ra, dec, mag, total_motion, alt_deg)

    return emp_line


def compute_relative_velocity_vectors(obs_pos_hel, obs_vel_hel, obj_pos, obj_vel, delta, dbg=True):
    '''Computes relative velocity vector between the observer and the object.
    Adapted from the Bill Gray/find_orb routine of the same name with some
    changes as obj_pos in our code is already the needed result of subtracting
    the Heliocenter->Observer vector from the Heliocenter->Asteroid vector and
    so we don't need to do this when we form the first 3 elements of matrix.'''

    obj_vel = obj_vel * 86400.0
    j2000_vel = zeros(3)
    matrix = zeros(9)
    i = 0 
    while (i < 3):
        j2000_vel[i] = obj_vel[i] - obs_vel_hel[i]
        matrix[i] = obj_pos[i] / delta
        i += 1
    logger.debug("   obj_vel= %15.10f %15.10f %15.10f" % (obj_vel[0], obj_vel[1], obj_vel[2]))
    logger.debug("   obs_vel= %15.10f %15.10f %15.10f" % (obs_vel_hel[0], obs_vel_hel[1], obs_vel_hel[2]))
    logger.debug("   obs_vel= %15.10e %15.10e %15.10e" % (obs_vel_hel[0], obs_vel_hel[1], obs_vel_hel[2]))

    logger.debug(" j2000_vel= %15.10e %15.10e %15.10e" % (j2000_vel[0], j2000_vel[1], j2000_vel[2]))
    logger.debug("matrix_vel= %15.10f %15.10f %15.10f" % (matrix[0], matrix[1], matrix[2] ))

    length = sqrt( matrix[0] * matrix[0] + matrix[1] * matrix[1])
    matrix[3] =  matrix[1] / length
    matrix[4] = -matrix[0] / length
    matrix[5] = 0.

    matrix[6] =  matrix[4] * matrix[2]
    matrix[7] = -matrix[3] * matrix[2]
    matrix[8] = length

    vel = zeros(3)
    i = 0
    while (i < 9):
        vel[i / 3] = matrix[i] * j2000_vel[0] + matrix[i+1] * j2000_vel[1] + matrix[i+2] * j2000_vel[2]
        i += 3

    return vel

def compute_sky_motion(sky_vel, delta, dbg=True):
    '''Computes the total motion and Position Angle, along with the RA, Dec
    components, of an asteroids' sky motion. Motion is in "/min, PA in degrees.

    Adapted from the Bill Gray/find_orb routine of the same name.'''

    ra_motion = degrees(sky_vel[1]) / delta
    dec_motion = degrees(sky_vel[2]) / delta
    ra_motion = -ra_motion * 60.0 / 24.0
    dec_motion = dec_motion * 60.0 / 24.0

    sky_pa = 180.0 + degrees(atan2(-ra_motion, -dec_motion))
    logger.debug( "RA motion, Dec motion, PA=%10.7f %10.7f %6.1f" % (ra_motion, dec_motion, sky_pa ))

    total_motion = sqrt(ra_motion * ra_motion + dec_motion * dec_motion)
    logger.debug( "Total motion=%10.7f" % (total_motion))

    return (total_motion, sky_pa, ra_motion, dec_motion)

def format_emp_line(emp_line, site_code):

# Get site and mount parameters
    (site_name, site_long, site_lat, site_hgt) = get_sitepos(site_code)
    (ha_neg_limit, ha_pos_limit, mount_alt_limit) = get_mountlimits(site_code)

    blk_row_format = "%-16s|%s|%s|%04.1f|%5.2f|%+d|%04.2f|%3d|%+02.2d|%+04d|%s"

# Convert radians for RA, Dec into strings for printing
    (ra_string, dec_string) = radec2strings(emp_line[1], emp_line[2], ' ')
# Compute apparent RA, Dec of the Moon
    (moon_app_ra, moon_app_dec, diam) = moon_ra_dec(emp_line[0], site_long, site_lat, site_hgt) 
# Convert to alt, az (only the alt is actually needed)
    (moon_az, moon_alt) = moon_alt_az(emp_line[0], moon_app_ra, moon_app_dec, site_long, site_lat, site_hgt)
    moon_alt = degrees(moon_alt)
# Compute object<->Moon seperation and convert to degrees
    moon_obj_sep = S.sla_dsep(emp_line[1], emp_line[2], moon_app_ra, moon_app_dec)
    moon_obj_sep = degrees(moon_obj_sep)
# Calculate Moon phase (in range 0.0..1.0)
    moon_phase = moonphase(emp_line[0], site_long, site_lat, site_hgt)

# Compute H.A.
    ha = compute_hourangle(emp_line[0], site_long, site_lat, site_hgt, emp_line[1], emp_line[2])
    ha_in_deg = degrees(ha)
# Check HA is in limits, skip this slot if not
    if (ha_in_deg >= ha_pos_limit or ha_in_deg <= ha_neg_limit):
            ha_string = 'Limits'
    else:
        (ha_string,junk) = radec2strings(ha, ha, ':')
        ha_string = ha_string[0:6]

# Calculate slot score
    slot_score = compute_score(emp_line[5], moon_alt, moon_obj_sep, mount_alt_limit)

# Calculate the no. of FOVs from the starting position
#    pointings_sep = S.sla_dsep(emp_line[1], emp_line[2], start_ra, start_dec)
#    num_fov = int(pointings_sep/ccd_fov)

# Format time and print out the overall ephemeris
    emp_time = datetime.strftime(emp_line[0], '%Y %m %d %H:%M')

    formatted_line = blk_row_format % (emp_time, ra_string, dec_string, \
        emp_line[3], emp_line[4], emp_line[5],\
        moon_phase, moon_obj_sep, moon_alt, slot_score, ha_string)

    line_as_list = formatted_line.split('|')
    return line_as_list

def call_compute_ephem(elements, dark_start, dark_end, site_code, ephem_step_size, alt_limit=0):
    '''Wrapper for compute_ephem to enable use within plan_obs (or other codes)
    by making repeated calls for datetimes from <dark_start> -> <dark_end> spaced
    by <ephem_step_size> seconds. The results are assembled into a list of tuples
    in the same format as returned by read_findorb_ephem()'''

#    print
#    formatted_elem_lines = mpc_8lineformat(elements)
#    for line in formatted_elem_lines:
#        print line

    slot_length = 0 # XXX temporary hack
    step_size_secs = 300
    if str(ephem_step_size)[-1] == 'm':
        try:
            step_size_secs = float(ephem_step_size[0:-1]) * 60
        except ValueError:
            pass
    else:
        step_size_secs = ephem_step_size
    ephem_time = round_datetime(dark_start, step_size_secs / 60, False)

    full_emp = []
    while ephem_time < dark_end:
        emp_line = compute_ephem(ephem_time, elements, site_code, dbg=False, perturb=True, display=False)
        full_emp.append(emp_line)
        ephem_time = ephem_time + timedelta(seconds=step_size_secs)

# Get subset of ephemeris when it's dark and object is up
    visible_emp = dark_and_object_up(full_emp, dark_start, dark_end, slot_length, alt_limit)
    emp = []
    for line in visible_emp:
        emp.append(format_emp_line(line, site_code))

    return emp

def determine_darkness_times(site_code, utc_date=datetime.utcnow(), debug=False):
    '''Determine the times of darkness at the site specified by <site_code>
    for the date of [utc_date] (which defaults to UTC now if not given).
    The darkness times given are when the Sun is lower than -15 degrees
    altitude (intermediate between nautical (-12) and astronomical (-18)
    darkness, which has been chosen as more appropriate for fainter asteroids.
    '''
    # Check if current date is greater than the end of the last night's astro darkness
    # Add 1 hour to this to give a bit of slack at the end and not suddenly jump
    # into the next day
    try:
        utc_date = utc_date.replace(hour=0, minute=0, second=0, microsecond=0)
    except TypeError:
        utc_date = datetime.combine(utc_date, time())
    (start_of_darkness, end_of_darkness) = astro_darkness(site_code, utc_date)
    end_of_darkness = end_of_darkness+timedelta(hours=1)
    logger.debug("Start,End of darkness=%s %s", start_of_darkness, end_of_darkness)
    if utc_date > end_of_darkness:
        logger.debug("Planning for the next night")
        utc_date = utc_date + timedelta(days=1)
    elif start_of_darkness.hour > end_of_darkness.hour and  utc_date.hour < end_of_darkness.hour:
        logger.debug("Planning for the previous night")
        utc_date = utc_date + timedelta(days=-1)

    utc_date = utc_date.replace(hour=0, minute=0, second=0, microsecond=0)
    logger.debug("Planning observations for %s for %s", utc_date, site_code)
    # Get hours of darkness for site
    (dark_start, dark_end) = astro_darkness(site_code, utc_date)
    logger.debug("Dark from %s to %s", dark_start, dark_end)

    return dark_start, dark_end

def astro_darkness(sitecode, utc_date, round_ad=True):

    accurate = True
    if accurate == True:
        (ad_start, ad_end) = accurate_astro_darkness(sitecode, utc_date)
    else:
        (ad_start, ad_end) = crude_astro_darkness(sitecode, utc_date)

    if ad_start != None and ad_end != None:
        if round_ad == True:
            ad_start = round_datetime(ad_start, 10)
            ad_end = round_datetime(ad_end, 10)

    return ad_start, ad_end

def crude_astro_darkness(sitecode, utc_date):
    '''Really crude version of routine to compute times of astronomical
    darkness which just hard-wires times based on the site'''

    if sitecode == 'F65':
        ad_start = utc_date + timedelta(hours=6, minutes=00)
        ad_end = utc_date + timedelta(hours=14, minutes=50)
    elif sitecode == 'E10':
        ad_start = utc_date + timedelta(hours=8, minutes=00)
        ad_end = utc_date + timedelta(hours=20, minutes=00)
    elif sitecode == 'G51':
        ad_start = utc_date + timedelta(hours=4, minutes=20)
        ad_end = utc_date + timedelta(hours=11, minutes=44)
    elif sitecode == '711' or sitecode == 'V37':
        ad_start = utc_date + timedelta(hours=3, minutes=00)
        ad_end = utc_date + timedelta(hours=10, minutes=50)
    elif sitecode == 'W85' or sitecode == 'W86' or sitecode == 'W87':
        ad_start = utc_date + timedelta(hours=1, minutes=00)
        ad_end = utc_date + timedelta(hours=8, minutes=39)
    elif sitecode == 'K91' or sitecode == 'K92' or sitecode == 'K93':
        ad_start = utc_date + timedelta(hours=0, minutes=0)
        ad_end = utc_date + timedelta(hours=4, minutes=39)
    else:
        print "Unsupported sitecode", sitecode
        return (None, None)

    return ad_start, ad_end

def accurate_astro_darkness(sitecode, utc_date, debug=False):

# Convert passed UTC date to MJD and then Julian centuries

    mjd_utc = datetime2mjd_utc(utc_date)
    T = (mjd_utc - 51544.5)/36525.0

# Mean longitude of the Sun
    sun_mean_long = (280.46645 + T * (36000.76983 + T * 0.0003032) ) % 360

# Mean anomaly of the Sun
    sun_mean_anom = (357.52910 + T * (35999.05030 - T * (0.0001559 - 0.00000048 * T ) ) ) % 360

# Earth's eccentricity
    earth_e = 0.016708617 - T * (0.000042037 - T * 0.0000001236)

# Sun's equation of the center
    sun_eqcent = (1.914600 - T * (0.004817 - 0.000014 * T)) * sin(radians(sun_mean_anom)) +\
                 (0.019993 - T * 0.000101) * sin(2.0 *radians(sun_mean_anom)) +\
                 0.000290 * sin(3.0 *radians(sun_mean_anom))
# Sun's true longitude
    sun_true_long = sun_mean_long + sun_eqcent

# Obliquity of the ecliptic
    (dpsi, deps, eps0) = S.sla_nutc80(mjd_utc)

# Omega (Longitude of the ascending node of the Moon's orbit)
    omega = radians(125.04-1934.136*T)
    eps = degrees(eps0) + 0.00256*cos(omega)

    sun_app_long = sun_true_long - 0.00569-0.00478*sin(omega)
    sun_app_ra = atan2(cos(radians(eps)) * sin(radians(sun_app_long)), cos(radians(sun_app_long)))
    sun_app_ra = S.sla_dranrm(sun_app_ra)
    sun_app_dec = asin(sin(radians(eps)) * sin(radians(sun_app_long)))

    (site_name, site_long, site_lat, site_hgt) = get_sitepos(sitecode)

# Zenith distance of the Sun in degrees, normally 102 (nautical twilight as used
# in the scheduler) but could be 108 (astronomical twilight) or 90.5 (sunset)
# Here we use 105 (-15 degrees Sun altitude) to keep windows away from the
# brighter twilight which could be a problem for our faint targets.

    sun_zd = 105
    hourangle = degrees(acos(cos(radians(sun_zd))/(cos(site_lat)*cos(sun_app_dec))-tan(site_lat)*tan(sun_app_dec)))

    eqtime = 4.0 * (sun_mean_long - 0.0057183 - degrees(sun_app_ra) + degrees(dpsi) * cos(radians(eps)))
    solarnoon = (720-4*degrees(site_long)-eqtime)/1440
    sunrise = (solarnoon - hourangle*4/1440) % 1
    sunset = (solarnoon + hourangle*4/1440) % 1
    if debug: print solarnoon + hourangle*4/1440, solarnoon - hourangle*4/1440
    if debug: print sunset, sunrise

    if sunrise < sunset:
        sunrise = sunrise + 1
    if debug:
        to_return = [T, sun_mean_long, sun_mean_anom, earth_e, sun_eqcent, \
            sun_true_long, degrees(omega), sun_app_long, degrees(eps0), eps, \
            degrees(sun_app_ra), degrees(sun_app_dec), eqtime, hourangle]
        print to_return

    else:
        to_return = (utc_date+timedelta(days=sunset), utc_date+timedelta(days=sunrise))

    return to_return

def dark_and_object_up(emp, dark_start, dark_end, slot_length, alt_limit=30.0, debug=False):
    '''Returns the subset of the passed ephemeris where the object is up and
    the site is dark.
    Modified 2013/1/21: Now slot_length is passed in so this is subtracted
    from the night end, ensuring blocks don't begin at sunrise.'''

    dark_up_emp = []

    for x in emp:
        visible = False
        if  (x[0]>=dark_start and x[0]<=dark_end-timedelta(minutes=slot_length)) and x[5] >= float(alt_limit):
            visible = True
            dark_up_emp.append(x)
        if debug: print x[0].date(), x[0].time(), (x[0]>=dark_start and x[0]<dark_end-timedelta(minutes=slot_length)), x[5], alt_limit, visible


    return dark_up_emp

class MagRangeError(Exception):
    '''Raised when an invalid magnitude is found'''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

BRIGHTEST_ALLOWABLE_MAG = 10

def get_mag_mapping(site_code):
    '''Defines the site-specific mappings from target magnitude to desired
    slot length (in minutes). A null dictionary is returned if the site name
    isn't recognized'''

    twom_site_codes = ['F65', 'E10']
    good_onem_site_codes = ['V37', 'K91', 'K92', 'K93', 'W85', 'W86', 'W87']
    # COJ normally has bad seeing, allow more time
    bad_onem_site_codes = ['Q63', 'Q64']

# Magnitudes represent upper bin limits
    site_code = site_code.upper()
    if site_code in twom_site_codes:
# Mappings for FTN/FTS. Assumes Spectral+Solar filter
        mag_mapping = {
                19   : 15,
                20   : 20,
                20.5 : 22.5,
                21   : 25,
                21.5 : 27.5,
                22   : 30,
                23.3 : 35
               }
    elif site_code in good_onem_site_codes:
# Mappings for McDonald. Assumes kb74+w
        mag_mapping = {
                18   : 15,
                20   : 20,
                20.5 : 22.5,
                21   : 25,
                21.5 : 30,
                22.0 : 40,
                22.5 : 45
               }
    elif site_code in bad_onem_site_codes:
# COJ normally has bad seeing, allow more time
        mag_mapping = {
                18   : 17.5,
                19.5 : 20,
                20   : 22.5,
                20.5 : 25,
                21   : 27.5,
                21.5 : 32.5,
                22.0 : 35
               }
    else:
        mag_mapping = {}

    return mag_mapping


def determine_slot_length(target_name, mag, site_code, debug=False):

    if mag < BRIGHTEST_ALLOWABLE_MAG:
        raise MagRangeError("Target too bright")

# Obtain magnitude->slot length mapping dictionary
    mag_mapping = get_mag_mapping(site_code)
    if debug: print mag_mapping
    if mag_mapping == {}: return 0

    # Derive your tuple from the magnitude->slot length mapping data structure
    upper_mags = tuple(sorted(mag_mapping.keys()))

    for upper_mag in upper_mags:
        if mag < upper_mag:
            return mag_mapping[upper_mag]

    raise MagRangeError("Target magnitude outside bins")

def estimate_exptime(rate, pixscale=0.304, roundtime=10.0):
    '''Gives the estimated exposure time (in seconds) for the given rate and
    pixelscale'''

    exptime = (60.0 / rate / pixscale)*1.0
    round_exptime = max(int(exptime/roundtime)*roundtime, 1.0)
    return (round_exptime, exptime)

def determine_exptime(speed, pixel_scale, max_exp_time=300.0):
    (round_exptime, full_exptime) =  estimate_exptime(speed, pixel_scale, 5.0)

    if ( round_exptime > max_exp_time ):
        logger.debug("Capping exposure time at %.1f seconds (Was %1.f seconds" % \
            (round_exptime, max_exp_time))
        round_exptime = full_exptime = max_exp_time
    if ( round_exptime < 10.0 ):
# If under 10 seconds, re-round to nearest half second
        (round_exptime, full_exptime) = estimate_exptime(speed, pixel_scale, 0.5)
    logger.debug("Estimated exptime=%.1f seconds (%.1f)" % (round_exptime ,full_exptime))

    return round_exptime

def determine_exp_time_count(speed, site_code, slot_length_in_mins):
    exp_time = None
    exp_count = None

    (chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit) = get_sitecam_params(site_code)

    exp_time = determine_exptime(speed, pixel_scale, max_exp_time)

    slot_length = slot_length_in_mins * 60.0
    exp_count = int((slot_length - setup_overhead)/(exp_time + exp_overhead))
    if exp_count < 4:
        exp_count = 4
        exp_time = (slot_length - setup_overhead - (exp_overhead * float(exp_count))) / exp_count
        logger.debug("Reducing exposure time to %.1f secs to allow %d exposures in group" % ( exp_time, exp_count ))
    logger.debug("Slot length of %.1f mins (%.1f secs) allows %d x %.1f second exposures" % \
        ( slot_length/60.0, slot_length, exp_count, exp_time))
    if exp_time == None or exp_time <= 0.0 or exp_count < 1:
        logger.debug("Invalid exposure count")
        exp_time = None
        exp_count = None

    return exp_time, exp_count

def compute_score(obj_alt, moon_alt, moon_sep, alt_limit=25.0):
    '''Simple noddy scoring calculation for choosing best slot'''
    
    objalt_wgt = 1.0
    moonalt_wgt = 0.33
    bad_score = -999
    score = bad_score
# Check distance to the Moon. If <25deg, it's no good. Should really be a
# function of moon phase
    if moon_sep < 25.0:
        score = bad_score
    elif obj_alt < alt_limit:
        score = bad_score
    else:
# Prefer when object is highest and moon is lowest
        score = (objalt_wgt * obj_alt) - (moonalt_wgt * moon_alt)

    return score

def arcmins_to_radians(arcmin):
    return (arcmin/60.0)*(pi/180.0)

def get_sitepos(site_code, dbg=False):
    '''Returns site name, geodetic longitude (East +ve), latitude (both in radians)
    and altitude (meters) for passed sitecode. This can be either a SLALIB site
    name or a MPC sitecode (FTN, FTS and SQA currently defined).
    Be *REALLY* careful over longitude sign conventions...'''

    site_code = site_code.upper()
    if site_code == 'F65' or site_code == 'FTN':
# MPC code for FTN. Positions from JPL HORIZONS, longitude converted from 203d 44' 32.6" East 
# 156d 15' 27.4" W
        (site_lat, status)  =  S.sla_daf2r(20, 42, 25.5)
        (site_long, status) =  S.sla_daf2r(156, 15, 27.4)
        site_long = -site_long
        site_hgt = 3055.0
        site_name = 'Haleakala-Faulkes Telescope North (FTN)'
    elif site_code == 'E10' or site_code == 'FTS':
# MPC code for FTS. Positions from JPL HORIZONS ( 149d04'13.0''E, 31d16'23.4''S, 1111.8 m )
        (site_lat, status)  =  (S.sla_daf2r(31, 16, 23.4))
        site_lat = -site_lat
        (site_long, status) = S.sla_daf2r(149, 04, 13.0)
        site_hgt = 1111.8
        site_name = 'Siding Spring-Faulkes Telescope South (FTS)'
    elif site_code == 'SQA' or site_code == 'G51':
        (site_lat, status)  =  S.sla_daf2r(34, 41, 29.23)
        (site_long, status) =  S.sla_daf2r(120, 02, 32.0)
        site_long = -site_long
        site_hgt = 328.0
        site_name = 'Sedgwick Observatory (SQA)'
    elif site_code == 'ELP' or site_code == '711' or site_code == 'V37':
        (site_lat, status)  =  S.sla_daf2r(30, 40, 47.53)
        (site_long, status) =  S.sla_daf2r(104, 00, 54.63)
        site_long = -site_long
        site_hgt = 2010.0
        site_name = 'LCOGT Node at McDonald Observatory (ELP)'
    elif site_code == 'BPL' or site_code == '500':
        (site_lat, status)  =  S.sla_daf2r(34, 25, 57)
        (site_long, status) =  S.sla_daf2r(119, 51, 46)
        site_long = -site_long
        site_hgt = 7.0
        site_name = 'LCOGT Back Parking Lot Node (BPL)'
    elif site_code == 'LSC-DOMA-1M0A' or site_code == 'W85':
# Latitude, longitude from Eric Mamajek (astro-ph: 1210.1616) Table 6. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(30, 10, 2.58)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 17.24)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2201.0
        site_name = 'LCOGT LSC Node 1m0 Dome A at Cerro Tololo'
    elif site_code == 'LSC-DOMB-1M0A' or site_code == 'W86':
# Latitude, longitude from Eric Mamajek (astro-ph: 1210.1616) Table 6. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(30, 10, 2.39)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 16.78)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2201.0
        site_name = 'LCOGT LSC Node 1m0 Dome B at Cerro Tololo'
    elif site_code == 'LSC-DOMC-1M0A' or site_code == 'W87':
# Latitude, longitude from Eric Mamajek (astro-ph: 1210.1616) Table 6. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(30, 10, 2.81)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 16.85)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2201.0
        site_name = 'LCOGT LSC Node 1m0 Dome C at Cerro Tololo'
    elif site_code == 'LSC-AQWA-0M4A' or site_code == 'W85':
# Latitude, longitude from somewhere
        (site_lat, status)  =  S.sla_daf2r(30, 10, 3.79)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 16.88)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2202.5
        site_name = 'LCOGT LSC Node 0m4a Aqawan A at Cerro Tololo'
    elif site_code == 'CPT-DOMA-1M0A' or site_code == 'K91':
# Latitude, longitude from site GPS co-ords plus offsets from site plan. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(32, 22, 50.0)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(20, 48, 36.65)
        site_hgt = 1807.0
        site_name = 'LCOGT CPT Node 1m0 Dome A at Sutherland'
    elif site_code == 'CPT-DOMB-1M0A' or site_code == 'K92':
# Latitude, longitude from site GPS co-ords plus offsets from site plan. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(32, 22, 50.0)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(20, 48, 36.13)
        site_hgt = 1807.0
        site_name = 'LCOGT CPT Node 1m0 Dome B at Sutherland'
    elif site_code == 'CPT-DOMC-1M0A' or site_code == 'K93':
# Latitude, longitude from site GPS co-ords plus offsets from site plan. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(32, 22, 50.38)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(20, 48, 36.39)
        site_hgt = 1807.0
        site_name = 'LCOGT CPT Node 1m0 Dome C at Sutherland'
    elif site_code == 'COJ-DOMA-1M0A' or site_code == 'Q63':
# Latitude, longitude from Google Earth guesswork. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(31, 16, 22.56)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(149, 04, 14.33)
        site_hgt = 1168.0
        site_name = 'LCOGT COJ Node 1m0 Dome A at Siding Spring'
    elif site_code == 'COJ-DOMB-1M0A' or site_code == 'Q64':
# Latitude, longitude from Google Earth guesswork. Height
# corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(31, 16, 22.89)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(149, 04, 14.75)
        site_hgt = 1168.0
        site_name = 'LCOGT COJ Node 1m0 Dome B at Siding Spring'
    else:
# Obtain latitude, longitude of the observing site.
# Reverse longitude to get the more normal East-positive convention
        (site_num, site_name, site_long, site_lat, site_hgt) = S.sla_obs(0, site_code)
        site_name = site_name.rstrip()
        site_long = -site_long

    logger.debug("Site name, lat/long/height=%s %f %f %.1f" % (site_name, site_long, site_lat, site_hgt))
    return (site_name, site_long, site_lat, site_hgt)

def moon_ra_dec(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg=False):
    '''Calculate the topocentric (from an observing location) apparent RA, Dec
    of the Moon. <date> is a UTC datetime, obsvr_long, obsvr_lat are geodetic
    North/East +ve observatory positions (in radians) and obsvr_hgt is the height
    (in meters).
    Returns a (RA, Dec, diameter) (in radians) tuple.'''

    body = 3 # The Moon...

    mjd_tdb = datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg)

# Compute Moon's apparent RA, Dec, diameter (all in radians)
    (moon_ra, moon_dec, diam) = S.sla_rdplan(mjd_tdb, body, obsvr_long, obsvr_lat)

    logger.debug("Moon RA, Dec, diam=%s %s %s" % (moon_ra, moon_dec, diam))
    return (moon_ra, moon_dec, diam)

def atmos_params(airless):
    '''Atmospheric parameters either airless or average'''
    if airless:
        temp_k = 0.0
        pres_mb = 0.0
        rel_humid = 0.0
        wavel = 0.0
        tlr = 0.0
    else:
# "Standard" atmosphere
        temp_k = 283.0 # 10 degC
# Average of FTN (709), FTS (891), TFN(767.5), SAAO(827), CTIO(777), SQA(981)
# and McDonald (790) on 2011-02-05
        pres_mb = 820.0
        rel_humid = 0.5
        wavel = 0.55 # Approx Bessell V
# International Civil Aviation Organization (ICAO) defines an international
# standard atmosphere (ISA) at 6.49 K/km
        tlr = 0.0065

    return (temp_k, pres_mb, rel_humid, wavel, tlr)

def moon_alt_az(date, moon_app_ra, moon_app_dec, obsvr_long, obsvr_lat,\
    obsvr_hgt, dbg=False):
    '''Calculate Moon's Azimuth, Altitude (returned in radians).
    No refraction or polar motion is assumed.'''

# No atmospheric refraction...
    airless = True
    (temp_k, pres_mb, rel_humid, wavel, tlr) = atmos_params(airless)

# Assume no polar motion
    xp = yp = 0.0

# Compute MJD_UTC
    mjd_utc = datetime2mjd_utc(date)
    logger.debug(mjd_utc)
# Compute UT1-UTC

    dut = ut1_minus_utc(mjd_utc)
    logger.debug(dut)
# Perform apparent->observed place transformation
    (obs_az, obs_zd, obs_ha, obs_dec, obs_ra) = S.sla_aop(moon_app_ra, moon_app_dec,\
        mjd_utc, dut, obsvr_long, obsvr_lat, obsvr_hgt, xp, yp, \
        temp_k, pres_mb, rel_humid, wavel, tlr)

# Normalize azimuth into range 0..2PI
    obs_az = S.sla_ranorm(obs_az)
# Convert zenith distance to altitude (assumes no depression of the horizon
# due to observers' elevation above sea level)

    obs_alt = (pi/2.0)-obs_zd
    logger.debug("Az, ZD, Alt=%f %f %f" % (obs_az, obs_zd, obs_alt))
    return (obs_az, obs_alt)

def moonphase(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg=False):

    mjd_tdb = datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg)
    (moon_ra, moon_dec, moon_diam) = S.sla_rdplan(mjd_tdb, 3, obsvr_long, obsvr_lat)

    (sun_ra, sun_dec, sun_diam) = S.sla_rdplan (mjd_tdb, 0, obsvr_long, obsvr_lat)

    cosphi = ( sin(sun_dec) * sin(moon_dec) + cos(sun_dec) \
        * cos(moon_dec) * cos(sun_ra - moon_ra) )
    logger.debug("cos(phi)=%s" % cosphi)

# Full formula for phase angle, i. Requires r (Earth-Sun distance) and del(ta) (the
# Earth-Moon distance) neither of which we have with our methods. However Meeus
# _Astronomical Algorithms_ p 316 reckons we can "put cos(i) = -cos(phi) and k (the
# Moon phase) will never be in error by more than 0.0014"
#    i = atan2( r * sin(phi), del - r * cos(phi) )

    cosi = -cosphi
    logger.debug("cos(i)=%s" % cosi)
    mphase = (1.0 + cosi) / 2.0

    return mphase

def compute_hourangle(date, obsvr_long, obsvr_lat, obsvr_hgt, mean_ra, mean_dec, dbg=False):

    mjd_tdb = datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, False)
 # Compute MJD_UTC
    mjd_utc =  datetime2mjd_utc(date)

# Compute UT1-UTC

    dut = ut1_minus_utc(mjd_utc)

# Compute local apparent sidereal time
# Do GMST first which takes UT1 and then add East longitude and the equation of the equinoxes
# (which takes TDB)
#
    gmst = S.sla_gmst(mjd_utc+(dut/86400.0))
    stl = gmst + obsvr_long + S.sla_eqeqx(mjd_tdb)

    logger.debug('GMST, LAST, EQEQX, GAST, long= %.17f %.17f %E %.17f %.17f' % (gmst, stl, S.sla_eqeqx(mjd_tdb), gmst+S.sla_eqeqx(mjd_tdb), obsvr_long))

    (app_ra, app_dec) = S.sla_map(mean_ra, mean_dec, 0.0, 0.0, 0.0, 0.0, 2000.0, mjd_tdb)
    (ra_str, dec_str) = radec2strings(app_ra, app_dec)
    logger.debug("%f %f %s %s" % (app_ra, app_dec, ra_str, dec_str))
    hour_angle = stl - app_ra
    logger.debug(hour_angle)
    hour_angle = S.sla_drange(hour_angle)
    logger.debug(hour_angle)

    return hour_angle

def radec2strings(ra_radians, dec_radians, seperator=' '):
    '''Format an (RA, Dec) pair (in radians) into a tuple of strings, with 
    configurable seperator (defaults to <space>).
    There is no sign produced on the RA quantity unless ra_radians and dec_radians
    are equal.'''

    ra_format =  "%s%02.2d%c%02.2d%c%02.2d.%02.2d"
    dec_format = "%s%02.2d%c%02.2d%c%02.2d.%d"

    (rsign, ra ) = S.sla_dr2tf(2, ra_radians) 
    (dsign, dec) = S.sla_dr2af(1, dec_radians)

    if rsign == '+' and ra_radians != dec_radians: rsign = ''
    ra_str = ra_format % ( rsign, ra[0], seperator, ra[1], seperator, ra[2],  ra[3] )
    dec_str = dec_format % ( dsign, dec[0], seperator, dec[1], seperator, dec[2], dec[3] )

    return (ra_str, dec_str)

def get_mountlimits(site_code_or_name):
    '''Returns the negative, positive and altitude mount limits (in degrees)
    for the LCOGT telescopes specified by <site_code_or_name>.

    <site_code_or_name> can either be a MPC site code e.g. 'V37' (=ELP 1m),
    or by desigination e.g. 'OGG-CLMA-2M0A' (=FTN)'''

    site = site_code_or_name.upper()
    ha_pos_limit = 12.0 * 15.0
    ha_neg_limit = -12.0 * 15.0
    alt_limit = 25.0

    if '-1M0A' in site or site in ['V37', 'W85', 'W86', 'W87', 'K91', 'K92', 'K93', 'Q63', 'Q64']:
        ha_pos_limit = 4.5 * 15.0
        ha_neg_limit = -4.5 * 15.0
        alt_limit = 30.0
    elif '-AQWA' in site:
        ha_pos_limit = 4.25 * 15.0
        ha_neg_limit = -4.25 * 15.0

    return (ha_neg_limit, ha_pos_limit, alt_limit)


def get_sitecam_params(site):
    '''Translates <site> (e.g. 'FTN') to MPC site code, pixel scale, maximum
    exposure time, setup and exposure overheads.
    site_code is set to 'XXX' and the others are set to -1 in the event of an
    unrecognized site.'''

    onem_fov = 15.5
    onem_pixscale = 0.464
    onem_sinistro_fov = 26.4
    onem_sinistro_pixscale = 0.389
    point4m_fov = 24.35
    point4m_pixscale = 0.571
    normal_alt_limit = 30.0
    twom_alt_limit = 20.0

    onem_exp_overhead = 15.5
    sinistro_exp_overhead = 48.0
    onem_setup_overhead = 120.0
    twom_setup_overhead = 180.0
    twom_exp_overhead = 22.5
    point4m_exp_overhead = 7.5 # for BPL

    valid_site_codes = [ 'V37', 'W85', 'W86', 'W87', 'K91', 'K92', 'K93', 'Q63', 'Q64' ] 

    site = site.upper()
    if site == 'FTN' or 'OGG-CLMA' in site or site == 'F65':
        site_code = 'F65'
        setup_overhead = twom_setup_overhead
        exp_overhead = twom_exp_overhead
        pixel_scale = 0.304
        fov = arcmins_to_radians(10.0)
        max_exp_length = 300.0
        alt_limit = twom_alt_limit
    elif site == 'FTS' or 'COJ-CLMA' in site or site == 'E10':
        site_code = 'E10'
        setup_overhead = twom_setup_overhead
        exp_overhead = twom_exp_overhead
        pixel_scale = 0.304
        fov = arcmins_to_radians(10.0)
        max_exp_length = 300.0
        alt_limit = twom_alt_limit
    elif site in valid_site_codes:
        setup_overhead = onem_setup_overhead
        exp_overhead = onem_exp_overhead
        pixel_scale = onem_pixscale
        fov = arcmins_to_radians(onem_fov)
        if 'W86' in site or 'W87' in site:
            pixel_scale = onem_sinistro_pixscale
            fov = arcmins_to_radians(onem_sinistro_fov)
            exp_overhead = sinistro_exp_overhead
        max_exp_length = 300.0
        alt_limit = normal_alt_limit
        site_code = site
    else:
# Unrecognized site
        site_code = 'XXX'
        setup_overhead = exp_overhead = pixel_scale = fov = max_exp_length = alt_limit = -1

    return (site_code, setup_overhead, exp_overhead, pixel_scale, fov, max_exp_length, alt_limit)
