import sys,os,pathlib
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;B=HERE.parents[1]
sys.path.insert(1,str(B/'tools'));os.environ['V18_PRODUCER']='B3'
import cpu_runner as c
r=c.r
assert r.load(B/'reports/rmw_phase_gate_B3.json')['result']['status'].startswith('PASS')
items=[]
for method in ('P_ED_FREQUENT','P_ED_PERIODIC_N1','P_ECC','P_TMR'):
 reference=B/'runtime/cpu_trials'/('CHECKSUM_B1.'+method)/'EXECUTION.json';old=r.load(reference)['task'];label='POST_RMW_B3.'+method;p=B/'runtime/configs'/(label+'.ticks')
 with p.open('x') as f:f.write('1000000 GU:R49\n')
 t={k:old[k] for k in ('program','program_binary','input','expected_stdout','early','query_L','timeout_seconds')};t.update(label=label,method=method,phase='REGRESSION_B3_POST_RMW4',output=str(B/'runtime/cpu_trials'/label),schedule=r.ref(p),expected_applied_events=1,architectural_reference=r.ref(reference),gate_kind='POST_RMW_PRIMARY_SINGLE');items.append(t)
good,rows=c.batch('B3_POST_RMW_PRIMARY_GATE',items,2)
if not good:raise RuntimeError('B3_LATE_SOURCE_GATE_FAILED')
r.put(B/'reports/B3_CORRECTNESS_ACCEPTANCE.json',{'status':'PASS_NEW_POST_RMW_SOURCE_GATE_ALL4_PROTECTED_NOT_ALL_ADDED_BITS','CPP_source_phases':r.ref(B/'reports/rmw_phase_gate_B3.json'),'actual_CPU4':r.ref(B/'reports/B3_POST_RMW_PRIMARY_GATE.json'),'producer':r.ref(B/'reports/PRODUCER_B3.lock.json'),'old_B2_fault_qualification_revoked':True,'resources':r.snapshot()})
