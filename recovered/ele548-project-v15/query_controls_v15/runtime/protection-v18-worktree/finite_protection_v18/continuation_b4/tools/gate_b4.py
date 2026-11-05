"""B4 O3 checksum6, overlap6 and finite mid-stage DUE6 before campaigns."""
import pathlib,sys,os
sys.dont_write_bytecode=True
os.environ['V18_PRODUCER']='B4'
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(1,str(HERE.parents[1]/'tools'))
import cpu_runner as c
import gate_cpu as g
r=c.r;B=c.B
def main():
 assert r.load(B/'reports/INITIALIZATION_B4.json')['status']=='PASS_ALL6_TICK0_ONLY_NOT_CPU'
 items=g.tasks('CHECKSUM');pilot=[x for x in items if x['method'] in ('P0','P_ECC')]
 for name,tasks,width in [('CHECKSUM_INITIAL2',pilot,2),('CHECKSUM_REST4',[x for x in items if x not in pilot],2)]:
  good,rows=c.batch('B4_GATE_'+name,tasks,width)
  assert good,('B4_FAILED_GATE_RAW_RETAINED',name)
 for name in ('MICRO','MID_STAGE_DOUBLE'):
  good,rows=c.batch('B4_GATE_'+name,g.tasks(name),2)
  assert good,('B4_FAILED_GATE_RAW_RETAINED',name)
 # Actual decoder DUE/reset/refill/normal program output must be observed.
 ecc=r.load(B/'runtime/cpu_trials/MID_STAGE_DOUBLE_B4.P_ECC/EXECUTION.json')
 s=ecc['program_exit_seu'];assert s['protection_DUE']>0 and s['protection_resets']>0 and s['committed_refill_publications']>=130 and s['refill_drains']>0
 for method in c.config.METHODS:
  row=r.load(B/'runtime/cpu_trials'/('MICRO_B4.'+method)/'EXECUTION.json');assert row['program_exit_seu']['max_lookup_pending']>=2
 r.put(B/'reports/B4_CORRECTNESS_ACCEPTANCE.json',{'status':'PASS_B4_CPP_AND_ACTUAL_O3_NORMAL_OVERLAP_DUE18_NOT_ALL_ADDED_BITS','producer':r.ref(B/'reports/PRODUCER_B4.lock.json'),'component_gates':[r.ref(B/'reports'/(name+'_B4.json')) for name in ('scope_gate','vector_gate','source_guard_gate','source_transport_gate','transaction_gate','zero_undo_gate','rmw_phase_gate','commit_ingress_gate')],'actual_O3_18':[r.ref(B/'reports'/('B4_GATE_'+name+'.json')) for name in ('CHECKSUM_INITIAL2','CHECKSUM_REST4','MICRO','MID_STAGE_DOUBLE')],'B3_failure_retained':r.ref(B/'runtime/continuation_b3/reports/B3_ROUND_STOP_104.json'),'all_queues_and_time_units_finite':True,'program_performance_and_independent_ABCD_not_yet_measured':True,'resources':r.snapshot()})
 print('B4_O3_GATE18_PASS',flush=True)
if __name__=='__main__':main()
