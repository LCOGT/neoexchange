# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Body.origin'
        db.alter_column('ingest_body', 'origin', self.gf('django.db.models.fields.CharField')(max_length=1, null=True))

        # Changing field 'Body.epochofel'
        db.alter_column('ingest_body', 'epochofel', self.gf('django.db.models.fields.DateTimeField')(null=True))

        # Changing field 'Body.epochofperih'
        db.alter_column('ingest_body', 'epochofperih', self.gf('django.db.models.fields.DateTimeField')(null=True))

        # Changing field 'Body.elements_type'
        db.alter_column('ingest_body', 'elements_type', self.gf('django.db.models.fields.CharField')(max_length=16, null=True))

        # Changing field 'Body.source_type'
        db.alter_column('ingest_body', 'source_type', self.gf('django.db.models.fields.CharField')(max_length=1, null=True))

        # Changing field 'Body.longascnode'
        db.alter_column('ingest_body', 'longascnode', self.gf('django.db.models.fields.FloatField')(null=True))

        # Changing field 'Body.orbinc'
        db.alter_column('ingest_body', 'orbinc', self.gf('django.db.models.fields.FloatField')(null=True))

        # Changing field 'Body.eccentricity'
        db.alter_column('ingest_body', 'eccentricity', self.gf('django.db.models.fields.FloatField')(null=True))

        # Changing field 'Body.argofperih'
        db.alter_column('ingest_body', 'argofperih', self.gf('django.db.models.fields.FloatField')(null=True))

    def backwards(self, orm):

        # Changing field 'Body.origin'
        db.alter_column('ingest_body', 'origin', self.gf('django.db.models.fields.CharField')(max_length=1))

        # User chose to not deal with backwards NULL issues for 'Body.epochofel'
        raise RuntimeError("Cannot reverse this migration. 'Body.epochofel' and its values cannot be restored.")

        # Changing field 'Body.epochofperih'
        db.alter_column('ingest_body', 'epochofperih', self.gf('django.db.models.fields.FloatField')(null=True))

        # User chose to not deal with backwards NULL issues for 'Body.elements_type'
        raise RuntimeError("Cannot reverse this migration. 'Body.elements_type' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Body.source_type'
        raise RuntimeError("Cannot reverse this migration. 'Body.source_type' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Body.longascnode'
        raise RuntimeError("Cannot reverse this migration. 'Body.longascnode' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Body.orbinc'
        raise RuntimeError("Cannot reverse this migration. 'Body.orbinc' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Body.eccentricity'
        raise RuntimeError("Cannot reverse this migration. 'Body.eccentricity' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Body.argofperih'
        raise RuntimeError("Cannot reverse this migration. 'Body.argofperih' and its values cannot be restored.")

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
            'argofperih': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'eccentricity': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'elements_type': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'epochofel': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'epochofperih': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'fast_moving': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ingest': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 3, 2, 0, 0)'}),
            'longascnode': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'meananom': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'meandist': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'orbinc': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'origin': ('django.db.models.fields.CharField', [], {'default': "'M'", 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'perihdist': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'provisional_name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'provisional_packed': ('django.db.models.fields.CharField', [], {'max_length': '7', 'null': 'True', 'blank': 'True'}),
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