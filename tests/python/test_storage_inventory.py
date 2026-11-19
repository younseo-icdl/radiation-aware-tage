from pathlib import Path
import tempfile
import unittest

from simulation.eda.storage_inventory import classify, liberty_cells, mapped_storage
from simulation.eda.rtl_storage_catalog import bindings
from simulation.eda.rtl_storage_tape import audit


class StorageInventoryTests(unittest.TestCase):
    def test_multiline_hierarchy_and_two_instances_of_one_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lib = root / 'cells.lib'
            lib.write_text('library (example) {\n  cell (BUF) {\n  }\n'
                           '  cell (DFF) {\n    ff (IQ, IQN) {\n    }\n  }\n}\n')
            net = root / 'mapped.v'
            net.write_text(r'''
module inner();
  DFF \raw_mem_reg[0] (.D(data));
  BUF helper(.A(data));
endmodule
module top();
  inner
      one (.data(one_data));
  inner two (.data(two_data));
endmodule
''')
            registers, cells = mapped_storage(net, 'top', liberty_cells(lib))
            self.assertEqual(cells, {'DFF': 2, 'BUF': 2})
            self.assertEqual({row['instance'] for row in registers},
                             {'one.raw_mem_reg[0]', 'two.raw_mem_reg[0]'})
            self.assertEqual({row['category'] for row in registers}, {'raw_ring'})

    def test_variant_control_scopes(self):
        self.assertEqual(classify('history.lease.controller.remaining_reg[0]'), 'lease_timer')
        self.assertEqual(classify('refill.remaining_reg[0]'), 'refill_control')
        self.assertEqual(classify('history.ecc_raw.failed_reg'), 'secded_failed')

    def test_physical_ring_keys_share_storage_across_configurations(self):
        base = set(bindings('unprotected'))
        lease = set(bindings('lease'))
        tmr = set(bindings('tmr'))
        self.assertEqual(len(lease - base), 15)
        self.assertEqual(len(tmr - base), 692)
        self.assertEqual(lease & tmr, base)
        self.assertIn(('history.raw_mem', 1023, 'raw_ring'), base)

    def test_time_and_bit_readback_are_checked_for_each_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tape, log = root / 'tape', root / 'log'
            tape.write_text('5 history.head 1\n5 history.head 1\n')
            record = ('STORAGE_XOR 5 5 history.head 1 0 1\n'
                      'STORAGE_XOR 5 5 history.head 1 1 0\n'
                      'PASS_HISTORY_STORAGE_TAPE edges=1 applied=2 responses=0 stopped=0\n')
            log.write_text(record)
            self.assertEqual(audit(tape, log)['applied_events'], 2)
            log.write_text(record.replace('5 5 history.head 1 1 0', '5 6 history.head 1 1 0'))
            with self.assertRaisesRegex(ValueError, 'incorrect bit or time'):
                audit(tape, log)
