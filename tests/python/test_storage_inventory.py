from pathlib import Path
import tempfile
import unittest

from simulation.eda.storage_inventory import classify, liberty_cells, mapped_storage


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
