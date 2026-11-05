import unittest
from radiation.cern import parse
from radiation.empirical import cern_marks, flying_events, translations
from test_data import CLUSTER


class EmpiricalTests(unittest.TestCase):
    def test_whole_shapes(self):
        rows = parse(CLUSTER)
        self.assertTrue(translations(rows[0]['offsets_from_anchor']))
        for mapping in ('contiguous', 'interleaved', 'dispersed'):
            a, b = cern_marks(rows, 548, mapping), cern_marks(rows, 548, mapping)
            for _ in range(20):
                first = next(a)
                self.assertEqual(first, next(b))
                self.assertEqual(len(first), 2)
                self.assertEqual(len(set(first)), 2)

    def test_unmappable_shape_rejected(self):
        rows = parse(CLUSTER)
        rows[0]['offsets_from_anchor'] = [[0, 0], [99, 0]]
        with self.assertRaises(ValueError):
            next(cern_marks(rows, 548))

    def test_detection_policies_and_matched_marks(self):
        timestamps = [10, 10, 20, 100]
        collapsed = flying_events(timestamps, 548, 100, multiplicity='charm')
        preserved = flying_events(timestamps, 548, 100, duplicates='preserve', multiplicity='charm')
        self.assertEqual(len(collapsed), 3)
        self.assertEqual(len(preserved), 4)
        for row in collapsed:
            pair = next(r for r in preserved if r['source_group'] == row['source_group'] and r['record_in_group'] == 0)
            self.assertEqual(row['sites'], pair['sites'])
        for mode in ('observed', 'permuted', 'fixed-count-poisson'):
            rows = flying_events(timestamps, 548, 100, timing=mode)
            positions = [r['position'] for r in rows]
            self.assertEqual(sorted(positions), positions)
            self.assertTrue(all(1 <= p <= 100 for p in positions))
            self.assertTrue(all(len(r['sites']) == 1 for r in rows))


if __name__ == '__main__':
    unittest.main()
