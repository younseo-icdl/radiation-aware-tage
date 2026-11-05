#!/usr/bin/env python3
"""Link prepared measured objects only after actual user budget authorization."""
from pathlib import Path
import importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('bounded',BASE/'tools/prepare.py');r=module('resources',BASE/'tools/resources.py')
def main():
 assert r.caps()['approved'],'USER_BUDGET_APPROVAL_REQUIRED_NO_MUTATION'
 r.snapshot(additional_MiB=52);objects=json.loads((BASE/'reports/MEASURED_OBJECTS_B1.json').read_text());plan=json.loads(Path(objects['plan']['path']).read_text())
 assert m.sha(objects['plan']['path'])==objects['plan']['sha256']
 replacements={v['replace']:Path(v['object']['path']) for v in objects['objects']}
 for v in objects['objects']:assert m.sha(v['object']['path'])==v['object']['sha256']
 for v in plan['new_files']+plan['old_link_objects']+plan['old_static_libraries']:assert m.sha(v['path'])==v['sha256']
 binary=BASE/'runtime/gem5_measured_B1/gem5.finite_measured.opt';assert not binary.exists()
 inputs=[replacements.get(v['path'],Path(v['path'])) for v in plan['old_link_objects']];libs=[Path(v['path']) for v in plan['old_static_libraries']]
 execution=m.invoke('measured_link_B1',[m.CC,'-o',binary,'-rdynamic','-O3','-Wl,--as-needed','-Wl,--no-keep-memory',*inputs,'-Wl,--start-group',*libs,'-Wl,--end-group','-L/opt/miniconda3/lib','-lpython3.13','-lpthread','-lz','-lrt','-ldl'])
 version=m.invoke('measured_buildinfo_B1',['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary,'--build-info'])
 assert 'gem5 version 25.1.0.1' in Path(version['stdout']['path']).read_text()
 deps={}
 for p in (BASE/'runtime/gem5_measured_B1').glob('*.d'):
  text=p.read_text().replace('\\\n',' ')
  for name in text.split(':',1)[1].split():deps[name]=m.ref(name)
 for v in plan['new_files']+plan['old_link_objects']+plan['old_static_libraries']:assert m.sha(v['path'])==v['sha256']
 m.put(BASE/'reports/MEASURED_BINARY_B1.json',{'status':'PASS_MEASURED_O3_BINARY_BUILT_NOT_CPU_EXECUTED','binary':m.ref(binary),'plan':objects['plan'],'execution':execution,'version':version,'actual_dependencies':list(deps.values()),'CPU_new':0,'resources':r.snapshot()});print('PASS_MEASURED_O3_BINARY_BUILT_NOT_CPU_EXECUTED')
if __name__=='__main__':main()
