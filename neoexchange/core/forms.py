from datetime import datetime, timedelta
from django import forms
from django.db.models import Q
from .models import Body, Proposal
from django.utils.translation import ugettext_lazy as _
import logging
logger = logging.getLogger(__name__)

SITES = (('V37','ELP (V37)'),
         ('F65','FTN (F65)'),
         ('E10', 'FTS (E10)'),
         ('W85','LSC (W85; SBIG)'),
         ('W86','LSC (W86-87)'),
         ('K92','CPT (K91-93)'),
         ('Q63','COJ (Q63-64)'))

class EphemQuery(forms.Form):

    target = forms.CharField(label="Enter target name...", max_length=10, required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'Target name is required')})
    site_code = forms.ChoiceField(required=True, choices=SITES)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d',], initial=datetime.utcnow().date(), required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'UTC date is required')})
    alt_limit = forms.FloatField(initial=30.0, required=True, widget=forms.TextInput(attrs={'size':'4'}))

    def clean_target(self):
        name = self.cleaned_data['target']
        body = Body.objects.filter(Q(provisional_name__icontains = name )|Q(provisional_packed__icontains = name)|Q(name__icontains = name))
        if body.count() == 1 :
            return body[0]
        elif body.count() == 0:
            raise forms.ValidationError("Object not found.")
        elif body.count() > 1:
            raise forms.ValidationError("Multiple objects found.")

class ScheduleForm(forms.Form):
    proposal_code = forms.ChoiceField(required=True)
    site_code = forms.ChoiceField(required=True, choices=SITES)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d',], initial=datetime.utcnow().date(), required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'UTC date is required')})
    # body_id = forms.IntegerField(widget=forms.HiddenInput())
    # ok_to_schedule = forms.BooleanField(initial=False, required=False, widget=forms.HiddenInput())

    # def clean_body_id(self):
    #     body = Body.objects.filter(pk=self.cleaned_data['body_id'])
    #     if body.count() == 1 :
    #         return body[0]
    #     elif body.count() == 0:
    #         raise forms.ValidationError("Object not found.")
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


class ScheduleBlockForm(forms.Form):
    start_time = forms.DateTimeField(widget=forms.HiddenInput(), input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'])
    end_time = forms.DateTimeField(widget=forms.HiddenInput(), input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'])
    exp_count = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    exp_length = forms.FloatField(widget=forms.HiddenInput(), required=False)
    slot_length = forms.FloatField(widget=forms.NumberInput(attrs={'size': '5'}))
    proposal_code = forms.CharField(max_length=20,widget=forms.HiddenInput())
    site_code = forms.CharField(max_length=5,widget=forms.HiddenInput())
    group_id = forms.CharField(max_length=30,widget=forms.HiddenInput())

    def clean_start_time(self):
        start = self.cleaned_data['start_time']
        logger.debug("cleaned_data=%s" % (self.cleaned_data))
        window_cutoff = datetime.utcnow() - timedelta(days=1)
        logger.debug("In clean_start_time %s %s" % (start, window_cutoff))
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

    def clean(self):
        if not self.cleaned_data['exp_length'] and not self.cleaned_data['exp_count']:
            raise forms.ValidationError("The slot length is too short")
        elif self.cleaned_data['exp_count'] == 0:
            raise forms.ValidationError("There must be more than 1 exposure")
        elif self.cleaned_data['exp_length'] < 0.1:
            raise forms.ValidationError("Exposure length is too short")
