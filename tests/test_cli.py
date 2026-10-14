"""Exercise documented commands against isolated, disposable databases."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = self.directory / 'monitor.sqlite'

    def run_cli(self, *args):
        result = subprocess.run(
            [sys.executable, '-m', 'eirewatch', '--db', str(self.db), *args],
            cwd=ROOT, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_documented_demo_replay_and_report(self):
        args = ('import', 'examples/sources.json', 'examples/incidents.json')
        self.assertEqual(self.run_cli(*args), 1)
        self.assertEqual(self.run_cli(*args), 0)
        snapshot_path = self.directory / 'snapshot.json'
        self.run_cli('export', str(snapshot_path))
        snapshot = json.loads(snapshot_path.read_text())
        self.assertEqual(len(snapshot['history']), 1)
        self.assertEqual(snapshot['incidents'][0]['review'], 'pending')
        self.assertFalse(snapshot['sources'][0]['config']['official'])
        report_path = self.directory / 'report.html'
        self.run_cli('export', str(report_path), '--html')
        self.assertIn('DEMO ONLY', report_path.read_text())
        self.assertIn('Not a live emergency service', report_path.read_text())
        self.assertEqual(self.run_cli('queue'), 0)

    def test_empty_production_config_does_not_activate_sources(self):
        self.assertEqual(self.run_cli('collect', 'examples/production-sources.json'), {})
        self.assertEqual(self.run_cli('health'), [])
        self.assertEqual(self.run_cli('queue'), 0)

    def test_review_inspection_and_required_reason(self):
        self.run_cli('import', 'examples/sources.json', 'examples/incidents.json')
        row = self.run_cli('review-queue')[0]
        self.assertEqual(self.run_cli('review-detail', row['id'], '1')['decisions'], [])
        self.run_cli('review', row['id'], '1', 'rejected', '--actor', 'test', '--reason', 'Synthetic test')
        self.assertEqual(self.run_cli('review-queue'), [])
        self.assertEqual(self.run_cli('review-detail', row['id'], '1')['decisions'][0]['reason'], 'Synthetic test')
