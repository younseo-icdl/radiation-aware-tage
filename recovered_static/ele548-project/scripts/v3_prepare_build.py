import shutil,subprocess
from v3_common import *
pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9';target=ROOT/'third_party/gem5-costaware-v3'
if not target.exists():
 subprocess.run(['git','-C',ROOT/'third_party/gem5','worktree','add','--detach',target,pin],check=True)
 subprocess.run(['git','-C',target,'apply',ROOT/'reports/e3_integration/gem5_transport.patch'],check=True)
 for n in ['BPSEU.py','research_tage.hh','research_tage.cc']:shutil.copy2(ROOT/'gem5_ext'/n,target/'src/cpu/pred'/n)
assert subprocess.check_output(['git','-C',target,'rev-parse','HEAD'],text=True).strip()==pin
p=target/'src/cpu/pred/SConscript';s=p.read_text();extra="\nSimObject('BPCostAwareV3.py', sim_objects=['CostAwareV3TAGEBase','CostAwareV3TAGE'])\nSource('research_costaware_v3_tage.cc')\n"
if extra not in s:p.write_text(s+extra)
for p in (ROOT/'gem5_costaware_v3_ext').glob('*'):
 if p.is_file():shutil.copy2(p,target/'src/cpu/pred'/p.name)
for n in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:assert sha(target/'src/cpu/pred'/n)==sha(ROOT/'third_party/gem5/src/cpu/pred'/n)
files=list((ROOT/'src/costaware_v3').glob('*'))+list((ROOT/'gem5_costaware_v3_ext').glob('*'))+[ROOT/'gem5/o3_costaware_v3.py']
write(OUT/'configs/source_A.lock.json',dict(status='PREPARED_NOT_SIMULATED',pin=pin,sources={str(p.relative_to(ROOT)):sha(p) for p in files if p.is_file()},upstream_TAGE_unchanged=True,previous_producer_untouched=True))
