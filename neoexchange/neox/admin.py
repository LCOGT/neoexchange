'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from core.models import *
from django.contrib import admin

import reversion

class BodyAdmin(reversion.VersionAdmin):
    fieldsets = (
        (None, {
            'fields': ('provisional_name', 'provisional_packed', 'name','origin','source_type')
        }),
        ('Elements', {
            'fields': ('elements_type', 'epochofel', 'abs_mag', 'slope', 'orbinc','longascnode','argofperih','eccentricity','meandist','meananom','perihdist', 'epochofperih')
       }),
        ('Follow Up',{
                'fields' : ('active','fast_moving','ingest','score','discovery_date','num_obs','arc_length','not_seen','update_time','updated')
        })
    )
    search_fields = ('provisional_name','name')
    list_display = ('id', 'provisional_name', 'name', 'origin', 'source_type', 
      'active', 'num_obs', 'not_seen', 'ingest')
    list_filter = ('origin', 'source_type', 'elements_type', 'active', 
      'fast_moving', 'updated')
    ordering = ('-ingest',)


class BlockAdmin(reversion.VersionAdmin):
    def format_block_start(self, obj):
        return obj.block_start.strftime('%Y-%m-%d %H:%M')
    format_block_start.short_description = 'Block start'
    format_block_start.admin_order_field = 'block_start'

    def body_name(self, obj):
        return obj.body.current_name()

    list_display = ('groupid', 'body_name', 'site', 'proposal', 'block_start', 'num_observed', 'active', 'reported',  )
    list_filter = ('site', 'telclass', 'proposal', 'block_start', 'num_observed', 'active', 'reported',)

    ordering = ('-block_start',)

class FrameAdmin(reversion.VersionAdmin):
    pass

class ProposalAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'pi', 'tag', 'active')


admin.site.register(Body,BodyAdmin)
admin.site.register(Frame,FrameAdmin)
admin.site.register(Block,BlockAdmin)
admin.site.register(Proposal,ProposalAdmin)
