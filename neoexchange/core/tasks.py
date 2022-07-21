import sys
import logging

import dramatiq
from redis.exceptions import RedisError

from core.models import (
    AsyncError, ASYNC_STATUS_FAILED, PipelineProcess
)

logger = logging.getLogger(__name__)

def task(**kwargs):
    """
    Decorator that wraps dramatiq.actor, but runs tasks synchronously during
    tests
    """
    def wrap(func):
        if 'test' not in sys.argv:
            return dramatiq.actor(func, **kwargs)
        func.send = func
        return func
    return wrap


def send_task(task, process, *args):
    """
    Wrapper around queuing a task to start an AsyncProcess sub-class, which
    sets the status and failure message of the process if an exception occurs
    when submitting.

    The task must accept the process's PK as its first argument. *args are
    forwarded to the task.
    """
    try:
        task.send(process.pk, *args)
    except RedisError as ex:
        logger.error('failed to submit job: {}'.format(ex))
        process.status = ASYNC_STATUS_FAILED
        process.failure_message = 'Failed to submit job'
        process.save()


@task(time_limit=3600_000, max_retries=0)
def run_pipeline(process_pk, cls_name):
    """
    Task to run a PipelineProcess sub-class. `cls_name` is the name of the
    pipeline as given in PIPELINES setting.
    """
    try:
        pipeline_cls = PipelineProcess.get_subclass(cls_name)
    except ImportError:
        logger.error('pipeline \'{}\' not found'.format(cls_name), file=sys.stderr)
        return
    try:
        process = pipeline_cls.objects.get(pk=process_pk)
    except pipeline_cls.DoesNotExist:
        logger.error('could not find {} with PK {}'.format(pipeline_cls.__name__, process_pk),
              file=sys.stderr)
        return
    run_process(process)


def run_process(process):
    """
    Helper function to call the run() method of an AsyncProcess, catch errors,
    and update statuses and error messages.

    Note that this runs in the dramatiq worker processes.
    """
    logger.info("running process")
    failure_message = None
    try:
        process.run()
    except AsyncError as ex:
        failure_message = str(ex)
    except NotImplementedError as ex:
        logger.error('S3 not configured correctly: {}'.format(ex))
        failure_message = str(ex)
    except TypeError as ex:
        logger.error('Unexpected input type: {}'.format(ex))
        failure_message = 'Unexpected input type'
    except Exception as ex:
        logger.error('unknown error occurred: {}'.format(ex))
        failure_message = f'An unexpected error occurred {ex}'

    if failure_message is not None:
        logger.error('task failed: {}'.format(failure_message))
        process.failure_message = failure_message
        process.status = ASYNC_STATUS_FAILED
        process.save()
    logger.info('process finished')
    return
