#!/usr/bin/env python3


#import packages
import os
import sys
from pathlib import Path
import shutil
sys.path.insert(0, '/home/mwalker/git/neoexchange/neoexchange') #point to top of file path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neox.settings')
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
import argparse

import django
django.setup()
from django.conf import settings

import pandas as pd
import numpy as np
from IPython.display import display
import matplotlib.pyplot as plt


#astropy tools
from astropy.table import vstack
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import ZScaleInterval
from photutils import DAOStarFinder
from astropy.stats import sigma_clipped_stats
from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry, ApertureStats  #investigate documentatiom for this
from astropy.time import Time
from datetime import datetime
from photutils.centroids import centroid_com
from astropy.nddata import Cutout2D

#Django modeling
from core.models import Body #Body Class
from core.models.sources import StaticSource #static class
from core.models.blocks import Block  #Block class
from core.models.frame import Frame 

os.chdir("/home/mwalker/git/neoexchange/neoexchange") #temp fix for json issue
from core.views import summarize_block_quality
from core.views import GuideMovie
from core.plots import generalized_fwhm_plotter, generalized_zeropoint_plotter  #get pngs for fwhm and zp to analyze
from astrometrics.ephem_subs import horizons_ephem





class Table_Generator:

    def __init__(self, body_name, source_type_field):
        self.name = body_name  #body name is string: '65803 for didymos
        self.field_name = source_type_field #ex: REFERENCE
        self.yr = '2026'
        self.asteroid_name = None
        self.field= None
        self.get_file_name()

    def get_file_name(self):
        """ Get Body, Field Query and Reference Field name
        Input: Instance Attributes
        Output: 
        
        """
    

        #reference field is an attribute from the source_type attribute, gets attached via django
        self.source_type = getattr(StaticSource, f"{self.field_name}_FIELD")
        self.frame_type = getattr(Frame, f"{self.field_name}_FRAMETYPE")
        self.asteroid_name = Body.objects.get(name = self.name)
        self.field =  StaticSource.objects.filter(
            source_type = self.source_type, 
            name__contains = self.yr
                        ) 
        
    def gen_table(self):
        """Objective: Generate table with:
            -field name
            -ra and dec
            -number of blocks
            -obs blocks
            -num of referrence frames
            
            
            Inputs:
            
            Outputs: 
            Data Table (pd.DataFrame): table with defined information
            
            """
        

        # Get ra, dec, name

        self.ra = []
        self.dec = []
        self.ind_field_names = []
        for f in self.field:
            self.ra.append(f.ra)
            self.dec.append(f.dec)
            self.ind_field_names.append(f.name)


        #get num of blocks and num of blocks observed
        self.num_blocks = []
        self.num_blocks_obs = []
        self.ref_num = []

        for f in self.field:
            blocks = list(Block.objects.filter(calibsource = f))
            self.num_blocks.append(len(blocks))
            
            ref_num = 0
            obs_num = 0

            for b in blocks:
                if b.num_observed is not None:
                    obs_num += b.num_observed

                    #count ref frames
                    frames = Frame.objects.filter(block = b, frametype =  self.frame_type).count()     #---self.ref_frame= REFERENCE_FRAMETYPE    
                    ref_num += frames
            self.num_blocks_obs.append(obs_num)
            self.ref_num.append(ref_num)

        #Build Data Table
        table = pd.DataFrame({
            'Field name': self.ind_field_names ,
            "RA": self.ra,
            "DEC": self.dec,
            "Blocks": self.num_blocks,
            "obs.blocks": self.num_blocks_obs,
            "# Ref Frames": self.ref_num,
        })
        return table

    def ref_image_quality(self, out_put_dir = None):
        """ 
        Objective: Obtain Table of statistics of the attribute: self.field_type
            --Also: Add in a few basic filters before conducting analysis of the frames
                
            Inputs: 
            self ():
            out_put_dir for excel spreadsheet (str):
                
            Returns: 
            Reference Frame Quality Data Table (astropy.table.Table): Table containing
                -frame file name
                -mid point
                -filter
                -zp
                -zp error
                -FWHM
                -Fit RMS : diff between observe and prediction positions
                -num of fitted stars
                -XY Contrast
                -AS Contrast
                -num of ref stars
                -Field Name
                - Block #
                
        """
        

        astro_quality_table = []

        for f in self.field:
            obs_blocks = Block.objects.filter(calibsource = f, num_observed__gte =1)
            
            for b in obs_blocks:
            
                dataroot = os.path.join(settings.DATA_ROOT, 'Hera', b.get_blockdayobs)
                t =summarize_block_quality(dataroot, b)
                
                if t is not None:
                    t["Field Name"] = np.full(len(t), f.name)
                    t["# block"] = np.full(len(t), b.id)
                    astro_quality_table.append(t)

        master_astro_qual_table = vstack(astro_quality_table)

        #organize by smallest to largst rms 
        #Low RMS means the observed and predicted positions are close
        #next: get rid of -99's as those indicate no valid read on fit
        #Also only keep values with fwhm < 3
        # & and indicator 
        #mask &= <condition --- True only if mask AND condition are true
        # | is the or operator

        #intially start as all true 

        master_astro_qual_table.sort('Fit RMS')
        master_astro_qual_table["Fit RMS"]

        #intially start as all true 
        mask = np.ones(len(master_astro_qual_table), dtype=bool)

        for col in master_astro_qual_table.colnames:
            mask &= (master_astro_qual_table[col] != -99.0) #constrcut boolean mask where -99 = FALSE

        master_astro_qual_table = master_astro_qual_table[mask] #table with "TRUE" rows remain

        m_a_q_table_reduced_1 = master_astro_qual_table[
            (master_astro_qual_table["FWHM"] < 2.8) & 
            (master_astro_qual_table["ZP err"] < 0.28)]

        self.table = m_a_q_table_reduced_1
        #save as .xlsx
        
        if out_put_dir is not None:
        
            out_put_dir_ = os.path.join(out_put_dir, "reference_image_quality.xlsx" )
            data_ref_images = m_a_q_table_reduced_1.to_pandas()
            data_ref_images.to_excel(out_put_dir_ , index = False)

        return m_a_q_table_reduced_1


    def fwhm_zp_plot(self, out_put_dir_fwhm, out_put_dir_zp,):
        """Objective: Generate FWHM and RMS plots for the reference frames
            Inputs:
            self
            out_put_dir (str): directory to save plots
            
            Ouputs:
            FWHM and RMS plots (png): saved in out_put_dir
            """
        
        #file_paths

        file_p_fwhm = out_put_dir_fwhm
        file_p_zp = out_put_dir_zp


        #select fields and block numbers in lieu of Static.objects.filter( source_type = StaticSource.REFERENCE_FIELD, name__contains__ ='COJ 2026 Field)
        #already filtered out files
        table = self.ref_image_quality()
        coj_fields = table["Field Name"]

        print(type(table))

        if hasattr(table, "columns"):
            print(table.columns)
        else:
            print(table.colnames)
        block_nums_w_ref = table["# block"]

        #We will filter out by field and by block
        fields_plot = [StaticSource.objects.get(name = name) for name in coj_fields] #need Query object
        blocks_plot = [Block.objects.get(pk =block_id) for block_id in block_nums_w_ref] # gte list of ind blocks

        #plot fwhm and zp with remaining files

        generalized_fwhm_plotter(fields_plot,['rp'],['tomato'], file_p_fwhm, False, True)   #indi_block_plots = False, Night_sky_plot = True 
        generalized_zeropoint_plotter(fields_plot, ["rp"], ["tomato"], file_p_zp, False, True)


        #now do blocks 
        block_fp_zp = os.path.join(out_put_dir_zp, "filt_rp_tom_ind_blocks/")
        block_fp_fwhm = os.path.join(out_put_dir_fwhm, "filt_rp_tom_ind_blocks/")

        generalized_fwhm_plotter(blocks_plot,["rp"],["tomato"],block_fp_fwhm,True,True,)
        generalized_zeropoint_plotter(blocks_plot,["rp"],["tomato"],block_fp_zp,True,True,)





###NEXT CLASS: photometry + further analysis of data  ###

class Table_analysis(Table_Generator):

    def __init__(self, body_name, source_type_field):
        super().__init__(body_name, source_type_field)    #intializes parent class: Table_Generator    

        self.table = self.ref_image_quality()

    def analyze(self, out_dir =None, input_dir = None, Display = True):
        """Objective:
        
            Inputs:
            out_dir (str): Optional output directory for graphs and images
            input_dir (str): Optional input directory with table generated with method gen_table()



            Returns:
            Analysis Table (pd.Dataframe): FHWM, ZP, ETC
        
        """

        #Fix columns to Data
        if input_dir is None:
            if hasattr(self.table, "to_pandas"):
                self.table = self.table.to_pandas()
            self.table.columns = self.table.columns.str.rstrip()
            print(self.table.columns)
                   
        else:
            file_path_cv = input_dir
            self.table = pd.read_csv(file_path_cv)
            self.table.columns = self.table.columns.str.rstrip()
            
            print(self.table.columns)



        #calculae difference in zp mag for same field and same block
        #Find range of fwhm and zp for each field and block
        #print percetage of fitted stars to reference stars for each field and block
        #find max/mion RMS for each field and block ---because some fields obs by multiple blocks


        field_names = self.table["Field Name"].unique()
        self.table["FWHM"] = pd.to_numeric(self.table["FWHM"], errors = 'coerce')
        self.table["ZP"] = pd.to_numeric(self.table["ZP"], errors = 'coerce')
        self.table["Fit RMS"] = pd.to_numeric(self.table["Fit RMS"], errors = 'coerce')
        self.table["ZP err"] = pd.to_numeric(self.table["ZP err"], errors = 'coerce')

        percentage_fit_stars_list = []
        zp_range = []
        rms_range = []
        fwhm_range = []
        Field_names = []

        for f in field_names:
            Field_name = self.table[self.table["Field Name"] == f]
            blocks = Field_name["# block"].unique()  #gets unique blocks obs for field

            for b in blocks:
                Block_name = Field_name[Field_name["# block"] == b]
                fwhm_r = Block_name["FWHM"].max() - Block_name["FWHM"].min()
                zp_r = Block_name["ZP"].max() - Block_name["ZP"].min()
                rms_r = Block_name["Fit RMS"].max() - Block_name["Fit RMS"].min()
                num_ref_stars = Block_name["num ref stars"].max()
                num_fit_stars = Block_name["num fit stars"].max()
                percentage_fit_stars = (num_fit_stars / num_ref_stars) * 100

                print("-------------------------------")
                print(f"Field: {f}, Block: {b}")
                print(f"FWHM Range: {fwhm_r}")
                print(f"ZP Range: {zp_r}")
                print(f"RMS Range: {rms_r}")
                print(f"Percentage of Fitted Stars: {percentage_fit_stars}%")
                print("-----------------------------------")

                percentage_fit_stars_list.append(percentage_fit_stars)
                zp_range.append(zp_r)
                rms_range.append(rms_r)
                fwhm_range.append(fwhm_r)
                Field_names.append(f)

                #low zero point = clouds

        new_dict = {"field_names": Field_names, 
                    "zp_range": zp_range, 
                    "rms_range": rms_range, 
                    "fwhm_range": fwhm_range, 
                    "percentage_fit_stars": percentage_fit_stars_list}

        self.new_df = pd.DataFrame(new_dict)

        if Display is True:
            display(self.new_df)

    def Graph_analysis(self):
        """
        Objective: Generate graphs of fwhm, zp, number of stars and find correlations.
        
        
        """

         #low zero point = clouds

        #trends with filter ??
        #pull shape of fit --- 


        #make some plots and histograms to find correlations between fwhm, zp, rms, and percentage of fitted stars
        if not hasattr(self, "new_df"):
            raise RuntimeError(
                "Run Analysis() method prior to calling Graph_analysis()"
            )


        x_fwhm = self.new_df["fwhm_range"]
        y_zp = self.new_df["zp_range"]

        y_rms = self.new_df["rms_range"]
        y_percentage_fit_stars = self.new_df["percentage_fit_stars"]

        x_zp = self.new_df["zp_range"]

        x_num_stars = self.new_df["percentage_fit_stars"]
        #plot fwhm vs zp


        fig, axs = plt.subplots(2, 3, figsize=(10, 10))
        axs[0, 0].scatter(x_fwhm, y_zp)
        axs[0, 0].set_xlabel("FWHM Range")
        axs[0, 0].set_ylabel("ZP Range")
        axs[0, 0].set_title("FWHM Range vs ZP Range")
        axs[0, 0].grid()

        #plot fwhm vs rms
        axs[0, 1].scatter(x_fwhm, y_rms)
        axs[0, 1].set_xlabel("FWHM Range")
        axs[0, 1].set_ylabel("RMS Range")
        axs[0, 1].set_title("FWHM Range vs RMS Range")
        axs[0, 1].grid()


        #plot fwhm vs percentage of fitted stars
        axs[1, 0].scatter(x_fwhm, y_percentage_fit_stars)
        axs[1, 0].set_xlabel("FWHM Range")
        axs[1, 0].set_ylabel("Percentage of Fitted Stars")
        axs[1, 0].set_title("FWHM Range vs Percentage of Fitted Stars")
        axs[1, 0].grid()

        axs[1, 1].scatter(x_zp, y_percentage_fit_stars)
        axs[1, 1].set_xlabel("ZP Range")
        axs[1, 1].set_ylabel("Percentage of Fitted Stars")
        axs[1, 1].set_title("ZP Range vs Percentage of Fitted Stars")
        axs[1, 1].grid()

        
        #plot fwhm vs rms
        axs[0,2].scatter(x_num_stars,x_zp)
        axs[0,2].set_ylabel("Zero Point Range")
        axs[0,2].set_xlabel("Percentage of Fitted Stars")
        axs[0,2].set_title("ZP vs Percentage of Fitted Stars")
        axs[0,2].grid()

                                                                    
        axs[1,2].scatter( x_num_stars, x_fwhm)
        axs[1,2].set_xlabel("Percentage of Stars Fitted")
        axs[1,2].set_ylabel("FWHM Range in Field")
        axs[1,2].set_title("FHWM vs NUM of Fitted Stars")
        axs[1,2].grid()

        fig.show()

        return self.new_df




class Locate_Didymos(Table_Generator):

    def __init__(self, body_name, source_type_field, input_dir_2, out_put_dir_2 = None):
        super().__init__(body_name, source_type_field)
        self.inpath = input_dir_2
        self.outpath = out_put_dir_2


    def Didymos_Field_Location(self,out_put_root, local_stat_out_path = None):
        """
        Objective: Find what Fields Didymos is in
            Inputs:
            out_put_root (str): For putting fields where didymos is present
            
            Returns:
            -If local_stat_out_path not NONE: save a table with location status of didymos
            
        """

        fields = StaticSource.objects.filter(source_type = self.source_type, name__contains = '2026')

        input_dir_2 = Path(self.inpath)                                   #Path("/apophis/eng/rocks/20260708/")
        output_root = Path(self.outpath)                               #Path("/home/mwalker/git/Didymos_data")
        out_put_root = Path(out_put_root)
        # Copy each file into the directory f2 as Didiymos is in that field rn...
        fits_names = [f for f in input_dir_2.glob(f"*.fits*")
                    if ".fz" not in f.name]  #selects fits

        field_num_ = []
        obs_info = []
        for field in fields:

            # Extract the field number from the name
            field_num = field.name.split("#")[-1].strip()
            field_num_.append(field_num)
            # Create output directory (f1, f2, ..., f16)
            outdir = output_root / f"f{field_num}"
            outdir.mkdir(parents=True, exist_ok=True)
            
            ra = field.ra
            dec = field.dec


            for file in fits_names:
                ep = file.name.split("-")[1].strip(" ")
                # Only ep07 files
                if ep != "ep07":
                    continue

                with fits.open(file) as hdul:
                    wcs = WCS(hdul[0].header)
                    data = hdul[0].data
                    header = hdul[0].header
                    date_obs = header["DATE-OBS"]

                    x,y = wcs.world_to_pixel_values(ra,dec)    #Check if x,y of fits in field #2

                    ny , nx = data.shape

                    if 0 <= x <= nx and 0 <=y <= ny:
                        print(f"{file.name} found in and copying to {field.name}")      
                        shutil.copy2(file, outdir/ file.name)
                        print(f"{file.name} time of obs is {date_obs}")
                        obs_info.append({
                                "field": field.name,
                                "time": Time(date_obs, format="isot", scale="utc"),
                                "file": file.name,
                            })
                                
        
        if local_stat_out_path is not None:
            self.outpath = Path(local_stat_out_path)
            data_table = pd.DataFrame(obs_info)
            os.makedirs(self.outpath, exist_ok=True)
            dst = self.outpath / "Didymos_location_status.csv"
            data_table.to_csv(dst, index = False)

        self.Didymos_Field_Loc_T =obs_info

        return self.Didymos_Field_Loc_T   #works


    def get_didymos_ephemeris(self, Found_field_name):
        """
        Objective: Match observation times to Horizons ephemeris.

        Inputs:
        Field name (str): Where was Didymos Found when running didymos_Field_Location()

        Returns:
        -------
        selected_rows : Astropy Table
        """


        # Get the ephemeris for Didymos; returns an Astropy Table
        ephem_FTS = horizons_ephem('65803', datetime(2026,7,8), datetime(2026,7,9), 'E10', '5m', alt_limit=30)   #add date start and dat end as inputs
        nighttime_mask = ephem_FTS['solar_presence'] == ''
        ephem_FTS = ephem_FTS[nighttime_mask]

        # For the start and the end of the ephemeris (first and last row of `ephem_FTS`) compute the separation between Didymos's position (given by `RA` and `DEC` columns) at that time with that of each of the Fields in `coj_fields`.
        # Hint: make SkyCoord's out of Didymos's position and the reference field and then look at spherical_offsets_to()

        #Get field 2#
        field_2_obs = [ 
            obs for obs in self.Didymos_Field_Loc_T if obs["field"].strip() == Found_field_name
        ]

        mask = []
        for obs in field_2_obs:
            delta_t = np.abs(ephem_FTS["datetime"] -obs["time"])
            idx = np.argmin(delta_t)  #get row where the difference is smallest in time obs and in field
            mask.append(idx)

        selected_rows = ephem_FTS[mask]

        ra_ = selected_rows["RA"]

        ra_ds9 = []
        for ra in ra_:
            ra = Angle(ra * u.deg)
            string = ra.to_string(unit = u.hour, sep = ":", precision = 4)
            ra_ds9.append(string)
            
        #selected_rows["RA"] = ra_ds9
        display(selected_rows)
        print(np.min(ephem_FTS["RA"]), np.max(ephem_FTS["RA"]))
        print(np.min(ephem_FTS["DEC"]), np.max(ephem_FTS["DEC"]))

        self.selected_rows = selected_rows
        return self.selected_rows

    def circular_aperture_photometry(self, center_x, center_y, radius,file_path):
        """
        Perform (very ROUGH!!!) Circular aperature photometry on image data

        Inputs:
        - image_data: 2D numpy array representing the image
        - center_x: x-coordinate of the center of the aperature (pixels)
        - center_y: y-coordinate of the center of the aperature (pixels)
        - radius: radius of the aperature (pixels)
        
        Returns:
        - aperature_sum: sum of pixel values within the aperature minus background
        - SNR: signal-to-noise ratio of the aperature photometry
        """

        with fits.open(file_path) as hdul:
            header = hdul[0].header
            image_data = hdul[0].data
            zp = header.get('ZP', 25.0)  # Default zero point if not found in header
            
        background = np.median(image_data)
        y, x = np.indices(image_data.shape)
        aperature_mask = (x-center_x)**2 + (y-center_y)**2 <= radius**2

        aperature_sum = np.sum(image_data[aperature_mask]) - background*np.sum(aperature_mask)        #bk * num_pixels = total flux
        SNR = aperature_sum / np.sqrt(aperature_sum + np.sum(aperature_mask) * background)  #SNR = signal / sqrt(signal + noise)
        appar_mag = -2.5 * np.log10(aperature_sum) + zp  #apparent magnitude = -2.5 * log10(flux)
        return aperature_sum, SNR, appar_mag


    def plot_didymos_frames(self,fits_dir,save_path=None,):
        """
        Plot the predicted Didymos position in each FITS image and perform
        circular aperture photometry.

        Parameters
        ----------
        ephem_rows : Astropy Table
            Table containing RA, DEC and datetime.
        fits_dir : Path or str
            Directory containing FITS images.
        save_path : str or Path, optional
            Save the figure if supplied.

        Returns
        -------
        didymos_stats : list[dict]
        pixel_positions : ndarray
        """
        #fucntion of circular aperature + sum and - bk

        fig, axes =  plt.subplots(3, 3, figsize=(12, 14))
        axes = axes.ravel()  #2D -> 1D array 

        ra__2 = self.selected_rows["RA"]
        dec__2 = self.selected_rows["DEC"]
        time__2 = self.selected_rows["datetime"]


        f_path = Path(fits_dir)

        f_files = sorted(f_path.glob(f"*.fits*"))

        didymos_stats_ = []
        pix_c_d = np.zeros((len(ra__2),2))
        for i, (ax, file, ra, dec, time) in enumerate(zip(axes,f_files, ra__2, dec__2, time__2)):

            with fits.open(file) as hdul:

                header = hdul[0].header
                data= hdul[0].data

                # Extract the WCS information from the header
                wcs_info = WCS(header)
                coord = SkyCoord(ra = ra *u.deg, dec = dec *u.deg)
                x, y = wcs_info.world_to_pixel(coord)
                pix_c_d[i] = x,y  #append positions for photutils
                file_p = file

                aperture_sum, SNR, appar_mag = self.circular_aperture_photometry(x, y, 13,file_p)

                didymos_stats_.append({
                    "aperture_Sum": aperture_sum,
                    "SNR": SNR, 
                    "Apparent Magnitude": appar_mag
                })


            #plotting
            interval = ZScaleInterval()
            vmin, vmax = interval.get_limits(data)
            ax.imshow(data, origin = "lower", cmap ="gray", vmin=vmin, vmax=vmax)
            ax.plot(x,y, "r+", markersize = 10)
            circle = plt.Circle((x,y), 14, fill= False, color = "red", linewidth = 3)
            ax.add_patch(circle)
            ax.set_title(file.name, fontsize = 8)
            ax.set_xlim(1100,1500)
            ax.set_ylim(900,1200)
            ax.text(
            0.02, 0.98,
            f"Sum = {aperture_sum:.0f}\n"
            f"SNR = {SNR:.1f}\n"
            f"Mag = {appar_mag:.2f}\n"
            f"Didymos = ({x:.4f}, {y:.4f})",
            transform=ax.transAxes,
            fontsize=8,
            color="white",
            verticalalignment="top",
            bbox=dict(facecolor="black", alpha=0.6)
            )
            # #graph the image of the (reference frame 13 with the bright star marked on it
            

        plt.tight_layout()

        if save_path is not None:
            save_dir_ds9= save_path
            plt.savefig (os.path.join(save_dir_ds9 , "didymos_ds9.png"),
                        dpi=300,
                        bbox_inches="tight")

        plt.show()

        #save results
        self.didymos_stats = didymos_stats_
        self.didymos_pixel_positions = pix_c_d

        return didymos_stats_, pix_c_d    #worked


    def measure_didymos_shape(self, fits_dir, positions,
                          aper_r=5, annulus_in=8, annulus_out=12):
        """
        Objective: Measure Didymos eccentricity/elongation in every frame.

        Inputs:
        fits_dir (str): Path to fits files -- ref fields
        positions (ndarray: [Nx2]): x,y positions calculated with ephem + ds9

        Returns:
        didymos_geo : list[dict]
        """

        ###USE photutils to get ellipicity of didymos vs surrounding stars  --SourceCatalog  ---ApertureStats

        positions_refined = []
        fits_dir = Path(fits_dir)
        fits_files = sorted(fits_dir.glob("*.fits*"))

        for file, pos in zip(fits_files, positions):

            with fits.open(file) as hdul:
                data = hdul[0].data

            # ---------- Refine the position ----------
            annulus = CircularAnnulus(pos, r_in=10, r_out=15)
            bkg = ApertureStats(data, annulus).median
        
            # 21x21 pixel cutout centered on your approximate position
            cutout = Cutout2D(data-bkg, pos, (7, 7))

            # centroid in cutout coordinates
            y_cen, x_cen = centroid_com(cutout.data)

            # convert back to full-image coordinates
            x_refined = cutout.xmin_original + x_cen
            y_refined = cutout.ymin_original + y_cen

            positions_refined.append((x_refined, y_refined))

            print(f"Original: {pos}")
            print(f"Refined : ({x_refined:.3f}, {y_refined:.3f})")


        app_phot_tables_d = []    #flux data
        app_phot_tables_d_geo = []  #geoemetric data
        #aperature_tables and subtraction
        for i, (file,pos) in enumerate(zip(fits_files, positions_refined)):

            with fits.open(file) as hdul:

                header = hdul[0].header
                data= hdul[0].data


                annulus = CircularAnnulus(pos, r_in = annulus_in, r_out = annulus_out)
                aperture = CircularAperture(positions=pos, r = aper_r)

                aperture_table = aperture_photometry(data, aperture)   #raw data counts

                annulus_stats = ApertureStats(data, annulus)
                aper_stats = ApertureStats(data, aperture)
                bkg_median = annulus_stats.median     #median background in annulus

                total_bkg = bkg_median * aperture.area_overlap(data, method = "center")

                aperture_table["bkg"] = total_bkg
                aperture_table["aperture_sum_bkg"] = aperture_table['aperture_sum'] - total_bkg   #NOW we have bkg and subtracted values for flux
                aperture_table["background"] = bkg_median
                aper_stats = ApertureStats(data-bkg_median, aperture)

                sig = aperture_table["aperture_sum_bkg"][0] 
                SNR  = (aperture_table["aperture_sum_bkg"][0] / np.sqrt(aperture_table["aperture_sum_bkg"][0] + total_bkg))
                aperture_table["SNR"] = SNR
                app_phot_tables_d_geo.append( {
                    "file": file.name,
                    "eccen" : aper_stats.eccentricity ,
                    "elongation" : aper_stats.elongation,
                    "semi-major": aper_stats.semimajor_sigma,
                    "semi-minor": aper_stats.semiminor_sigma,
                    "orientation (semi-major)": aper_stats.orientation

                })
                app_phot_tables_d.append(aperture_table)

        self.didymos_photometry = app_phot_tables_d
        self.didymos_geo = app_phot_tables_d_geo
        self.didymos_positions = positions_refined
        
        return app_phot_tables_d_geo


    def Star_Data(self,data,r,r_in, r_out, file):
        """
        Objective: 
            -Find stars
            -Perform bk_sub, aperture photometry
            -Get eccentricity + other stats on stars with SNR > 500
        Inputs:
            data [(2,2) np.array]: Data array
            file (str): got the data form the file, use for tracking purposes
            r, r_in, r_out (int): radius for aperture and annulus
        Returns:
            app_phot_table list [dict]: list of aperture tables
            app_phot_table_geo list[dict]: list of dict with eccen, SNR, etc...

        """

        ### Get star Positions ###
        mean, med, std = sigma_clipped_stats(data)
        dao_find = DAOStarFinder(threshold = 5 * std, fwhm = 3.0)
        stars = dao_find(data - med)

        if stars is None:
            print(f"No stars were found")

        x_positions = stars["xcentroid"]
        y_positions = stars["ycentroid"]

        app_phot_table = []
        app_phot_table_geo = []
        for x,y in zip(x_positions, y_positions):
            pos = (x,y)

            aperture = CircularAperture(positions = pos, r=r)
            annulus = CircularAnnulus(pos, r_in= r_in, r_out = r_out)

            aper_table = aperture_photometry(data, aperture)

            aper_stats = ApertureStats(data, aperture)
            annulus_stats = ApertureStats(data, annulus)

            med_bkg = annulus_stats.median
            total_bkg = med_bkg * aperture.area_overlap(data, method = 'center')

            aper_table["aperture_sum_bkg"] = aper_table['aperture_sum'] - total_bkg   #NOW we have bkg and subtracted values for flux
            aper_table["background"] = med_bkg
            aper_stats = ApertureStats(data - med_bkg, aperture)
            #compute SNR:
            sig = aper_table["aperture_sum_bkg"][0] 
            SNR  = (aper_table["aperture_sum_bkg"][0] / np.sqrt(aper_table["aperture_sum_bkg"][0] + total_bkg))
            aper_table["SNR"] = SNR
            avg_fwhm = 2.355 * np.sqrt(aper_stats.semimajor_sigma * aper_stats.semiminor_sigma)
            
            if (SNR < 30):
                continue
        
            ny, nx = data.shape
            margin = 20

            if (
                x < margin or
                x > nx - margin or
                y < margin or
                y > ny - margin
            ):
                continue
            app_phot_table_geo.append( {
                "file": file.name,
                "x": x,
                "y": y,
                "eccen" : aper_stats.eccentricity ,
                "elongation" : aper_stats.elongation,
                "semi-major": aper_stats.semimajor_sigma,
                "semi-minor": aper_stats.semiminor_sigma,
                "orientation (semi-major)": aper_stats.orientation,
                "flux": sig,
                "SNR": SNR,
                "FHWM": 2.355 * np.sqrt(aper_stats.semimajor_sigma * aper_stats.semiminor_sigma)
            })
            app_phot_table.append(aper_table)

        return app_phot_table, app_phot_table_geo



    def plot_eccentricity_histograms(self,fits_dir,save_path=None):
        """
        Objective: Compare Didymos eccentricity with surrounding stars.

        inputs:
        fits_dir (str):
        save_path (str):

        Returns:

        """
        ### Get the eccen and phtometry for stars in the data and graph the eccentricity in a histogram 

        fits_dir = Path(fits_dir)
        fits_files = sorted(fits_dir.glob("*.fits*"))


        fig, axes =  plt.subplots(3, 3, figsize=(12, 16))
        axes = axes.ravel()  #2D -> 1D array 

        all_star_info = []
        fwhms = []
        for i, (ax, file, diddy) in enumerate(zip(axes,fits_files,self.didymos_geo)):
            with fits.open(file) as hudl:
                data = hudl[0].data
                header = hudl[0].header

            flux_info , geo_info = self.Star_Data(data,15, 20, 25, file)

            ecc = [star["eccen"] for star in geo_info ]
            ecc = np.asarray(ecc, dtype=float).ravel()
            mean_star_eccen = np.mean(ecc)
            ecc_d = diddy["eccen"]
            fwhm = [star["FHWM"] for star in geo_info]
            fwhms.append(fwhm)
        

            all_star_info.append(geo_info)
            self.star_geo = all_star_info

            #Plot histograms of eccen and stars

            ax.hist(ecc, bins = 15, color = "blue", alpha = 0.7)
            ax.set_title(file.name, fontsize = 8)
            ax.set_xlabel("Eccentricity")
            ax.set_ylabel("Number of stars")
            ax.axvline(ecc_d, color="red", linewidth = 4,label= "Didymos")
            ax.legend(fontsize=8, loc = "upper right")
            ax.text(
                0.02, 0.98,   #percent of axes fron left and bottom when using transform method
                f"Mean Star Eccentricity: {mean_star_eccen:.3f} \n"
                f" Didymos Eccentricity: {ecc_d:.3f} \n"
                f"N stars = {len(ecc)}\n",
                transform = ax.transAxes,
                fontsize = 8,
                color = "black",
                verticalalignment = "top",
                bbox = dict(facecolor = "pink", alpha = 0.7)

            )
        plt.tight_layout()
        if save_path is not None:
            save_dir_png = Path(save_path)
            plt.savefig (os.path.join(save_dir_png ,"eccentricity_histograms_true_pos.png"),
                        dpi=300,
                        bbox_inches="tight")

        plt.show()
        return all_star_info
























###might do some subclass stuff?

###get ssh access!!!



####Bash Commands: i.e LINUX #####

#add output dir in arguments

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("action")
    parser.add_argument("body_name")
    parser.add_argument("source_type")  #---put REFERENCE
    parser.add_argument("--output_dir") # -- = positional and only needed for def ref_quality
    parser.add_argument("--out_put_dir_fwhm") # -- = positional and only needed for def fwhm_zp_plot
    parser.add_argument("--out_put_dir_zp") # -- = positional and only needed for def fwhm_zp_plot
    parser.add_argument("--input_dir_diddy")
    parser.add_argument("--out_put_dir")  #optional argument for Locate_Didymos Class
    parser.add_argument("--field_name") #optional argument for Locate_Didymos
    args = parser.parse_args()

    tg = Table_Generator(
        body_name=args.body_name,
        source_type_field= args.source_type,
) 
    ta = Table_analysis(
        body_name = args.body_name,
        source_type_field = args.source_type
)
    ld = Locate_Didymos(
        body_name= args.body_name,
        source_type_field = args.source_type,
        input_dir_2 = args.input_dir_diddy,
        out_put_dir_2 = args.out_put_dir
    )
    if args.action == "table":
        print(tg.gen_table())

    elif args.action == "ref_quality":
        print(tg.ref_image_quality(args.output_dir))

    elif args.action == "fwhm_zp_plot":   #shows it has been done          
        print(tg.fwhm_zp_plot(args.out_put_dir_fwhm, args.out_put_dir_zp))
    
    elif args.action == "analyze":
        ta.analyze(args.output_dir
                   )
    elif args.action == "plot_num_stars":
        ta.analyze()
        ta.Graph_analysis()

    elif args.action == "Field_Location":
        print(ld.Didymos_Field_Location(args.out_put_dir))
        selected_rows = ld.get_didymos_ephemeris(args.field_name)
        print(selected_rows)

    elif args.action == "plot_frames":
        ld.Didymos_Field_Location(args.out_put_dir)
        ld.get_didymos_ephemeris(args.field_name)
        ld.plot_didymos_frames(args.out_put_dir)

    elif args.action == "measure_shape":
        ld.Didymos_Field_Location(args.out_put_dir)
        ld.get_didymos_ephemeris(args.field_name)
        _, positions = ld.plot_didymos_frames(args.out_put_dir)
        shape = ld.measure_didymos_shape(args.out_put_dir, positions)
        print(shape)

    elif args.action == "plot_ecc":
        ld.Didymos_Field_Location(args.out_put_dir)
        ld.get_didymos_ephemeris(args.field_name)
        _, positions = ld.plot_didymos_frames(args.out_put_dir)
        ld.measure_didymos_shape(args.out_put_dir, positions)
        ld.plot_eccentricity_histograms(args.out_put_dir)



#example bash command: neo_table_generator_v1.py table 65803 REFERENCE_FIELD EXPOSE




####To-DO####


#add appropriate arguments, intializers, and actions methods
#-wrtie unit tests + do research on this