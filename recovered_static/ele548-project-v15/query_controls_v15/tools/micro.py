#!/usr/bin/env python3
import sys
sys.dont_write_bytecode=True
import prepare as m
m.budget(extra_MiB=1,extra_seconds=10);source=m.BASE/'src/pipeline_micro.S';binary=m.BASE/'runtime/pipeline_micro'
build=m.invoke('micro_build_A1',[m.CC,'-nostdlib','-static','-no-pie','-Wl,-e,_start',source,'-o',binary])
run=m.invoke('micro_native_A1',[binary]);expected=m.BASE/'runtime/micro.expected.stdout'
expected.write_bytes(b'pipeline_checksum=4096\n')
assert open(run['stdout']['path'],'rb').read()==expected.read_bytes()
disassembly=m.invoke('micro_disassembly_A1',['/usr/bin/objdump','-d',binary])
m.put(m.BASE/'reports/MICRO_NATIVE_A1.json',{'status':'PASS_NATIVE_SYNTHETIC_CHECKSUM_NOT_GEM5','source':m.ref(source),'binary':m.ref(binary),'expected_stdout':m.ref(expected),'build':build,'run':run,'disassembly':disassembly,'CPU_new':0,'resources':m.budget()})
print('PASS_NATIVE_SYNTHETIC_CHECKSUM_NOT_GEM5')
