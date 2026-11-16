import csv
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from simulation.analysis.recovery import summarize_replay

ROOT = Path(__file__).resolve().parents[2]


class CausalReplayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.trace = self.root/'branches.txt'
        self.trace.write_text(''.join(f'{4096+4*(i%13)} {8192+4*(i%7)} {(i//13+i%5)&1} {int(i%11!=0)}\n'
                                      for i in range(512)))

    def command(self, site='R0', trace_format='pc-target-taken-conditional'):
        return [str(ROOT/'build/tage-causal'), '--trace', str(self.trace),
                '--trace-format', trace_format, '--event-branch', '17', '--limit', '512',
                '--site', site, '--output', str(self.root/'result')]

    def test_output_contract_and_no_fabricated_cpu_time(self):
        subprocess.run(self.command(), check=True, capture_output=True)
        case = json.loads((self.root/'result/case.json').read_text())
        self.assertEqual(case['execution_status'], 'COMPLETE')
        self.assertEqual(case['all_state_sanity_status'], 'PASS')
        self.assertEqual(case['applied_flips'], 1)
        self.assertIsNone(case['own_cycle'])
        self.assertFalse(case['CPU_performance_result'])
        summaries = summarize_replay(self.root/'result')
        raw = next(r for r in summaries if r['state_component']=='raw_distance')
        self.assertIsNotNone(raw['first_zero_history_updates_since_fault'])
        with (self.root/'result/STATE_DISTANCE_TIMESERIES.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertTrue(all(None not in row for row in rows))
        unconditional = [r for r in rows if r['phase']=='PRE_LOOKUP' and r['conditional']=='0']
        self.assertTrue(unconditional)
        self.assertTrue(all(r['index_mismatch']=='NOT_APPLICABLE' for r in unconditional))

    def test_invalid_atomic_event_creates_no_partial_trial(self):
        for site in ('R0;R0', 'R4294967296'):
            result = subprocess.run(self.command(site), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.root/'result').exists())

    def test_trace_column_order_must_be_explicit(self):
        result = subprocess.run(self.command(trace_format='pc-taken-target-conditional'), capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root/'result').exists())


if __name__ == '__main__':
    unittest.main()
