from pathlib import Path
import tempfile
import unittest
from simulation.eda.synthesize import site_values, tcl_word
from simulation.eda.implement import die_utilization, physical_values, retime_history_sdc
from simulation.eda.history_timing import worst_path


class EdaConfigTests(unittest.TestCase):
    def test_route_period_preserves_other_sdc_constraints(self):
        original = ('create_clock -name "history_clk" -period 0.5 -waveform {0.0 0.25} [get_ports clk_i]\n'
                    'set_clock_uncertainty 0.025 [get_clocks history_clk]\n')
        self.assertEqual(retime_history_sdc(original, 6.5),
                         original.replace('0.5 -waveform {0.0 0.25}', '6.5 -waveform {0.0 3.25}'))
        with self.assertRaises(ValueError):
            retime_history_sdc(original+original, 6.5)
        with self.assertRaises(ValueError):
            retime_history_sdc(original, float('inf'))

    def test_registered_sta_units_and_corner(self):
        report = ('Path 1: VIOLATED (-0.176 ns) Late Output Delay Assertion\n'
                  ' View: slowview\n Startpoint: (R) head_reg/CK\n'
                  ' Endpoint: (F) query_tag_o[0]\n')
        self.assertEqual(worst_path(report, 'slowview', 'Late')['slack_ps'], '-176.000')
        with self.assertRaises(ValueError):
            worst_path(report, 'fastview', 'Late')
        with self.assertRaises(ValueError):
            worst_path(report, 'slowview', 'Early')

    def test_utilization_uses_die_bounds_and_excludes_physical_only_area(self):
        report = ('Hinst Name Module Name Inst Count Total Area Buffer Inverter '
                  'Combinational Flop Latch Clock Gate Macro Physical\n'
                  'top  100  7500  0 0 7000 0 0 0 0 500\n')
        values = die_utilization('5 10 105 110', report, 'top')
        self.assertEqual(values['die_utilization_percent'], 70)
        self.assertEqual(values['die_area_um2'], 10000)

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

    def test_physical_site_checks_real_views_and_top_name(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for name in ['slow.lib','fast.lib','rc.tbl','tech.lef','cells.lef']:
                (p/name).write_text('fixture only')
            cfg={'slow_library_file':str(p/'slow.lib'),'fast_library_file':str(p/'fast.lib'),
                 'rc_cap_table':str(p/'rc.tbl'),'lef_files':[str(p/'tech.lef'),str(p/'cells.lef')]}
            values=physical_values(cfg,'hash_MASK5',4)
            self.assertEqual(values['core_width_um'],120)
            with self.assertRaises(ValueError):
                physical_values(cfg,'hash;bad',4)
            (p/'cells.lef').unlink()
            with self.assertRaises(ValueError):
                physical_values(cfg,'hash_MASK5',4)


if __name__ == '__main__':
    unittest.main()
