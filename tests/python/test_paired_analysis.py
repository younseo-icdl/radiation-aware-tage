import unittest
from simulation.analysis.runtime_pairs import paired_summary


def pair(owner, uf=100, mf=80, valid=True):
    return {'owner_id': owner, 'UF_status': 'PASS', 'MF_status': 'PASS',
            'UF_cycles': uf, 'MF_cycles': mf, 'pair_valid': valid}


class PairedTests(unittest.TestCase):
    def test_both_signs_remain_and_interval_is_reproducible(self):
        rows = [pair('a'), pair('b', mf=120)]
        first = paired_summary(rows, seed=548, replicates=1000)
        self.assertEqual(first, paired_summary(rows, seed=548, replicates=1000))
        self.assertEqual(first['mean_benefit_percent'], 0)
        self.assertEqual(first['positive_owners'], 1)
        self.assertEqual(first['negative_owners'], 1)
        self.assertLess(first['ci_lower_percent'], 0)
        self.assertGreater(first['ci_upper_percent'], 0)
        self.assertEqual(first['decision'], 'SUPERIORITY_NOT_ESTABLISHED')

    def test_failure_does_not_become_zero_runtime_or_all_owner_win(self):
        rows = [pair('a'), pair('b'), pair('failed', mf=0, valid=False)]
        result = paired_summary(rows, seed=548)
        self.assertEqual(result['valid_pairs'], 2)
        self.assertEqual(result['mean_benefit_percent'], 20)
        self.assertEqual(result['runtime_scope'], 'CONDITIONAL_ON_VALID_PAIRS')
        self.assertEqual(result['decision'], 'NO_ALL_OWNER_CLAIM_FAILURES_OR_NONCOMPARABLE_PAIRS')

    def test_duplicates_and_invalid_success_times_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate owner'):
            paired_summary([pair('a'), pair('a')], seed=548)
        with self.assertRaisesRegex(ValueError, 'positive completion'):
            paired_summary([pair('a', mf=0)], seed=548)

    def test_single_owner_does_not_supply_spurious_zero_width_interval(self):
        result = paired_summary([pair('a')], seed=548)
        self.assertEqual(result['decision'], 'INSUFFICIENT_VALID_OWNERS')
        self.assertIsNone(result['ci_lower_percent'])


if __name__ == '__main__':
    unittest.main()
