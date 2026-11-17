import csv
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class TraceScreenTests(unittest.TestCase):
    def write_trace(self, path, gap=False):
        with gzip.open(path, 'wt', newline='') as f:
            keys = ['branch_id', 'conditional', 'pc', 'raw_limb0', 'raw_limb1',
                    'raw_limb2', 'provider_type', 'hit_bank', 'alternate_bank']
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for i in range(100):
                w.writerow(dict(zip(keys, [i+1+int(gap and i>50), 1, 4096,
                    i%2, 0, 0, 1 if i%2 else 3, 7, 2])))

    def test_content_reuse_and_provider_selection(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.write_trace(p/'trace.gz')
            x = subprocess.run([str(ROOT/'build/tage-trace-screen'), str(p/'trace.gz'),
                                str(p/'out')], capture_output=True, text=True)
            self.assertEqual(x.returncode, 0, x.stderr)
            with (p/'out/FOLD_CACHE_LOCALITY.csv').open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 14)
            self.assertTrue(all(int(x['hits'])==98 and int(x['misses'])==2 for x in rows))
            with (p/'out/PROVIDER_COUNTS.csv').open() as f:
                banks = {x['selected_bank']:int(x['committed_conditional_queries'])
                         for x in csv.DictReader(f)}
            self.assertEqual(banks['7'], 50)
            self.assertEqual(banks['2'], 50)
            self.assertEqual(json.loads((p/'out/SUMMARY.json').read_text())['CPU_speedup'], 'NOT_MEASURED')

    def test_identity_gap_is_rejected_without_partial_output(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.write_trace(p/'trace.gz', gap=True)
            x = subprocess.run([str(ROOT/'build/tage-trace-screen'), str(p/'trace.gz'),
                                str(p/'out')], capture_output=True, text=True)
            self.assertNotEqual(x.returncode, 0)
            self.assertIn('identity', x.stderr)
            self.assertFalse((p/'out').exists())


if __name__ == '__main__':
    unittest.main()
