#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
import common as m
r=m.r;B=m.BASE
METHODS={'P0':('P0',0,'recurrent'),'P_ED_FREQUENT':('P_ED',0,'recurrent'),'P_ED_PERIODIC_N1':('P_ED',64,'recurrent'),'P_ECC':('P_ECC',0,'recurrent'),'P_TMR':('P_TMR',0,'recurrent'),'EXACT_DIRECT':('P0',0,'direct')}
def args(method,program,input_path=None,early=True,L=1,schedule=''):
 scheme,k,rep=METHODS[method];out=['--binary',str(program),'--representation',rep,'--scheme',scheme,'--inspection-interval',str(k),'--query-latency',str(L),'--update-latency','1']
 if input_path:out+=['--input',str(input_path)]
 if early:out+=['--early-unconditional']
 if schedule:out+=['--schedule',str(schedule)]
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',default='A2');a=p.parse_args();build=r.load(B/'reports'/('CPU_BUILD_'+a.build+'.json'));binary=Path(build['binary']['path']);assert r.sha(binary)==build['binary']['sha256']
 old=r.load(m.V15/'reports/CPU18_PROPOSAL.lock.json');program=Path(old['tasks'][0]['program_binary']['path']);config=B/'gem5_overlay/o3_protection_v18.py'
 rows=[]
 for method in METHODS:
  out=B/'runtime/initialization_A1'/method;out.mkdir(parents=True,exist_ok=False)
  execution=m.invoke('initialize_A1_'+method,['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary,'--outdir='+str(out),config,*args(method,program),'--initialize-only'],limit=120)
  init=r.load(out/'INITIALIZATION_ONLY.json');manifest=r.load(out/'logical_manifest.json');summary=r.load(out/'seu.json')
  assert init['tick']==0 and not init['CPU_trial'] and summary['applied_events']==0
  at=0
  for region in manifest['regions']:assert region['start']==at and region['bits']>0;at+=region['bits']
  assert at==manifest['total_logical_bits'] and manifest['protection_check_L']==1 and manifest['II']==1 and sum(manifest['word_widths'])==346
  rows.append({'method':method,'execution':execution,'manifest':r.ref(out/'logical_manifest.json'),'summary':r.ref(out/'seu.json'),'logical_bits':at})
 r.put(B/'reports/INITIALIZATION_A1.json',{'status':'PASS_ALL6_TICK0_ONLY_NOT_CPU','binary':r.ref(binary),'config':r.ref(config),'rows':rows,'resources':r.snapshot(),'new_CPU':0});print('PASS_ALL6_TICK0_ONLY_NOT_CPU',[(x['method'],x['logical_bits']) for x in rows])
if __name__=='__main__':main()
