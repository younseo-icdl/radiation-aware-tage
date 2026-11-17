import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from simulation.analysis.native import summarize


class NativeAnalysisTests(unittest.TestCase):
    def fixture(self, root, offset=lambda i: 20, mismatch=False):
        for name in ('clean', 'fault'):
            out = root/name
            out.mkdir()
            state = {'missing_lookup_mapping': 0, 'missing_retirement_mapping': 0,
                     'tick': 60000 + (20 if name == 'fault' else 0),
                     'retired_ops': 5000, 'retired_instructions': 5000, 'retired_pc_identity': 17}
            (out/'native.json').write_text(json.dumps(state))
            (out/'program.stdout').write_text('OK\n')
            with gzip.open(out/'committed.csv.gz', 'wt', newline='') as f:
                fields = ['branch_id', 'pc', 'target', 'taken', 'conditional', 'tage_prediction',
                          'lookup_tick', 'retire_tick', 'raw_limb0', 'raw_limb1', 'raw_limb2',
                          'path', 'nonspec_path', 'folds', 'indices', 'query_tags',
                          'provider_type', 'hit_bank', 'alternate_bank', 'fold_invariant_distance']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for i in range(1, 4201):
                    row = dict.fromkeys(fields, '0')
                    row.update(branch_id=i, pc=4, target=8, taken=1, conditional=1,
                               tage_prediction=1, lookup_tick=10*i,
                               retire_tick=10*i+(offset(i) if name == 'fault' else 0))
                    if mismatch and name == 'fault' and i == 250:
                        row['pc'] = 12
                    writer.writerow(row)
        (root/'fault/events.csv').write_text('applied_tick,multiplicity\n100,1\n')
        (root/'fault/raw_origins.csv').write_text(
            'tick,callback_ordinal,active_origin_bits,restorable_origin_bits\n'
            '100,1,1,1\n110,2,0,1\n120,3,0,0\n130,4,0,0\n')

    def test_constant_retained_gap_is_recovered_incremental_time(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            result = summarize(root/'clean', root/'fault')
            self.assertEqual(result['status'], 'COMPARABLE')
            self.assertEqual(result['timing']['recovery_status'], 'RECOVERED_WITHIN_OBSERVED_SUFFIX')
            self.assertEqual(result['tick_difference'], 20)
            self.assertEqual(result['origin_recovery']['live_raw_origin']['first_zero'], 3)

    def test_architectural_divergence_rejects_timing_pair(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root, mismatch=True)
            with self.assertRaisesRegex(ValueError, 'NA_ALIGNMENT'):
                summarize(root/'clean', root/'fault')

    def test_net_zero_does_not_hide_branch_time_cancellation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root, offset=lambda i: 2*(i % 2))
            result = summarize(root/'clean', root/'fault')
            self.assertEqual(result['timing']['recovery_status'], 'RIGHT_CENSORED')
            self.assertTrue(result['timing']['windows'][0]['net_zero_within_window'])

    def test_actual_bpu_flags_override_tage_proxy_and_include_unconditional(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            for name in ('clean', 'fault'):
                path = root/name/'committed.csv.gz'
                with gzip.open(path, 'rt') as f:
                    reader = csv.DictReader(f)
                    fields = reader.fieldnames + ['bpu_pred_taken', 'bpu_mispredicted', 'bpu_predicted_target']
                    rows = list(reader)
                for row in rows:
                    row.update(bpu_pred_taken='1', bpu_mispredicted='0', bpu_predicted_target='8')
                    if row['branch_id'] == '250':
                        row['conditional'] = '0'
                        if name == 'fault':
                            row.update(bpu_mispredicted='1', bpu_predicted_target='12')
                    if row['branch_id'] == '251' and name == 'fault':
                        row['tage_prediction'] = '0'  # Overridden by final BPU.
                    if row['branch_id'] == '252' and name == 'fault':
                        row.update(bpu_mispredicted='1', bpu_predicted_target='16')
                with gzip.open(path, 'wt', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
            result = summarize(root/'clean', root/'fault')
            self.assertEqual(result['counts']['harmful'], 1)
            final = result['final_BPU_prediction_recovery']
            self.assertEqual(final['counts']['harmful'], 2)
            self.assertEqual(final['series']['target_address_difference']['last_nonzero'], 252)

    def test_partial_bpu_schema_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            path = root/'fault/committed.csv.gz'
            with gzip.open(path, 'rt') as f:
                text = f.read()
            with gzip.open(path, 'wt') as f:
                f.write(text.replace('branch_id,', 'bpu_pred_taken,branch_id,', 1))
            with self.assertRaisesRegex(ValueError, 'malformed|partial'):
                summarize(root/'clean', root/'fault')


if __name__ == '__main__':
    unittest.main()
