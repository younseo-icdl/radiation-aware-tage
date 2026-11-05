"""Prepare only the NEW v6 worktree; never mutate active v5 producers."""
from pathlib import Path
import json,shutil,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rate_state_v5_pipeline_v7/runtime'
TARGET=ROOT/'third_party/gem5-rate-pipeline-v6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert TARGET.name=='gem5-rate-pipeline-v6'
if not TARGET.exists():
 subprocess.run(['git','-C',ROOT/'third_party/gem5','worktree','add','--detach',TARGET,'c8222cc67a399bfc01e8658dd14b30d5bfd634f9'],check=True)
 parent=json.loads((ROOT/'rate_state_v5/runtime_r5/configs/source.lock.json').read_text())
 for name,digest in parent['transport'].items():
  source=ROOT/'third_party/gem5-rate-state-v5/src'/name;assert sha(source)==digest
  dest=TARGET/'src'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
 # The private overlay carries the actual six modified transport files.
 for source in (OUT/'sources/TRANSPORT').rglob('*'):
  if source.is_file():shutil.copy2(source,TARGET/'src'/source.relative_to(OUT/'sources/TRANSPORT'))
 sc=TARGET/'src/cpu/pred/SConscript'
 sc.write_text(sc.read_text().replace('BPRateStateV5','BPPipelineV7').replace('RateStateV5','PipelineV7').replace('research_rate_state_v5','research_pipeline_v7'))
 sc=TARGET/'src/SConscript';text=sc.read_text();assert "envs['opt'].Append(CCFLAGS=['-g']" in text
 sc.write_text(text.replace("envs['opt'].Append(CCFLAGS=['-g']","envs['opt'].Append(CCFLAGS=['-g0']"))
 cfg=TARGET/'build/X86_PIPELINE/gem5.build';cfg.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT/'third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.build/config',cfg/'config')
assert subprocess.check_output(['git','-C',TARGET,'rev-parse','HEAD'],text=True).strip()=='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:assert (p/'exe').resolve()!=TARGET/'build/X86_PIPELINE/gem5.opt','New producer still executing'
 except (OSError,RuntimeError):pass
assert not (OUT/'configs/PRODUCER.lock.json').exists(),'Frozen producer must not be rebuilt'
for p in (ROOT/'gem5_rate_pipeline_v7_ext').iterdir():
 if p.is_file():shutil.copy2(p,TARGET/'src/cpu/pred'/p.name)
transport=['cpu/pred/conditional.hh','cpu/pred/bpred_unit.hh','cpu/pred/bpred_unit.cc','cpu/o3/bac.hh','cpu/o3/fetch.hh','cpu/o3/fetch.cc']
snap=OUT/'sources/TRANSPORT'
for name in transport:
 p=snap/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(TARGET/'src'/name,p)
files=[p for folder in ['src/rate_pipeline_v7','gem5_rate_pipeline_v7_ext'] for p in (ROOT/folder).glob('*') if p.is_file()]
old=json.loads((ROOT/'rate_state_v5/runtime_r5/configs/source.lock.json').read_text())
data=dict(status='PREPARED_NOT_GATED',pin=old['pin'],sources={str(p.relative_to(ROOT)):sha(p) for p in files},
 transport={name:sha(TARGET/'src'/name) for name in old['transport']},
 build_debug_symbols=False,assertions=True,upstream_opt_sconscript_sha256=sha(TARGET/'src/SConscript'),
 config='gem5/o3_pipeline_v7.py',config_sha256=sha(ROOT/'gem5/o3_pipeline_v7.py'),
 base_R5_source_lock_sha256=sha(ROOT/'rate_state_v5/runtime_r5/configs/source.lock.json'),
 change='Finite address operands and actual delayed provider stage; separate request/response queues and tokens; coupled PC waits; common synchronous history maintenance for matched representation tests.')
(OUT/'configs/source.lock.json').write_text(json.dumps(data,indent=2)+'\n')
pres=OUT/'configs/PRESERVED_V5.lock.json'
if not pres.exists():
 names=['rate_state_v5/runtime_r5/configs/PRODUCER.lock.json','rate_state_v5/runtime_r5/configs/source.lock.json',
 'third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt','gem5/o3_rate_state_v5_r5.py']
 names+=['third_party/gem5-rate-state-v5/src/'+n for n in old['transport']]
 pres.write_text(json.dumps(dict(status='LOCKED_BEFORE_V6_BUILD',hashes={n:sha(ROOT/n) for n in names}),indent=2)+'\n')
print('NEW producer prepared; active R5 source/config/binary preserved')
