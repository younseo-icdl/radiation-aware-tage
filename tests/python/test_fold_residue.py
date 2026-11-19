from collections import Counter
import unittest

from simulation.analysis.fold_residue import DIMENSIONS, duration_summary


def row(tick, op, bad, origins):
    return dict(tick=tick, operation=op, raw_appends=tick, active_raw_origin_labels=origins,
                **{name: int(name in bad) for name in DIMENSIONS[1:]})


class FoldResidueTests(unittest.TestCase):
    def test_same_tick_events_and_post_raw_residue(self):
        rows = [
            row(10, 'before_injection', set(), 0),
            row(10, 'after_injection', {'bank2'}, 1),
            row(10, 'append', {'bank2'}, 1),
            row(20, 'append', {'bank2'}, 0),
            row(40, 'publish', set(), 0),
        ]
        result = duration_summary(rows, 10, 60, Counter({10: 1}))
        bank = result['dimensions']['bank2']
        self.assertEqual(bank['mismatch_ticks'], 30)
        self.assertEqual(bank['mismatch_ticks_without_active_raw_origin_labels'], 20)
        self.assertEqual(bank['episodes'], [dict(start_tick=10, end_tick=40,
                                                left_censored=False, right_censored=False)])

    def test_terminal_and_missing_injection(self):
        rows = [row(10, 'append', set(), 0), row(20, 'restore', {'bank1'}, 0)]
        result = duration_summary(rows, 0, 60, Counter())
        self.assertEqual(result['observed_ticks'], 50)
        self.assertTrue(result['dimensions']['any_bank']['episodes'][0]['right_censored'])
        with self.assertRaisesRegex(ValueError, 'injection boundary'):
            duration_summary(rows, 0, 60, Counter({20: 1}))
