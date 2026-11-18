"""Estimate routed block power from a specified private VCD interval."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from .implement import retime_history_sdc
from .synthesize import tcl_word


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--route', type=Path, required=True)
    p.add_argument('--vcd', type=Path, required=True)
    p.add_argument('--scope', required=True)
    p.add_argument('--start-ps', type=int, default=0)
    p.add_argument('--end-ps', type=int, required=True)
    p.add_argument('--clock-period-ps', type=int,
                   help='Use an explicitly rechecked period on a registered checkpoint')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cpus', type=int, default=1)
    a = p.parse_args()
    try:
        route = a.route.resolve(strict=True)
        checkpoint = (route/'outputs/routed.inn').resolve(strict=True)
        parent = json.loads((route/'PRODUCER.json').read_text())
        vcd = a.vcd.resolve(strict=True)
        if (parent['status'] != 'FLOW_COMPLETE_CHECK_REPORTS' or not vcd.is_file()
                or not re.fullmatch(r'[a-zA-Z_0-9/]+', a.scope)
                or not 0 <= a.start_ps < a.end_ps or not 1 <= a.cpus <= 16):
            raise ValueError('completed route, VCD, valid scope/interval and 1..16 CPUs required')
        sdc = None
        if a.clock_period_ps is not None:
            if parent['scope'] != 'B1A_HISTORY_DATAPATH':
                raise ValueError('clock retiming requires a registered history checkpoint')
            sdc = retime_history_sdc((route/'inputs/mapped.sdc').read_text(),
                                     Decimal(a.clock_period_ps)/1000)
        values = dict(checkpoint=checkpoint, activity='activity.vcd', activity_scope=a.scope,
                      start_ps=a.start_ps, end_ps=a.end_ps, cpus=a.cpus,
                      constraint_file='activity.sdc' if sdc is not None else '')
        script = ''.join(f'set {key} {tcl_word(value)}\n' for key, value in values.items())
    except (KeyError, OSError, ValueError) as error:
        p.error(str(error))
    out = a.output.resolve()
    out.mkdir(parents=True)
    (out/'reports').mkdir()
    shutil.copy2(Path(__file__).with_name('innovus_power.tcl'), out/'flow.tcl')
    (out/'site.tcl').write_text(script)
    if sdc is not None:
        (out/'activity.sdc').write_text(sdc)
    shutil.copy2(vcd, out/'activity.vcd')
    with (out/'activity.vcd').open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    record = dict(route=str(route), block_scope=parent['scope'], vcd=str(vcd),
                  vcd_sha256=digest, activity_scope=a.scope, start_ps=a.start_ps,
                  end_ps=a.end_ps, clock_period_override_ps=a.clock_period_ps, status='RUNNING')
    (out/'PRODUCER.json').write_text(json.dumps(record, indent=2)+'\n')
    args = ['innovus','-stylus','-no_gui','-files','flow.tcl','-log','innovus.log']
    with (out/'console.log').open('x') as log:
        run = subprocess.run(['timeout','-k','10','1200','csh','-c','exec '+shlex.join(args)],
                             cwd=out,stdout=log,stderr=subprocess.STDOUT)
    report = out/'reports/power.rpt'
    valid = (run.returncode == 0 and report.is_file() and report.stat().st_size
             and 'PASS_TAGE_ACTIVITY_POWER_FLOW' in (out/'console.log').read_text(errors='replace'))
    record.update(status='FLOW_COMPLETE_CHECK_ACTIVITY' if valid else 'FAIL', returncode=run.returncode)
    (out/'PRODUCER.json').write_text(json.dumps(record, indent=2)+'\n')
    if not valid:
        p.exit(1, 'power flow failed; retained logs and producer record\n')


if __name__ == '__main__':
    main()
