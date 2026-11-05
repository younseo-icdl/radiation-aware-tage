"""Separate worktree, preserving every in-flight B producer byte."""
import subprocess,shutil
from v3_common import *
target=ROOT/'third_party/gem5-costaware-v3-c';prior=ROOT/'third_party/gem5-costaware-v3-b';pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
if not target.exists():subprocess.run(['git','-C',ROOT/'third_party/gem5','worktree','add','--detach',target,pin],check=True)
else:assert subprocess.check_output(['git','-C',target,'rev-parse','HEAD'],text=True).strip()==pin
for name in ['cpu/o3/cpu.hh','cpu/o3/commit.cc','cpu/o3/bac.hh','cpu/o3/fetch.cc','cpu/o3/fetch.hh','cpu/pred/bpred_unit.hh','cpu/pred/conditional.hh','cpu/pred/SConscript','cpu/pred/BPSEU.py','cpu/pred/research_tage.hh','cpu/pred/research_tage.cc']:
 shutil.copy2(prior/'src'/name,target/'src'/name)
for p in (ROOT/'gem5_costaware_v3_c_ext').iterdir():
 if p.is_file():shutil.copy2(p,target/'src/cpu/pred'/p.name)
if not (target/'build/X86_STAGE0').exists():
 subprocess.run(['mkdir','-p',target/'build'],check=True)
 subprocess.run(['cp','-a','--reflink=auto',prior/'build/X86_STAGE0',target/'build/'],check=True)
for n in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:assert sha(target/'src/cpu/pred'/n)==sha(ROOT/'third_party/gem5/src/cpu/pred'/n)
shared=json.loads((OUT/'configs/source_B.lock.json').read_text())
files=[p for p in shared['sources'] if p.startswith('src/')]+[str(p.relative_to(ROOT)) for p in (ROOT/'gem5_costaware_v3_c_ext').iterdir() if p.is_file()]+['gem5/o3_costaware_v3_C.py']
transport=list(shared['transport_hashes'])+[str((prior/'src/cpu/o3'/n).relative_to(ROOT)) for n in ['fetch.cc','fetch.hh']]+[str((prior/'src/cpu/pred/SConscript').relative_to(ROOT))]
for p in transport:assert sha(ROOT/p)==sha(target/Path(p).relative_to(prior.relative_to(ROOT))),('MISSING_TRANSPORT',p)
write(OUT/'configs/source_C.lock.json',dict(status='PREPARED_GATE_PENDING',pin=pin,sources={p:sha(ROOT/p) for p in files},transport_hashes={str((target/Path(p).relative_to(prior.relative_to(ROOT))).relative_to(ROOT)):sha(target/Path(p).relative_to(prior.relative_to(ROOT))) for p in transport},fix='Staged metadata validated before pre-ROB retirement classification; direct refill invariant, CSV flush at actual exit',parent_B_source_sha256=sha(OUT/'configs/source_B.lock.json'),pinned_TAGE_algorithm_unchanged=True))
