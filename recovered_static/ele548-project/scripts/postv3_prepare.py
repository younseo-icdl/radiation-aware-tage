"""Isolated producer; no old source, build or output may be changed."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'postv3/runtime'
target=ROOT/'third_party/gem5-postv3'
prior=ROOT/'third_party/gem5-costaware-v3-c'
pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
if not target.exists():
    subprocess.run(['git','-C',ROOT/'third_party/gem5','worktree','add','--detach',target,pin],check=True)
assert subprocess.check_output(['git','-C',target,'rev-parse','HEAD'],text=True).strip()==pin
names=['cpu/o3/cpu.hh','cpu/o3/commit.cc','cpu/o3/bac.hh','cpu/o3/fetch.cc','cpu/o3/fetch.hh',
       'cpu/pred/bpred_unit.hh','cpu/pred/conditional.hh','cpu/pred/SConscript','cpu/pred/BPSEU.py',
       'cpu/pred/research_tage.hh','cpu/pred/research_tage.cc']
for n in names:shutil.copy2(prior/'src'/n,target/'src'/n)
for p in (ROOT/'gem5_postv3_ext').iterdir():
    if p.is_file():shutil.copy2(p,target/'src/cpu/pred'/p.name)
path=target/'src/cpu/pred/conditional.hh'
s=path.read_text();needle='    virtual bool seuCanRetire('
assert s.count(needle)==1
s=s.replace(needle,'    virtual void seuAuditCommit(uint64_t,uint64_t,unsigned,bool,bool,void*) {}\n    virtual void seuAuditInflight(unsigned) {}\n'+needle)
path.write_text(s)
path=target/'src/cpu/pred/bpred_unit.hh';s=path.read_text()
s=s.replace('    bool seuCanRetire(ThreadID tid, InstSeqNum sn) {', '''    void seuAuditCommit(ThreadID tid,InstSeqNum sn,Addr pc,unsigned micro,bool last,bool control){
        void* info=nullptr;if(control)for(auto*h:predHist[tid])if(h->seqNum==sn){info=h->bpHistory;break;}
        cPred->seuAuditCommit(sn,pc,micro,last,control,info);
    }
    bool seuCanRetire(ThreadID tid, InstSeqNum sn) {''')
s=s.replace('return cPred->seuFrontendBlocked(tid, predHist[tid].empty());','cPred->seuAuditInflight(predHist[tid].size());return cPred->seuFrontendBlocked(tid, predHist[tid].empty());')
s=s.replace('return cPred->seuPredictionReady(tid, pc, conditional);','cPred->seuAuditInflight(predHist[tid].size());return cPred->seuPredictionReady(tid, pc, conditional);')
path.write_text(s)
for rel,needle,method in [
 ('cpu/o3/cpu.hh','    bool predictorCanRetire(', '    void predictorAuditCommit(ThreadID tid,InstSeqNum sn,Addr pc,unsigned micro,bool last,bool control){bac.seuAuditCommit(tid,sn,pc,micro,last,control);}\n'),
 ('cpu/o3/bac.hh','    bool seuCanRetire(', '    void seuAuditCommit(ThreadID tid,InstSeqNum sn,Addr pc,unsigned micro,bool last,bool control){bpu->seuAuditCommit(tid,sn,pc,micro,last,control);}\n')]:
    path=target/'src'/rel;s=path.read_text();assert s.count(needle)==1;s=s.replace(needle,method+needle);path.write_text(s)
path=target/'src/cpu/o3/commit.cc';s=path.read_text();needle='    // Return true to indicate that we have committed an instruction.'
assert s.count(needle)==1
s=s.replace(needle,'''    cpu->predictorAuditCommit(tid,head_inst->seqNum,head_inst->pcState().instAddr(),head_inst->pcState().microPC(),!head_inst->isMicroop()||head_inst->isLastMicroop(),head_inst->isControl());
'''+needle);path.write_text(s)
if not (target/'build/X86_STAGE0').exists():
    (target/'build').mkdir(exist_ok=True)
    subprocess.run(['cp','-a','--reflink=auto',prior/'build/X86_STAGE0',target/'build/'],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:
    assert sha(target/'src/cpu/pred'/n)==sha(prior/'src/cpu/pred'/n)
sources=list((ROOT/'src/postv3').glob('*'))+list((ROOT/'gem5_postv3_ext').glob('*'))+[ROOT/'gem5/o3_postv3.py']
lock=dict(status='PREPARED_NOT_YET_CPU_GATED',pin=pin,parent_source_lock_sha256=sha(ROOT/'continuation_v3/runtime/configs/source_C.lock.json'),
          sources={str(p.relative_to(ROOT)):sha(p) for p in sources if p.is_file()},
          transport={str((target/'src'/n).relative_to(ROOT)):sha(target/'src'/n) for n in names},
          changes='Observation-only dynamic commit provenance and wait/phase traces; static promotion grouping; clean-only SHAM_WAIT')
(OUT/'configs/source.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print('Isolated producer prepared; old source/build hashes untouched')
