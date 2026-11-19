"""Verify a history-block power measurement against its routed activity producer."""
from decimal import Decimal
import math
from pathlib import Path
import re

from simulation.analysis.physical_clock import read, sha256
from .implement import retime_history_sdc

POWERS = ('internal', 'switching', 'leakage', 'total')


def measured_components(report):
    if not re.search(r'(?m)^\*\s*Power Units\s*=\s*1\s*mW\s*$', report):
        raise ValueError('the power report does not specify mW')
    result = {}
    for name in POWERS:
        label = '' if name == 'total' else ' ' + name.title()
        matches = re.findall(fr'(?m)^Total{label} Power:\s+(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)', report)
        if len(matches) != 1:
            raise ValueError(f'expected exactly one {name} power measurement')
        value = float(matches[0])
        if not math.isfinite(value):
            raise ValueError(f'invalid {name} power measurement')
        result[name+'_mw'] = value
    if not math.isclose(sum(result[name+'_mw'] for name in POWERS[:-1]), result['total_mw'],
                        rel_tol=1e-5, abs_tol=1e-8):
        raise ValueError('total power differs from internal, switching and leakage components')
    return result


def verify_measurement(power_dir, route, period, start, end, activity_scope):
    producer = power_dir / 'PRODUCER.json'
    meta = read(producer)
    if (meta['status'] != 'FLOW_COMPLETE_CHECK_ACTIVITY'
            or meta['block_scope'] != 'STAGED_HISTORY_RETURNED_ROWS'
            or Path(meta['route']).resolve() != route.resolve()
            or (meta['clock_period_override_ps'],meta['start_ps'],meta['end_ps']) != (period,start,end)
            or not 0 <= start < end or meta['activity_scope'] != activity_scope):
        raise ValueError('power producer did not measure the specified routed checkpoint and window')
    constraints = retime_history_sdc((route / 'inputs/mapped.sdc').read_text(), Decimal(period)/1000)
    if (power_dir / 'activity.sdc').read_text() != constraints:
        raise ValueError('power analysis SDC does not match the qualified clock period')
    console = (power_dir / 'console.log').read_text()
    if 'PASS_TAGE_ACTIVITY_POWER_FLOW' not in console:
        raise ValueError('missing activity power completion marker')
    coverage = {}
    for name in ('Flop outputs', 'Total Nets'):
        matches = re.findall(fr'{name}\s*:\s*(\d+)/(\d+)\s*=\s*100%', console)
        if not matches or any(a != b or a == '0' for a, b in matches) or len(set(matches)) != 1:
            raise ValueError(f'{name}: incomplete or inconsistent activity annotation')
        coverage[name] = int(matches[0][0])
    power_report = power_dir / 'reports/power.rpt'
    text = power_report.read_text()
    units = re.search(r'Time Units\s*=\s*([\d.eE+-]+)\s+secs', text)
    window = re.search(r'Vcd Window used\(Start Time, Stop Time\):\s*\(([\d.]+),\s*([\d.]+)\)', text)
    if (units is None or window is None
            or tuple(Decimal(value)*Decimal(units[1])*10**12 for value in window.groups()) != (start,end)):
        raise ValueError('reported VCD window differs from the requested measurement interval')
    supply = re.search(r'Rail:\s+VDD\s+Voltage:\s+([\d.]+)', text)
    if ('Power View : slowview' not in text or supply is None or Decimal(supply[1]) != Decimal('0.9')):
        raise ValueError('power report does not use the matched slow view and 0.9 V supply')
    values = measured_components(text)
    return dict(components_mw=values, energy_uj=values['total_mw']*(end-start)/1e9,
                clock_period_ps=period, window_start_ps=start, window_end_ps=end,
                power_view='slowview', supply_v=0.9,
                annotation=coverage, activity_sha256=meta['vcd_sha256'],
                power_report_sha256=sha256(power_report), producer_sha256=sha256(producer))
