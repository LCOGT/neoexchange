"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

ephem_subs.py -- Asteroid ephemeris related routines.

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
from datetime import datetime, timedelta, time
from math import sin, cos, tan, asin, acos, atan2, degrees, radians, pi, sqrt, fabs, exp, log10, ceil, log

try:
    import pyslalib.slalib as S
except:
    pass

from numpy import array, concatenate, zeros
import copy
from itertools import groupby
import re

# Local imports
from astrometrics.time_subs import datetime2mjd_utc, datetime2mjd_tdb, mjd_utc2mjd_tt, ut1_minus_utc, round_datetime
# from astsubs import mpc_8lineformat
import astrometrics.site_config as cfg


logger = logging.getLogger(__name__)


def compute_phase_angle(r, delta, es_Rsq, dbg=False):
    """Method to compute the phase angle (beta), trapping bad values"""
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


def perturb_elements(orbelems, epoch_mjd, mjd_tt, comet, perturb):
    """
    Convert Orbital elements into radians.
    Return Perturbed elements if requested.
    """

    if comet is True:
        jform = 3
        p_orbelems = {'LongNode' : radians(orbelems['longascnode']),
                      'Inc' : radians(orbelems['orbinc']),
                      'ArgPeri' : radians(orbelems['argofperih']),
                      'SemiAxisOrQ' : orbelems['perihdist'],
                      'Ecc' : orbelems['eccentricity'],
                     }
        orbelems['meananom'] = 0.0
        aorq = orbelems['perihdist']
        epoch_mjd = datetime2mjd_utc(orbelems['epochofperih'])
    else:
        jform = 2
        p_orbelems = {'LongNode' : radians(orbelems['longascnode']),
                      'Inc' : radians(orbelems['orbinc']),
                      'ArgPeri' : radians(orbelems['argofperih']),
                      'SemiAxisOrQ' : orbelems['meandist'],
                      'Ecc' : orbelems['eccentricity']
                     }
        try:
            p_orbelems['MeanAnom'] = radians(orbelems['meananom'])
        except TypeError:
            p_orbelems['MeanAnom'] = 0.0
            orbelems['meananom'] = 0.0
        try:
            aorq = float(orbelems['meandist'])
        except TypeError:
            aorq = 0.0
    p_orbelems['H'] = orbelems['abs_mag']
    p_orbelems['G'] = orbelems['slope']
    if perturb is True:
        (p_epoch_mjd, p_orbelems['Inc'], p_orbelems['LongNode'], p_orbelems['ArgPeri'],
         p_orbelems['SemiAxisOrQ'], p_orbelems['Ecc'], p_orbelems['MeanAnom'], j) = S.sla_pertel( jform, epoch_mjd,
                                                                                                  mjd_tt, epoch_mjd, radians(orbelems['orbinc']), radians(orbelems['longascnode']),
                                                                                                  radians(orbelems['argofperih']), aorq, orbelems['eccentricity'], radians(orbelems['meananom']))
    else:
        p_epoch_mjd = epoch_mjd
        j = 0
    return p_orbelems, p_epoch_mjd, j


def compute_ephem(d, orbelems, sitecode, dbg=False, perturb=True, display=False, detailed=False):
    """Routine to compute the geocentric or topocentric position, magnitude,
    motion and altitude of an asteroid or comet for a specific date and time
    from a dictionary of orbital elements.
    """
# Light travel time for 1 AU (in sec)
    tau = 499.004783806

# Compute MJD for UTC
    mjd_utc = datetime2mjd_utc(d)

# Compute epoch of the elements as a MJD
    try:
        epochofel = datetime.strptime(orbelems['epochofel'], '%Y-%m-%d %H:%M:%S')
    except TypeError:
        epochofel = orbelems['epochofel']
    epoch_mjd = datetime2mjd_utc(epochofel)

    logger.debug('Element Epoch= %.1f' % epoch_mjd)
    logger.debug('MJD(UTC) =   %.15f' % mjd_utc)
    logger.debug(' JD(UTC) = %.8f' % (mjd_utc + 2400000.5))

# Convert MJD(UTC) to MJD(TT)
    mjd_tt = mjd_utc2mjd_tt(mjd_utc)
    logger.debug('MJD(TT)  =   %.15f' % mjd_tt)

# Compute UT1-UTC

    dut = ut1_minus_utc(mjd_utc)
    logger.debug("UT1-UTC  = %.15f" % dut)

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

    if site_name == '?' or sitecode == '500':
        if site_name == '?':
            logger.warning("WARN: No site co-ordinates found, computing for geocenter")
        pvobs = zeros(6)
    else:
        # Compute local apparent sidereal time
        # Do GMST first which takes UT1 and then add East longitiude and the equation of the equinoxes
        # (which takes TDB; but we use TT here)

        gmst = S.sla_gmst(mjd_utc+(dut/86400.0))
        stl = gmst + site_long + S.sla_eqeqx(mjd_tt)
        logger.debug('GMST, LAST, EQEQX, GAST, long= %.17f %.17f %E %.17f %.17f' % (gmst, stl, S.sla_eqeqx(mjd_tt), gmst+S.sla_eqeqx(mjd_tt), site_long))
        pvobs = S.sla_pvobs(site_lat, site_hgt, stl)

    logger.debug("PVobs(orig)=%s\n            %s" % (pvobs[0:3], pvobs[3:6]*86400.0))

# Apply transpose of precession/nutation matrix to pv vector to go from
# true equator and equinox of date to J2000.0 mean equator and equinox (to
# match the reference system of sla_epv)
#
    pos_new = S.sla_dimxv(rmat, pvobs[0:3])
    vel_new = S.sla_dimxv(rmat, pvobs[3:6])
    pvobs_new = concatenate([pos_new, vel_new])
    logger.debug("PVobs(new)=%s\n            %s" % (pvobs_new[0:3], pvobs_new[3:6]*86400.0))

# Earth position and velocity

# Moderate precision/speed version. N.B different order of bary vs. heliocentric!
# (vel_bar, pos_bar, e_vel_hel, e_pos_hel) = S.sla_evp(mjd_tt, 2000.0)

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
    jform = 2
    if 'elements_type' in orbelems and str(orbelems['elements_type']).upper() == 'MPC_COMET':
        comet = True
        jform = 3

    # Convert orbital elements into radians and perturb if requested
    p_orbelems, p_epoch_mjd, j = perturb_elements(orbelems, epoch_mjd, mjd_tt, comet, perturb)

    if j != 0:
        logger.error("Perturbing error=%s" % j)
        return []

    r3 = -100.
    delta = 0.0
    ltt = 0.0
    pos = zeros(3)
    vel = zeros(3)
    # rel_pos= [0.0, 0.0, 0.0]

    while fabs(delta - r3) > .01:
        r3 = delta
        if comet is True:
            (pv, status) = S.sla_planel(mjd_tt - (ltt/86400.0), jform, p_epoch_mjd,
                            p_orbelems['Inc'], p_orbelems['LongNode'],
                            p_orbelems['ArgPeri'], p_orbelems['SemiAxisOrQ'], p_orbelems['Ecc'],
                            0.0, 0.0)
        else:
            (pv, status) = S.sla_planel(mjd_tt - (ltt/86400.0), jform, p_epoch_mjd,
                            p_orbelems['Inc'], p_orbelems['LongNode'],
                            p_orbelems['ArgPeri'], p_orbelems['SemiAxisOrQ'], p_orbelems['Ecc'],
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
        delta_dot = ((vel[0]*pos[0]+vel[1]*pos[1]+vel[2]*pos[2])/delta)*86400.0
        logger.debug("Geometric distance, delta (AU)=%s" % delta)

# Light travel time to asteroid
        ltt = tau * delta
        logger.debug("Light travel time (sec, min, days)=%s %s %s" % (ltt, ltt/60.0, ltt/86400.0))

# Correct position for planetary aberration
    for i, a_pos in enumerate(pos):
        pos[i] = a_pos - (ltt * vel[i])

    logger.debug("Earth->Asteroid [x,y,z]=%s" % pos)
    logger.debug("Earth->Asteroid [x,y,z]= %20.15E %20.15E %20.15E" % (pos[0], pos[1], pos[2]))
    logger.debug("Earth->Asteroid [xdot,ydot,zdot]=%s %s %s" % (vel[0]*86400.0, vel[1]*86400.0, vel[2]*86400.0))

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
    r_dot = ((pv[3]*cposx+pv[4]*cposy+pv[5]*cposz)/r)*86400.0

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

    mag = -99
    mag_dot = 0
    beta = 0
    separation = 0
    if comet is True:
        # Calculate magnitude of comet
        # Here 'H' is the absolute magnitude, 'kappa' the slope parameter defined in Meeus
        # _Astronomical Algorithms_ p. 231, is equal to 2.5 times the 'G' read from the elements
        if p_orbelems['H'] and p_orbelems['G']:
            mag = p_orbelems['H'] + 5.0 * log10(delta) + 2.5 * p_orbelems['G'] * log10(r)
            mag_dot = 5.0 * delta_dot / log(10) / delta + 2.5 * p_orbelems['G'] * r_dot / log(10) / r

    else:
        # Compute phase angle, beta (Sun-Target-Earth angle)
        beta = compute_phase_angle(r, delta, es_Rsq)
        beta_dot = -1/sqrt(1-(cos(beta))**2)*(r*(delta**2-r**2+1)*delta_dot-delta*(delta**2-r**2-1)*r_dot)/(2*delta*delta*r*r)

        phi1 = exp(-3.33 * (tan(beta/2.0))**0.63)
        phi2 = exp(-1.87 * (tan(beta/2.0))**1.22)

        phi1_dot = phi1 * -3.33 * 0.63 * (tan(beta/2.0))**(0.63-1) * 0.5 * beta_dot * (cos(beta/2.0))**(-2)
        phi2_dot = phi1 * -1.87 * 1.22 * (tan(beta/2.0))**(1.22-1) * 0.5 * beta_dot * (cos(beta/2.0))**(-2)

        #    logger.debug("Phi1, phi2=%s" % phi1,phi2)

        # If requested, calculate the effective separation between the RA of object and the sun as seen on the sky.
        # We make simplifying assumptions that more or less balance out, such as the observers are located
        # anywhere on the equator, but can see all the way to the horizon.
        if detailed is not False:
            # compute RA/Dec of the Sun
            sun_coord = S.sla_dcc2s(e_pos_hel * -1)
            sun_ra = S.sla_dranrm(sun_coord[0])
            sun_dec = sun_coord[1]
            # rotate object ra to solar position
            lon_new = ra - sun_ra
            lon_new = atan2(sin(lon_new-pi/2) * cos(sun_dec) - tan(dec) * sin(sun_dec), cos(lon_new-pi/2)) + pi/2
            # convert longitude of object to distance in radians
            separation = abs(S.sla_drange(lon_new))

        # Calculate magnitude of object
        if p_orbelems['H'] and p_orbelems['G']:
            try:
                mag = p_orbelems['H'] + 5.0 * log10(r * delta) - \
                    (2.5 * log10((1.0 - p_orbelems['G'])*phi1 + p_orbelems['G']*phi2))
                mag_dot = 5 * (delta * r_dot + r * delta_dot) / (r * delta * log(10)) - \
                    2.5 * ((1.0 - p_orbelems['G'])*phi1_dot + p_orbelems['G']*phi2_dot) / \
                    (log(10) * ((1.0 - p_orbelems['G'])*phi1 + p_orbelems['G']*phi2))
            except ValueError:
                logger.error("Error computing magnitude")
                logger.error("{")
                for key in p_orbelems:
                    logger.error("'%s': %s" % (key, str(p_orbelems[key])))
                logger.error("}")
                logger.error("r, delta=%f %f" % (r, delta))
    az_rad, alt_rad = moon_alt_az(d, ra, dec, site_long, site_lat, site_hgt)
    airmass = S.sla_airmas((pi/2.0)-alt_rad)
    alt_deg = degrees(alt_rad)

#    if display: print("  %02.2dh %02.2dm %02.2d.%02.2ds %s%02.2dd %02.2d\' %02.2d.%01.1d\"  V=%.1f  %5.2f %.1f % 7.3f %8.4f" % ( ra_geo_deg[0],
    if display:
        print("  %02.2d %02.2d %02.2d.%02.2d %s%02.2d %02.2d %02.2d.%01.1d  V=%.1f  %5.2f %.1f % 7.3f %8.4f" % ( ra_geo_deg[0],
            ra_geo_deg[1], ra_geo_deg[2], ra_geo_deg[3],
            dsign.decode('utf-8'), dec_geo_deg[0], dec_geo_deg[1], dec_geo_deg[2], dec_geo_deg[3],
            mag, total_motion, sky_pa, alt_deg, airmass))

# Compute South Polar Distance from Dec
    dec_arcsec_decimal = dec_geo_deg[2] + dec_geo_deg[3]
    dec_arcmin_decimal = dec_geo_deg[1] + (dec_arcsec_decimal/60.)
    dec_deg_decimal = dec_geo_deg[0] + (dec_arcmin_decimal/60.)
    if b'+' in dsign:
        spd = 90. + dec_deg_decimal
    elif b'-' in dsign:
        spd = 90. - dec_deg_decimal
    else:
        spd = None

#               0   1   2   3       4           5       6       7
    emp_line = (d, ra, dec, mag, total_motion, alt_deg, spd, sky_pa)
    if detailed:
        return emp_line, mag_dot, separation

    return emp_line


def compute_relative_velocity_vectors(obs_pos_hel, obs_vel_hel, obj_pos, obj_vel, delta, dbg=True):
    """Computes relative velocity vector between the observer and the object.
    Adapted from the Bill Gray/find_orb routine of the same name with some
    changes as obj_pos in our code is already the needed result of subtracting
    the Heliocenter->Observer vector from the Heliocenter->Asteroid vector and
    so we don't need to do this when we form the first 3 elements of matrix."""

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
    while i < 9:
        vel[i // 3] = matrix[i] * j2000_vel[0] + matrix[i+1] * j2000_vel[1] + matrix[i+2] * j2000_vel[2]
        i += 3

    return vel


def compute_sky_motion(sky_vel, delta, dbg=True):
    """Computes the total motion and Position Angle, along with the RA, Dec
    components, of an asteroids' sky motion. Motion is in "/min, PA in degrees East of North.

    Adapted from the Bill Gray/find_orb routine of the same name."""

    ra_motion = degrees(sky_vel[1]) / delta
    dec_motion = degrees(sky_vel[2]) / delta
    ra_motion = -ra_motion * 60.0 / 24.0
    dec_motion = dec_motion * 60.0 / 24.0

    sky_pa = 180.0 + degrees(atan2(-ra_motion, -dec_motion))
    logger.debug( "RA motion, Dec motion, PA=%10.7f %10.7f %6.1f" % (ra_motion, dec_motion, sky_pa ))

    total_motion = sqrt(ra_motion * ra_motion + dec_motion * dec_motion)
    logger.debug( "Total motion=%10.7f" % total_motion)

    return total_motion, sky_pa, ra_motion, dec_motion


def format_emp_line(emp_line, site_code):

    # Convert radians for RA, Dec into strings for printing
    (ra_string, dec_string) = radec2strings(emp_line[1], emp_line[2], ' ')
    # Format time and print out the overall ephemeris
    emp_time = datetime.strftime(emp_line[0], '%Y %m %d %H:%M')

    if str(site_code) == '500':
        # Geocentric position, so no altitude. moon parameters, score or hour angle
        geo_row_format = "%-16s|%s|%s|%04.1f|%5.2f|%5.1f|N/A|N/A|N/A|N/A|N/A|N/A"

        formatted_line = geo_row_format % (emp_time, ra_string, dec_string,
            emp_line[3], emp_line[4], emp_line[7])

    else:
        # Get site and mount parameters
        (site_name, site_long, site_lat, site_hgt) = get_sitepos(site_code)
        (ha_neg_limit, ha_pos_limit, mount_alt_limit) = get_mountlimits(site_code)

#                         Date  RA Dec Mag   Motion P.A  Alt Mphase Msep Malt   Score HA
        blk_row_format = "%-16s|%s|%s|%04.1f|%5.2f|%5.1f|%+d|%04.2f|%3d|%+02.2d|%+04d|%s"

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
        if ha_in_deg >= ha_pos_limit or ha_in_deg <= ha_neg_limit:
            ha_string = 'Limits'
        else:
            (ha_string, junk) = radec2strings(ha, ha, ':')
            ha_string = ha_string[0:6]

# Calculate slot score
        slot_score = compute_score(emp_line[5], moon_alt, moon_obj_sep, mount_alt_limit)

# Calculate the no. of FOVs from the starting position
#    pointings_sep = S.sla_dsep(emp_line[1], emp_line[2], start_ra, start_dec)
#    num_fov = int(pointings_sep/ccd_fov)

        formatted_line = blk_row_format % (emp_time, ra_string, dec_string,
            emp_line[3], emp_line[4],  emp_line[7], emp_line[5],
            moon_phase, moon_obj_sep, moon_alt, slot_score, ha_string)

    line_as_list = formatted_line.split('|')
    return line_as_list


def call_compute_ephem(elements, dark_start, dark_end, site_code, ephem_step_size, alt_limit=0):
    """Wrapper for compute_ephem to enable use within plan_obs (or other codes)
    by making repeated calls for datetimes from <dark_start> -> <dark_end> spaced
    by <ephem_step_size> seconds. The results are assembled into a list of tuples
    in the same format as returned by read_findorb_ephem()"""

#    print
#    formatted_elem_lines = mpc_8lineformat(elements)
#    for line in formatted_elem_lines:
#        print line

    slot_length = 0  # XXX temporary hack
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
        if 'epochofel' in elements:
            emp_line = compute_ephem(ephem_time, elements, site_code, dbg=False, perturb=True, display=False)
        elif 'ra' in elements and 'dec' in elements:
            emp_line = compute_sidereal_ephem(ephem_time, elements, site_code)
        else:
            break
        full_emp.append(emp_line)
        ephem_time = ephem_time + timedelta(seconds=step_size_secs)

# Get subset of ephemeris when it's dark and object is up
    visible_emp = dark_and_object_up(full_emp, dark_start, dark_end, slot_length, alt_limit)
    emp = []
    for line in visible_emp:
        emp.append(format_emp_line(line, site_code))

    return emp


def read_findorb_ephem(empfile):
    """Routine to read find_orb produced ephemeris.emp files from non-interactive
    mode.
    Returns a dictionary containing the ephemeris details (object id, time system,
    motion rate units, sitecode) and a list of tuples containing:
    Datetime, RA, Dec, magnitude, rate, altitude"""

    emp = []
    emp_fh = open(empfile, 'r')
    uncertain_mag = False
    for line in emp_fh.readlines():
        # Skip blank lines first off all
        if len(line.lstrip()) != 0:
            if line.lstrip()[0] == '#' :
                # print(line.lstrip())
                # First line contains object id and the sitecode the ephemeris is for. Fetch...
                chunks = list(filter(None, re.split("[,(,),\n,:]+", line.lstrip()[1:])))
                try:
                    chunks.remove(' ')
                except ValueError:
                    pass
                obj_id = ''
                for chunk in chunks[::-1]:
                    if chunk.isdigit():
                        obj_id = chunk
                        break
                if not obj_id:
                    if '19' in chunks[-1] or '20' in chunks[-1]:
                        obj_id = chunks[-1].replace(' ', '').replace('=', '')
                    else:
                        logger.warning("Could not pull Object ID from header line1 ({:s})".format(line))
                        return None, None
                ephem_info = {'obj_id' : obj_id,
                              'emp_sitecode' : chunks[0]}
            elif line.lstrip()[0:4] == 'Date':
                # next line has the timescale of the ephemeris and the units of the motion
                # rate. We *hope* it's always UTC and arcmin/hr but grab and check anyway...
                chunks = line.strip().split()
                if len(chunks) != 13 and len(chunks) != 14 :
                    logger.warning("Unexpected number of chunks in header line2 ({:d})".format(len(chunks)))
                    return None, None
                ephem_info2 = {'emp_timesys' : chunks[1], 'emp_rateunits' : chunks[9]}
            elif line.lstrip()[0:4] == '----':
                pass
            else:
                # Read main ephemeris
                line = line.strip()
                chunks = line.split()
                emp_datetime = datetime(int(chunks[0]), int(chunks[1]), int(chunks[2]), int(chunks[3][0:2]), int(chunks[3][3:5]))
                emp_ra, status = S.sla_dtf2r(chunks[4], chunks[5], chunks[6])
                if status != 0:
                    logger.error("Error converting RA value")
                decstr = ' '.join([chunks[x] for x in range(7, 10)])
                nstrt = 1
                nstrt, emp_dec, status = S.sla_dafin(decstr, nstrt)
                if status != 0:
                    logger.error("Error converting Dec value")
                    logger.error("Decstr=", decstr)
                    logger.error(chunks)
                if '?' in chunks[13]:
                    # Phase angle >120deg, magnitude uncertain
                    if uncertain_mag is False:
                        logger.warning("Phase angle >120deg, magnitude uncertain")
                    chunks[13] = chunks[13].replace('?', '')
                    uncertain_mag = True
                emp_mag = float(chunks[13])
                emp_rate = float(chunks[14])
                try:
                    emp_alt = float(chunks[16])
                except ValueError:
                    if 'm' in chunks[16]:
                        emp_alt = float(chunks[16][:-1])/1000
                    elif "'" in chunks[16]:
                        emp_alt = float(chunks[16][:-1])*60
                    else:
                        logger.warning("Unable to read Ephemeris sig err {}".format(chunks[16]))
                        return None, None
                emp_line = (emp_datetime, emp_ra, emp_dec, emp_mag, emp_rate, emp_alt)
                # print(emp_line)
                emp.append(emp_line)
    # Done, close file
    emp_fh.close()

    # Join ephem_info dictionaries together
    ephem_info.update(ephem_info2)

    return ephem_info, emp


def make_unit_vector(angle):
    """Make a unit vector from the passed angle (in degrees).
    The result is returned in a numpy array"""

    return array([cos(radians(angle)), sin(radians(angle))])


def average_angles(angle1, angle2):
    """Average two angles <angle1> <angle2> (in degrees) correctly.
    The result is returned in degrees."""

    v1 = make_unit_vector(angle1)
    v2 = make_unit_vector(angle2)
    v = v1 + v2
    average = degrees(atan2(v[1], v[0]))
    if average < 0.0:
        average += 360.0
    return average


def determine_rates_pa(start_time, end_time, elements, site_code):
    """Determine the minimum and maximum rates (in "/min) and the average
    position angle (PA) and range of PA (delta PA) during the time
    from <start_time> -> <end_time> for the body represented by <elements>
    from the <site_code>"""

    first_frame_emp = compute_ephem(start_time, elements, site_code, dbg=False, perturb=True, display=True)
    # Check for no ephemeris caused by perturbing error
    if not first_frame_emp:
        first_frame_emp = compute_ephem(start_time, elements, site_code, dbg=False, perturb=False, display=True)
    first_frame_speed = first_frame_emp[4]
    first_frame_pa = first_frame_emp[7]

    last_frame_emp = compute_ephem(end_time, elements, site_code, dbg=False, perturb=True, display=True)
    # Check for no ephemeris caused by perturbing error
    if not last_frame_emp:
        last_frame_emp = compute_ephem(end_time, elements, site_code, dbg=False, perturb=False, display=True)
    last_frame_speed = last_frame_emp[4]
    last_frame_pa = last_frame_emp[7]

    logger.debug("Speed range %.2f ->%.2f, PA range %.1f->%.1f" % (first_frame_speed , last_frame_speed, first_frame_pa, last_frame_pa))
    min_rate = min(first_frame_speed, last_frame_speed) - (0.01*min(first_frame_speed, last_frame_speed))
    max_rate = max(first_frame_speed, last_frame_speed) + (0.01*max(first_frame_speed, last_frame_speed))
    pa = average_angles(first_frame_pa, last_frame_pa)
    deltapa = max(first_frame_pa, last_frame_pa) - min(first_frame_pa, last_frame_pa)
    if deltapa > 180.0:
        deltapa = 360.0 - deltapa
    deltapa = max(10.0, deltapa)

    return min_rate, max_rate, pa, deltapa


def determine_darkness_times(site_code, utc_date=datetime.utcnow(), debug=False):
    """Determine the times of darkness at the site specified by <site_code>
    for the date of [utc_date] (which defaults to UTC now if not given).
    The darkness times given are when the Sun is lower than -15 degrees
    altitude (intermediate between nautical (-12) and astronomical (-18)
    darkness, which has been chosen as more appropriate for fainter asteroids.
    """
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
    elif start_of_darkness.hour > end_of_darkness.hour > utc_date.hour:
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
    if accurate is True:
        (ad_start, ad_end) = accurate_astro_darkness(sitecode, utc_date)
    else:
        (ad_start, ad_end) = crude_astro_darkness(sitecode, utc_date)

    if ad_start is not None and ad_end is not None:
        if round_ad is True:
            ad_start = round_datetime(ad_start, 10)
            ad_end = round_datetime(ad_end, 10)

    return ad_start, ad_end


def crude_astro_darkness(sitecode, utc_date):
    """Really crude version of routine to compute times of astronomical
    darkness which just hard-wires times based on the site"""

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
        print("Unsupported sitecode", sitecode)
        return None, None

    return ad_start, ad_end


def accurate_astro_darkness(sitecode, utc_date, solar_pos=False, debug=False):

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
                 (0.019993 - T * 0.000101) * sin(2.0 * radians(sun_mean_anom)) +\
                 0.000290 * sin(3.0 * radians(sun_mean_anom))
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

    if solar_pos is not False:
        return sun_app_ra, sun_app_dec

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
    if debug:
        print(solarnoon + hourangle*4/1440, solarnoon - hourangle*4/1440)
    if debug:
        print(sunset, sunrise)

    if sunrise < sunset:
        sunrise = sunrise + 1
    if debug:
        to_return = [T, sun_mean_long, sun_mean_anom, earth_e, sun_eqcent,
            sun_true_long, degrees(omega), sun_app_long, degrees(eps0), eps,
            degrees(sun_app_ra), degrees(sun_app_dec), eqtime, hourangle]
        print(to_return)

    else:
        to_return = (utc_date+timedelta(days=sunset), utc_date+timedelta(days=sunrise))

    return to_return


def dark_and_object_up(emp, dark_start, dark_end, slot_length, alt_limit=30.0, debug=False):
    """Returns the subset of the passed ephemeris where the object is up and
    the site is dark.
    Modified 2013/1/21: Now slot_length is passed in so this is subtracted
    from the night end, ensuring blocks don't begin at sunrise."""

    dark_up_emp = []

    for x in emp:
        visible = False
        if (dark_start <= x[0] <= dark_end - timedelta(minutes=slot_length)) and x[5] >= float(alt_limit):
            visible = True
            dark_up_emp.append(x)
        if debug:
            print(x[0].date(), x[0].time(), (dark_start <= x[0] < dark_end - timedelta(minutes=slot_length)), x[5], alt_limit, visible)

    return dark_up_emp


class MagRangeError(Exception):
    """Raised when an invalid magnitude is found"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


BRIGHTEST_ALLOWABLE_MAG = 6


def get_mag_mapping(site_code):
    """Defines the site-specific mappings from target magnitude to desired
    slot length (in minutes) assuming minimum exposure count is 4. A null
    dictionary is returned if the site name isn't recognized"""

    twom_site_codes = ['F65', 'E10', '2M']
    good_onem_site_codes = ['V37', 'K91', 'K92', 'K93', 'W85', 'W86', 'W87', 'Q63', 'Q64', 'GOOD1M']
    # COJ normally has bad seeing, allow more time
    # Disabled by TAL 2018/8/10 after mirror recoating
#    bad_onem_site_codes = ['Q63', 'Q64']
    bad_onem_site_codes = ['BAD1M']
    point4m_site_codes = ['Z21', 'Z17', 'W89', 'W79', 'T04', 'T03', 'Q58', 'Q59', 'V38', 'L09', '0M4']

# Magnitudes represent upper bin limits
    site_code = site_code.upper()
    if site_code in twom_site_codes:
        # Mappings for FTN/FTS. Assumes Spectral+Solar filter
        mag_mapping = {
                17   : 5.5,
                17.5 : 7.5,
                18   : 10,
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
                16.0 : 5.5,
                16.5 : 6.5,
                17   : 9.5,
                17.5 : 12,
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
                16.0 : 6.5,
                16.5 : 9.5,
                17   : 12,
                17.5 : 15,
                18   : 17.5,
                19.5 : 20,
                20   : 22.5,
                20.5 : 25,
                21   : 27.5,
                21.5 : 32.5,
                22.0 : 35
               }
    elif site_code in point4m_site_codes:
        mag_mapping = {
                12   : 15.0,
                15   : 17.5,
                17.5 : 20,
                18.5 : 22.5,
                19.5 : 25,
                20   : 27.5,
                20.5 : 32.5,
                21.0 : 35
               }
    else:
        mag_mapping = {}

    return mag_mapping


def determine_slot_length(mag, site_code, debug=False):

    if mag < BRIGHTEST_ALLOWABLE_MAG:
        raise MagRangeError("Target too bright")

# Obtain magnitude->slot length mapping dictionary
    mag_mapping = get_mag_mapping(site_code)
    if debug:
        print(mag_mapping)
    if mag_mapping == {}:
        return 0

    # Derive your tuple from the magnitude->slot length mapping data structure
    upper_mags = tuple(sorted(mag_mapping.keys()))

    for upper_mag in upper_mags:
        if mag < upper_mag:
            return mag_mapping[upper_mag]

    raise MagRangeError("Target magnitude outside bins")


def estimate_exptime(rate, pixscale=0.304, roundtime=10.0):
    """Gives the estimated exposure time (in seconds) for the given rate and
    pixelscale"""

    exptime = (60.0 / rate / pixscale)*1.0
    round_exptime = max(int(exptime/roundtime)*roundtime, 1.0)
    return round_exptime, exptime


def determine_exptime(speed, pixel_scale, max_exp_time=300.0):
    (round_exptime, full_exptime) = estimate_exptime(speed, pixel_scale, 5.0)

    if round_exptime > max_exp_time:
        logger.debug("Capping exposure time at %.1f seconds (Was %1.f seconds)" % \
            (round_exptime, max_exp_time))
        round_exptime = full_exptime = max_exp_time
    if round_exptime < 10.0 :
        # If under 10 seconds, re-round to nearest half second
        (round_exptime, full_exptime) = estimate_exptime(speed, pixel_scale, 0.5)
    logger.debug("Estimated exptime=%.1f seconds (%.1f)" % (round_exptime , full_exptime))

    return round_exptime


def determine_exp_time_count(speed, site_code, slot_length_in_mins, mag, filter_pattern):
    exp_time = None
    exp_count = None
    min_exp_count = 4

    (chk_site_code, setup_overhead, exp_overhead, pixel_scale, ccd_fov, site_max_exp_time, alt_limit) = get_sitecam_params(site_code)

    slot_length = slot_length_in_mins * 60.0

    # Set maximum exposure time to value that will achieve approximately S/N = 100 for objects fainter than 18 in V,R,I,gp,rp,ip.
    # This allows for LC with reasonable cadence for bright, slow moving objects.
    try:
        max_exp_time = min((determine_slot_length(mag, site_code)*60.) / min_exp_count, site_max_exp_time)
    except MagRangeError:
        max_exp_time = site_max_exp_time
    # pretify max exposure time to nearest 5 seconds

    max_exp_time = ceil(max_exp_time/5)*5

    exp_time = determine_exptime(speed, pixel_scale, max_exp_time)

    # Make first estimate for exposure count ignoring molecule creation
    exp_count = int((slot_length - setup_overhead)/(exp_time + exp_overhead))
    # Reduce exposure count by number of exposures necessary to accomidate molecule overhead
    mol_overhead = molecule_overhead(build_filter_blocks(filter_pattern, exp_count))
    exp_count = int(ceil(exp_count * (1.0-(mol_overhead / ((( exp_time + exp_overhead ) * exp_count) + mol_overhead)))))
    # Safety while loop for edge cases
    while setup_overhead + molecule_overhead(build_filter_blocks(filter_pattern, exp_count)) + (exp_overhead * float(exp_count)) + exp_time * float(exp_count) > slot_length:
        exp_count -= 1

    if exp_count < min_exp_count:
        exp_count = min_exp_count
        exp_time = (slot_length - setup_overhead - molecule_overhead(build_filter_blocks(filter_pattern, min_exp_count)) - (exp_overhead * float(exp_count))) / exp_count
        logger.debug("Reducing exposure time to %.1f secs to allow %d exposures in group" % ( exp_time, exp_count))
    logger.debug("Slot length of %.1f mins (%.1f secs) allows %d x %.1f second exposures" %
        ( slot_length/60.0, slot_length, exp_count, exp_time))
    if exp_time is None or exp_time <= 0.0 or exp_count < 1:
        logger.debug("Invalid exposure count")
        exp_time = None
        exp_count = None

    return exp_time, exp_count


def determine_spectro_slot_length(exp_time, calibs, exp_count=1):
    """Determine the length of time that a planned spectroscopic observation will take.
    This is based on the <exp_time> and no. of spectrum exposures [exp_count] (defaults
    to 1) and also on the value of <calibs>, which can be one of ('none', before',
    'after' or 'both') depending on whether calibrations (arcs and lamp flats) are not
    wanted, wanted either before or after the spectrum, or both before and after.
    Values and formulae come from Valhalla and values are encoded in
    get_sitecam_params(). Currently only FLOYDS is supported and no distinction is
    made between FTN and FTS.
    The estimated time, in seconds, is returned."""

    site_code = 'F65-FLOYDS'
    slot_length = None

    (chk_site_code, overheads, exp_overhead, pixel_scale, ccd_fov, max_exp_time, alt_limit) = get_sitecam_params(site_code)

    num_molecules = 1
    calibs = calibs.lower()
    if calibs == 'before' or calibs == 'after':
        num_molecules = 3
    elif calibs == 'both':
        num_molecules = 5

    if type(overheads) == dict and exp_overhead > -1:
        slot_length = (exp_time + exp_overhead) * float(exp_count)
        if calibs != 'none':
            # If we have calibration molecules, add their time and readout to the total
            slot_length += float(num_molecules-1)*(overheads['calib_exposure_time'] + exp_overhead)
        slot_length += num_molecules * (overheads.get('config_change_time', 0.0) + overheads.get('per_molecule_time', 0.0))
        slot_length += overheads.get('acquire_exposure_time', 0.0) + overheads.get('acquire_processing_time', 0.0)
        slot_length += overheads.get('front_padding', 0.0)
        slot_length = ceil(slot_length)
    return slot_length


def molecule_overhead(filter_blocks):
    single_mol_overhead = cfg.molecule_overhead['filter_change'] + cfg.molecule_overhead['per_molecule_time']
    molecule_setup_overhead = single_mol_overhead * len(filter_blocks)
    return molecule_setup_overhead


def build_filter_blocks(filter_pattern, exp_count):
    """Take in filter pattern string, export list of [filter, # of exposures in filter] """
    filter_bits = filter_pattern.split(',')
    filter_bits = list(filter(None, filter_bits))
    filter_list = []
    filter_blocks = []
    while exp_count > 0:
        filter_list += filter_bits[:exp_count]
        exp_count -= len(filter_bits)
    for f, m in groupby(filter_list):
        filter_blocks.append(list(m))
    if len(filter_blocks) == 0:
        filter_blocks = [filter_bits]
    return [[block[0], len(block)] for block in filter_blocks]
    # return filter_blocks


def compute_score(obj_alt, moon_alt, moon_sep, alt_limit=25.0):
    """Simple noddy scoring calculation for choosing best slot"""

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


def comp_sep(ra_cand_deg, dec_cand_deg, ra_ephem_rad, dec_ephem_rad):
    """Wrapper around SLALIB's sla_dsep to compute the separation between a
    detected position specified by (ra_cand_deg, dec_cand_deg; in DEGREES) with
    an ephemeris position (ra_ephem_rad, dec_ephem_rad; in RADIANS).
    The computed separation is returned in arcseconds"""

    sep = S.sla_dsep(radians(ra_cand_deg), radians(dec_cand_deg), ra_ephem_rad, dec_ephem_rad)
    sep = degrees(sep)*3600.0
    return sep


def get_sitepos(site_code, dbg=False):
    """Returns site name, geodetic longitude (East +ve), latitude (both in radians)
    and altitude (meters) for passed sitecode. This can be either a SLALIB site
    name or a MPC sitecode (FTN, FTS and SQA currently defined).
    Be *REALLY* careful over longitude sign conventions..."""

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
        (site_long, status) = S.sla_daf2r(149, 4., 13.0)
        site_hgt = 1111.8
        site_name = 'Siding Spring-Faulkes Telescope South (FTS)'
    elif site_code == 'SQA' or site_code == 'G51':
        (site_lat, status)  =  S.sla_daf2r(34, 41, 29.23)
        (site_long, status) =  S.sla_daf2r(120, 2., 32.0)
        site_long = -site_long
        site_hgt = 328.0
        site_name = 'Sedgwick Observatory (SQA)'
    elif site_code == 'ELP-DOMA' or site_code == 'V37':
        (site_lat, status)  =  S.sla_daf2r(30, 40, 47.53)
        (site_long, status) =  S.sla_daf2r(104, 0., 54.63)
        site_long = -site_long
        site_hgt = 2010.0
        site_name = 'LCO Node at McDonald Observatory (ELP)'
    elif site_code == 'ELP-AQWA-0M4A' or site_code == 'V38':
        (site_lat, status)  =  S.sla_daf2r(30, 40, 48.15)
        (site_long, status) =  S.sla_daf2r(104, 0., 54.24)
        site_long = -site_long
        site_hgt = 2027.0
        site_name = 'LCO Node at McDonald Observatory (ELP)'
    elif site_code == 'BPL':
        (site_lat, status)  =  S.sla_daf2r(34, 25, 57)
        (site_long, status) =  S.sla_daf2r(119, 51, 46)
        site_long = -site_long
        site_hgt = 7.0
        site_name = 'LCO Back Parking Lot Node (BPL)'
    elif site_code == 'LSC-DOMA-1M0A' or site_code == 'W85':
        # Latitude, longitude from Eric Mamajek (astro-ph: 1210.1616) Table 6. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(30, 10, 2.58)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 17.24)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2201.0
        site_name = 'LCO LSC Node 1m0 Dome A at Cerro Tololo'
    elif site_code == 'LSC-DOMB-1M0A' or site_code == 'W86':
        # Latitude, longitude from Eric Mamajek (astro-ph: 1210.1616) Table 6. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(30, 10, 2.39)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 16.78)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2201.0
        site_name = 'LCO LSC Node 1m0 Dome B at Cerro Tololo'
    elif site_code == 'LSC-DOMC-1M0A' or site_code == 'W87':
        # Latitude, longitude from Eric Mamajek (astro-ph: 1210.1616) Table 6. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(30, 10, 2.81)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 16.85)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2201.0
        site_name = 'LCO LSC Node 1m0 Dome C at Cerro Tololo'
    elif site_code == 'LSC-AQWA-0M4A' or site_code == 'W89':
        # Latitude, longitude from somewhere
        (site_lat, status)  =  S.sla_daf2r(30, 10, 3.79)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 16.88)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2202.5
        site_name = 'LCO LSC Node 0m4a Aqawan A at Cerro Tololo'
    elif site_code == 'LSC-AQWB-0M4A' or site_code == 'W79':
        # Latitude, longitude from Nikolaus/Google Earth
        (site_lat, status)  =  S.sla_daf2r(30, 10, 3.56)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(70, 48, 16.74)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2202.5
        site_name = 'LCO LSC Node 0m4a Aqawan A at Cerro Tololo'
    elif site_code == 'CPT-DOMA-1M0A' or site_code == 'K91':
        # Latitude, longitude from site GPS co-ords plus offsets from site plan. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(32, 22, 50.0)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(20, 48, 36.65)
        site_hgt = 1807.0
        site_name = 'LCO CPT Node 1m0 Dome A at Sutherland'
    elif site_code == 'CPT-DOMB-1M0A' or site_code == 'K92':
        # Latitude, longitude from site GPS co-ords plus offsets from site plan. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(32, 22, 50.0)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(20, 48, 36.13)
        site_hgt = 1807.0
        site_name = 'LCO CPT Node 1m0 Dome B at Sutherland'
    elif site_code == 'CPT-DOMC-1M0A' or site_code == 'K93':
        # Latitude, longitude from site GPS co-ords plus offsets from site plan. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(32, 22, 50.38)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(20, 48, 36.39)
        site_hgt = 1807.0
        site_name = 'LCO CPT Node 1m0 Dome C at Sutherland'
    elif site_code == 'COJ-DOMA-1M0A' or site_code == 'Q63':
        # Latitude, longitude from Google Earth guesswork. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(31, 16, 22.56)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(149, 4., 14.33)
        site_hgt = 1168.0
        site_name = 'LCO COJ Node 1m0 Dome A at Siding Spring'
    elif site_code == 'COJ-DOMB-1M0A' or site_code == 'Q64':
        # Latitude, longitude from Google Earth guesswork. Height
        # corrected by +3m for telescope height from Vince.
        (site_lat, status)  =  S.sla_daf2r(31, 16, 22.89)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(149, 4., 14.75)
        site_hgt = 1168.0
        site_name = 'LCO COJ Node 1m0 Dome B at Siding Spring'
    elif site_code == 'TFN-AQWA-0M4A' or site_code == 'Z21':
        # Latitude, longitude from Todd B./Google Earth
        (site_lat, status)  =  S.sla_daf2r(28, 18, 1.11)
        (site_long, status) =  S.sla_daf2r(16, 30, 42.13)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2390.0
        site_name = 'LCO TFN Node 0m4a Aqawan A at Tenerife'
    elif site_code == 'TFN-AQWA-0M4B' or site_code == 'Z17':
        # Latitude, longitude from Todd B./Google Earth
        (site_lat, status)  =  S.sla_daf2r(28, 18, 1.11)
        (site_long, status) =  S.sla_daf2r(16, 30, 42.21)
        site_long = -site_long # West of Greenwich !
        site_hgt = 2390.0
        site_name = 'LCO TFN Node 0m4b Aqawan A at Tenerife'
    elif site_code == 'OGG-CLMA-0M4B' or site_code == 'T04':
        # Latitude, longitude from Google Earth, SW corner of clamshell, probably wrong
        (site_lat, status)  =  S.sla_daf2r(20, 42, 25.1)
        (site_long, status) =  S.sla_daf2r(156, 15, 27.11)
        site_long = -site_long # West of Greenwich !
        site_hgt = 3037.0
        site_name = 'LCO OGG Node 0m4b at Maui'
    elif site_code == 'OGG-CLMA-0M4C' or site_code == 'T03':
        # Latitude, longitude from Google Earth, SW corner of clamshell, probably wrong
        (site_lat, status)  =  S.sla_daf2r(20, 42, 25.1)
        (site_long, status) =  S.sla_daf2r(156, 15, 27.12)
        site_long = -site_long # West of Greenwich !
        site_hgt = 3037.0
        site_name = 'LCO OGG Node 0m4c at Maui'
    elif site_code == 'COJ-CLMA-0M4A' or site_code == 'Q58':
        # Latitude, longitude from Google Earth, SE corner of clamshell, probably wrong
        (site_lat, status)  =  S.sla_daf2r(31, 16, 22.38)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(149, 4., 15.05)
        site_hgt = 1191.0
        site_name = 'LCO COJ Node 0m4a at Siding Spring'
    elif site_code == 'COJ-CLMA-0M4B' or site_code == 'Q59':
        # Latitude, longitude from Google Earth, SW corner of clamshell, probably wrong
        (site_lat, status)  =  S.sla_daf2r(31, 16, 22.48)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(149, 4., 14.91)
        site_hgt = 1191.0
        site_name = 'LCO COJ Node 0m4b at Siding Spring'
    elif site_code == 'CPT-AQWA-0M4A' or site_code == 'L09':
        # Latitude, longitude from Nikolaus/Google Earth
        (site_lat, status)  =  S.sla_daf2r(32, 22, 50.25)
        site_lat = -site_lat   # Southern hemisphere !
        (site_long, status) =  S.sla_daf2r(20, 48, 35.54)
        site_hgt = 1804.0
        site_name = 'LCO CPT Node 0m4a Aqawan A at Sutherland'
    elif site_code == '500':
        site_lat = 0.0
        site_long = 0.0
        site_hgt = 0.0
        site_name = 'Geocenter'
    else:
        # Obtain latitude, longitude of the observing site.
        # Reverse longitude to get the more normal East-positive convention
        (site_num, site_name, site_long, site_lat, site_hgt) = S.sla_obs(0, site_code)
        site_name = site_name.rstrip().decode()
        site_long = -site_long

    logger.debug("Site name, lat/long/height=%s %f %f %.1f" % (site_name, site_long, site_lat, site_hgt))
    return site_name, site_long, site_lat, site_hgt


def moon_ra_dec(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg=False):
    """Calculate the topocentric (from an observing location) apparent RA, Dec
    of the Moon. <date> is a UTC datetime, obsvr_long, obsvr_lat are geodetic
    North/East +ve observatory positions (in radians) and obsvr_hgt is the height
    (in meters).
    Returns a (RA, Dec, diameter) (in radians) tuple."""

    body = 3 # The Moon...

    mjd_tdb = datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg)

# Compute Moon's apparent RA, Dec, diameter (all in radians)
    (moon_ra, moon_dec, diam) = S.sla_rdplan(mjd_tdb, body, obsvr_long, obsvr_lat)

    logger.debug("Moon RA, Dec, diam=%s %s %s" % (moon_ra, moon_dec, diam))
    return moon_ra, moon_dec, diam


def atmos_params(airless):
    """Atmospheric parameters either airless or average"""
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

    return temp_k, pres_mb, rel_humid, wavel, tlr


def moon_alt_az(date, moon_app_ra, moon_app_dec, obsvr_long, obsvr_lat,
    obsvr_hgt, dbg=False):
    """Calculate Moon's Azimuth, Altitude (returned in radians).
    No refraction or polar motion is assumed."""

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
    (obs_az, obs_zd, obs_ha, obs_dec, obs_ra) = S.sla_aop(moon_app_ra, moon_app_dec,
        mjd_utc, dut, obsvr_long, obsvr_lat, obsvr_hgt, xp, yp,
        temp_k, pres_mb, rel_humid, wavel, tlr)

# Normalize azimuth into range 0..2PI
    obs_az = S.sla_ranorm(obs_az)
# Convert zenith distance to altitude (assumes no depression of the horizon
# due to observers' elevation above sea level)

    obs_alt = (pi/2.0)-obs_zd
    logger.debug("Az, ZD, Alt=%f %f %f" % (obs_az, obs_zd, obs_alt))
    return obs_az, obs_alt


def moonphase(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg=False):

    mjd_tdb = datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg)
    (moon_ra, moon_dec, moon_diam) = S.sla_rdplan(mjd_tdb, 3, obsvr_long, obsvr_lat)

    (sun_ra, sun_dec, sun_diam) = S.sla_rdplan (mjd_tdb, 0, obsvr_long, obsvr_lat)

    cosphi = ( sin(sun_dec) * sin(moon_dec) + cos(sun_dec) \
        * cos(moon_dec) * cos(sun_ra - moon_ra) )
    logger.debug("cos(phi)=%s" % cosphi)

# Full formula for phase angle, i. Requires r (Earth-Sun distance) and del(ta) (the
# Earth-Moon distance) neither of which we have with our methods. However Meeus
# _Astronomical Algorithms_ p 345 reckons we can "put cos(i) = -cos(phi) and k (the
# Moon phase) will never be in error by more than 0.0014"
#    i = atan2( r * sin(phi), del - r * cos(phi) )

    cosi = -cosphi
    logger.debug("cos(i)=%s" % cosi)
    mphase = (1.0 + cosi) / 2.0

    return mphase


def compute_hourangle(date, obsvr_long, obsvr_lat, obsvr_hgt, mean_ra, mean_dec, dbg=False):

    mjd_tdb = datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, False)
    # Compute MJD_UTC
    mjd_utc = datetime2mjd_utc(date)

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
    """Format an (RA, Dec) pair (in radians) into a tuple of strings, with
    configurable seperator (defaults to <space>).
    There is no sign produced on the RA quantity unless ra_radians and dec_radians
    are equal."""

    ra_format =  "%s%02.2d%c%02.2d%c%02.2d.%02.2d"
    dec_format = "%s%02.2d%c%02.2d%c%02.2d.%d"

    (rsign, ra ) = S.sla_dr2tf(2, ra_radians)
    (dsign, dec) = S.sla_dr2af(1, dec_radians)

    # Remove the byte bits on the signs imposed by S.sla
    rsign = rsign.decode()
    dsign = dsign.decode()

    if rsign == '+' and ra_radians != dec_radians:
        rsign = ''
    ra_str = ra_format % ( rsign, ra[0], seperator, ra[1], seperator, ra[2],  ra[3] )
    dec_str = dec_format % ( dsign, dec[0], seperator, dec[1], seperator, dec[2], dec[3] )

    return ra_str, dec_str


def get_mountlimits(site_code_or_name):
    """Returns the negative, positive and altitude mount limits (in degrees)
    for the LCOGT telescopes specified by <site_code_or_name>.

    <site_code_or_name> can either be a MPC site code e.g. 'V37' (=ELP 1m),
    or by desigination e.g. 'OGG-CLMA-2M0A' (=FTN)"""

    site = site_code_or_name.upper()
    ha_pos_limit = 12.0 * 15.0
    ha_neg_limit = -12.0 * 15.0
    alt_limit = 25.0

    if '-1M0A' in site or site in ['V37', 'W85', 'W86', 'W87', 'K91', 'K92', 'K93', 'Q63', 'Q64']:
        ha_pos_limit = 4.5 * 15.0
        ha_neg_limit = -4.5 * 15.0
        alt_limit = 30.0
    elif '-AQWA' in site or '-AQWB' in site or 'CLMA-0M4' in site or site in ['Z17', 'Z21', 'Q58', 'Q59', 'T03', 'T04', 'W89', 'W79', 'V38', 'L09']:
        ha_pos_limit = 4.46 * 15.0
        ha_neg_limit = -4.5 * 15.0
        alt_limit = 15.0

    return ha_neg_limit, ha_pos_limit, alt_limit


def LCOGT_site_codes():
    """Return a list of LCOGT site codes"""

    valid_site_codes = cfg.valid_site_codes

    return valid_site_codes.values()


def LCOGT_domes_to_site_codes(siteid, encid, telid):
    """Returns the mapped value of LCOGT Site-Enclosure-Telescope to site code"""

    valid_site_codes = cfg.valid_site_codes

    instance = "%s-%s-%s" % (siteid.strip().upper(), encid.strip().upper(), telid.strip().upper())
    return valid_site_codes.get(instance, 'XXX')


def MPC_site_code_to_domes(site):
    """ Returns the mapped value of the MPC site code to LCO Site, Eclosure, and telescope"""

    key = cfg.valid_telescope_codes.get(site.upper(), '--')

    key = key.split('-')
    siteid = key[0].lower()
    encid = key[1].lower()
    telid = key[2].lower()

    return siteid, encid, telid


def get_sitecam_params(site):
    """Translates <site> (e.g. 'FTN') to MPC site code, pixel scale, maximum
    exposure time, setup and exposure overheads.
    site_code is set to 'XXX' and the others are set to -1 in the event of an
    unrecognized site."""

    valid_site_codes = LCOGT_site_codes()
    valid_point4m_codes = ['Z17', 'Z21', 'W89', 'W79', 'T03', 'T04', 'Q58', 'Q59', 'V38', 'L09']

    site = site.upper()
    if site == 'FTN' or 'OGG-CLMA-2M0' in site or site == 'F65':
        site_code = 'F65'
        setup_overhead = cfg.tel_overhead['twom_setup_overhead']
        exp_overhead = cfg.inst_overhead['twom_exp_overhead']
        pixel_scale = cfg.tel_field['twom_pixscale']
        fov = arcmins_to_radians(cfg.tel_field['twom_fov'])
        max_exp_length = 300.0
        alt_limit = cfg.tel_alt['twom_alt_limit']
    elif site == 'FTS' or 'COJ-CLMA-2M0' in site or site == 'E10':
        site_code = 'E10'
        setup_overhead = cfg.tel_overhead['twom_setup_overhead']
        exp_overhead = cfg.inst_overhead['twom_exp_overhead']
        pixel_scale = cfg.tel_field['twom_pixscale']
        fov = arcmins_to_radians(cfg.tel_field['twom_fov'])
        max_exp_length = 300.0
        alt_limit = cfg.tel_alt['twom_alt_limit']
    elif site == 'F65-FLOYDS' or site == 'E10-FLOYDS':
        site_code = site[0:3]
        exp_overhead = cfg.inst_overhead['floyds_exp_overhead']
        pixel_scale = cfg.tel_field['twom_floyds_pixscale']
        fov = arcmins_to_radians(cfg.tel_field['twom_floyds_fov'])
        max_exp_length = 3600.0
        alt_limit = cfg.tel_alt['twom_alt_limit']
        setup_overhead = { 'front_padding' : cfg.tel_overhead['twom_setup_overhead'],
                           'config_change_time' : cfg.inst_overhead['floyds_config_change_overhead'],
                           'acquire_processing_time' : cfg.inst_overhead['floyds_acq_proc_overhead'],
                           'acquire_exposure_time': cfg.inst_overhead['floyds_acq_exp_time'],
                           'per_molecule_time' : cfg.molecule_overhead['per_molecule_time'],
                           'calib_exposure_time' : cfg.inst_overhead['floyds_calib_exp_time']
                         }
    elif site in valid_point4m_codes:
        site_code = site
        setup_overhead = cfg.tel_overhead['point4m_setup_overhead']
        exp_overhead = cfg.inst_overhead['point4m_exp_overhead']
        pixel_scale = cfg.tel_field['point4m_pixscale']
        fov = arcmins_to_radians(cfg.tel_field['point4m_fov'])
        max_exp_length = 300.0
        alt_limit = cfg.tel_alt['point4m_alt_limit']
    elif site in valid_site_codes:
        setup_overhead = cfg.tel_overhead['onem_setup_overhead']
        exp_overhead = cfg.inst_overhead['sinistro_exp_overhead']
        pixel_scale = cfg.tel_field['onem_sinistro_pixscale']
        fov = arcmins_to_radians(cfg.tel_field['onem_sinistro_fov'])
        max_exp_length = 300.0
        alt_limit = cfg.tel_alt['normal_alt_limit']
        site_code = site
    else:
        # Unrecognized site
        site_code = 'XXX'
        setup_overhead = exp_overhead = pixel_scale = fov = max_exp_length = alt_limit = -1

    return site_code, setup_overhead, exp_overhead, pixel_scale, fov, max_exp_length, alt_limit


def comp_FOM(orbelems, emp_line):
    """Computes a Figure of Merit (FOM) priority score that is used as a
    metric for ranking targets to follow-up.
    Currently, this prioritizes targets that have not been seen in a while,
    have a short arc, are big and bright, have a high "likely NEO" score,
    and will go directly overhead of our southern hemisphere sites.
    The 'not_seen'/'arc_length', 'emp_line[3]' (V_mag), and 'abs_mag'
    terms in the FOM computation are exponential (i.e., for brighter, larger,
    seen less recently, shorter arc targets, the FOM rises exponentially),
    whereas the 'score' and 'emp_line[6]' (south polar distance (SPD)) terms
    are gaussian, where the expected values are 100 and 60 deg, respectively.
    The 'score' term is weighted lower (multiplied by 0.5) than the others
    to avoid it dominating the priority ranking. The 'not_seen' and
    'arc_length' parameters are linked together such that targets with high
    'not_seen' values and low 'arc_length' values (those that haven't been
    seen in a while and have short arcs) are ranked higher than those with
    both values high (those that haven't been seen in a while and have longer
    arcs) or both values low (those that were seen recently and have short
    arcs).
    """
    FOM = None
    if 'U' in orbelems['source_type'] and orbelems['not_seen'] is not None and orbelems['arc_length'] is not None and orbelems['score'] is not None:
        try:
            if orbelems['arc_length'] < 0.01:
                orbelems['arc_length'] = 0.005
            FOM = (exp(orbelems['not_seen']/orbelems['arc_length'])-1.) + (exp(1./emp_line[3])-1.) + (0.5*exp((-0.5*(orbelems['score']-100.)**2)/10.)) + (exp(1./orbelems['abs_mag'])-1.) + (exp((-0.5*(emp_line[6]-60.)**2)/180.))
        except Exception as e:
            logger.error(e)
            logger.error(str(orbelems))
            logger.error(str(emp_line))
    return FOM


def determine_sites_to_schedule(sched_date=datetime.utcnow()):
    """Determines which sites should be attempted for scheduling based on the
    time of day.
    Returns a dictionary with keys of 'north' and 'south', each of which will
    have two keys of '0m4' and '1m0' which will contain a list of sites (or an
    empty list) that can be scheduled."""

    N_point4m_sites = N_onem_sites = S_point4m_sites = S_onem_sites = []

    if 17 <= sched_date.hour < 23:
        N_point4m_sites = ['Z21', 'Z17']
        N_onem_sites = ['V37', ]
        S_point4m_sites = ['L09', ]
        S_onem_sites = ['K93', 'K92', 'K91']
    elif sched_date.hour >= 23 or (0 <= sched_date.hour < 8):
        N_point4m_sites = ['T04', 'T03', 'V38']
        N_onem_sites = ['V37', ]
        S_point4m_sites = ['W89', 'W79']
        S_onem_sites = ['W87', 'W85']
    elif 8 <= sched_date.hour < 12:
        N_point4m_sites = ['T04', 'T03']
        N_onem_sites = [ ]
        S_point4m_sites = ['Q58', ]
        S_onem_sites = ['Q63', 'Q64']
    elif 12 <= sched_date.hour < 17:
        N_point4m_sites = [ ]
        N_onem_sites = [ ]
        S_point4m_sites = ['Q58', ]
        S_onem_sites = ['Q63', 'Q64']

    sites = {   'north' : { '0m4' : N_point4m_sites, '1m0' : N_onem_sites},
                'south' : { '0m4' : S_point4m_sites, '1m0' : S_onem_sites},
            }

    return sites


def monitor_long_term_scheduling(site_code, orbelems, utc_date=datetime.utcnow(), date_range=30, dark_and_up_time_limit=3.0, slot_length=20, ephem_step_size='5 m'):
    """Determine when it's best to observe Yarkovsky & radar/ARM
    targets in the future"""

    visible_dates = []
    emp_visible_dates = []
    dark_and_up_time_all = []
    max_alt_all = []
    delta_date = 0
    while delta_date <= date_range:

        dark_start, dark_end = determine_darkness_times(site_code, utc_date)
        emp = call_compute_ephem(orbelems, dark_start, dark_end, site_code, ephem_step_size, alt_limit=30)

        dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)

        if emp_dark_and_up != []:

            obj_mag = float(emp_dark_and_up[0][3])

            moon_alt_start = int(emp_dark_and_up[0][9])
            moon_alt_end = int(emp_dark_and_up[-1][9])
            moon_up = False
            if moon_alt_start >= 30 or moon_alt_end >= 30:
                moon_up = True

            moon_phase = float(emp_dark_and_up[0][7])

            score = int(emp_dark_and_up[0][10])

            max_alt = compute_max_altitude(emp_dark_and_up)

            if dark_and_up_time >= dark_and_up_time_limit and obj_mag <= 21.5 and moon_up is True and moon_phase <= 0.85 and score > 0:
                visible_dates.append(emp_dark_and_up[0][0][0:10])
                emp_visible_dates.append(emp_dark_and_up[0])
                dark_and_up_time_all.append(dark_and_up_time)
                max_alt_all.append(max_alt)
            elif dark_and_up_time >= dark_and_up_time_limit and obj_mag <= 21.5 and moon_up is False:
                visible_dates.append(emp_dark_and_up[0][0][0:10])
                emp_visible_dates.append(emp_dark_and_up[0])
                dark_and_up_time_all.append(dark_and_up_time)
                max_alt_all.append(max_alt)

        utc_date += timedelta(days=1)
        delta_date += 1

    return visible_dates, emp_visible_dates, dark_and_up_time_all, max_alt_all


def compute_dark_and_up_time(emp):
    """Computes the amount of time a target is up and the
    sky is dark from emp"""

    dark_and_up_time = None
    dark_and_up_time_start = None
    dark_and_up_time_end = None
    emp_dark_and_up = []
    start = None

    if emp != []:
        for line in emp:
            if 'Limits' not in line[11] and start is None:
                dark_and_up_time_start = datetime.strptime(line[0], '%Y %m %d %H:%M')
                dark_and_up_time_end = datetime.strptime(line[0], '%Y %m %d %H:%M')
                start = 1
                emp_dark_and_up.append(line)
            elif 'Limits' not in line[11]:
                dark_and_up_time_end = datetime.strptime(line[0], '%Y %m %d %H:%M')
                emp_dark_and_up.append(line)
        if dark_and_up_time_start is not None and dark_and_up_time_end is not None:
            dark_and_up_time = dark_and_up_time_end - dark_and_up_time_start
            dark_and_up_time = dark_and_up_time.seconds/3600.0  # in hrs

    return dark_and_up_time, emp_dark_and_up


def compute_max_altitude(emp_dark_and_up):
    """Computes the maximum altitude a target
    reaches on a given night"""

    max_alt = 0
    prev_max_alt = 0

    for line in emp_dark_and_up:
        alt = int(float(line[6]))
        if alt > prev_max_alt:
            max_alt = alt
        prev_max_alt = max_alt

    return max_alt


def compute_sidereal_ephem(ephem_time, elements, site_code):
    site_name, site_long, site_lat, site_hgt = get_sitepos(site_code)
    az_rad, alt_rad = moon_alt_az(ephem_time, radians(elements['ra']), radians(elements['dec']), site_long, site_lat, site_hgt, dbg=False)
    alt_deg = degrees(alt_rad)

    #               0   1   2   3       4           5       6       7
    emp_line = (ephem_time, radians(elements['ra']), radians(elements['dec']), elements['vmag'], 0, alt_deg, 0, 0)
    return emp_line


def get_visibility(body_elements, dark_start, dark_end, site_code, step_size='30 m', alt_limit=30):

    emp = call_compute_ephem(body_elements, dark_start, dark_end, site_code, step_size, alt_limit)
    dark_and_up_time, emp_dark_and_up = compute_dark_and_up_time(emp)
    max_alt = compute_max_altitude(emp_dark_and_up)

    return dark_and_up_time, max_alt
