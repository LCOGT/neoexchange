from django.contrib import admin

from cal.models import *

from reversion.admin import VersionAdmin


@admin.register(CalEvent)
class CalEventAdmin(VersionAdmin):

    list_display = ('event_type', 'start', 'end', 'resource', 'state', 'created')
    list_filter = ('event_type', 'start', 'end', 'resource', 'state', 'created', 'modified')

    ordering = ('-start',)
