import unittest

from simulation.analysis.lease_intervals import PERIODS, summarize


def fixture():
    for rate, seed, law in ((0, 'clean', 'clean_reference'), (2000, '100', 'source'), (2000, '101', 'source')):
        for period in PERIODS:
            yield dict(
                workload='qsort', fault_law_id=law, seed_id=seed, reference_rate_eps=rate,
                rebuild_interval_appends=period, clock_period_ticks=10, ticks_per_second=1000,
                input_sha256='input', golden_sha256='gold', shared_tape_sha256=seed, git_commit='source',
                timing_contract='matched', exposure_policy='common_raw130', roi_start_tick=0,
                roi_end_tick=300 if period and rate else 500, direction_wrong=20 if period and rate else 30,
                retired_instructions=100, status='timeout' if seed=='101' and period==4096 else 'correct')


class LeaseIntervalsTests(unittest.TestCase):
    def test_failure_remains_in_completion_denominator(self):
        row = next(row for row in summarize(fixture()) if row['interval_appends']==4096)
        self.assertEqual((row['total_pairs'], row['correct'], row['joint_correct_vs_disabled']), (2, 1, 1))
        self.assertAlmostEqual(row['paired_mean_delta_cycles'], -20)
        self.assertEqual(row['paired_mean_delta_mpki'], -100)

    def test_clean_and_faulted_clocks_must_match(self):
        rows = list(fixture())
        rows[0]['clock_period_ticks'] = 15
        with self.assertRaisesRegex(ValueError, 'changed timing'):
            summarize(rows)
