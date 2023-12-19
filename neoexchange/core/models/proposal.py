"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2019 LCO
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class Proposal(models.Model):
    code = models.CharField(max_length=55)
    title = models.CharField(max_length=255)
    pi = models.CharField("PI", max_length=50, default='', help_text='Principal Investigator (PI)')
    tag = models.CharField(max_length=10, default='LCOGT')
    active = models.BooleanField('Proposal active?', default=True)
    time_critical = models.BooleanField('Time Critical/ToO proposal?', default=False)
    download = models.BooleanField('Auto download data?', default=True)

    class Meta:
        db_table = 'ingest_proposal'
        ordering = ['-id', ]

    def __str__(self):
        if len(self.title) >= 10:
            title = "%s..." % self.title[0:9]
        else:
            title = self.title[0:10]
        return "%s %s" % (self.code, title)


class ProposalPermission(models.Model):
    """
    Linking a user to proposals in NEOx to control their access
    """
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Proposal Permission')

    def __str__(self):
        return "%s is a member of %s" % (self.user, self.proposal)
