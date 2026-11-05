import tempfile
import hashlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from radiation.cern import parse
from radiation.data import flying_audit, fetch_cern

CLUSTER = '''cluster 1 with xmin 10 xmax 11 ymin 20 ymax 20
xadd 10 yadd 20 01:02:03
0 10 20
1 11 20
NUMBER OF EVENTS = 2
'''


class DatasetTests(unittest.TestCase):
    def catalog(self, raw):
        return {'files': [{'name': 'example.txt', 'url': 'https://example.invalid/example.txt',
                           'md5': hashlib.md5(raw).hexdigest()}], 'default_subset': ['example.txt']}

    def test_cache_preserves_verified_source_when_parser_requires_review(self):
        raw = (CLUSTER + CLUSTER).encode()
        with tempfile.TemporaryDirectory() as directory:
            with patch('radiation.data.json.loads', return_value=self.catalog(raw)), \
                    patch('radiation.data.urllib.request.urlopen', return_value=io.BytesIO(raw)):
                result = list(fetch_cern(directory, require_clean=False))[0]
            self.assertTrue(result['provider_md5_verified'])
            self.assertEqual(result['parse_status'], 'REVIEW_REQUIRED')
            self.assertEqual((Path(directory)/'example.txt').read_bytes(), raw)
            with patch('radiation.data.json.loads', return_value=self.catalog(raw)), \
                    patch('radiation.data.urllib.request.urlopen') as network:
                with self.assertRaises(ValueError):
                    list(fetch_cern(directory))
                network.assert_not_called()
            self.assertEqual((Path(directory)/'example.txt').read_bytes(), raw)

    def test_cache_rejects_mismatched_existing_file_without_overwriting(self):
        raw = CLUSTER.encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'example.txt'
            path.write_bytes(b'existing bytes')
            with patch('radiation.data.json.loads', return_value=self.catalog(raw)), \
                    patch('radiation.data.urllib.request.urlopen') as network:
                with self.assertRaises(ValueError):
                    list(fetch_cern(directory, require_clean=False))
                network.assert_not_called()
            self.assertEqual(path.read_bytes(), b'existing bytes')

    def test_whole_cluster_grammar(self):
        row = parse(CLUSTER)[0]
        self.assertEqual(row['coordinates'], [[10, 20], [11, 20]])
        self.assertEqual(row['source_clock_label'], '01:02:03')
        self.assertEqual(row['coordinate_record_ids'], [0, 1])
        self.assertEqual(row['multiplicity_from_unique_coordinates'], 2)

    def test_rejects_partial_or_invalid_file(self):
        for text in (CLUSTER + 'cluster 2 with xmin 0 xmax 0 ymin 0 ymax 0',
                     CLUSTER.replace('= 2', '= 3'), CLUSTER + CLUSTER,
                     CLUSTER.replace('1 11 20', '1 12 20'),
                     CLUSTER.replace('01:02:03', '25:02:03')):
            with self.assertRaises(ValueError):
                parse(text)

    def test_duplicate_records_are_not_mcu(self):
        text = ('Lon (deg),Lat (deg),Alt (m),Timestamp (ms UTC Unix),Time,Position Source\n'
                '0,1,2,1000,1970-01-01 00:00:01,TLE\n'
                '0,1,2,1000,1970-01-01 00:00:01,TLE\n'
                '0,1,2,2000,1970-01-01 00:00:02,TLE\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.csv'
            path.write_text(text)
            result = flying_audit(path)
        self.assertEqual(result['raw_rows'], 3)
        self.assertEqual(result['distinct_complete_records'], 2)
        self.assertEqual(result['duplicate_extra_rows'], 1)
        self.assertEqual(result['distinct_timestamps'], 2)


if __name__ == '__main__':
    unittest.main()
