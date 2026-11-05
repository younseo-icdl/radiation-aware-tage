import os,sys
sys.dont_write_bytecode=True
os.environ['V18_PRODUCER']='B2'
import gate_cpu as g
c=g.c;B=c.B;r=c.r
def run(kind,methods):
 items=[t for t in g.tasks(kind) if t['method'] in methods]
 if kind not in ('CHECKSUM','MICRO'):
  for t in items:t['architectural_reference']=r.ref(B/'runtime/cpu_trials'/('CHECKSUM_B1.'+t['method'])/'EXECUTION.json')
 for t in items:t['phase']='REGRESSION_RESERVE_B2'
 good,rows=c.batch('B2_REGRESSION_'+kind,items,2)
 if not good:raise RuntimeError('B2_REGRESSION_FAILED_'+kind)
 return rows
run('CHECKSUM',('P_ED_FREQUENT','P_ECC'));run('MICRO',('P0',));run('SBU',('P_ED_FREQUENT','P_ED_PERIODIC_N1'))
r.put(B/'reports/B2_REGRESSION_ACCEPTANCE.json',{'status':'PASS_TARGETED_B2_CPU_REGRESSION_FULL6_CPP_RERUN','normal_CPU':2,'micro_CPU':1,'SBU_CPU':2,'same_source_contract':True,'prior_full6_CPU_normal_gates':'B1 with zero-Undo ordering difference explicitly documented','resources':r.snapshot()})
# Remaining original stage-intermediate fault gate, all6 methods, primary6.
items=g.tasks('MID_STAGE_DOUBLE')
for t in items:t['architectural_reference']=r.ref(B/'runtime/cpu_trials'/('CHECKSUM_B1.'+t['method'])/'EXECUTION.json')
good,rows=c.batch('CPU_GATE_B2_MID_STAGE_DOUBLE',items,2)
if not good:raise RuntimeError('MID_STAGE_DOUBLE_GATE_FAILED')
r.put(B/'reports/G2_ACCEPTANCE.json',{'status':'PASS_COMPONENT_ALL6_AND_ACTUAL_CPU_GATES_WITH_RETAINED_FAILURES','producer':r.ref(B/'reports/PRODUCER_B2.lock.json'),'B1_normal6':r.ref(B/'reports/CPU_GATE_B1_CHECKSUM_REMAINING4.json'),'B1_micro6':r.ref(B/'reports/CPU_GATE_B1_MICRO.json'),'B1_SBU6_with_parity_failures_retained':r.ref(B/'reports/CPU_GATE_B1_SBU.json'),'B2_targeted_regression':r.ref(B/'reports/B2_REGRESSION_ACCEPTANCE.json'),'B2_midstage6':r.ref(B/'reports/CPU_GATE_B2_MID_STAGE_DOUBLE.json'),'CPU_performance_not_yet_evaluated':True,'resources':r.snapshot()})
