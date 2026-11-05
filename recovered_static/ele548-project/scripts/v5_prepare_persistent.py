"""Loop the same native-verified kernels inside one SE process, preserving BPU state."""
from v5_common import *
import subprocess,shutil,os
src=OUT/'sources/persistent';src.mkdir(exist_ok=False)
wrapper=src/'wrapper.c'
wrapper.write_text('''#include <stdio.h>
#include <stdlib.h>
int v5_task(int,char**);
int main(int argc,char**argv){
 if(argc!=2)return 91;
 FILE*f=fopen(argv[1],"r");if(!f)return 92;
 unsigned reps;char input[4096];
 if(fscanf(f,"%u %4095s",&reps,input)!=2||!reps||reps>32)return 93;
 fclose(f);char*args[]={argv[0],input,0};
 for(unsigned r=0;r<reps;++r){int status=v5_task(2,args);if(status)return status;}
 return 0;
}
''')
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
cc=ROOT/'.local/musl-1.2.6/bin/musl-gcc'
items=[]
for item in inputs:
    name=item['name'];folder=src/name;folder.mkdir()
    if name=='qsort_small':
        origin=ROOT/'third_party/mibench-original/automotive/qsort/qsort_small.c';code=origin.read_text();code=code.replace('  return 0;', '  fclose(fp);\n  return 0;');(folder/'kernel.c').write_text(code);files=[folder/'kernel.c'];flags=[]
    elif name=='dijkstra_small':
        origin=ROOT/'third_party/mibench-original/network/dijkstra/dijkstra_small.c';code=origin.read_text();assert code.count('exit(0);')==1;code=code.replace('exit(0);','fclose(fp);\n  return 0;');(folder/'kernel.c').write_text(code);files=[folder/'kernel.c'];flags=['-include','stdlib.h']
    else:
        origin=ROOT/'build/public_sources/sha/sha_driver.c'
        for p in origin.parent.iterdir():
            if p.suffix in ['.c','.h']:shutil.copy2(p,folder/p.name)
        files=[folder/'sha_driver.c',folder/'sha.c'];flags=['-DLITTLE_ENDIAN','-DUSE_MODIFIED_SHA']
    objects=[]
    for n,f in enumerate(files):
        o=folder/f'kernel{n}.o';r=timed([cc,'-O2','-static','-fno-pie','-no-pie','-Dmain=v5_task',*flags,'-c',f,'-o',o],folder/f'build{n}.log');assert r['exit_code']==0,r;objects.append(o)
    binary=folder/name;r=timed([cc,'-O2','-static','-fno-pie','-no-pie',wrapper,*objects,'-o',binary],folder/'link.log');assert r['exit_code']==0,r
    expected=(ROOT/item['native_stdout']).read_bytes()
    for reps in [1,2,8,32]:
        control=OUT/'inputs'/f'{name}.repeat{reps}.dat';control.write_text(f"{reps} {ROOT/item['input']}\n")
        result=timed([binary,control],folder/f'native_R{reps}.stdout');assert result['exit_code']==0
        data=(folder/f'native_R{reps}.stdout').read_bytes();assert data==expected*reps,'REPEATED_NATIVE_OUTPUT'
        items.append(dict(name=name,binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),
            input=str(control.relative_to(ROOT)),input_sha256=sha(control),native_stdout_sha256=sha(folder/f'native_R{reps}.stdout'),repetitions=reps,
            original_input_sha256=item['input_sha256'],original_stdout_sha256=item['native_stdout_sha256'],original_source=str(origin.relative_to(ROOT))))
write(OUT/'configs/persistent_inputs.lock.json',dict(status='NATIVE_EXACT_REPEATED_ANSWERS_PASS',programs=items,
    state_lifetime='One process, predictor not reset between calls. Runtime/allocator/cache/branch stream also persist; R-times cold launches is a separate surrogate, not isolated predictor-reset causality.',
    source_changes='Rename main, close task input, replace successful dijkstra exit with return; retain error exit; SHA LP64 port inherited.'))
print('PASS 12 persistent native outputs == complete original stdout repeated R times')
