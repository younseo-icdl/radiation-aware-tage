#!/usr/bin/env python3
"""Summarize executed C++ evidence; never starts a CPU or fabricates trials."""
from pathlib import Path
import difflib,importlib.util,json,sys
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('v16gate',Path(__file__).with_name('gate.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
B=g.BASE
def analyze():
 g.preserve();budget=g.parent.budget(extra_MiB=.2)
 gate=B/'reports/protocol_A2.json';d=json.loads(gate.read_text());r=d['result']
 assert r['status']=='PASS_PATH_ONLY_NATIVE_CHECKPOINT_PROTOCOL_NOT_CPU'
 assert not list((g.PARENT/'runtime').rglob('run_starts/*.json'))
 cases=[]
 for mode in range(3):
  for Q in (1,2):
   for conditional in (False,True):
    rows=[x for x in r['timing_cases'] if x['mode']==mode and x['query_L']==Q and x['conditional']==conditional and x['early']]
    full=next(x for x in rows if not x['path_only']);path=next(x for x in rows if x['path_only'])
    delta={k:path[k]-full[k] for k in ('prediction_done_cycle','checkpoint_done_cycle','retirement_done_cycle','max_lookup_pending')}
    if conditional:assert not any(delta.values())
    cases.append({'mode':['REC','DIRECT','OVERWRITE'][mode],'Q':Q,'U':1,'conditional':conditional,'early_full':full,'early_path':path,'path_minus_full':delta})
 sources=[]
 for p in sorted((B/'src').glob('*.hpp')):
  old=g.PARENT/'src'/p.name
  before=old.read_text().replace('namespace bp::v15','namespace bp::v16')
  after=p.read_text()
  sources.append({'current':g.ref(p),'v15':g.ref(old),'different_beyond_namespace':before!=after})
  if before!=after:
   dst=B/'reports'/(p.stem+'.v15-v16.diff')
   dst.write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(old)+' (normalized namespace)',tofile=str(p))))
 g.put(B/'reports/ANALYSIS.json',{'status':'EXECUTED_CPP_CONTROL_NOT_CPU_OR_PROTECTION_RANKING','gate':g.ref(gate),'cases':cases,'source_differences':sources,'old_v15_CPU18_proposal':g.ref(g.PARENT/'reports/CPU18_PROPOSAL.lock.json'),'v16_new_CPU':0,'resources':budget})
 print(json.dumps({'status':r['status'],'cases':len(cases),'changed_production_files':[Path(x['current']['path']).name for x in sources if x['different_beyond_namespace']],'resources':budget},indent=2))
if __name__=='__main__':analyze()
