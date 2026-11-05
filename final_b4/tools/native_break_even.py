"""Derived native cost threshold. Does not fabricate matched native fault B."""
import sys,pathlib,statistics
sys.dont_write_bytecode=True
import resources as r
B=r.BASE

def derive():
 native=r.load(B/'reports/NATIVE_REFERENCE6.json');assert native['status']=='PASS'
 means={(x['task']['label'].split('.')[1],x['task']['program']):x['cycles'] for x in native['rows']}
 results=[]
 for cohort in ('DEV','EVAL'):
  p=B/'reports'/(cohort+'_ANALYSIS.json')
  if not p.exists():continue
  analysis=r.load(p);groups={}
  for x in analysis['paired_rows']:
   if not x['valid_pair']:continue
   A=means[cohort,x['program']];key=(x['program'],x['scenario'],x['method']);groups.setdefault(key,[]).append({'owner':x['owner'],'native_clean_A':A,'finite_fault_D':x['D'],'required_native_fault_slowdown_pct_for_positive_absolute_net':100*(x['D']/A-1),'finite_common_B_minus_D':x['net_cycles']})
  for key,rows in sorted(groups.items()):results.append({'cohort':cohort,'program':key[0],'scenario':key[1],'method':key[2],'owners':rows,'mean_required_native_fault_slowdown_pct':statistics.mean(x['required_native_fault_slowdown_pct_for_positive_absolute_net'] for x in rows)})
 r.put(B/'reports/NATIVE_BREAK_EVEN_THRESHOLDS.json',{'status':'NEW_DERIVATION_FROM_ACTUAL_NATIVE_A_AND_FINITE_D_NOT_MEASURED_NATIVE_FAULT_B','formula':'Absolute protection net B_native-D >0 requires (B_native-A_native)/A_native > D/A_native-1. Both actual native A and finite D are measured here; matched native fault B is not.','native_reference':r.ref(B/'reports/NATIVE_REFERENCE6.json'),'rows':results,'does_not_prove_absolute_native_protection_win':True,'does_not_replace_common_resource_paired_analysis':True})
 print('NATIVE_BREAK_EVEN_DERIVED',len(results),flush=True)
if __name__=='__main__':derive()
