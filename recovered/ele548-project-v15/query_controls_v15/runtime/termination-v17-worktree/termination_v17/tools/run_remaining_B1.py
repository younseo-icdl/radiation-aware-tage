#!/usr/bin/env python3
"""Six original unstarted programs after PASS; <=6 parallel, no retries."""
from pathlib import Path
import argparse,ast,concurrent.futures,json,sys
sys.dont_write_bytecode=True
import run as v17
import resources_disk328 as r
B=v17.BASE;m=v17.m;V15=v17.V15;OUT=r.scope['OUT'];original=v17.original
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
 proposal=v17.load(V15/'reports/CPU18_PROPOSAL.lock.json')
 tasks=[t for t in proposal['tasks'][9:] if not (OUT/'run_starts'/(t['label']+'.json')).exists()]
 assert len(tasks)==6 and {t['program'] for t in tasks}=={'qsort_small','sha1'}
 if not a.run:print(json.dumps({'status':'DRY_RUN_ONLY','labels':[t['label'] for t in tasks],'resources':r.snapshot(),'guard_change':r.transformation()},indent=2));return
 assert v17.load(B/'reports/REGRESSIONS_A1.json')['status']=='PASS_TWO_TERMINAL_REGRESSIONS'
 assert r.snapshot()['outstanding_reservations']==0
 binary=original.checked(proposal['binary']);config=B/'config/o3_terminal_v17.py';build=v17.load(original.checked(proposal['build']))
 for dep in build['actual_dependencies']:original.checked(dep)
 old_reg=v17.load(B/'reports/REGRESSIONS_A1.lock.json')
 assert m.sha(config)==old_reg['config']['sha256'] and m.sha(B/'config/terminal_observer.py')==old_reg['observer']['sha256']
 assert all(not Path(t['output']).exists() for t in tasks)
 r.snapshot(sum(t['timeout_seconds']+5 for t in tasks),6)
 plan=B/'reports/REMAINING_B1.lock.json'
 m.put(plan,{'status':'FROZEN_SAME_SIX_UNSTARTED_CASES_AFTER_REAL_TERMINAL_REGRESSIONS','proposal':m.ref(V15/'reports/CPU18_PROPOSAL.lock.json'),'CPU_authorization':m.ref(r.scope['AUTH']),'disk_authorization':m.ref(r.auth),'regressions':m.ref(B/'reports/REGRESSIONS_A1.json'),'runner':m.ref(__file__),'guard':m.ref(Path(r.__file__)),'guard_derivation':r.transformation(),'binary':m.ref(binary),'config':m.ref(config),'observer':m.ref(B/'config/terminal_observer.py'),'tasks':tasks,'resources':r.snapshot()})
 oldplan=v17.load(original.checked(proposal['v14_execution_plan']));source=original.checked(oldplan['runner']);tree=ast.parse(source.read_text());main_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');one=next(n for n in main_node.body if isinstance(n,ast.FunctionDef) and n.name=='one')
 scope=vars(original.old).copy();scope.update(BASE=B,ROOT=m.ROOT,OUT=OUT,m=m,r=r,binary=binary,config=config,build=build,proposal=dict(proposal,config=m.ref(config)),plan=plan,validate=v17.validate)
 exec(compile(ast.Module(body=[one],type_ignores=[]),str(source),'exec'),scope)
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(scope['one'],tasks))
 good=all(x['status'].startswith('PASS_') for x in rows)
 m.put(B/'reports/REMAINING_B1.json',{'status':'PASS_SIX_REMAINING_PROGRAMS' if good else 'FAILURES_RETAINED','rows':rows,'plan':m.ref(plan),'resources':r.snapshot()})
 print('PASS_SIX_REMAINING_PROGRAMS' if good else 'FAILURES_RETAINED',len(rows),flush=True)
if __name__=='__main__':main()
