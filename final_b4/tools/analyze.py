"""Observed-only A/B/C/D and paired owner inference; no imputation."""
import sys,pathlib,json,math,itertools,collections,statistics
sys.dont_write_bytecode=True
import campaign as p
r=p.r;B=p.B
sys.path.insert(0,str(p.c.m.V9/'scripts'));from rng_namespace import rng

def summarize(cohort):
 clean=p.rows(cohort+'_CLEAN');fault=p.rows(cohort+'_FAULT');cm={(x['program'],x['method']):x for x in clean if x['status'].startswith('PASS')};groups=collections.defaultdict(list);by={}
 for x in fault:by[x['task']['owner'],x['task']['scenario'],x['program'],x['method']]=x
 details=[]
 for x in fault:
  t=x['task'];program=t['program'];method=t['method'];scenario=t['scenario'];owner=t['owner'];ref=by.get((owner,scenario,program,'P0'));a=cm.get((program,'P0'));c=cm.get((program,method));valid=all(z and z['status'].startswith('PASS') for z in (x,ref,a,c))
  row={'program':program,'scenario':scenario,'method':method,'owner':owner,'valid_pair':valid,'failure':x.get('failure'),'A':a['cycles'] if a else None,'B':ref['cycles'] if ref and ref['status'].startswith('PASS') else None,'C':c['cycles'] if c else None,'D':x['cycles'] if valid else None,'applied_events':x.get('applied_events'),'future_censored':x.get('program_exit_seu',{}).get('future_events_censored'),'host_cpu_seconds':x.get('host_cpu_seconds')}
  if valid:
   A,Bv,C,D=(row[k] for k in ('A','B','C','D'));row.update(net_cycles=Bv-D,net_pct_A=100*(Bv-D)/A,unprotected_damage=Bv-A,clean_overhead=C-A,residual_damage=D-C)
  details.append(row);groups[program,scenario,method].append(row)
 summaries=[]
 for key,values in sorted(groups.items()):
  good=[x for x in values if x['valid_pair']];gains=[x['net_cycles'] for x in good];nonzero=[x for x in gains if x];positive=sum(x>0 for x in nonzero);n=len(nonzero)
  sign=min(1.,2*sum(math.comb(n,i) for i in range(min(positive,n-positive)+1))/(2**n)) if n else 1.
  if gains:
   import numpy as np
   # Separate analysis namespace; does not alter any event or predictor stream.
   rr=rng(33000000000+len(summaries),'location');v=np.asarray(gains,dtype=float);samples=v[rr.integers(0,len(v),size=(20000,len(v)))].mean(axis=1);ci=[float(x) for x in np.quantile(samples,[.025,.975])]
  else:ci=None
  summaries.append({'program':key[0],'scenario':key[1],'method':key[2],'observed_owners':len(values),'valid_pairs':len(good),'failed_pairs':len(values)-len(good),'mean_B_minus_D':statistics.mean(gains) if gains else None,'mean_net_pct_A':statistics.mean(x['net_pct_A'] for x in good) if good else None,'bootstrap95_cycles':ci,'exact_two_sided_sign_p':sign,'positive_owners':sum(x>0 for x in gains),'zero_owners':sum(x==0 for x in gains),'negative_owners':sum(x<0 for x in gains),'complete_owner_ids':[x['owner'] for x in good]})
 for program,scenario in sorted({(x['program'],x['scenario']) for x in summaries}):
  ss=sorted([x for x in summaries if x['program']==program and x['scenario']==scenario and x['method']!='P0'],key=lambda x:x['exact_two_sided_sign_p']);running=0
  for i,x in enumerate(ss):running=max(running,min(1.,x['exact_two_sided_sign_p']*(len(ss)-i)));x['Holm_sign_p_within_program_scenario']=running
 clean_out=[]
 for x in clean:
  if not x['status'].startswith('PASS'):continue
  s=x['program_exit_seu'];cycles=x['cycles'];clean_out.append({'program':x['program'],'method':x['method'],'cycles':cycles,'IPC':x['IPC'],'accepted_per_source_cycle':s['lookup_accepted']/s['source_cycles'],'produced_per_source_cycle':s['lookup_produced']/s['source_cycles'],'consumed_per_source_cycle':s['lookup_consumed']/s['source_cycles'],'max_lookup_pending':s['max_lookup_pending'],'max_source_pending':s['max_source_pending'],'stalls_not_an_exact_CPI_decomposition':{k:v for k,v in s.items() if 'stall' in k or 'wait' in k or 'hold' in k},'normal_checks':s['protection_checks'],'normal_encodes':s['protection_encodes'],'retention_reentries_not_repairs':s['unverified_retention_reentries']})
 return {'cohort':cohort,'clean':clean_out,'paired_rows':details,'paired_summaries':summaries,'attempted_faults':len(fault),'valid_faults':sum(x['status'].startswith('PASS') for x in fault),'failure_count':sum(not x['status'].startswith('PASS') for x in fault),'assumptions':['n8 owner-level bootstrap is exploratory; same A/C reused and not independent samples','per-method complete pairs reported; missing failed owners are not zero or masked','sign tests plus Holm within program/scenario only; no global significance claim','main first-exit performance; helper cycles excluded; arbitrary modeled radiation stress not mission FIT']}
def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--cohort',choices=['DEV','EVAL'],required=True);ap.add_argument('--label',required=True);a=ap.parse_args();x=summarize(a.cohort);r.put(B/'reports'/(a.label+'.json'),x);print(a.label,'OBSERVED',x['attempted_faults'],x['failure_count'],flush=True)
if __name__=='__main__':main()
