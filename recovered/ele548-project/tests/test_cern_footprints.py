import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from parse_cern_clusters import parse
from run_cern_footprints import tile_mappings, translations


class FootprintContract(unittest.TestCase):
    def test_scope_bijections_and_source_shapes_are_never_clipped(self):
        scope = json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
        maps = tile_mappings(scope)
        self.assertEqual(set(maps['word_contiguous']), set(maps['word_interleaved']))
        checked, maximum = 0, 0
        for name in ['clust_p29MeV.txt', 'clust_p0.9MeV.txt', 'clust_Ar1050MeV.txt']:
            rows = parse((ROOT/'data/raw/cern'/name).read_text())
            self.assertEqual(rows[0]['cluster_id'], 0)
            self.assertEqual(rows[0]['suspected_origin_sentinel'], name != 'clust_p0.9MeV.txt')
            self.assertEqual(len(rows), {'clust_p29MeV.txt': 1165,
                                        'clust_p0.9MeV.txt': 7456,
                                        'clust_Ar1050MeV.txt': 638}[name])
            for row in rows:
                k = row['multiplicity_from_unique_coordinates']
                if k < 2:
                    continue
                anchors = translations(row['offsets_from_anchor'])
                self.assertTrue(anchors)
                for x, y in [anchors[0], anchors[-1]]:
                    cells = [(y+dy)*16+x+dx for dx, dy in row['offsets_from_anchor']]
                    self.assertEqual(len(set(cells)), k)
                    self.assertTrue(all(0 <= cell < 346 for cell in cells))
                    for mapping in ['word_contiguous', 'word_interleaved']:
                        self.assertEqual(len({maps[mapping][cell] for cell in cells}), k)
                checked += 1
                maximum = max(maximum, k)
        self.assertEqual(checked, 18+52+449)
        self.assertEqual(maximum, 12)

    def test_impossible_shape_rejected_rather_than_wrapped(self):
        self.assertEqual(translations([[0, 0], [16, 0]]), [])
        self.assertEqual(translations([[0, 0], [0, 22]]), [])


if __name__ == '__main__':
    unittest.main()
