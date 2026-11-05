#!/usr/bin/env python3
"""Final local source/raw/authority integrity gate; never runs a simulator."""
from pathlib import Path
import datetime,json,subprocess,sys
sys.dont_write_bytecode=True
import run as v
import resources_disk328 as r
B=v.BASE;V15=v.V15
def checked(x):v.original.checked(x);return x
def main():
 analysis=v.load(B/'reports/FINAL_ANALYSIS.json');assert analysis['actual_executions']==20 and analysis['selected_valid_conditions']==18
 assert v.load(B/'reports/REMAINING_B2.json')['CPU_simulations_added_by_recovery']==0
 proposal=v.load(V15/'reports/CPU18_PROPOSAL.lock.json')
 refs=[checked(x) for x in proposal.values() if isinstance(x,dict) and {'path','sha256'}<=x.keys()]
 build=v.load(proposal['build']['path']);dependencies=[checked(x) for x in build['actual_dependencies']]
 original_failed=v.load(B/'reports/PRECHECK_A1.json')['old_failed_files_preserved']
 for x in original_failed:checked(x)
 raw_checks=0
 for item in analysis['selected']:
  checked(item['execution']);row=v.load(item['execution']['path']);directory=Path(item['execution']['path']).parent
  for name,digest in row['hashes'].items():assert v.m.sha(directory/name)==digest;raw_checks+=1
 for name in ('REGRESSIONS_A1.lock.json','REMAINING_B1.lock.json'):
  plan=v.load(B/'reports'/name)
  for key in ('binary','config','observer','runner'):
   checked(plan[key])
  if 'guard' in plan:checked(plan['guard'])
 prefix=(B/'config/o3_terminal_v17.py').read_text().split('import atexit,sys',1)[0]
 assert prefix==Path(proposal['config']['path']).read_text().split('if a.initialize_only:\n',1)[0]
 a2=v.load(V15/'reports/early_gate_A2.source.lock.json')['files'];a3=v.load(V15/'reports/early_gate_A3.source.lock.json')['files']
 old={x['path']:x for x in a2};gate_differences=[]
 for x in a3:
  assert v.m.sha(x['verified_bytes'])==x['sha256'];checked(x)
  prior=old.get(x['path'])
  if prior and prior['sha256']!=x['sha256']:
   assert v.m.sha(prior['verified_bytes'])==prior['sha256']
   gate_differences.append({'path':x['path'],'proposal_A2_SHA':prior['sha256'],'current_A3_SHA':x['sha256']})
 assert len(gate_differences)==1 and gate_differences[0]['path'].endswith('/tests/early_gate.cpp')
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:argv=(proc/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  assert not(argv and argv[0]==proposal['binary']['path'].encode()),'LIVE_CPU'
 resources=r.snapshot();assert resources['CPU_global']==3531 and resources['outstanding_reservations']==0
 paths=[B/'reports'/x for x in ('FINAL_ANALYSIS.json','FINAL_REPORT.ko.md','USER_ACTIONS_REQUIRED.md','PRECHECK_A1.json','REGRESSIONS_A1.json','REMAINING_B2.json','RECORD_RECOVERY_B2.lock.json','DISK_AUTHORIZATION_328.lock.json')]
 paths += [B/'runtime/regressions_A1/TERMINAL.json',B/'runtime/remaining_B1/TERMINAL.json',B/'runtime/remaining_B1/stderr',Path(__file__),B/'tools/summarize_final.py',B/'tools/recover_records_B2.py']
 result={'status':'PASS_FROZEN_SOURCE_AND_RAW_INTEGRITY_NOT_HARDWARE_QUALIFICATION','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer_branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'proposal_refs_verified':refs,'compiled_dependencies_verified':dependencies,'compiled_dependency_count':len(dependencies),'original_failed_file_count_preserved':len(original_failed),'selected_raw_file_SHA_checks':raw_checks,'same_pre_exit_config_bytes':len(prefix.encode()),'proposal_A2_to_A3_gate_test_only_changes':gate_differences,'no_predictor_CPP_or_ELF_changes_in_v17':True,'observer_only_new_logical_storage_bits':0,'exact_refs':[v.m.ref(p) for p in paths],'resources':resources,'CPU_simulations_added_by_verifier':0,'scope':'First-exit program performance plus bounded actual helper completion. CPU/BPU context-switch, faulted CPU campaign, common protection port and physical costs remain unqualified.'}
 v.m.put(B/'reports/FINAL_BINDINGS.json',result)
 print(json.dumps({k:result[k] for k in ('status','compiled_dependency_count','original_failed_file_count_preserved','selected_raw_file_SHA_checks','same_pre_exit_config_bytes','resources')},indent=2))
if __name__=='__main__':main()
