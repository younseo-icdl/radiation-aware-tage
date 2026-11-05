"""Create an additive pinned gem5 producer; never mutate earlier trees."""
from v5_common import *
import shutil,subprocess
target=ROOT/'third_party/gem5-rate-state-v5'
prior=ROOT/'third_party/gem5-postv3'
pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
if not target.exists():subprocess.run(['git','-C',ROOT/'third_party/gem5','worktree','add','--detach',target,pin],check=True,stdout=subprocess.DEVNULL)
assert subprocess.check_output(['git','-C',target,'rev-parse','HEAD'],text=True).strip()==pin
names=['cpu/o3/cpu.hh','cpu/o3/commit.cc','cpu/o3/bac.hh','cpu/o3/fetch.cc','cpu/o3/fetch.hh','cpu/pred/bpred_unit.hh','cpu/pred/conditional.hh','cpu/pred/SConscript','cpu/pred/BPSEU.py','cpu/pred/research_tage.hh','cpu/pred/research_tage.cc']
for name in names:shutil.copy2(prior/'src'/name,target/'src'/name)
for p in (ROOT/'gem5_rate_state_v5_ext').iterdir():
    if p.is_file():shutil.copy2(p,target/'src/cpu/pred'/p.name)
sc=target/'src/cpu/pred/SConscript';s=sc.read_text()
s=s.replace("SimObject('BPRoundBV3.py', sim_objects=['RoundBV3TAGEBase','RoundBV3TAGE'])","SimObject('BPRateStateV5.py', sim_objects=['RateStateV5TAGEBase', 'RateStateV5TAGE'])")
s=s.replace("Source('research_roundb_v3_tage.cc')","Source('research_rate_state_v5_tage.cc')")
# Fail closed if the inherited registration syntax changes.
assert 'BPRateStateV5.py' in s and "Source('research_rate_state_v5_tage.cc')" in s
sc.write_text(s)
h=target/'src/cpu/pred/tage_base.hh';s=h.read_text()
s=s.replace('    void updateGHist(', '    virtual void updateGHist(').replace('    void restoreHistState(', '    virtual void restoreHistState(')
s=s.replace('    void recordHistState(', '    virtual void recordHistState(')
assert 'virtual void updateGHist(' in s and 'virtual void restoreHistState(' in s
h.write_text(s)
if not (target/'build/X86_STAGE0').exists():
    (target/'build').mkdir(exist_ok=True)
    subprocess.run(['cp','-a','--reflink=auto',prior/'build/X86_STAGE0',target/'build/'],check=True)
write(OUT/'configs/source.lock.json',dict(status='PREPARED_NOT_CPU_GATED',pin=pin,
    parent_lock_sha256=sha(ROOT/'postv3/runtime/configs/PRODUCER.lock.json'),
    sources={str(p.relative_to(ROOT)):sha(p) for folder in ['src/rate_state_v5','src/rate_state_v5_support','gem5_rate_state_v5_ext'] for p in (ROOT/folder).glob('*') if p.is_file()},
    config_sha256=sha(ROOT/'gem5/o3_rate_state_v5.py'),
    transport={n:sha(target/'src'/n) for n in names+['cpu/pred/tage_base.hh','cpu/pred/tage_base.cc']},
    base_algorithm_change='Two existing history methods made virtual for bounded raw ring implementation. Table/provider/training source unchanged.'))
print('New isolated v5 producer prepared',flush=True)
