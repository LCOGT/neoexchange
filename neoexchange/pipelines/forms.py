from datetime import datetime

from django import forms

from core.models import Proposal

class DLDataForm(forms.Form):
    obs_date = forms.DateField(label='Date')
    proposals = forms.MultipleChoiceField(label="Proposal code", required=True)
    spectraonly = forms.BooleanField(label="Only download Spectra", required=False)
    dlengimaging = forms.BooleanField(label="Download imaging for LCOEngineering", required=False)
    numdays = forms.FloatField(label="How many extra days to search", required=False)

    def clean_obs_date(self):
        date = self.cleaned_data['obs_date']
        datestr = datetime.strftime(date,'%Y%m%d')
        return datestr

    def __init__(self, *args, **kwargs):
        self.proposal = kwargs.pop('proposal', None)
        super(DLDataForm, self).__init__(*args, **kwargs)
        proposals = Proposal.objects.filter(active=True)
        proposal_choices = [(proposal.code, proposal.title) for proposal in proposals]
        self.fields['proposals'].choices = proposal_choices
