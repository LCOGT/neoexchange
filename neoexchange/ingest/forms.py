from datetime import datetime
from django import forms
from django.db.models import Q
from ingest.models import Body, Proposal
from django.utils.translation import ugettext as _

class EphemQuery(forms.Form):
    SITES = (('V37','ELP (V37)'),('F65','FTN (F65)'),('E10', 'FTS (E10)'),('W86','LSC (W85-87)'),('K92','CPT (K91-93)'),('Q63','COJ (Q63-64)'))
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
    SITES = (('V37','ELP (V37)'),('F65','FTN (F65)'),('E10', 'FTS (E10)'),('W86','LSC (W85-87)'),('K92','CPT (K91-93)'),('Q63','COJ (Q63-64)'))
    proposals = Proposal.objects.all()
    proposal_choices = []
    for proposal in proposals.values():
        proposal_choices.append((str(proposal['code']), str(proposal['title'])))
    proposal_code = forms.ChoiceField(required=True, choices=proposal_choices)
    site_code = forms.ChoiceField(required=True, choices=SITES)
    utc_date = forms.DateField(input_formats=['%Y-%m-%d',], initial=datetime.utcnow().date(), required=True, widget=forms.TextInput(attrs={'size':'10'}), error_messages={'required': _(u'UTC date is required')})
    body_id = forms.IntegerField(widget=forms.HiddenInput())
