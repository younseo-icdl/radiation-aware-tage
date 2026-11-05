import subprocess,shutil
from v3_common import *
pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9';target=ROOT/'third_party/gem5-costaware-v3-b'
if not target.exists():
 subprocess.run(['git','-C',ROOT/'third_party/gem5','worktree','add','--detach',target,pin],check=True)
 subprocess.run(['git','-C',target,'apply',ROOT/'reports/e3_integration/gem5_transport.patch'],check=True)
 for n in ['BPSEU.py','research_tage.hh','research_tage.cc']:shutil.copy2(ROOT/'gem5_ext'/n,target/'src/cpu/pred'/n)
p=target/'src/cpu/pred/SConscript';s=p.read_text();addition="\nSimObject('BPRoundBV3.py', sim_objects=['RoundBV3TAGEBase','RoundBV3TAGE'])\nSource('research_roundb_v3_tage.cc')\n"
if addition not in s:p.write_text(s+addition)
for p in (ROOT/'gem5_costaware_v3_b_ext').glob('*'):
 if p.is_file():shutil.copy2(p,target/'src/cpu/pred'/p.name)
p=target/'src/cpu/pred/conditional.hh';s=p.read_text();tag='    virtual bool seuCanRetire(ThreadID, void*) { return true; }\n    virtual void seuReserveRetire(ThreadID, void*) {}\n'
if tag not in s:s=s.replace('    virtual bool seuFrontendBlocked',tag+'    virtual bool seuFrontendBlocked');p.write_text(s)
p=target/'src/cpu/pred/bpred_unit.hh';s=p.read_text();tag='''    bool seuCanRetire(ThreadID tid, InstSeqNum sn) {
        for(auto* h:predHist[tid])if(h->seqNum==sn)return cPred->seuCanRetire(tid,h->bpHistory);
        return true;
    }
    void seuReserveRetire(ThreadID tid, InstSeqNum sn) {
        for(auto* h:predHist[tid])if(h->seqNum==sn){cPred->seuReserveRetire(tid,h->bpHistory);return;}
    }
'''
if tag not in s:s=s.replace('    bool seuFrontendBlocked',tag+'    bool seuFrontendBlocked');p.write_text(s)
p=target/'src/cpu/o3/bac.hh';s=p.read_text();tag='''    bool seuCanRetire(ThreadID tid, InstSeqNum sn) { return bpu->seuCanRetire(tid,sn); }
    void seuReserveRetire(ThreadID tid, InstSeqNum sn) { bpu->seuReserveRetire(tid,sn); }
'''
if tag not in s:s=s.replace('    enum BACStatus',tag+'    enum BACStatus');p.write_text(s)
p=target/'src/cpu/o3/cpu.hh';s=p.read_text();tag='''    bool predictorCanRetire(ThreadID tid, InstSeqNum sn) { return bac.seuCanRetire(tid,sn); }
    void predictorReserveRetire(ThreadID tid, InstSeqNum sn) { bac.seuReserveRetire(tid,sn); }
'''
if tag not in s:s=s.replace('    friend class ThreadContext;', '    friend class ThreadContext;\n public:\n'+tag);p.write_text(s)
p=target/'src/cpu/o3/commit.cc';s=p.read_text();tag='''    if (head_inst->isControl() && head_inst->isExecuted() && head_inst->getFault()==NoFault &&
        !cpu->predictorCanRetire(tid,head_inst->seqNum)) return false;
'''
needle='    ThreadID tid = head_inst->threadNumber;'
# Modify only commitHead, not other functions sharing the tid line.
a=s.index('Commit::commitHead(');b=s.index('void\nCommit::getInsts()',a);part=s[a:b]
if tag not in part:
 part=part.replace(needle,needle+'\n'+tag,1)
 part=part.replace('    updateComInstStats(head_inst);','    if(head_inst->isControl())cpu->predictorReserveRetire(tid,head_inst->seqNum);\n    updateComInstStats(head_inst);',1)
 s=s[:a]+part+s[b:];p.write_text(s)
for name in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:assert sha(target/'src/cpu/pred'/name)==sha(ROOT/'third_party/gem5/src/cpu/pred'/name)
files=[ROOT/'src/costaware_v3/finite_fifo.hpp',ROOT/'src/costaware_v3/ready_credits.hpp',ROOT/'src/costaware_v3/protected_counter.hpp']+list((ROOT/'src/costaware_v3_roundb').glob('*'))+list((ROOT/'gem5_costaware_v3_b_ext').glob('*'))+[ROOT/'gem5/o3_costaware_v3_B.py']
write(OUT/'configs/source_B.lock.json',dict(status='PREPARED_GATE_PENDING',pin=pin,sources={str(p.relative_to(ROOT)):sha(p) for p in files if p.is_file()},transport_hashes={str(p.relative_to(ROOT)):sha(p) for p in [target/'src/cpu/o3/cpu.hh',target/'src/cpu/o3/commit.cc',target/'src/cpu/o3/bac.hh',target/'src/cpu/pred/bpred_unit.hh',target/'src/cpu/pred/conditional.hh']},pinned_TAGE_algorithm_unchanged=True))
