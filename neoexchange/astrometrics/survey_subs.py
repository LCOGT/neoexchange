import ast
from datetime import datetime
from math import degrees, radians, pi, sqrt

from astropy import units as u
from astropy.constants import R_earth
import astropy.coordinates as coord
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.ticker import MultipleLocator
import numpy as np
import pyslalib.slalib as S

from .ephem_subs import get_sitepos, datetime2mjd_tdb, moon_ra_dec, moon_alt_az, moonphase # compute_local_st, 

def read_observables(filename):

    obs_fh = open(filename, 'r')
    observables = obs_fh.readlines()
    obs_fh.close()

    nights = []
    for night in observables:
        obs_night = datetime.strptime(night[2:18], '%Y-%m-%d %H:%M')
        foo_dict = ast.literal_eval(night[21:-2])
        nights.append( {'utc_date' : obs_night,
                        'asteroids' : foo_dict['asteroids'],
                        'night_length': foo_dict['night_length'],
                        'dark_start' : foo_dict['dark_start'],
                        'dark_end' : foo_dict['dark_end']
                        })

    return nights

def filter_by_speed(asteroids, min_speed=0.0, max_speed=999.9):
    '''Filter the passed list of <asteroids> by the speed.'''

    good_asteroids = []
    for rock in asteroids:
#                      0    1   2        3           4
#         emp_line = (ra, dec, mag, total_motion, alt_deg)
        emp_line = rock.values()[0]
        speed = emp_line[3] * (u.arcsec/u.minute)
        if speed >= min_speed and speed <= max_speed:
            good_asteroids.append(rock)

    return good_asteroids

def calculate_min_max_speed(pixel_scale=0.56, seeing=0.9, exptime=60, max_length=700):

    if hasattr(pixel_scale, 'unit') == False:
        pixel_scale = pixel_scale * u.arcsec
    if hasattr(seeing, 'unit') == False:
        seeing = seeing * u.arcsec
    if hasattr(exptime, 'unit') == False:
        exptime = exptime * u.second
    if hasattr(max_length, 'unit') == False:
        max_length = max_length * u.second

    # Lowest speed is set by the need to move by more the seeing in the total length of
    # the observing visit (max_length)
    min_speed = seeing / max_length
    min_speed = min_speed.to(u.arcsec/u.minute)
    # Maximum speed is set by the need to not trail by more than three times the seeing
    # in the exposure time
    max_speed = (3.0 * seeing) / exptime
    max_speed = max_speed.to(u.arcsec/u.minute)

    return min_speed, max_speed

def plot_rates(asteroids, min_speed, max_speed, plot_filename=None):

    mags = [x.values()[0][2] for x in asteroids]
    speeds = [x.values()[0][3] for x in asteroids]
    plt.hist(speeds, bins=25, color='b')
    if hasattr(min_speed, 'unit'):
        x_min = min_speed.to(u.arcsec/u.minute).value
    else:
        x_min = min_speed
    if hasattr(max_speed, 'unit'):
        x_max = max_speed.to(u.arcsec/u.minute).value
    else:
        x_max = max_speed

    plt.axvline(x=x_min, color='r', linestyle='--')
    plt.axvline(x=x_max, color='r', linestyle='--')
    plt.xlabel('Speed (arcsec/minute)')
    if plot_filename:
        plt.savefig(plot_filename, bbox_inches='tight')
    else:
        plt.show()

    return

def compute_ecliptic_location(date, site_code):
    '''Calculate and return two 4000 element long arrays giving the location of the ecliptic
    for the passed <date> (as a UTC datetime) in J2000 RA, Dec co-ordinates'''

    # Compute date as MJD_TDB
    (site_name, site_long, site_lat, site_hgt) = get_sitepos(site_code)
    mjd_tdb = datetime2mjd_tdb(date, site_long, site_lat, site_hgt, False)

    # Ecliptic plane
    ecl_lon = np.linspace(0,360,4000)
    ecl_lat = np.zeros(ecl_lon.shape)
    ecliptic_ra_list = []
    ecliptic_dec_list = []
    for elong,elat in zip(ecl_lon, ecl_lat):
        ecl_ra, ecl_dec = S.sla_ecleq(radians(elong), radians(elat), mjd_tdb)
        ecliptic_ra_list.append(ecl_ra)
        ecliptic_dec_list.append(ecl_dec)
    ecliptic_ra  = coord.Angle(ecliptic_ra_list * u.radian)
    ecliptic_dec = coord.Angle(ecliptic_dec_list * u.radian)

    return ecliptic_ra, ecliptic_dec

def plot_neos(date, site_code, asteroids, alt_limit=30.0, plot_filename=None):

    # Determine local sidereal time
    (site_name, site_long, site_lat, site_hgt) = get_sitepos(site_code)
    local_sidereal_time = compute_local_st(date, site_long, site_lat, site_hgt, dbg=False)
    # Normalize into range 0..PI for plot
    local_sidereal_time = S.sla_drange(local_sidereal_time)

    (moon_app_ra, moon_app_dec, diam) = moon_ra_dec(date, site_long, site_lat, site_hgt)
    moon_app_ra = S.sla_drange(moon_app_ra)
    ra_list = []
    dec_list = []
    for rock in asteroids:
        emp_line = rock.values()[0]
        if emp_line[4] >= alt_limit:
            ra = degrees(emp_line[0])
            dec = degrees(emp_line[1])
            ra_list.append(ra)
            dec_list.append(dec)

    ra = coord.Angle(ra_list*u.degree)
    ra = ra.wrap_at(180*u.degree)
    dec = coord.Angle(dec_list*u.degree)

    area, min_ra, max_ra, min_dec, max_dec = compute_area(asteroids, alt_limit)
#    width = max_ra - min_ra
#    height = max_dec - min_dec
    width =  height = radians(sqrt(400.0))
    center_ra = (max_ra + min_ra)/2.0
    center_ra = S.sla_drange(center_ra)
    center_dec = (max_dec + min_dec)/2.0
    radius = radians(90-alt_limit)
#    print("Center", center_ra, center_dec, radius)

    # Setup plot with Mollweide projection
    fig = plt.figure(figsize=(8,6))
    ax = fig.add_subplot(111, projection="mollweide")
    # The following line makes it so that the zoom level no longer changes,
    # otherwise Matplotlib has a tendency to zoom out when adding overlays.
    ax.set_autoscale_on(False)

    # Plot NEOs as a scatterplot
    ax.scatter(ra.radian, dec.radian, 10)

    # Plot a rectangle of the BlackGEM survey area centered on the LST and Declination=latitude
    r = Rectangle((local_sidereal_time, site_lat), width, height, edgecolor='black', facecolor='none')
    ax.add_patch(r)
    # Plot a circle at the mean RA,Dec
    c = Circle((center_ra, center_dec), radius, edgecolor='red', facecolor='none')
    ax.add_patch(c)
    ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])

    # Plot ecliptic. Plot in two parts because otherwise there is a distracting line
    # across the equator.
    ecliptic_ra, ecliptic_dec = compute_ecliptic_location(date, site_code)
    ecliptic_ra = ecliptic_ra.wrap_at(180*u.degree)
    # find breakpoint in the RA array when it wraps
    ra_wrap = ecliptic_ra.argmax()
    ax.plot(ecliptic_ra[0:ra_wrap].radian, ecliptic_dec[0:ra_wrap].radian, '--b')
    ax.plot(ecliptic_ra[ra_wrap+1:].radian, ecliptic_dec[ra_wrap+1:].radian, '--b')

    # Plot a circle at the Moon's position
    ax.scatter(moon_app_ra, moon_app_dec, 75, color='w', edgecolors='k')
    ax.set_title("%s #asteroids: %4d" % (date.strftime("%Y-%m-%d"), len(asteroids)))
    ax.grid(True)
    fig.tight_layout()
    if plot_filename:
        fig_file  = default_storage.open(plot_filename,"wb+")
        fig.savefig(fig_file, format='png')
        fig_file.close()
    else:
        fig.show()

    plt.close('all')

    return

def plot_summary(config, alt_limit, snr_cut, dates, num_asts, num_filtered, num_abovesnr, num_in_fov, phase):
    '''Construct a summary plot with the number of asteroids (original, filtered
    by speed, above SNR cut and within FOV) against time (in the <dates> list)'''

    fig = plt.figure(figsize=(8,6))
    ax = fig.add_subplot(111)
    ml = MultipleLocator(50)
    line1 = ax.plot(dates, num_asts, '-k', label='# asteroids')
    line2 = ax.plot(dates, num_filtered, label='# asts (after spd cuts)')
    line3 = ax.plot(dates, num_abovesnr, label='# asts (after SNR cuts)')
    line4 = ax.plot(dates, num_in_fov,   label='# asts in FOV')
    ax.yaxis.set_minor_locator(ml)

    ax2 = ax.twinx()
    ml2 = MultipleLocator(0.25)
    line5 = ax2.plot(dates, phase, label='Moon phase')
    ax2.set_ylim(top=5)
    ax2.set_ylabel('Moon Phase (0=New Moon, 1=Full Moon')
    ax2.yaxis.set_minor_locator(ml2)
    ax.set_ylabel('Number of asteroids')

    line = line1+line2+line3+line4+line5
    labs = [l.get_label() for l in line]
    ax.legend(line, labs, loc='best', fontsize='small')
    ax.axhline(0, color='gray', linestyle='--')

#    fig.tight_layout()
    plot_filename = "%s_%s-%s_%.1f_snr_%.1f.pdf" % (config, dates[0].strftime("%Y%m%d"), dates[-1].strftime("%Y%m%d"), alt_limit, snr_cut)
    fig_file  = default_storage.open(plot_filename,"wb+")
    fig.savefig(fig_file, format='png')
    fig_file.close()

    plt.close('all')

    return plot_filename

def calculate_airmass(altitude):
    '''Compute airmass from the passed altitude (in degrees)'''

    zd = radians(90.0 - altitude)
    airmass = S.sla_airmas(zd)

    return airmass

def compute_sky_mag_change(utc_date, site_code):
    '''Calculate the change in sky brightness due to the Moon for the specific utc_date
    from the passed sIte_code'''

    (site_name, site_long, site_lat, site_hgt) = get_sitepos(site_code)
# Compute apparent RA, Dec of the Moon
    (moon_app_ra, moon_app_dec, diam) = moon_ra_dec(utc_date, site_long, site_lat, site_hgt)
# Convert to alt, az (only the alt is actually needed)
    (moon_az, moon_alt) = moon_alt_az(utc_date, moon_app_ra, moon_app_dec, site_long, site_lat, site_hgt)
    moon_alt = degrees(moon_alt)

    moon_phase = moonphase(utc_date, site_long, site_lat, site_hgt)

    # Moon phase runs from 0 (New Moon) to 1.0 (Full Moon). Convert days from New Moon and
    # brightness changes from:
    # http://www.ls.eso.org/lasilla/Telescopes/2p2/D1p5M/misc/SkyBrightness.html
    # to phase ranges. Using R as an approximation to r'
    # Value of denomintor is synodic month (New Moon to New Moon)
    d2p = 1.0 / (29.530589/2.0)
    delta_mag = 0.0
    if moon_alt > 0:
        if moon_phase >= 3.0*d2p and moon_phase < 7.0*d2p:
            # 3-7 days from New Moon
            delta_mag = -0.1
        elif  moon_phase >= 7.0*d2p and moon_phase < 10.0*d2p:
             # 7-10 days from New Moon
            delta_mag = -0.3
        elif  moon_phase >= 10.0*d2p and moon_phase < 14.0*d2p:
             # 10-14 days from New Moon
            delta_mag = -0.6
        elif  moon_phase >= 14.0*d2p:
             # 14+ days from New Moon
            delta_mag = -1.0

    return delta_mag, moon_phase, moon_alt

def construct_obs_tech_dict():

    obs_tech_dict_list = {'blackgem': { 'zero_mag_flux_dens' :  (10.0**(16.847/2.5))/1390.0/(6170.0/1390.0),
                                        'tel_throughput' : 0.7**2, #two mirrors
                                        'inst_throughput' : 0.8 * 0.99**5, #six surfaces
                                        'mirror_eff_area' : (pi * (0.65)**2) - (pi * (0.26)**2), #[m^2]
                                        'filters' : { 'r' : { 'bandwidth'  : 1390.0,
                                                              'throughput' : 0.80,
                                                              'eff_wave'   : 6170.0,
                                                              'extinction' : 0.13/1.2,
                                                              'sky_mag'    : 21.1, #[mag/arcsec**2] #(Tonry et al., 2012)
                                                              'quantum_efficiency' : 0.91
                                                            },
                                                      'g' : { 'bandwidth'  : 1370.0,
                                                              'throughput' : 0.5,
                                                              'eff_wave'   : 4810.0,
                                                              'extinction' : 0.22/1.2,
                                                              'sky_mag'    : 21.7,
                                                              'quantum_efficiency' : 0.90
                                                            }
                                                     },
                                        'pixel_scale'   : 0.562,
                                        'dark_current'  : 0.001, # electrons/pixel/sec
                                        'read_noise'    : 5.5,   # readnoise in electrons
                                        'seeing'        : 0.9,   # Seeing at zenith@0.5um
                                        'mpc_site_code' : 'ESONTT'
                                      },
                          '1m0-sbig': {}
                         }

    return obs_tech_dict_list

def compute_source_pixels(zen_seeing, wavelength, airmass, pixel_scale, dbg=False):
    '''Compute the number of pixels covered by the source.
    The seeing at the zenith (<zen_seeing>) and 0.5um (5000 angstrom; ~V band) is
    scaled to the observed <wavelength> (in angstroms) and the airmass.
    The number of pixels is calculated from this diameter of the seeing disc, scaled
    by the <pixel_scale> (in arcsec/pixel)'''

    num_pixels = None
    # Compute seeing at wavelength and airmass
    if wavelength >= 3000.0 and wavelength <= 10000.0:
        seeing = zen_seeing * airmass**0.6/((wavelength/5000.0)**-0.2)
        num_pixels = int(round(pi*(seeing/2.0)**2 / pixel_scale**2))
        if dbg: print("Seeing", seeing, zen_seeing, wavelength, airmass)
    else:
        print("Wavelength out of range of 3000..10000 angstroms")
    return num_pixels

def compute_snr(obs_tech_dict_list, site_name, obs_filter, mag, airmass, exp_time, sky_delta_mag=0.0, dbg=False):

    snr = None
    S_o, S_s = compute_source_sky_flux(obs_tech_dict_list, site_name, obs_filter, mag, airmass, sky_delta_mag, dbg)

    if S_o and S_s:
        obs_details = obs_tech_dict_list.get(site_name, None)

        if obs_details == None:
            return snr

        if obs_filter not in obs_details['filters']:
            print("No match for filter", obs_filter)
            return snr

        filter_details = obs_details['filters'][obs_filter]
        Q = filter_details['quantum_efficiency']
        wavelength = filter_details['eff_wave']
        S_d = obs_details['dark_current']
        R_sq = obs_details['read_noise'] * obs_details['read_noise']
        seeing = obs_details['seeing']
        pixel_scale = obs_details['pixel_scale']

        # Compute the number of pixels
        n_p = compute_source_pixels(seeing, wavelength, airmass, pixel_scale, dbg)

        #compute the source term
        source = S_o * Q * exp_time
        if dbg: print("Source term", source, S_o, Q, exp_time)

        #compute the sky term
        sky = S_s * Q * exp_time * n_p
        if dbg: print("Sky term", sky, S_s, Q, exp_time, n_p)

        #compute the dark current term
        dark_current = S_d * exp_time * n_p
        if dbg: print("Dark c. term", dark_current)

        #compute the read noise term
        read_noise = R_sq * n_p
        if dbg: print("Readnoise term", read_noise)

        #compute the SNR
        SNR = source / sqrt(source + sky + dark_current + read_noise)

        if dbg: print("SNR=", SNR)
    return SNR

def compute_source_sky_flux(obs_tech_details, site_name, obs_filter, obj_mag, airmass, sky_deltam=0.0, dbg=False):

    obs_details = obs_tech_details.get(site_name, None)

    if obs_details == None:
        return None, None

    zero_mag_flux_dens = obs_details['zero_mag_flux_dens']
    tel_throughput = obs_details['tel_throughput']
    inst_throughput = obs_details['inst_throughput']
    mirror_eff_area = obs_details['mirror_eff_area']
    pixel_scale = obs_details['pixel_scale']

    if obs_filter not in obs_details['filters']:
        print("No match for filter", obs_filter)
        return None, None

    filter_details = obs_details['filters'][obs_filter]
    filter_throughput = filter_details['throughput']
    extinction = filter_details['extinction']
    bandwidth = filter_details['bandwidth']
    sky_mag = filter_details['sky_mag']

    flux_dens = zero_mag_flux_dens / (100.0**(obj_mag/5.0)) #[ph/s/cm**2/A]

    if dbg: print('flux', flux_dens, obj_mag)

    #account for extinction in atmosphere at maximum airmass in observing window
    flux_dens /= (100.0**(extinction*airmass/5.0)) #[ph/s/cm**2/A]

    #account for reflectivity of aluminum mirrors
    flux_dens *= tel_throughput #[ph/s/cm**2/A]

    #account for mirror/telescope collecting area
    flux_dens *= mirror_eff_area * (100.0**2) #[photons/s/A]

    #account for throughput of corrective lenses
    flux_dens *= inst_throughput #[ph/s/A]

    #account for filter throughput
    flux_dens *= filter_throughput #[ph/s/A]

    #account for filter bandwidth (Tonry et al., 2012)
    flux_dens *= bandwidth #[ph/s]

    if dbg: print('flux', flux_dens)

    S_o = flux_dens

    #sky background

    #scale zero_mag_flux_dens by sky magnitude, adjusted by sky_deltam (moonlight etc)
    sky_flux_dens = zero_mag_flux_dens / (100.0**((sky_mag+sky_deltam)/5.0)) #[ph/s/cm**2/A/arcsec**2]

    if dbg: print('sky mag, delta mag, sky flux', sky_mag,sky_deltam, sky_flux_dens)

    #account for extinction in atmosphere at airmass=1.0
    sky_flux_dens /= (100.0**(extinction*airmass/5.0)) #[ph/s/cm**2/A/arcsec**2]

#    print('sky flux', sky_flux_dens)

    #account for reflectivity of aluminum mirrors
    sky_flux_dens *= tel_throughput #[ph/s/cm**2/A/arcsec**2]

#    print('sky flux', sky_flux_dens)

    #account for mirror/telescope collecting area
    sky_flux_dens *= mirror_eff_area * (100.0**2) #[photons/s/A/arcsec**2]

#    print('sky flux', sky_flux_dens)

    #account for throughput of corrective lenses
    sky_flux_dens *= inst_throughput #[ph/s/A/arcsec**2]

#    print('sky flux', sky_flux_dens)

    #account for filter throughput
    sky_flux_dens *= filter_throughput #[ph/s/A]

#    print('sky flux', sky_flux_dens)

    #account for filter bandwidth (Tonry et al., 2012)
    sky_flux_dens *= bandwidth #[ph/s/arcsec**2]

#    print('sky flux', sky_flux_dens)

    S_s = sky_flux_dens

    S_s *= (pixel_scale)**2 #[photons/s/pixel] (Note: pixel_scale for typical binning used, i.e. sbig: 2x2, sinistro: 1x1, 2m: 2x2)

    return S_o, S_s

def filter_by_snr(utc_date, observable_asts, obs_config, obs_filter, exptime, snr_cut, sky_delta_mag=0.0, dbg=False):

    obs_tech_dict_list = construct_obs_tech_dict()

    site_code = obs_tech_dict_list[obs_config]['mpc_site_code']
    (site_name, site_long, site_lat, site_hgt) = get_sitepos(site_code)
    moon_ra, moon_dec, moon_diam = moon_ra_dec(utc_date, site_long, site_lat, site_hgt, dbg)
    moon_sep = radians(30.0)

    detected_asts = []
    num_moon_filtered = 0
    for asteroid in observable_asts:
#         emp_line = (ra, dec, mag, total_motion, alt_deg)
        emp_line = asteroid.values()[0]
        ra = emp_line[0]
        dec = emp_line[1]
        obj_moon_sep = S.sla_dsep(ra, dec, moon_ra, moon_dec)
        if obj_moon_sep > moon_sep:
            mag = emp_line[2]
            airmass = calculate_airmass(emp_line[4])
            if dbg: print("ra, dec, mag, total_motion, alt_deg,airmass", emp_line, airmass)
            snr = compute_snr(obs_tech_dict_list, obs_config, obs_filter, mag, airmass, exptime, sky_delta_mag, dbg)
            if snr >= snr_cut:
                detected_asts.append(asteroid)
        else:
            if dbg: print("Too close to the moon (%.1f deg) for %s: %s" % (degrees(obj_moon_sep), asteroid.keys()[0], emp_line))
            num_moon_filtered += 1
    return detected_asts, num_moon_filtered

def compute_area(asteroids, alt_limit=0.0):

    min_ra = 2.5 * pi
    max_ra = -2.5 * pi
    min_dec = 2.5 * pi
    max_dec = -2.5 * pi

    twopi = 2.0 *pi
    for asteroid in asteroids:
#                      0    1   2        3           4
#         emp_line = (ra, dec, mag, total_motion, alt_deg)
        emp_line = asteroid.values()[0]
        if emp_line[4] >= alt_limit:
            ra = emp_line[0]
            if abs(ra - min_ra) > pi and min_ra >= 0.0 and ra>pi:
                ra += twopi
            min_ra = min(min_ra, ra)
            max_ra = max(max_ra, ra)
            min_dec = min(min_dec, emp_line[1])
            max_dec = max(max_dec, emp_line[1])
    ra_range = degrees(max_ra-min_ra)
    dec_range = degrees(max_dec-min_dec)
    area = ra_range * dec_range

    return area, min_ra, max_ra, min_dec, max_dec

def filter_by_area(asteroids, footprint, alt_limit=30.0, dbg=False):

    # Compute edges of box
    min_ra = footprint['center'][0] - footprint['width'] / 2.0
    max_ra = footprint['center'][0] + footprint['width'] / 2.0
    c = footprint['center'][1] - footprint['height'] / 2.0
    d = footprint['center'][1] + footprint['height'] / 2.0
    min_dec = min(c, d)
    max_dec = max(c, d)
    if dbg: print("FOV:", min_ra, max_ra, min_dec, max_dec)

    detected_asts = []
    for asteroid in asteroids:
#                      0    1   2        3           4
#         emp_line = (ra, dec, mag, total_motion, alt_deg)
        emp_line = asteroid.values()[0]
        ra = emp_line[0]
        dec = emp_line[1]
        if emp_line[4] >= alt_limit:
            if ra >= min_ra and ra <= max_ra and dec >= min_dec and dec <= max_dec:
                if dbg: print("In box", ra, dec)
                detected_asts.append(asteroid)
    return detected_asts

def neo_absmag_frequency_distribution(H):
    """Returns log10 N( < H), the number of near-Earth objects with absolute magnitude
    smaller than H. N( < H) is tabulated in Harris & Chodas (2021, Appendix B)
    and has been approximated with a polynomial fit 
    (Farnocchia & Chodas, 2021, RNAAS, 5, 11)"""

    try:
        H = H.to_value()
    except AttributeError:
        pass

    Hbar = (H-20.250) / 6.278

    log10_N = 0.156*Hbar**7 - 0.036*Hbar**6 - 0.989*Hbar**5 + 0.270*Hbar**4 + \
        1.974*Hbar**3 - 0.160*Hbar**2 + 1.584*Hbar + 3.788

    return log10_N

def neo_close_approach_frequency(r, H):
    """Calculates and returns the frequency, f, of a NEO close approach within
     a distance <r> and a maximum absolute magnitude <H>.
      can be obtained from that of an impact:
    According to the 2017 Report of the Near-Earth Object Science 
    Definition Team, 1 the per-object impact frequency is 1.66 × 10−9 yr−1 
    and therefore f( < r⊕; < H) = 1.66 × 10−9 yr−1 × N( < H), where N( < H) 
    is the number of near-Earth objects with absolute magnitude smaller 
    than H"""

    # Obtain log10 of the number of NEOs brighter than a specific H and use
    # to scale impact frequency
    log10_N = neo_absmag_frequency_distribution(H)
    N_H = 10**log10_N
    impact_freq = 1.66e-9/u.yr * N_H

    # Calculate hyperbola function of r (scale from 1 (r=R_earth; grazing 
    # impact) to ~0.73 at large distance)
    eta = 2400*u.km
    phi = (1.0 + (eta/r.to(u.km))) / (1.0 + (eta/R_earth.to(u.km)))
    impact_freq * (r.to(u.km) / R_earth.to(u.km))**2 * phi

    return impact_freq
