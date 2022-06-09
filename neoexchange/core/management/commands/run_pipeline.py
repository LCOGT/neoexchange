import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from core.tasks import run_pipeline, send_task
from core.models import PipelineProcess


class Command(BaseCommand):

    help = 'Start at a pipeline runner'

    def add_arguments(self, parser):
        default_path = os.path.join(os.path.sep, 'data', 'eng', 'rocks')
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to download (YYYYMMDD)')
        parser.add_argument('--datadir', action="store", default=default_path, help='Path for processed data (e.g. /data/eng/rocks)')


    def handle(self, *args, **options):
        # Path to directory containing some e91 BANZAI files (this one is a local copy of a recent one from /apophis/eng/rocks)
        dataroot = '/Users/egomez/Downloads/neox/C_2021A1_391911468/'

        steps = [{
                    'name'   : 'proc-extract',
                    'inputs' : {'fits_file':os.path.join(dataroot, 'cpt1m010-fa16-20220531-0213-e91.fits'),
                               'datadir': os.path.join(dataroot, 'Temp')}
                },
                {
                    'name'   : 'proc-astromfit',
                    'inputs' : {'fits_file' : os.path.join(dataroot, 'cpt1m010-fa16-20220531-0213-e91.fits'),
                                'ldac_catalog' : os.path.join(dataroot, 'Temp', 'cpt1m010-fa16-20220531-0213-e91_ldac.fits'),
                                'datadir' : os.path.join(dataroot, 'Temp')
                                }
                }]

        for step in steps:
            pipeline_cls = PipelineProcess.get_subclass(step['name'])
            inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
            inputs.update(step['inputs'])
            pipe = pipeline_cls.create_timestamped(inputs)
            send_task(run_pipeline, pipe, step['name'])
