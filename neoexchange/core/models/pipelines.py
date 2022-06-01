from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime, date
import json
import dateutil.parser
import tempfile
from pathlib import Path
import re
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils.module_loading import import_string
from core.models.frame import Frame

from core.models.async_process import AsyncError, AsyncProcess, ASYNC_STATUS_CREATED

logger = logging.getLogger('pipelines')

class InvalidPipelineError(Exception):
    """
    Failed to import a PipelineProcess subclass from settings
    """


PipelineOutput = namedtuple('PipelineOutput', ['msg'])

class DateTimeEncoder(json.JSONEncoder):
        #Override the default method
        def default(self, obj):
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()

def decode_datetime(empDict):
    for date_key in ['obs_date', 'start_date', 'end_date']:
        if date_key in empDict:
            empDict[date_key] = dateutil.parser.parse(empDict[date_key])
    return empDict

class PipelineProcess(AsyncProcess):
    short_name = 'pipeline'
    inputs = None
    allowed_suffixes = None

    logs = models.TextField(null=True, blank=True)
    inputs_json = models.TextField(null=True, blank=True)

    def run(self):

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)

            # Do the actual work
            inputs = json.loads(self.inputs_json, object_hook=decode_datetime) if self.inputs_json else {}
            if inputs is None or inputs == {}:
                raise AsyncError("Error: empty inputs dictionary")

            try:
                self.do_pipeline(tmpdir, **inputs)
            except Exception as e:
                raise AsyncError(f"Error: '{e}'")

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
        logger.debug(msg)
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
            cls.validate_inputs(pipeline_cls.inputs)
        except AssertionError:
            raise InvalidPipelineError("Invalid 'inputs' attribute in {}".format(pipeline_cls))
        return pipeline_cls

    @classmethod
    def validate_inputs(cls, inputs):
        """
        Validate a class's `inputs` attribute. Raises AssertionError if
        invalid
        """
        if inputs is None:
            return
        assert isinstance(inputs, dict)
        # `name` will be used as an ID in the HTML, so must not contain
        # whitespace
        for name, info in inputs.items():
            assert re.match(r'[^\s]+$', name)
            assert isinstance(info, dict)
            assert 'default' in info
            assert 'long_name' in info

    @classmethod
    def create_timestamped(cls, inputs=None):
        date_str = datetime.now().strftime('%Y%m%d%H%M%S')
        identifier = f'{cls.short_name}__{date_str}'
        kwargs = {
            'identifier': identifier,
        }
        if inputs:
            kwargs['inputs_json'] = json.dumps(inputs, cls=DateTimeEncoder)

        pipe = cls.objects.create(**kwargs)
        pipe.save()
        return pipe

    def inputs_dict(self):
        return json.loads(self.inputs_json)
