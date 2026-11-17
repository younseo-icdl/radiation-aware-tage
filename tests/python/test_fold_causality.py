import csv
from pathlib import Path
import subprocess
import tempfile
import unittest


class ProductionFoldCausalityTests(unittest.TestCase):
    def test_production_sweep_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'fresh'
            command = ['build/tage-fold-causality', str(out)]
            result = subprocess.run(command, text=True, capture_output=True, check=True)
            self.assertIn('cases=10920', result.stdout)
            with (out/'SUMMARY.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 10920*7)
            selected = {r['arm']: r for r in rows if r['pattern'] == '0' and
                        r['bank'] == '3' and r['kind'] == '1' and r['age'] == '3'}
            self.assertEqual(selected['RAW_ONLY']['first_d_ref'], '12')
            self.assertEqual(selected['RAW_ONLY']['first_d_inv'], '0')
            self.assertEqual(selected['RAW_REPAIRED_BEFORE_TAP']['last_d_ref'], '-1')
            self.assertEqual(selected['RAW_REPAIRED_AFTER_TAP']['last_d_ref'], '260')
            self.assertEqual(selected['REBASE_OWN_AT0']['last_d_ref'], '11')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
