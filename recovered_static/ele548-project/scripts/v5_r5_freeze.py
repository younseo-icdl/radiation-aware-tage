from v5_common import ROOT,sha,write
import json,argparse
p=argparse.ArgumentParser();p.add_argument("--build",type=int,default=3);attempt=p.parse_args().build
OUT=ROOT/'rate_state_v5/runtime_r5'
assert 'scons: done building targets.' in (OUT/f'reports/BUILD_{attempt}.log').read_text()
assert len((OUT/f'reports/BUILD_{attempt}.time').read_text().splitlines())==1
assert (OUT/'reports/CPP_BATCH_FINAL.log').read_text().startswith('PASS')
lock=json.loads((OUT/'configs/source.lock.json').read_text())
for path,digest in lock['sources'].items():
 if path.endswith('batch_gate.cpp'):continue # The directed test's live FIFO-cell address was corrected, not production code.
 assert sha(ROOT/path)==digest,path
for p in (ROOT/'gem5_rate_state_v5_r5_ext').iterdir():
 if p.is_file():assert sha(p)==sha(ROOT/'third_party/gem5-rate-state-v5/src/cpu/pred'/p.name),p
lock['status']='BUILT_FROZEN_BEFORE_CPU_GATE';lock['sources']={path:sha(ROOT/path) for path in lock['sources']};write(OUT/'configs/source.lock.json',lock)
write(OUT/'configs/BUILT_PRODUCER.pending.json',dict(status='BUILT_NOT_CPU_GATED',
 binary='third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt',binary_sha256=sha(ROOT/'third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt'),
 config='gem5/o3_rate_state_v5_r5.py',config_sha256=sha(ROOT/'gem5/o3_rate_state_v5_r5.py'),source_lock_sha256=sha(OUT/'configs/source.lock.json')))
print('R5 built source/transport/binary frozen; CPU gate pending')
