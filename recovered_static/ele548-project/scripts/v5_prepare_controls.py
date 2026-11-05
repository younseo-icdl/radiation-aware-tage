"""Two new public controls from the already hash-verified MiBench archive.

Deterministic bitcount driver and explicit basicmath LP64 port; not official scores.
"""
from v5_common import *
import shutil,subprocess,math,re
src=OUT/'sources/controls';src.mkdir(exist_ok=False)
original=ROOT/'third_party/mibench-v5-controls/automotive'
cc=ROOT/'.local/musl-1.2.6/bin/musl-gcc'
items=[]
bit=src/'bitcount';bit.mkdir()
driver=bit/'driver.c'
driver.write_text('''#include <stdio.h>
#include <stdint.h>
#include <limits.h>
#include "bitops.h"
static int shift_count(long x){int n=0;for(unsigned j=0;x&&j<sizeof(long)*CHAR_BIT;++j,x>>=1)n+=x&1;return n;}
int main(int argc,char**argv){
 if(argc!=2)return 81;FILE*f=fopen(argv[1],"r");if(!f)return 82;
 unsigned n,seed;if(fscanf(f,"%u %u",&n,&seed)!=2||!n||n>1000000)return 83;fclose(f);
 int(*fn[])(long)={bit_count,bitcount,ntbl_bitcnt,ntbl_bitcount,BW_btbl_bitcount,AR_btbl_bitcount,shift_count};
 for(unsigned k=0;k<7;++k){unsigned long total=0;uint32_t x=seed&0x7fffffff;
  for(unsigned j=0;j<n;++j){total+=fn[k](x);x=(x+13)&0x7fffffff;}
  printf("%u %lu\\n",k,total);
 }return 0;
}
''')
binary=bit/'bitcount_det';files=[original/'bitcount'/f'bitcnt_{i}.c' for i in [1,2,3,4]]
r=timed([cc,'-O2','-static','-fno-pie','-no-pie','-I',original/'bitcount',driver,*files,'-o',binary],bit/'build.log');assert r['exit_code']==0,r
input=OUT/'inputs/bitcount.holdout.dat';input.write_text('4096 123456789\n');native=bit/'native.stdout';r=timed([binary,input],native);assert r['exit_code']==0
total=sum(((123456789+13*j)&0x7fffffff).bit_count() for j in range(4096));assert native.read_text()==''.join(f'{k} {total}\n' for k in range(7))
items.append(dict(name='bitcount_det',binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),input=str(input.relative_to(ROOT)),input_sha256=sha(input),native_stdout_sha256=sha(native),native_stdout=str(native.relative_to(ROOT)),
    independent_answer='Python bit_count for every deterministic operand and all7kernel totals',source='original MiBench bitcnt_1..4 kernels; new clock-free deterministic driver, 31bit nonnegative operands'))
mathdir=src/'basicmath';shutil.copytree(original/'basicmath',mathdir)
sqrt=mathdir/'isqrt.c';text=sqrt.read_text()
# Historical routine assumed 32bit long and 16bit unsigned struct fields.
# Preserve its restoring-root algorithm, make input shifts explicit uint32,
# and extract integer/fraction fields explicitly rather than memcpy layout.
text='#include <stdint.h>\n'+text
text=text.replace('unsigned long a =','uint64_t a =').replace('unsigned long r =','uint64_t r =').replace('unsigned long e =','uint64_t e =')
text=text.replace('      int i;','      int i;\n      uint32_t x32=(uint32_t)x;',1)
text=text.replace('TOP2BITS(x); x <<= 2;','TOP2BITS(x32); x32 <<= 2;').replace('memcpy(q, &a, sizeof(long));','q->sqrt=(unsigned)(a>>16); q->frac=(unsigned)(a&0xffff);')
sqrt.write_text(text)
binary=mathdir/'basicmath_lp64';files=[mathdir/f for f in ['basicmath_small.c','rad2deg.c','cubic.c','isqrt.c']]
r=timed([cc,'-O2','-static','-fno-pie','-no-pie','-include','stdio.h',*files,'-lm','-o',binary],mathdir/'build.log');assert r['exit_code']==0,r
input=OUT/'inputs/basicmath.fixed.dat';input.write_text('fixed published MiBench coefficient and angle ranges; argv ignored\n');native=mathdir/'native.stdout';r=timed([binary,input],native);assert r['exit_code']==0
lines=native.read_text().splitlines();solutions=[list(map(float,line.split(':')[1].split())) for line in lines if line.startswith('Solutions:')]
coeff=[(1.,-10.5,32.,-30.),(1.,-4.5,17.,-30.),(1.,-3.5,22.,-31.),(1.,-13.7,1.,-35.)]
coeff += [(float(a),float(b),5+.5*c,float(d)) for a in range(1,10) for b in range(10,0,-1) for c in range(20) for d in range(-1,-11,-1)]
assert len(solutions)==len(coeff)==18004
for roots,(a,b,c,d) in zip(solutions,coeff):
 assert len(roots) in [1,3]
 for x in roots:
  eps=5.1e-7;bound=eps*(3*abs(a)*(abs(x)+eps)**2+2*abs(b)*(abs(x)+eps)+abs(c))+1e-7
  assert abs(((a*x+b)*x+c)*x+d)<=bound,('CUBIC_RESIDUAL',a,b,c,d,x)
seen=0
for line in lines:
 m=re.fullmatch(r'sqrt\(\s*(\d+)\) =\s*(\d+)',line)
 if m:assert int(m[2])==math.isqrt(int(m[1]));seen+=1
 m=re.fullmatch(r'(\s*\d+) degrees = ([\d.]+) radians',line)
 if m:assert abs(float(m[2])-math.radians(float(m[1])))<1e-11
 m=re.fullmatch(r'([\d.]+) radians =\s*(\d+) degrees',line)
 if m:assert abs(float(m[2])-math.degrees(float(m[1])))<1e-8
assert seen==1001
m=next(re.fullmatch(r'sqrt\(([A-F0-9]+)\) = ([A-F0-9]+)',x) for x in lines if 'sqrt(3FED0169)' in x)
assert int(m[2],16)==math.isqrt(int(m[1],16))
items.append(dict(name='basicmath_lp64',binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),input=str(input.relative_to(ROOT)),input_sha256=sha(input),native_stdout_sha256=sha(native),native_stdout=str(native.relative_to(ROOT)),
    independent_answer='All18004printed cubic solution sets checked by polynomial residual at output precision; all1002isqrt outputs vs Python isqrt; all printed angle conversions vs Python math',
    source='MiBench basicmath_small with explicit LP64 restoring-isqrt port; fixed standard coefficient set, no official score'))
write(OUT/'configs/control_inputs.lock.json',dict(status='NATIVE_INDEPENDENT_ANSWERS_PASS_NOT_CPU_EVALUATED',programs=items,
    archive='third_party/downloads/mibench-automotive.tar.gz',archive_sha256=sha(ROOT/'third_party/downloads/mibench-automotive.tar.gz'),
    license='Original extracted LICENSE: FREE with no restrictions, retained locally',
    scope='Two extra held-out program kernels; no CPU results used to select taps/resource candidates. Derived drivers/LP64 changes disclosed.'))
print('PASS two public MiBench-derived controls, deterministic native answers independently checked')
