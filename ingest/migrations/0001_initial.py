# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Proposal'
        db.create_table('ingest_proposal', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('ingest', ['Proposal'])

        # Adding model 'Body'
        db.create_table('ingest_body', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('provisional_name', self.gf('django.db.models.fields.CharField')(max_length=15, null=True, blank=True)),
            ('provisional_packed', self.gf('django.db.models.fields.CharField')(max_length=7, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=15, null=True, blank=True)),
            ('origin', self.gf('django.db.models.fields.CharField')(default='M', max_length=1)),
            ('source_type', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('elements_type', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('fast_moving', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('urgency', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('epochofel', self.gf('django.db.models.fields.FloatField')()),
            ('orbinc', self.gf('django.db.models.fields.FloatField')()),
            ('longascnode', self.gf('django.db.models.fields.FloatField')()),
            ('argofperih', self.gf('django.db.models.fields.FloatField')()),
            ('eccentricity', self.gf('django.db.models.fields.FloatField')()),
            ('meandist', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('meananom', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('perihdist', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('epochofperih', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('ingest', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2015, 2, 28, 0, 0))),
        ))
        db.send_create_signal('ingest', ['Body'])

        # Adding model 'Block'
        db.create_table('ingest_block', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('telclass', self.gf('django.db.models.fields.CharField')(default='1m0', max_length=3)),
            ('site', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('body', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ingest.Body'])),
            ('proposal', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ingest.Proposal'])),
            ('block_start', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('block_end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('tracking_number', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
            ('when_observed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('ingest', ['Block'])

        # Adding model 'Record'
        db.create_table('ingest_record', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('instrument', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('filter', self.gf('django.db.models.fields.CharField')(max_length=15)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=31)),
            ('exp', self.gf('django.db.models.fields.FloatField')()),
            ('whentaken', self.gf('django.db.models.fields.DateTimeField')()),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ingest.Block'])),
        ))
        db.send_create_signal('ingest', ['Record'])


    def backwards(self, orm):
        # Deleting model 'Proposal'
        db.delete_table('ingest_proposal')

        # Deleting model 'Body'
        db.delete_table('ingest_body')

        # Deleting model 'Block'
        db.delete_table('ingest_block')

        # Deleting model 'Record'
        db.delete_table('ingest_record')


    models = {
        'ingest.block': {
            'Meta': {'object_name': 'Block'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'block_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'block_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ingest.Body']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'proposal': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ingest.Proposal']"}),
            'site': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'telclass': ('django.db.models.fields.CharField', [], {'default': "'1m0'", 'max_length': '3'}),
            'tracking_number': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'when_observed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'ingest.body': {
            'Meta': {'object_name': 'Body'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'argofperih': ('django.db.models.fields.FloatField', [], {}),
            'eccentricity': ('django.db.models.fields.FloatField', [], {}),
            'elements_type': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'epochofel': ('django.db.models.fields.FloatField', [], {}),
            'epochofperih': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'fast_moving': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ingest': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 2, 28, 0, 0)'}),
            'longascnode': ('django.db.models.fields.FloatField', [], {}),
            'meananom': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'meandist': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'orbinc': ('django.db.models.fields.FloatField', [], {}),
            'origin': ('django.db.models.fields.CharField', [], {'default': "'M'", 'max_length': '1'}),
            'perihdist': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'provisional_name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'provisional_packed': ('django.db.models.fields.CharField', [], {'max_length': '7', 'null': 'True', 'blank': 'True'}),
            'source_type': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'urgency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'ingest.proposal': {
            'Meta': {'object_name': 'Proposal'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'ingest.record': {
            'Meta': {'object_name': 'Record'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ingest.Block']"}),
            'exp': ('django.db.models.fields.FloatField', [], {}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '31'}),
            'filter': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instrument': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'site': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'whentaken': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['ingest']