#!/usr/bin/env python3
"""Tick0-only object/config gate; no m5.simulate call on the executed branch."""
from pathlib import Path
import argparse,ast,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',default='A1');p.add_argument('--build-report',default='CPU_BUILD_A1.json');a=p.parse_args();m.budget();build=BASE/'reports'/a.build_report;b=json.loads(build.read_text());binary=Path(b['binary']['path']);assert m.sha(binary)==b['binary']['sha256']
 config=BASE/'gem5_overlay/o3_finite_v14.py';module=ast.parse(config.read_text());branch=next(n for n in module.body if isinstance(n,ast.If) and ast.unparse(n.test)=='a.initialize_only')
 assert not any(isinstance(n,ast.Call) and ast.unparse(n.func)=='m5.simulate' for item in branch.body for n in ast.walk(item))
 checksum=Path('/home/youns/workspace/ele548-project/build/checksum_freestanding');assert m.sha(checksum)=='d51408b0f09f4d9ad811066707f532cd98ff9c27e1b12f5abe748608f2170f66'
 plan=BASE/'reports'/('INIT_PLAN_'+a.attempt+'.lock.json');m.put(plan,{'status':'FROZEN_TICK0_INIT_ONLY','build':m.ref(build),'config':m.ref(config),'ELF':m.ref(checksum),'simulate_on_executed_branch':False,'CPU_new':0,'resources':m.budget()})
 rows=[]
 for rep in ['recurrent','direct','overwrite']:
  for L in [1,2]:
   label='init_'+rep+'_L'+str(L)+'_'+a.attempt;out=BASE/'runtime'/label;out.mkdir(exist_ok=False)
   r=m.invoke('command_'+label,['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary,'--outdir='+str(out),config,'--binary',checksum,'--representation',rep,'--source-latency',str(L),'--initialize-only'])
   proof=json.loads((out/'INITIALIZATION_ONLY.json').read_text());summary=json.loads((out/'seu.json').read_text());c=json.loads((out/'config.json').read_text())
   assert proof['tick']==0 and not proof['simulate_called'] and summary['tick']==0 and summary['source_cycles']==0 and summary['committed_ops']==0 and summary['lookups']==0 and summary['source_accepted']==0 and summary['conserved']
   assert c['system']['cpu']['type']=='BaseO3CPU' and c['system']['cpu']['numThreads']==1 and not c['system']['cpu']['decoupledFrontEnd']
   rows.append({'representation':rep,'source_L':L,'proof':m.ref(out/'INITIALIZATION_ONLY.json'),'summary':m.ref(out/'seu.json'),'manifest':m.ref(out/'logical_manifest.json'),'config':m.ref(out/'config.json'),'execution':r})
 m.put(BASE/'reports'/('INITIALIZATION_'+a.attempt+'.json'),{'status':'PASS_SIX_TICK0_OBJECT_CONFIGS_NOT_O3_FUNCTIONAL_GATE','plan':m.ref(plan),'cases':rows,'CPU_new':0,'resources':m.budget()});print('PASS_SIX_TICK0_OBJECT_CONFIGS_NOT_O3_FUNCTIONAL_GATE')
if __name__=='__main__':main()
