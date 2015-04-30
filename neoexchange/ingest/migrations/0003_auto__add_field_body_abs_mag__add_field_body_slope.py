# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Body.abs_mag'
        db.add_column('ingest_body', 'abs_mag',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Body.slope'
        db.add_column('ingest_body', 'slope',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Body.abs_mag'
        db.delete_column('ingest_body', 'abs_mag')

        # Deleting field 'Body.slope'
        db.delete_column('ingest_body', 'slope')


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
            'abs_mag': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'argofperih': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'eccentricity': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'elements_type': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'epochofel': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'epochofperih': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'fast_moving': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ingest': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 4, 5, 0, 0)'}),
            'longascnode': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'meananom': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'meandist': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'orbinc': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'origin': ('django.db.models.fields.CharField', [], {'default': "'M'", 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'perihdist': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'provisional_name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'provisional_packed': ('django.db.models.fields.CharField', [], {'max_length': '7', 'null': 'True', 'blank': 'True'}),
            'slope': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'source_type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
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