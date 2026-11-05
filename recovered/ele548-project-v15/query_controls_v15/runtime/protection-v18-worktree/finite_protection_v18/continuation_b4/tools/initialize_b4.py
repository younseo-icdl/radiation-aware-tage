"""Tick-zero only; no CPU trials. Uses the separately frozen B4 producer."""
import pathlib,sys,os
sys.dont_write_bytecode=True
os.environ['V18_PRODUCER']='B4'
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(1,str(HERE.parents[1]/'tools'))
import cpu_runner as c
r=c.r;B=c.B
def main():
 producer=c.prepare_producer('B4');fixture=r.load(c.m.V15/'reports/CPU18_PROPOSAL.lock.json')['tasks'][0];rows=[]
 for method in c.config.METHODS:
  out=B/'runtime/initialization_B4'/method;out.mkdir(parents=True,exist_ok=False)
  execution=c.m.invoke('initialize_B4_'+method,['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',producer['binary']['path'],'--outdir='+str(out),producer['config']['path'],*c.config.args(method,fixture['program_binary']['path']),'--initialize-only'],120)
  init=r.load(out/'INITIALIZATION_ONLY.json');manifest=r.load(out/'logical_manifest.json');summary=r.load(out/'seu.json')
  assert init['tick']==0 and not init['CPU_trial'] and summary['applied_events']==0
  at=0
  for region in manifest['regions']:assert region['start']==at and region['bits']>0;at+=region['bits']
  assert at==manifest['total_logical_bits'] and sum(manifest['word_widths'])==346
  assert manifest['II']==manifest['protection_check_L']==manifest['encode_L']==1
  rows.append({'method':method,'execution':execution,'manifest':r.ref(out/'logical_manifest.json'),'summary':r.ref(out/'seu.json'),'logical_bits':at})
 r.put(B/'reports/INITIALIZATION_B4.json',{'status':'PASS_ALL6_TICK0_ONLY_NOT_CPU','producer':r.ref(B/'reports/PRODUCER_B4.lock.json'),'rows':rows,'new_CPU':0,'resources':r.snapshot()})
 print('B4_INITIALIZATION_PASS',[(x['method'],x['logical_bits']) for x in rows],flush=True)
if __name__=='__main__':main()
