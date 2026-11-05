import math
import unittest
import numpy as np
from radiation.models import events, history_site, HISTORY_WIDTHS
from radiation.rng import rng


class ModelTests(unittest.TestCase):
    def test_geometry(self):
        self.assertEqual(sum(HISTORY_WIDTHS), 346)
        sites = [history_site(i) for i in range(346)]
        self.assertEqual(len(set(sites)), 346)
        self.assertEqual(sites[-1], 'W22:15')
        with self.assertRaises(ValueError):
            history_site(346)

    def test_repeatability_and_namespaces(self):
        self.assertEqual(list(events(548, 1000, .2)), list(events(548, 1000, .2)))
        self.assertFalse(np.array_equal(rng(548, 'time').random(10), rng(548, 'location').random(10)))
        raw = list(events(548, 1000, .2, multiplicity='single'))
        marked = list(events(548, 1000, .2))
        self.assertEqual([t for t, _ in raw], [t for t, _ in marked])

    def test_single_and_zero(self):
        result = list(events(42, 100, scope='sstar', single=True, multiplicity='single'))
        self.assertEqual(len(result), 1)
        self.assertTrue(1 <= result[0][0] <= 100)
        self.assertEqual(list(events(42, 100, 0)), [])

    def test_poisson_and_marks(self):
        # Large enough deterministic sample to catch flips/events rate confusion.
        result = list(events(99, 100000, .1))
        expected = 10000
        self.assertLess(abs(len(result) - expected), 6 * math.sqrt(expected))
        doubles = sum(len(sites) == 2 for _, sites in result)
        p = 9 / 214
        self.assertLess(abs(doubles - len(result) * p), 6 * math.sqrt(len(result) * p * (1-p)))
        for time, sites in result:
            self.assertTrue(1 <= time <= 100000)
            self.assertEqual(len(sites), len(set(sites)))
            if len(sites) == 2:
                self.assertEqual(int(sites[1][1:]) - int(sites[0][1:]), 1)

    def test_invalid(self):
        for kwargs in ({'rate': -1}, {'rate': float('nan')}, {'rate': .1, 'single': True},
                       {'rate': .1, 'scope': 'sstar'}, {'rate': 1, 'max_events': 1}):
            with self.assertRaises(ValueError):
                list(events(5, 100, **kwargs))


if __name__ == '__main__':
    unittest.main()
