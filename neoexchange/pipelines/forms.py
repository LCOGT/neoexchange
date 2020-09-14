from datetime import datetime

from django import forms

from core.models import Proposal

class DLDataForm(forms.Form):
    obs_date = forms.DateField(label='Date', widget=forms.DateInput(attrs={'type': 'date'}))
    proposals = forms.MultipleChoiceField(label="Proposal code", required=True,  widget=forms.widgets.SelectMultiple(attrs={'class': 'multiselect'}))
    spectraonly = forms.BooleanField(label="Only download Spectra", required=False)
    dlengimaging = forms.BooleanField(label="Download imaging for LCOEngineering", required=False)
    numdays = forms.FloatField(label="How many extra days to search", required=False)


    def __init__(self, *args, **kwargs):
        self.proposal = kwargs.pop('proposal', None)
        super(DLDataForm, self).__init__(*args, **kwargs)
        proposals = Proposal.objects.filter(active=True)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        self.fields['proposals'].choices = proposal_choices
