"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO

time_subs.py -- Various routines to handle times.

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
import time
import logging

try:
    import pyslalib.slalib as S
except:
    pass

logger = logging.getLogger(__name__)


def get_semester_start(date):

    if date <= datetime(2017, 3, 31, 23, 59, 59):
        year, month, day, hour, minute, second = date.year, 4, 1, 0, 0, 0
        if date.month >= 10 or date.month < 4:
            month = 10
            if date.month < 10:
                year -= 1
        start = datetime(year, month, day, hour, minute, second)
    elif datetime(2017, 4, 1, 0, 0, 0) <= date <= datetime(2017, 11, 30, 23, 59, 59):
        start = datetime(2017, 4, 1, 0, 0, 0)
    else:
        year, month, day, hour, minute, second = date.year, 12, 1, 0, 0, 0
        if 6 <= date.month < 12:
            month = 6
        elif date.month <= 5:
            year -= 1
        start = datetime(year, month, day, hour, minute, second)

    return start


def get_semester_end(date):

    if date <= datetime(2017, 3, 31, 23, 59, 59):
        year, month, day, hour, minute, second = date.year, 9, 30, 23, 59, 59
        if date.month >= 10 or date.month < 4:
            month = 3
            day = 31
            if date.month >= 10:
                year += 1
        end = datetime(year, month, day, hour, minute, second)

    elif datetime(2017, 4, 1, 0, 0, 0) <= date <= datetime(2017, 11, 30, 23, 59, 59):
        # Odd 2017AB semester
        end = datetime(2017, 11, 30, 23, 59, 59)
    else:
        year, month, day, hour, minute, second = date.year, 5, 31, 23, 59, 59
        if 6 <= date.month < 12:
            month = 11
            day = 30
        if date.month >= 12:
            year += 1
        end = datetime(year, month, day, hour, minute, second)

    return end


def get_semester_dates(date):
    """Returns the semester start and end datetimes for the LCOGT semesters.
    LCOGT has two semesters, A & B, which run as follows:
    A semester: <year>-04-01 00:00:00 UTC until <year>-09-30 23:59:59 UTC
    B semester: <year>-10-01 00:00:00 UTC until <year+1>-03-31 23:59:59 UTC
    e.g. 2015B runs from 2015-10-01 00:00:00->2016-03-31 23:59:59 and 2016A
    runs from 2016-04-01 00:00:00 until 2016-09-30 23:59:59"""

    start = get_semester_start(date)
    end = get_semester_end(date)

    return start, end


def parse_neocp_date(neocp_datestr, dbg=False):
    """Parse dates from the NEOCP (e.g. '(Nov. 16.81 UT)' ) into a datetime
    object and return this. Checking for the wrong number of days in the month
    is done (in which case we set it to the first day of the next month) but
    otherwise, no sanity checking of the input is done"""
    month_map = { 'Jan' : 1,
                  'Feb' : 2,
                  'Mar' : 3,
                  'Apr' : 4,
                  'May' : 5,
                  'Jun' : 6,
                  'Jul' : 7,
                  'Aug' : 8,
                  'Sep' : 9,
                  'Oct' : 10,
                  'Nov' : 11,
                  'Dec' : 12}

    chunks = neocp_datestr.split()
    if dbg:
        print(chunks)
    if len(chunks) != 3:
        return None
    month_str = chunks[0].replace('(', '').replace('.', '')
    day_chunks = chunks[1].split('.')
    if dbg:
        print(day_chunks)
    month_num = month_map[month_str[0:3]]
    day_num = int(day_chunks[0])
    try:
        neocp_datetime = datetime(year=datetime.utcnow().year, month=month_num, day=day_num)
    except ValueError:
        month_num += 1
        day_num = 1
        neocp_datetime = datetime(year=datetime.utcnow().year, month=month_num, day=day_num)
    decimal_day = float('0.' + day_chunks[1].split()[0])
    neocp_datetime = neocp_datetime + timedelta(days=decimal_day)

    return neocp_datetime


def parse_neocp_decimal_date(neocp_datestr, dbg=False):
    """Parse decimal dates from the NEOCP (e.g. '2015 09 22.5' ) into a datetime
    object and return this. No sanity checking of the input is done"""
    chunks = neocp_datestr.split(' ')
    if dbg:
        print(chunks)
    if len(chunks) != 3:
        return None
    day_chunks = chunks[2].split('.')
    if dbg:
        print(day_chunks)
    neocp_datetime = datetime(year=int(chunks[0]), month=int(chunks[1]), day=int(day_chunks[0]))

    decimal_day = float('0.' + day_chunks[1].split()[0])
    neocp_datetime = neocp_datetime + timedelta(days=decimal_day)

    return neocp_datetime


def round_datetime(date_to_round, round_mins=10, round_up=False):
    """Rounds the passed datetime object, <date_to_round>, to the
    'floor' (default) or the 'ceiling' (if [roundup=True]) of
    the nearest passed amount (which defaults to 10min)"""

    correct_mins = 0
    if round_up:
        correct_mins = round_mins
    date_to_round = date_to_round - timedelta(minutes=(date_to_round.minute % round_mins)-correct_mins,
                        seconds=date_to_round.second,
                        microseconds=date_to_round.microsecond)

    return date_to_round


def extract_mpc_epoch(epochstring):
    """Convert packed MPC epoch format (e.g. 'J974L') from NEOCP orbit files
    into a datetime.datetime epoch (e.g. '1997 4 21'). Returns -1 if invalid
    length (no other sanity checking is done)"""

    if len(epochstring) != 5:
        return -1
    year = 100 * (ord(epochstring[0]) - ord('A') + 10) + \
           10 * (ord(epochstring[1]) - ord('0'))\
           + (ord(epochstring[2]) - ord('0'))

    month = extract_packed_date(epochstring[3])
    day = extract_packed_date(epochstring[4])

    return datetime(year, month, day, 0)


def extract_packed_date(value):
    lookup = {  'A'     : 10,
            'B'     : 11,
            'C'     : 12,
            'D'     : 13,
            'E'     : 14,
            'F'     : 15,
            'G'     : 16,
            'H'     : 17,
            'I'     : 18,
            'J'     : 19,
            'K'     : 20,
            'L'     : 21,
            'M'     : 22,
            'N'     : 23,
            'O'     : 24,
            'P'     : 25,
            'Q'     : 26,
            'R'     : 27,
            'S'     : 28,
            'T'     : 29,
            'U'     : 30,
            'V'     : 31}
    try:
        return int(value)
    except ValueError:
        return lookup[value]


def jd_utc2datetime(jd):
    """Converts a passed Julian date to a Python datetime object. 'None' is
    returned if the conversion was not possible."""

    try:
        mjd_utc = jd-2400000.5
    except TypeError:
        try:
            mjd_utc = float(jd)-2400000.5
        except:
            return None
    year, month, day, frac, status = S.sla_djcl(mjd_utc)
    if status != 0:
        return None
    sign, hms = S.sla_dd2tf(0, frac)
    dt = datetime(year, month, day, hms[0], hms[1], hms[2])
    return dt


def mjd_utc2datetime(mjd):
    """Converts a passed Modified Julian date to a Python datetime object. 'None' is
    returned if the conversion was not possible."""

    year, month, day, frac, status = S.sla_djcl(mjd)
    if status != 0:
        return None
    sign, hms = S.sla_dd2tf(0, frac)
    dt = datetime(year, month, day, hms[0], hms[1], hms[2])
    return dt


def datetime2mjd_utc(d):
    """Converts a passed datetime object in UTC to the equivalent Modified Julian
    Date (MJD), which is returned"""
# Compute MJD for UTC
    (mjd, status) = S.sla_cldj(d.year, d.month, d.day)
    if status != 0:
        return None
    (fday, status) = S.sla_dtf2d(d.hour, d.minute, d.second+(d.microsecond/1e6))
    if status != 0:
        return None
    mjd_utc = mjd + fday

    return mjd_utc


def mjd_utc2mjd_tt(mjd_utc, dbg=False):
    """Converts a MJD in UTC (MJD_UTC) to a MJD in TT (Terrestial Time) which is
    needed for any position/ephemeris-based calculations.
    UTC->TT consists of: UTC->TAI = 10s offset + 26 leapseconds (last one 2015 Jul 1.)
                         TAI->TT  = 32.184s fixed offset"""
# UTC->TT offset
    tt_utc = S.sla_dtt(mjd_utc)
    if dbg:
        print('TT-UTC(s)=', tt_utc)

# Correct MJD to MJD(TT)
    mjd_tt = mjd_utc + (tt_utc/86400.0)
    if dbg:
        print('MJD(TT)  =  ', mjd_tt)

    return mjd_tt


def datetime2mjd_tdb(date, obsvr_long, obsvr_lat, obsvr_hgt, dbg=False):

    auinkm = 149597870.691
# Compute MJD_UTC from passed datetime
    mjd_utc = datetime2mjd_utc(date)
    if mjd_utc is None:
        return None

# Compute MJD_TT
    mjd_tt = mjd_utc2mjd_tt(mjd_utc, dbg)

# Compute TT->TDB

# Convert geodetic position to geocentric distance from spin axis (r) and from
# equatorial plane (z)
    (r, z) = S.sla_geoc(obsvr_lat, obsvr_hgt)

    ut1 = compute_ut1(mjd_utc, dbg)
    if dbg:
        print("UT1=", ut1)

# Compute relativistic clock correction TDB->TT
    tdb_tt = S.sla_rcc(mjd_tt, ut1, -obsvr_long, r*auinkm, z*auinkm)
    if dbg:
        print("(TDB-TT)=", tdb_tt)
    if dbg:
        print("(CT-UT)=", S.sla_dtt(mjd_utc)+tdb_tt)

    mjd_tdb = mjd_tt + (tdb_tt/86400.0)

    return mjd_tdb


def ut1_minus_utc(mjd_utc, dbg=False):
    """Compute UT1-UTC (in seconds), needed for tasks that require the Earth's orientation.
    UT1-UTC can be had from IERS Bulletin A (http://maia.usno.navy.mil/ser7/ser7.dat)
    but only for a short timespan and in arrears requiring continual downloading.
    Really need to get and read ftp://maia.usno.navy.mil/ser7/finals.all
    to get accurate UT1 value or switch to astropy which can automatically
    handle this. Exercise for the reader...
    Currently we fake it by asuming 0.0. This will be wrong by at most +/- 0.9s
    until they do away with leapseconds."""

    dut = 0.0
    return dut


def compute_ut1(mjd_utc, dbg=False):
    """Compute UT1 (as fraction of a day), needed for tasks that require the Earth's orientation.
    Currently we fake it by taking the fractional part of the day. This is good
    to +/- 0.9s until they do away with leapseconds."""

    dut = ut1_minus_utc(mjd_utc)
    if dbg:
        print("DUT=", dut)
    ut1 = (mjd_utc - int(mjd_utc)) + (dut/86400.0)

    return ut1


def datetime2st(d, obsvr_long=0.0):
    """Converts the passed datetime object in UTC to a Sidereal Time.
    If the site longitude [obsvr_long] (East +ve; radians) is passed, then
    the returned `stl` will be the Local Apparent Sidereal Time.
    If not passed (or zero), then the Greenwich Apparent Sidereal Time
    will be returned (Greenwich Mean Sidereal Time (GMST) plus the equation
    of the equinoxes.
    `stl`, the sidereal time, is returned in radians, normalized to the
    range 0...2*PI
    """

    # Compute MJD_UTC and MJD_TT
    mjd_utc = datetime2mjd_utc(d)
    mjd_tt = mjd_utc2mjd_tt(mjd_utc)
    # Determine UT1-UTC and hence MJD_UT1
    dut = ut1_minus_utc(mjd_utc)
    mjd_ut1 = mjd_utc+(dut/86400.0)
    # Greenwich Mean Sidereal Time (GMST), just a function of UT1 ("Earth Rotation Angle")
    gmst = S.sla_gmst(mjd_ut1)
    # Compute Local Apparent Sidereal Time
    stl = gmst + obsvr_long + S.sla_eqeqx(mjd_tt)
    stl = S.sla_dranrm(stl)

    return stl


def hourstodegrees(value, arg):
    """Converts decimal hours to decimal degrees"""
    if ":" in str(value):
        return value
    try:
        return float(value)*15
    except:
        return ""


def degreestohours(value):
    """Converts decimal degrees to decimal hours"""
    if ":" in str(value):
        return value
    try:
        return float(value)/15
    except:
        return ""


def degreestodms(value, sep):
    """Converts decimal degrees to decimal degrees minutes and seconds"""
    if ":" in str(value):
        return value
    try:
        if value < 0:
            sign = "-"
        else:
            sign = "+"
        value = abs(value)
        mnt, sec = divmod(value*3600, 60)
        deg, mnt = divmod(mnt, 60)
        return "%s%02d%c%02d%c%04.1f" % (sign, deg, sep, mnt, sep, sec)
    except:
        return ""


def radianstodms(value, sep):
    """Convert radians e.g a Dec from SLALIB routines to decimal hours minutes
    and seconds"""
    if ":" in str(value):
        return value
    try:
        value = degrees(float(value))
        return degreestodms(value, sep)
    except:
        return ""


def degreestohms(value, sep):
    """Converts decimal degrees to decimal hours minutes and seconds"""
    if ":" in str(value):
        return value
    try:
        value = float(value)/15.
        mnt, sec = divmod(value*3600, 60)
        deg, mnt = divmod(mnt, 60)
        return "%02d%c%02d%c%05.2f" % (deg, sep, mnt, sep, sec)
    except:
        return ""


def radianstohms(value, sep):
    """Convert radians e.g an RA from SLALIB routines to decimal hours minutes
    and seconds"""
    if ":" in str(value):
        return value
    try:
        value = degrees(float(value))
        return degreestohms(value, sep)
    except:
        return ""


def hmstohours(value):
    if ":" not in str(value):
        return value
    el = value.split(":")
    return float(el[0]) + float(el[1])/60. + float(el[2])/3600.

def decimaldaytodt(date_string):
    """Converts a MPC-style Year, Month, Decimal day <date_string> e.g.
    '2013 10 31.16159' into a datetime object (datetime(2013, 10, 31, 3, 52, 41, 376000)
    (Actually just a wrapper around parse_neocp_decimal_date() to provide the
    inverse of dttodecimalday()...)
    """

    return parse_neocp_decimal_date(date_string)

def dttodecimalday(dt, microdays=False):
    """Converts a datetime object <dt> into MPC-style Year, Month, Decimal day. An
    optional argument, microdays, can be given to produce the decimal day to
    6 d.p. i.e. ~0.8 second"""

    try:
        decimal_day = (dt.hour + (dt.minute/60.0)+((dt.second+dt.microsecond/1e6)/3600.0))/24.0
        if microdays:
            date_string = "%02d %02d %09.6f" % (dt.year, dt.month, dt.day + decimal_day)
        else:
            date_string = "%02d %02d %08.5f " % (dt.year, dt.month, dt.day + decimal_day)
    except:
        date_string = ""

    return date_string


def timeit(method):
    """Decorator for timing methods"""
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print('%r (%r, %r) %2.2f sec' % (method.__name__, args, kw, te-ts))
        logger.debug("%r (%r, %r) %2.2f sec" % (method.__name__, args, kw, te-ts))
        return result

    return timed


def tomorrow(n=1):
    """
    Build a function for returning tomorrow's date using datetime.today()
    Will accept integer for number of days after today to return.
    """
    t = datetime.today() + timedelta(days=n)
    return t
