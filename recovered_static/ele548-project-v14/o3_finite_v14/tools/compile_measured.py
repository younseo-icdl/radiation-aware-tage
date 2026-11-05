#!/usr/bin/env python3
"""Prepare measured producer objects only; preserve A1 executable/source.
Link needs another50MiB and is deliberately deferred until aggregate disk
approval. Pure observation changes are compared after stripping marked blocks.
"""
from pathlib import Path
import importlib.util,json,re,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def read(p):return json.loads(Path(p).read_text())
def strip(s):return re.sub(r' // OBSERVATION_BEGIN\n.*? // OBSERVATION_END\n','',s,flags=re.S)
def compact(s):return re.sub(r'\s+','',s)
def main():
 m.budget();native=BASE/'reports/CONTROLLER_GATE_B1.json';assert read(native)['result']['normal_controls']==23052
 # Reconstruct exact algorithm text outside observation-only code, with the
 # equivalent named-ready return and JSON punctuation normalized explicitly.
 for p in (BASE/'src').glob('*.hpp'):
  assert strip((BASE/'measured_src'/p.name).read_text())==p.read_text(),p.name
 for p in (BASE/'gem5_overlay/src').rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(BASE/'gem5_overlay/src');new=strip((BASE/'gem5_measured/src'/rel).read_text()).replace('/measured_src/source_access.hpp','/src/source_access.hpp')
  if p.suffix=='.cc' and p.name=='research_native_v9r2_tage.cc':
   new=new.replace('const bool ready=core.engine->can_retire(static_cast<TageBranchInfo*>(history)->tageBranchInfo->nGhist);\n return ready;','return core.engine->can_retire(static_cast<TageBranchInfo*>(history)->tageBranchInfo->nGhist);')
   new=new.replace('out<<"\\"model\\":\\"V14_FINITE_SOURCE_P0\\",','out<<"{\\"model\\":\\"V14_FINITE_SOURCE_P0\\",')
  assert compact(new)==compact(p.read_text()),('OBSERVATION_CHANGED_ALGORITHM_TEXT',str(rel))
 old=read(BASE/'reports/CPU_BUILD_PLAN_A1.lock.json');output=BASE/'runtime/gem5_measured_B1';output.mkdir(exist_ok=False)
 overlay=BASE/'gem5_measured/src';flags=['-I'+str(overlay),*old['flags']];gem=m.V9/'third_party/gem5-native-v9r2'
 plan=BASE/'reports/MEASURED_BUILD_PLAN_B1.lock.json';m.put(plan,{'status':'FROZEN_BEFORE_OBSERVATION_OBJECT_BUILD_NOT_LINKED','algorithm_reference':m.ref(BASE/'reports/CPU_BUILD_A1.json'),'native_gate':m.ref(native),'new_files':[m.ref(p) for directory in [BASE/'measured_src',overlay] for p in sorted(directory.rglob('*')) if p.is_file()],'consumers':old['consumers'],'flags':flags,'old_link_objects':old['old_link_objects'],'old_static_libraries':old['old_static_libraries'],'observation_stripped_algorithm_matches_A1':True,'new_CPU':0,'resources':m.budget()})
 rows=[]
 for i,item in enumerate(old['consumers']):
  source=Path(item['source']);rel=source.relative_to(gem/'src') if source.is_relative_to(gem/'src') else None
  if rel is not None and (overlay/rel).exists():source=overlay/rel
  obj=output/(str(i)+'_'+Path(item['object']).name);dep=output/(str(i)+'.d');run=m.invoke('measured_compile_'+str(i)+'_B1',[m.CC,*flags,'-MMD','-MF',dep,'-c',source,'-o',obj]);rows.append({'replace':item['object'],'object':m.ref(obj),'dependency':m.ref(dep),'execution':run})
 m.put(BASE/'reports/MEASURED_OBJECTS_B1.json',{'status':'PASS_MEASURED_FOUR_OBJECTS_NOT_LINKED_OR_CPU_EXECUTED','plan':m.ref(plan),'objects':rows,'new_CPU':0,'resources':m.budget()});print('PASS_MEASURED_FOUR_OBJECTS_NOT_LINKED_OR_CPU_EXECUTED')
if __name__=='__main__':main()
