#!/usr/bin/env python3
import argparse,sys
sys.dont_write_bytecode=True
import cpu_runner as c
r=c.r;B=c.B
def tasks(kind):
 old=r.load(c.m.V15/'reports/CPU18_PROPOSAL.lock.json');fixture=next(t for t in old['tasks'] if t['program']=='pipeline_micro') if kind=='MICRO' else old['tasks'][0]
 init=r.load(B/'reports'/('INITIALIZATION_'+c.PRODUCER+'.json'));assert init['status']=='PASS_ALL6_TICK0_ONLY_NOT_CPU'
 manifests={x['method']:r.load(x['manifest']['path']) for x in init['rows']};out=[]
 for method in c.config.METHODS:
  label=kind+'_'+c.PRODUCER+'.'+method;task={'label':label,'phase':'CPU_GATE24','method':method,'program':'pipeline_micro' if kind=='MICRO' else 'checksum','program_binary':fixture['program_binary'],'input':None,'expected_stdout':fixture['expected_stdout'],'timeout_seconds':300,'early':True,'query_L':1,'output':str(B/'runtime/cpu_trials'/label),'expected_applied_events':0}
  if kind in ('SBU','MID_STAGE_DOUBLE'):
   path=B/'runtime/configs'/(label+'.ticks')
   if kind=='SBU':text='1000000 R49\n';task['expected_applied_events']=1
   else:
    start=next(x['start'] for x in manifests[method]['regions'] if x['name']=='protect_stage_payload');text=f'1000000 G1R:{start}\n1000001 G1R:{start+1}\n';task['expected_applied_events']=2;task['gate_kind']=kind
   with path.open('x') as f:f.write(text)
   task['schedule']=r.ref(path)
  if kind!='CHECKSUM':
   base=B/'runtime/cpu_trials'/('CHECKSUM_'+c.PRODUCER+'.'+method)/'EXECUTION.json'
   if kind!='MICRO':task['architectural_reference']=r.ref(base)
  out.append(task)
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--kind',choices=['CHECKSUM','MICRO','SBU','MID_STAGE_DOUBLE'],required=True);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
 items=tasks(a.kind)
 if a.kind=='CHECKSUM':
  pilot=[t for t in items if t['method'] in ('P0','P_ECC')];rest=[t for t in items if t not in pilot]
  good,_=c.batch('CPU_GATE_'+c.PRODUCER+'_CHECKSUM_INITIAL2',pilot,2)
  if good:good,_=c.batch('CPU_GATE_'+c.PRODUCER+'_CHECKSUM_REMAINING4',rest,2)
 else:good,_=c.batch('CPU_GATE_'+c.PRODUCER+'_'+a.kind,items,a.workers)
 if not good:sys.exit(1)
if __name__=='__main__':main()
