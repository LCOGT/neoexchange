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

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.body import Body

TAX_SCHEME_CHOICES = (
                        ('T', 'Tholen'),
                        ('Ba', 'Barucci'),
                        ('Td', 'Tedesco'),
                        ('H', 'Howell'),
                        ('S', 'SMASS'),
                        ('B', 'Bus'),
                        ('3T', 'S3OS2_TH'),
                        ('3B', 'S3OS2_BB'),
                        ('BD', 'Bus-DeMeo'),
                        ('Sd', 'SDSS')
                     )

TAX_REFERENCE_CHOICES = (
                        ('PDS6', 'Neese, Asteroid Taxonomy V6.0, (2010).'),
                        ('BZ04', 'Binzel, et al. (2004).'),
                        ('SDSS', 'Hasselmann, et al. Asteroid Taxonomy V1.1, (2012).')
                     )

SPECTRAL_WAV_CHOICES = (
                        ('Vis', 'Visible'),
                        ('NIR', 'Near Infrared'),
                        ('Vis+NIR', 'Both Visible and Near IR'),
                        ('NA', 'None Yet.'),
                     )

SPECTRAL_SOURCE_CHOICES = (
                        ('S', 'SMASS'),
                        ('M', 'MANOS'),
                        ('U', 'Unknown'),
                        ('O', 'Other')
                     )


class SpectralInfo(models.Model):
    body                = models.ForeignKey(Body, on_delete=models.CASCADE)
    taxonomic_class     = models.CharField('Taxonomic Class', blank=True, null=True, max_length=6)
    tax_scheme          = models.CharField('Taxonomic Scheme', blank=True, choices=TAX_SCHEME_CHOICES, null=True, max_length=2)
    tax_reference       = models.CharField('Reference source for Taxonomic data', max_length=6, choices=TAX_REFERENCE_CHOICES, blank=True, null=True)
    tax_notes           = models.CharField('Notes on Taxonomic Classification', max_length=30, blank=True, null=True)

    def make_readable_tax_notes(self):
        text = self.tax_notes
        text_out = ''
        end = ''
        if self.tax_reference == 'PDS6':
            if "|" in text:
                chunks = text.split('|')
                text = chunks[0]
                end = chunks[1]
            if self.tax_scheme in "T,Ba,Td,H,S,B":
                if text[0].isdigit():
                    if len(text) > 1:
                        if text[1].isdigit():
                            text_out = text_out + ' %s color indices were used.\n' % (text[0:2])
                        else:
                            text_out = text_out + ' %s color indices were used.\n' % (text[0])
                    else:
                        text_out = text_out + ' %s color indices were used.\n' % (text[0])
                if "G" in text:
                    text_out += ' Used groundbased radiometric albedo.'
                if "I" in text:
                    text_out += ' Used IRAS radiometric albedo.'
                if "A" in text:
                    text_out += ' An Unspecified albedo was used to eliminate Taxonomic degeneracy.'
                if "S" in text:
                    text_out += ' Used medium-resolution spectrum by Chapman and Gaffey (1979).'
                if "s" in text:
                    text_out += ' Used high-resolution spectrum by Xu et al (1995) or Bus and Binzel (2002).'
            elif self.tax_scheme == "BD":
                if "a" in text:
                    text_out += ' Visible: Bus (1999), Bus and Binzel (2002a), Bus and Binzel (2002b). NIR: DeMeo et al. (2009).'
                if "b" in text:
                    text_out += ' Visible: Xu (1994), Xu et al. (1995). NIR: DeMeo et al. (2009).'
                if "c" in text:
                    text_out += ' Visible: Burbine (2000), Burbine and Binzel (2002). NIR: DeMeo et al. (2009).'
                if "d" in text:
                    text_out += ' Visible: Binzel et al. (2004c). NIR: DeMeo et al. (2009).'
                if "e" in text:
                    text_out += ' Visible and NIR: DeMeo et al. (2009).'
                if "f" in text:
                    text_out += ' Visible: Binzel et al. (2004b).  NIR: DeMeo et al. (2009).'
                if "g" in text:
                    text_out += ' Visible: Binzel et al. (2001).  NIR: DeMeo et al. (2009).'
                if "h" in text:
                    text_out += ' Visible: Bus (1999), Bus and Binzel (2002a), Bus and Binzel (2002b).  NIR: Binzel et al. (2004a).'
                if "i" in text:
                    text_out += ' Visible: Bus (1999), Bus and Binzel (2002a), Bus and Binzel (2002b).  NIR: Rivkin et al. (2005).'
        elif self.tax_reference == 'SDSS':
            chunks = text.split('|')
            if int(chunks[1]) > 1:
                plural = 's'
            else:
                plural = ''
            text_out = 'Probability score of {} found using {} observation{}.'.format(chunks[0], chunks[1], plural)
            if chunks[2] != '-' and chunks[2] != self.taxonomic_class:
                text_out += ' | Other less likely taxonomies also found ({})'.format(chunks[2].replace(self.taxonomic_class, ''))
        text_out = text_out+end
        return text_out

    class Meta:
        verbose_name = _('Spectroscopy Detail')
        verbose_name_plural = _('Spectroscopy Details')
        db_table = 'ingest_taxonomy'

    def __str__(self):
        return "%s is a %s-Type Asteroid" % (self.body.name, self.taxonomic_class)


class PreviousSpectra(models.Model):
    body        = models.ForeignKey(Body, on_delete=models.CASCADE)
    spec_wav    = models.CharField('Wavelength', blank=True, null=True, max_length=7, choices=SPECTRAL_WAV_CHOICES)
    spec_vis    = models.URLField('Visible Spectra Link', blank=True, null=True)
    spec_ir     = models.URLField('IR Spectra Link', blank=True, null=True)
    spec_ref    = models.CharField('Spectra Reference', max_length=10, blank=True, null=True)
    spec_source = models.CharField('Source', max_length=1, blank=True, null=True, choices=SPECTRAL_SOURCE_CHOICES)
    spec_date   = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = _('External Spectroscopy')
        verbose_name_plural = _('External Spectroscopy')
        db_table = 'ingest_previous_spectra'

    def __unicode__(self):
        return "%s has %s spectra of %s" % (self.spec_source, self.spec_wav, self.body.name)
