"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime

from django.test import TestCase
from mock import patch, Mock
from astropy.wcs import WCS

from core.models import Body, Proposal, Block, SuperBlock
from neox.tests.mocks import mock_fetch_archive_frames, mock_archive_frame_header
from core.frames import *

# Disable logging during testing
import logging
logger = logging.getLogger(__name__)
# Disable anything below CRITICAL
logging.disable(logging.CRITICAL)


class TestBlockStatus(TestCase):

    def setUp(self):
        # Initialise with a test body, test proposal, and cadence SuperBlock
        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        sb_params = {  'cadence'       : 'True',
                       'body'          : self.body,
                       'proposal'      : self.neo_proposal,
                       'block_start'   : '2015-04-20 13:00:00',
                       'block_end'     : '2015-04-21 03:00:00',
                       'tracking_number' : '00042',
                       'active'        : True
                    }
        self.super_block, created = SuperBlock.objects.get_or_create(**sb_params)

        # Create test blocks
        block_params = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'superblock'  : self.super_block,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00003',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        block_params2 = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '1430663',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block2 = Block.objects.create(**block_params2)

        block_params3 = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00015',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block3 = Block.objects.create(**block_params3)

        block_params4 = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'superblock'  : self.super_block,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00009',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block4 = Block.objects.create(**block_params4)

    def insert_spectro_blocks(self):

        sb_params = {  'cadence'       : 'False',
                       'body'          : self.body,
                       'proposal'      : self.neo_proposal,
                       'block_start'   : '2015-04-20 05:00:00',
                       'block_end'     : '2015-04-21 15:00:00',
                       'tracking_number' : '4242',
                       'active'        : True
                    }
        self.spec_super_block, created = SuperBlock.objects.get_or_create(**sb_params)

        spec_block_params1 = { 'telclass' : '2m0',
                               'site'     : 'ogg',
                               'body'     : self.body,
                               'superblock'  : self.spec_super_block,
                               'proposal' : self.neo_proposal,
                               'block_start' : '2015-04-20 13:00:00',
                               'block_end'   : '2015-04-21 03:00:00',
                               'tracking_number' : '1391169',
                               'num_exposures' : 1,
                               'exp_length' : 1800.0,
                               'active'   : True,
                               'num_observed' : 0,
                               'reported' : False
                               }
        self.spec_test_block1 = Block.objects.create(**spec_block_params1)

    # Create Mocked output to image request from Valhala.
    # Header URL and Reqnum have been changed for easy tracking.
    # no images for last block
    def mock_check_for_archive_images(request_id, obstype='EXPOSE'):
        result_images_out = [{u'BLKUID': 226770074,
                              u'DATE_OBS': u'2018-02-27T04:10:51.702000Z',
                              u'EXPTIME': u'10.238',
                              u'FILTER': u'w',
                              u'INSTRUME': u'kb80',
                              u'L1PUBDAT': u'2019-02-27T04:10:51.702000Z',
                              u'OBJECT': '1test_'+str(request_id),
                              u'OBSTYPE': u'EXPOSE',
                              u'PROPID': u'LCO2018A-012',
                              u'REQNUM': request_id,
                              u'RLEVEL': 91,
                              u'SITEID': u'elp',
                              u'TELID': u'0m4a',
                              u'area': {u'coordinates': [[[175.3634230138293, 73.42041723658008],
                                 [176.489579845721, 73.42430056668292],
                                 [176.493982451836, 72.94199402324494],
                                 [175.39874986356807, 72.93821734095452],
                                 [175.3634230138293, 73.42041723658008]]],
                               u'type': u'Polygon'},
                              u'basename': u'elp0m411-kb80-20180226-0077-e91',
                              u'filename': u'elp0m411-kb80-20180226-0077-e91.fits.fz',
                              u'headers': '1test_'+str(request_id),
                              u'id': request_id,
                              u'related_frames': [7203968, 8035197, 8035195, 8030893, 7986266],
                              u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/8387/elp0m411-kb80-20180226-0077-e91?versionId=zeF8aanQzLDJKXGSqhQ6kS5.wRROHUgI&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=S4R2UzFEDpeFgnIN3pVxhaBk6r4%3D&Expires=1520120748',
                              u'version_set': [{u'created': u'2018-02-27T16:16:10.482024Z',
                                u'extension': u'.fits.fz',
                                u'id': 8349661,
                                u'key': u'zeF8aanQzLDJKXGSqhQ6kS5.wRROHUgI',
                                u'md5': u'd21928112095941617fec2372384da36',
                                u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/8387/elp0m411-kb80-20180226-0077-e91?versionId=zeF8aanQzLDJKXGSqhQ6kS5.wRROHUgI&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=S4R2UzFEDpeFgnIN3pVxhaBk6r4%3D&Expires=1520120748'}]},
                             {u'BLKUID': 226770074,
                              u'DATE_OBS': u'2018-02-27T04:10:35.712000Z',
                              u'EXPTIME': u'10.237',
                              u'FILTER': u'w',
                              u'INSTRUME': u'kb80',
                              u'L1PUBDAT': u'2019-02-27T04:10:35.712000Z',
                              u'OBJECT': '2test_'+str(request_id),
                              u'OBSTYPE': u'EXPOSE',
                              u'PROPID': u'LCO2018A-012',
                              u'REQNUM': request_id,
                              u'RLEVEL': 91,
                              u'SITEID': u'elp',
                              u'TELID': u'0m4a',
                              u'area': {u'coordinates': [[[175.36244049289198, 73.42075299265626],
                                 [176.48876179976844, 73.42464488204425],
                                 [176.49320403467433, 72.94227739986835],
                                 [175.39781591212306, 72.93849240870662],
                                 [175.36244049289198, 73.42075299265626]]],
                               u'type': u'Polygon'},
                              u'basename': u'elp0m411-kb80-20180226-0076-e91',
                              u'filename': u'elp0m411-kb80-20180226-0076-e91.fits.fz',
                              u'headers': '2test_'+str(request_id),
                              u'id': 8035227,
                              u'related_frames': [7203968, 8035197, 8035195, 8030891, 7986266],
                              u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/c286/elp0m411-kb80-20180226-0076-e91?versionId=YquJyq8u_tEoCSFpVMPPM7kLzxZ0p_it&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=tuTe1RILDACBEaKFfDMtO%2Fr9iyU%3D&Expires=1520120748',
                              u'version_set': [{u'created': u'2018-02-27T16:16:05.924956Z',
                                u'extension': u'.fits.fz',
                                u'id': 2 * request_id,
                                u'key': u'YquJyq8u_tEoCSFpVMPPM7kLzxZ0p_it',
                                u'md5': u'53393c9054c33090df6710215ac72342',
                                u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/c286/elp0m411-kb80-20180226-0076-e91?versionId=YquJyq8u_tEoCSFpVMPPM7kLzxZ0p_it&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=tuTe1RILDACBEaKFfDMtO%2Fr9iyU%3D&Expires=1520120748'}]},
                            {u'BLKUID': 226770074,
                              u'DATE_OBS': u'2018-02-27T04:10:19.822000Z',
                              u'EXPTIME': u'10.237',
                              u'FILTER': u'w',
                              u'INSTRUME': u'kb80',
                              u'L1PUBDAT': u'2019-02-27T04:10:19.822000Z',
                              u'OBJECT': '3test_'+str(request_id),
                              u'OBSTYPE': u'EXPOSE',
                              u'PROPID': u'LCO2018A-012',
                              u'REQNUM': request_id,
                              u'RLEVEL': 91,
                              u'SITEID': u'elp',
                              u'TELID': u'0m4a',
                              u'area': {u'coordinates': [[[175.36112661033172, 73.42086136781433],
                                 [176.48737193066208, 73.42475818787373],
                                 [176.49184160850814, 72.94242630853277],
                                 [175.39652536517892, 72.93863651517941],
                                 [175.36112661033172, 73.42086136781433]]],
                               u'type': u'Polygon'},
                              u'basename': u'elp0m411-kb80-20180226-0075-e91',
                              u'filename': u'elp0m411-kb80-20180226-0075-e91.fits.fz',
                              u'headers': '3test_'+str(request_id),
                              u'id': 3 * request_id,
                              u'related_frames': [7203968, 8035197, 8035195, 8030887, 7986266],
                              u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/28d0/elp0m411-kb80-20180226-0075-e91?versionId=hZF3yaFjXBvVWpHhQeiYSPKLJIPeHOnD&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=FxTVEMMOT24%2FzLemz1vYennkko4%3D&Expires=1520120748',
                              u'version_set': [{u'created': u'2018-02-27T16:15:57.913799Z',
                                u'extension': u'.fits.fz',
                                u'id': 8349659,
                                u'key': u'hZF3yaFjXBvVWpHhQeiYSPKLJIPeHOnD',
                                u'md5': u'24f8ca63ef9e25915d49dd80732c1e89',
                                u'url': u'https://s3.us-west-2.amazonaws.com/archive.lcogt.net/28d0/elp0m411-kb80-20180226-0075-e91?versionId=hZF3yaFjXBvVWpHhQeiYSPKLJIPeHOnD&AWSAccessKeyId=AKIAIJQVPYFWOR234BCA&Signature=FxTVEMMOT24%2FzLemz1vYennkko4%3D&Expires=1520120748'}]}
                             ]
        if request_id == 9:
            return [], 0
        else:
            return result_images_out, 3

    # Mock Header output read from Valhalla
    # modified Origname for easy tracking
    def mock_lco_api_call(link):
        header_out= {u'data': {u'AGCAM': u'kb80',
                              u'AGDEC': u'',
                              u'AGDX': 0.0,
                              u'AGDY': 0.0,
                              u'AGFILST': u'Enabled',
                              u'AGFILTER': u'w,',
                              u'AGFILTID': u'PSTR-WX-124,',
                              u'AGFOCDMD': u'',
                              u'AGFOCOFF': 0.0,
                              u'AGFOCST': u'',
                              u'AGFOCUS': u'',
                              u'AGFWHM': u'',
                              u'AGGMAG': u'',
                              u'AGLCKFRC': 0.0,
                              u'AGMIRDMD': u'',
                              u'AGMIRPOS': u'00.0, N/A',
                              u'AGMIRST': u'ERROR',
                              u'AGMODE': u'OFF',
                              u'AGNSRC': 0,
                              u'AGRA': u'',
                              u'AGSTATE': u'IDLE',
                              u'AIRMASS': 4.4792254,
                              u'ALTDMD': u'',
                              u'ALTITUDE': 12.6719931,
                              u'ALTSTAT': u'OKAY',
                              u'AMEND': 4.4792229,
                              u'AMPNAME': u'default',
                              u'AMSTART': 4.4792279,
                              u'AUXPITCH': 0.0,
                              u'AUXROLL': 0.0,
                              u'AZDMD': u'',
                              u'AZIMUTH': 0.0706666,
                              u'AZSTAT': u'OKAY',
                              u'BIASLVL': 1973.494791666667,
                              u'BIASSEC': u'',
                              u'BITPIX': -32,
                              u'BLKAIRCO': u'',
                              u'BLKEDATE': u'2018-02-27T00:25:41',
                              u'BLKMNDST': u'',
                              u'BLKMNPH': u'',
                              u'BLKNOMEX': 4116.0,
                              u'BLKSDATE': u'2018-02-26T23:17:05',
                              u'BLKSEECO': u'',
                              u'BLKTRNCO': u'',
                              u'BLKTYPE': u'POND',
                              u'BLKUID': u'226616444',
                              u'BSCALE': 1.0,
                              u'BZERO': 0.0,
                              u'CAT_DEC': u'NaN',
                              u'CAT_EPOC': 2000.0,
                              u'CAT_RA': u'NaN',
                              u'CCDATEMP': -20.0320677,
                              u'CCDSEC': u'',
                              u'CCDSESIG': u'',
                              u'CCDSTEMP': -20.0045808,
                              u'CCDSUM': u'2 2',
                              u'CCDXPIXE': 9e-06,
                              u'CCDYPIXE': 9e-06,
                              u'CD1_1': 0.0003222,
                              u'CD1_2': 0.0,
                              u'CD2_1': 0.0,
                              u'CD2_2': 0.0003222,
                              u'CHECKSUM': u'BJWAEIV6BIVABIV3',
                              u'CONFMODE': u'',
                              u'CONFNAME': u'',
                              u'CRPIX1': 758.25,
                              u'CRPIX2': 507.25,
                              u'CRVAL1': 42.2781143,
                              u'CRVAL2': -0.16971,
                              u'CTYPE1': u'RA---TAN',
                              u'CTYPE2': u'DEC--TAN',
                              u'CUNIT1': u'deg',
                              u'CUNIT2': u'deg',
                              u'DARKCURR': 0.0,
                              u'DATADICV': u'LCOGT-DIC.FITS-0.11.0',
                              u'DATASEC': u'[1:1550,1:1028]',
                              u'DATASUM': u'198780119',
                              u'DATE': u'2018-02-26',
                              u'DATE_OBS': u'2018-02-27T06:48:55.979000',
                              u'DAY_OBS': u'20180226',
                              u'DEC': u'+72:04:12.33',
                              u'DECTRACK': 0.0,
                              u'DETECTID': u'ccdkb80-1',
                              u'DETECTOR': u'',
                              u'DETSEC': u'',
                              u'DETSIZE': u'[1:0,1:0]',
                              u'ENC1STAT': u'CLOSED',
                              u'ENC2STAT': u'CLOSED',
                              u'ENCAZ': 0.0,
                              u'ENCID': u'aqwa',
                              u'ENCLOSUR': u'Aqawan-01',
                              u'ENCRLIGT': u'OFF',
                              u'ENCWLIGT': u'OFF',
                              u'ENGSTATE': u'',
                              u'EOPSRC': u'IERS BULL. A 2018/02/22',
                              u'EXPTIME': 299.786,
                              u'EXTEND': True,
                              u'EXTNAME': u'SCI',
                              u'FILTER': u'w',
                              u'FILTER1': u'w',
                              u'FILTER2': u'NOTPRESENT',
                              u'FILTER3': u'NOTPRESENT',
                              u'FILTERI1': u'PSTR-WX-124',
                              u'FILTERI2': u'NOTPRESENT',
                              u'FILTERI3': u'NOTPRESENT',
                              u'FOCAFOFF': 1.6191343,
                              u'FOCDMD': 0.0,
                              u'FOCFLOFF': -1.0,
                              u'FOCINOFF': 0.0,
                              u'FOCOBOFF': 0.0,
                              u'FOCPOSN': -0.0071343,
                              u'FOCSTAT': u'HALTED',
                              u'FOCTELZP': 1.5,
                              u'FOCTEMP': 17.6249995,
                              u'FOCTOFF': 0.0359625,
                              u'FOCZOFF': 0.0527706,
                              u'FOLDPORT': u'1',
                              u'FOLDPOSN': u'00.0, N/A',
                              u'FOLDSTAT': u'ERROR',
                              u'FRAMENUM': 18,
                              u'FRMTOTAL': 5,
                              u'FWID': u'p4fw50-01',
                              u'GAIN': 1.0,
                              u'GCOUNT': 1,
                              u'GROUPID': u'LCOGT',
                              u'HDRVER': u'LCOGT-HDR-1.4.0',
                              u'HEIGHT': 2030.0,
                              u'ICSVER': u'master@0xc0b254f',
                              u'INSSTATE': u'OKAY',
                              u'INSTRUME': u'kb80',
                              u'ISSTEMP': u'',
                              u'L1IDBIAS': u'bias_kb80_20180226_bin2x2',
                              u'L1IDMASK': u'bpm_elp_kb80_20171012_bin2x2',
                              u'L1PUBDAT': u'2018-02-27T06:48:55.979000',
                              u'L1STATBI': 1,
                              u'L1STATOV': 0,
                              u'L1STATTR': 1,
                              u'LATITUDE': 30.6800415,
                              u'LONGITUD': -104.015066,
                              u'LST': u'02:50:02.48',
                              u'M1COVER': u'STOWED',
                              u'M1HRTMN': u'STOWED',
                              u'M1TEMP': u'',
                              u'M2PITCH': -166.22,
                              u'M2ROLL': -26.498,
                              u'MAXLIN': 133164.0,
                              u'MJD_OBS': 58175.9715837,
                              u'MOLFRNUM': 1,
                              u'MOLNUM': 3,
                              u'MOLTYPE': u'DARK',
                              u'MOLUID': u'493556972',
                              u'MOONALT': 20.459731,
                              u'MOONDIST': 76.084124,
                              u'MOONFRAC': 0.8790016,
                              u'MOONSTAT': u'UP',
                              u'NAXIS': 2,
                              u'NAXIS1': 1526,
                              u'NAXIS2': 1017,
                              u'OBJECT': u'',
                              u'OBRECIPE': u'',
                              u'OBSGEO_X': -1330017.31,
                              u'OBSGEO_Y': -5328438.752,
                              u'OBSGEO_Z': 3236472.371,
                              u'OBSID': u'300 dark',
                              u'OBSNOTE': u'',
                              u'OBSTELEM': u'',
                              u'OBSTYPE': u'DARK',
                              u'OFSTART': 1400,
                              u'OFSTOP': -10,
                              u'OFST_DEC': u'NaN',
                              u'OFST_RA': u'NaN',
                              u'ORIGIN': u'LCOGT',
                              u'ORIGNAME': link,
                              u'OVERSCAN': 0.0,
                              u'PARALLAX': 0.0,
                              u'PCOUNT': 0,
                              u'PCRECIPE': u'',
                              u'PIPEVER': u'0.7.9dev1212',
                              u'PIXSCALE': 1.16,
                              u'PM_DEC': 0.0,
                              u'PM_RA': 0.0,
                              u'POLARMOX': 0.0022,
                              u'POLARMOY': 0.3359,
                              u'PPRECIPE': u'',
                              u'PROPID': u'calibrate',
                              u'RA': u'14:49:02.155',
                              u'RADESYS': u'ICRS',
                              u'RADVEL': 0.0,
                              u'RATRACK': 0.0,
                              u'RDNOISE': 5.3,
                              u'RDSPEED': 30.0,
                              u'REFHUMID': u'',
                              u'REFPRES': u'',
                              u'REFTEMP': u'',
                              u'REQNUM': None,
                              u'REQTIME': 300.0,
                              u'RLEVEL': 91,
                              u'ROI': u'',
                              u'ROLLERDR': 6.1814493,
                              u'ROLLERND': 6.0029779,
                              u'ROTANGLE': u'',
                              u'ROTDMD': u'',
                              u'ROTMODE': u'FIXED',
                              u'ROTSKYPA': u'',
                              u'ROTSTAT': u'OFF',
                              u'ROTTYPE': u'NONE',
                              u'RWSTART': u'23:19:05.474',
                              u'RWSTOP': u'23:24:06.670',
                              u'SATFRAC': 0.0,
                              u'SATURATE': 153440.0,
                              u'SCHEDNAM': u'POND',
                              u'SCHEDSEE': u'',
                              u'SCHEDTRN': u'',
                              u'SIMPLE': True,
                              u'SITE': u'LCOGT node at McDonald Observatory',
                              u'SITEID': u'elp',
                              u'SKYMAG': 4.1302861,
                              u'SRCTYPE': u'',
                              u'SUNALT': 18.5146595,
                              u'SUNDIST': 106.3795788,
                              u'TAGID': u'LCOGT',
                              u'TCSSTATE': u'OKAY',
                              u'TCSVER': u'0.4',
                              u'TELESCOP': u'0m4-11',
                              u'TELID': u'0m4a',
                              u'TELMODE': u'AUTOMATIC',
                              u'TELSTATE': u'OKAY',
                              u'TIMESYS': u'UTC',
                              u'TPNTMODL': u'20180226124316',
                              u'TPT_DEC': u'NaN',
                              u'TPT_RA': u'NaN',
                              u'TRACKNUM': u'',
                              u'TRIGGER': u'',
                              u'TRIMSEC': u'[11:1536,6:1022]',
                              u'TUBETEMP': 17.6229997,
                              u'USERID': u'ELPOps',
                              u'UT1_UTC': 0.16904,
                              u'UTSTART': u'23:19:06.874',
                              u'UTSTOP': u'23:24:06.660',
                              u'WINDDIR': 193.0,
                              u'WINDSPEE': 19.6560001,
                              u'WMSCLOUD': -23.3893333,
                              u'WMSDEWPT': -7.6999998,
                              u'WMSHUMID': 20.7999992,
                              u'WMSMOIST': 257.6000061,
                              u'WMSPRES': 846.3305789,
                              u'WMSRAIN': u'CLEAR',
                              u'WMSSKYBR': 0.0,
                              u'WMSSTATE': u'OKAY',
                              u'WMSTEMP': 14.5,
                              u'XTENSION': u'BINTABLE',
                              u'ZDITHER0': 7960}}

        return header_out

    # Mock block records output from Valhalla
    # One for each block in superblock. Changed block id's to match blocks
    def mock_check_result_status(tracking_num):
        result_status_out = {u'created': u'2018-02-23T23:56:01.695109Z',
                         u'group_id': u'N999r0q_V38-cad-0223-0227',
                         u'id': 42,
                         u'ipp_value': 1.05,
                         u'modified': u'2018-02-27T05:54:41.007389Z',
                         u'observation_type': u'NORMAL',
                         u'operator': u'MANY',
                         u'proposal': u'LCO2018A-012',
                         u'requests': [{u'acceptability_threshold': 90.0,
                           u'completed': None,
                           u'constraints': {u'max_airmass': 1.74,
                            u'max_lunar_phase': None,
                            u'max_seeing': None,
                            u'min_lunar_distance': 30.0,
                            u'min_transparency': None},
                           u'created': u'2018-02-23T23:56:01.697048Z',
                           u'duration': 9372,
                           u'fail_count': 0,
                           u'id': 3,
                           u'location': {u'site': u'elp', u'telescope_class': u'0m4'},
                           u'modified': u'2018-02-24T11:46:40.239116Z',
                           u'molecules': [{u'acquire_mode': u'OFF',
                             u'acquire_radius_arcsec': 0.0,
                             u'acquire_strategy': u'',
                             u'ag_exp_time': 10.0,
                             u'ag_filter': u'',
                             u'ag_mode': u'OPTIONAL',
                             u'ag_name': u'',
                             u'ag_strategy': u'',
                             u'args': u'',
                             u'bin_x': 2,
                             u'bin_y': 2,
                             u'defocus': None,
                             u'expmeter_mode': u'OFF',
                             u'expmeter_snr': None,
                             u'exposure_count': 386,
                             u'exposure_time': 10.0,
                             u'filter': u'w',
                             u'instrument_name': u'0M4-SCICAM-SBIG',
                             u'priority': 1,
                             u'readout_mode': u'',
                             u'spectra_lamp': u'',
                             u'spectra_slit': u'',
                             u'type': u'EXPOSE'}],
                           u'observation_note': u'Submitted by NEOexchange (by tlister@lcogt.net)',
                           u'scheduled_count': 0,
                           u'state': u'WINDOW_EXPIRED',
                           u'target': {u'acquire_mode': None,
                            u'argofperih': 180.74461,
                            u'eccentricity': 0.2695826,
                            u'epochofel': 58200.0,
                            u'longascnode': 347.31601,
                            u'meananom': 8.89267,
                            u'meandist': 1.36967423,
                            u'name': u'N999r0q',
                            u'orbinc': 9.2247,
                            u'rot_angle': 0.0,
                            u'rot_mode': u'',
                            u'scheme': u'MPC_MINOR_PLANET',
                            u'type': u'NON_SIDEREAL',
                            u'vmag': None},
                           u'windows': [{u'end': u'2018-02-24T11:45:00Z',
                             u'start': u'2018-02-24T03:45:00Z'}]},
                          {u'acceptability_threshold': 90.0,
                           u'completed': None,
                           u'constraints': {u'max_airmass': 1.74,
                            u'max_lunar_phase': None,
                            u'max_seeing': None,
                            u'min_lunar_distance': 30.0,
                            u'min_transparency': None},
                           u'created': u'2018-02-23T23:56:01.704260Z',
                           u'duration': 9372,
                           u'fail_count': 0,
                           u'id': 1430663,
                           u'location': {u'site': u'elp', u'telescope_class': u'0m4'},
                           u'modified': u'2018-02-25T11:47:06.795120Z',
                           u'molecules': [{u'acquire_mode': u'OFF',
                             u'acquire_radius_arcsec': 0.0,
                             u'acquire_strategy': u'',
                             u'ag_exp_time': 10.0,
                             u'ag_filter': u'',
                             u'ag_mode': u'OPTIONAL',
                             u'ag_name': u'',
                             u'ag_strategy': u'',
                             u'args': u'',
                             u'bin_x': 2,
                             u'bin_y': 2,
                             u'defocus': None,
                             u'expmeter_mode': u'OFF',
                             u'expmeter_snr': None,
                             u'exposure_count': 386,
                             u'exposure_time': 10.0,
                             u'filter': u'w',
                             u'instrument_name': u'0M4-SCICAM-SBIG',
                             u'priority': 1,
                             u'readout_mode': u'',
                             u'spectra_lamp': u'',
                             u'spectra_slit': u'',
                             u'type': u'EXPOSE'}],
                           u'observation_note': u'Submitted by NEOexchange (by tlister@lcogt.net)',
                           u'scheduled_count': 0,
                           u'state': u'WINDOW_EXPIRED',
                           u'target': {u'acquire_mode': None,
                            u'argofperih': 180.74461,
                            u'eccentricity': 0.2695826,
                            u'epochofel': 58200.0,
                            u'longascnode': 347.31601,
                            u'meananom': 8.89267,
                            u'meandist': 1.36967423,
                            u'name': u'N999r0q',
                            u'orbinc': 9.2247,
                            u'rot_angle': 0.0,
                            u'rot_mode': u'',
                            u'scheme': u'MPC_MINOR_PLANET',
                            u'type': u'NON_SIDEREAL',
                            u'vmag': None},
                           u'windows': [{u'end': u'2018-02-25T11:45:00Z',
                             u'start': u'2018-02-25T03:45:00Z'}]},
                          {u'acceptability_threshold': 90.0,
                           u'completed': None,
                           u'constraints': {u'max_airmass': 1.74,
                            u'max_lunar_phase': None,
                            u'max_seeing': None,
                            u'min_lunar_distance': 30.0,
                            u'min_transparency': None},
                           u'created': u'2018-02-23T23:56:01.709915Z',
                           u'duration': 9372,
                           u'fail_count': 0,
                           u'id': 15,
                           u'location': {u'site': u'elp', u'telescope_class': u'0m4'},
                           u'modified': u'2018-02-26T11:47:31.639510Z',
                           u'molecules': [{u'acquire_mode': u'OFF',
                             u'acquire_radius_arcsec': 0.0,
                             u'acquire_strategy': u'',
                             u'ag_exp_time': 10.0,
                             u'ag_filter': u'',
                             u'ag_mode': u'OPTIONAL',
                             u'ag_name': u'',
                             u'ag_strategy': u'',
                             u'args': u'',
                             u'bin_x': 2,
                             u'bin_y': 2,
                             u'defocus': None,
                             u'expmeter_mode': u'OFF',
                             u'expmeter_snr': None,
                             u'exposure_count': 386,
                             u'exposure_time': 10.0,
                             u'filter': u'w',
                             u'instrument_name': u'0M4-SCICAM-SBIG',
                             u'priority': 1,
                             u'readout_mode': u'',
                             u'spectra_lamp': u'',
                             u'spectra_slit': u'',
                             u'type': u'EXPOSE'}],
                           u'observation_note': u'Submitted by NEOexchange (by tlister@lcogt.net)',
                           u'scheduled_count': 0,
                           u'state': u'WINDOW_EXPIRED',
                           u'target': {u'acquire_mode': None,
                            u'argofperih': 180.74461,
                            u'eccentricity': 0.2695826,
                            u'epochofel': 58200.0,
                            u'longascnode': 347.31601,
                            u'meananom': 8.89267,
                            u'meandist': 1.36967423,
                            u'name': u'N999r0q',
                            u'orbinc': 9.2247,
                            u'rot_angle': 0.0,
                            u'rot_mode': u'',
                            u'scheme': u'MPC_MINOR_PLANET',
                            u'type': u'NON_SIDEREAL',
                            u'vmag': None},
                           u'windows': [{u'end': u'2018-02-26T11:45:00Z',
                             u'start': u'2018-02-26T03:45:00Z'}]},
                          {u'acceptability_threshold': 90.0,
                           u'completed': u'2018-02-27T05:54:40.984190Z',
                           u'constraints': {u'max_airmass': 1.74,
                            u'max_lunar_phase': None,
                            u'max_seeing': None,
                            u'min_lunar_distance': 30.0,
                            u'min_transparency': None},
                           u'created': u'2018-02-23T23:56:01.715505Z',
                           u'duration': 9372,
                           u'fail_count': 0,
                           u'id': 9,
                           u'location': {u'site': u'elp', u'telescope_class': u'0m4'},
                           u'modified': u'2018-02-27T05:54:40.986064Z',
                           u'molecules': [{u'acquire_mode': u'OFF',
                             u'acquire_radius_arcsec': 0.0,
                             u'acquire_strategy': u'',
                             u'ag_exp_time': 10.0,
                             u'ag_filter': u'',
                             u'ag_mode': u'OPTIONAL',
                             u'ag_name': u'',
                             u'ag_strategy': u'',
                             u'args': u'',
                             u'bin_x': 2,
                             u'bin_y': 2,
                             u'defocus': None,
                             u'expmeter_mode': u'OFF',
                             u'expmeter_snr': None,
                             u'exposure_count': 386,
                             u'exposure_time': 10.0,
                             u'filter': u'w',
                             u'instrument_name': u'0M4-SCICAM-SBIG',
                             u'priority': 1,
                             u'readout_mode': u'',
                             u'spectra_lamp': u'',
                             u'spectra_slit': u'',
                             u'type': u'EXPOSE'}],
                           u'observation_note': u'Submitted by NEOexchange (by tlister@lcogt.net)',
                           u'scheduled_count': 0,
                           u'state': u'COMPLETED',
                           u'target': {u'acquire_mode': None,
                            u'argofperih': 180.74461,
                            u'eccentricity': 0.2695826,
                            u'epochofel': 58200.0,
                            u'longascnode': 347.31601,
                            u'meananom': 8.89267,
                            u'meandist': 1.36967423,
                            u'name': u'N999r0q',
                            u'orbinc': 9.2247,
                            u'rot_angle': 0.0,
                            u'rot_mode': u'',
                            u'scheme': u'MPC_MINOR_PLANET',
                            u'type': u'NON_SIDEREAL',
                            u'vmag': None},
                           u'windows': [{u'end': u'2018-02-27T11:45:00Z',
                             u'start': u'2018-02-27T03:45:00Z'}]}],
                         u'state': u'COMPLETED',
                         u'submitter': u'neox_robot'}
        return result_status_out

    def mock_check_request_status_spectro(tracking_num):
        result_status_out = {u'created': u'2018-01-10T22:58:32.524744Z',
                             u'group_id': u'8_F65-20180111_spectra',
                             u'id': 557017,
                             u'ipp_value': 1.0,
                             u'modified': u'2018-01-11T06:49:53.678461Z',
                             u'observation_type': u'NORMAL',
                             u'operator': u'SINGLE',
                             u'proposal': u'LCOEngineering',
                             u'requests': [{u'acceptability_threshold': 90.0,
                               u'completed': u'2018-01-11T06:49:53.665958Z',
                               u'constraints': {u'max_airmass': 1.74, u'min_lunar_distance': 30.0},
                               u'created': u'2018-01-10T22:58:32.526661Z',
                               u'duration': 845,
                               u'fail_count': 0,
                               u'id': 1391169,
                               u'location': {u'site': u'ogg', u'telescope_class': u'2m0'},
                               u'modified': u'2018-01-11T06:49:53.667734Z',
                               u'molecules': [{
                                 u'bin_x': 1, u'bin_y': 1,
                                 u'exposure_count': 1,
                                 u'exposure_time': 60.0,
                                 u'filter': u'',
                                 u'instrument_name': u'2M0-FLOYDS-SCICAM',
                                 u'spectra_slit': u'slit_2.0as',
                                 u'type': u'LAMP_FLAT'},
                                {
                                 u'bin_x': 1, u'bin_y': 1,
                                 u'exposure_count': 1,
                                 u'exposure_time': 60.0,
                                 u'filter': u'',
                                 u'instrument_name': u'2M0-FLOYDS-SCICAM',
                                 u'spectra_slit': u'slit_2.0as',
                                 u'type': u'ARC'},
                                {
                                 u'bin_x': 1, u'bin_y': 1,
                                 u'exposure_count': 1,
                                 u'exposure_time': 300.0,
                                 u'filter': u'',
                                 u'instrument_name': u'2M0-FLOYDS-SCICAM',
                                 u'spectra_lamp': u'',
                                 u'spectra_slit': u'slit_2.0as',
                                 u'type': u'SPECTRUM'}],
                               u'observation_note': u'Submitted by NEOexchange (by tlister@lcogt.net)',
                               u'scheduled_count': 0,
                               u'state': u'COMPLETED',
                               u'target': {u'acquire_mode': None,
                                u'name': u'8',
                                u'rot_mode': u'VFLOAT',
                                u'scheme': u'MPC_MINOR_PLANET',
                                u'type': u'NON_SIDEREAL',
                                u'vmag': None},
                               u'windows': [{u'end': u'2018-01-11T15:50:00Z',
                                 u'start': u'2018-01-11T05:00:00Z'}]}],
                             u'state': u'COMPLETED',
                             u'submitter': u'tlister@lcogt.net'}
        return result_status_out

    @patch('core.frames.lco_api_call', side_effect=mock_lco_api_call)
    @patch('core.frames.check_request_status', side_effect=mock_check_result_status)
    @patch('core.frames.check_for_archive_images', side_effect=mock_check_for_archive_images)
    def test_block_status_updates_num_observed(self, check_request_status, check_for_archive_images, lco_api_call):
        expected = ('3/4', '0/4')

        blocks = Block.objects.filter(superblock=self.super_block, active=True)
        self.assertEqual(4, blocks.count())
        for block in blocks:
            block_status(block.id)

        result = self.body.get_block_info()
        self.assertEqual(expected, result)

    @patch('core.frames.lco_api_call', side_effect=mock_lco_api_call)
    @patch('core.frames.check_request_status', side_effect=mock_check_result_status)
    @patch('core.frames.check_for_archive_images', side_effect=mock_check_for_archive_images)
    def test_correct_frames_per_block(self, check_request_status, check_for_archive_images, lco_api_call):
        expected = ['1test_3.fits', '2test_3.fits', '3test_3.fits']
        blocks = Block.objects.filter(active=True)
        for block in blocks:
            block_status(block.id)

        frame_names_blk1 = []
        frames = Frame.objects.filter(block=blocks[0])
        for frame in frames:
            frame_names_blk1.append(frame.filename)
        self.assertEqual(expected, frame_names_blk1)

        frame_names_blk2 = []
        frames = Frame.objects.filter(block=blocks[1])
        for frame in frames:
            frame_names_blk2.append(frame.filename)
        for element in expected:
            self.assertNotIn(element, frame_names_blk2)

    @patch('core.frames.check_request_status', mock_check_request_status_spectro)
    @patch('core.archive_subs.fetch_archive_frames', mock_fetch_archive_frames)
    @patch('core.frames.lco_api_call', mock_archive_frame_header)
    def test_check_spectro_block(self):
        self.insert_spectro_blocks()

        self.assertEqual(0, self.spec_test_block1.num_observed)
        status = block_status(self.spec_test_block1.id)

        self.assertEqual(True, status)
        spec_block = Block.objects.get(id=self.spec_test_block1.id)
        self.assertEqual(1, spec_block.num_observed)


class TestFrameParamsFromHeader(TestCase):

    def setUp(self):
        # Initialise with a test body, test proposal, and SuperBlock
        params = {  'provisional_name' : 'N999r0q',
                    'abs_mag'       : 21.0,
                    'slope'         : 0.15,
                    'epochofel'     : '2015-03-19 00:00:00',
                    'meananom'      : 325.2636,
                    'argofperih'    : 85.19251,
                    'longascnode'   : 147.81325,
                    'orbinc'        : 8.34739,
                    'eccentricity'  : 0.1896865,
                    'meandist'      : 1.2176312,
                    'source_type'   : 'U',
                    'elements_type' : 'MPC_MINOR_PLANET',
                    'active'        : True,
                    'origin'        : 'M',
                    }
        self.body, created = Body.objects.get_or_create(**params)

        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)

        sb_params = {  'cadence'       : False,
                       'body'          : self.body,
                       'proposal'      : self.neo_proposal,
                       'block_start'   : '2015-04-20 13:00:00',
                       'block_end'     : '2015-04-21 03:00:00',
                       'tracking_number' : '00042',
                       'active'        : True
                    }
        self.super_block, created = SuperBlock.objects.get_or_create(**sb_params)

        # Create test blocks
        block_params = { 'telclass' : '0m4',
                         'site'     : 'elp',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'superblock'  : self.super_block,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00003',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True,
                         'num_observed' : 0,
                         'reported' : False
                       }
        self.test_block = Block.objects.create(**block_params)

        self.maxDiff = None

    def test_expose_red_good_rlevel(self):
        expected_params = {  'midpoint' : datetime(2015, 4, 20, 16, 00, 14, int(0.409*1e6)),
                             'sitecode' : 'V38',
                             'filter'   : 'w',
                             'frametype': 91,
                             'block'    : self.test_block,
                             'instrument': 'kb92',
                             'filename'  : 'elp0m411-kb92-20150420-0236-e91.fits',
                             'exptime'   : 20.0,
                             'wcs'       : WCS() }

        header_params = { 'SITEID'   : 'elp',
                          'ENCID'    : 'aqwa',
                          'TELID'    : '0m4a',
                          'DATE_OBS' : '2015-04-20T16:00:04.409',
                          'EXPTIME'  : 20.0,
                          'INSTRUME' : 'kb92',
                          'FILTER'   : 'w',
                          'OBSTYPE'  : 'EXPOSE',
                          'ORIGNAME' : 'elp0m411-kb92-20150420-0236-e00',
                          'RLEVEL'   : 91,
                          'L1FWHM'   : 1.42
                        }

        frame_params = frame_params_from_header(header_params, self.test_block)

        for key in expected_params:
            if key != 'wcs':
                self.assertEqual(expected_params[key], frame_params[key], "Comparison failed on " + key)

    def test_expose_red_bad_rlevel(self):
        expected_params = {  'midpoint' : datetime(2015, 4, 20, 16, 00, 14, int(0.409*1e6)),
                             'sitecode' : 'V38',
                             'filter'   : 'w',
                             'frametype': 91,
                             'block'    : self.test_block,
                             'instrument': 'kb92',
                             'filename'  : 'elp0m411-kb92-20150420-0236-e91.fits',
                             'exptime'   : 20.0,
                             'wcs'       : WCS() }

        header_params = { 'SITEID'   : 'elp',
                          'ENCID'    : 'aqwa',
                          'TELID'    : '0m4a',
                          'DATE_OBS' : '2015-04-20T16:00:04.409',
                          'EXPTIME'  : 20.0,
                          'INSTRUME' : 'kb92',
                          'FILTER'   : 'w',
                          'OBSTYPE'  : 'EXPOSE',
                          'ORIGNAME' : 'elp0m411-kb92-20150420-0236-e00',
                          'RLEVEL'   : '91',
                          'L1FWHM'   : 1.42
                        }

        frame_params = frame_params_from_header(header_params, self.test_block)

        for key in expected_params:
            if key != 'wcs':
                self.assertEqual(expected_params[key], frame_params[key], "Comparison failed on " + key)
