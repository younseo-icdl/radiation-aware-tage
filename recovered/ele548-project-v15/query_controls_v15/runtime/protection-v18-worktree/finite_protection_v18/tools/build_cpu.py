#!/usr/bin/env python3
"""New four-object producer; immutable old objects and ELF remain unchanged."""
from pathlib import Path
import argparse,concurrent.futures,json,sys
sys.dont_write_bytecode=True
import common as m
r=m.r;B=m.BASE
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);a=p.parse_args()
 for name in ('scope_gate_FINAL_B1','vector_gate_FINAL_B1','source_guard_gate_FINAL_B1','source_transport_gate_FINAL_C2'):
  x=r.load(B/'reports'/(name+'.json'));assert x['result']['status'].startswith('PASS') and x['result']['CPU_trials']==0
  if name=='source_transport_gate_FINAL_C2':
   lock=r.load(x['source']['path'])
   for z in lock['files']:
    if '/src/' in z['path'] or '/tests/' in z['path']:assert r.sha(z['path'])==z['sha256']
 oldpath=Path('/home/youns/workspace/ele548-project-v14/o3_finite_v14/reports/MEASURED_BUILD_PLAN_B1.lock.json');old=r.load(oldpath)
 for z in old['old_link_objects']+old['old_static_libraries']:assert r.sha(z['path'])==z['sha256']
 oldelf=r.load(B/'reports/PRESERVED_BASELINE.lock.json')['current_binary'];assert r.sha(oldelf['path'])==oldelf['sha256']
 overlay=B/'gem5_overlay/src';gem=m.V9/'third_party/gem5-native-v9r2';flags=['-I'+str(overlay),*old['flags']]
 out=B/'runtime'/('gem5_build_'+a.attempt);out.mkdir(exist_ok=False);lock=m.freeze('CPU_BUILD_'+a.attempt)
 plan=B/'reports'/('CPU_BUILD_PLAN_'+a.attempt+'.lock.json');r.put(plan,{'status':'SOURCE_FROZEN_BEFORE_NEW_BUILD_NO_CPU','source_lock':lock,'old_plan':r.ref(oldpath),'flags':flags,'old_binary':oldelf,'new_binary_path':str(out/'gem5.protection_v18.opt'),'objects':old['old_link_objects'],'libraries':old['old_static_libraries'],'resources':r.snapshot(600,70)})
 def compile_one(pair):
  i,item=pair;source=Path(item['source']);relative=source.relative_to(gem/'src') if source.is_relative_to(gem/'src') else None
  if relative is not None and (overlay/relative).exists():source=overlay/relative
  obj=out/(str(i)+'_'+Path(item['object']).name);dep=out/(str(i)+'.d')
  run=m.invoke('cpu_compile_'+a.attempt+'_'+str(i),[m.CC,*flags,'-MMD','-MF',dep,'-c',source,'-o',obj],limit=600,extra_MiB=15)
  return {'replace':item['object'],'object':r.ref(obj),'dependency':r.ref(dep),'execution':run}
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:objects=list(pool.map(compile_one,enumerate(old['consumers'])))
 replacements={x['replace']:x['object']['path'] for x in objects};assert len(replacements)==4
 inputs=[replacements.get(x['path'],x['path']) for x in old['old_link_objects']];assert len(inputs)==1516
 binary=out/'gem5.protection_v18.opt'
 link=m.invoke('cpu_link_'+a.attempt,[m.CC,'-o',binary,'-rdynamic','-O3','-Wl,--as-needed','-Wl,--no-keep-memory',*inputs,'-Wl,--start-group',*[z['path'] for z in old['old_static_libraries']],'-Wl,--end-group','-L/opt/miniconda3/lib','-lpython3.13','-lpthread','-lz','-lrt','-ldl'],limit=600,extra_MiB=50)
 info=m.invoke('cpu_buildinfo_'+a.attempt,['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary,'--build-info']);assert 'gem5 version 25.1.0.1' in Path(info['stdout']['path']).read_text()
 deps={}
 for f in out.glob('*.d'):
  for name in f.read_text().replace('\\\n',' ').split(':',1)[1].split():deps[name]=r.ref(name)
 for z in old['old_link_objects']+old['old_static_libraries']+[oldelf]:assert r.sha(z['path'])==z['sha256']
 r.put(B/'reports'/('CPU_BUILD_'+a.attempt+'.json'),{'status':'PASS_NEW_V18_BUILD_NOT_CPU_QUALIFICATION','binary':r.ref(binary),'plan':r.ref(plan),'objects':objects,'unchanged_objects_reused':1512,'actual_dependencies':list(deps.values()),'link':link,'build_info':info,'resources':r.snapshot(),'new_CPU':0})
 print('PASS_NEW_V18_BUILD_NOT_CPU_QUALIFICATION',r.ref(binary))
if __name__=='__main__':main()
