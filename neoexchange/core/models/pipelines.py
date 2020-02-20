from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime
import json
import tempfile
from pathlib import Path
import re
import os.path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils.module_loading import import_string
from core.models.frame import Frame

from core.models.async_process import AsyncError, AsyncProcess, ASYNC_STATUS_CREATED
from tom_education.utils import assert_valid_suffix


class InvalidPipelineError(Exception):
    """
    Failed to import a PipelineProcess subclass from settings
    """


PipelineOutput = namedtuple('PipelineOutput', ['path', 'output_type'], defaults=('',))


class PipelineProcess(AsyncProcess):
    short_name = 'pipeline'
    flags = None
    allowed_suffixes = None

    logs = models.TextField(null=True, blank=True)
    flags_json = models.TextField(null=True, blank=True)

    def run(self):
        if not self.input_files.exists():
            raise AsyncError('No input files to process')

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)

            # Do the actual work
            flags = json.loads(self.flags_json) if self.flags_json else {}
            try:
                outputs = self.do_pipeline(tmpdir, **flags)
                for output in outputs:
                    if not isinstance(output, PipelineOutput):
                        output = PipelineOutput(*output)

                    path, output_type = output
                    identifier = f'{self.identifier}_{path.name}'
            except:
                raise AsyncError(f"Invalid output type '{output_type}'")

        self.status = ASYNC_STATUS_CREATED
        self.save()

    def do_pipeline(self, tmpdir):
        """
        Perform the actual work, and return a sequence of PipelineOutput
        objects (or tuples) for each output file to be saved.

        Should raise AsyncError(failure_message) on failure
        """
        raise NotImplementedError('Must be implemented in child classes')

    @contextmanager
    def update_status(self, status):
        self.status = status
        self.save()
        yield None

    def log(self, msg, end='\n'):
        if not self.logs:
            self.logs = ''
        self.logs += msg + end
        self.save()

    @classmethod
    def get_available(cls):
        """
        Return the pipelines dict from settings.py
        """
        return getattr(settings, 'PIPELINES', {})

    @classmethod
    def get_subclass(cls, name):
        """
        Return the sub-class corresponding to the name given
        """
        try:
            pipeline_cls = import_string(cls.get_available()[name])
        except ImportError as ex:
            raise InvalidPipelineError(ex)

        # Check imported object is a class, and has PipelineProcess as a parent
        err = '{} does not look like a PipelineProcess sub-class'.format(pipeline_cls)
        try:
            if not issubclass(pipeline_cls, PipelineProcess):
                raise InvalidPipelineError(err)
        except TypeError:  # TypeError raised by issubclass() if first arg is not a class
            raise InvalidPipelineError(err)

        try:
            cls.validate_flags(pipeline_cls.flags)
        except AssertionError:
            raise InvalidPipelineError("Invalid 'flags' attribute in {}".format(pipeline_cls))
        return pipeline_cls

    @classmethod
    def validate_flags(cls, flags):
        """
        Validate a class's `flags` attribute. Raises AssertionError if
        invalid
        """
        if flags is None:
            return
        assert isinstance(flags, dict)
        # `name` will be used as an ID in the HTML, so must not contain
        # whitespace
        for name, info in flags.items():
            assert re.match(r'[^\s]+$', name)
            assert isinstance(info, dict)
            assert 'default' in info
            assert 'long_name' in info

    @classmethod
    def create_timestamped(cls, target, products, flags=None):
        date_str = datetime.now().strftime('%Y%m%d%H%M%S')
        identifier = f'{cls.short_name}_{target.pk}_{date_str}'
        kwargs = {
            'identifier': identifier,
            'target': target
        }
        if flags:
            kwargs['flags_json'] = json.dumps(flags)

        pipe = cls.objects.create(**kwargs)
        pipe.input_files.add(*products)
        pipe.save()
        return pipe
