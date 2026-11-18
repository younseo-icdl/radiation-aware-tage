"""Map a TAGE block using private site constraints."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BLOCKS = {
    'hash': ('B0_COMBINATIONAL_HASH_ONLY', 'genus_hash.tcl',
             'PASS_B0_HASH_SYNTHESIS_NOT_FULL_HISTORY_PPA'),
    'state': ('B1A_HISTORY_DATAPATH', 'genus_state.tcl',
              'PASS_B1A_STATE_SYNTHESIS'),
    'provider': ('PROVIDER_SELECT_RETURNED_ROWS_ONLY', 'genus_hash.tcl',
                 'PASS_PROVIDER_SELECT_SYNTHESIS'),
    'row-store': ('ONE_TAGGED_BANK_2R1W_REFERENCE', 'genus_row_store.tcl',
                  'PASS_ROW_STORE_SYNTHESIS'),
}


def tcl_word(value):
    text = str(value)
    if any(c in text for c in '{}\\\n\r'):
        raise ValueError('site values containing Tcl braces, backslashes or newlines are unsupported')
    return '{'+text+'}'


def site_values(config, mask, cpus):
    library = Path(config['library_file']).resolve()
    if not library.is_file():
        raise ValueError('Liberty file is missing')
    if not 0 <= mask < 128 or not 1 <= cpus <= 16:
        raise ValueError('mask must be 0..127 and CPU count 1..16')
    values = dict(library_file=str(library), direct_mask=mask, cpus=cpus)
    for key, default in [('clock_period_ns', .5), ('clock_uncertainty_ns', .025),
                         ('input_delay_ns', .05), ('output_delay_ns', .05),
                         ('input_transition_ns', .05), ('output_load_pf', .01)]:
        value = float(config.get(key, default))
        if not value > 0 or not value < float('inf'):
            raise ValueError('positive finite '+key+' required')
        values[key] = value
    return values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site', type=Path, required=True, help='private JSON with library_file and common constraints')
    p.add_argument('--direct-mask', type=lambda s:int(s, 0), required=True)
    p.add_argument('--block', choices=BLOCKS, default='hash')
    p.add_argument('--publish-mask', type=lambda s: int(s, 0), default=0)
    p.add_argument('--lease-period', type=int, default=0)
    p.add_argument('--lease-service-cycles', type=int, default=2)
    p.add_argument('--cpus', type=int, default=4)
    p.add_argument('--timeout', type=float, default=1200)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output exists; choose a fresh producer directory')
    try:
        values = site_values(json.loads(a.site.read_text()), a.direct_mask, a.cpus)
        if not 0 < a.timeout < float('inf'):
            raise ValueError('finite positive host timeout required')
        if not 0 <= a.publish_mask < 128 or (a.block != 'state' and a.publish_mask):
            raise ValueError('publication mask must be 0..127 and applies to the state block')
        if a.block == 'state':
            values['publish_mask'] = a.publish_mask
            values['lease_period'] = a.lease_period
            values['lease_service_cycles'] = a.lease_service_cycles
        if a.block in ('provider', 'row-store') and a.direct_mask:
            raise ValueError('provider and row store boundaries have no direct bank mask')
        if (not 0 <= a.lease_period <= 65535 or
                not 1 <= a.lease_service_cycles <= 65535 or
                (a.lease_period and (a.block != 'state' or not a.publish_mask))):
            raise ValueError('an enabled lease requires a state block and a nonzero publication mask')
    except (ValueError, OSError, KeyError) as error:
        p.error(str(error))
    out = a.output.resolve()
    (out/'inputs').mkdir(parents=True)
    (out/'flow').mkdir()
    (out/'reports').mkdir()
    scope, script, marker = BLOCKS[a.block]
    values['provider_select'] = int(a.block == 'provider')
    rtl_name = {'provider': 'tage_history_provider.sv',
                'row-store': 'tage_history_row_store.sv'}.get(a.block, 'tage_history_hash.sv')
    shutil.copy2(ROOT/'tage/rtl'/rtl_name, out/'inputs'/rtl_name)
    if a.block == 'state':
        shutil.copy2(ROOT/'tage/rtl/tage_history_state.sv', out/'inputs/tage_history_state.sv')
        shutil.copy2(ROOT/'tage/rtl/tage_history_lease.sv', out/'inputs/tage_history_lease.sv')
    shutil.copy2(Path(__file__).with_name(script), out/'flow'/script)
    (out/'site.tcl').write_text(''.join('set {} {}\n'.format(k, tcl_word(v)) for k,v in values.items()))
    metadata = {'scope': scope, 'full_history_stage_qualified': False,
                'constraints': values, 'private_site': str(a.site.resolve()),
                'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,text=True).strip(),
                'source_dirty': bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
                'status': 'RUNNING', 'physical_PPA': 'NOT_MEASURED_SYNTHESIS_ONLY'}
    (out/'PRODUCER.json').write_text(json.dumps(metadata, indent=2)+'\n')
    command = ['genus','-no_gui','-files','flow/'+script,'-log','genus.log']
    # csh supplies the user's configured Cadence environment; all paths are quoted.
    launch = ['timeout','-k','10',str(a.timeout), 'csh','-c','exec '+shlex.join(command)]
    with (out/'console.log').open('x') as log:
        result = subprocess.run(launch, cwd=out, stdout=log, stderr=subprocess.STDOUT)
    text = (out/'console.log').read_text(errors='replace')
    valid = result.returncode == 0 and marker in text
    artifacts = ['mapped.v','mapped.sdc','TOP.txt','reports/area.rpt','reports/timing.rpt']
    if a.block == 'state':
        artifacts.append('reports/query_timing.rpt')
    if a.block == 'row-store':
        artifacts.append('reports/read_address_timing.rpt')
    valid = valid and all((out/x).is_file() and (out/x).stat().st_size>0 for x in artifacts)
    metadata.update(status='PASS' if valid else 'FAIL', returncode=result.returncode)
    (out/'PRODUCER.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(out), 'status': metadata['status'], 'scope': metadata['scope']}))
    if not valid:
        p.exit(1, 'synthesis failed; retained private console and producer record\n')


if __name__ == '__main__':
    main()
