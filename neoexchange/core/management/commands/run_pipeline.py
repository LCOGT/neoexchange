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
                    choices=['GAIA-DR2', 'PS1', 'REFCAT2', 'SkyMapper'],
                    help='Reference catalog: choice of GAIA-DR2, PS1, REFCAT2, SkyMapper (default: %(default)s)')
        parser.add_argument('--tempdir', action="store", default=default_tempdir, help=f'Temporary processing directory name (e.g. {default_tempdir}')
        parser.add_argument('--zp_tolerance', type=float, default=0.1, help='Tolerance on zeropoint std.dev for a good fit (default: %(default)s) mag')
        parser.add_argument('--overwrite', default=False, action='store_true', help='Whether to ignore existing files/DB entries and overwrite')

    def handle(self, *args, **options):
        # Path to directory containing some e91 BANZAI files
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
                raise CommandError(f"Dataroot {dataroot} or {dataroot2} don't exist. Halting")
            else:
                dataroot = dataroot2

        # Ensure trailing slash is present
        dataroot = os.path.join(dataroot, '')
        fits_files, fits_catalogs = determine_images_and_catalogs(self, dataroot)

        if fits_files is None or len(fits_files) == 0:
            raise CommandError(f"No FITS files found in {dataroot}")

        # Process all files through all pipeline steps
        for fits_filepath in fits_files:
            # fits_filepath is the full path including the dataroot and obs_date e.g. /apophis/eng/rocks/20220731/cpt1m010-fa16-20220731-0146-e91.fits
            # fits_file is the basename e.g. cpt1m010-fa16-20220731-0146-e91.fits
            fits_file = os.path.basename(fits_filepath)
            steps = [{
                        'name'   : 'proc-extract',
                        'inputs' : {'fits_file':fits_filepath,
                                   'datadir': os.path.join(dataroot, options['tempdir']),
                                   'overwrite' : options['overwrite']}
                    },
                    {
                        'name'   : 'proc-astromfit',
                        'inputs' : {'fits_file' : fits_filepath,
                                    'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace('e91.fits', 'e91_ldac.fits')),
                                    'datadir' : os.path.join(dataroot, options['tempdir'])
                                    }
                    },
                    {
                        'name'   : 'proc-zeropoint',
                        'inputs' : {'ldac_catalog' : os.path.join(dataroot, options['tempdir'], fits_file.replace('e91.fits', 'e92_ldac.fits')),
                                    'datadir' : os.path.join(dataroot, options['tempdir']),
                                    'zeropoint_tolerance' : options['zp_tolerance'],
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
#                self.stdout.write(f"  PK={pipe.pk} for {step['name']}")
                pipes.append(run_pipeline.message_with_options(args=[pipe.pk, step['name']], pipe_ignore=True))
            runner  = pipeline(pipes).run()
        self.stdout.write("Waiting for pipeline to complete")
        runner.get_result(block=True, timeout=180_000*len(fits_files))
        self.stdout.write("Completed")
