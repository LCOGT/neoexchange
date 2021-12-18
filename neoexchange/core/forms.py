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

from datetime import datetime, date, timedelta
import logging

from django import forms
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from astrometrics.sources_subs import fetch_sfu, fetch_filter_list
from .models import Body, Proposal, Block, StaticSource, ORIGINS, STATUS_CHOICES
from astrometrics.time_subs import tomorrow

logger = logging.getLogger(__name__)


SITES = (('1M0', '------------ Any 1.0m ------------'),
         ('W86', 'LSC 1.0m - W85-87; (CTIO, Chile)'),
         ('V37', 'ELP 1.0m - V37,V39; (McDonald, Texas)'),
         ('Q63', 'COJ 1.0m - Q63-64; (Siding Spring, Aust.)'),
         ('K92', 'CPT 1.0m - K91-93; (Sutherland, S. Africa)'),
         ('Z24', 'TFN 1.0m - Z31,Z24; (Tenerife, Spain)'),
         ('0M4', '------------ Any 0.4m ------------'),
         ('W89', 'LSC 0.4m - W89,W79; (CTIO, Chile)'),
         ('V38', 'ELP 0.4m - V38; (McDonald, Texas)'),
         ('T04', 'OGG 0.4m - T03-04; (Maui, Hawaii)'),
         ('Q58', 'COJ 0.4m - Q58-59; (Siding Spring, Aust.)'),
         ('L09', 'CPT 0.4m - L09; (Sutherland, S. Africa)'),
         ('Z21', 'TFN 0.4m - Z17,Z21; (Tenerife, Spain)'),
         ('2M0', '------------ Any 2.0m ------------'),
         ('E10', 'FTS 2.0m - E10; (Siding Spring, Aust.)'),
         ('F65', 'FTN 2.0m - F65; (Maui, Hawaii ) [MuSCAT3]'),
         ('non', '------------ Non LCO  ------------'),
         ('474', 'Mt John 1.8m - 474 (Mt John, NZ)'))


SPECTRO_SITES = (('F65-FLOYDS', 'Maui, Hawaii (FTN - F65)'),
                 ('E10-FLOYDS', 'Siding Spring, Aust. (FTS - E10)'))

CALIBS = (('Both', 'Calibrations before and after spectrum'),
          ('Before', 'Calibrations before spectrum'),
          ('After', 'Calibrations after spectrum'),
          ('None', 'No Calibrations (not recommended)'))

MOON = (('G', 'Grey',),
        ('B', 'Bright'),
        ('D', 'Dark'))

BIN_MODES = (('full_chip', 'Full Chip, 1x1'),
             ('2k_2x2', 'Central 2k, 2x2'))

ANALOG_OPTIONS = (('1', '1'),
                  ('2', '2'),
                  ('3', '3'),
                  ('4', '4'),
                  ('5', '5'))

LC_QUALITIES = (('3', 'Unambiguous (3)'),
                ('3-', 'Unique (3-)'),
                ('2+', 'Possible Ambiguity (2+)'),
                ('2', 'Within 30% accurate (2)'),
                ('2-', 'Not well established (2-)'),
                ('1+', 'Possibly Just Noise (1+)'),
                ('1', 'Possibly Completely Wrong (1)'),
                ('1-', 'Probably Completely Wrong (1-)'),
                ('0', 'Debunked (0)'))


class SiteSelectWidget(forms.Select):
    """
    Subclass of Django's select widget that allows disabling options.
    """
    def __init__(self, *args, **kwargs):
        self._disabled_choices = []
        super(forms.Select, self).__init__(*args, **kwargs)

    @property
    def disabled_choices(self):
        return self._disabled_choices

    @disabled_choices.setter
    def disabled_choices(self, other):
        self._disabled_choices = other

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option_dict = super(forms.Select, self).create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value in self.disabled_choices:
            option_dict['attrs']['disabled'] = 'disabled'
        return option_dict


class EphemQuery(forms.Form):

    target = forms.CharField(label="Enter target name...", max_length=14, required=True, widget=forms.TextInput(attrs={'size': '10'}),
                             error_messages={'required': _(u'Target name is required')})
    site_code = forms.ChoiceField(required=True, choices=SITES, widget=SiteSelectWidget)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d', ], initial=date.today, required=True, widget=forms.TextInput(attrs={'size': '10'}),
                               error_messages={'required': _(u'UTC date is required')})
    alt_limit = forms.FloatField(initial=30.0, required=True, widget=forms.TextInput(attrs={'size': '4'}))

    def clean_target(self):
        name = self.cleaned_data['target']
        body = Body.objects.filter(Q(provisional_name__startswith=name) | Q(provisional_packed__startswith=name) | Q(name__startswith=name))
        if body.count() == 1 :
            return body[0]
        elif body.count() == 0:
            raise forms.ValidationError("Object not found.")
        elif body.count() > 1:
            newbody = Body.objects.filter(Q(provisional_name__exact=name) | Q(provisional_packed__exact=name) | Q(name__exact=name))
            if newbody.count() == 1:
                return newbody[0]
            else:
                raise forms.ValidationError("Multiple objects found.")

    def __init__(self, *args, **kwargs):
        super(EphemQuery, self).__init__(*args, **kwargs)
        self.fields['site_code'].widget.disabled_choices = ['non']


class ScheduleForm(forms.Form):
    proposal_code = forms.ChoiceField(required=True)
    site_code = forms.ChoiceField(required=True, choices=SITES, widget=SiteSelectWidget)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d', ], initial=date.today, required=True, widget=forms.TextInput(attrs={'size': '10'}),
                               error_messages={'required': _(u'UTC date is required')})
    too_mode = forms.BooleanField(initial=False, required=False)

    def clean_utc_date(self):
        start = self.cleaned_data['utc_date']
        if start < datetime.utcnow().date():
            raise forms.ValidationError("Window cannot start in the past")
        return start

    def __init__(self, *args, **kwargs):
        self.proposal_code = kwargs.pop('proposal_code', None)
        super(ScheduleForm, self).__init__(*args, **kwargs)
        proposals = Proposal.objects.filter(active=True)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        self.fields['proposal_code'].choices = proposal_choices
        self.fields['site_code'].widget.disabled_choices = ['non', '474', '2M0']


class ScheduleCadenceForm(forms.Form):
    proposal_code = forms.ChoiceField(required=True, widget=forms.Select(attrs={'id': 'id_proposal_code_cad', }))
    site_code = forms.ChoiceField(required=True, choices=SITES, widget=SiteSelectWidget(attrs={'id': 'id_site_code_cad', }))
    start_time = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M'],
                                     initial=datetime.today, required=True, error_messages={'required': _(u'UTC start date is required')})
    end_time = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M'],
                                   initial=tomorrow, required=True, error_messages={'required': _(u'UTC end date is required')})
    period = forms.FloatField(initial=2.0, required=True, widget=forms.TextInput(attrs={'size': '10'}), error_messages={'required': _(u'Period is required')})
    jitter = forms.FloatField(initial=0.25, required=True, widget=forms.TextInput(attrs={'size': '10'}), error_messages={'required': _(u'Jitter is required')})
    too_mode = forms.BooleanField(initial=False, required=False)

    # def clean_end_time(self):
    #     end = self.cleaned_data['end_time']
    #     if end < datetime.utcnow():
    #         raise forms.ValidationError("Window cannot end in the past")
    #     return end

    def clean_start_time(self):
        start = self.cleaned_data['start_time']
        window_cutoff = datetime.utcnow() - timedelta(days=1)
        if start <= window_cutoff:
            return datetime.utcnow().replace(microsecond=0)
        else:
            return self.cleaned_data['start_time']

    def clean_period(self):
        if self.cleaned_data['period'] is not None and self.cleaned_data['period'] < 0.02:
            return 0.02
        else:
            return self.cleaned_data['period']

    def clean(self):
        cleaned_data = super(ScheduleCadenceForm, self).clean()
        try:
            start = cleaned_data['start_time']
            end = cleaned_data['end_time']
            if end < start:
                raise forms.ValidationError("End date must be after start date")
        except KeyError:
            # Bad datetimes should be caught by Django validation
            pass

    def __init__(self, *args, **kwargs):
        self.proposal_code = kwargs.pop('proposal_code', None)
        super(ScheduleCadenceForm, self).__init__(*args, **kwargs)
        proposals = Proposal.objects.filter(active=True)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        self.fields['proposal_code'].choices = proposal_choices
        self.fields['site_code'].widget.disabled_choices = ['non', '474']


class ScheduleBlockForm(forms.Form):
    start_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'style': 'width: 200px;'}), input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'])
    end_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'style': 'width: 200px;'}), input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'])
    exp_count = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    exp_length = forms.FloatField(widget=forms.NumberInput(attrs={'size': '5'}))
    slot_length = forms.FloatField(widget=forms.NumberInput(attrs={'size': '5'}), required=False)
    filter_pattern = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}))
    pattern_iterations = forms.FloatField(widget=forms.HiddenInput(), required=False)
    proposal_code = forms.CharField(max_length=20, widget=forms.HiddenInput())
    site_code = forms.CharField(max_length=5, widget=forms.HiddenInput())
    group_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'style': 'text-align: right; width: -webkit-fill-available; width: -moz-available;'}))
    utc_date = forms.DateField(input_formats=['%Y-%m-%d', ], widget=forms.HiddenInput(), required=False)
    jitter = forms.FloatField(widget=forms.NumberInput(attrs={'size': '5'}), required=False)
    period = forms.FloatField(widget=forms.NumberInput(attrs={'size': '5'}), required=False)
    bin_mode = forms.ChoiceField(required=False, choices=BIN_MODES)
    spectroscopy = forms.BooleanField(required=False, widget=forms.HiddenInput())
    too_mode = forms.BooleanField(required=False, widget=forms.HiddenInput())
    calibs = forms.ChoiceField(required=False, widget=forms.HiddenInput(), choices=CALIBS)
    instrument_code = forms.CharField(max_length=10, widget=forms.HiddenInput(), required=False)
    solar_analog = forms.BooleanField(initial=True, widget=forms.HiddenInput(), required=False)
    calibsource_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    calibsource_exptime = forms.IntegerField(widget=forms.NumberInput(attrs={'size': '5'}), required=False)
    calibsource_list = forms.ChoiceField(required=False)
    max_airmass = forms.FloatField(widget=forms.NumberInput(attrs={'style': 'width: 75px;'}), required=False)
    ipp_value = forms.FloatField(widget=forms.NumberInput(attrs={'style': 'width: 75px;'}), required=False)
    para_angle = forms.BooleanField(initial=False, required=False)
    min_lunar_dist = forms.FloatField(widget=forms.NumberInput(attrs={'style': 'width: 75px;'}), required=False)
    acceptability_threshold = forms.FloatField(widget=forms.NumberInput(attrs={'style': 'width: 75px;'}), required=False)
    ag_exp_time = forms.FloatField(widget=forms.NumberInput(attrs={'style': 'width: 75px;'}), required=False)
    edit_window = forms.BooleanField(initial=False, required=False, widget=forms.CheckboxInput(attrs={'class': 'window-switch'}))
    add_dither = forms.BooleanField(initial=False, required=False, widget=forms.CheckboxInput(attrs={'class': 'dither-switch'}))
    dither_distance = forms.FloatField(widget=forms.NumberInput(attrs={'style': 'width: 75px;'}), required=False)
    gp_explength = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'size': '5'}))
    rp_explength = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'size': '5'}))
    ip_explength = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'size': '5'}))
    zp_explength = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'size': '5'}))
    muscat_sync = forms.BooleanField(initial=False, required=False)

    def clean_dither_distance(self):
        """Limit dither distance to values between 0 and 60 arcsec."""
        if not self.cleaned_data['dither_distance'] or self.cleaned_data['dither_distance'] < 0:
            return 10
        if self.cleaned_data['dither_distance'] > 60:
            return 60
        return self.cleaned_data['dither_distance']

    def clean_exp_length(self):
        if not self.cleaned_data['exp_length'] or self.cleaned_data['exp_length'] < 0.1:
            return 0.1
        else:
            return self.cleaned_data['exp_length']

    def clean_min_lunar_dist(self):
        if self.cleaned_data['min_lunar_dist'] > 180:
            return 180
        elif self.cleaned_data['min_lunar_dist'] < 0:
            return 0
        else:
            return self.cleaned_data['min_lunar_dist']

    def clean_acceptability_threshold(self):
        if self.cleaned_data['acceptability_threshold'] > 100:
            return 100
        elif self.cleaned_data['acceptability_threshold'] < 0:
            return 0
        else:
            return self.cleaned_data['acceptability_threshold']

    def clean_ag_exp_time(self):
        if self.cleaned_data['ag_exp_time'] is not None and self.cleaned_data['ag_exp_time'] < 0.1:
            return 0.1
        elif self.cleaned_data['ag_exp_time'] is None:
            return None
        else:
            return self.cleaned_data['ag_exp_time']

    def clean_ipp_value(self):
        if self.cleaned_data['ipp_value'] < 0.5:
            return 0.5
        elif self.cleaned_data['ipp_value'] > 2:
            return 2.0
        else:
            return self.cleaned_data['ipp_value']

    def clean_max_airmass(self):
        if self.cleaned_data['max_airmass'] < 1:
            return 1.0
        else:
            return self.cleaned_data['max_airmass']

    def clean_start_time(self):
        start = self.cleaned_data['start_time']
        window_cutoff = datetime.utcnow() - timedelta(days=1)
        if start <= window_cutoff:
            return datetime.utcnow().replace(microsecond=0)
        else:
            return self.cleaned_data['start_time']

    def clean_end_time(self):
        end = self.cleaned_data['end_time']
        if end <= datetime.utcnow():
            raise forms.ValidationError("Window cannot end in the past")
        else:
            return self.cleaned_data['end_time']

    def clean_filter_pattern(self):
        try:
            pattern = self.cleaned_data['filter_pattern']
            stripped_pattern = pattern.replace(" ", ",").replace(";", ",").replace("/", ",")

            chunks = stripped_pattern.split(',')
            chunks = list(filter(None, chunks))
            if chunks.count(chunks[0]) == len(chunks):
                chunks = [chunks[0]]
            cleaned_filter_pattern = ",".join(chunks)
        except KeyError:
            cleaned_filter_pattern = ''
        except IndexError:
            cleaned_filter_pattern = ''
        return cleaned_filter_pattern

    def clean_period(self):
        if self.cleaned_data['period'] is not None and self.cleaned_data['period'] < 0.02:
            return 0.02
        else:
            return self.cleaned_data['period']

    def clean_slot_length(self):
        if self.cleaned_data['slot_length'] is None:
            return 0
        else:
            return self.cleaned_data['slot_length']

    def clean(self):
        cleaned_data = super(ScheduleBlockForm, self).clean()
        site = self.cleaned_data['site_code']
        spectra = self.cleaned_data['spectroscopy']
        filter_list, fetch_error = fetch_filter_list(site, spectra)
        if fetch_error:
            raise forms.ValidationError(fetch_error)
        try:
            if not self.cleaned_data['filter_pattern']:
                raise forms.ValidationError("You must select a filter.")
        except KeyError:
            raise forms.ValidationError('Dude, you had to actively input a bunch of spaces and nothing else to see this error. '
                                        'Why?? Just pick a filter from the list! %(filters)s', params={'filters': ",".join(filter_list)})
        pattern = self.cleaned_data['filter_pattern']
        chunks = pattern.split(',')
        bad_filters = [x for x in chunks if x not in filter_list]
        if len(bad_filters) > 0:
            if len(bad_filters) == 1:
                raise forms.ValidationError('%(bad)s is not an acceptable filter at this site.', params={'bad': ",".join(bad_filters)})
            else:
                raise forms.ValidationError('%(bad)s are not acceptable filters at this site.', params={'bad': ",".join(bad_filters)})
        elif self.cleaned_data['exp_count'] == 0:
            raise forms.ValidationError("There must be more than 1 exposure")
        if self.cleaned_data.get('end_time') and self.cleaned_data.get('start_time'):
            window_width = self.cleaned_data['end_time'] - self.cleaned_data['start_time']
            window_width = window_width.total_seconds() / 60
            if window_width < self.cleaned_data['slot_length']:
                raise forms.ValidationError("Requested Observations will not fit within Scheduling Window.")
            if self.cleaned_data.get('end_time') < self.cleaned_data.get('start_time'):
                raise forms.ValidationError("Scheduling Window cannot end before it begins without breaking causality. Please Fix.")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.calibsource_list = kwargs.pop('calibsource_list', None)
        super(ScheduleBlockForm, self).__init__(*args, **kwargs)
        self.fields['calibsource_list'].choices = ANALOG_OPTIONS


class ScheduleSpectraForm(forms.Form):
    proposal_code = forms.ChoiceField(required=True)
    instrument_code = forms.ChoiceField(required=True, choices=SPECTRO_SITES)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d', ], initial=date.today, required=True, widget=forms.TextInput(attrs={'size': '10'}), error_messages={'required': _(u'UTC date is required')})
    exp_count = forms.IntegerField(initial=1, widget=forms.NumberInput(attrs={'size': '5'}), required=True)
    exp_length = forms.FloatField(initial=1800.0, required=True)
    calibs = forms.ChoiceField(required=True, choices=CALIBS)
    solar_analog = forms.BooleanField(initial=True, required=False)
    spectroscopy = forms.BooleanField(initial=True, widget=forms.HiddenInput(), required=False)
    too_mode = forms.BooleanField(initial=False, required=False)

    def clean_utc_date(self):
        start = self.cleaned_data['utc_date']
        if start < datetime.utcnow().date():
            raise forms.ValidationError("Window cannot start in the past")
        return start

    def clean(self):
        cleaned_data = super(ScheduleSpectraForm, self).clean()
        site = self.cleaned_data['instrument_code']
        spectra = self.cleaned_data['spectroscopy']
        filter_list, fetch_error = fetch_filter_list(site[0:3], spectra)
        if fetch_error:
            raise forms.ValidationError(fetch_error)

    def __init__(self, *args, **kwargs):
        self.proposal_code = kwargs.pop('proposal_code', None)
        super(ScheduleSpectraForm, self).__init__(*args, **kwargs)
        proposals = Proposal.objects.filter(active=True)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        self.fields['proposal_code'].choices = proposal_choices


class MPCReportForm(forms.Form):
    block_id = forms.IntegerField(widget=forms.HiddenInput())
    report = forms.CharField(widget=forms.Textarea)

    def clean(self):
        try:
            block = Block.objects.get(id=self.cleaned_data['block_id'])
            self.cleaned_data['block'] = block
        except:
            raise forms.ValidationError('Block ID %s is not valid' % self.cleaned_data['block_id'])


class SpectroFeasibilityForm(forms.Form):
    instrument_code = forms.ChoiceField(required=True, choices=SPECTRO_SITES)
    magnitude = forms.FloatField()
    exp_length = forms.FloatField(initial=1800.0, required=True)
    moon_phase = forms.ChoiceField(choices=MOON, required=True)
    airmass = forms.FloatField(initial=1.2, required=True)
    sfu = forms.FloatField(disabled=True, required=True)

    def __init__(self, *args, **kwargs):
        sfu_values = fetch_sfu()
        body = kwargs.pop('body', None)
        mag = None
        if body and isinstance(body, Body):
            emp = body.compute_position()
            if emp is not False:
                mag = round(emp[2], 1)
        elif body and isinstance(body, StaticSource):
            mag = body.vmag
        super(SpectroFeasibilityForm, self).__init__(*args, **kwargs)
        self.fields['magnitude'].initial = mag
        # Set default SFU value of 70; replace with value from fetch if it isn't None
        self.fields['sfu'].initial = 70.0
        self.fields['sfu'].initial = self.fields['sfu'].initial if sfu_values[1] is None else sfu_values[1].value


class AddTargetForm(forms.Form):
    origin = forms.ChoiceField(choices=ORIGINS, widget=forms.HiddenInput())
    target_name = forms.CharField(label="Enter target to add...", max_length=30, required=True, widget=forms.TextInput(attrs={'size': '20'}),
                             error_messages={'required': _(u'Target name is required')})


class AddPeriodForm(forms.Form):
    period = forms.FloatField(label="Period", initial=None, required=True, widget=forms.DateTimeInput(attrs={'style': 'width: 75px;'}))
    error = forms.FloatField(label="Error", initial=0.0, required=False, widget=forms.DateTimeInput(attrs={'style': 'width: 75px;'}))
    quality = forms.ChoiceField(required=False, choices=LC_QUALITIES)
    notes = forms.CharField(label="Notes", required=False, widget=forms.DateTimeInput(attrs={'style': 'width: 275px;'}))
    preferred = forms.BooleanField(initial=False, required=False)


class UpdateAnalysisStatusForm(forms.Form):
    update_body = forms.ChoiceField(required=False, choices=[])
    status = forms.ChoiceField(required=False, choices=STATUS_CHOICES)
