#!/usr/bin/env python3
"""User-local static MiBench builds and independent native answer validation."""
import hashlib
import heapq
import json
import re
import shutil
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    src=ROOT/'third_party/mibench-original';out=ROOT/'build/public_workloads';out.mkdir(parents=True,exist_ok=True)
    native=ROOT/'reports/e3_setup/native';native.mkdir(parents=True,exist_ok=True)
    cc=ROOT/'.local/musl-1.2.6/bin/musl-gcc';commands=[]
    def build(name,sources,flags):
        command=[str(cc),'-O2','-static','-fno-pie','-no-pie',*flags,*map(str,sources),'-o',str(out/name)]
        with (native/(name+'.build.log')).open('w') as f:subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
        commands.append(command)
    q=src/'automotive/qsort';d=src/'network/dijkstra';s=src/'security/sha'
    build('qsort_small',[q/'qsort_small.c'],[])
    # Historical source omitted stdlib prototypes; supply them at compilation.
    build('dijkstra_small',[d/'dijkstra_small.c'],['-include','stdlib.h'])
    # LP64 port: the historical LONG means a 32-bit SHA word, and the printf
    # format must match that word. Original source is preserved byte-for-byte.
    derived=ROOT/'build/public_sources/sha';derived.mkdir(parents=True,exist_ok=True)
    for p in s.iterdir():
        if p.is_file() and p.suffix in ['.c','.h']:shutil.copy2(p,derived/p.name)
    h=(derived/'sha.h').read_text();assert h.count('typedef unsigned long LONG;')==1
    (derived/'sha.h').write_text(h.replace('typedef unsigned long LONG;','#include <stdint.h>\ntypedef uint32_t LONG;'))
    code=(derived/'sha.c').read_text();assert code.count('%08lx')==5
    (derived/'sha.c').write_text(code.replace('%08lx','%08x'))
    # USE_MODIFIED_SHA is the original documented SHA-1 build option; LITTLE_ENDIAN
    # matches X86. The resulting digest is checked against independent hashlib.
    build('sha1',[derived/'sha_driver.c',derived/'sha.c'],['-DLITTLE_ENDIAN','-DUSE_MODIFIED_SHA'])
    items=[]
    for name,input_path in [('qsort_small',q/'input_small.dat'),('dijkstra_small',d/'input.dat'),('sha1',s/'input_small.asc')]:
        binary=out/name;output=native/(name+'.stdout');error=native/(name+'.stderr')
        with output.open('wb') as f,error.open('wb') as e:
            completed=subprocess.run([str(binary),str(input_path)],stdout=f,stderr=e,cwd=ROOT,timeout=30)
        assert completed.returncode==0 and not error.read_bytes(),(name,completed.returncode)
        text=output.read_text()
        if name=='qsort_small':
            tokens=input_path.read_text(encoding='ascii').split();assert 0<len(tokens)<60000 and max(map(len,tokens))<128
            lines=text.strip().splitlines();assert lines[0]==f'Sorting {len(tokens)} elements.' and lines[1]==''
            assert lines[2:]==sorted(tokens,reverse=True)
            validation={'algorithm':'independent Python descending full token multiset','tokens':len(tokens)}
        elif name=='sha1':
            digest=''.join(text.split());expected=hashlib.sha1(input_path.read_bytes()).hexdigest();assert digest==expected,(digest,expected)
            validation={'algorithm':'independent Python hashlib SHA-1 full public input','digest':expected}
        else:
            values=list(map(int,input_path.read_text().split()));assert len(values)==10000 and min(values)>=0
            matrix=[values[i*100:(i+1)*100] for i in range(100)];lines=text.strip().splitlines();assert len(lines)==20
            for a,line in enumerate(lines):
                match=re.fullmatch(r'Shortest path is (\d+) in cost\. Path is: (.*)',line);assert match,line
                cost=int(match[1]);route=list(map(int,match[2].split()));target=(a+50)%100
                assert route[0]==a and route[-1]==target and sum(matrix[x][y] for x,y in zip(route,route[1:]))==cost
                distances=[float('inf')]*100;distances[a]=0;heap=[(0,a)]
                while heap:
                    distance,node=heapq.heappop(heap)
                    if distance!=distances[node]:continue
                    for neighbor,weight in enumerate(matrix[node]):
                        if weight!=9999 and distance+weight<distances[neighbor]:distances[neighbor]=distance+weight;heapq.heappush(heap,(distance+weight,neighbor))
                assert distances[target]==cost
            validation={'algorithm':'independent Python heap shortest distances + all printed path costs/endpoints','nodes':100,'paths':20}
        sources=list(q.glob('*.c')) if name=='qsort_small' else [d/'dijkstra_small.c'] if name=='dijkstra_small' else list(derived.glob('*'))
        items.append({'name':name,'binary':str(binary.relative_to(ROOT)),'binary_sha256':sha(binary),
            'argv':[str(binary),str(input_path)],'input':str(input_path.relative_to(ROOT)),'input_sha256':sha(input_path),'input_bytes':input_path.stat().st_size,
            'native_stdout':str(output.relative_to(ROOT)),'native_stdout_sha256':sha(output),'native_exit_code':completed.returncode,'independent_answer':validation,
            'source_files':{str(p.relative_to(ROOT)):sha(p) for p in sources},'license_file':str((q if name=='qsort_small' else d if name=='dijkstra_small' else s).relative_to(ROOT))+'/LICENSE'})
    record={'status':'PASS_THREE_ACTUAL_PUBLIC_PROGRAM_NATIVE_ANSWERS','source_lock_sha256':sha(ROOT/'sources/public_workload_sources.lock.json'),
        'programs':items,'build_commands':commands,'compiler':'shell-local GCC11 via user-local musl1.2.6 wrapper','static':True,
        'source_changes':{'qsort_small':'none','dijkstra_small':'-include stdlib.h to supply missing declarations','sha1':'derived copy only: uint32_t LONG and %08x format; documented USE_MODIFIED_SHA/LITTLE_ENDIAN options'},
        'ROI':'whole process from startup to exit, includes libc/input parsing/output; no claim of compute-only or SPEC score',
        'workload_boundary':'official MiBench public small inputs; not HW1 or actual SPEC application execution',
        'gem5_O3_run':'NOT_YET_RUN'}
    (ROOT/'reports/E3_PUBLIC_WORKLOADS.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS qsort full ordering/multiset, dijkstra independent shortest paths, SHA-1 independent digest; same static ELF available to gem5')
if __name__=='__main__':main()
