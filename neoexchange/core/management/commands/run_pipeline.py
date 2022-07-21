import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from dramatiq import pipeline

from core.tasks import run_pipeline, send_task
from core.models import PipelineProcess
from core.views import determine_images_and_catalogs

class Command(BaseCommand):

    help = 'Start at a pipeline runner'

    def add_arguments(self, parser):
        default_path = os.path.join(os.path.sep, 'data', 'eng', 'rocks')
        default_tempdir = 'Temp_cvc'
        parser.add_argument('--date', action="store", default=datetime.utcnow(), help='Date of the data to process (YYYYMMDD)')
        parser.add_argument('--datadir', action="store", default=default_path, help='Path for processed data (e.g. /data/eng/rocks)')
        parser.add_argument('--refcat',
                    default='GAIA-DR2',
                    const='GAIA-DR2',
                    nargs='?',
                    choices=['GAIA-DR2', 'PS1', 'REFCAT2'],
                    help='Reference catalog: choice of GAIA-DR2, PS1, REFCAT2 (default: %(default)s)')
        parser.add_argument('--tempdir', action="store", default=default_tempdir, help=f'Temporary processing directory name (e.g. {default_tempdir}')

    def handle(self, *args, **options):
        # Path to directory containing some e91 BANZAI files (this one is a local copy of a recent one from /apophis/eng/rocks)
        # XXX Should just be able to give this via --datadir now
        #dataroot = '/Users/egomez/Downloads/neox/C_2021A1_391911468/'
        dataroot = options['datadir']

        if isinstance(options['date'], str):
            try:
                obs_date = datetime.strptime(options['date'], '%Y%m%d')
            except ValueError:
                raise CommandError(usage)
        else:
            obs_date = options['date']

        obs_date = obs_date.strftime('%Y%m%d')

        # Check for valid dataroot. Try original `dataroot`, then `dataroot/obs_date`
        if os.path.exists(dataroot) is False:
            dataroot2 = os.path.join(dataroot, obs_date)
            if os.path.exists(dataroot2) is False:
                raise CommandError(f"Dataroot {dataroot:} or {dataroot2:} don't exist. Halting")
            else:
                dataroot = dataroot2

        # Ensure trailing slash is present
        dataroot = os.path.join(dataroot, '')
        fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot)

        temp_dir = options['tempdir']
        for fits_file in fits_files:
            steps = [{
                        'name'   : 'proc-extract',
                        'inputs' : {'fits_file':fits_file,
                                   'datadir': os.path.join(dataroot, temp_dir)}
                    },
                    {
                        'name'   : 'proc-astromfit',
                        'inputs' : {'fits_file' : fits_file,
                                    'ldac_catalog' : os.path.join(dataroot, temp_dir, fits_file.replace('e91.fits', 'e91_ldac.fits')),
                                    'datadir' : os.path.join(dataroot, temp_dir)
                                    }
                    },
                    {
                        'name'   : 'proc-zeropoint',
                        'inputs' : {'ldac_catalog' : os.path.join(dataroot, temp_dir, fits_file.replace('e91.fits', 'e92_ldac.fits')),
                                    'datadir' : os.path.join(dataroot, temp_dir),
                                    'desired_catalog' : options['refcat']
                                    }
                    }]
            self.stdout.write(f"Running pipeline on {fits_file}:")

            pipes = []
            for step in steps:
                pipeline_cls = PipelineProcess.get_subclass(step['name'])
                inputs = {f: pipeline_cls.inputs[f]['default'] for f in pipeline_cls.inputs}
                inputs.update(step['inputs'])
                self.stdout.write(f"  Performing pipeline step {step['name']}")
                pipe = pipeline_cls.create_timestamped(inputs)
                pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
            runner  = pipeline(pipes).run()
