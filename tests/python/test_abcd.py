import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from simulation.analysis.abcd import analyze, read_csv


class ABCDTests(unittest.TestCase):
    def data(self):
        clean = [dict(program='p', policy=policy, cycles=str(cycles), status='PASS',
                      conditional_MPKI=str(mpki), all_branch_MPKI=str(mpki+1))
                 for policy, cycles, mpki in [('U', 100, 10), ('ECC', 105, 11)]]
        rows = [dict(program='p', scenario='SBU', owner=owner, policy=policy,
                     A='100', B=str(b), C=str(c), D=str(d), pair_valid='True',
                     status='PASS', conditional_MPKI=str(mpki), all_branch_MPKI=str(mpki+1))
                for owner, b, fault_mpki in [('1', 120, 15), ('2', 90, 9)]
                for policy, c, d, mpki in [('U', 100, b, fault_mpki), ('ECC', 105, 110, 12)]]
        return rows, clean

    def run_analysis(self, rows=None, clean=None, **kwargs):
        defaults, controls = self.data()
        return analyze(defaults if rows is None else rows, controls if clean is None else clean,
                       unprotected='U', contract=kwargs.get('contract', 'inline-stage-fit'), cohort='EVAL')

    def test_decomposition_retains_helpful_fault_and_losing_protection(self):
        result = self.run_analysis()
        ecc = next(row for row in result['summaries'] if row['candidate'] == 'ECC')
        self.assertEqual(ecc['metrics']['net_B_minus_D_cycles'], dict(n=2, mean=-5, min=-20, max=10))
        self.assertEqual(ecc['fault_B_minus_A_cycles_signs'], dict(positive=1, zero=0, negative=1))
        self.assertEqual(ecc['mpki']['conditional_MPKI']['fault_B_minus_A']['mean'], 2)
        for sample in result['samples']:
            m = sample['metrics']
            self.assertEqual(m['net_B_minus_D_cycles'], m['fault_B_minus_A_cycles']
                             - m['clean_C_minus_A_cycles'] - m['residual_D_minus_C_cycles'])

    def test_failure_retains_raw_and_is_not_zero_damage(self):
        rows, clean = self.data()
        rows[-1].update(pair_valid='False', status='TIMEOUT', D='')
        result = self.run_analysis(rows, clean)
        ecc = next(row for row in result['summaries'] if row['candidate'] == 'ECC')
        self.assertEqual(ecc['valid_owners'], 1)
        self.assertEqual(ecc['failures'], {'TIMEOUT': 1})
        self.assertTrue(any(s['raw']['status'] == 'TIMEOUT' for s in result['samples']))

    def test_missing_mpki_and_future_events_stay_visible(self):
        rows, clean = self.data()
        for row in rows+clean:
            row.pop('conditional_MPKI')
            row.pop('all_branch_MPKI')
        rows[0]['future_censored'] = '7'
        result = self.run_analysis(rows, clean)
        self.assertTrue(all(s['mpki']['conditional_MPKI']['A']['n'] == 0 for s in result['summaries']))
        self.assertTrue(any(s['raw'].get('future_censored') == '7' for s in result['samples']))
        json.dumps(result, allow_nan=False)

        rows, clean = self.data()
        clean[1].pop('conditional_MPKI')
        result = self.run_analysis(rows, clean)
        ecc = next(s for s in result['summaries'] if s['candidate'] == 'ECC')
        self.assertEqual(ecc['mpki']['conditional_MPKI']['fault_B_minus_A']['n'], 2)
        self.assertEqual(ecc['mpki']['conditional_MPKI']['residual_D_minus_C']['n'], 0)

    def test_duplicate_or_mismatched_owner_and_controls_rejected(self):
        rows, clean = self.data()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.run_analysis(rows+[rows[0]], clean)
        rows[1]['B'] = '121'
        with self.assertRaisesRegex(ValueError, 'unprotected owner'):
            self.run_analysis(rows, clean)
        rows, clean = self.data()
        clean[1]['cycles'] = '106'
        with self.assertRaisesRegex(ValueError, 'clean control'):
            self.run_analysis(rows, clean)

    def test_conditions_and_contracts_are_explicit(self):
        rows, clean = self.data()
        additional = [dict(row, scenario='K2') for row in rows]
        self.assertEqual(len(self.run_analysis(rows+additional, clean)['summaries']), 4)
        with self.assertRaises(ValueError):
            self.run_analysis(contract='')
        rows[0]['contract'] = 'finite'
        with self.assertRaisesRegex(ValueError, 'mixed contract'):
            self.run_analysis(rows, clean)

    def test_b4_aliases_and_bom_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'pairs.csv'
            path.write_text('program,scenario,owner,method,A,B,C,D,valid_pair,failure\n'
                            'p,SBU,1,P0,100,95,100,95,True,\n'
                            'p,SBU,1,ECC,100,95,100,100,True,\n', encoding='utf-8-sig')
            self.assertEqual(read_csv(path)[0]['program'], 'p')
            output = subprocess.check_output([sys.executable, '-m', 'simulation.analysis.abcd',
                                             str(path), '--unprotected', 'P0',
                                             '--contract', 'finite', '--cohort', 'DEV'], text=True)
            result = json.loads(output)
            self.assertEqual(result['pair_rows'], 2)
            self.assertEqual(result['contract'], 'finite')


if __name__ == '__main__':
    unittest.main()
