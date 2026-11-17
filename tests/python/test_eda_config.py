from pathlib import Path
import tempfile
import unittest
from simulation.eda.synthesize import site_values, tcl_word


class EdaConfigTests(unittest.TestCase):
    def test_private_site_validation_and_safe_word(self):
        with tempfile.TemporaryDirectory() as d:
            lib=Path(d)/'example model.lib';lib.write_text('test fixture only')
            values=site_values({'library_file':str(lib)},5,4)
            self.assertEqual(values['direct_mask'],5)
            self.assertEqual(tcl_word(lib),'{'+str(lib)+'}')
            with self.assertRaises(ValueError):
                site_values({'library_file':str(lib),'clock_period_ns':float('nan')},5,4)
            with self.assertRaises(ValueError):
                site_values({'library_file':str(lib)},128,4)
            with self.assertRaises(ValueError):
                tcl_word('bad}\nexec command')


if __name__ == '__main__':
    unittest.main()
