import json
from pathlib import Path
import tempfile
import unittest

from simulation.analysis.lease_stalls import lease_counters


class LeaseStallsTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.run = Path(scratch.name)
        (self.run / 'config.ini').write_text('[system.cpu]\nnumThreads=1\nsmtNumFetchingThreads=1\n')
        self.native = dict(lease_drain_wait_calls=5, lease_service_wait_calls=3,
                           lease_frontend_wait_calls=8, lease_publications=1,
                           lease_completion_censored_at_exit=True, lease_busy_at_exit=True)
        self.ledger = (
            'event,tick,age,live_owners,ready_tick\n'
            'start,60,4096,0,80\n'
            'publish,80,0,0,80\n'
            'start,100,4096,0,120\n'
        )

    def counters(self):
        (self.run / 'native.json').write_text(json.dumps(self.native))
        (self.run / 'lease_events.csv').write_text(self.ledger)
        return lease_counters(self.run, 10, 110, 2, True)

    def test_censored_service_window_is_bounded_at_terminal_tick(self):
        data = self.counters()
        self.assertEqual(data['service_window_ticks'], 30)
        self.assertEqual(data['blocked_fetch_cycles'], 8)
        self.assertEqual(data['published_leases'], 1)

    def test_overlapping_counts_are_rejected(self):
        self.native['lease_frontend_wait_calls'] = 7
        with self.assertRaisesRegex(ValueError, 'exclusive'):
            self.counters()

    def test_incorrect_publication_timestamp_is_rejected(self):
        self.ledger = self.ledger.replace('publish,80,0', 'publish,90,0')
        with self.assertRaisesRegex(ValueError, 'sequence'):
            self.counters()
