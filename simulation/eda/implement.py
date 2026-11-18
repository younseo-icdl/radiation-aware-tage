"""Implement a frozen mapped TAGE block using a private physical site."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from .synthesize import ROOT, tcl_word

REGISTERED_HISTORY_SCOPES = {'B1A_HISTORY_DATAPATH', 'STAGED_HISTORY_RETURNED_ROWS'}
ROW_REFERENCE_SCOPES = {
    'ONE_TAGGED_BANK_2R1W_REFERENCE', 'T0_PREDICTION_BITS_REFERENCE', 'SIMPLE_BTB_HIT_REFERENCE',
}


def retime_history_sdc(text, period_ns):
    return retime_clock_sdc(text, period_ns, 'history_clk')


def retime_clock_sdc(text, period_ns, clock):
    period = Decimal(str(period_ns))
    if not period.is_finite() or period <= 0:
        raise ValueError('route clock period must be finite and positive')
    pattern = (r'^(create_clock -name "' + re.escape(clock) + r'" -period )[\d.]+'
               r'( -waveform \{)0\.0 [\d.]+(\} \[get_ports clk_i\])$')
    text, count = re.subn(
        pattern,
        lambda m: m[1]+format(period, 'f')+m[2]+'0.0 '+format(period/2, 'f')+m[3],
        text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f'expected one generated {clock} clock and 50% waveform')
    return text


def die_utilization(bbox_text, area_text, top):
    x0, y0, x1, y1 = map(float, bbox_text.split())
    rows = [row.split() for row in area_text.splitlines() if row.split()[:1] == [top]]
    if len(rows) != 1 or 'Physical' not in area_text or x1 <= x0 or y1 <= y0:
        raise ValueError('missing die bounds or detailed top-level area')
    # Last columns are instance count, total area and eight area categories.
    total = float(rows[0][-9])
    physical_only = float(rows[0][-1])
    if not 0 <= physical_only < total:
        raise ValueError('invalid detailed area numbers')
    die_area = (x1-x0)*(y1-y0)
    return {'die_bbox_um': [x0, y0, x1, y1], 'die_area_um2': die_area,
            'placed_cell_area_um2': total-physical_only,
            'physical_only_area_um2': physical_only,
            'die_utilization_percent': 100*(total-physical_only)/die_area}


def physical_values(config, top, cpus):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', top) or not 1 <= cpus <= 16:
        raise ValueError('invalid top or CPU count')
    values = {'top': top, 'cpus': cpus}
    for key in ['slow_library_file','fast_library_file','rc_cap_table']:
        file = Path(config[key]).resolve()
        if not file.is_file():
            raise ValueError('missing physical site file: '+key)
        values[key] = str(file)
    lefs = [Path(f).resolve() for f in config['lef_files']]
    if len(lefs)<2 or not all(f.is_file() for f in lefs):
        raise ValueError('technology and cell LEF views required')
    values['lef_files'] = ' '.join(tcl_word(f) for f in lefs)
    for key, default in [('slow_temperature_c',125), ('fast_temperature_c',0),
                         ('core_width_um',120), ('core_height_um',120), ('core_margin_um',10)]:
        value = float(config.get(key,default))
        if not abs(value)<float('inf') or ('_um' in key and value<=0):
            raise ValueError('invalid '+key)
        values[key] = value
    return values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--synthesis',type=Path,required=True)
    p.add_argument('--site',type=Path,required=True)
    p.add_argument('--cpus',type=int,default=4)
    p.add_argument('--timeout',type=float,default=1800)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output exists; choose a fresh implementation producer')
    try:
        parent=json.loads((a.synthesis/'PRODUCER.json').read_text())
        if parent['status']!='PASS' or parent['scope'] not in (
            REGISTERED_HISTORY_SCOPES | ROW_REFERENCE_SCOPES | {'B0_COMBINATIONAL_HASH_ONLY'}
        ):
            raise ValueError('a passed TAGE synthesis producer is required')
        top=(a.synthesis/'TOP.txt').read_text().strip()
        config=json.loads(a.site.read_text())
        values=physical_values(config,top,a.cpus)
        values['registered'] = int(parent['scope'] in REGISTERED_HISTORY_SCOPES | ROW_REFERENCE_SCOPES)
        values['pipeline'] = int(parent['scope'] == 'STAGED_HISTORY_RETURNED_ROWS')
        values['row_reference'] = int(parent['scope'] in ROW_REFERENCE_SCOPES)
        route_period=config.get('route_clock_period_ns')
        if route_period is not None and (not values['registered']
                or not isinstance(route_period, (int, float)) or isinstance(route_period, bool)):
            raise ValueError('route_clock_period_ns is numeric and applies to registered blocks')
        constraints=(a.synthesis/'mapped.sdc').read_text()
        if route_period is not None:
            clock = 'row_clk' if values['row_reference'] else 'history_clk'
            constraints=retime_clock_sdc(constraints,route_period,clock)
        if not 0<a.timeout<float('inf'):
            raise ValueError('finite positive host timeout required')
    except (ValueError, OSError, KeyError) as error:
        p.error(str(error))
    out=a.output.resolve()
    for name in ['inputs','flow','reports','outputs']:
        (out/name).mkdir(parents=True,exist_ok=True)
    shutil.copy2(a.synthesis/'mapped.v',out/'inputs/mapped.v')
    (out/'inputs/mapped.sdc').write_text(constraints)
    for name in ['innovus_hash.tcl','mmmc_hash.tcl']:
        shutil.copy2(Path(__file__).with_name(name),out/'flow'/name)
    with (out/'site.tcl').open('x') as f:
        for key,value in values.items():
            f.write('set {} {}\n'.format(key, '[list '+value+']' if key=='lef_files' else tcl_word(value)))
    metadata={'scope':parent['scope'],'source_synthesis':str(a.synthesis.resolve()),
              'source_parent':parent,'physical_site':str(a.site.resolve()),'constraints':values,
              'route_clock_period_ns':route_period,
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
              'status':'RUNNING','signoff':'NOT_FOUNDRY_SIGNOFF','full_history_stage_qualified':False,
              'CTS':'REQUESTED' if values['registered'] else 'NOT_APPLICABLE_VIRTUAL_CLOCK',
              'activity_power':'NOT_MEASURED',
              'placement_seed':'TOOL_DEFAULT_NOT_YET_INDEPENDENT_SEED_STUDY'}
    (out/'PRODUCER.json').write_text(json.dumps(metadata,indent=2)+'\n')
    cmd=['innovus','-stylus','-no_gui','-files','flow/innovus_hash.tcl','-log','innovus.log']
    with (out/'console.log').open('x') as log:
        done=subprocess.run(['timeout','-k','10',str(a.timeout),'csh','-c','exec '+shlex.join(cmd)],
                            cwd=out,stdout=log,stderr=subprocess.STDOUT)
    text=(out/'console.log').read_text(errors='replace')
    marker = 'PASS_B1A_ROUTED_STATE' if values['registered'] else 'PASS_B0_ROUTED_HASH_NOT_FULL_HISTORY_OR_SIGNOFF'
    valid=done.returncode==0 and marker in text
    valid=valid and all((out/f).is_file() and (out/f).stat().st_size for f in
                       ['outputs/postroute.v','reports/setup_path.rpt','reports/hold_path.rpt',
                        'reports/area.rpt','reports/die_bbox_um.txt',
                        'reports/internal_drc.rpt','reports/connectivity.rpt'])
    if values['registered']:
        valid = valid and all((out/f).is_file() and (out/f).stat().st_size for f in
                              ['reports/clock_trees.rpt','reports/query_setup.rpt'])
        metadata['CTS'] = 'FLOW_COMPLETE_CHECK_REPORTS' if valid else 'CHECK_PARTIAL_REPORTS'
    if values['pipeline']:
        feedback = out/'reports/provider_to_state_setup.rpt'
        valid = valid and feedback.is_file() and feedback.stat().st_size > 0
    if valid:
        try:
            metadata.update(die_utilization((out/'reports/die_bbox_um.txt').read_text(),
                                            (out/'reports/area.rpt').read_text(), top))
        except ValueError as error:
            metadata['die_utilization_error'] = str(error)
            valid = False
    metadata.update(status='FLOW_COMPLETE_CHECK_REPORTS' if valid else 'FAIL',returncode=done.returncode)
    (out/'PRODUCER.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'output':str(out),'status':metadata['status']}))
    if not valid:
        p.exit(1,'implementation failed; all partial reports preserved\n')


if __name__=='__main__':
    main()
