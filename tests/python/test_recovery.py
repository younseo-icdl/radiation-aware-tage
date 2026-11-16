import unittest
from simulation.analysis.recovery import RecoverySeries, timing_windows


class RecoveryTest(unittest.TestCase):
    def test_first_zero_recurrence_and_final_suffix_are_separate(self):
        series = RecoverySeries()
        for i, value in enumerate((1, 0, 0, 1, 0, 0)):
            series.observe(i, value)
        result = series.summary()
        self.assertEqual(result['first_zero'], 1)
        self.assertEqual(result['stable_to_horizon_start'], 4)
        self.assertEqual(result['last_nonzero'], 3)
        self.assertEqual(result['recurrence_count'], 1)
        self.assertEqual(result['recovery_status'], 'RECOVERED_WITHIN_OBSERVED_SUFFIX')

    def test_zero_only_at_final_observation_is_censored(self):
        series = RecoverySeries()
        series.observe(0, 1)
        series.observe(1, 0)
        self.assertEqual(series.summary()['recovery_status'], 'RIGHT_CENSORED')

    def test_alignment_gap_does_not_supply_an_exact_first_zero(self):
        series = RecoverySeries()
        for i, value in enumerate((1, None, 0, 0)):
            series.observe(i, value)
        result = series.summary()
        self.assertIsNone(result['first_zero'])
        self.assertEqual(result['first_zero_interval'], (0, 2))
        self.assertTrue(result['had_alignment_gap'])

    def test_unknown_is_not_not_affected(self):
        series = RecoverySeries()
        series.observe(0, None)
        series.observe(1, 0)
        self.assertEqual(series.summary()['recovery_status'], 'NA_ALIGNMENT')

    def test_cumulative_loss_can_remain_after_recovery(self):
        points = [dict(branch_id=i*512, clean_time=i*10, fault_time=i*10+7)
                  for i in range(7)]
        result = timing_windows(points)
        self.assertEqual(result['recovery_status'], 'RECOVERED_WITHIN_OBSERVED_SUFFIX')
        self.assertEqual(result['windows'][-1]['cumulative_time_gap'], 7)

    def test_late_observation_does_not_claim_no_damage_or_exact_first_zero(self):
        series = RecoverySeries(pre_fault_observed=False)
        series.observe(50, 0)
        series.observe(51, 0)
        self.assertEqual(series.summary()['recovery_status'], 'PRE_ROI_HISTORY_UNOBSERVED')
        self.assertIsNone(series.summary()['first_zero'])

    def test_clean_partial_tail_does_not_erase_three_observed_full_windows(self):
        points = [dict(branch_id=i*512, clean_time=i*10, fault_time=i*10+7)
                  for i in range(8)]
        result = timing_windows(points)
        self.assertTrue(result['trailing_incomplete'])
        self.assertEqual(result['recovery_status'], 'RECOVERED_WITHIN_OBSERVED_SUFFIX')

    def test_coarse_endpoints_cannot_rule_out_internal_cancellation(self):
        points = [dict(branch_id=i*1024, clean_time=i*10, fault_time=i*10)
                  for i in range(4)]
        self.assertEqual(timing_windows(points)['recovery_status'], 'INSUFFICIENT_OBSERVATION')

    def test_zero_net_window_with_subwindow_cancellation_is_not_recovery(self):
        points = [dict(branch_id=0, clean_time=0, fault_time=0),
                  dict(branch_id=512, clean_time=10, fault_time=15),
                  dict(branch_id=1024, clean_time=20, fault_time=20)]
        result = timing_windows(points, required_windows=1)
        self.assertTrue(result['windows'][0]['net_zero_within_window'])
        self.assertEqual(result['last_positive_excess_window'], 0)
        self.assertIsNone(result['last_nonzero_excess_window'])
        self.assertEqual(result['recovery_status'], 'RIGHT_CENSORED')

    def test_missing_or_partial_window_is_not_a_complete_suffix(self):
        points = [dict(branch_id=0, clean_time=0, fault_time=0),
                  dict(branch_id=2048, clean_time=20, fault_time=20)]
        self.assertFalse(timing_windows(points, required_windows=1)['windows'][0]['full_window'])
        self.assertEqual(timing_windows(points, required_windows=1)['recovery_status'],
                         'INSUFFICIENT_OBSERVATION')


if __name__ == '__main__':
    unittest.main()
