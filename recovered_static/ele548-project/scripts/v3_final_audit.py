"""Fail-closed old-state preservation, actual output and frozen-producer audit."""
import json,subprocess,platform
from v3_common import *
names=['A1_COST','A2_FACTORIAL','A3_CPU','A3_FUNCTIONAL_V2','B_FUNCTIONAL','B_SOURCE_REPLAY','B_WINDOWS','B_DIRECTED','B_ADVERSARIAL','B_CPU_GATE','C_CPU_GATE','CPU_DESIGN','B_WHOLE_DESIGN','B_RESOURCE','CPU_EVALUATION','B_WHOLE_EVALUATION','B_SPARSE']
checks=[];execution=[];failures=[]
for n in names:
 p=OUT/'reports'/f'{n}.json';x=json.loads(p.read_text());assert x['status'] in ['PASS','FAIL_RETAINED'],(n,x['status'])
 assert x['completed']==x['planned']==len(x['tasks']),(n,'incomplete')
 for t in x['tasks']:
  if t['status']!='PASS':failures.append(dict(report=n,label=t.get('label',t.get('output')),status=t['status'],failure=t.get('failure')));continue
  if t.get('hashes') and t.get('cycles'):
   for f,h in t['hashes'].items():assert sha(ROOT/t['output']/f)==h,(n,t['output'],f)
   execution.append(dict(report=n,output=t['output'],producer=t['producer_binary_sha256'],cycles=t['cycles'],instructions=t['instructions'],oracle=t.get('oracle',False)))
  elif t.get('CSV_sha256'):assert sha(ROOT/(t['output']+'.csv'))==t['CSV_sha256']
 checks.append(dict(report=n,status=x['status'],actual_completed=x['completed'],sha256=sha(p)))
snapshot=json.loads((OUT/'BASELINE_SNAPSHOT.json').read_text())
for p,h in snapshot['old_files'].items():assert sha(ROOT/p)==h,('OLD_WORK_CHANGED',p)
for label in ['A','B','C']:
 lock=json.loads((OUT/f'configs/source_{label}.lock.json').read_text())
 for p,h in lock['sources'].items():assert sha(ROOT/p)==h,('SOURCE_CHANGED',label,p)
 for p,h in lock.get('transport_hashes',{}).items():assert sha(ROOT/p)==h,('TRANSPORT_CHANGED',label,p)
for dir in ['gem5-costaware-v3','gem5-costaware-v3-b','gem5-costaware-v3-c']:
 target=ROOT/'third_party'/dir
 assert subprocess.check_output(['git','-C',target,'rev-parse','HEAD'],text=True).strip()=='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
 for f in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:assert sha(target/'src/cpu/pred'/f)==sha(ROOT/'third_party/gem5/src/cpu/pred'/f)
freeze=json.loads((OUT/'configs/CANDIDATE_SPEC.lock.json').read_text());producer=json.loads((OUT/'configs/FINAL_PRODUCER.lock.json').read_text());assert freeze['producer']==producer
assert sha(ROOT/producer['binary'])==producer['binary_sha256'] and sha(ROOT/producer['config'])==producer['config_sha256']
for n in ['CPU_EVALUATION','B_WHOLE_EVALUATION','B_SPARSE']:
 x=json.loads((OUT/f'reports/{n}.json').read_text())
 for t in x['tasks']:
  assert t['producer_binary_sha256']==producer['binary_sha256'] and t['config_sha256']==producer['config_sha256']
  assert not t.get('oracle'),('ORACLE_IN_EVALUATION',n,t['label'])
write(OUT/'reports/G7_AUDIT.json',dict(status='PASS',old_files_preserved=len(snapshot['old_files']),actual_reports=checks,actual_CPU_runs=len(execution),oracle_CPU_runs=sum(t['oracle'] for t in execution),retained_failures=failures,source_and_transport_hashes_verified=True,pinned_plain_TAGE_algorithm_verified=True,recorded_host_core_hours=used_cpu()/3600,checkpoint_core_hours=32))
write(OUT/'reports/software.lock.json',dict(status='GATES_AND_RAW_OUTPUTS_AUDITED',baseline_commit=snapshot['commit'],implementation_commit=subprocess.check_output(['git','rev-parse','719cc5aa'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),gem5_pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9',tag='v25.1.0.1',final_producer=producer,source_locks={n:sha(OUT/f'configs/source_{n}.lock.json') for n in ['A','B','C']},platform=platform.platform(),python=platform.python_version(),scope_sha256=sha(ROOT/'sources/protection_scope.lock.json'),inputs={n:sha(OUT/f'configs/{n}_inputs.lock.json') for n in ['design','evaluation']},old_outputs_modified=False,physical_tools_used=False,TCAD_used=False,metric_units='simulated cycles/instructions/IPC, actual GNU host CPU seconds, logical encoded cells; no measured PPA/FIT',audit_sha256=sha(OUT/'reports/G7_AUDIT.json')))
print('G7 PASS preserved',len(snapshot['old_files']),'old files;',len(execution),'actual CPU runs;',len(failures),'retained failures')
