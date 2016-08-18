'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2016 LCOGT

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
from astrometrics.time_subs import degreestohms, degreestodms

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
      'fast_moving', 'updated', 'ingest')
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
    def format_midpoint(self, obj):
        return obj.midpoint.strftime('%Y-%m-%d %H:%M:%S')
    format_midpoint.short_description = 'Frame midpoint'
    format_midpoint.admin_order_field = 'midpoint'

    def block_groupid(self, obj):
        if obj.block:
            return obj.block.groupid
        else:
            return "No block"

    def filename_or_midpoint(self, obj):

        if obj.filename:
            name= obj.filename
        else:
            name = "%s@%s" % ( obj.midpoint, obj.sitecode.rstrip() )
        return name

    list_display = ('id', 'block_groupid', 'quality', 'frametype', 'filename_or_midpoint', 'exptime', 'filter', 'sitecode')
    list_filter = ('quality', 'frametype', 'midpoint', 'filter', 'sitecode', 'instrument')

    ordering = ('-midpoint',)

class ProposalAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'pi', 'tag', 'active')

class SourceMeasurementAdmin(admin.ModelAdmin):

    def body_name(self, obj):
        provisional_name = ''
        if obj.body.provisional_name:
            provisional_name = obj.body.provisional_name
        joiner = ''
        if obj.body.provisional_name and obj.body.name:
            joiner = '->'
        final_name = ''
        if obj.body.name:
            final_name = obj.body.name

        return provisional_name + joiner + final_name

    def site_code(self, obj):
        return obj.frame.sitecode

    def obs_ra_hms(self, obj):
        return degreestohms(obj.obs_ra,' ')

    def obs_dec_dms(self, obj):
        return degreestodms(obj.obs_dec,' ')

    list_display = ('body_name', 'frame', 'flags', 'obs_ra_hms', 'obs_dec_dms', 'site_code')
    search_fields = ('body__name', 'body__provisional_name')

class CatalogSourcesAdmin(admin.ModelAdmin):

    def site_code(self, obj):
        return obj.frame.sitecode

    def obs_ra_hms(self, obj):
        return degreestohms(obj.obs_ra,' ')

    def obs_dec_dms(self, obj):
        return degreestodms(obj.obs_dec,' ')

    list_display = ('frame', 'flags', 'obs_ra_hms', 'obs_dec_dms', 'obs_mag', 'site_code')
    list_filter = ('frame__sitecode', 'flags')
    search_fields = ('frame__filename',)

class CandidateAdmin(admin.ModelAdmin):

    def score_fmt(self, obj):
        return "%.2f" % obj.score
    score_fmt.short_description = 'Score'
    score_fmt.admin_order_field = 'score'

    def avg_x_fmt(self, obj):
        return "%.2f" % obj.avg_x
    avg_x_fmt.short_description = 'Mean X co-ord'
    avg_x_fmt.admin_order_field = 'abg_x'

    def avg_y_fmt(self, obj):
        return "%.2f" % obj.avg_y
    avg_y_fmt.short_description = 'Mean Y co-ord'
    avg_y_fmt.admin_order_field = 'avg_y'

    def avg_ra_fmt(self, obj):
        return "%.5f" % obj.avg_ra
    avg_ra_fmt.short_description = 'Mean RA value'
    avg_ra_fmt.admin_order_field = 'avg_ra'

    def avg_dec_fmt(self, obj):
        return "%.5f" % obj.avg_dec
    avg_dec_fmt.short_description = 'Mean Dec value'
    avg_dec_fmt.admin_order_field = 'avg_dec'

    def avg_mag_fmt(self, obj):
        return "%.1f" % obj.avg_mag
    avg_mag_fmt.short_description = 'Mean Mag.'
    avg_mag_fmt.admin_order_field = 'avg_mag'

    def avg_midpoint_fmt(self, obj):
        return obj.avg_midpoint.strftime('%Y-%m-%d %H:%M:%S')
    avg_midpoint_fmt.short_description = 'Mean Frame midpoint'
    avg_midpoint_fmt.admin_order_field = 'avg_midpoint'

    list_display = ('__unicode__', 'cand_id', 'score_fmt', 'avg_midpoint_fmt', 'avg_x_fmt', 'avg_y_fmt', 'avg_ra_fmt', 'avg_dec_fmt', 'avg_mag_fmt', 'speed', 'sky_motion_pa')
    ordering = ('-block__id', 'cand_id')

admin.site.register(Body,BodyAdmin)
admin.site.register(Frame,FrameAdmin)
admin.site.register(Block,BlockAdmin)
admin.site.register(Proposal,ProposalAdmin)
admin.site.register(SourceMeasurement,SourceMeasurementAdmin)
admin.site.register(ProposalPermission)
admin.site.register(CatalogSources,CatalogSourcesAdmin)
admin.site.register(Candidate,CandidateAdmin)
