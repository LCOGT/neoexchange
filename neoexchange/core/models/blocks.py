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
from collections import Counter, OrderedDict
from datetime import datetime
import warnings
import logging

from django.conf import settings
from django.forms.models import model_to_dict
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.contrib.contenttypes.fields import GenericRelation
from requests.compat import urljoin
from numpy import frombuffer, mean
from astropy.wcs import FITSFixedWarning

from astrometrics.ephem_subs import compute_ephem, comp_sep
from core.archive_subs import check_for_archive_images, lco_api_call

from core.models.body import Body
from core.models.frame import Frame
from core.models.proposal import Proposal
from core.models.dataproducts import DataProduct
from core.models.sources import StaticSource

TELESCOPE_CHOICES = (
                        ('1m0', '1-meter'),
                        ('2m0', '2-meter'),
                        ('0m4', '0.4-meter'),
                        ('2m4', '2.4-meter')
                    )

SITE_CHOICES = (
                    ('ogg', 'Haleakala'),
                    ('coj', 'Siding Spring'),
                    ('lsc', 'Cerro Tololo'),
                    ('elp', 'McDonald'),
                    ('cpt', 'Sutherland'),
                    ('tfn', 'Tenerife'),
                    ('sbg', 'SBIG cameras'),
                    ('sin', 'Sinistro cameras'),
                    ('spc', 'Spectral cameras'),
                    ('lco', 'Las Campanas'),
                    ('mro', 'Magdalena Ridge')
    )

NONLCO_SITES = ['lco', 'mro']

logger = logging.getLogger(__name__)


class SuperBlock(models.Model):

    cadence         = models.BooleanField(default=False)
    rapid_response  = models.BooleanField('Is this a ToO/Rapid Response observation?', default=False)
    body            = models.ForeignKey(Body, null=True, blank=True, on_delete=models.CASCADE)
    calibsource     = models.ForeignKey('StaticSource', null=True, blank=True, on_delete=models.CASCADE)
    proposal        = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    block_start     = models.DateTimeField(null=True, blank=True, db_index=True)
    block_end       = models.DateTimeField(null=True, blank=True, db_index=True)
    groupid         = models.CharField(max_length=55, null=True, blank=True)
    tracking_number = models.CharField(max_length=15, null=True, blank=True, db_index=True)
    period          = models.FloatField('Spacing between cadence observations (hours)', null=True, blank=True)
    jitter          = models.FloatField('Acceptable deviation before or after strict period (hours)', null=True, blank=True)
    timeused        = models.FloatField('Time used (seconds)', null=True, blank=True)
    active          = models.BooleanField(default=False)
    dataproduct     = GenericRelation(DataProduct, related_query_name='sblock')

    @cached_property
    def get_blocks(self):
        """Return and Cache the queryset of all blocks connected to the SuperBlock"""
        return self.block_set.all()

    def current_name(self):
        name = ''
        if self.body is not None:
            name = self.body.current_name()
        elif self.calibsource is not None:
            name = self.calibsource.current_name()
        return name

    def make_obsblock_link(self):
        url = ''
        if self.tracking_number is not None and self.tracking_number != '':
            url = urljoin(settings.PORTAL_USERREQUEST_URL, self.tracking_number)
        return url

    def get_sites(self):
        bl = self.get_blocks
        qs = list(set([b.site for b in bl]))
        qs = [q for q in qs if q is not None]
        if qs:
            return ", ".join(qs)
        else:
            return None

    def get_telclass(self):
        bl = self.get_blocks
        qs = list(set([(b.telclass, b.obstype) for b in bl]))
        qs.sort()

        # Convert obstypes into "(S)" suffix for spectra, nothing for imaging
        class_obstype = [x[0]+str(x[1]).replace(str(Block.OPT_SPECTRA), '(S)').replace(str(Block.OPT_SPECTRA_CALIB), '(SC)').replace(str(Block.OPT_IMAGING), '') for x in qs]

        return ", ".join(class_obstype)

    def get_obsdetails(self):
        obs_details_str = ""

        bl = self.get_blocks
        qs = [(b.num_exposures, b.exp_length) for b in bl]

        # Count number of unique N exposure x Y exposure length combinations
        counts = Counter([elem for elem in qs])

        if len(counts) > 1:
            obs_details = []
            for c in counts.items():
                obs_details.append("%d of %dx%.1f secs" % (c[1], c[0][0], c[0][1]))

            obs_details_str = ", ".join(obs_details)
        elif len(counts) == 1:
            c = list(counts)
            obs_details_str = "%dx%.1f secs" % (c[0][0], c[0][1])

        return obs_details_str

    def get_num_observed(self):
        bl = self.get_blocks
        num_obs = sum([b.num_observed for b in bl if b.num_observed and b.num_observed >= 1])
        return num_obs, bl.count()

    def get_num_reported(self):
        bl = self.get_blocks
        num_reported = len([b for b in bl if b.reported is True])
        return num_reported, bl.count()

    def get_last_observed(self):
        last_observed = None
        qs = Block.objects.filter(superblock=self.id, num_observed__gte=1)
        if qs.count() > 0:
            last_observed = qs.latest('when_observed').when_observed

        return last_observed

    def get_last_reported(self):
        last_reported = None
        qs = Block.objects.filter(superblock=self.id, reported=True)
        if qs.count() > 0:
            last_reported = qs.latest('when_reported').when_reported

        return last_reported

    def get_obstypes(self):
        obstype = []
        obstypes = Block.objects.filter(superblock=self.id).values_list('obstype', flat=True).distinct()

        return ",".join([str(x) for x in obstypes])

    class Meta:
        verbose_name = _('SuperBlock')
        verbose_name_plural = _('SuperBlocks')
        db_table = 'ingest_superblock'

    def __str__(self):
        if self.active:
            text = ''
        else:
            text = 'not '

        return '%s is %sactive' % (self.tracking_number, text)


class Block(models.Model):

    RATE_CHOICES = (
        (100, 'Target Tracking'),
        (50, 'Half-Rate Tracking'),
        (0, 'Sidereal Tracking'),
        (-99, 'Non-Standard Tracking')
    )

    OPT_IMAGING = 0
    OPT_SPECTRA = 1
    OPT_IMAGING_CALIB = 2
    OPT_SPECTRA_CALIB = 3
    OBSTYPE_CHOICES = (
                        (OPT_IMAGING, 'Optical imaging'),
                        (OPT_SPECTRA, 'Optical spectra'),
                        (OPT_IMAGING_CALIB, 'Optical imaging calibration'),
                        (OPT_SPECTRA_CALIB, 'Optical spectro calibration')
                      )

    telclass        = models.CharField(max_length=3, null=False, blank=False, default='1m0', choices=TELESCOPE_CHOICES)
    site            = models.CharField(max_length=3, choices=SITE_CHOICES, null=True)
    body            = models.ForeignKey(Body, null=True, blank=True, on_delete=models.CASCADE)
    calibsource     = models.ForeignKey('StaticSource', null=True, blank=True, on_delete=models.CASCADE)
    superblock      = models.ForeignKey(SuperBlock, null=True, blank=True, on_delete=models.CASCADE)
    obstype         = models.SmallIntegerField('Observation Type', null=False, blank=False, default=0, choices=OBSTYPE_CHOICES)
    block_start     = models.DateTimeField(null=True, blank=True, db_index=True)
    block_end       = models.DateTimeField(null=True, blank=True, db_index=True)
    request_number  = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    num_exposures   = models.IntegerField(null=True, blank=True)
    exp_length      = models.FloatField('Exposure length in seconds', null=True, blank=True)
    num_observed    = models.IntegerField(help_text='No. of scheduler blocks executed', null=True, blank=True)
    when_observed   = models.DateTimeField(help_text='Date/time of latest frame', null=True, blank=True)
    active          = models.BooleanField(default=False)
    reported        = models.BooleanField(default=False)
    when_reported   = models.DateTimeField(null=True, blank=True)
    dataproduct     = GenericRelation(DataProduct, related_query_name='block')
    tracking_rate   = models.SmallIntegerField('Tracking Strategy', choices=RATE_CHOICES, blank=False, default=100)

    @cached_property
    def get_blockuid(self):
        """Return and Cache the BLKUID. Returns a list (can be empty) of the BLKUID(s)"""
        warnings.simplefilter('ignore', FITSFixedWarning)
        blockuid = []

        frames_qs = Frame.objects.filter(block=self, frametype=Frame.BANZAI_RED_FRAMETYPE, frameid__isnull=False)
        if frames_qs.count() > 1:
            frame = frames_qs.earliest('midpoint')
            frames = [frame, ]
            if self.num_observed and self.num_observed >= 2:
                if self.num_observed > 2:
                    logger.warning(f"More than 2 observations of Block id={self.id} - cannot retrieve all BLKUIDs")
                last_frame = Frame.objects.filter(block=self, frametype=Frame.BANZAI_RED_FRAMETYPE, frameid__isnull=False).latest('midpoint')
                frames.append(last_frame)
            for frame in frames:
                if frame is not None:
                    if frame.frameid is not None:
                        url = f"{settings.ARCHIVE_FRAMES_URL}{frame.frameid}"
                        headers = lco_api_call(url)
                        frame_blockuid = headers.get('BLKUID', None)
                        if frame_blockuid is not None:
                            blockuid.append(str(frame_blockuid))
        return blockuid

    @cached_property
    def get_blockdayobs(self):
        """Return and Cache the DAY_OBS"""
        warnings.simplefilter('ignore', FITSFixedWarning)
        blockdayobs = None
        frames_qs = Frame.objects.filter(block=self, frametype=Frame.BANZAI_RED_FRAMETYPE, frameid__isnull=False)
        if frames_qs.count() > 1:
            frame = frames_qs.first()
            if frame is not None:
                if frame.frameid is not None:
                    url = f"{settings.ARCHIVE_FRAMES_URL}{frame.frameid}"
                    headers = lco_api_call(url)
                    blockdayobs = headers.get('DAY_OBS', None)
                    if blockdayobs is not None:
                        blockdayobs = str(blockdayobs).replace('-','')
        return blockdayobs

    def current_name(self):
        name = ''
        if self.body is not None:
            name = self.body.current_name()
        elif self.calibsource is not None:
            name = self.calibsource.name
        return name

    def make_obsblock_link(self):
        url = ''
        if self.request_number is not None and self.request_number != '':
            url = urljoin(settings.PORTAL_REQUEST_URL, self.request_number)
        return url

    def get_obsdetails(self):
        """Returns the number of exposures and exposure length as a string e.g. '6x60.0 secs'"""
        obs_details_str = ""

        if self.num_exposures and self.exp_length:
            obs_details_str = "%dx%.1f secs" % (self.num_exposures, self.exp_length)

        return obs_details_str

    def num_red_frames(self):
        """Returns the total number of reduced frames (quicklook and fully reduced)"""
        return self.frame_set.filter(frametype__in=[11, 61, 71, 91]).count()

    def num_unique_red_frames(self):
        """Returns the number of *unique* reduced frames (quicklook OR fully reduced)"""
        reduced_frames = self.frame_set.filter(frametype__in=[61, 71, 91])
        ql_frames = self.frame_set.filter(frametype=11)
        if reduced_frames.count() >= ql_frames.count():
            total_exposure_number = reduced_frames.count()
        else:
            total_exposure_number = ql_frames.count()
        return total_exposure_number

    def num_spectro_frames(self):
        """Returns the numbers of different types of spectroscopic frames"""
        num_moltypes_string = 'No data'
        data, num_frames = check_for_archive_images(self.request_number, obstype='', obj=self.current_name())
        if num_frames > 0:
            moltypes = [x['OBSTYPE'] if x['RLEVEL'] != 90 else "TAR" for x in data]
            num_moltypes = {x: moltypes.count(x) for x in set(moltypes)}
            num_moltypes_sort = OrderedDict(sorted(num_moltypes.items(), reverse=True))
            num_moltypes_string = ", ".join([x+": "+str(num_moltypes_sort[x]) for x in num_moltypes_sort])
        return num_moltypes_string

    def num_spectra_complete(self):
        """Returns the number of actually completed spectra excluding lamps/arcs"""
        num_spectra = 0
        data, num_frames = check_for_archive_images(self.request_number, obstype='')
        if num_frames > 0:
            moltypes = [x['OBSTYPE'] if x['RLEVEL'] != 90 else "TAR" for x in data]
            num_spectra = moltypes.count('SPECTRUM')
        return num_spectra

    def num_candidates(self):
        return Candidate.objects.filter(block=self.id).count()

    def where_observed(self):
        where_observed=''
        if self.num_observed is not None:
            frames = Frame.objects.filter(block=self.id, frametype=Frame.BANZAI_RED_FRAMETYPE)
            if frames.count() > 0:
                # Code for producing full site strings + site codes e.g. 'W85'
                # where_observed_qs = frames.distinct('sitecode')
                # where_observed = ",".join([site.return_site_string() + " (" + site.sitecode + ")" for site in where_observed_qs])
                # Alternative which doesn't need PostgreSQL DISTINCT ON <fieldname>
                unique_sites = frames.values('sitecode').distinct()
                where_observed = ",".join([frames.filter(sitecode=site['sitecode'])[0].return_site_string() + " (" + site['sitecode'] + ")" for site in unique_sites])
        return where_observed

    class Meta:
        verbose_name = _('Observation Block')
        verbose_name_plural = _('Observation Blocks')
        db_table = 'ingest_block'

    def __str__(self):
        if self.active:
            text = ''
        else:
            text = 'not '

        return '%s is %sactive' % (self.request_number, text)


class ExportedBlock(models.Model):
    """Class to hold record of Blocks that have been exported elsewhere e.g. PDS
    """

    PDS_V4 = 1
    TARBALL = 10
    EXPORT_CHOICES = (
                        (PDS_V4, 'PDS V4 collection'),
                        (TARBALL, 'Tarball of files')
                     )
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    input_path = models.CharField('Input path to exporter', max_length=4096, null=True)
    export_path = models.CharField('Export path from exporter', max_length=4096, null=True)
    export_format = models.SmallIntegerField('Export format', choices=EXPORT_CHOICES, blank=False, default=1)
    when_exported  = models.DateTimeField(default=datetime.utcnow)
    notes = models.TextField('Notes', blank=True, null=True)

    class Meta:
        verbose_name = _('Exported Block')
        verbose_name_plural = _('Exported Blocks')

    def __str__(self):
        export_date = self.when_exported.strftime("%Y-%m-%d %H:%M")
        return f"{self.block.request_number} -> {self.export_path} on {export_date}"


class Candidate(models.Model):
    """Class to hold candidate moving object detections found by the moving
    object code"""

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    cand_id = models.PositiveIntegerField('Candidate Id')
    score = models.FloatField('Candidate Score', db_index=True)
    avg_midpoint = models.DateTimeField('Average UTC midpoint', db_index=True)
    avg_x = models.FloatField('Average CCD X co-ordinate')
    avg_y = models.FloatField('Average CCD Y co-ordinate')
    avg_ra = models.FloatField('Average Observed RA (degrees)')
    avg_dec = models.FloatField('Average Observed Dec (degrees)')
    avg_mag = models.FloatField('Average Observed Magnitude', blank=True, null=True)
    speed = models.FloatField('Speed (degrees/day)')
    sky_motion_pa = models.FloatField('Position angle of motion on the sky (degrees)')
    detections = models.BinaryField('Detections array', blank=True, null=True, editable=False)

    def convert_speed(self):
        """Convert speed in degrees/day into arcsec/min"""
        new_speed = (self.speed*3600.0)/(24.0*60.0)
        return new_speed

    def unpack_dets(self):
        """Unpacks the binary BLOB from the detections field into a numpy
        structured array"""
        dtypes = detections_array_dtypes()
        dets = frombuffer(self.detections, dtype=dtypes)
        return dets

    def compute_separation(self, body=None, time=None):
        """Computes the separation between the Candidate's avg_ra and avg_dec
        and the RA, Dec of the body at a time of avg_midpoint"""
        if body is None or type(body) != 'core.models.Body':
            body = self.block.body
        if time is None:
            time = self.avg_midpoint

        try:
            elements = model_to_dict(body)
            emp_line = compute_ephem(time, elements, self.block.site, perturb=False)
            separation = comp_sep(self.avg_ra, self.avg_dec, emp_line['ra'], emp_line['dec'])
        except AttributeError:
            separation = None

        return separation

    class Meta:
        verbose_name = _('Candidate')

    def __str__(self):
        return "%s#%04d" % (self.block.request_number, self.cand_id)


def detections_array_dtypes():
    """Declare the columns and types of the structured numpy array for holding
    the per-frame detections from the mtdlink moving object code"""

    dtypes = {  'names' : ('det_number', 'frame_number', 'sext_number', 'jd_obs', 'ra', 'dec', 'x', 'y', 'mag', 'fwhm', 'elong', 'theta', 'rmserr', 'deltamu', 'area', 'score', 'velocity', 'sky_pos_angle', 'pixels_frame', 'streak_length'),
                'formats' : ('i4',       'i1',           'i4',          'f8',     'f8', 'f8', 'f4', 'f4', 'f4', 'f4',   'f4',    'f4',    'f4',     'f4',       'i4',   'f4',   'f4',       'f4',        'f4',           'f4')
             }

    return dtypes

def obs_details_retriever(ref_fields):
    """Given a set of reference fields <ref_fields>, returns information about
    each observed block associated about the reference field in string format.
    Information includes, for each observed filter within the observed block:
    Tracking #, Request #, Site, obs details for superblock, observed filter,
    \# of raw frames, ratio of frames with good zeropoints to total neox
    reduced frames, fwhm, range of block observation time"""
    try:
        num_ref_fields = len(ref_fields)
    except TypeError:
        ref_fields = [ref_fields, ]
    ref_count = 0
    lines = []
    for ref in ref_fields:
        ref_count +=1
        try:
            blocks = Block.objects.filter(superblock__calibsource=ref)
            obs_blocks = blocks.filter(num_observed__gte=1)
        except ValueError:
            blocks = []
            obs_blocks = ref_fields.filter(num_observed__gte =1)
            for ref in ref_fields:
                blocks.append(ref)
        for block in obs_blocks:
            lines.append(f"#Track# Rquest# Site(MPC) Obs details Filter #raw #good_zp/#num reduced frames FWHM \n {block.current_name()} \n")
            all_frames = Frame.objects.filter(block = block)
            filterset = all_frames.values_list('filter', flat = True).distinct()
            lines.append(block.make_obsblock_link() + "\n")
            for obs_filter in filterset:
                fwhms = []
                neoxreds = 0
                raw = 0
                frame_count = 0
                good_zp = 0
                frames = all_frames.filter(filter=obs_filter)
                for frame in frames:
                    frame_count +=1
                    fwhms.append(frame.fwhm)
                    if frame.frametype == 91:
                        raw +=1
                    if frame.frametype == 92:
                        neoxreds +=1
                    if frame.frametype == 92 and frame.zeropoint > 0:
                        good_zp +=1
                mean_fwhm = mean(fwhms)
                lines.append(f"{block.superblock.tracking_number} {block.request_number} {block.site} {block.superblock.get_obsdetails()}, {obs_filter} {raw}  {good_zp}/{neoxreds} fwhm: {mean_fwhm:.3f} {block.block_start} --> {block.block_end}\n")
    return lines