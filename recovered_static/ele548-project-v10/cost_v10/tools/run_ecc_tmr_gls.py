from pathlib import Path
import subprocess,json
from budget import ROOT,BASE,check
model='/export/PDK/TSMC/28nm/Library/tcbn28hpcplusbwp30p140_190a/TSMCHOME/digital/Front_End/verilog/tcbn28hpcplusbwp30p140_110a/tcbn28hpcplusbwp30p140.v'
rows=[]
for mode,mapname in [('secded','map_secded_A2'),('tmr','map_tmr_A1')]:
 check();p=BASE/'tests'/('protection_mapped_'+mode+'_A3');name='gls_'+mode+'_A3';m=json.loads((p/'GLS_INPUTS.json').read_text());print('START',name,flush=True)
 command=[str(ROOT/'.venv/bin/python'),str(BASE/'tools/run_job.py'),'--tool','xrun','--name',name,'--top','protection_mapped_tb','--sv',model,str(BASE/'runtime'/mapname/'mapped.v'),str(p/'protection_mapped_tb.sv'),'--plusarg','+VECTORS='+str(p/'vectors.txt')]
 r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
 log=(BASE/'runtime'/name/'xrun.log').read_text();ok=r.returncode==0 and m['acceptance_marker'] in log and '*F,' not in log and '*E,' not in log
 rows.append(dict(name=name,status='PASS_QBOUNDARY_CLAMP_EDGE_FUNCTION_NOT_INTERNAL_SEU' if ok else 'FAIL',rows=m['rows']));(BASE/'reports/ECC_TMR_GLS.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows[-1]),flush=True)
 if not ok:raise SystemExit(2)
