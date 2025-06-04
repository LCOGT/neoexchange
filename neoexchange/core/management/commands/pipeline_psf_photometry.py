import os
import tempfile
from datetime import datetime

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.time import Time
from astropy.table import Table
from django.core.management.base import BaseCommand, CommandError, CommandParser

from astropy.visualization import interval, ZScaleInterval

from core.models import Frame
from core.views import determine_images_and_catalogs
from core.blocksfind import get_ephem, ephem_interpolate
from photometrics.image_subs import get_saturate
from photometrics.external_codes import round_up_to_odd
from photometrics.catalog_subs import open_fits_catalog, trim_catalog
import matplotlib
matplotlib.use('TkAgg')
matplotlib.interactive(True)
from matplotlib import pyplot as plt
from trippy import psf, pill, psfStarChooser

class Command(BaseCommand):

    help = """Perform PSF photometry on a set of processed FITS frames.
    Steps include PSF star selection, Point Spread Function and Trailed Source Function
    model generation, photometry and aperture correction"""

    def add_arguments(self, parser: CommandParser) -> None:
        default_path = os.path.join(os.path.sep, 'apophis', 'eng', 'rocks')

        parser.add_argument('datadir', action="store", default=default_path, help='Path for processed data (e.g. %(default)s)')
        parser.add_argument('--keep-temp-dir', action="store_true", help='Whether to remove the temporary dir')
        parser.add_argument('--temp-dir', dest='temp_dir', action="store", help='Name of the temporary directory to use')
        parser.add_argument('--overwrite', default=False, action='store_true', help='Whether to overwrite existing PSF/output files')

    def handle(self, *args, **options):

        self.stdout.write("==== Pipeline processing PSF/Trailed photometry %s ====" % (datetime.now().strftime('%Y-%m-%d %H:%M')))

        datadir = os.path.expanduser(options['datadir'])
        datadir = os.path.join(datadir, '')
        self.stdout.write(f"datapath= {datadir}")

        # Get lists of NEOx processed images and catalogs
        fits_files, fits_catalogs = determine_images_and_catalogs(self, datadir, red_level='e92')
        if fits_files is None or fits_catalogs is None:
            raise CommandError(f"No e92 FITS files found in {datadir}")

        # If a --temp_dir option was given on the command line use that as our
        # directory, otherwise create a random directory in /tmp
        if options['temp_dir']:
            temp_dir = options['temp_dir']
            temp_dir = os.path.expanduser(temp_dir)
            if os.path.exists(temp_dir) is False:
                os.makedirs(temp_dir)
        else:
            temp_dir = tempfile.mkdtemp(prefix='tmp_neox_')

        keep_temp = ''
        if options['keep_temp_dir']: 
            keep_temp = ' (will keep)'
        self.stdout.write(f"Using {temp_dir} as temp dir{keep_temp}")

        # Find Block for first FITS file (probably should be the other way round -
        # get Block # from cmdline and determine Frames from that)
        first_file = os.path.basename(fits_files[0])
        try:
            frame = Frame.objects.get(filename=first_file, frametype=Frame.NEOX_RED_FRAMETYPE)
            obs_block = frame.block
        except Frame.DoesNotExist:
            raise CommandError(f"Frame entry for FITS file ({first_file}) not found")
        except Frame.MultipleObjectsReturned:
            raise CommandError(f"Multiple Frame entries for the same FITS file ({first_file}) found")
        self.stdout.write(f"\nPSF Photometry for: {obs_block.current_name()} Block ID: {obs_block.id} ReqNum: {obs_block.request_number} Site: {obs_block.site}\n")
        #f"Filter(s): {filter_string} Frames: {frames.earliest('midpoint')} -> {frames.latest('midpoint')} Num Frames: {num_frames}")

        ras, decs, xcenters, ycenters, aperture_sums, aperture_sum_errs, fwhms, zps, zp_errs, mags, magerrs, filters, flags, aperture_radii = [],[],[],[],[],[],[],[],[],[],[],[],[], []
        times = []
        paths_to_e92_frames = []
        ephem = get_ephem(obs_block)
        log_fh = open(os.path.join(datadir, 'LOG_trippy'), 'w')

        for fits_filepath, catalog_filepath in zip(fits_files, fits_catalogs):
            fits_file = os.path.basename(fits_filepath)
            catalog_file = os.path.basename(catalog_filepath)
            self.stdout.write(f"Running pipeline on {fits_file} image and {catalog_file} catalog")

            # Step 1: read FITS catalog
            cat_header, fits_catalog, cat_type = open_fits_catalog(catalog_filepath)
            # Turn the fitrec fits_table into an Astropy Table object
            full_catalog = Table(fits_catalog)

            with fits.open(fits_filepath) as hdulist:
                img_header = hdulist[0].header
                data = hdulist[0].data
                wcs = WCS(img_header)
                pixscale = proj_plane_pixel_scales(wcs).mean()*3600.0
                sat_level = get_saturate(img_header)
                exptime = img_header['EXPTIME']
                midpoint = Time(img_header['DATE-OBS']) + exptime*u.s / 2.0

            # Step 2: trim catalog to unsaturated, well separated stars 
            catalog = trim_catalog(full_catalog, max_saturate=sat_level)
            self.stdout.write(f"Lengths {len(full_catalog)}, {len(catalog)}")

            # Step 3: find target coords, rate and angle
            result_RA, result_DEC, extra_params = ephem_interpolate(midpoint, ephem, extra_quantity=['Sky_motion', 'Sky_mot_PA'])
            xp, yp = wcs.world_to_pixel_values(result_RA, result_DEC)
            xp = xp[0]
            yp = yp[0]
            dist = ((full_catalog['XWIN_IMAGE']-xp)**2+(full_catalog['YWIN_IMAGE']-yp)**2)**0.5
            args = np.argsort(dist)
            xt = full_catalog['XWIN_IMAGE'][args][0]
            yt = full_catalog['YWIN_IMAGE'][args][0]
            source_flag = full_catalog['FLAGS'][args][0]
            rate = extra_params['Sky_motion'][0] * img_header.get('TRACFRAC', 1.0) * 60.0 # Arcsec/hour
            angle = extra_params['Sky_mot_PA'][0] - 90.0
            self.stdout.write(f"Target at RA, Dec {result_RA[0]:8.4f} {result_DEC[0]:+8.4f} -> {xt:>8.3f},{yt:>8.3f} moving at {rate/60.0:.2f}\"/min PA {angle:.1f} Extractor flag={source_flag}")

            # Step 4: choose PSF stars (61/14 factor is from Notebook example)
            psf_filepath = os.path.join(datadir, fits_file.replace('e92.fits', 'psf.fits'))

            if os.path.exists(psf_filepath): # and options['overwrite'] is False:
                self.stdout.write(f"Loading PSF from {os.path.basename(psf_filepath)}")
                goodPSF = psf.modelPSF(restore=psf_filepath)
            else:
                psf_size = (61/14) * rate * (exptime / 3600.0) / pixscale
                psf_size = round_up_to_odd(psf_size)
                self.stdout.write(f"Calculated PSF size {psf_size}")

                starChooser=psfStarChooser.starChooser(data,
                                                    catalog['XWIN_IMAGE'],catalog['YWIN_IMAGE'],
                                                    catalog['FLUX_AUTO'],catalog['FLUXERR_AUTO'])
                (goodFits,goodMeds,goodSTDs) = starChooser(moffatWidth=30, moffatSNR=100, noVisualSelection=True, autoTrim=True,
                                                        xWidth=psf_size, yWidth=psf_size,
                                                        bgRadius=15, quickFit = False,
                                                        printStarInfo = False,
                                                        repFact=5, ftol=1.49012e-08)
                print(goodFits)
                print(goodMeds)
                print(fits_file, len(full_catalog), len(catalog), len(goodFits), file=log_fh)
                if len(goodFits) == 0 or len(goodMeds) == 0:
                    continue

                # Step 5: make PSF and TSF
                goodPSF = psf.modelPSF(np.arange(psf_size),np.arange(psf_size), alpha=goodMeds[2],beta=goodMeds[3],repFact=10)
                goodPSF.genLookupTable(data,goodFits[:,4], goodFits[:,5], verbose=False)

                zscale = ZScaleInterval()
                (z1, z2) = zscale.get_limits(goodPSF.lookupTable)
                normer = interval.ManualInterval(z1,z2)
                plt.imshow(normer(goodPSF.lookupTable))
                lut_filepath = os.path.join(datadir, fits_file.replace('e92.fits', 'lut.png'))
                plt.savefig(lut_filepath)

                fwhm = goodPSF.FWHM() ###this is the FWHM with lookuptable included
                goodPSF.line(rate,angle,exptime/3600.,pixScale=pixscale,useLookupTable=True)
                goodPSF.computeLineAperCorrFromTSF(psf.extent(0.1*fwhm,4*fwhm,10),
                                                                    l=(exptime/3600.)*rate/pixscale,a=angle,display=False,displayAperture=False)
                goodPSF.computeRoundAperCorrFromPSF(psf.extent(0.8*fwhm,4*fwhm,10),display=False,
                                                                    displayAperture=False,
                                                                    useLookupTable=True)
                # Step 6: store PSF
                goodPSF.psfStore(psf_filepath, psfV2=True)

            fwhm = goodPSF.FWHM() ###this is the FWHM with lookuptable included
            fwhm_moffat = goodPSF.FWHM(fromMoffatProfile=True) ###this is the pure moffat FWHM.

            self.stdout.write(f"Full width at half maximum {fwhm:5.3f}, pure Moffat {fwhm_moffat:5.3f} (in pix).")
            aperture_radius = fwhm*1.4


            roundAperCorr = goodPSF.roundAperCorr(aperture_radius)
            lineAperCorr = goodPSF.lineAperCorr(aperture_radius)
            print(lineAperCorr,roundAperCorr)

            # Step 7: pill/TSF photometry
            phot = pill.pillPhot(data, repFact=10)

            #get photometry
            #enableBGselection=True allows you to zoom in on a good background region in the aperture display window
            #trimBGhighPix is a sigma cut to get rid of the cosmic rays. They get marked as blue in the display window
            #background is selected inside the box and outside the skyRadius value
            #mode is th background mode selection. Options are median, mean, histMode (JJ's jjkmode technique),
            #fraserMode (ask me about it), gaussFit, and "smart".
            #Smart does a gaussian fit first, and if the gaussian fit value is discrepant compared to the expectation
            #from the background std, it resorts to the fraserMode. "smart" seems quite robust to nearby bright sources

            #examples of round sources
            # phot(goodFits[0][4], goodFits[0][5],radius=fwhm*1.1,l=0.0,a=0.0,
            #     skyRadius=4*fwhm, width=6*fwhm,
            #     zpt=img_header['L1ZP'],exptime=exptime,enableBGSelection=True,display=True,
            #     backupMode="fraserMode",trimBGHighPix=3.)

            #example of a trailed source
            phot(xt, yt, radius=aperture_radius, l=(exptime/3600.)*rate/pixscale, a=angle,
                 skyRadius=4*fwhm, width=6*fwhm,
                 zpt=img_header['L1ZP'], exptime=exptime, enableBGSelection=False, display=False,
                 backupMode="smart", trimBGHighPix=3.)

            phot.SNR(gain=img_header['GAIN'], readNoise=img_header['RDNOISE'], verbose=True)
            ras.append(result_RA[0])
            decs.append(result_DEC[0])
            xcenters.append(xt)
            ycenters.append(yt)
            aperture_sums.append(phot.sourceFlux)
            aperture_sum_errs.append(np.sqrt(phot.sourceFlux))
            fwhms.append(fwhm)
            zps.append(img_header['L1ZP'])
            zp_errs.append(img_header['L1ZPERR'])
            mags.append(phot.magnitude + lineAperCorr)
            magerrs.append(phot.dmagnitude)
            filters.append(img_header['l1filter'])
            aperture_radii.append(aperture_radius)
            flags.append(source_flag)
            times.append(midpoint)
            paths_to_e92_frames.append(fits_file)

        results_table = Table()
        results_table['path to frame'] = paths_to_e92_frames
        results_table['times'] = times
        results_table['filters'] = filters
        results_table['RA'] = ras
        results_table['DEC'] = decs
        results_table['xcenter'] = xcenters
        results_table['ycenter'] = ycenters
        results_table['aperture sum'] = aperture_sums
        results_table['aperture sum err'] = aperture_sum_errs
        results_table['FWHM'] = fwhms
        results_table['ZP'] = zps
        results_table['ZP_sig'] = zp_errs
        results_table['mag'] = mags
        results_table['magerr'] = magerrs
        results_table['flags'] = flags
        results_table['aperture radius'] = aperture_radii

        stringified_times = []
        mjd_times = []
        results_table.remove_column('times')
        for i in range (0, len(times)):
            stringified_times.append(f"{times[i]}")
            mjd_times.append(times[i].mjd)
        results_table['times'] = stringified_times
        results_table['times_mjd'] = mjd_times

        new_order = ['path to frame','times', 'times_mjd', 'filters','RA','DEC','xcenter','ycenter','aperture sum','aperture sum err','FWHM','ZP','ZP_sig','mag','magerr','flags','aperture radius']
        col_formats = ['%s', '%s', '%12.6f', '%2s', '%13.8f', '%+13.8f', '%8.3f', '%8.3f', '%.6f', '%.6f', '%6.3f', '%8.4f', '%6.4f', '%8.4f', '%6.4f', '%3d', '%.4f']

        results_table = results_table[new_order]
        formats_dict = dict(zip(new_order, col_formats))
        for col_name, col_format in formats_dict.items():
            results_table[col_name].format = col_format

        block_date_str = f"{obs_block.block_start}"[:-9]
        results_table_filename = os.path.join(datadir, f"lcogt_{obs_block.site}_{frame.instrument}_{block_date_str}_{obs_block.request_number}_trailphot.ecsv")
        results_table.write(results_table_filename, format='ascii.ecsv', formats=formats_dict, overwrite = options['overwrite'])
