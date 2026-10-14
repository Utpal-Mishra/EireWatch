"""Synthetic trusted-local workflow tests; no authentication claim."""
from test_monitor import RECORD, NOW
import unittest


class ReviewTests(unittest.TestCase):
    def setUp(self):
        from eirewatch.core import Monitor
        from test_monitor import CONFIG
        self.m = Monitor(':memory:')
        self.addCleanup(self.m.db.close)
        self.m.register(CONFIG)
        self.m.ingest('test', [RECORD], NOW)
        self.id = self.m.review_queue()[0]['id']

    def test_inspection_and_decision_history(self):
        self.assertEqual(self.m.review_detail(self.id, 1)['decisions'], [])
        self.m.review(self.id, 1, 'approved', 'operator', NOW, reason='Source checked')
        self.m.review(self.id, 1, 'rejected', 'operator', NOW, reason='Correction needed')
        decisions = self.m.review_detail(self.id, 1)['decisions']
        self.assertEqual([r['decision'] for r in decisions], ['approved', 'rejected'])
        self.assertEqual(decisions[0]['reason'], 'Source checked')
        self.assertEqual(self.m.review_queue(), [])

    def test_blank_reason_and_actor_do_not_mutate(self):
        for actor, reason in [('operator', ' '), (' ', 'Checked')]:
            with self.assertRaises(ValueError):
                self.m.review(self.id, 1, 'approved', actor, NOW, reason=reason)
        self.assertEqual(len(self.m.review_queue()), 1)
        self.assertEqual(self.m.review_detail(self.id, 1)['decisions'], [])

    def test_stale_inspection_and_decision_are_rejected(self):
        self.m.ingest('test', [{**RECORD, 'updated': NOW, 'instruction': 'Changed'}], NOW)
        with self.assertRaises(ValueError):
            self.m.review_detail(self.id, 1)
        with self.assertRaises(ValueError):
            self.m.review(self.id, 1, 'approved', 'operator', NOW, reason='Checked')
        self.assertEqual(self.m.review_queue()[0]['revision'], 2)

    def pair(self):
        self.m.ingest('test', [{**RECORD, 'id': 'two'}], NOW)
        candidate = self.m.duplicate_candidates()[0]
        return candidate['first_incident'], candidate['second_incident']

    def test_duplicate_disposition_never_merges_or_approves(self):
        first, second = self.pair()
        self.m.review_duplicate(first, second, (1, 1), 'duplicate', 'operator', 'Same notice', NOW)
        self.assertEqual(len(self.m.review_queue()), 2)
        self.assertEqual(self.m.duplicate_candidates('duplicate')[0]['state'], 'duplicate')
        self.assertEqual(self.m.queue(NOW), 0)

    def test_candidate_revision_change_reopens_review(self):
        first, second = self.pair()
        self.m.review_duplicate(first, second, (1, 1), 'distinct', 'operator', 'Separate events', NOW)
        self.m.ingest('test', [{**RECORD, 'updated': NOW, 'instruction': 'Changed'}], NOW)
        self.assertEqual(len(self.m.duplicate_candidates()), 1)
        with self.assertRaises(ValueError):
            self.m.review_duplicate(first, second, (1, 1), 'duplicate', 'operator', 'Checked', NOW)

    def test_unknown_pair_and_invalid_decision(self):
        for decision in ('duplicate', 'merge'):
            with self.assertRaises(ValueError):
                self.m.review_duplicate('missing', 'other', (1, 1), decision, 'operator', 'Checked', NOW)
