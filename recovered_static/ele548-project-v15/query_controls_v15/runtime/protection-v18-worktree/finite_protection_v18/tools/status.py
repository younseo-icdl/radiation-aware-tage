"""Read-only actual state. Does not start trials or change a producer."""
import sys,pathlib,collections,json,datetime
sys.dont_write_bytecode=True
import resources as r

def snapshot():
 state=r.snapshot();counts=collections.Counter();fail=[];active=[]
 for marker in sorted((r.BASE/'runtime/run_starts').glob('*.json')):
  t=r.load(marker);p=pathlib.Path(t['output'])/'EXECUTION.json'
  if p.exists():
   x=r.load(p);counts[(t['phase'],x['status'])]+=1
   if x['status'].startswith('FAIL'):fail.append({'label':t['label'],'failure':x.get('failure'),'execution':r.ref(p)})
  else:active.append({'label':t['label'],'output':t['output'],'started':t['started']})
 return {'at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'resources':state,'counts':[{'phase':a,'status':b,'count':n} for (a,b),n in sorted(counts.items())],'active':active,'failures_retained':fail,'stage_gates':{p.name:r.load(p).get('status') for p in (r.BASE/'reports').glob('*ACCEPTANCE.json')},'matrix_complete':(r.BASE/'reports/FINITE_MATRIX_COMPLETED.json').exists(),'not_a_hardware_qualification':True}
if __name__=='__main__':print(json.dumps(snapshot(),indent=2))
