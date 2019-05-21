from datetime import datetime, timedelta

from astropy.table import Column
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from astrometrics.ephem_subs import determine_darkness_times


def plot_ra_dec(ephem, title=None):
    """Plot RA against Dec"""

    fig, ax = plt.subplots()

    ax.plot(ephem['RA'], ephem['DEC'])
    ax.set_xlim(360.0, 0.0)
    ax.set_ylim(-90, 90)
    ax.set_xlabel('RA (deg)')
    ax.set_ylabel('Dec (deg)')
    ax.minorticks_on()
    ax.xaxis.set_ticks_position('both')
    ax.yaxis.set_ticks_position('both')

    first = ephem[0]
    first_date = datetime.strptime(first['datetime_str'], "%Y-%b-%d %H:%M")
    last = ephem[-1]
    last_date = datetime.strptime(last['datetime_str'], "%Y-%b-%d %H:%M")

    if title is None:
        title = "{} for {} to {}".format(first['targetname'], first_date.strftime("%Y-%m-%d"), last_date.strftime("%Y-%m-%d"))
    fig.suptitle(title)
    ax.set_title("Sky position")


    ax.annotate(first_date.strftime("%Y-%m-%d"), xy=(first['RA'], first['DEC']), xytext=(first['RA'], first['DEC']+10),
            arrowprops=dict(facecolor='black', arrowstyle='->'))
    ax.annotate(last_date.strftime("%Y-%m-%d"), xy=(last['RA'], last['DEC']), xytext=(last['RA'], last['DEC']+10),
            arrowprops=dict(arrowstyle='->'))

    save_file = "{}_radec_{}-{}.png".format(first['targetname'].replace(" ", "_"), first_date.strftime("%Y%m%d"), last_date.strftime("%Y%m%d"))
    fig.savefig(save_file, format='png')
    plt.close()

    return save_file

def plot_helio_geo_dist(ephem, title=None):
    """Plot heliocentric distance (r) and geocentric distance (delta)
    against time
    """

    first = ephem[0]
    first_date = datetime.strptime(first['datetime_str'], "%Y-%b-%d %H:%M")
    last = ephem[-1]
    last_date = datetime.strptime(last['datetime_str'], "%Y-%b-%d %H:%M")

    hel_color = 'r' # Red
    geo_color = "#0083ff" # A nice pale blue
    peri_color = '#ff5900' # Sort of orange
    ca_color = '#4700c3'

    fig, ax = plt.subplots()
    dates = [datetime.strptime(d, "%Y-%b-%d %H:%M") for d in ephem['datetime_str']]
    ax.plot(dates, ephem['r'], color=hel_color, linestyle='-')
    ax.plot(dates, ephem['delta'], color=geo_color, linestyle='-')

    perihelion = dates[ephem['r'].argmin()]
    close_approach = dates[ephem['delta'].argmin()]

    ylim = ax.get_ylim()
    ax.vlines([perihelion, close_approach], ylim[0], ylim[1], colors=[peri_color, ca_color])
    ax.set_ylim(0, ylim[1])
    ax.set_xlabel('Date')
    ax.set_ylabel('Distance (AU)')
    ax.minorticks_on()
    ax.xaxis.set_ticks_position('both')
    ax.yaxis.set_ticks_position('both')

    ax.annotate('Heliocentric', xy=(dates[0], first['r']), color=hel_color)
    ax.annotate('Geocentric', xy=(dates[-1], last['delta']), color=geo_color, horizontalalignment='right')
    ax.text(perihelion, 0.9*ylim[1], "perihelion", rotation=90, color=peri_color, horizontalalignment='right')
    ax.text(close_approach, 0.1*ylim[1], "C/A", rotation=90, color=ca_color, horizontalalignment='left')

    if title is None:
        title = "{} for {} to {}".format(first['targetname'], first_date.strftime("%Y-%m-%d"), last_date.strftime("%Y-%m-%d"))
    fig.suptitle(title)
    ax.set_title('Heliocentric & Geocentric distance')

    save_file = "{}_dist_{}-{}.png".format(first['targetname'].replace(" ", "_"), first_date.strftime("%Y%m%d"), last_date.strftime("%Y%m%d"))
    fig.savefig(save_file, format='png')
    plt.close()

    return save_file

def plot_brightness(ephem, title=None):
    """Plot magnitude against time
    """

    first = ephem[0]
    first_date = datetime.strptime(first['datetime_str'], "%Y-%b-%d %H:%M")
    last = ephem[-1]
    last_date = datetime.strptime(last['datetime_str'], "%Y-%b-%d %H:%M")

    hel_color = 'r' # Red
    geo_color = "#0083ff" # A nice pale blue
    peri_color = '#ff5900' # Sort of orange
    ca_color = '#4700c3'

    fig, ax = plt.subplots()
    dates = ephem['datetime']
    ax.plot(dates, ephem['V'], color=hel_color, linestyle='-')

    perihelion = dates[ephem['r'].argmin()]
    close_approach = dates[ephem['delta'].argmin()]

    ylim = ax.get_ylim()
    ax.vlines([perihelion, close_approach], ylim[0], ylim[1], colors=[peri_color, ca_color])
    ax.set_ylim(ylim[1], ylim[0])
    ax.set_xlabel('Date')
    ax.set_ylabel('V magnitude')
    ax.minorticks_on()
    ax.xaxis.set_ticks_position('both')
    ax.yaxis.set_ticks_position('both')

    ax.text(perihelion, 0.9*ylim[1], "perihelion", rotation=90, color=peri_color, horizontalalignment='right')
    ax.text(close_approach, 0.1*ylim[1], "C/A", rotation=90, color=ca_color, horizontalalignment='left')

    if title is None:
        title = "{} for {} to {}".format(first['targetname'], first_date.strftime("%Y-%m-%d"), last_date.strftime("%Y-%m-%d"))
    fig.suptitle(title)
    ax.set_title('Predicted brightness')

    save_file = "{}_mag_{}-{}.png".format(first['targetname'].replace(" ", "_"), first_date.strftime("%Y%m%d"), last_date.strftime("%Y%m%d"))
    fig.savefig(save_file, format='png')
    plt.close()

    return save_file

def plot_hoursup(ephem_ca, site_code, title=None, add_altitude=False, dbg=False):
    """Calculate the number of hours an object is up at a site <site_code>
    from <ephem_ca> - a more closely spaced ephemeris (e.g. 5m) over a
    shorter range. Produces a 2 panel plot which plots the hours above 30 deg
    altitude and V magnitude in the bottom panel and the on-sky rate and
    optionally (if [add_altitude]=True) in the top panel.
    The name of plot file is returned.
    """
    ca_color = '#4700c3'

    first = ephem_ca[0]

    hours_visible = []
    visible_dates = []

    dates = ephem_ca['datetime']

    # Determine times of darkness for the site for the first night and use
    # the hour value of "sunset" as the boundary value of the night range
    dark_start, dark_end = determine_darkness_times(site_code, dates[0])
    dark_start = dark_start - timedelta(hours=2)
    dark_end = dark_end + timedelta(hours=2)
    start_date = dates[0].replace(hour=dark_start.hour, minute=0, second=0, microsecond=0)
    if start_date >= dark_start:
        start_date = start_date - timedelta(days=1)
    end_date = dates[-1].replace(hour=dark_end.hour, minute=0, second=0, microsecond=0)
    if dates[-1] < end_date:
        if dbg: print("Subtracting 1 day from", end_date,dates[-1])
        end_date -= timedelta(days=1)
    if dbg: print(start_date, end_date)
    close_approach = dates[ephem_ca['delta'].argmin()]

    date = start_date
    while date < end_date:
        visible_dates.append(date.date())
        end_dt = date + timedelta(days=1)
        visible_ephem = ephem_ca[(ephem_ca['datetime'] >= date) & (ephem_ca['datetime'] < end_dt) & (ephem_ca['solar_presence'] != 'C')]
        hours_up = 0.0
        if len(visible_ephem) > 0:
            time_up = visible_ephem[-1]['datetime'] - visible_ephem[0]['datetime']
            hours_up = time_up.total_seconds()/3600.0
        hours_visible.append(hours_up)
        if dbg: print("{}->{}: {:.2f} hours".format(date.strftime("%Y-%m-%d %H:%M"), end_dt.strftime("%Y-%m-%d %H:%M"), hours_up))
        date += timedelta(days=1)

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10,8))
    fig.subplots_adjust(hspace=0.1)
    # Do bottom plot
    ax = axes[1]
    ax2 = ax.twinx()
    line_hours = ax.plot(visible_dates, hours_visible, 'k-')
    line_vmag = ax2.plot(dates, ephem_ca['V'], color= '#ff5900', linestyle='-.')
    y2lim = ax2.get_ylim()
    ax2.set_ylim(y2lim[1], y2lim[0])
    ylim = ax.get_ylim()
    ax.axvline(close_approach, color=ca_color)
    ax.text(close_approach, 0.1*ylim[1], "C/A", rotation=90, color=ca_color, horizontalalignment='left')

    # Do top plot
    ax = axes[0]
    line_rate = ax.plot(dates, ephem_ca['mean_rate'], color='b', linestyle='-')
    if add_altitude is True:
        upper_ax2 = ax.twinx()
        line_alt = upper_ax2.plot(dates, ephem_ca['EL'], color='g', linestyle=':')
        ylim = upper_ax2.get_ylim()
        upper_ax2.set_ylim(ylim[0], 90)
    ax.axvline(close_approach, color=ca_color)

    if title is None:
        title = "{} for {} to {}".format(first['targetname'], dates[0].strftime("%Y-%m-%d"), dates[-1].strftime("%Y-%m-%d"))
    fig.suptitle(title)
    ax.set_title('Visibility at ' + site_code)
    if add_altitude is False:
        ax.yaxis.set_ticks_position('both')
    else:
        ax.yaxis.set_ticks_position('left')
        upper_ax2.yaxis.set_ticks_position('right')
        upper_ax2.minorticks_on()
        upper_ax2.set_ylabel("Altitude")
    ax.set_ylabel('Rate ("/min)')
    ax.minorticks_on()

#    ax.legend(handles=(line_rate[0],), labels=('Rate',), loc='best', fontsize='x-small')

    # Back to bottom plot to set date labels
    ax = axes[1]
    ylim = ax.get_ylim()
    ax.set_ylim(0, ylim[1])
    start_year = dates[0].year
    end_year = dates[-1].year
    year = str(start_year)
    if start_year != end_year:
        year = "{}--{}".format(start_year, end_year)
    xlabel = "Date ({})".format(year)
    ax.set_xlabel(xlabel)
    num_days = dates[-1] - dates[0]
    day_interval = max(int(num_days.days / 5), 1)
    ax.get_xaxis().set_major_locator(mdates.DayLocator(interval=day_interval))
    ax.get_xaxis().set_major_formatter(mdates.DateFormatter("%m-%d"))

    y_units_label = 'Hours above $30^\circ$ altitude'
    ax.set_ylabel(y_units_label)
    ax2.set_ylabel('V magnitude')
    ax.legend(handles=(line_hours[0], line_vmag[0]), labels=('Hours up', 'V mag'), loc='best', fontsize='x-small')

    ax.minorticks_on()
    ax2.minorticks_on()
    ax.xaxis.set_ticks_position('both')
    ax.yaxis.set_ticks_position('left')
    ax2.yaxis.set_ticks_position('right')

    save_file = "{}_timeup_{}_{}-{}.png".format(first['targetname'].replace(" ", "_"), site_code, dates[0].strftime("%Y%m%d"), dates[-1].strftime("%Y%m%d"))
    fig.savefig(save_file, format='png')
    plt.close()

    return save_file