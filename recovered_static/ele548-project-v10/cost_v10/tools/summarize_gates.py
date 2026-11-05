from pathlib import Path
import json,re,hashlib
from budget import BASE,check
cases=[('protection_rtl_A2','PROTECTION_ACTUAL23WORD_RTL_PASS rows=64155',64155),('history_state_rtl_A1','PASS_HISTORY_STATE_RTL_PINNED_R2_NORMAL_ARBITRARY_FORWARD_UNDO_HOLD_TWO_EDGE_CORRECT n=3804',3804),('gls_p0_A2','PROTECTION_MAPPED_FORCED_Q_BOUNDARY_PASS mode=0 rows=2583',2583),('gls_parity_frequent_A2','PROTECTION_MAPPED_FORCED_Q_BOUNDARY_PASS mode=1 rows=2675',2675),('gls_parity_incremental_A2','PROTECTION_MAPPED_FORCED_Q_BOUNDARY_PASS mode=2 rows=2675',2675),('gls_secded_A3','PROTECTION_MAPPED_FORCED_Q_BOUNDARY_PASS mode=3 rows=50779',50779),('gls_tmr_A3','PROTECTION_MAPPED_FORCED_Q_BOUNDARY_PASS mode=4 rows=5443',5443),('gls_history_A1','PASS_HISTORY_MAPPED_QBOUNDARY_PINNED_R2_NORMAL_ARBITRARY_FORWARD_UNDO_HOLD_TWO_EDGE_CORRECT n=3804',3804)]
cases.append(('overwrite_rtl_A2','PASS_HISTORY_OVERWRITE_PRIMITIVE_NOT_GEM5 n=3650 midcycle_fold_fixtures=400',3650))
out=[]
for name,marker,count in cases:
 p=BASE/'runtime'/name/'xrun.log';log=p.read_text();execution=json.loads((p.parent/'EXECUTION.json').read_text());assert execution['exit_code']==0 and marker in log and '*F,' not in log and '*E,' not in log
 out.append(dict(name=name,status='PASS_SCOPED_FUNCTION_GATE',rows=count,marker=marker,log_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),inputs=json.loads((p.parent/'INPUTS.json').read_text())))
d=dict(status='PASS_FUNCTION_AND_STORAGE_GATES_NOT_HARDWARE_QUALIFICATION',gates=out,protection_mapped_rows=sum(x[2] for x in cases if x[0].startswith('gls_') and x[0]!='gls_history_A1'),history_mapped_rows=3804,scope='Mappedfaultfixture clampsQthroughsamplingedge and releases; not internalUDPmemory mutation or silicon radiation physics',preserved_failed_runs=['protection_rtl_A1','genus_preserve_probe_A1','map_secded_A1','gls_p0_A1','overwrite_rtl_A1'],new_overwrite_primitive=dict(cpp_vectors=3650,rtl_vectors=3650,midcycle_fold_fixtures=400,status='PASS_PRIMITIVE_ONLY_NOT_GEM5_VARIANT',new_mapping_runs=0),resource=check())
(BASE/'reports/FINAL_GATES.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],d['protection_mapped_rows'])
