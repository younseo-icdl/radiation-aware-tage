#!/usr/bin/env python3
"""Recheck actual gates, recover exact historical source bindings, retain failure."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def read(p):return json.loads(Path(p).read_text())
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--attempt",default="A2");a=ap.parse_args();resources=m.budget();cache={};bindings={};frozen=BASE/'runtime/frozen';frozen.mkdir(exist_ok=True)
 def digest(p):
  p=str(p)
  if p not in cache:cache[p]=m.sha(p)
  return cache[p]
 def walk(v):
  if isinstance(v,dict):
   if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str):
    p=Path(v['path']);want=v['sha256']
    if p.is_file() and digest(p)==want:bindings[(str(p),want)]=str(p)
    else:
     candidates=list(frozen.glob(want+'.*'))
     if not candidates and p.is_relative_to(BASE):
      rel=p.relative_to(BASE);old=m.V12/'finite_source_v12'/rel
      if old.is_file():
       content=old.read_bytes().replace(b'bp::v12',b'bp::v13')
       if hashlib.sha256(content).hexdigest()==want:
        saved=frozen/(want+p.suffix);saved.write_bytes(content);candidates=[saved]
     assert candidates and digest(candidates[0])==want,('MISSING_EXACT_HISTORICAL_BYTES',str(p),want)
     bindings[(str(p),want)]=str(candidates[0])
   for item in v.values():walk(item)
  elif isinstance(v,list):
   for item in v:walk(item)
 reports=list((BASE/'reports').glob('*.json'))
 for p in reports:walk(read(p))
 executions=[];failures=[]
 for p in sorted((BASE/'runtime').glob('*/EXECUTION.json')):
  v=read(p);walk(v);executions.append(m.ref(p))
  if v['exit_code']!=0:failures.append({'execution':m.ref(p),'exit_code':v['exit_code'],'stderr':Path(v['stderr']['path']).read_text()})
 assert len(failures)==1 and failures[0]['exit_code']==1 and 'trained pinned provider mismatch' in failures[0]['stderr']
 chosen=['service_A1','bulk_A1','tage_A1','bridge_A1','pipeline_A1','lookup_A3','manifest_A1','serial_A1']
 selected=[]
 for label in chosen:
  p=BASE/'reports'/(label+'.json');v=read(p);assert v['run']['exit_code']==0;assert v['result']['status'].startswith('PASS_');selected.append({'label':label,'report':m.ref(p),'result':v['result']})
 for p in read(BASE/'reports/lookup_A3.dependencies.json')['files']:assert digest(p['path'])==p['sha256'],'CURRENT_DEP_CHANGED'
 clock=read(BASE/'reports/CLOCK_COMPILE_A2.json');assert clock['execution']['exit_code']==0
 for x in clock['actual_dependencies']:assert digest(x['path'])==x['sha256'],'CLOCK_DEP_CHANGED'
 prior=read(BASE/'reports/PRESERVATION.lock.json')
 for x in prior['preserved']:assert digest(x['path'])==x['sha256'],'PRESERVED_ARTIFACT_CHANGED'
 lock=read(m.V9/'rate_state_v9/r2/runtime/configs/source.lock.json');transport=lock['transport']
 for name,sha in transport.items():assert digest(m.V9/'third_party/gem5-native-v9r2/src'/name)==sha
 counts={'legacy_before_v9':3009,'v9':len(list((m.V9/'rate_state_v9').glob('**/reports/run_starts/*.json'))),'v10':len(list((m.V10/'native_lifetime_next/runtime/reports/run_starts').glob('*.json'))),'v11_clean':len(list((m.V11/'overwrite_v11/runtime/cpu_regression/run_starts').glob('*.json'))),'v11_fault':len(list((m.V11/'overwrite_v11/runtime/cpu_fault_next/run_starts').glob('*.json')))}
 assert counts=={'legacy_before_v9':3009,'v9':352,'v10':108,'v11_clean':6,'v11_fault':12} and sum(counts.values())==3487
 index=BASE/'reports'/('SOURCE_VERSION_INDEX_'+a.attempt+'.json');m.put(index,{'status':'EXACT_CURRENT_OR_FROZEN_BYTES_VERIFIED','bindings':[{'original_path':p,'sha256':s,'verified_bytes':b} for (p,s),b in sorted(bindings.items())]})
 manifest=BASE/'runtime/manifest_A1.manifest.json';rows=read(manifest)['models'];assert sum(x['total_bits'] for x in rows)==59548
 table=[{'mode':['RECURRENT','DIRECT','OVERWRITE'][x['mode']],'source_update_L':x['source_update_L'],'source_query_L':x['source_query_L'],'provider_extra_L':1,'source_bits':x['source_bits'],'total_source_provider_bits':x['total_bits']} for x in rows]
 result={'status':'PASS_V13_BULK_UNDO_AND_FINITE_PROVIDER_COMPONENT_NOT_O3_OR_HARDWARE_QUALIFICATION','goal_status':'active','selected_gates':selected,'clock_compile':m.ref(BASE/'reports/CLOCK_COMPILE_A2.json'),'retained_failed_stages':failures,'concrete_fix_count':1,'source_version_index':m.ref(index),'manifest':m.ref(manifest),'component_bit_counts':table,'cpu_start_counts':counts,'CPU_actual_global':3487,'CPU_cap':3487,'CPU_v13':0,'EDA_v13':0,'resources':resources,'preserved':m.ref(BASE/'reports/PRESERVATION.lock.json'),'old_transport_files_unchanged':len(transport),'actual_commands':executions,'NOT_DONE':['instantiated/linked O3 BPU integration','consecutive squash admission and upstream backpressure','full parity/ECC/TMR controller staging','new CPU cycles/IPC/ABCD/paired owner evaluation','hardware PPA/qualification'],'next':m.ref(BASE/'reports/NEXT_GEM5_CONNECTION.ko.md')}
 m.put(BASE/'reports'/('FINAL_GATES_'+a.attempt+'.json'),result)
 m.put(BASE/'reports'/('software.lock_'+a.attempt+'.json'),{'compiler':{'path':str(m.CC),'version':subprocess.check_output([str(m.CC),'--version'],text=True).splitlines()[0]},'python':{'path':sys.executable,'version':sys.version.split()[0]},'gem5_pin':lock['pin'],'inherited_commit':'06f67db12','new_installations':0,'current_component_gate':m.ref(BASE/'reports/lookup_A3.json'),'current_gem5_clock_compile':m.ref(BASE/'reports/CLOCK_COMPILE_A2.json'),'CPU_new':0,'EDA_new':0})
 print(json.dumps({'status':result['status'],'resources':resources,'retained_failures':len(failures),'physical_bits':table}))
if __name__=='__main__':main()
