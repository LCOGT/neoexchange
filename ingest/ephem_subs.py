from datetime import datetime, timedelta
import os 
import slalib as S
from math import sin, cos, tan, asin, acos, atan2, degrees, radians, pi, sqrt, fabs, exp, log10
from numpy import array, concatenate, zeros

# Local imports
from timesubs import datetime2mjd_utc, mjd_utc2mjd_tt, datetime2mjd_tdb, \
    ut1_minus_utc, round_datetime
from astsubs import mpc_8lineformat


def compute_phase_angle(r, delta, es_Rsq, dbg=False):
    '''Method to compute the phase angle (beta), trapping bad values'''
    # Compute phase angle, beta (Sun-Target-Earth angle)
    if dbg: print "r,r^2,delta,delta^2,es_Rsq=",r,r*r,delta,delta*delta,es_Rsq
    arg = (r*r+delta*delta-es_Rsq)/(2.0*r*delta)
    if dbg: print "arg=", arg

    if arg >= 1.0:
        beta = 0.0
    elif arg <= -1.0:
        beta = pi
    else:
        beta = acos(arg)

    if dbg: print
    if dbg: print "Phase angle, beta (deg)=", beta,beta*(1.0/d2r)
    return beta

def compute_ephem(d, orbelems, sitecode, dbg=True, perturb=True, display=True):


# Light travel time for 1 AU (in sec)
    tau = 499.004783806

# Compute MJD for UTC
    (mjd, status) = S.sla_cldj(d.year, d.month, d.day)
    (fday, status) = S.sla_dtf2d(d.hour, d.minute, d.second + (d.microsecond / 1e6))
    mjd_utc = mjd + fday

# Compute epoch of the elements as a MJD
    ericformat = False
    if orbelems.has_key('epoch'): ericformat = True
    if ericformat == False:
        (epoch_mjd, status) = S.sla_cldj(orbelems['Epoch'].year, orbelems['Epoch'].month, orbelems['Epoch'].day)
        (fday, status) = S.sla_dtf2d(orbelems['Epoch'].hour, orbelems['Epoch'].minute, orbelems['Epoch'].second)
        epoch_mjd = epoch_mjd + fday
        #epoch_mjd= 55501.0
        if status != 0:
            print 'Error in MJD conversion'
    else:
        epoch_mjd = orbelems['epoch']

    if dbg: print 'Element Epoch=', epoch_mjd
    if dbg: print 'MJD(UTC) =  ', mjd_utc
    if dbg: print ' JD(UTC) =', mjd_utc + 2400000.5

# UTC->TT offset
    tt_utc = S.sla_dtt(mjd_utc)
    if dbg: print 'TT-UTC(s)=', tt_utc

# Correct MJD to MJD(TT)
    mjd_tt = mjd_utc + (tt_utc/86400.0)
    if dbg: print 'MJD(TT)  =  %.15f' % (mjd_tt)

# Compute UT1-UTC

    dut = ut1_minus_utc(mjd_utc)
    if dbg: print "UT1-UTC  =", dut

# Obtain precession-nutation 3x3 rotation matrix
# Should really be TDB but "TT will do" says The Wallace...

    rmat = S.sla_prenut(2000.0, mjd_tt)

    if dbg: print rmat

# Obtain latitude, longitude of the observing site.
# Reverse longitude to get the more normal East-positive convention
#    (site_num, site_name, site_long, site_lat, site_hgt) = S.sla_obs(0, 'SAAO74')
#    site_long = -site_long
    (site_name, site_long, site_lat, site_hgt) = get_sitepos(sitecode)
    if dbg: print
    if dbg: print sitecode, site_name, site_long, site_lat, site_hgt

# Compute local apparent sidereal time
# Do GMST first which takes UT1 and then add East longitiude and the equation of the equinoxes
# (which takes TDB; but we use TT here)
#
    gmst = S.sla_gmst(mjd_utc+(dut/86400.0))
    stl = gmst + site_long + S.sla_eqeqx(mjd_tt)
    if dbg:
        print 'GMST, LAST, EQEQX, GAST, long=', gmst, stl, S.sla_eqeqx(mjd_tt), gmst+S.sla_eqeqx(mjd_tt), site_long
    pvobs = S.sla_pvobs(site_lat, site_hgt, stl)

    if site_name == '?':
        print "WARN: No site co-ordinates found, computing for geocenter"
        pvobs = pvobs * 0.0

    if dbg: print "PVobs(orig)=", pvobs[0:3], "\n           ", pvobs[3:6]*86400.0

# Apply transpose of precession/nutation matrix to pv vector to go from
# true equator and equinox of date to J2000.0 mean equator and equinox (to
# match the reference system of sla_epv)
#
    pos_new = S.sla_dimxv(rmat, pvobs[0:3])
    vel_new = S.sla_dimxv(rmat, pvobs[3:6])
    pvobs_new = concatenate([pos_new, vel_new])
    if dbg: print "PVobs(new)=", pvobs_new[0:3], "\n           ", pvobs_new[3:6]*86400.0

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
#    ephem = Ephemeris(423) #  Ephemeris(430)
#    (e_pos_hel, e_vel_hel, e_pos_bar, e_vel_bar ) = ephem.epv(mjd_tt)
    e_vel_hel = e_vel_hel/86400.0

    if dbg: print
    if dbg: print "Sun->Earth [X, Y, Z]=", e_pos_hel
    if dbg: print "Sun->Earth [X, Y, Z]= %20.15E %20.15E %20.15E" % (e_pos_hel[0], e_pos_hel[1], e_pos_hel[2])
    if dbg: print "Sun->Earth [Xdot, Ydot, Zdot]=", e_vel_hel
    if dbg: print "Sun->Earth [Xdot, Ydot, Zdot]= %20.15E %20.15E %20.15E" % (e_vel_hel[0]*86400.0, e_vel_hel[1]*86400.0, e_vel_hel[2]*86400.0)

# Add topocentric offset in position and velocity
    e_pos_hel = e_pos_hel + pvobs_new[0:3]
    e_vel_hel = e_vel_hel + pvobs_new[3:6]
    if dbg: print
    if dbg: print "Sun->Obsvr [X, Y, Z]=", e_pos_hel
    if dbg: print "Sun->Obsvr [Xdot, Ydot, Zdot]=", e_vel_hel

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
        if perturb == True:
            if comet == True:
                (p_epoch_mjd, p_orbelems['Inc'], p_orbelems['LongNode'], p_orbelems['ArgPeri'],
                  p_orbelems['SemiAxisOrQ'], p_orbelems['Ecc'], p_orbelems['MeanAnom'], j) = S.sla_pertel( 3, epoch_mjd,
                            mjd_tt, epoch_mjd, orbelems['inclination'].in_radians(), orbelems['long_node'].in_radians(),
                            orbelems['arg_perihelion'].in_radians(), orbelems['perihdist'], orbelems['eccentricity'],
                            0.0)
                p_epoch_mjd = orbelems['epochofperih']
            else:
                (p_epoch_mjd, p_orbelems['Inc'], p_orbelems['LongNode'], p_orbelems['ArgPeri'],
                  p_orbelems['SemiAxis'], p_orbelems['Ecc'], p_orbelems['MeanAnom'], j) = S.sla_pertel( 2, epoch_mjd,
                            mjd_tt, epoch_mjd, orbelems['inclination'].in_radians(), orbelems['long_node'].in_radians(),
                            orbelems['arg_perihelion'].in_radians(), orbelems['semi_axis'], orbelems['eccentricity'],
                            orbelems['mean_anomaly'].in_radians())
        else:
            if dbg: print "Not perturbing"
            p_epoch_mjd = epoch_mjd
            j = 0
    else:
        p_orbelems = orbelems.copy()
        if perturb == True:
            (p_epoch_mjd, p_orbelems['Inc'], p_orbelems['LongNode'], p_orbelems['ArgPeri'],
              p_orbelems['SemiAxis'], p_orbelems['Ecc'], p_orbelems['MeanAnom'], j) = S.sla_pertel( 2, epoch_mjd, mjd_tt, epoch_mjd, radians(orbelems['Inc']), radians(orbelems['LongNode']),
                        radians(orbelems['ArgPeri']), orbelems['SemiAxis'], orbelems['Ecc'],
                        radians(orbelems['MeanAnom']))
        else:
            p_epoch_mjd = epoch_mjd
            j = 0

    if j != 0:
        print "Perturbing error=", j


    r3 = -100.
    delta = 0.0
    ltt = 0.0
    pos = zeros(3)
    vel = zeros(3)
    #rel_pos= [0.0, 0.0, 0.0]

    while ( fabs(delta - r3) > .01):
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


        if dbg: print "Sun->Asteroid [x,y,z]=", pv[0:3], status
        if dbg: print "Sun->Asteroid [xdot,ydot,zdot]=", pv[3:6], status


        #for earth_vec, ast_vec, rel_pos in zip(e_pos_hel, a_pos, pos):
        #    rel_pos = -earth_vec + ast_vec

        for i, e_pos in enumerate(e_pos_hel):
            pos[i] = pv[i] - e_pos

        for i, e_vel in enumerate(e_vel_hel):
            vel[i] = pv[i+3] - e_vel

        if dbg: print "Earth->Asteroid [x,y,z]=", pos
        if dbg: print "Earth->Asteroid [xdot,ydot,zdot]=", vel

# geometric distance, delta (AU)
        delta = sqrt(pos[0]*pos[0] + pos[1]*pos[1] + pos[2]*pos[2])
        if dbg: print
        if dbg: print "Geometric distance, delta (AU)=", delta

# Light travel time to asteroid
        ltt = tau * delta
        if dbg: print "Light travel time (sec, min, days)=", ltt, ltt/60.0, ltt/86400.0

# Correct position for planetary aberration
    for i, a_pos in enumerate(pos):
        pos[i] = a_pos - (ltt * vel[i])

    if dbg: print
    if dbg: print "Earth->Asteroid [x,y,z]=", pos
    if dbg: print "Earth->Asteroid [x,y,z]= %20.15E %20.15E %20.15E" % (pos[0], pos[1], pos[2])
    if dbg: print "Earth->Asteroid [xdot,ydot,zdot]=", vel*86400.0
    (ra, dec) = S.sla_dcc2s(pos)
    (rsign, ra_geo_deg) = S.sla_dr2tf(2,ra)
    (dsign, dec_geo_deg) = S.sla_dr2af(1,dec)

# Convert Cartesian to RA, Dec
    (ra, dec) = S.sla_dcc2s(pos)
    if dbg: print "ra,dec=", ra, dec
    ra = S.sla_dranrm(ra)
    if dbg: print "ra,dec=", ra, dec
    (rsign, ra_geo_deg) = S.sla_dr2tf(2,ra)
    (dsign, dec_geo_deg) = S.sla_dr2af(1,dec)

# Compute topocentric apparent ra,dec of asteroid
#    (ra_app, dec_app, r, status) = S.sla_plante(mjd_tt, site_long, site_lat, 2,
#                    p_epoch_mjd,
#                    p_orbelems['Inc'], p_orbelems['LongNode'],
#                    p_orbelems['ArgPeri'], p_orbelems['SemiAxis'], p_orbelems['Ecc'],
#                    p_orbelems['MeanAnom'], 0.0)

    #print "Topocentric apparent (rad)=", ra_app, dec_app
# Convert radians to Hours, Min, Sec and Degrees, Arcmin, Arcsec
#    (rsign,  ra_app_deg) = S.sla_dr2tf(2,ra_app)
#    (dsign, dec_app_deg) = S.sla_dr2af(1,dec_app)

#    print "Topocentric apparent : %s%02.2dh %02.2dm %02.2d.%02.2ds %s%02.2dd %02.2d\' %02.2d.%d\"" % ( rsign,
#        ra_app_deg[0], ra_app_deg[1], ra_app_deg[2], ra_app_deg[3],
#        dsign, dec_app_deg[0], dec_app_deg[1], dec_app_deg[2], dec_app_deg[3] )

# Compute r, the Sun-Target distance. Correct for light travel time first
    cposx = pv[0] - (ltt * pv[3])
    cposy = pv[1] - (ltt * pv[4])
    cposz = pv[2] - (ltt * pv[5])
    r = sqrt(cposx*cposx + cposy*cposy + cposz*cposz)

    if dbg: print "r (AU) =", r

# Compute R, the Earth-Sun distance. (Only actually need R^2 for the mag. formula)
    es_Rsq = (e_pos_hel[0]*e_pos_hel[0] + e_pos_hel[1]*e_pos_hel[1] + e_pos_hel[2]*e_pos_hel[2])

    if dbg: print "R (AU) =", sqrt(es_Rsq)
    if dbg: print "delta (AU)=", delta

# Compute sky motion

    sky_vel = compute_relative_velocity_vectors(e_pos_hel, e_vel_hel, pos, vel, delta, dbg)
    if dbg: print "vel1, vel2, r= %15.10lf %15.10lf %15.10lf" % (sky_vel[1],  sky_vel[2] , delta)
    if dbg: print "vel1, vel2, r= %15.10e %15.10e %15.10lf\n" % (sky_vel[1],  sky_vel[2] , delta)

    total_motion, sky_pa, ra_motion, dec_motion  = compute_sky_motion(sky_vel, delta, dbg)

    if comet == True:
    # Calculate magnitude of comet
    # Here 'H' is the absolute magnitude, 'kappa' the slope parameter defined in Meeus
    # _Astronomical Algorithms_ p. 231, is equal to 2.5 times the 'G' read from the
        mag = orbelems['H'] + 5.0 * log10(delta) + 2.5 * orbelems['G'] * log10(r)

    else:
    # Compute phase angle, beta (Sun-Target-Earth angle)
        beta = compute_phase_angle(r, delta, es_Rsq)

        phi1 = exp(-3.33 * (tan(beta/2.0))**0.63)
        phi2 = exp(-1.87 * (tan(beta/2.0))**1.22)

    #    if dbg: print "Phi1, phi2=", phi1,phi2

    # Calculate magnitude of object
        mag = orbelems['H'] + 5.0 * log10(r * delta) - \
            (2.5 * log10((1.0 - orbelems['G'])*phi1 + orbelems['G']*phi2))

    az_rad,alt_rad = moon_alt_az(d, ra, dec, site_long, site_lat, site_hgt)
    airmass = S.sla_airmas((pi/2.0)-alt_rad)
    alt_deg = degrees(alt_rad)

#    if display: print "  %02.2dh %02.2dm %02.2d.%02.2ds %s%02.2dd %02.2d\' %02.2d.%01.1d\"  V=%.1f  %5.2f %.1f % 7.3f %8.4f" % ( ra_geo_deg[0],
    if display: print "  %02.2d %02.2d %02.2d.%02.2d %s%02.2d %02.2d %02.2d.%01.1d  V=%.1f  %5.2f %.1f % 7.3f %8.4f" % ( ra_geo_deg[0],
        ra_geo_deg[1], ra_geo_deg[2], ra_geo_deg[3],
        dsign, dec_geo_deg[0], dec_geo_deg[1], dec_geo_deg[2], dec_geo_deg[3],
        mag, total_motion, sky_pa, alt_deg, airmass )

    emp_line = (d, ra, dec, mag, total_motion, alt_deg)

    return emp_line # (ra,dec)


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
    if dbg: print "   obj_vel= %15.10f %15.10f %15.10f" % ( obj_vel[0], obj_vel[1], obj_vel[2])
    if dbg: print "   obs_vel= %15.10f %15.10f %15.10f" % ( obs_vel_hel[0], obs_vel_hel[1], obs_vel_hel[2])
    if dbg: print "   obs_vel= %15.10e %15.10e %15.10e" % ( obs_vel_hel[0], obs_vel_hel[1], obs_vel_hel[2])

    if dbg: print " j2000_vel= %15.10e %15.10e %15.10e" % ( j2000_vel[0], j2000_vel[1], j2000_vel[2])
    if dbg: print "matrix_vel= %15.10f %15.10f %15.10f" % ( matrix[0], matrix[1], matrix[2] )

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
    if dbg: print  "RA motion, Dec motion, PA=%10.7f %10.7f %6.1f" % (ra_motion, dec_motion, sky_pa )

    total_motion = sqrt(ra_motion * ra_motion + dec_motion * dec_motion)
    if dbg: print  "Total motion=%10.7f" % (total_motion)

    return (total_motion, sky_pa, ra_motion, dec_motion)

def call_compute_ephem(orbit_file, dark_start, dark_end, site_code, ephem_step_size):
    '''Wrapper for compute_ephem to enable use within plan_obs (or other codes)
    by making repeated calls for datetimes from <dark_start> -> <dark_end> spaced
    by <ephem_step_size> seconds. The results are assembled into a list of tuples
    in the same format as returned by read_findorb_ephem()'''
    from urlsubs import fetch_NEOCP_orbit
    from rise_set.moving_objects import read_neocp_orbit

    ast = os.path.basename(orbit_file)
    ast = ast.replace('.neocp', '')
    print "Reading from",orbit_file, "for", ast
    elements = read_neocp_orbit(orbit_file)

    print
    formatted_elem_lines = mpc_8lineformat(elements)
    for line in formatted_elem_lines:
        print line

    step_size_secs = 300
    if ephem_step_size[-1] == 'm':
        try:
            step_size_secs = float(ephem_step_size[0:-1]) * 60
        except ValueError:
            pass
    ephem_time = round_datetime(dark_start, step_size_secs / 60, False)

    emp = []
    while ephem_time < dark_end:
        emp_line = compute_ephem(ephem_time, elements, site_code, dbg=False, perturb=True, display=False)
        emp.append(emp_line)
        ephem_time = ephem_time + timedelta(seconds=step_size_secs)
    print

# Construct ephem_info
    ephem_info = { 'obj_id' : ast,
                   'emp_sitecode' : site_code,
                   'emp_timesys': '(UT)',
                   'emp_rateunits': '"/min'
                 }

    return ephem_info, emp


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
        print "Unsupported sitecode",sitecode
        return (None,None)

    return ad_start, ad_end

def accurate_astro_darkness(sitecode, utc_date, debug=False):

# Convert passed UTC date to MJD and then Julian centuries

    mjd_utc = datetime2mjd_utc(utc_date)
    T = (mjd_utc - 51544.5)/36525.0

# Mean longitude of the Sun
    sun_mean_long = ( 280.46645 + T * (36000.76983 + T * 0.0003032) ) % 360

# Mean anomaly of the Sun
    sun_mean_anom = ( 357.52910 + T * (35999.05030 - T * ( 0.0001559 - 0.00000048 * T ) ) ) % 360

# Earth's eccentricity
    earth_e = 0.016708617 - T * ( 0.000042037 - T * 0.0000001236 )

# Sun's equation of the center
    sun_eqcent = (1.914600 - T * (0.004817 - 0.000014 * T)) * sin(radians(sun_mean_anom)) +\
                 (0.019993 - T * 0.000101 ) * sin(2.0 *radians(sun_mean_anom)) +\
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
    sunrise = ( solarnoon - hourangle*4/1440  ) % 1
    sunset = ( solarnoon + hourangle*4/1440 ) % 1
    if debug: print solarnoon + hourangle*4/1440, solarnoon - hourangle*4/1440
    if debug: print sunset,sunrise

    if sunrise < sunset:
        sunrise = sunrise + 1
    if debug:
        to_return = [T, sun_mean_long, sun_mean_anom, earth_e, sun_eqcent, sun_true_long, degrees(omega), sun_app_long, \
            degrees(eps0), eps, degrees(sun_app_ra), degrees(sun_app_dec), eqtime, hourangle ]
        print to_return

    else:
        to_return = ( utc_date+timedelta(days=sunset), utc_date+timedelta(days=sunrise) )

    return to_return

def dark_and_object_up(emp, dark_start, dark_end, slot_length, alt_limit=30.0, debug=False):
    '''Returns the subset of the passed ephemeris where the object is up and
    the site is dark.
    Modified 2013/1/21: Now slot_length is passed in so this is subtracted
    from the night end, ensuring blocks don't begin at sunrise.'''

    dark_up_emp = []

    for x in emp:
        visible = False
        if  (x[0]>=dark_start and x[0]<=dark_end-timedelta(minutes=slot_length)) and x[5] >= alt_limit:
            visible = True
            dark_up_emp.append(x)
        if debug: print x[0].date(), x[0].time(), (x[0]>=dark_start and x[0]<dark_end-timedelta(minutes=slot_length)), x[5], visible


    return dark_up_emp

class MagRangeError(Exception):
    '''Raised when an invalid magnitude is found'''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

BRIGHTEST_ALLOWABLE_MAG = 5

def get_mag_mapping(site):
    '''Defines the site-specific mappings from target magnitude to desired
    exposure time. A null dictionary is returned if the site name isn't
    recognized'''

# Magnitudes represent upper bin limits
    site = site.upper()
    if site == 'FTX' or site == 'FTS':
# Mappings for FTN/FTS. Assumes Spectral+Solar filter
        mag_mapping = {
                19   : 45,
                19.5 : 60,
                20   : 100,
                20.5 : 120,
                21   : 150,
                21.5 : 215,
                22   : 240,
                23.3 : 300
               }
    elif site == 'SQA' :
# Mappings for Sedgwick. Assumes kb18+parfocal clear
        mag_mapping = {
                18   : 45,
                19   : 100,
                20   : 150,
                21   : 240,
                21.6 : 300
                }
    elif site == 'ELP' or site == 'LSC' or site == 'CPT':
# Mappings for McDonald. Assumes kb74+w
        mag_mapping = {
                18   : 45,
                19   : 100,
                20   : 150,
                21   : 240,
                22.0 : 300
               }
    else:
        mag_mapping = {}

    return mag_mapping


def mag_to_exptime(site, mag, debug=False):

    if mag < BRIGHTEST_ALLOWABLE_MAG:
        raise MagRangeError("Target too bright")

# Obtain magnitude->exp. time mapping dictionary
    mag_mapping = get_mag_mapping(site)
    if debug: print mag_mapping
    if mag_mapping == {}: return 9999

    # Derive your tuple from the magnitude-exposure mapping data structure
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
        score = (objalt_wgt * obj_alt) - (moonalt_wgt * moon_alt )

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

    if dbg: print
    if dbg: print site_name, site_long, site_lat, site_hgt
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

    if dbg: print "Moon RA, Dec, diam=", moon_ra, moon_dec, diam
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
    mjd_utc =  datetime2mjd_utc(date)
    if dbg: print mjd_utc
# Compute UT1-UTC

    dut = ut1_minus_utc(mjd_utc)
    if dbg: print dut
# Perform apparent->observed place transformation
    (obs_az, obs_zd, obs_ha, obs_dec, obs_ra) = S.sla_aop(moon_app_ra, moon_app_dec,\
        mjd_utc, dut, obsvr_long, obsvr_lat, obsvr_hgt, xp, yp, \
        temp_k, pres_mb, rel_humid, wavel, tlr)

# Normalize azimuth into range 0..2PI
    obs_az = S.sla_ranorm(obs_az)
# Convert zenith distance to altitude (assumes no depression of the horizon
# due to observers' elevation above sea level)

    obs_alt = (pi/2.0)-obs_zd
    if dbg: print obs_az, obs_zd, obs_alt
    return (obs_az, obs_alt)

def moonphase(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg=False):

    mjd_tdb = datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg)
    (moon_ra, moon_dec, moon_diam) = S.sla_rdplan(mjd_tdb, 3, obsvr_long, obsvr_lat)

    (sun_ra, sun_dec, sun_diam) = S.sla_rdplan (mjd_tdb, 0, obsvr_long, obsvr_lat)

    cosphi = ( sin( sun_dec ) * sin( moon_dec ) + cos( sun_dec ) \
        * cos( moon_dec ) * cos( sun_ra - moon_ra ) )
    if dbg: print "cos(phi)=", cosphi

# Full formula for phase angle, i. Requires r (Earth-Sun distance) and del(ta) (the
# Earth-Moon distance) neither of which we have with our methods. However Meeus
# _Astronomical Algorithms_ p 316 reckons we can "put cos(i) = -cos(phi) and k (the
# Moon phase) will never be in error by more than 0.0014"
#    i = atan2( r * sin(phi), del - r * cos(phi) )

    cosi = -cosphi
    if dbg: print "cos(i)=", cosi
    mphase = ( 1.0 + cosi ) / 2.0

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
    if ( dbg ):
        print 'GMST, LAST, EQEQX, GAST, long=', gmst, stl, S.sla_eqeqx(mjd_tdb), gmst+S.sla_eqeqx(mjd_tdb), obsvr_long

    (app_ra, app_dec) = S.sla_map(mean_ra, mean_dec, 0.0, 0.0, 0.0, 0.0, 2000.0, mjd_tdb)
    if dbg: print app_ra, app_dec, radec2strings(app_ra, app_dec)
    hour_angle = stl - app_ra
    if dbg: print hour_angle
    hour_angle = S.sla_drange(hour_angle)
    if dbg: print hour_angle

    return hour_angle

def sla_geoc_iers2003_au(p, h):
    '''Convert geodetic position to geocentric.
    *  Given:
    *     p     dp     latitude (geodetic, radians)
    *     h     dp     height above reference spheroid (geodetic, metres)
    *
    *  Returned:
    *     r     dp     distance from Earth axis (km)
    *     z     dp     distance from plane of Earth equator (km)
    *  Notes:
    *
    *  1  Geocentric latitude can be obtained by evaluating ATAN2(Z,R).
    *
    *  2  This version is an update of the original sla_geoc (which used
    *     IAU 1976 constants) to use IERS2003 constants.
    *'''

# Earth equatorial radius (metres)
    a0=6378137.0

#  Astronomical unit in metres
    au=1.49597870700e11

# Reference spheroid flattening factor and useful function
    f=1.0/298.257223563
    b=(1.0-f)**2

# Geodetic to geocentric conversion
#
    sp = sin(p)
    cp = cos(p)
    c = 1.0 / sqrt(cp * cp + b * sp * sp )
    s = b * c
    r = ((a0*c + h) * cp)/au
    z = ((a0*s + h) * sp)/au

    return (r, z)

def tal_pvobs_2003(p, h, stl):

#  Mean sidereal rate (at J2000) in radians per (UT1) second
    sr = 7.292115855306589e-5
    
#  Geodetic to geocentric conversion
    (r, z) = sla_geoc_iers2003_au(p, h)

#  Functions of Sidereal Time
    s=sin(stl)
    c=cos(stl)

#  Speed
    v=sr*r

# Form  Position and Velocity array
    pv = array([  r*c,
                  r*s,
                  z,
                  -v*s,
                  v*c,
                  0.0])

    return pv

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

def validate_radec(ra_radians, dec_radians):

    twopi = pi * 2.0
    valid = True
    
    if (ra_radians < 0 or ra_radians > twopi ):
        valid = False

    if (dec_radians < -pi or dec_radians > pi ):
        valid = False

    return valid

def get_mountlimits(site):

    ha_pos_limit = 12.0 * 15.0
    ha_neg_limit = -12.0 * 15.0

    if '-1M0A' in site:
        ha_pos_limit = 4.5 * 15.0
        ha_neg_limit = -4.5 * 15.0
    elif '-AQWA' in site:
        ha_pos_limit = 4.25 * 15.0
        ha_neg_limit = -4.25 * 15.0

    return (ha_neg_limit, ha_pos_limit)


def get_siteparams(site):
    '''Translates <site> (e.g. 'FTN') to MPC site code, pixel scale, maximum
    exposure time and slot length.
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

    valid_site_codes = [ 'V37', 'W85', 'W86', 'W87', 'K91', 'K92', 'K93', 'Q63', 'Q64' ] 

    site = site.upper()
    if site == 'FTN' or 'OGG-CLMA' in site or site == 'F65':
        site_code = 'F65'
        slot_length =  30
        pixel_scale = 0.304
        fov = arcmins_to_radians(10.0)
        max_exp_length = 300.0
        alt_limit = twom_alt_limit
    elif site == 'FTS' or 'COJ-CLMA' in site or site == 'E10':
        site_code = 'E10'
        slot_length = 30
        pixel_scale = 0.304
        fov = arcmins_to_radians(10.0)
        max_exp_length = 300.0
        alt_limit = twom_alt_limit
    elif 'SQA' in site:
        site_code = 'G51'
        slot_length = 30
        pixel_scale = 0.57
        fov = arcmins_to_radians(12.0)
        max_exp_length = 300.0
        alt_limit = normal_alt_limit
    elif 'ELP-DOM' in site:
        site_code = 'V37'
        slot_length = 35
        pixel_scale = onem_pixscale
        fov = arcmins_to_radians(onem_fov)
        max_exp_length = 300.0
        alt_limit = normal_alt_limit
    elif 'BPL-DOM' in site:
        site_code = 'G51'
        slot_length = 30
        pixel_scale = onem_sinistro_pixscale
        fov = arcmins_to_radians(onem_sinistro_fov)
        max_exp_length = 300.0
        alt_limit = normal_alt_limit
    elif 'ELP-SITE' in site or 'LSC-SITE' in site or 'CPT-SITE' in site or 'COJ-SITE' in site:
# Overall metasite for Planck observations
        pond_site_codes = { 'ELP-SITE' : 'V37', 
                            'LSC-SITE' : 'W85',
                            'CPT-SITE' : 'K91',
                            'ELP-SITE-1M0A' : 'V37',
                            'LSC-SITE-1M0A' : 'W85',
                            'CPT-SITE-1M0A' : 'K91',
                            'COJ-SITE-1M0A' : 'Q63',
                          }
        site_code = pond_site_codes.get(site, 'XXX')
# Lookup failed, set to unrecognized
        if site_code == 'XXX':
            slot_length = pixel_scale = fov = max_exp_length = alt_limit = -1 
        else:
# Site code found, set parameters
            slot_length = 35.0
            pixel_scale = onem_pixscale
            fov = arcmins_to_radians(onem_fov)
            if 'LSC-SITE' in site:
                pixel_scale = onem_sinistro_pixscale
                fov = arcmins_to_radians(onem_sinistro_fov)
            max_exp_length = 300.0
            alt_limit = normal_alt_limit
# Used for GAIA
#            max_exp_length = 90.0
#            alt_limit = 40.0
    elif 'LSC-DOM' in site or 'CPT-DOM' in site or 'COJ-DOM' in site:
        pond_site_codes = { 'LSC-DOMA-1M0A' : 'W85',
                            'LSC-DOMB-1M0A' : 'W86',
                            'LSC-DOMC-1M0A' : 'W87',
                            'CPT-DOMA-1M0A' : 'K91',
                            'CPT-DOMB-1M0A' : 'K92',
                            'CPT-DOMC-1M0A' : 'K93',
                            'COJ-DOMA-1M0A' : 'Q63',
                            'COJ-DOMB-1M0A' : 'Q64',
                          }
        site_code = pond_site_codes.get(site, 'XXX')
# Lookup failed, set to unrecognized
        if site_code == 'XXX':
            slot_length = pixel_scale = fov = max_exp_length = alt_limit = -1
        else:
# Site code found, set parameters
            slot_length = 35.0
            pixel_scale = onem_pixscale
            fov = arcmins_to_radians(onem_fov)
            if 'LSC-DOMB' in site or 'LSC-DOMC' in site:
                pixel_scale = onem_sinistro_pixscale
                fov = arcmins_to_radians(onem_sinistro_fov)
            max_exp_length = 300.0
            alt_limit = normal_alt_limit
    elif 'LSC-AQWA-0M4A' in site:
        site_code = 'W85' #  XXX Wrong
        slot_length = 30
        pixel_scale = point4m_pixscale
        fov = arcmins_to_radians(point4m_fov)
        max_exp_length = 300.0
        alt_limit = 17.0
    elif site in valid_site_codes:
        slot_length = 25
        pixel_scale = onem_pixscale
        fov = arcmins_to_radians(onem_fov)
        if 'W86' in site or 'W87' in site:
            pixel_scale = onem_sinistro_pixscale
            fov = arcmins_to_radians(onem_sinistro_fov)
        max_exp_length = 300.0
        alt_limit = normal_alt_limit
        site_code = site
    else:
# Unrecognized site
        site_code = 'XXX'
        slot_length = pixel_scale = fov = max_exp_length = alt_limit = -1

    return (site_code, slot_length, pixel_scale, fov, max_exp_length, alt_limit)
