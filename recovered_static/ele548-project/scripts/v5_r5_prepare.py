"""Add bounded BPU undo packets while preserving the immutable R4 producer."""
from v5_common import ROOT,sha,write
from pathlib import Path
import shutil,os,json
OUT=ROOT/'rate_state_v5/runtime_r5';target=ROOT/'third_party/gem5-rate-state-v5'
old=ROOT/'rate_state_v5/runtime/configs/PRODUCER.lock.json';moved=json.loads((old.parent/'PRODUCER.relocation.json').read_text())
assert sha(old)==moved['original_lock_sha256'] and sha(ROOT/moved['binary'])==moved['binary_sha256']
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:assert (p/'exe').resolve()!=target/'build/X86_STAGE0/gem5.opt','Old mutable build output still executing'
 except (OSError,RuntimeError):pass
for name in ['conditional.hh','bpred_unit.cc']:
 shutil.copy2(OUT/'sources/R4_TRANSPORT/cpu/pred'/name,target/'src/cpu/pred'/name)
path=target/'src/cpu/pred/conditional.hh';s=path.read_text();needle='    virtual void seuAuditCommit('
assert s.count(needle)==1;s=s.replace(needle,'    virtual void seuSquashBegin(ThreadID) {}\n    virtual void seuSquashEnd(ThreadID) {}\n'+needle);path.write_text(s)
path=target/'src/cpu/pred/bpred_unit.cc';s=path.read_text();start=s.index('BPredUnit::squash(const InstSeqNum &squashed_sn, ThreadID tid)');end=s.index('BPredUnit::squashHistory(',start)
piece=s[start:end];left=piece.index('{')+1;right=piece.rfind('}')
piece=piece[:left]+'\n    cPred->seuSquashBegin(tid);'+piece[left:right]+'    cPred->seuSquashEnd(tid);\n'+piece[right:];s=s[:start]+piece+s[end:]
# The resolved branch's inverse restore follows the inner squash loop. Keep
# both overloads in one nested boundary and flush before its corrected append.
start=s.index('BPredUnit::squash(const InstSeqNum &squashed_sn,\n');end=s.index('\nvoid\n',start)
piece=s[start:end];left=piece.index('{')+1;right=piece.rfind('}')
piece=piece[:left]+'\n    cPred->seuSquashBegin(tid);'+piece[left:right]+'    cPred->seuSquashEnd(tid);\n'+piece[right:];s=s[:start]+piece+s[end:];path.write_text(s)
for p in (ROOT/'gem5_rate_state_v5_r5_ext').iterdir():
 if p.is_file():shutil.copy2(p,target/'src/cpu/pred'/p.name)
prior=json.loads((ROOT/'rate_state_v5/runtime/configs/source.lock.json').read_text())
transport={n:sha(target/'src'/n) for n in list(prior['transport'])+['cpu/pred/bpred_unit.cc']}
write(OUT/'configs/source.lock.json',dict(status='PREPARED_NOT_CPU_GATED',pin=prior['pin'],R4_parent_source_lock_sha256=sha(ROOT/'rate_state_v5/runtime/configs/source.lock.json'),
 sources={str(p.relative_to(ROOT)):sha(p) for folder in ['src/rate_state_v5_r5','src/rate_state_v5_r5_support','gem5_rate_state_v5_r5_ext'] for p in (ROOT/folder).glob('*') if p.is_file()},transport=transport,
 config='gem5/o3_rate_state_v5_r5.py',config_sha256=sha(ROOT/'gem5/o3_rate_state_v5_r5.py'),
 change='Explicit begin/end around actual BPU squash; one aggregate rewind count/last-path packet, finite L2 service; fixed table/provider/RNG/update rules.',
 BPU_contract='Decoded invalidation span and oldest saved path available at end of existing squash boundary; valid-span reduction and one checkpoint path-read port required externally; existing BPU ownership fault exclusions retained. Not unlimited serial metadata RMWs or a hidden shadow.'))
print('R5 prepared; R4 source/config/binary snapshot unchanged')
