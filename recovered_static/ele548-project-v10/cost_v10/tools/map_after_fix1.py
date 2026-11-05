"""Sequential immutable product mapping after P0 proved the common flow."""
from pathlib import Path
import subprocess,json
from budget import check,ROOT,BASE
cases=[('secded','protection_words_secded',467),('tmr','protection_words_tmr',1038),('history_recurrent','history_state_recurrent',200),('history_direct','history_state_direct',0)]
results=[]
for short,top,bits in cases:
    check();name='map_'+short+('_A2' if short=='secded' else '_A1');print('START',name,flush=True)
    r=subprocess.run([str(ROOT/'.venv/bin/python'),str(BASE/'tools/run_job.py'),'--tool','genus','--name',name,'--top',top,'--tcl','cost_v10/flow/component_map_A2.tcl'],cwd=ROOT,capture_output=True,text=True)
    out=BASE/'runtime'/name;log=(out/'console.log').read_text()
    ok=r.returncode==0 and f'\nV10_COMPONENT_MAP_PASS {top} STATE {bits}\n' in log and 'Error   :' not in log and 'Encountered problems processing file' not in log
    row=dict(name=name,top=top,status='PASS_COMPONENT_EXPORT_NOT_TIMING_QUALIFICATION' if ok else 'FAIL_STAGE_ACCEPTANCE',expected_bits=bits)
    results.append(row);(BASE/'reports/MAPPING_EXECUTION_AFTER_FIX1.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(row),flush=True)
    if not ok:raise SystemExit(2)
