from datetime import datetime

from django.db import models
from core.models.body import Body


# Statuses for asynchronous processes
ASYNC_STATUS_PENDING = 'pending'
ASYNC_STATUS_CREATED = 'success'
ASYNC_STATUS_FAILED = 'failed'
ASYNC_TERMINAL_STATES = (ASYNC_STATUS_CREATED, ASYNC_STATUS_FAILED)


class AsyncError(Exception):
    """
    An error occurred in an asynchronous process
    """


class AsyncProcess(models.Model):
    process_type = models.CharField(null=True, blank=True, max_length=100)
    identifier = models.CharField(null=False, blank=False, max_length=100, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default=ASYNC_STATUS_PENDING)
    # Time at which the processes entered a terminal state
    terminal_timestamp = models.DateTimeField(null=True, blank=True)
    failure_message = models.CharField(max_length=255, blank=True)

    def clean(self):
        self.process_type = self.__class__.__name__
        if self.status in ASYNC_TERMINAL_STATES:
            self.terminal_timestamp = datetime.utcnow()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def run(self):
        """
        Perform the potentially long-running task. Should raise AsyncError with
        an appropriate error message on failure.
        """
        raise NotImplementedError

    def __str__(self):
        return self.identifier
