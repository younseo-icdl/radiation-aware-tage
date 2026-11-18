import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from simulation.analysis.source_run import check_delivery


class SourceRunTests(unittest.TestCase):
    def test_equal_tick_records_stay_separate_and_due_events_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tape = root/'input.events'
            tape.write_text('# time_unit=ticks environment=SOURCE seed=7 horizon=1500 rng_namespace=2\n'
                            '500 R128;R129\n500 R128\n1500 R0\n')
            events = [(500, ('R128', 'R129')), (500, ('R128',)), (1500, ('R0',))]
            manifest = {'words': [{'name': 'raw_path:0', 'width': 130, 'site_ids': list(range(130))}]}
            (root/'logical_manifest.json').write_text(json.dumps(manifest))
            state = dict(tick=500, faults_frozen=True, scheduled_events=3, applied_events=2,
                         applied_flips=3, future_events_censored=1, declared_tape_horizon_tick=1500,
                         schedule_exhausted_before_exit=False)
            (root/'native.json').write_text(json.dumps(state))
            trace = root/'events.csv'
            header = ('event_ordinal,requested_tick,applied_tick,multiplicity,logical_site_ids,'
                      'raw_physical_indices,bit_values_before,bit_values_after\n')
            first = '1,500,500,2,128;129,20;21,0;1,1;0\n'
            second = '2,500,500,1,128,20,1,0\n'
            with patch('simulation.analysis.source_run.source_events', return_value=events):
                trace.write_text(header+first+second)
                summary = check_delivery(root, tape)
                self.assertEqual((summary['applied_events'], summary['applied_flips']), (2, 3))
                trace.write_text(header+first)
                with self.assertRaisesRegex(ValueError, 'expected time prefix'):
                    check_delivery(root, tape)
                trace.write_text(header+first+second.replace(',20,1,0', ',20,1,1'))
                with self.assertRaisesRegex(ValueError, 'did not XOR'):
                    check_delivery(root, tape)
