import io
import unittest

from simulation.analysis.history_activity import check_trace


class HistoryActivityTests(unittest.TestCase):
    def check(self, rows, period=None):
        return check_trace(io.StringIO(
            '# capture_end_tick=100\ntick,operation,owner,value,auxiliary\n'+rows), period)

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

    def test_same_tick_ordering_is_distinct_from_width_conflicts(self):
        result = self.check('1,append,1,0,1\n'
                            '2,undo,1,1,0\n2,append,1,0,1\n2,query,0,64,0\n'
                            '2,append,2,1,1\n2,query,0,68,0\n'
                            '3,query,0,72,0\n')
        self.assertEqual(result['status'], 'NO_OBSERVED_EDGE_CONFLICT')
        self.assertEqual(result['same_tick_ordering'], {
            'query_after_undo': 2, 'query_after_append': 2,
            'append_after_query': 1, 'query_after_query_then_append': 1,
        })

    def test_service_deadline_and_live_owner(self):
        with self.assertRaisesRegex(ValueError, 'occupied owners'):
            self.check('1,append,1,0,0\n2,service_start,0,4,4096\n')
        with self.assertRaisesRegex(ValueError, 'crossed'):
            self.check('1,service_start,0,4,4096\n4,query,0,64,0\n')

    def test_staged_capture_cancels_after_same_tick_undo(self):
        result = self.check('1,append,1,0,1\n2,query_request,10,64,0\n'
                            '3,hash_capture,10,64,0\n3,undo,1,1,0\n3,query_cancel,10,64,0\n'
                            '4,query_request,11,68,0\n5,hash_capture,11,68,0\n'
                            '6,row_response,11,68,0\n6,append,2,1,1\n', period=1)
        self.assertEqual(result['status'], 'NO_OBSERVED_EDGE_CONFLICT')
        staged = result['staged_queries']
        self.assertEqual(staged['canceled_after_same_tick_capture_and_mutation'], 1)
        self.assertEqual(staged['row_response_capture_latency_tick_counts'], {1: 1})
        self.assertIsNone(staged['pending_at_capture_end'])

    def test_staged_response_needs_live_token_and_append(self):
        pending = '1,query_request,10,64,0\n2,hash_capture,10,64,0\n'
        with self.assertRaisesRegex(ValueError, 'no matching request'):
            self.check(pending+'3,row_response,11,64,0\n')
        with self.assertRaisesRegex(ValueError, 'before a recorded response appended'):
            self.check(pending+'3,row_response,10,64,0\n')
        with self.assertRaisesRegex(ValueError, 'invalidated hash'):
            self.check(pending+'2,append,1,0,0\n3,row_response,10,64,0\n')
        with self.assertRaisesRegex(ValueError, 'registered edge'):
            self.check('5,query_request,10,64,0\n15,hash_capture,10,64,0\n', period=5)
