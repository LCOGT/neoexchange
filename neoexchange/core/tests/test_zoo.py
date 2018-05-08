"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2017-2018 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import glob
import os
import logging
import csv
import json
import tempfile
import shutil

from panoptes_client import SubjectSet, Subject, Panoptes, Project
from panoptes_client.panoptes import PanoptesAPIException
from django.test import TestCase
from django.conf import settings
from numpy import mean, sqrt
from mock import patch, Mock
import requests

from core.models import Frame, Block, PanoptesReport, CatalogSources, Proposal, Body
from core.zoo import download_images_block, download_image, panoptes_add_set_mtd, \
    create_panoptes_report, identify_sources


def mock_download_image(frame, current_files, download_dir, blockid):
    return 'myfile.fits'


def mock_create_mosaic(filename, frame_id, download_dir):
    return ['myfile1.jpg', 'myfile2.jpg']


def mock_convert_coords(x, y, quad, xscale, yscale, xsize, ysize):
    return 195.0, 205.0, 340., 345.0


class TestPanoptes(TestCase):

    def setUp(self):
        neo_proposal_params = { 'code'  : 'LCO2015A-009',
                                'title' : 'LCOGT NEO Follow-up Network'
                              }
        self.neo_proposal, created = Proposal.objects.get_or_create(**neo_proposal_params)
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
                    'ingest'        : '2015-05-11 17:20:00',
                    'score'         : 90,
                    'discovery_date': '2015-05-10 12:00:00',
                    'update_time'   : '2015-05-18 05:00:00',
                    'num_obs'       : 17,
                    'arc_length'    : 3.0,
                    'not_seen'      : 0.42,
                    'updated'       : True
                    }
        self.body, created = Body.objects.get_or_create(pk=1, **params)

        block_params = { 'telclass' : '1m0',
                         'site'     : 'cpt',
                         'body'     : self.body,
                         'proposal' : self.neo_proposal,
                         'block_start' : '2015-04-20 13:00:00',
                         'block_end'   : '2015-04-21 03:00:00',
                         'tracking_number' : '00042',
                         'num_exposures' : 5,
                         'exp_length' : 42.0,
                         'active'   : True
                       }
        self.block = Block.objects.create(pk=1, **block_params)

        frame_params = {'sitecode'  : 'F65',
                        'filter'    : 'w',
                        'midpoint'  : '2015-05-11 17:20:00',
                        'frametype' : 91,
                        'frameid'   : 99,
                        'astrometric_catalog': 'Y',
                        'photometric_catalog': 'X'
                        }
        self.frame = Frame.objects.create(pk=1, **frame_params)

        catsource_params = {
                            'frame' : self.frame,
                            'obs_x' : 199.0,
                            'obs_y' : 343.0,
                            'obs_ra': 12.99,
                            'obs_dec' : -20.2,
                            'background' : 10.2,
                            'major_axis' : 10.2,
                            'minor_axis' : 10.2,
                            'position_angle' : 10.2,
                            'ellipticity' : 10.2
                            }
        self.catsource1 = CatalogSources.objects.create(pk=1, **catsource_params)
        catsource_params['obs_y'] = 200.0
        self.catsource2 = CatalogSources.objects.create(pk=2, **catsource_params)
        self.download_dir = '/my-downloads/'
        self.scale = 2.3


    @patch('core.zoo.download_image', mock_download_image)
    @patch('core.zoo.create_mosaic', mock_create_mosaic)
    def _download_images_block(self):
        frames = [
            {'id':1,},
            {'id':2,}
        ]
        mosaicfiles = download_images_block(self.block.id, frames, self.scale, self.download_dir)
        self.assertEqual(mosaicfiles,['myfile1.jpg','myfile2.jpg','myfile1.jpg','myfile2.jpg'])
        return

    def _download_image(self):
        download_dir = tempfile.mkdtemp()
        current_files = []
        frame = {'id':1, 'url':'https://lco.global/files/null/.thumbnails/feature-spacebook2.jpg/feature-spacebook2-144x81.jpg'}
        file_name = 'block_%s_%s.jpg' % (self.block.id, frame['id'])
        filename = os.path.join(download_dir, file_name)
        # Try first without any current files
        filename_compare = download_image(frame, current_files, download_dir, self.block.id)
        self.assertEqual(filename, filename_compare)
        # Next try with pass file back in current files
        current_files.append(filename)
        filename_compare = download_image(frame, current_files, download_dir, self.block.id)
        self.assertEqual(filename, filename_compare)
        shutil.rmtree(download_dir)

        return

    @patch('core.zoo.Panoptes', Mock())
    @patch('core.zoo.Subject', Mock())
    @patch('core.zoo.SubjectSet', Mock())
    @patch('core.zoo.Project', autospec=True)
    def _panoptes_add_set(self, mock_project):
        mock_project.list = Mock()
        mock_project.list.workspace = Mock(return_value=[{'id':1}])
        files = ['myfile-1.jpg','myfile2-1.jpg']
        num_segments = 1
        subject_ids = panoptes_add_set_mtd(files, num_segments, self.block.id, self.download_dir)
        self.assertEqual(subject_ids, [])
        return

    def _convert_coords(self):

        coord_range = convert_coords(200,300,0,640,640, 640,640)
        coord_range_test = (195.0, 205.0, 335.0, 345.0)
        self.assertEqual(coord_range, coord_range_test)

    def _create_panoptes_report(self):
        subjects = [
            {'quad':4,'id':1},
            {'quad':4,'id':2}
        ]
        no_reports = PanoptesReport.objects.all().count()
        self.assertEqual(no_reports, 0)
        create_panoptes_report(self.block, subjects)
        no_reports = PanoptesReport.objects.all().count()
        self.assertEqual(no_reports, 1)
        return

    @patch('core.zoo.convert_coords',mock_convert_coords)
    def _identify_sources(self):
        subjects = {
            '1': [{'frame':'frame-99-x.fits','x':200,'y':200,'quad':3}],
            '2': [{'frame':'frame-99-x.fits','x':200,'y':200,'quad':3}]
        }
        returns = identify_sources(subjects)
        returns_test = [(self.catsource1,2)]
        self.assertEqual(returns, returns_test)
