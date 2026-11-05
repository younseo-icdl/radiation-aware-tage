import unittest
from simulation.analysis.paired import summarize


class PairedTests(unittest.TestCase):
    def rows(self):
        return [dict(program='example', candidate='P_ECC', owner=str(owner), cell=cell,
                     cycles=str(value), status='PASS')
                for owner, values in enumerate(((100, 120, 105, 110), (200, 250, 210, 230)))
                for cell, value in zip('ABCD', values)]

    def test_owner_pairing(self):
        result = summarize(self.rows(), bootstrap=1000)[0]
        self.assertEqual(result['net_B_minus_D_cycles'], 15)
        self.assertEqual(result['clean_C_minus_A_cycles'], 7.5)
        low, high = result['net_B_minus_D_95pct_paired_bootstrap_CI']
        self.assertTrue(10 <= low <= 15 <= high <= 20)

    def test_failure_is_visible(self):
        rows = self.rows()
        rows[-1]['status'] = 'OUTPUT_MISMATCH'
        rows[-1]['cycles'] = ''
        result = summarize(rows, bootstrap=100)[0]
        self.assertEqual(result['complete_pass_pairs'], 1)
        self.assertEqual(result['excluded_owners'], 1)
        self.assertEqual(result['failed_cells_by_status'], {'OUTPUT_MISMATCH': 1})
        self.assertIsNone(result['net_B_minus_D_95pct_paired_bootstrap_CI'])

    def test_duplicates_rejected(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            summarize(rows + [rows[0]], bootstrap=100)

    def test_conditions_stay_separate(self):
        source = [dict(row, condition='SOURCE') for row in self.rows()]
        whole = [dict(row, condition='WHOLE') for row in self.rows()]
        result = summarize(source + whole, bootstrap=100)
        self.assertEqual(len(result), 2)
        self.assertEqual({row['condition'] for row in result}, {'SOURCE', 'WHOLE'})


if __name__ == '__main__':
    unittest.main()
