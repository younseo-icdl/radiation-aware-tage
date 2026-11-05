import os,sys
sys.dont_write_bytecode=True
os.environ['V18_PRODUCER']='B2'
import cpu_runner as c
r=c.r;B=c.B
init=r.load(B/'reports/INITIALIZATION_B2.json');manifests={x['method']:r.load(x['manifest']['path']) for x in init['rows']}
def tasks(kind,methods):
 out=[]
 for method in methods:
  original=r.load(B/'runtime/cpu_trials'/('CHECKSUM_B1.'+method)/'EXECUTION.json');fixture=original['task'];label=kind+'_B2.'+method
  t={k:fixture[k] for k in ('program','program_binary','input','expected_stdout','early','query_L','timeout_seconds')};t.update(label=label,phase='REGRESSION_RESERVE_B2' if kind=='SBU' else 'CPU_GATE24',method=method,output=str(B/'runtime/cpu_trials'/label),expected_applied_events=1 if kind=='SBU' else 2,architectural_reference=r.ref(B/'runtime/cpu_trials'/('CHECKSUM_B1.'+method)/'EXECUTION.json'))
  if kind=='SBU':text='1000000 R49\n'
  else:
   start=next(x['start'] for x in manifests[method]['regions'] if x['name']=='protect_stage_payload');text=f'1000000 G1R:{start}\n1000001 G1R:{start+1}\n';t['gate_kind']=kind
  p=B/'runtime/configs'/(label+'.ticks')
  if p.exists():assert p.read_text()==text
  else:
   with p.open('x') as f:f.write(text)
  t['schedule']=r.ref(p);out.append(t)
 return out
def main():
 for name in ('B2_REGRESSION_CHECKSUM','B2_REGRESSION_MICRO'):assert r.load(B/'reports'/(name+'.json'))['status']=='PASS'
 r.put(B/'reports/B2_DISPATCH_REFERENCE_FAILURE.json',{'status':'RETAINED_PLANNING_EXCEPTION_NO_CPU_DISPATCH','command':'python -B finite_protection_v18/tools/regression_b2.py','exception':'FileNotFoundError for CHECKSUM_B2.P0/EXECUTION.json while constructing unstarted SBU task list','completed_CPU_regressions':3,'new_SBU_CPU_before_exception':0,'fix':'Separate continuation explicitly binds each same-input architectural check to actual CHECKSUM_B1 method record; no surrogate zero or missing record','new_source_or_config_change':False})
 good,_=c.batch('B2_REGRESSION_SBU',tasks('SBU',('P_ED_FREQUENT','P_ED_PERIODIC_N1')),2)
 if not good:raise RuntimeError('B2_SBU_REGRESSION_FAILED')
 r.put(B/'reports/B2_REGRESSION_ACCEPTANCE.json',{'status':'PASS_TARGETED_B2_CPU_REGRESSION_FULL6_CPP_RERUN','normal_CPU':2,'micro_CPU':1,'SBU_CPU':2,'prior_normal_full6_producer':'B1, zero-Undo ordering update difference documented','resources':r.snapshot()})
 good,_=c.batch('CPU_GATE_B2_MID_STAGE_DOUBLE',tasks('MID_STAGE_DOUBLE',c.config.METHODS),2)
 if not good:raise RuntimeError('MID_STAGE_DOUBLE_GATE_FAILED')
 r.put(B/'reports/G2_ACCEPTANCE.json',{'status':'PASS_COMPONENT_ALL6_AND_ACTUAL_CPU_GATES_WITH_RETAINED_FAILURES','producer':r.ref(B/'reports/PRODUCER_B2.lock.json'),'B1_normal_initial2':r.ref(B/'reports/CPU_GATE_B1_CHECKSUM_INITIAL2.json'),'B1_normal_remaining4':r.ref(B/'reports/CPU_GATE_B1_CHECKSUM_REMAINING4.json'),'B1_micro6':r.ref(B/'reports/CPU_GATE_B1_MICRO.json'),'B1_SBU6_with_parity_failures_retained':r.ref(B/'reports/CPU_GATE_B1_SBU.json'),'B2_targeted_regression':r.ref(B/'reports/B2_REGRESSION_ACCEPTANCE.json'),'B2_midstage6':r.ref(B/'reports/CPU_GATE_B2_MID_STAGE_DOUBLE.json'),'CPU_performance_not_yet_evaluated':True,'resources':r.snapshot()})
if __name__=='__main__':main()
