import unittest
from scripts.parse_cern_clusters import parse
class FullGrammarTests(unittest.TestCase):
    def test_indexed_clock_preserved(self):
        r=parse("cluster 0 with xmin 1191 xmax 1191 ymin 1025 ymax 1025\nxadd 1191 yadd 1025 11:27:23\n216 1191 1025\nNUMBER OF EVENTS =1")[0]
        self.assertEqual(r["coordinates"],[[1191,1025]])
        self.assertEqual(r["coordinate_record_ids"],[216])
        self.assertEqual(r["source_clock_label"],"11:27:23")
        self.assertFalse(r["suspected_origin_sentinel"])
    def test_invalid_clock_rejected(self):
        with self.assertRaises(ValueError):
            parse("cluster 0 with xmin 1 xmax 1 ymin 2 ymax 2\nxadd 1 yadd 2 25:00:00\n1 1 2\nNUMBER OF EVENTS =1")
    def test_indexed_without_clock_rejected(self):
        with self.assertRaises(ValueError):
            parse("cluster 0 with xmin 1 xmax 1 ymin 2 ymax 2\nxadd 1 yadd 2\n1 1 2\nNUMBER OF EVENTS =1")
