import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from radiation.fixed import source_events
from simulation.analysis.source_run import check_delivery, map_tmr_tape


class SourceRunTests(unittest.TestCase):
    def test_tmr_mapping_preserves_each_event_and_uses_one_replica(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root/'shared.events'
            rows = list(source_events(7, 10**11, rate=8000))
            shared.write_text('# time_unit=ticks environment=SOURCE seed=7 horizon=100000000000 '
                              'rng_namespace=2 rate=8000\n' +
                              ''.join(f'{tick} {";".join(marks)}\n' for tick, marks in rows))
            first, second = root/'one.events', root/'two.events'
            self.assertEqual(map_tmr_tape(shared, first, 8), map_tmr_tape(shared, second, 8))
            mapped = first.read_text().splitlines()[1:]
            self.assertEqual(len(mapped), len(rows))
            replicas = set()
            trace = ['event_ordinal,requested_tick,applied_tick,multiplicity,logical_site_ids,'
                     'raw_physical_indices,bit_values_before,bit_values_after']
            flips = 0
            for ordinal, (entry, (tick, marks)) in enumerate(zip(mapped, rows), 1):
                when, tokens = entry.split()
                self.assertEqual(int(when), tick)
                targets = tuple(tokens.split(';'))
                replica = 0 if targets[0].startswith('R') else int(targets[0][1])
                replicas.add(replica)
                expected = tuple(f'T{replica}:21:{mark[1:]}' for mark in marks) if replica else marks
                self.assertEqual(targets, expected)
                ages = [int(mark[1:]) for mark in marks]
                width = len(ages)
                fmt = lambda values: ';'.join(map(str, values))
                trace.append(f'{ordinal},{tick},{tick},{width},{fmt(replica*130+a for a in ages)},'
                             f'{fmt(ages) if not replica else ""},{fmt([0]*width)},{fmt([1]*width)}')
                flips += width
            self.assertEqual(replicas, {0, 1, 2})
            (root/'events.csv').write_text('\n'.join(trace)+'\n')
            (root/'logical_manifest.json').write_text(json.dumps({
                'words': [{'name': 'raw_path:0', 'width': 130, 'site_ids': list(range(130))}],
                'protection_sites': [
                    dict(structure='replica', word=21, replica=replica, bit=age, id=replica*130+age)
                    for replica in (1, 2) for age in range(130)],
            }))
            (root/'native.json').write_text(json.dumps(dict(
                tick=10**11, faults_frozen=True, scheduled_events=len(rows), applied_events=len(rows),
                applied_flips=flips, future_events_censored=0, declared_tape_horizon_tick=10**11,
                schedule_exhausted_before_exit=False)))
            self.assertEqual(check_delivery(root, shared, tmr_replica_seed=8)['applied_flips'], flips)
            with self.assertRaisesRegex(ValueError, 'SOURCE coordinate or order mismatch'):
                check_delivery(root, shared, tmr_replica_seed=9)

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
