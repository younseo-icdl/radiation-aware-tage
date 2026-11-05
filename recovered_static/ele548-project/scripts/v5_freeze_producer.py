"""Freeze actual successfully built sources before dispatching CPU correctness gates."""
from v5_common import *
import subprocess,sys
import argparse
p=argparse.ArgumentParser();p.add_argument("--build",type=int,default=4);attempt=p.parse_args().build
assert 'scons: done building targets.' in (OUT/f'reports/BUILD_{attempt}.log').read_text()
assert len((OUT/f'reports/BUILD_{attempt}.time').read_text().splitlines())==1
for p in ['CPP_R2_correctness.log','CPP_R2_META_FIX1.log']:
 assert (OUT/'reports'/p).read_text().startswith('PASS'),p
prior=json.loads((OUT/'configs/source.lock.json').read_text())
changes=[name for name,digest in prior['sources'].items() if sha(ROOT/name)!=digest]
assert not [n for n in changes if n.startswith('gem5_rate_state_v5_ext/') or n.endswith('representation.hpp')],('PRODUCER_MUTATED_DURING_BUILD',changes)
target=ROOT/'third_party/gem5-rate-state-v5'
sources={str(p.relative_to(ROOT)):sha(p) for folder in ['src/rate_state_v5','src/rate_state_v5_support','gem5_rate_state_v5_ext'] for p in (ROOT/folder).glob('*') if p.is_file()}
transport={n:sha(target/'src'/n) for n in prior['transport']}
for p in (ROOT/'gem5_rate_state_v5_ext').iterdir():
 if p.is_file():assert sha(p)==sha(target/'src/cpu/pred'/p.name),p
write(OUT/'configs/source.lock.json',dict(status='BUILT_FROZEN_BEFORE_CPU_GATE',pin=prior['pin'],sources=sources,transport=transport,
 parent_lock_sha256=prior['parent_lock_sha256'],config_sha256=sha(ROOT/'gem5/o3_rate_state_v5.py'),
 implementation='Three existing history primitives virtualized. Exact direct/sparse bounded raw journal; finite deferred journal source publication; upstream table/provider/training preserved.',
 build_log_sha256=sha(OUT/f'reports/BUILD_{attempt}.log'),binary_sha256=sha(target/'build/X86_STAGE0/gem5.opt'),
 changes_since_prepare_nonproducer=changes,failed_builds=['BUILD_1_PREFLIGHT_STOP.json','BUILD_2.log','BUILD_3.log'],
 source_freeze='No production code modifications allowed while running this producer or its CPU evaluation.'))
sys.path.insert(0,str(ROOT/'rate_state_v5/handoff/BP_SEU_Rate_State_Research_Handoff_v5/tools'))
import labctl
state=json.loads((OUT/'STATE.json').read_text())
for taskid,evidence,decision,next_action in [
 ('S0',[OUT/'reports/S0_ACCEPTANCE.json',OUT/'configs/protocol.lock.json'],'Prior producer exact regression; new namespace and budget frozen','Two axes'),
 ('A0',[OUT/'RATE_ANCHORS_AUDIT.json'],'Rate evidence audited; source-device conditional arithmetic only, missing spectrum/FF calibration documented','Conditional and stress experiments'),
 ('B0',[OUT/'reports/CPP_R2_correctness.log',OUT/'reports/CPP_R2_META_FIX1.log'],'Exact direct clean/speculative/deferred-publication gates pass','CPU gate and finite cost envelope')]:
 if next(t for t in state['tasks'] if t['id']==taskid)['status']!='completed':labctl.record(OUT,taskid,'completed',evidence,decision,next_action)
print('PASS actual successful build/source/transport frozen before CPU gate')
