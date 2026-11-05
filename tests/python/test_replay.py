import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from radiation.models import HISTORY_WIDTHS

ROOT = Path(__file__).resolve().parents[2]
SIMULATOR = ROOT / 'build/tage-sim'


class ReplayTests(unittest.TestCase):
    def test_exported_geometry(self):
        result = subprocess.check_output([str(SIMULATOR), '--list-state'], universal_newlines=True)
        row = json.loads(result)
        self.assertEqual(tuple(w['width'] for w in row['selected_history_words']), HISTORY_WIDTHS)
        self.assertEqual(row['base_exposed_bits'], 65370)

    def run_model(self, *args):
        return subprocess.run([str(SIMULATOR), '--demo', '1000'] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)

    def test_clean_methods(self):
        values = []
        for scheme in ('P0', 'P_ED', 'P_ECC', 'P_TMR'):
            result = self.run_model('--scheme', scheme)
            self.assertEqual(result.returncode, 0, result.stderr)
            row = json.loads(result.stdout)
            values.append(row['mispredictions'])
            self.assertEqual(row['detected'], 0)
            self.assertEqual(row['workload'], 'synthetic')
        self.assertEqual(len(set(values)), 1)

    def test_inject_and_censor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'schedule.txt'
            path.write_text('# time_unit=branches\n100 R9\n2000 W0:0\n')
            result = self.run_model('--scheme', 'P_ECC', '--schedule', str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads(result.stdout)
        self.assertEqual(row['applied_events'], 1)
        self.assertEqual(row['future_events_censored'], 1)
        self.assertEqual(row['corrected'], 1)

    def test_bad_schedule_rejected_before_replay(self):
        for content in ('1 R0\n2 R1;R1\n', '1 R130\n', '1 W23:0\n',
                        '# time_unit=cycles\n500 R0\n', '# time_unit=ticks\n500 R0\n', '1 R1;\n'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'schedule.txt'
                path.write_text(content)
                result = self.run_model('--schedule', str(path))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
