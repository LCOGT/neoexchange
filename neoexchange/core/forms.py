'''
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2014-2018 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime, date, timedelta
from django import forms
from django.db.models import Q
from .models import Body, Proposal, Block
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from astrometrics.sources_subs import fetch_filter_list
import logging
logger = logging.getLogger(__name__)


SITES = (('V37','McDonald, Texas (ELP - V37; Sinistro)'),
         ('F65','Maui, Hawaii (FTN - F65)'),
         ('E10','Siding Spring, Aust. (FTS - E10)'),
         ('W86','CTIO, Chile (LSC - W85-87; Sinistro)'),
         ('K92','Sutherland, S. Africa (CPT - K91-93; Sinistro)'),
         ('Q63','Siding Spring, Aust. (COJ - Q63-64; Sinistro)'),
         ('Q58','Siding Spring, Aust. (COJ - Q58-59; 0.4m)'),
         ('Z21','Tenerife, Spain (TFN - Z17,Z21; 0.4m)'),
         ('T04','Maui, Hawaii (OGG - T03-04; 0.4m)'),
         ('W89','CTIO, Chile (LSC - W89,W79; 0.4m)'),
         ('V38','McDonald, Texas (ELP - V38; 0.4m)'),
         ('L09','Sutherland, S. Africa (CPT - L09; 0.4m)'))

class EphemQuery(forms.Form):

    target = forms.CharField(label="Enter target name...", max_length=14, required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'Target name is required')})
    site_code = forms.ChoiceField(required=True, choices=SITES)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d',], initial=date.today, required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'UTC date is required')})
    alt_limit = forms.FloatField(initial=30.0, required=True, widget=forms.TextInput(attrs={'size':'4'}))

    def clean_target(self):
        name = self.cleaned_data['target']
        body = Body.objects.filter(Q(provisional_name__startswith = name )|Q(provisional_packed__startswith = name)|Q(name__startswith = name))
        if body.count() == 1 :
            return body[0]
        elif body.count() == 0:
            raise forms.ValidationError("Object not found.")
        elif body.count() > 1:
            newbody = Body.objects.filter(Q(provisional_name__exact = name )|Q(provisional_packed__exact = name)|Q(name__exact = name))
            if newbody.count() == 1:
                return newbody[0]
            else:
                raise forms.ValidationError("Multiple objects found.")

class ScheduleForm(forms.Form):
    proposal_code = forms.ChoiceField(required=True)
    site_code = forms.ChoiceField(required=True, choices=SITES)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d',], initial=date.today, required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'UTC date is required')})

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


class ScheduleCadenceForm(forms.Form):
    proposal_code = forms.ChoiceField(required=True, widget=forms.Select(attrs={'id': 'id_proposal_code_cad',}))
    site_code = forms.ChoiceField(required=True, choices=SITES, widget=forms.Select(attrs={'id': 'id_site_code_cad',}))
    start_time = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M'], initial=datetime.today, required=True, error_messages={'required': _(u'UTC start date is required')})
    end_time = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M'], initial=datetime.today, required=True, error_messages={'required': _(u'UTC end date is required')})
    period = forms.FloatField(initial=2.0, required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'Period is required')})
    jitter = forms.FloatField(initial=0.25, required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'Jitter is required')})

    # def clean_start_time(self):
    #     start = self.cleaned_data['start_time']
    #     if start < datetime.utcnow():
    #         raise forms.ValidationError("Window cannot start in the past")
    #     return start
    #
    # def clean_end_time(self):
    #     end = self.cleaned_data['end_time']
    #     if end < datetime.utcnow():
    #         raise forms.ValidationError("Window cannot end in the past")
    #     return end

    def clean(self):
        cleaned_data = super(ScheduleCadenceForm, self).clean()
        start = cleaned_data['start_time']
        end = cleaned_data['end_time']
        if end < start:
            raise forms.ValidationError("End date must be after start date")

    def __init__(self, *args, **kwargs):
        self.proposal_code = kwargs.pop('proposal_code', None)
        super(ScheduleCadenceForm, self).__init__(*args, **kwargs)
        proposals = Proposal.objects.filter(active=True)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        self.fields['proposal_code'].choices = proposal_choices

class ScheduleBlockForm(forms.Form):
    start_time = forms.DateTimeField(widget=forms.HiddenInput(), input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'])
    end_time = forms.DateTimeField(widget=forms.HiddenInput(), input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'])
    exp_count = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    exp_length = forms.FloatField(widget=forms.HiddenInput(), required=False)
    slot_length = forms.FloatField(widget=forms.NumberInput(attrs={'size': '5'}))
    filter_pattern = forms.CharField(widget=forms.TextInput(attrs={'size':'20'}))
    pattern_iterations = forms.FloatField(widget=forms.HiddenInput(), required=False)
    proposal_code = forms.CharField(max_length=20,widget=forms.HiddenInput())
    site_code = forms.CharField(max_length=5,widget=forms.HiddenInput())
    group_id = forms.CharField(max_length=30,widget=forms.HiddenInput())
    utc_date = forms.DateField(input_formats=['%Y-%m-%d',], widget=forms.HiddenInput(), required=False)
    jitter = forms.FloatField(widget=forms.HiddenInput(), required=False)
    period = forms.FloatField(widget=forms.HiddenInput(), required=False)

    def clean_start_time(self):
        start = self.cleaned_data['start_time']
        window_cutoff = datetime.utcnow() - timedelta(days=1)
        if start <= window_cutoff:
            raise forms.ValidationError("Window cannot start in the past")
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
            stripped_pattern = pattern.replace(" ",",").replace(";",",").replace("/",",").replace(".",",")
            chunks = stripped_pattern.split(',')
            chunks=filter(None, chunks)
            if chunks.count(chunks[0]) == len(chunks):
                chunks = [chunks[0]]
            cleaned_filter_pattern = ",".join(chunks)
        except KeyError as e:
            cleaned_filter_pattern = ','
        return cleaned_filter_pattern

    def clean(self):
        site = self.cleaned_data['site_code']
        if not fetch_filter_list(site):
            raise forms.ValidationError("This Site/Telescope combination is not currently available.")
        try:
            pattern = self.cleaned_data['filter_pattern']
            chunks = pattern.split(',')
            bad_filters = [x for x in chunks if x not in fetch_filter_list(site)]
            if len(bad_filters) > 0:
                if len(bad_filters) == 1:
                    raise ValidationError(_('%(bad)s is not an acceptable filter at this site.'), params={'bad': ",".join(bad_filters)}, )
                else:
                    raise ValidationError(_('%(bad)s are not acceptable filters at this site.'), params={'bad': ",".join(bad_filters)}, )
        except KeyError as e:
            raise ValidationError(_('Dude, you had to actively input a bunch of spaces and nothing else to see this error. Why?? Just pick a filter from the list! %(filters)s'), params={'filters': ",".join(fetch_filter_list(site))}, )
        if not self.cleaned_data['exp_length'] and not self.cleaned_data['exp_count']:
            raise forms.ValidationError("The slot length is too short")
        elif self.cleaned_data['exp_count'] == 0:
            raise forms.ValidationError("There must be more than 1 exposure")
        elif self.cleaned_data['exp_length'] < 0.1:
            raise forms.ValidationError("Exposure length is too short")
        elif self.cleaned_data['period'] > 0.0 and self.cleaned_data['slot_length'] / 60.0 > self.cleaned_data['jitter']:
            raise forms.ValidationError("Jitter must be larger than slot length")

class MPCReportForm(forms.Form):
    block_id = forms.IntegerField(widget=forms.HiddenInput())
    report = forms.CharField(widget=forms.Textarea)

    def clean(self):
        try:
            block = Block.objects.get(id=self.cleaned_data['block_id'])
            self.cleaned_data['block'] = block
        except:
            raise forms.ValidationError('Block ID %s is not valid' % self.cleaned_data['block_id'])




