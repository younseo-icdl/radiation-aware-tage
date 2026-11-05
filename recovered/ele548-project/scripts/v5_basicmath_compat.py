"""One explicit workload compatibility port; frozen original evidence untouched."""
from v5_common import *
import shutil,math,re,argparse
ap=argparse.ArgumentParser();ap.add_argument('--integer-io',action='store_true');args=ap.parse_args()
name='basicmath_sseio' if args.integer_io else 'basicmath_double'
old=OUT/'sources/controls/basicmath';out=OUT/'sources/controls'/name
assert not out.exists();shutil.copytree(old,out)
p=out/'cubic.c';s=p.read_text();assert 'long double' in s;p.write_text(s.replace('long double','double'))
if args.integer_io:
 p=out/'basicmath_small.c';s=p.read_text()
 helper='''
static void fixed(double x,unsigned digits){
 unsigned long long scale=digits==6?1000000ULL:1000000000000ULL;
 unsigned long long value=(unsigned long long)(fabs(x)*(double)scale+0.5);
 printf("%s%llu.%0*llu",x<0?"-":"",value/scale,(int)digits,value%scale);
}
'''
 s=s.replace('int main(void)',helper+'\nint main(void)')
 assert s.count('printf(" %f",x[i]);')==5
 s=s.replace('printf(" %f",x[i]);','{ putchar(32); fixed(x[i],6); }')
 s=s.replace('printf("%3.0f degrees = %.12f radians\\n", X, deg2rad(X));','{ printf("%3d degrees = ",(int)(X+0.5)); fixed(deg2rad(X),12); puts(" radians"); }')
 s=s.replace('printf("%.12f radians = %3.0f degrees\\n", X, rad2deg(X));','{ fixed(X,12); printf(" radians = %3d degrees\\n",(int)(rad2deg(X)+0.5)); }')
 assert '%f' not in s and '%.12f' not in s;p.write_text(s)
binary=out/name;cc=ROOT/'.local/musl-1.2.6/bin/musl-gcc'
with trial_slot():
 r=timed([cc,'-O2','-static','-fno-pie','-no-pie','-mfpmath=sse','-msse2','-include','stdio.h',*[out/f for f in ['basicmath_small.c','rad2deg.c','cubic.c','isqrt.c']],'-lm','-o',binary],out/'compat_build.log');assert r['exit_code']==0
 native=out/'double.native.stdout';input=OUT/'inputs/basicmath.fixed.dat';r=timed([binary,input],native);assert r['exit_code']==0
lines=native.read_text().splitlines();solutions=[list(map(float,x.split(':')[1].split())) for x in lines if x.startswith('Solutions:')]
coeff=[(1.,-10.5,32.,-30.),(1.,-4.5,17.,-30.),(1.,-3.5,22.,-31.),(1.,-13.7,1.,-35.)]+[(float(a),float(b),5+.5*c,float(d)) for a in range(1,10) for b in range(10,0,-1) for c in range(20) for d in range(-1,-11,-1)]
assert len(coeff)==len(solutions)==18004
for roots,(a,b,c,d) in zip(solutions,coeff):
 assert len(roots) in [1,3]
 for x in roots:
  eps=5.1e-7;bound=eps*(3*abs(a)*(abs(x)+eps)**2+2*abs(b)*(abs(x)+eps)+abs(c))+1e-7
  assert math.isfinite(x) and abs(((a*x+b)*x+c)*x+d)<=bound
seen=0
for line in lines:
 m=re.fullmatch(r'sqrt\(\s*(\d+)\) =\s*(\d+)',line)
 if m:assert int(m[2])==math.isqrt(int(m[1]));seen+=1
 m=re.fullmatch(r'(\s*\d+) degrees = ([\d.]+) radians',line)
 if m:assert abs(float(m[2])-math.radians(float(m[1])))<1e-11
 m=re.fullmatch(r'([\d.]+) radians =\s*(\d+) degrees',line)
 if m:assert abs(float(m[2])-math.degrees(float(m[1])))<1e-8
assert seen==1001
m=next(re.fullmatch(r'sqrt\(([A-F0-9]+)\) = ([A-F0-9]+)',x) for x in lines if 'sqrt(3FED0169)' in x);assert int(m[2],16)==math.isqrt(int(m[1],16))
item=dict(name=name,binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),input=str(input.relative_to(ROOT)),input_sha256=sha(input),native_stdout=str(native.relative_to(ROOT)),native_stdout_sha256=sha(native),
 source='Explicit binary64 cubic intermediate port of MiBench basicmath plus prior LP64 isqrt port. Different workload binary/name; original x87 unsupported fcomip/fsubr failures preserved.',
 independent_answer='All18004cubic polynomial residuals,1002isqrt,all angle conversions independently verified. gem5 must match full native output exactly.')
write(OUT/('configs/basicmath_sseio.lock.json' if args.integer_io else 'configs/basicmath_compat.lock.json'),dict(status='NATIVE_PASS_CPU_PENDING',program=item,attempt=2 if args.integer_io else 1,original_failure='Original binary80: unsupported fcomip/fsubr and checksum mismatch. Binary64-only fix: musl floating printf x87 path caused unmapped-stack write; no successful CPU performance claimed.',
   attempted_fix='Binary64 arithmetic plus integer-only fixed precision printing to bypass musl floating printf x87' if args.integer_io else 'long double intermediates -> explicit double; compile -mfpmath=sse -msse2; no simulator ISA emulation or predictor change',
   source_hashes={str(p.relative_to(ROOT)):sha(p) for p in out.glob('*') if p.suffix in ['.c','.h']}))
print('PASS binary64 port native; CPU exactness still pending')
