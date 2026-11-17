"""Implement a frozen B0 mapped hash with the private matched physical site."""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from .synthesize import ROOT, tcl_word


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
        if parent['status']!='PASS' or parent['scope']!='B0_COMBINATIONAL_HASH_ONLY':
            raise ValueError('a passed B0 synthesis producer is required')
        top=(a.synthesis/'TOP.txt').read_text().strip()
        values=physical_values(json.loads(a.site.read_text()),top,a.cpus)
        if not 0<a.timeout<float('inf'):
            raise ValueError('finite positive host timeout required')
    except (ValueError, OSError, KeyError) as error:
        p.error(str(error))
    out=a.output.resolve()
    for name in ['inputs','flow','reports','outputs']:
        (out/name).mkdir(parents=True,exist_ok=True)
    for name in ['mapped.v','mapped.sdc']:
        shutil.copy2(a.synthesis/name,out/'inputs'/name)
    for name in ['innovus_hash.tcl','mmmc_hash.tcl']:
        shutil.copy2(Path(__file__).with_name(name),out/'flow'/name)
    with (out/'site.tcl').open('x') as f:
        for key,value in values.items():
            f.write('set {} {}\n'.format(key, '[list '+value+']' if key=='lef_files' else tcl_word(value)))
    metadata={'scope':'B0_COMBINATIONAL_HASH_ONLY','source_synthesis':str(a.synthesis.resolve()),
              'source_parent':parent,'physical_site':str(a.site.resolve()),'constraints':values,
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
              'status':'RUNNING','signoff':'NOT_FOUNDRY_SIGNOFF','full_history_stage_qualified':False,
              'CTS':'NOT_APPLICABLE_VIRTUAL_CLOCK','activity_power':'NOT_MEASURED',
              'placement_seed':'TOOL_DEFAULT_NOT_YET_INDEPENDENT_SEED_STUDY'}
    (out/'PRODUCER.json').write_text(json.dumps(metadata,indent=2)+'\n')
    cmd=['innovus','-stylus','-no_gui','-files','flow/innovus_hash.tcl','-log','innovus.log']
    with (out/'console.log').open('x') as log:
        done=subprocess.run(['timeout','-k','10',str(a.timeout),'csh','-c','exec '+shlex.join(cmd)],
                            cwd=out,stdout=log,stderr=subprocess.STDOUT)
    text=(out/'console.log').read_text(errors='replace')
    valid=done.returncode==0 and 'PASS_B0_ROUTED_HASH_NOT_FULL_HISTORY_OR_SIGNOFF' in text
    valid=valid and all((out/f).is_file() and (out/f).stat().st_size for f in
                       ['outputs/postroute.v','reports/setup_path.rpt','reports/hold_path.rpt',
                        'reports/area.rpt','reports/internal_drc.rpt','reports/connectivity.rpt'])
    metadata.update(status='FLOW_COMPLETE_CHECK_REPORTS' if valid else 'FAIL',returncode=done.returncode)
    (out/'PRODUCER.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'output':str(out),'status':metadata['status']}))
    if not valid:
        p.exit(1,'implementation failed; all partial reports preserved\n')


if __name__=='__main__':
    main()
