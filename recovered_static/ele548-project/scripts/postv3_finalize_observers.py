"""Apply final observer counters only after the preceding build has stopped."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'postv3/runtime'
shutil.copyfile(OUT/'configs/source.lock.json',OUT/'configs/source_BUILD2.lock.json')
p=ROOT/'src/postv3/history_access.hpp';s=p.read_text()
assert 'observation_training_calls' not in s
s=s.replace(' public:\n',' public:\n uint64_t observation_training_calls=0,observation_allocation_requests=0;\n void condBranchUpdate(gem5::ThreadID tid,gem5::Addr pc,bool taken,Base::BranchInfo*bi,int nrand,gem5::Addr target,bool pred,bool pre=false)override{++observation_training_calls;Base::condBranchUpdate(tid,pc,taken,bi,nrand,target,pred,pre);}\n',1)
s=s.replace('  bool all=true;', '  if(alloc)++observation_allocation_requests;\n  bool all=true;')
p.write_text(s)
p=ROOT/'gem5_postv3_ext/research_roundb_v3_tage.hh';s=p.read_text().replace('uint64_t audit_predictions=0,audit_inflight=0;', 'uint64_t audit_predictions=0,audit_inflight=0,observed_squash_calls=0,observed_correct_calls=0;');p.write_text(s)
p=ROOT/'gem5_postv3_ext/research_roundb_v3_tage.cc';s=p.read_text()
s=s.replace('maintenance_calls,drain_calls,retire_calls\\n','maintenance_calls,drain_calls,retire_calls,training_calls,allocation_requests,squash_calls,correction_calls\\n')
s=s.replace('void CpuRoundBV3TAGEBase::dumpSeu(){','void CpuRoundBV3TAGEBase::dumpSeu(){\n    phase("PROGRAM_END","RIGHT_CENSOR_MARKER");')
s=s.replace('assert(history);auto* info=static_cast<CpuInfo*>(history);\n    auto detected=', 'assert(history);if(squashed)++core.observed_correct_calls;auto* info=static_cast<CpuInfo*>(history);\n    auto detected=',1)
s=s.replace('void CpuRoundBV3TAGE::squash(gem5::ThreadID tid,void*& history){','void CpuRoundBV3TAGE::squash(gem5::ThreadID tid,void*& history){\n    ++core.observed_squash_calls;')
p.write_text(s)
p=ROOT/'gem5_postv3_ext/postv3_audit.inc';s=p.read_text().replace("<<retire_block_cycles<<'\\n';", "<<retire_block_cycles<<','<<observation_training_calls<<','<<observation_allocation_requests<<','<<observed_squash_calls<<','<<observed_correct_calls<<'\\n';");p.write_text(s)
print('Final read-only observers added; production policies still differ only in safe static promotion grouping')
