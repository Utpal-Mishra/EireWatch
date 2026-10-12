"""Synthetic-only source approval, freshness and migration regressions."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from eirewatch.core import Monitor
from eirewatch.collectors import collect
from eirewatch.registry import validate_config
from test_monitor import CONFIG, RECORD, NOW

POLICY = {**CONFIG, 'publication_max_age_hours': 2}


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.m = Monitor(':memory:')
        self.m.register(POLICY)
        self.m.subscribe('cork', ['Cork'], ['road'])

    def tearDown(self):
        self.m.db.close()

    def load(self, publication):
        return collect(self.m, POLICY, NOW, lambda c: (
            {'schema_version': 1, 'published': publication, 'incidents': [RECORD]}, 'synthetic-hash'))

    def test_successful_fetch_cannot_refresh_old_publication(self):
        self.assertEqual(self.load('2026-10-10T07:00:00Z'), 'publication_stale')
        h = self.m.health(NOW)[0]
        self.assertEqual(h['connection_status'], 'healthy')
        row = self.m.snapshot(NOW)['incidents'][0]
        self.m.review(row['id'], 1, 'approved', 'synthetic-reviewer', NOW)
        self.assertEqual(self.m.queue(NOW), 0)
        self.assertEqual(self.load('2026-10-10T09:00:00Z'), 'healthy')
        self.assertEqual(self.m.queue(NOW), 1)
        # Publication becomes stale while collection still passes its own threshold.
        self.assertEqual(self.m.inbox('cork', '2026-10-10T11:01:00Z'), [])

    def test_unknown_empty_feed_is_not_fresh_or_resolution(self):
        self.assertEqual(self.load(None), 'publication_unknown')
        self.m.ingest('test', [], NOW, published=NOW)
        self.assertEqual(self.m.health(NOW)[0]['publication_status'], 'fresh')
        self.assertEqual(self.m.snapshot(NOW)['incidents'][0]['data']['status'], 'active')
        self.m.ingest('test', [], NOW)
        self.assertEqual(self.m.health(NOW)[0]['publication_status'], 'unknown')

    def test_future_and_regressed_publication_are_atomic_failures(self):
        self.load(NOW)
        for publication in ('2026-10-10T10:00:01Z', '2026-10-10T09:00:00Z', 'invalid'):
            with self.assertRaises(ValueError):
                self.m.ingest('test', [{**RECORD, 'title': 'Must not commit'}], NOW, published=publication)
        snapshot = self.m.snapshot(NOW)
        self.assertEqual(len(snapshot['history']), 1)
        self.assertEqual(snapshot['sources'][0]['published'], NOW)

    def test_threshold_boundary_and_timezone(self):
        self.assertEqual(self.load('2026-10-10T09:00:00+01:00'), 'healthy')
        self.assertEqual(self.m.health('2026-10-10T10:00:01Z')[0]['status'], 'publication_stale')

    def test_registry_rejects_unverified_production_and_bad_types(self):
        production = {**POLICY, 'synthetic': False}
        with self.assertRaises(ValueError):
            validate_config(production)
        for change in ({'approved_for_ingestion': 'false'}, {'max_age_hours': float('nan')},
                       {'publication_max_age_hours': 0}, {'synthetic': 'yes'}):
            with self.assertRaises(ValueError):
                validate_config({**POLICY, **change})
        validate_config({**production, 'approved_for_ingestion': False})

    def test_documented_production_gate_and_legacy_fail_closed(self):
        approval = dict(publisher='Synthetic test publisher', endpoint_evidence_url='https://example.org/docs',
                        reuse_terms_url='https://example.org/terms', reuse_notes='Synthetic test only',
                        reviewed_at=NOW, reviewer='test', adapter_test_evidence='tests/test_sources.py',
                        endpoint_verified=True, reuse_verified=True, adapter_verified=True)
        config = {**POLICY, 'synthetic': False, 'approval': approval}
        validate_config(config)
        for field in ('endpoint_verified', 'reuse_verified', 'adapter_verified'):
            with self.assertRaises(ValueError):
                validate_config({**config, 'approval': {**approval, field: False}})
        self.load(NOW)
        row = self.m.snapshot(NOW)['incidents'][0]
        self.m.review(row['id'], 1, 'approved', 'test', NOW)
        legacy = {**CONFIG};legacy.pop('synthetic')
        self.m.db.execute('UPDATE sources SET config=?', (json.dumps(legacy),))
        self.m.db.commit()
        self.assertEqual(self.m.health(NOW)[0]['status'], 'configuration_invalid')
        self.assertEqual(self.m.queue(NOW), 0)

    def test_disabled_source_does_not_fetch(self):
        def forbidden(config):
            self.fail('Disabled sources must not fetch')
        self.assertEqual(collect(self.m, {**POLICY, 'approved_for_ingestion': False}, NOW, forbidden), 'disabled')

    def test_additive_legacy_database_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'legacy.sqlite'
            db = sqlite3.connect(path)
            db.execute('CREATE TABLE sources(id TEXT PRIMARY KEY, config TEXT NOT NULL, checked TEXT, succeeded TEXT, failures INTEGER NOT NULL DEFAULT 0, error TEXT, raw_hash TEXT)')
            db.execute('INSERT INTO sources(id,config) VALUES(?,?)', ('test', json.dumps(POLICY)))
            db.commit();db.close()
            for _ in range(2):
                monitor = Monitor(path)
                self.assertIsNone(monitor.health(NOW)[0]['published'])
                self.assertEqual(monitor.health(NOW)[0]['id'], 'test')
                monitor.db.close()
