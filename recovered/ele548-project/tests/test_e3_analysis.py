import json
import copy
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from summarize_e3_cpu import analyze, audit, estimate, wilson, comparable_config


class AnalysisContract(unittest.TestCase):
    def test_equal_program_weight_not_pooled_trial_weight(self):
        result = estimate([[0., 0.], [10., 10., 10., 10.]], np.random.default_rng(1), 2000)
        self.assertEqual(result['mean'], 5.)
        self.assertEqual(result['bootstrap95CI'], [5., 5.])
        self.assertIsNone(estimate([[1.]], np.random.default_rng(1), 2000)['bootstrap95CI'])

    def test_zero_failures_do_not_imply_zero_uncertainty(self):
        lo, hi = wilson(0, 20)
        self.assertAlmostEqual(lo, 0.)
        self.assertGreater(hi, .1)

    def test_self_consistent_metadata_cannot_override_original_cpu_stats(self):
        report = json.loads((ROOT/'reports/E3_CPU_PILOT.json').read_text())
        config = json.loads((ROOT/'configs/e3.cpu.lock.json').read_text())
        row = next(r for r in report['tasks'] if r['mode'] == 'single')
        row['cycles'] += 100
        row['IPC_from_counts'] = row['committed_instructions']/row['cycles']
        with self.assertRaisesRegex(AssertionError, 'original stats'):
            audit(report, config, 'pilot')

    def test_config_normalization_preserves_clock_and_cache_constraints(self):
        path = ROOT/'reports/gem5_o3_public/qsort_small/config.json'
        baseline = json.loads(path.read_text())
        changed = copy.deepcopy(baseline)
        changed['system']['clk_domain']['clock'] = [1000]
        self.assertNotEqual(comparable_config(baseline), comparable_config(changed))

    def test_seed_bootstrap_ignores_host_completion_order(self):
        # Synthetic statistical fixture, never used as a CPU execution result.
        report = json.loads((ROOT/'reports/E3_CPU_PILOT.json').read_text())
        config = json.loads((ROOT/'configs/e3.cpu.lock.json').read_text())
        baseline = json.loads((ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json').read_text())
        expanded = []
        for row in report['tasks']:
            if row['mode'] == 'zero':
                expanded.append(row)
                continue
            for trial in range(10):
                example = copy.deepcopy(row)
                example.update(trial=trial, seed=row['seed']+trial, label=row['label']+f'.statistical_fixture{trial}')
                example['cycles'] += 100*trial
                example['IPC_from_counts'] = example['committed_instructions']/example['cycles']
                expanded.append(example)
        report['tasks'] = expanded
        a = analyze(report, config, 'pilot', baseline)
        report['tasks'] = list(reversed(expanded))
        self.assertEqual(a, analyze(report, config, 'pilot', baseline))

    def test_completed_pilot_failure_kept_and_mutated_hash_rejected(self):
        report = json.loads((ROOT/'reports/E3_CPU_PILOT.json').read_text())
        config = json.loads((ROOT/'configs/e3.cpu.lock.json').read_text())
        baseline = json.loads((ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json').read_text())
        row = next(r for r in report['tasks'] if r['scheme'] == 'P_ECC' and r['mode'] == 'single')
        row['status'] = 'FAIL_EXECUTION'
        report['successful_runs'] -= 1
        failures = audit(report, config, 'pilot')
        self.assertEqual(len(failures), 1)
        group = next(g for g in analyze(report, config, 'pilot', baseline)
                     if g['mode'] == 'single' and g['scheme'] == 'P_ECC' and g['field'] == row['field'])
        self.assertEqual(group['attempted_runs'], 2)
        self.assertEqual(group['successful_runs'], 1)
        self.assertEqual(group['failures_by_program'][row['program']]['failed'], 1)
        self.assertIsNone(group['metrics']['cycles'])
        good = next(r for r in report['tasks'] if r['status'] == 'PASS')
        good['stats_sha256'] = '0'*64
        with self.assertRaises(AssertionError):
            audit(report, config, 'pilot')


if __name__ == '__main__':
    unittest.main()
