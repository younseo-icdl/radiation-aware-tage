#!/usr/bin/env python3
"""New manual incremental gem5 producer; old sources/objects/binaries read-only.
Friend-only BAC/BPredUnit declarations preserve every layout/vtable. Original
CPU layout is unchanged; tick body and four affected object consumers rebuilt.
"""
from pathlib import Path
import argparse,importlib.util,json,pickle,sys
import SCons.dblite
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def read(p):return json.loads(Path(p).read_text())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--attempt',default='A1');a=ap.parse_args();m.budget()
 gate=BASE/'reports/CONTROLLER_GATE_A2.json';assert read(gate)['result']['status']=='PASS_FINITE_INGRESS_AND_SHARED_TAGE_SOURCE_NOT_O3_EXECUTION'
 oldplan=m.V11/'overwrite_v11/reports/CPU_OVERLAY_A3.lock.json';lock=read(oldplan);oldbuild=read(m.V11/'overwrite_v11/reports/CPU_BUILD.lock.json');gem=m.V9/'third_party/gem5-native-v9r2';overlay=BASE/'gem5_overlay/src'
 assert m.sha(lock['scons_database']['path'])==lock['scons_database']['sha256']
 for item in lock['immutable_link_objects']+lock['static_libraries']+[lock['old_binary']]:assert m.sha(item['path'])==item['sha256']
 for item in read(BASE/'reports/PRESERVATION.lock.json')['preserved']:assert m.sha(item['path'])==item['sha256']
 # Only friend declarations: exact inverse patch must reproduce old headers.
 for path in ['cpu/o3/bac.hh','cpu/pred/bpred_unit.hh']:
  text=(overlay/path).read_text().replace('namespace bp::v14 { struct RecoveryBridge; }\n\n','').replace('\n    friend struct ::bp::v14::RecoveryBridge;','')
  assert text==(gem/'src'/path).read_text(),'NON_FRIEND_BPU_BAC_LAYOUT_CHANGE'
 db=SCons.dblite.open(str(gem/'build/X86_PIPELINE/gem5.build/sconsign'),'r');entry=pickle.loads(db['build/X86_PIPELINE/cpu/o3'])['cpu.o']
 cpu={'source':str(gem/'src/cpu/o3/cpu.cc'),'object':str(gem/'build/X86_PIPELINE/cpu/o3/cpu.o'),'implicit':[str(gem/p) if not p.startswith('/') else p for p in entry.binfo.bimplicit]}
 consumers=[*lock['abi_consumers'],cpu]
 flags=['-I'+str(overlay),*oldbuild['flags']]
 external=set()
 for item in consumers:
  for name in item['implicit']:
   p=Path(name)
   if p.is_relative_to(gem/'ext'):
    for parent in p.parents:
     if parent==gem:break
     external.add(parent)
 flags.extend('-I'+str(p) for p in sorted(external,key=lambda p:(-len(p.parts),str(p))))
 output=BASE/'runtime'/('gem5_build_'+a.attempt);output.mkdir(exist_ok=False)
 source_files=[m.ref(p) for folder in [BASE/'src',overlay] for p in sorted(folder.rglob('*')) if p.is_file()]
 plan=BASE/'reports'/('CPU_BUILD_PLAN_'+a.attempt+'.lock.json');m.put(plan,{'status':'FROZEN_BEFORE_NEW_GEM5_BUILD_NOT_CPU_TESTED','controller_gate':m.ref(gate),'old_plan':m.ref(oldplan),'new_sources':source_files,'consumers':consumers,'flags':flags,'old_link_objects':lock['immutable_link_objects'],'old_static_libraries':lock['static_libraries'],'ABI_scope':'Only3 prior research-header consumers + CPU tick. BAC/BPredUnit friend-only edits no member/vtable change; CPU data layout unchanged. New research classes used only by these rebuilt bindings and new CPU dynamic_cast. Manual incremental build, not full SCons rebuild.','new_CPU':0,'resources':m.budget()})
 replacements={};records=[];new=[]
 for i,item in enumerate(consumers):
  source=Path(item['source']);relative=source.relative_to(gem/'src') if source.is_relative_to(gem/'src') else None
  if relative is not None and (overlay/relative).exists():source=overlay/relative
  target=output/(str(i)+'_'+Path(item['object']).name);dep=output/(str(i)+'.d')
  r=m.invoke('compile_'+str(i)+'_'+a.attempt,[m.CC,*flags,'-MMD','-MF',dep,'-c',source,'-o',target]);records.append(r);replacements[item['object']]=target;new.append(m.ref(target))
 objects=[replacements.get(item['path'],Path(item['path'])) for item in lock['immutable_link_objects']];assert len(replacements)==4 and len(objects)==1516
 binary=output/'gem5.finite_source.opt';libraries=[Path(item['path']) for item in lock['static_libraries']]
 records.append(m.invoke('link_'+a.attempt,[m.CC,'-o',binary,'-rdynamic','-O3','-Wl,--as-needed','-Wl,--no-keep-memory',*objects,'-Wl,--start-group',*libraries,'-Wl,--end-group','-L/opt/miniconda3/lib','-lpython3.13','-lpthread','-lz','-lrt','-ldl']))
 info=m.invoke('buildinfo_'+a.attempt,['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary,'--build-info']);assert 'gem5 version 25.1.0.1' in Path(info['stdout']['path']).read_text()
 for item in lock['immutable_link_objects']+lock['static_libraries']+[lock['old_binary']]:assert m.sha(item['path'])==item['sha256'],'OLD_LINK_INPUT_CHANGED'
 deps={}
 for p in output.glob('*.d'):
  text=p.read_text().replace('\\\n',' ')
  for name in text.split(':',1)[1].split():deps[name]=m.ref(name)
 m.put(BASE/'reports'/('CPU_BUILD_'+a.attempt+'.json'),{'status':'PASS_NEW_O3_FINITE_SOURCE_BINARY_BUILT_NOT_CPU_EXECUTED','binary':m.ref(binary),'plan':m.ref(plan),'new_objects':new,'old_objects_reused':1512,'actual_dependencies':list(deps.values()),'executions':records,'version':info,'new_CPU':0,'resources':m.budget()});print(json.dumps({'status':'PASS_NEW_O3_FINITE_SOURCE_BINARY_BUILT_NOT_CPU_EXECUTED','binary':m.ref(binary),'resources':m.budget()}))
if __name__=='__main__':main()
