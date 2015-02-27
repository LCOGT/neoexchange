'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from ingest.models import *
from django.contrib import admin

import reversion

class BodyAdmin(reversion.VersionAdmin):
    pass

class BlockAdmin(reversion.VersionAdmin):
    pass

class RecordAdmin(reversion.VersionAdmin):
    pass

class ProposalAdmin(admin.ModelAdmin):
    pass

admin.site.register(Body,BodyAdmin)
admin.site.register(Record,RecordAdmin)
admin.site.register(Block,BlockAdmin)
admin.site.register(Proposal,ProposalAdmin)