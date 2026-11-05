from continuation_common import *
import shutil
PIN='c8222cc67a399bfc01e8658dd14b30d5bfd634f9';target=ROOT/'third_party/gem5-continuation'
if not target.exists():
 subprocess.run(['git','-C',str(ROOT/'third_party/gem5'),'worktree','add','--detach',str(target),PIN],check=True)
 subprocess.run(['git','-C',str(target),'apply',str(ROOT/'reports/e3_integration/gem5_transport.patch')],check=True)
 for name in ['BPSEU.py','research_tage.hh','research_tage.cc']:shutil.copy2(ROOT/'gem5_ext'/name,target/'src/cpu/pred'/name)
assert subprocess.check_output(['git','-C',str(target),'rev-parse','HEAD'],text=True).strip()==PIN
p=target/'src/cpu/pred/SConscript';s=p.read_text();addition="\nSimObject('BPContinuation.py', sim_objects=['ContinuationTAGEBase','ContinuationTAGE'])\nSource('research_continuation_tage.cc')\n"
if addition not in s:p.write_text(s+addition)
for name in ['BPContinuation.py','research_continuation_tage.hh','research_continuation_tage.cc']:shutil.copy2(ROOT/'gem5_continuation_ext'/name,target/'src/cpu/pred'/name)
for name in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:assert sha(target/'src/cpu/pred'/name)==sha(ROOT/'third_party/gem5/src/cpu/pred'/name)
files=list((ROOT/'src/continuation').glob('*.hpp'))+list((ROOT/'gem5_continuation_ext').glob('*'))+[ROOT/'gem5/o3_continuation.py']
write(OUT/'configs/gem5_source.lock.json',dict(status='PREPARED_GATE_PENDING',pin=PIN,worktree=str(target),sources={str(p.relative_to(ROOT)):sha(p) for p in files},upstream_TAGE_unchanged=True,old_producers_preserved=True))
