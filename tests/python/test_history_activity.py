import io
import unittest

from simulation.analysis.history_activity import check_trace


class HistoryActivityTests(unittest.TestCase):
    def check(self, rows):
        return check_trace(io.StringIO(
            '# capture_end_tick=100\ntick,operation,owner,value,auxiliary\n'+rows))

    def test_restore_correction_and_release(self):
        result = self.check('1,query,0,64,0\n1,append,1,0,1\n'
                            '2,undo,1,1,0\n2,append,1,1,1\n3,release,1,0,0\n'
                            '4,service_start,0,5,4096\n5,publish,0,0,0\n')
        self.assertEqual(result['status'], 'NO_OBSERVED_EDGE_CONFLICT')
        self.assertEqual(result['peak_per_tick']['owners'], 1)
        self.assertFalse(result['cpu_timing_qualified'])

    def test_undo_interleaving_requires_scheduling(self):
        result = self.check('1,append,1,0,0\n2,query,0,64,0\n2,undo,1,1,0\n2,release,1,0,0\n')
        self.assertEqual(result['status'], 'REQUIRES_SCHEDULING')
        self.assertEqual(result['first_conflict_tick']['undo_after_append_or_query'], 2)

    def test_service_deadline_and_live_owner(self):
        with self.assertRaisesRegex(ValueError, 'occupied owners'):
            self.check('1,append,1,0,0\n2,service_start,0,4,4096\n')
        with self.assertRaisesRegex(ValueError, 'crossed'):
            self.check('1,service_start,0,4,4096\n4,query,0,64,0\n')
