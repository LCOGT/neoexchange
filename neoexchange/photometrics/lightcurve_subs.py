"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2021-2021 LCO

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
import os
import re
import warnings

import numpy as np
from astropy.table import Column, Table, unique
from astropy.time import Time
from astropy.wcs import FITSFixedWarning

from core.models import CatalogSources, Frame, SourceMeasurement
from photometrics.photometry_subs import ASTEROID_COLOR_TERMS

logger = logging.getLogger(__name__)

def read_photompipe_file(filepath):
    """Reads a photometry table file at <filepath> produced by the photometrypipeline and
    returns an Astropy Table.
    """

    table = None
    if os.path.exists(filepath):
        table = Table.read(filepath, format='ascii.commented_header')
        if len(table) >= 2 and table['filename'][0] == table['filename'][1]:
            logger.debug("Doubling detected")
            table = unique(table, keys='filename')
    return table

def extract_photompipe_aperradius(logfile):
    """Parse through a passed photometrypipeline log file to extract the
    aperture radius used.
    """

    aper_radius = None

    if os.path.exists(logfile):
        regex = r"aperture radius: (\d+.\d+)"
        with open(logfile, 'r') as f:
            for line in f.readlines():
                matches = re.search(regex, line)
                if matches:
                    if len(matches.groups()) == 1:
                        aper_radius = float(matches.group(1))
                    else:
                        logger.warning("Unexpected number of matches")
            if aper_radius is None:
                logger.info("Not found, trying alternative method")
                f.seek(0)
                regex = r"^pp_extract.*'aprad': (\d+.\d+)"
                for line in f.readlines():
                    matches = re.search(regex, line)
                    if matches:
                        if len(matches.groups()) == 1:
                            aper_radius = float(matches.group(1))
                        else:
                            logger.warning("Unexpected number of matches")
    return aper_radius

def create_table_from_srcmeasures(block):
    """Creates an AstroPy table (of the format suitable for write_dartformat_file()) from
    the SourceMeasurements associated with Block <block>"""

    col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad']
    dtypes = ('<U36', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<U7', '<i8', '<f8')
    table = Table(names=col_names, dtype=dtypes)

    sources = SourceMeasurement.objects.filter(frame__block=block, frame__frametype__in=[Frame.NEOX_RED_FRAMETYPE, Frame.NEOX_SUB_FRAMETYPE]).order_by('frame__midpoint')

    warnings.simplefilter('ignore', FITSFixedWarning)

    tolerance = 0.5 / 3600.0
    mag_tolerance = 0.01
    for i, src in enumerate(sources):
        t = Time(src.frame.midpoint)
        catsrc = CatalogSources.objects.filter(frame=src.frame, obs_ra__range=(src.obs_ra-tolerance, src.obs_ra+tolerance),\
            obs_dec__range=(src.obs_dec-tolerance, src.obs_dec+tolerance),\
            obs_mag__range=(src.obs_mag-mag_tolerance, src.obs_mag+mag_tolerance))
        flags = 0
        if catsrc.count() == 1:
            flags = catsrc[0].flags
        else:
            logger.warning(f"Unexpected number of CatalogSources ({catsrc.count()}) found for {src.frame.filename}")
        # print(i, src.frame.filename, t.jd, src.obs_mag, src.err_obs_mag,
               # src.frame.zeropoint,\
               # src.frame.zeropoint_err,\
               # src.obs_mag-src.frame.zeropoint,\
               # src.err_obs_mag,\
               # flags, src.aperture_size)
        row = [src.frame.filename, t.jd, src.obs_mag, \
               np.sqrt(src.err_obs_mag**2 + src.frame.zeropoint_err**2),
               src.frame.zeropoint,\
               src.frame.zeropoint_err,\
               src.obs_mag-src.frame.zeropoint,\
               src.err_obs_mag,\
               src.frame.filter,
               flags, src.aperture_size_pixels]
        table.add_row(row)

    return table

def write_dartformat_file(table, filepath, aprad=0.0, overwrite=False):
    """Writes out the passed Astropy <table > in "DART lightcurve format" to the
    given <filepath>"""

    output_col_names = ['file', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'inst_sig', 'filter', 'SExtractor_flag', 'aprad']
    input_col_names = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad']
    def_fmt = '%.4f'
    formatters = {  'file' : '%-36.36s', 'julian_date' : '%15.7f', 'mag' : def_fmt, 'sig' : def_fmt,
                    'ZP' : def_fmt, 'ZP_sig' : def_fmt, 'inst_mag' : def_fmt, 'inst_sig' : def_fmt,
                    'aprad' : '%5.2f'
                 }
#    col_starts = (1, 39, 55, 65, 72, 82, 90, 100, 110, 118, 135)
#    col_ends = (37, 54, 63, 71, 80, 88, 98, 108, 116, 133, 140)

    # Create directory path if it doesn't exist
    filepath_dir = os.path.dirname(filepath)
    if os.path.exists(filepath_dir) is False:
        os.makedirs(filepath_dir)

    # Replace truncated '.lda' in filename with real name.
    # Also add a column for aperture radius
    new_names = [x.replace('.ldac','.fits').replace('.lda','.fits').replace('e91','e92') for x in table['filename']]
    new_table = table.copy()
    new_table.replace_column('filename', new_names)
    if 'aprad' not in new_table.colnames:
        aprad_column = Column(np.full(len(new_table), aprad), name='aprad')
        new_table.add_column(aprad_column)
    new_table[input_col_names].write(filepath, format='ascii.fixed_width', names=output_col_names,
        comment=False, delimiter='', formats=formatters, overwrite=overwrite)

    return


# Observed filter name -> PS1 passband key in ASTEROID_COLOR_TERMS. MuSCAT z_s has no
# tabulated colour; PS1 z (818-922 nm) is the closest analogue.
FILTER_TO_PS1_PASSBAND = {'gp': 'g', 'rp': 'r', 'ip': 'i', 'zp': 'z', 'zs': 'z', 'w': 'w', 'Y': 'Y'}

DART_TABLE_COLUMNS = ['filename', 'julian_date', 'mag', 'sig', 'ZP', 'ZP_sig', 'inst_mag', 'in_sig', '[7]', '[8]', 'aprad']


def expected_color_offsets(ref_filter='rp', taxonomy='S'):
    """Returns a dict of the expected magnitude offset (<band> - <ref_filter>) for each
    filter in FILTER_TO_PS1_PASSBAND, for an asteroid of the given <taxonomy>
    (a key of ASTEROID_COLOR_TERMS: SOLAR, MEAN, S, C, Q, X, D, NEO).
    Filters without a tabulated colour, or an unknown taxonomy, are left out."""

    color_terms = ASTEROID_COLOR_TERMS.get(taxonomy.upper(), {})
    ref_term = color_terms.get(FILTER_TO_PS1_PASSBAND.get(ref_filter))
    offsets = {}
    if ref_term is None:
        return offsets
    for obs_filter, passband in FILTER_TO_PS1_PASSBAND.items():
        band_term = color_terms.get(passband)
        if band_term is not None:
            # mag_band - mag_ref = (V - ref) - (V - band)
            offsets[obs_filter] = round(ref_term - band_term, 4)
    return offsets


def _clean_aper_photometry_table(phot_table):
    """Returns a copy of a perform_aper_photometry() table with the numeric columns
    coerced to float, a `julian_date` column, a `filename` column and the unusable
    rows removed (the ""-filled rows written when a frame could not be measured,
    non-finite or non-positive fluxes, and ZP < -90). The number of rows removed is
    returned alongside."""

    numeric_cols = ['aperture sum', 'aperture sum err', 'ZP', 'ZP_sig', 'mag', 'magerr', 'aperture radius pix']
    table = phot_table.copy()
    for col in numeric_cols:
        values = []
        for value in table[col]:
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                values.append(np.nan)
        table.replace_column(col, Column(values, name=col, dtype=float))
    times = []
    for value in table['times']:
        try:
            times.append(Time(value).jd)
        except (TypeError, ValueError):
            times.append(np.nan)
    table['julian_date'] = Column(times, dtype=float)
    table['filename'] = [os.path.basename(str(path)) for path in table['path to frame']]
    table['filters'] = [str(obs_filter) for obs_filter in table['filters']]

    good = np.isfinite(table['julian_date']) & np.isfinite(table['mag']) & np.isfinite(table['magerr']) \
        & np.isfinite(table['aperture sum']) & (table['aperture sum'] > 0) & (table['ZP'] > -90)
    num_removed = int((~good).sum())
    return table[good], num_removed


def _running_median(values, width=7):
    """Median of the up-to-<width> neighbours of each point, excluding the point itself
    (so a point's own value does not shrink its residual)."""
    out = np.empty(len(values))
    half = width // 2
    for i in range(len(values)):
        neighbours = np.concatenate([values[max(0, i - half):i], values[i + 1:i + half + 1]])
        out[i] = np.nanmedian(neighbours) if len(neighbours) else values[i]
    return out


def combine_simultaneous_bands(phot_table, ref_filter='rp', color_priors=None, taxonomy='S',
                               match_tolerance=None, outlier_sigma=4.0, prior_tolerance=0.1, min_bands=1):
    """Combines the simultaneous multi-band aperture photometry in <phot_table> (the
    table returned by perform_aper_photometry(), or that table read back from its
    ECSV file; all filters of the Block in one table) into a single lightcurve on
    the <ref_filter> magnitude scale.

    Each band's points are shifted by a per-night colour offset (<band> - <ref_filter>),
    fitted as the median pairwise difference between simultaneous frames of that band
    and the reference band, and compared with the prior from <color_priors> (a dict of
    offsets) or, if None, expected_color_offsets(<ref_filter>, <taxonomy>). A band whose
    fitted offset differs from its prior by more than <prior_tolerance> mag is flagged
    but the fitted offset is still used. Frames of the other bands are matched to the
    reference-band frames by midpoint time within <match_tolerance> (days; default half
    the median spacing of the reference frames); the closest frame wins when two land on
    the same epoch. Per-band errors are sqrt(magerr^2 + ZP_sig^2); points further than
    <outlier_sigma> * robust sigma from a 7-point running median of their band are
    excluded. The combined magnitude per epoch is the inverse-variance weighted mean of
    the shifted bands; epochs with fewer than <min_bands> usable bands are dropped.

    Returns (combined, per_band, info):
      combined: Table of julian_date, mag, sig, nbands, bands, chi2_bands plus the
        columns write_dartformat_file() needs (filename, ZP, ZP_sig of the reference-band
        frame at that epoch or the earliest frame used, inst_mag, in_sig, [7]=ref_filter,
        [8]=0, aprad). .meta holds ref_filter, offsets, priors, taxonomy, match_tolerance_s,
        n_epochs, p2p_scatter and warnings.
      per_band: dict of filter -> Table(julian_date, filename, mag, err, flag, offset_applied, epoch)
        with epoch = -1 for unmatched frames.
      info: dict with per-band counts (used/flagged/unmatched), offsets, priors,
        prior_mismatch flags, num_rows_removed and warnings."""

    table, num_removed = _clean_aper_photometry_table(phot_table)
    filters = [str(obs_filter) for obs_filter in dict.fromkeys(table['filters'])]
    if ref_filter not in filters:
        raise ValueError(f"Reference filter {ref_filter} not present in table (filters: {filters})")

    if color_priors is None:
        priors = expected_color_offsets(ref_filter, taxonomy)
    else:
        priors = dict(color_priors)
    priors[ref_filter] = 0.0

    per_band = {}
    for obs_filter in filters:
        band = table[table['filters'] == obs_filter]
        band.sort('julian_date')
        mag = np.array(band['mag'])
        err = np.sqrt(np.array(band['magerr'])**2 + np.array(band['ZP_sig'])**2)
        residual = mag - _running_median(mag)
        robust_sigma = 1.4826 * np.nanmedian(np.abs(residual))
        flag = np.abs(residual) > outlier_sigma * robust_sigma if robust_sigma > 0 else np.zeros(len(mag), bool)
        per_band[obs_filter] = Table({'julian_date': band['julian_date'], 'filename': band['filename'],
                                      'mag': mag, 'err': err, 'flag': flag,
                                      'offset_applied': np.zeros(len(mag)), 'epoch': np.full(len(mag), -1),
                                      'ZP': band['ZP'], 'ZP_sig': band['ZP_sig'],
                                      'aprad': band['aperture radius pix']})

    ref = per_band[ref_filter]
    epoch_jds = np.array(ref['julian_date'])
    ref['epoch'] = np.arange(len(ref))
    if match_tolerance is None:
        match_tolerance = 0.5 * np.median(np.diff(epoch_jds)) if len(epoch_jds) > 1 else 0.0

    # Assign every other band's frames to the nearest reference epoch, closest frame winning
    unmatched = {ref_filter: 0}
    for obs_filter in filters:
        if obs_filter == ref_filter:
            continue
        band = per_band[obs_filter]
        nearest = np.array([np.argmin(np.abs(epoch_jds - jd)) for jd in band['julian_date']])
        delta = np.abs(np.array(band['julian_date']) - epoch_jds[nearest])
        epoch = np.where(delta <= match_tolerance, nearest, -1)
        for epoch_num in set(epoch[epoch >= 0]):
            contenders = np.where(epoch == epoch_num)[0]
            if len(contenders) > 1:
                loser = contenders[contenders != contenders[np.argmin(delta[contenders])]]
                epoch[loser] = -1
        band['epoch'] = epoch

    # Frames with no reference-band frame nearby (reference frame unmeasurable, or
    # cameras drifted apart) form extra epochs of their own so the data are not lost
    extra_jds = []
    stragglers = sorted((jd, obs_filter, i) for obs_filter in filters if obs_filter != ref_filter
                        for i, (jd, e) in enumerate(zip(per_band[obs_filter]['julian_date'], per_band[obs_filter]['epoch'])) if e < 0)
    extra_members = []
    for jd, obs_filter, i in stragglers:
        target = None
        if extra_jds:
            k = int(np.argmin(np.abs(np.array(extra_jds) - jd)))
            if abs(extra_jds[k] - jd) <= match_tolerance and obs_filter not in extra_members[k]:
                target = k
        if target is None:
            extra_jds.append(jd)
            extra_members.append(set())
            target = len(extra_jds) - 1
        extra_members[target].add(obs_filter)
        per_band[obs_filter]['epoch'][i] = len(epoch_jds) + target
    epoch_jds = np.concatenate([epoch_jds, np.array(extra_jds)]) if extra_jds else epoch_jds
    for obs_filter in filters:
        unmatched[obs_filter] = int((per_band[obs_filter]['epoch'] < 0).sum())

    # Colour offsets from the pairwise differences with the reference band
    offsets = {ref_filter: 0.0}
    prior_mismatch = {}
    warnings_list = []
    ref_ok = ~np.array(ref['flag'])
    ref_mag_by_epoch = {int(e): m for e, m, ok in zip(ref['epoch'], ref['mag'], ref_ok) if ok}
    for obs_filter in filters:
        if obs_filter == ref_filter:
            continue
        band = per_band[obs_filter]
        diffs = [m - ref_mag_by_epoch[int(e)] for e, m, flagged in zip(band['epoch'], band['mag'], band['flag'])
                 if not flagged and int(e) in ref_mag_by_epoch]
        if len(diffs) == 0:
            offsets[obs_filter] = np.nan
            warnings_list.append(f"{obs_filter}: no frames simultaneous with {ref_filter}; band not used")
            continue
        offsets[obs_filter] = float(np.median(diffs))
        prior = priors.get(obs_filter)
        if prior is None:
            warnings_list.append(f"{obs_filter}: no colour prior available; fitted offset {offsets[obs_filter]:+.3f} unchecked")
        else:
            prior_mismatch[obs_filter] = abs(offsets[obs_filter] - prior) > prior_tolerance
            if prior_mismatch[obs_filter]:
                warnings_list.append(f"{obs_filter}: fitted offset {offsets[obs_filter]:+.3f} differs from "
                                     f"prior {prior:+.3f} by more than {prior_tolerance} mag")
    for obs_filter, band in per_band.items():
        band['offset_applied'] = np.full(len(band), offsets[obs_filter])

    # Inverse-variance weighted mean per epoch
    rows = []
    num_used = {obs_filter: 0 for obs_filter in filters}
    for epoch_num in range(len(epoch_jds)):
        mags, weights, used, jds, frames = [], [], [], [], []
        for obs_filter in filters:
            band = per_band[obs_filter]
            if not np.isfinite(offsets[obs_filter]):
                continue
            idx = np.where((band['epoch'] == epoch_num) & ~band['flag'])[0]
            if len(idx) == 0:
                continue
            i = idx[0]
            mags.append(band['mag'][i] - offsets[obs_filter])
            weights.append(1.0 / band['err'][i]**2)
            used.append(obs_filter)
            jds.append(band['julian_date'][i])
            frames.append((obs_filter != ref_filter, band['julian_date'][i], band['filename'][i], band['ZP'][i], band['ZP_sig'][i], band['aprad'][i]))
        if len(mags) < max(min_bands, 1):
            continue
        for used_filter in used:
            num_used[used_filter] += 1
        mags, weights = np.array(mags), np.array(weights)
        mean = np.sum(weights * mags) / np.sum(weights)
        sig = 1.0 / np.sqrt(np.sum(weights))
        chi2 = np.sum(weights * (mags - mean)**2) / (len(mags) - 1) if len(mags) > 1 else 0.0
        _, _, filename, zp, zp_sig, aprad = min(frames)  # reference-band frame first, else earliest
        rows.append({'julian_date': float(np.mean(jds)), 'mag': mean, 'sig': sig, 'nbands': len(mags),
                     'bands': ''.join(obs_filter[0] for obs_filter in used), 'chi2_bands': chi2, 'filename': filename, 'ZP': zp, 'ZP_sig': zp_sig,
                     'inst_mag': mean - zp, 'in_sig': sig, '[7]': ref_filter, '[8]': 0, 'aprad': aprad})

    combined_cols = ['julian_date', 'mag', 'sig', 'nbands', 'bands', 'chi2_bands', 'filename'] + DART_TABLE_COLUMNS[4:]
    combined = Table(rows=rows, names=combined_cols) if rows else Table(names=combined_cols)
    combined.sort('julian_date')
    p2p_scatter = np.nan
    if len(combined) > 2:
        deltas = np.diff(combined['mag'])
        p2p_scatter = float(1.4826 * np.median(np.abs(deltas - np.median(deltas))) / np.sqrt(2.0))
    combined.meta = {'ref_filter': ref_filter, 'offsets': offsets, 'priors': priors, 'taxonomy': taxonomy,
                     'match_tolerance_s': float(match_tolerance * 86400.0), 'n_epochs': len(combined),
                     'p2p_scatter': p2p_scatter, 'warnings': warnings_list}
    info = {'filters': filters, 'offsets': offsets, 'priors': priors, 'prior_mismatch': prior_mismatch,
            'counts': {obs_filter: {'used': num_used[obs_filter],
                                    'flagged': int(band['flag'].sum()),
                                    'unmatched': unmatched[obs_filter]} for obs_filter, band in per_band.items()},
            'unmatched': unmatched, 'num_rows_removed': num_removed, 'match_tolerance_s': combined.meta['match_tolerance_s'],
            'p2p_scatter': p2p_scatter, 'warnings': warnings_list}
    return combined, per_band, info


def bin_lightcurve(table, nbin=2, mag_col='mag', sig_col='sig', time_col='julian_date'):
    """Bins consecutive groups of <nbin> rows of <table> by inverse-variance weighted mean.
    An incomplete trailing group is dropped. `nbands` is summed and `bands` joined if present."""

    rows = []
    for start in range(0, len(table) - nbin + 1, nbin):
        chunk = table[start:start + nbin]
        weights = 1.0 / np.array(chunk[sig_col])**2
        row = {time_col: float(np.mean(chunk[time_col])),
               mag_col: float(np.sum(weights * chunk[mag_col]) / np.sum(weights)),
               sig_col: float(1.0 / np.sqrt(np.sum(weights)))}
        if 'nbands' in table.colnames:
            row['nbands'] = int(np.sum(chunk['nbands']))
        if 'bands' in table.colnames:
            row['bands'] = ''.join(chunk['bands'])
        rows.append(row)
    names = [time_col, mag_col, sig_col] + [c for c in ('nbands', 'bands') if c in table.colnames]
    return Table(rows=rows, names=names) if rows else Table(names=names)


def aper_table_to_dart_table(phot_table, obs_filter):
    """Extracts the rows of <phot_table> (a perform_aper_photometry() table) taken in
    <obs_filter> as a table with the columns write_dartformat_file() expects. `sig` is
    the magnitude error with the zeropoint error added in quadrature; `in_sig` is the
    instrumental error alone."""

    table, _ = _clean_aper_photometry_table(phot_table)
    band = table[table['filters'] == obs_filter]
    band.sort('julian_date')
    sig = np.sqrt(np.array(band['magerr'])**2 + np.array(band['ZP_sig'])**2)
    return Table([band['filename'], band['julian_date'], band['mag'], sig, band['ZP'], band['ZP_sig'],
                  band['mag'] - band['ZP'], band['magerr'], [obs_filter] * len(band), np.zeros(len(band), int),
                  band['aperture radius pix']], names=DART_TABLE_COLUMNS)

def write_photompipe_file(table, filepath):
    """Writes out the passed Astropy <table > in "photometrypipeline lightcurve format" to the
    given <filepath>"""
    with open(filepath,  'w') as out_fh:
        # Write header
        out_fh.write('#                           filename     julian_date      ' +
                   'mag    sig     source_ra    source_dec   [1]   [2]   ' +
                   '[3]   [4]    [5]       ZP ZP_sig inst_mag ' +
                   'in_sig               [6] [7] [8]    [9]          [10] ' +
                   'FWHM"\n')

        # Iterate over rows
        for row in table:
            out_fh.write(('%35.35s ' % row['filename'].replace(' ', '_')) +
                       ('%15.7f ' % row['julian_date']) +
                       ('%8.4f ' % row['mag']) +
                       ('%6.4f ' % row['sig']) +
                       ('%13.8f ' % row['source_ra']) +
                       ('%+13.8f ' % row['source_dec']) +
                       ('%5.2f ' % row['[1]']) +
                       ('%5.2f ' % row['[2]']) +
                       ('%5.2f ' % row['[3]']) +
                       ('%5.2f ' % row['[4]']) +
                       ('%5.2f ' % row['[5]']) +
                       ('%8.4f ' % row['ZP']) +
                       ('%6.4f ' % row['ZP_sig']) +
                       ('%8.4f ' % row['inst_mag']) +
                       ('%6.4f ' % row['in_sig']) +
                       ('%s ' % row['[6]']) +
                       ('%s ' % row['[7]']) +
                       ('%3d ' % row['[8]']) +
                       ('%s' % row['[9]']) +
                       ('%10s ' % row['[10]']) +
                       ('%4.2f\n' % row['FWHM"']))

        # Write footer
        out_fh.writelines('#\n# [1]: predicted_RA - source_RA [arcsec]\n' +
                        '# [2]: predicted_Dec - source_Dec [arcsec]\n' +
                        '# [3,4]: manual target offsets in RA and DEC ' +
                        '[arcsec]\n' +
                        '# [5]: exposure time (s)\n' +
                        '# [6]: photometric catalog\n' +
                        '# [7]: photometric band\n' +
                        '# [8]: Source Extractor flag\n' +
                        '# [9]: telescope/instrument\n' +
                        '# [10]: photometry method\n')
    return
