#!/usr/bin/env python3
"""Configuration-only reset gate; explicitly never m5.simulate."""
import argparse,ast,json,sys
sys.dont_write_bytecode=True
import prepare as m
BASE=m.BASE
def load(p):return json.loads(p.read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);a=p.parse_args();m.budget(extra_MiB=3,extra_seconds=30);m.preserve()
 build=BASE/'reports/CPU_BUILD_A1.json';binary=load(build)['binary'];assert m.sha(binary['path'])==binary['sha256']
 config=BASE/'gem5_overlay/o3_query_v15.py';tree=ast.parse(config.read_text());branch=next(n for n in tree.body if isinstance(n,ast.If) and ast.unparse(n.test)=='a.initialize_only')
 assert not any(isinstance(n,ast.Call) and ast.unparse(n.func)=='m5.simulate' for child in branch.body for n in ast.walk(child))
 checksum=m.V14.parent.parent/'ele548-project/build/checksum_freestanding';assert m.sha(checksum)=='d51408b0f09f4d9ad811066707f532cd98ff9c27e1b12f5abe748608f2170f66'
 plan=BASE/'reports'/('INIT_PLAN_'+a.attempt+'.lock.json');m.put(plan,{'status':'FROZEN_TICK0_NO_SIMULATE','build':m.ref(build),'config':m.ref(config),'checksum':m.ref(checksum),'tool':m.ref(__file__),'CPU_new':0})
 rows=[];bits={}
 for rep in ['recurrent','direct','overwrite']:
  for Q,U,early in [(1,1,False),(2,1,False),(2,2,False),(1,1,True),(2,1,True)]:
   label='init_'+rep+'_Q'+str(Q)+'U'+str(U)+'E'+str(int(early))+'_'+a.attempt;out=BASE/'runtime'/label;out.mkdir(exist_ok=False)
   run=m.invoke(label+'_command',['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary['path'],'--outdir='+str(out),config,'--binary',checksum,'--representation',rep,'--query-latency',Q,'--update-latency',U,*(['--early-unconditional'] if early else []),'--initialize-only'])
   proof=load(out/'INITIALIZATION_ONLY.json');summary=load(out/'seu.json');manifest=load(out/'logical_manifest.json');cfg=load(out/'config.json')
   assert proof['tick']==0 and not proof['simulate_called'] and summary['tick']==0 and summary['source_cycles']==0 and summary['committed_ops']==0 and summary['source_accepted']==0 and summary['early_pending']==0 and summary['conserved']
   assert summary['early_enabled']==early and manifest['early_unconditional']==early and manifest['source_query_L']==Q and manifest['source_update_L']==(1 if rep=='direct' else U)
   assert cfg['system']['cpu']['type']=='BaseO3CPU' and not cfg['system']['cpu']['decoupledFrontEnd'] and cfg['system']['cpu']['numThreads']==1
   cursor=0
   for region in manifest['regions']:assert region['start']==cursor and region['bits']>0;cursor+=region['bits']
   assert cursor==manifest['total_logical_bits'];bits[rep,Q,U,early]=cursor
   if early:assert bits[rep,Q,U,True]-bits[rep,Q,U,False]==848
   if not early and Q==U:
    old=load(m.V14/'runtime/cpu_trials'/('checksum.'+rep+'.L'+str(Q))/'logical_manifest.json');assert old['regions']==manifest['regions'] and old['total_logical_bits']==cursor
   rows.append({'representation':rep,'query_L':Q,'update_L':U,'early':early,'proof':m.ref(out/'INITIALIZATION_ONLY.json'),'summary':m.ref(out/'seu.json'),'manifest':m.ref(out/'logical_manifest.json'),'config':m.ref(out/'config.json'),'execution':run})
 m.preserve();m.put(BASE/'reports'/('INITIALIZATION_'+a.attempt+'.json'),{'status':'PASS_15_TICK0_CONFIGS_NOT_CPU_EXECUTION','plan':m.ref(plan),'cases':rows,'CPU_new':0,'resources':m.budget()});print('PASS_15_TICK0_CONFIGS_NOT_CPU_EXECUTION')
if __name__=='__main__':main()
