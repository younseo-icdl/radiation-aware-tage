import unittest
from radiation.fixed import (source_events, whole_events, schedule, per_bit_rate,
                             TICKS_PER_SECOND, arrival_ticks)


class FixedEnvironmentTests(unittest.TestCase):
    def test_source_rate_and_atomic_contiguous_marks(self):
        rows = list(source_events(548, TICKS_PER_SECOND))
        self.assertTrue(1800 < len(rows) < 2200)  # event rate, not flip rate
        doubles = 0
        for tick, sites in rows:
            self.assertEqual(tick % 500, 0)
            self.assertIn(len(sites), (1, 2))
            ages = [int(s[1:]) for s in sites]
            self.assertTrue(all(0 <= age < 130 for age in ages))
            if len(ages) == 2:
                doubles += 1
                self.assertEqual(ages[1], ages[0]+1)
        self.assertTrue(50 < doubles < 120)
        self.assertEqual(rows, list(source_events(548, TICKS_PER_SECOND)))

    def test_absent_sites_thin_the_same_union_tape(self):
        horizon = 100*TICKS_PER_SECOND
        union = {'base:0': '0', 'extra:0': '1', 'extra:1': '2'}
        rows, full = schedule('WHOLE_1e16', 548, horizon, union)
        thinned, info = schedule('WHOLE_1e16', 548, horizon,
                                  dict(union, **{'extra:0': None, 'extra:1': None}))
        self.assertEqual(thinned, [(t,s) for t,s in rows if s == ('0',)])
        self.assertEqual(info['emitted_union_events'], full['emitted_union_events'])
        self.assertEqual(info['applicable_events']+info['absent_site_events'], len(rows))
        self.assertAlmostEqual(per_bit_rate(10**16), 10*per_bit_rate(10**15))

    def test_equal_quantized_ticks_are_not_merged(self):
        ticks = list(arrival_ticks(548, 5000, TICKS_PER_SECOND, max_events=20000))
        self.assertGreater(len(ticks), len(set(ticks)))
        self.assertEqual(ticks, sorted(ticks))

    def test_source_rate_and_multiplicity_variants(self):
        seed = 202613180101
        horizon = 700069967000
        mixture = list(source_events(seed, horizon, rate=200))
        single = list(source_events(seed, horizon, rate=200, law='k1_only'))
        self.assertEqual(mixture[0], (2157197000, ('R118',)))
        self.assertEqual([tick for tick, _ in mixture], [tick for tick, _ in single])
        self.assertTrue(any(len(sites) == 2 for _, sites in mixture))
        self.assertTrue(all(len(sites) == 1 for _, sites in single))
        with self.assertRaises(ValueError):
            list(source_events(seed, horizon, law='unknown'))

    def test_longer_tape_keeps_exact_prefix_and_non_grid_horizon(self):
        short_horizon=TICKS_PER_SECOND+173
        short=list(source_events(548,short_horizon))
        longer=list(source_events(548,2*TICKS_PER_SECOND))
        self.assertTrue(all(t<=short_horizon for t,_ in short))
        self.assertEqual(short,[(t,s) for t,s in longer if t<=short_horizon])

    def test_bad_population_rate_and_bound_are_explicit(self):
        with self.assertRaises(ValueError):
            list(whole_events(548, 1000, ['same', 'same'], 10**15))
        with self.assertRaises(ValueError):
            per_bit_rate(10**14)
        with self.assertRaises(ValueError):
            list(source_events(548, TICKS_PER_SECOND, max_events=1))
        with self.assertRaises(ValueError):
            schedule('WHOLE_1e15', 548, 1000, {'a':'0','b':'0'})


if __name__ == '__main__':
    unittest.main()
