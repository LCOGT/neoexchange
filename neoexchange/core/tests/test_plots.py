import os
import numpy
import shutil
import tempfile
import matplotlib
from glob import glob
from astropy.io import fits
from unittest import skipIf
from datetime import datetime, timedelta

from django.test import TestCase
from django.http import HttpResponse
from django.forms import model_to_dict # remove later
from django.core.files.storage import default_storage

from core.models import Body, SourceMeasurement, Designations
# Import module methods to test
from core.views import perform_aper_photometry
from core.models import Proposal
from core.models.frame import Frame
from core.models.blocks import Block, SuperBlock
from core.models.sources import StaticSource, CatalogSources
from core.plots import find_existing_vis_file, determine_plot_valid, make_visibility_plot, generalized_fwhm_plotter, generalized_zeropoint_plotter, plot_magnitude

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL level
logging.disable(logging.CRITICAL)

@skipIf(True, "Needs Mocks")
class TestFindExistingVisFile(TestCase):
    # XXX Need to work out how to mock default_storage in both local and S3 mode
    def test_all_the_things(self):
        pass

class TestDeterminePlotValid(TestCase):

    def test_old_hoursup(self):

        orig_vis_file = 'visibility/42/2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,21,1,2,3)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual('', vis_file)

    def test_new_hoursup(self):

        orig_vis_file = 'visibility/42/2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,14,23,59,59)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual(orig_vis_file, vis_file)

    def test_old_hoursup_2names(self):

        orig_vis_file = 'visibility/42/12345_2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,21,1,2,3)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual('', vis_file)

    def test_new_hoursup_2names(self):

        orig_vis_file = 'visibility/42/12345_2013XA22_hoursup_20191001-20191101.png'
        compare_time = datetime(2019,10,14,23,59,59)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual(orig_vis_file, vis_file)

    def test_old_uncertainty(self):

        orig_vis_file = 'visibility/42/2013XA22_uncertainty_20191001-20191101.png'
        compare_time = datetime(2019,10,2,1,2,3)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual('', vis_file)

    def test_new_uncertainty(self):

        orig_vis_file = 'visibility/42/2013XA22_uncertainty_20191001-20191101.png'
        compare_time = datetime(2019,10,1,23,59,59)

        vis_file = determine_plot_valid(orig_vis_file, compare_time)

        self.assertEqual(orig_vis_file, vis_file)


class TestMakeVisibilityPlot(TestCase):

    def setUp(self):
        body_params = {
                         'provisional_name': None,
                         'provisional_packed': 'j5432',
                         'name': '455432',
                         'origin': 'A',
                         'source_type': 'N',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': True,
                         'fast_moving': True,
                         'urgency': None,
                         'epochofel': datetime(2019, 7, 31, 0, 0),
                         'orbit_rms': 0.46,
                         'orbinc': 31.23094,
                         'longascnode': 301.42266,
                         'argofperih': 22.30793,
                         'eccentricity': 0.3660154,
                         'meandist': 1.7336673,
                         'meananom': 352.55084,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.54,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(2003, 9, 7, 3, 7, 18),
                         'num_obs': 130,
                         'arc_length': 6209.0,
                         'not_seen': 3.7969329574421296,
                         'updated': True,
                         'ingest': datetime(2019, 7, 4, 5, 28, 39),
                         'update_time': datetime(2019, 7, 30, 19, 7, 35)
                        }
        self.test_body = Body.objects.create(**body_params)
        self.targetname = '455432_2003RP8'

        body_params['provisional_name'] = 'N999foo'
        body_params['provisional_packed'] = None
        body_params['name'] = None
        self.test_neocp_body = Body.objects.create(**body_params)

        self.start_time = datetime(2021,6,1)
        self.end_time = self.start_time + timedelta(days=31)

    def test_badplottype(self):
        response = make_visibility_plot(None, self.test_body.pk, 'cucumber', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual('image/gif', response['Content-Type'])
        self.assertEqual(b'GIF89a', response.content[0:6])

    def test_nonameobject(self):
        response = make_visibility_plot(None, self.test_neocp_body.pk, 'radec', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(b'', response.content)

    def test_plot_radec(self):

        plot_filename = "visibility/{}/{}_radec_{}-{}.png".format(self.test_body.pk,
            self.targetname, self.start_time.strftime("%Y%m%d"), self.end_time.strftime("%Y%m%d"))

        response = make_visibility_plot(None, self.test_body.pk, 'radec', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual('image/png', response['Content-Type'])
        self.assertEqual(b'\x89PNG\r\n', response.content[0:6])
        self.assertTrue(default_storage.exists(plot_filename))

    def test_plot_gallonglat(self):

        plot_filename = "visibility/{}/{}_glonglat_{}-{}.png".format(self.test_body.pk,
            self.targetname, self.start_time.strftime("%Y%m%d"), self.end_time.strftime("%Y%m%d"))

        response = make_visibility_plot(None, self.test_body.pk, 'glonglat', self.start_time)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual('image/png', response['Content-Type'])
        self.assertEqual(b'\x89PNG\r\n', response.content[0:6])
        self.assertTrue(default_storage.exists(plot_filename))

class TestObsPlotters(TestCase):
    def setUp(self):

        self.framedir = os.path.abspath(os.path.join('photometrics', 'tests'))
        self.test_file = 'hotpants_test_frame.fits'
        self.test_file_path = os.path.join(self.framedir, self.test_file)
        self.test_file_rms = 'hotpants_test_frame.rms.fits'
        self.test_file_path_rms = os.path.join(self.framedir, self.test_file)

#       self.test_dir = '/tmp/tmp_neox_wibble'
        self.test_dir =  '/tmp/tmp_neox_fjody5q5' #tempfile.mkdtemp(prefix='tmp_neox_')

        self.test_output_dir = os.path.join(self.test_dir, '20240729')
        os.makedirs(self.test_output_dir, exist_ok=True)

        body_params = {
                         'id': 36254,
                         'provisional_name': None,
                         'provisional_packed': None,
                         'name': '65803',
                         'origin': 'N',
                         'source_type': 'N',
                         'source_subtype_1': 'N3',
                         'source_subtype_2': 'PH',
                         'elements_type': 'MPC_MINOR_PLANET',
                         'active': False,
                         'fast_moving': False,
                         'urgency': None,
                         'epochofel': datetime(2021, 2, 25, 0, 0),
                         'orbit_rms': 0.56,
                         'orbinc': 3.40768,
                         'longascnode': 73.20234,
                         'argofperih': 319.32035,
                         'eccentricity': 0.3836409,
                         'meandist': 1.6444571,
                         'meananom': 77.75787,
                         'perihdist': None,
                         'epochofperih': None,
                         'abs_mag': 18.27,
                         'slope': 0.15,
                         'score': None,
                         'discovery_date': datetime(1996, 4, 11, 0, 0),
                         'num_obs': 829,
                         'arc_length': 7305.0,
                         'not_seen': 2087.29154187494,
                         'updated': True,
                         'ingest': datetime(2018, 8, 14, 17, 45, 42),
                         'update_time': datetime(2021, 3, 1, 19, 59, 56, 957500)
                         }

        self.test_body, created = Body.objects.get_or_create(**body_params)

        desig_params = { 'body' : self.test_body, 'value' : 'Didymos', 'desig_type' : 'N', 'preferred' : True, 'packed' : False}
        test_desig, created = Designations.objects.get_or_create(**desig_params)
        desig_params['value'] = '65803'
        desig_params['desig_type'] = '#'
        test_desig, created = Designations.objects.get_or_create(**desig_params)

        ref_field_params = {
                            'name': 'Didymos COJ 2024 practice #25',
                            'ra': 262.88411499999995,
                            'dec': -28.493625,
                            'pm_ra': 0.0,
                            'pm_dec': 0.0,
                            'parallax': 0.0,
                            'vmag': 9.0,
                            'spectral_type': '',
                            'source_type': 16,
                            'notes': '',
                            'quality': 0,
                            'reference': ''}

        self.test_ref_field = StaticSource.objects.create(**ref_field_params)

        block_params = {
                         'body' : self.test_body,
                         'calibsource' : self.test_ref_field,
                         'request_number' : '12345',
                         'block_start' : datetime(2024, 6, 10, 0, 40),
                         'block_end' : datetime(2024, 6, 10, 17, 59),
                         'obstype' : Block.OPT_IMAGING,
                         'num_observed' : 1
                        }
        self.test_block, created = Block.objects.get_or_create(**block_params)
        # Second block with no frames attached
        block_params['num_observed'] = 1
        block_params['request_number'] = 12346
        self.test_block2, created = Block.objects.get_or_create(**block_params)

        midpoints_for_good_elevs = []
        for i in range (0, 28):
            desired_midpoint = datetime(2024, 6, 10, 17, 2 * i)
            midpoints_for_good_elevs.append(desired_midpoint)

        for item in [self.test_block, self.test_block2]:
            frame_params = {
                            'sitecode' : 'E10',
                            'instrument' : 'ep07',
                            'exptime' : 170.0,
                            'filter' : 'rp',
                            'block' : item,
                            'frametype' : Frame.BANZAI_RED_FRAMETYPE,
                            'fwhm': 2.7,
                            'zeropoint' : 27.0,
                            'zeropoint_err' : 0.03,
                            'midpoint' : block_params['block_start'] + timedelta(minutes=5)
                        }
            #print(f"filter {frame_params['filter']}")
            i = 0
            self.test_banzai_files = []
            source_details = { 45234032 : {'mag' : 14.8447, 'err_mag' : 0.0054, 'flags' : 0},
                            45234584 : {'mag' : 14.8637, 'err_mag' : 0.0052, 'flags' : 3},
                            45235052 : {'mag' : 14.8447, 'err_mag' : 0.0051, 'flags' : 0}
                            }
            ra = [0, 283.50961, 283.50922, 283.50883]
            dec = [0, -25.07526, -25.07538, -25.07550]
            for frame_num, frameid in zip(range(65,126,30),[45234032, 45234584, 45235052]):
                #print(f"FRAME NUM {frame_num, i}")
                i += 1
                frame_params['filename'] = f"coj2m002-ep07-20240610-{frame_num:04d}-e91.fits"
                frame_params['midpoint'] = midpoints_for_good_elevs[i]
                frame_params['frameid'] = frameid
                self.e91_frame, created = Frame.objects.get_or_create(**frame_params)
                #print(self.e91_frame.filename)
                # Create NEOX_RED_FRAMETYPE type also
                red_frame_params = frame_params.copy()
                red_frame_params['frametype'] = Frame.NEOX_RED_FRAMETYPE
                red_frame_params['filename'] = red_frame_params['filename'].replace('e91', 'e92')
                self.e92_frame, created = Frame.objects.get_or_create(**red_frame_params)
                #print(self.e92_frame.filename)
                # Create NEOX_SUB_FRAMETYPE type also
                sub_frame_params = frame_params.copy()
                sub_frame_params['frametype'] = Frame.NEOX_SUB_FRAMETYPE
                sub_frame_params['filename'] = red_frame_params['filename'].replace('e92', 'e93')
                self.e93_frame, created = Frame.objects.get_or_create(**sub_frame_params)
                #print(self.e93_frame.filename)

                cat_source = source_details[frameid]
                source_params = { 'body' : self.test_body,
                                'frame' : self.e93_frame,
                                'obs_ra' : 208.728,
                                'obs_dec' : -10.197,
                                'obs_mag' : cat_source['mag'],
                                'err_obs_ra' : 0.0003,
                                'err_obs_dec' : 0.0003,
                                'err_obs_mag' : cat_source['err_mag'],
                                'astrometric_catalog' : self.e93_frame.astrometric_catalog,
                                'photometric_catalog' : self.e93_frame.photometric_catalog,
                                'aperture_size' : 10*0.389,
                                'snr' : 1/cat_source['err_mag'],
                                'flags' : cat_source['flags']
                                }
                source, created = SourceMeasurement.objects.get_or_create(**source_params)
                source_params = { 'frame' : self.e93_frame,
                                'obs_x' : 2048+frame_num/10.0,
                                'obs_y' : 2043-frame_num/10.0,
                                'obs_ra' : 208.728,
                                'obs_dec' : -10.197,
                                'obs_mag' : cat_source['mag'],
                                'err_obs_ra' : 0.0003,
                                'err_obs_dec' : 0.0003,
                                'err_obs_mag' : cat_source['err_mag'],
                                'background' : 42,
                                'major_axis' : 3.5,
                                'minor_axis' : 3.25,
                                'position_angle' : 42.5,
                                'ellipticity' : 0.3711,
                                'aperture_size' : 10*0.389,
                                'flags' : cat_source['flags']
                                }
                cat_src, created = CatalogSources.objects.get_or_create(**source_params)
                for extn in ['e92-ldac', 'e92.bkgsub', 'e92', 'e92.rms', 'e93', 'e93.rms']:
                    new_name = os.path.join(self.test_output_dir, frame_params['filename'].replace('e91', extn))
                    filename = shutil.copy(self.test_file_path, new_name)
                    # Change object name to 65803
                    with fits.open(filename) as hdulist:
                        #print(f"FILENAME {filename}")
                        hdulist[0].header['telescop'] = '2m0-02'
                        hdulist[0].header['instrume'] = 'ep07'
                        hdulist[0].header['object'] = '65803 '
                        half_exp = timedelta(seconds=hdulist[0].header['exptime'] / 2.0)
                        date_obs = frame_params['midpoint'] - half_exp
                        #print("SUB LOOP MIDPOINT", frame_params['midpoint'])
                        hdulist[0].header['date-obs'] = date_obs.strftime("%Y-%m-%dT%H:%M:%S")
                        utstop = frame_params['midpoint'] + half_exp + timedelta(seconds=8.77)
                        hdulist[0].header['utstop'] = utstop.strftime("%H:%M:%S.%f")[0:12]
                        hdulist[0].header['crval1'] = ra[i]
                        hdulist[0].header['crval2'] = dec[i]
                        hdulist.writeto(filename, overwrite=True, checksum=True)
    #                   hdulist.close()
                        self.test_banzai_files.append(os.path.basename(filename))

        # Make one additional copy which is renamed to an -e91 (so it shouldn't be found)
        new_name = os.path.join(self.test_output_dir, 'coj2m002-ep07-20240610-0065-e91.fits')
        shutil.copy(self.test_file_path, new_name)
        self.test_banzai_files.insert(1, os.path.basename(new_name))

        self.remove = True
        self.debug_print = True
        self.maxDiff = None

        self.block_date_str = f"{self.test_block.block_start}"[:-9]
        self.field_name = self.test_block.calibsource.name[-3:]
        self.block_date_str2 = f"{self.test_block2.block_start}"[:-9]
        self.field_name2 = self.test_block2.calibsource.name[-3:]
        self.filters = ['rp']
        self.colors = ['tomato']
        self.remove = True
        self.debug_print = True
        self.maxDiff = None
    def tearDown(self):
        # Generate an example test dir to compare root against and then remove it
        temp_test_dir = tempfile.mkdtemp(prefix='tmp_neox')
        os.rmdir(temp_test_dir)
        if self.remove and self.test_dir.startswith(temp_test_dir[:-8]):
            shutil.rmtree(self.test_dir)
        else:
            if self.debug_print:
                print("Not removing temporary test directory", self.test_dir)


    def test_fwhm_plot_single_block_full_night(self):
        test_plot = generalized_fwhm_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= True)
        filename = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_fwhm_plot_single_block_ind_block(self):
        test_plot = generalized_fwhm_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= False)
        filename = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_fwhm_plot_single_block_allTrue(self):
        print(self.filters, self.colors)
        test_plot = generalized_fwhm_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        filename = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_fwhm_plot_single_block_allFalse(self):
        test_plot = generalized_fwhm_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        filename = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_fwhm_plot_mult_blocks_full_night(self):
        test_plot = generalized_fwhm_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_FWHM_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_fwhm_plot_mult_blocks_ind_block(self):
        test_plot = generalized_fwhm_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= False)
        filename1 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        filenames = [filename1, filename2]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(filenames, test_plot)


    def test_fwhm_plot_mult_blocks_allTrue(self):
        test_plot = generalized_fwhm_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_FWHM_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename1 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        full_night_filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename1, filename2, full_night_filename]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        img3 = matplotlib.image.imread(full_night_filename)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertTrue(img3.shape[0]> 0, img3.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(type(img3), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_fwhm_plot_mult_blocks_allFalse(self):
        test_plot = generalized_fwhm_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_FWHM_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_fwhm_plot_ref_field_full_night(self):
        test_plot = generalized_fwhm_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_FWHM_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_fwhm_plot_ref_field_ind_block(self):
        test_plot = generalized_fwhm_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= False)
        filename1 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        filenames = [filename1, filename2]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(filenames, test_plot)


    def test_fwhm_plot_ref_field_allTrue(self):
        test_plot = generalized_fwhm_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_FWHM_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename1 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_FWHM_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        full_night_filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename1, filename2, full_night_filename]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        img3 = matplotlib.image.imread(full_night_filename)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertTrue(img3.shape[0]> 0, img3.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(type(img3), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_fwhm_plot_ref_field_allFalse(self):
        test_plot = generalized_fwhm_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_FWHM_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_zeropoint_plot_single_block_full_night(self):
        test_plot = generalized_zeropoint_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= True)
        filename = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_zeropoint_plot_single_block_ind_block(self):
        test_plot = generalized_zeropoint_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= False)
        filename = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_zeropoint_plot_single_block_allTrue(self):
        test_plot = generalized_zeropoint_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        filename = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_zeropoint_plot_single_block_allFalse(self):
        test_plot = generalized_zeropoint_plotter(self.test_block, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        filename = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual([filename], test_plot)

    def test_zeropoint_plot_mult_blocks_full_night(self):
        test_plot = generalized_zeropoint_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_ZP_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_zeropoint_plot_mult_blocks_ind_block(self):
        test_plot = generalized_zeropoint_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= False)
        filename1 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        filenames = [filename1, filename2]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(filenames, test_plot)


    def test_zeropoint_plot_mult_blocks_allTrue(self):
        test_plot = generalized_zeropoint_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_ZP_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename1 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        full_night_filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename1, filename2, full_night_filename]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        img3 = matplotlib.image.imread(full_night_filename)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertTrue(img3.shape[0]> 0, img3.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(type(img3), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_zeropoint_plot_mult_blocks_allFalse(self):
        test_plot = generalized_zeropoint_plotter([self.test_block, self.test_block2], self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_ZP_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_zeropoint_plot_ref_field_full_night(self):
        test_plot = generalized_zeropoint_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_ZP_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_zeropoint_plot_ref_field_ind_block(self):
        test_plot = generalized_zeropoint_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= False)
        filename1 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        filenames = [filename1, filename2]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(filenames, test_plot)


    def test_zeropoint_plot_ref_field_allTrue(self):
        test_plot = generalized_zeropoint_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= True, make_full_night_plot= True)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_ZP_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename1 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str}_Field_{self.field_name}.png")
        filename2 = os.path.join(self.test_output_dir, f"single_block_ZP_plot_{self.block_date_str2}_Field_{self.field_name2}.png")
        full_night_filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename1, filename2, full_night_filename]
        img1 = matplotlib.image.imread(filename1)
        img2 = matplotlib.image.imread(filename2)
        img3 = matplotlib.image.imread(full_night_filename)
        self.assertTrue(img1.shape[0]> 0, img1.shape[1] > 0)
        self.assertTrue(img2.shape[0]> 0, img2.shape[1] > 0)
        self.assertTrue(img3.shape[0]> 0, img3.shape[1] > 0)
        self.assertEqual(type(img1), numpy.ndarray)
        self.assertEqual(type(img2), numpy.ndarray)
        self.assertEqual(type(img3), numpy.ndarray)
        self.assertEqual(filenames, test_plot)

    def test_zeropoint_plot_ref_field_allFalse(self):
        test_plot = generalized_zeropoint_plotter(self.test_ref_field, self.filters, self.colors, self.test_output_dir, individual_block_plots= False, make_full_night_plot= False)
        field_names = []
        for block in ([self.test_block, self.test_block2]):
            field_name = block.calibsource.name[-3:]
            field_names.append(field_name)
        fields_str_for_file = "_".join(field_names)
        shortfilename = f"_ZP_plot_{block.get_blockdayobs}_Field_{fields_str_for_file}_plot1.png"
        filename = os.path.join(self.test_output_dir, shortfilename)
        filenames = [filename]
        img = matplotlib.image.imread(filename)
        self.assertTrue(img.shape[0]> 0, img.shape[1] > 0)
        self.assertEqual(type(img), numpy.ndarray)
        self.assertEqual(filenames, test_plot)