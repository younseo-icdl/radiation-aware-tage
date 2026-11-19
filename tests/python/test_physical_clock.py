from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from simulation.analysis.physical_clock import PATHS, arm_evidence, qualified_clock
from simulation.eda.history_timing import retime_history_sdc, row_arrival_constraints, worst_path
from simulation.eda.synthesize import tcl_word


class PhysicalClockTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def test_reject_missing_methods(self):
        (self.root / 'SELECTED_ROUTES.json').write_text('{"paths":{}}')
        (self.root / 'COMMON_CLOCK.json').write_text(json.dumps(dict(
            period_ps=14900, row_arrival_ps=6641, target_arrival_ps=9582,
            clock_mhz=1e6/14900, tested_periods_ps=[14900], timing={})))
        with self.assertRaisesRegex(ValueError, 'no complete matched'):
            qualified_clock(self.root)

    def test_halt_route_does_not_qualify_refill_or_changed_sta(self):
        route, sta = (self.root / name for name in ('route', 'sta'))
        for parent in (route, sta):
            for child in ('reports', 'inputs', 'outputs'):
                (parent / child).mkdir(parents=True)
        check = route / 'outputs/routed.inn'
        check.mkdir()
        (route / 'outputs/postroute.v').write_text('module fixture; endmodule\n')
        complete = 'FLOW_COMPLETE_CHECK_REPORTS'
        constraints = dict(lease_period=0, secded=1, pipeline=1, direct_mask=0,
                           lease_service_cycles=2, publish_mask=0)
        (route / 'PRODUCER.json').write_text(json.dumps(dict(
            CTS=complete, status=complete, scope='STAGED_HISTORY_RETURNED_ROWS',
            die_utilization_percent=70, source_parent=dict(status='PASS', constraints=constraints))))
        rd = route / 'reports'
        (rd / 'internal_drc.rpt').write_text('No DRC violations were found\n')
        for name in ('connectivity', 'pg_connectivity'):
            (rd / f'{name}.rpt').write_text('Found no problems or warnings.\n')
        (sta / 'site.tcl').write_text(f'set checkpoint {tcl_word(check)}\n')
        (sta / 'reports/cppr.txt').write_text('both\n')
        base = 'create_clock -name "history_clk" -period 13.85 -waveform {0.0 6.925} [get_ports clk_i]\n'
        (route / 'inputs/mapped.sdc').write_text(base)
        (sta / 'inputs/recheck.sdc').write_text(
            retime_history_sdc(base, Decimal('14.9')) + row_arrival_constraints(6641, 9582))
        summary = dict(rechecked_period_ps=14900, cppr='both', late_row_arrival_override_ps=6641,
                       late_target_arrival_override_ps=9582)
        for key, (filename, view, analysis) in PATHS.items():
            text = f'Path 1: MET (5 ps) {analysis}\nView: {view}\nStartpoint: in\nEndpoint: q\n'
            (sta / 'reports' / filename).write_text(text)
            summary[key] = worst_path(text, view, analysis)
        (sta / 'MODE_TIMING.json').write_text(json.dumps(summary))
        args = route, sta, 14900, 6641, 9582
        self.assertEqual(arm_evidence('ecc-halt', *args)['die_utilization_percent'], 70)
        with self.assertRaisesRegex(ValueError, 'routed history mode'):
            arm_evidence('ecc-refill', *args)
        (sta / 'inputs/recheck.sdc').write_text(base)
        with self.assertRaisesRegex(ValueError, 'applied STA constraints'):
            arm_evidence('ecc-halt', *args)
