from datetime import datetime

from django.db import models
from django.contrib.auth.models import User

class CalEvent(models.Model):

    EVENT_TYPES = (
        ('OBSERVATION', 'Observations'),
        ('CAMPAIGN', 'Campaign'),
        ('DOWNTIME', 'Downtime/unavailability')
    )

    STATE_CHOICES = (
        ('PROPOSED', 'Proposed or planned'),
        ('SCHEDULED', 'Time awarded or scheduled'),
        ('COMPLETED', 'Observed/Completed'),
        ('FAILED', 'Not obtained (clouded out, etc)'),
        ('CANCELLED', 'Cancelled')
    )

    submitter = models.ForeignKey(User, on_delete=models.CASCADE, help_text='The user that submitted this CalEvent')
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES, help_text='The type of CalEvent')
    start = models.DateTimeField(db_index=True, help_text='The time when this CalEvent starts')
    end = models.DateTimeField(db_index=True, help_text='The time when this CalEvent ends')
    resource = models.CharField(max_length=255, help_text='The telescope or other resource this CalEvent refers to')
    state = models.CharField(max_length=40, choices=STATE_CHOICES, default=STATE_CHOICES[0][0], help_text='Current state of this CalEvent')
    created = models.DateTimeField(default=datetime.utcnow, db_index=True, help_text='Time when this CalEvent was created')
    modified = models.DateTimeField(blank=True, null=True, db_index=True, help_text='Time when this CalEvent was last changed')
    event_note = models.CharField(max_length=255, default='', blank=True)

    class Meta:
        ordering = ('-created',)
