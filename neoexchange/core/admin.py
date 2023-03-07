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
from django.urls import reverse
from django.contrib import admin

from core.models import *
from astrometrics.time_subs import degreestohms, degreestodms, radianstohms, radianstodms

from reversion.admin import VersionAdmin


@admin.register(Body)
class BodyAdmin(VersionAdmin):
    fieldsets = (
        (None, {
            'fields': ('provisional_name', 'provisional_packed', 'name', 'origin', 'source_type')
        }),
        ('Elements', {
            'fields': ('elements_type', 'epochofel', 'abs_mag', 'slope', 'orbinc', 'longascnode', 'argofperih', 'eccentricity', 'meandist', 'meananom', 'perihdist', 'epochofperih')
       }),
        ('Follow Up', {
                'fields' : ('active', 'fast_moving', 'ingest', 'score', 'discovery_date', 'num_obs', 'arc_length', 'not_seen', 'update_time', 'updated')
        })
    )
    search_fields = ('provisional_name', 'name')
    list_display = ('id', 'provisional_name', 'name', 'origin', 'source_type',
      'active', 'num_obs', 'not_seen', 'ingest')
    list_filter = ('origin', 'source_type', 'elements_type', 'active',
      'fast_moving', 'updated')
    ordering = ('-ingest',)


@admin.register(SuperBlock)
class SuperBlockAdmin(VersionAdmin):
    def format_block_start(self, obj):
        return obj.block_start.strftime('%Y-%m-%d %H:%M')
    format_block_start.short_description = 'Block start'
    format_block_start.admin_order_field = 'block_start'

    def body_name(self, obj):
        name = ''
        if obj.body is not None:
            name = obj.body.current_name()
        elif obj.calibsource is not None:
            name = obj.calibsource.name
        return name

    # Use raw_id fields (https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.raw_id_fields)
    # for the Body to stop it making a select box tens of thousands entries long...
    raw_id_fields = ("body",)

    list_display = ('groupid', 'body_name', 'proposal', 'block_start', 'active', )
    list_filter = ('proposal', 'block_start', 'active', )
    ordering = ('-block_start',)


@admin.register(Block)
class BlockAdmin(VersionAdmin):
    def format_block_start(self, obj):
        return obj.block_start.strftime('%Y-%m-%d %H:%M')
    format_block_start.short_description = 'Block start'
    format_block_start.admin_order_field = 'block_start'

    def body_name(self, obj):
        name = ''
        if obj.body is not None:
            name = obj.body.current_name()
        elif obj.calibsource is not None:
            name = obj.calibsource.name
        return name

    def groupid(self, obj):
        groupid = ''
        if obj.superblock.groupid is not None:
            groupid = obj.superblock.groupid
        return groupid

    def proposal(self, obj):
        return obj.superblock.proposal

    # Use raw_id fields (https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.raw_id_fields)
    # for the Body to stop it making a select box tens of thousands entries long...
    raw_id_fields = ("body",)

    list_display = ('groupid', 'body_name', 'site', 'proposal', 'block_start', 'num_observed', 'active', 'reported')
    list_filter = ('site', 'telclass', 'superblock__proposal', 'block_start', 'num_observed', 'active', 'reported',)

    ordering = ('-block_start',)


@admin.register(Frame)
class FrameAdmin(VersionAdmin):
    def format_midpoint(self, obj):
        return obj.midpoint.strftime('%Y-%m-%d %H:%M:%S')
    format_midpoint.short_description = 'Frame midpoint'
    format_midpoint.admin_order_field = 'midpoint'

    def block_groupid(self, obj):
        if obj.block and obj.block.superblock:
            return obj.block.superblock.groupid
        else:
            return "No block"

    def filename_or_midpoint(self, obj):

        if obj.filename:
            name = obj.filename
        else:
            name = "%s@%s" % (obj.midpoint, obj.sitecode.rstrip())
        return name

    # Use raw_id fields (https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.raw_id_fields)
    # for the Block to stop it making a select box tens of thousands entries long...
    raw_id_fields = ("block",)

    list_display = ('id', 'block_groupid', 'quality', 'frametype', 'filename_or_midpoint', 'exptime', 'filter', 'sitecode')
    list_filter = ('quality', 'frametype', 'midpoint', 'filter', 'sitecode', 'instrument')
    search_fields = ('filename', )

    ordering = ('-midpoint',)


@admin.register(SpectralInfo)
class SpectralInfoAdmin(VersionAdmin):

    def body_name(self, obj):
        return obj.body.current_name()

    list_display = ('body_name', 'taxonomic_class', 'tax_scheme', 'tax_reference', 'make_readable_tax_notes')
    list_filter = ('taxonomic_class', 'tax_scheme')


@admin.register(PreviousSpectra)
class PreviousSpectraAdmin(VersionAdmin):

    def body_name(self, obj):
        return obj.body.current_name()

    list_display = ('body_name', 'spec_wav', 'spec_source', 'spec_date')
    list_filter = ('spec_wav', 'spec_source')


class ProposalAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'pi', 'tag', 'active', 'time_critical', 'download')


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
        return degreestohms(obj.obs_ra, ' ')

    def obs_dec_dms(self, obj):
        return degreestodms(obj.obs_dec, ' ')

    # Use raw_id fields (https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.raw_id_fields)
    # for the Body and Frame to stop it making a select box tens of thousands entries long...
    raw_id_fields = ("body", "frame")

    list_display = ('body_name', 'frame', 'flags', 'obs_ra_hms', 'obs_dec_dms', 'site_code')
    search_fields = ('body__name', 'body__provisional_name')


class CatalogSourcesAdmin(admin.ModelAdmin):

    def obs_x_rnd(self, obj):
        return round(obj.obs_x, 3)
    obs_x_rnd.short_description = "CCD X"

    def obs_y_rnd(self, obj):
        return round(obj.obs_y, 3)
    obs_y_rnd.short_description = "CCD Y"

    def obs_ra_hms(self, obj):
        return degreestohms(obj.obs_ra, ' ')
    obs_ra_hms.short_description = "RA (h m s)"

    def obs_dec_dms(self, obj):
        return degreestodms(obj.obs_dec, ' ')
    obs_dec_dms.short_description = "Dec (d ' \")"

    def obs_mag_error(self, obj):
        return "%.2f +/- %.3f" % ( obj.obs_mag, obj.err_obs_mag)
    obs_mag_error.short_description = "Magnitude"

    # Use raw_id fields (https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.raw_id_fields)
    # for the Frame to stop it making a select box tens of thousands entries long...
    raw_id_fields = ("frame",)

    list_display = ('id', 'frame', 'obs_x_rnd', 'obs_y_rnd', 'obs_ra', 'obs_dec', 'obs_ra_hms', 'obs_dec_dms', 'obs_mag_error')
    search_fields = ('frame__filename', )


class CandidateAdmin(admin.ModelAdmin):

    list_select_related = True

    def block_info(self, obj):
        ct = obj.block._meta
        url = reverse('admin:%s_%s_change' % (ct.app_label, ct.model_name), args=(obj.block.pk,))
        return "<a href=%s>%s@%s</a>" % (url, obj.block.body.current_name(), obj.block.site)
    block_info.allow_tags = True

    def cand_score(self, obj):
        return round(obj.score, 2)

    def avg_midpoint_iso(self, obj):
        return obj.avg_midpoint.strftime("%Y-%m-%d %H:%M:%S")
    avg_midpoint_iso.short_description = "Average midpoint(UTC)"

    def avg_x_rnd(self, obj):
        return "%08.3f" % obj.avg_x
    avg_x_rnd.short_description = "Average CCD X"

    def avg_y_rnd(self, obj):
        return "%08.3f" % obj.avg_y
    avg_y_rnd.short_description = "Average CCD Y"

    def avg_mag_rnd(self, obj):
        return "%.2f" % obj.avg_mag
    avg_mag_rnd.short_description = "Average mag."

    def speed_amin(self, obj):
        return round(obj.convert_speed(), 3)
    speed_amin.short_description = 'Speed ("/min)'

    def sky_motion_pa_rnd(self, obj):
        return "%.1f" % obj.sky_motion_pa
    sky_motion_pa_rnd.short_description = "PA of sky motion (deg)"

    def avg_r(self, obj):
        return "%.1f" % (obj.compute_separation())
    avg_r.short_description = 'Separation (")'

    list_display = ( 'id', 'block_info', 'cand_id', 'cand_score', 'avg_midpoint_iso', 'avg_r', 'avg_x_rnd', 'avg_y_rnd', 'avg_ra', 'avg_dec', 'avg_mag_rnd', 'speed_amin', 'sky_motion_pa_rnd')
    list_display_links = ('id', )

    ordering = ( 'block', 'cand_id')

    search_fields = ('block__body__provisional_name', )


class StaticSourceAdmin(admin.ModelAdmin):

    def calib_ra_hms(self, obj):
        return degreestohms(obj.ra, ' ')
    calib_ra_hms.short_description = "RA (h m s)"

    def calib_dec_dms(self, obj):
        return degreestodms(obj.dec, ' ')
    calib_dec_dms.short_description = "Dec (d ' \")"

    list_display = ['id', 'name', 'calib_ra_hms', 'calib_dec_dms', 'vmag', 'spectral_type', 'source_type', 'notes']
    list_filter = ['spectral_type', 'source_type']

    ordering = [ 'ra', ]

    search_fields = ('name',)


class PhysicalParametersAdmin(admin.ModelAdmin):

    def body_name(self, obj):
        name = ''
        if obj.body is not None:
            name = obj.body.full_name()
        elif obj.calibsource is not None:
            name = obj.calibsource.name
        return name

    search_fields = ('body__name', 'body__provisional_name')
    list_display = ('id', 'body_name', 'parameter_type', 'value', 'error', 'units', 'preferred')
    list_filter = ('parameter_type', 'preferred')
    ordering = ['body__name', 'parameter_type', '-preferred']


class DesignationsAdmin(admin.ModelAdmin):

    def body_name(self, obj):
        name = ''
        if obj.body is not None:
            name = obj.body.full_name()
        elif obj.calibsource is not None:
            name = obj.calibsource.name
        return name

    search_fields = ('value',)
    list_display = ('id', 'value', 'desig_type', 'body_name', 'preferred', 'update_time')
    list_filter = ('desig_type', 'preferred')
    ordering = ['body__name', 'desig_type', '-preferred']


class ColorValuesAdmin(admin.ModelAdmin):

    def body_name(self, obj):
        name = ''
        if obj.body is not None:
            name = obj.body.full_name()
        elif obj.calibsource is not None:
            name = obj.calibsource.name
        return name

    search_fields = ('body__name', 'body__provisional_name')
    list_display = ('id', 'body_name', 'color_band', 'value', 'error', 'preferred', 'update_time')
    list_filter = ('color_band', 'preferred')
    ordering = ['body__name', 'color_band', '-preferred']


class DataProductsAdmin(admin.ModelAdmin):

    def body_name(self, obj):
        name = ''
        if obj.body is not None:
            name = obj.body.full_name()
        elif obj.calibsource is not None:
            name = obj.calibsource.name
        return name

    # search_fields = ('body_name', 'body_provisional_name')
    list_display = ('id', 'filetype', 'product', 'created', 'content_type')
    list_filter = ('filetype',)
    # ordering = ['body_name', 'filetype', 'created']


class ExportedBlockAdmin(admin.ModelAdmin):

    list_select_related = True

    def block_info(self, obj):
        block_info = f"#{obj.block.request_number}"
        if obj.block.superblock.groupid is not None:
            block_info += f" ({obj.block.superblock.groupid})"
        return block_info
    block_info.allow_tags = True

    # Use raw_id fields (https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.raw_id_fields)
    # for the Block to stop it making a select box tens of thousands entries long...
    raw_id_fields = ("block",)

    list_display = ('block_info', 'input_path', 'export_path', 'export_format', 'when_exported')
    list_display_links = ('block_info', )
    list_filter = ('export_format', )

admin.site.register(Proposal, ProposalAdmin)
admin.site.register(SourceMeasurement, SourceMeasurementAdmin)
admin.site.register(ProposalPermission)
admin.site.register(CatalogSources, CatalogSourcesAdmin)
admin.site.register(Candidate, CandidateAdmin)
admin.site.register(StaticSource, StaticSourceAdmin)
admin.site.register(PhysicalParameters, PhysicalParametersAdmin)
admin.site.register(Designations, DesignationsAdmin)
admin.site.register(ColorValues, ColorValuesAdmin)
admin.site.register(DataProduct, DataProductsAdmin)
admin.site.register(ExportedBlock, ExportedBlockAdmin)
