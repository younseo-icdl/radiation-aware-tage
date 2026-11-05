#!/usr/bin/env python3
"""Apply a recorded minimal transport patch to a separate pinned worktree."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
TARGET=ROOT/'third_party/gem5-e3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert subprocess.check_output(['git','-C',str(TARGET),'rev-parse','HEAD'],text=True).strip()==PIN
    def edit(path,old,new):
        p=TARGET/path;text=p.read_text()
        if new in text:return
        assert text.count(old)==1,(path,text.count(old));p.write_text(text.replace(old,new))
    edit('src/cpu/pred/conditional.hh','    virtual bool lookup(ThreadID tid, Addr pc, void * &bp_history) = 0;',
         '    virtual bool lookup(ThreadID tid, Addr pc, void * &bp_history) = 0;\n\n'
         '    // Optional response transport, default zero-latency/no drain.\n'
         '    virtual bool seuFrontendBlocked(ThreadID, bool) { return false; }\n'
         '    virtual bool seuPredictionReady(ThreadID, Addr, bool) { return true; }\n'
         '    virtual void seuCancelPending(ThreadID) {}')
    edit('src/cpu/pred/bpred_unit.hh','    void update(const InstSeqNum &done_sn, ThreadID tid);',
         '    void update(const InstSeqNum &done_sn, ThreadID tid);\n\n'
         '    bool seuFrontendBlocked(ThreadID tid) {\n'
         '        return cPred->seuFrontendBlocked(tid, predHist[tid].empty());\n'
         '    }\n'
         '    bool seuPredictionReady(ThreadID tid, Addr pc, bool conditional) {\n'
         '        return cPred->seuPredictionReady(tid, pc, conditional);\n'
         '    }\n'
         '    void seuCancelPending(ThreadID tid) { cPred->seuCancelPending(tid); }')
    edit('src/cpu/o3/bac.hh','    void startupStage();',
         '    void startupStage();\n\n'
         '    bool seuFrontendBlocked(ThreadID tid) { return bpu->seuFrontendBlocked(tid); }\n'
         '    bool seuPredictionReady(ThreadID tid, Addr pc, bool conditional) {\n'
         '        return bpu->seuPredictionReady(tid, pc, conditional);\n'
         '    }\n'
         '    void seuCancelPending(ThreadID tid) { bpu->seuCancelPending(tid); }')
    edit('src/cpu/o3/fetch.hh','    StaticInstPtr macroop[MaxThreads];',
         '    StaticInstPtr macroop[MaxThreads];\n'
         '    // Decoded control instruction held until predictor response.\n'
         '    StaticInstPtr seuPendingInst[MaxThreads];')
    edit('src/cpu/o3/fetch.cc','    fetchStatus[tid] = Squashing;\n\n    // Empty fetch queue',
         '    fetchStatus[tid] = Squashing;\n'
         '    seuPendingInst[tid] = nullptr;\n'
         '    bac->seuCancelPending(tid);\n\n    // Empty fetch queue')
    edit('src/cpu/o3/fetch.cc','    fetchStats.status[Running]++;\n    std::unique_ptr<PCStateBase> next_pc(this_pc.clone());',
         '    if (bac->seuFrontendBlocked(tid)) {\n'
         '        cpu->activityThisCycle();\n'
         '        return;\n'
         '    }\n'
         '    fetchStats.status[Running]++;\n    std::unique_ptr<PCStateBase> next_pc(this_pc.clone());')
    edit('src/cpu/o3/fetch.cc','            !inRom && !macroop[tid]) {',
         '            !inRom && !macroop[tid] && !seuPendingInst[tid]) {')
    edit('src/cpu/o3/fetch.cc','    bool quiesce = false;',
         '    bool quiesce = false;\n    bool seuResponseHold = false;')
    edit('src/cpu/o3/fetch.cc','           && !predictedBranch && !quiesce) {',
         '           && !predictedBranch && !quiesce && !seuResponseHold) {')
    edit('src/cpu/o3/fetch.cc','        bool needMem = !inRom && !curMacroop && !dec_ptr->instReady();',
         '        bool needMem = !seuPendingInst[tid] && !inRom && !curMacroop && !dec_ptr->instReady();')
    edit('src/cpu/o3/fetch.cc','            if (!(curMacroop || inRom)) {',
         '            if (seuPendingInst[tid]) {\n'
         '                staticInst = seuPendingInst[tid];\n'
         '            } else if (!(curMacroop || inRom)) {')
    edit('src/cpu/o3/fetch.cc','            DynInstPtr instruction = buildInst(\n                    tid, staticInst, curMacroop, this_pc, *next_pc, true);',
         '            if (staticInst->isControl() &&\n'
         '                !bac->seuPredictionReady(tid, this_pc.instAddr(),\n'
         '                                         !staticInst->isUncondCtrl())) {\n'
         '                seuPendingInst[tid] = staticInst;\n'
         '                seuResponseHold = true;\n'
         '                cpu->activityThisCycle();\n'
         '                break;\n'
         '            }\n'
         '            seuPendingInst[tid] = nullptr;\n'
         '            DynInstPtr instruction = buildInst(\n                    tid, staticInst, curMacroop, this_pc, *next_pc, true);')
    edit('src/cpu/o3/fetch.cc','        fetchStatus[tid] != QuiescePending && !curMacroop;',
         '        fetchStatus[tid] != QuiescePending && !curMacroop && !seuPendingInst[tid];')
    edit('src/cpu/pred/SConscript',"Import('*')", "Import('*')\n\nSimObject('BPSEU.py', sim_objects=['ResearchTAGEBase', 'ResearchTAGE'])\nSource('research_tage.cc')")
    for name in ['BPSEU.py','research_tage.hh','research_tage.cc']:shutil.copy2(ROOT/'gem5_ext'/name,TARGET/'src/cpu/pred'/name)
    for name in ['tage_base.hh','tage_base.cc','tage.cc','tage.hh']:
        assert sha(TARGET/'src/cpu/pred'/name)==sha(ROOT/'third_party/gem5/src/cpu/pred'/name),name
    out=ROOT/'reports/e3_integration';out.mkdir(exist_ok=True)
    patch=subprocess.check_output(['git','-C',str(TARGET),'diff','--','src'],text=True)
    (out/'gem5_transport.patch').write_text(patch)
    changed=['src/cpu/pred/conditional.hh','src/cpu/pred/bpred_unit.hh','src/cpu/o3/bac.hh','src/cpu/o3/fetch.hh','src/cpu/o3/fetch.cc','src/cpu/pred/SConscript']
    record={'status':'PREPARED_SOURCE_NOT_YET_CPU_VERIFIED','pin':PIN,'worktree':str(TARGET),'patch_sha256':sha(out/'gem5_transport.patch'),
            'modified_files':{name:sha(TARGET/name) for name in changed},'new_files':{name:sha(ROOT/'gem5_ext'/name) for name in ['BPSEU.py','research_tage.hh','research_tage.cc']},
            'upstream_TAGE_files_unchanged':True,'CPU_threads':1,'decoupled_frontend':False,
            'shared_code':{p:sha(ROOT/p) for p in ['src/predictor/tage_access.hpp','src/protection/word.hpp','src/protection/history_controller.hpp','src/protection/spec_history.hpp']},
            'injection_priority':49,'CPU_tick_priority':50,'latency_semantics':'read/check at check_due; storage writeback begins at detection; every read/consume/speculate/commit/corrected/discard repair batch serializes R cycles on response port; independent backend update lane continues; cached direction delivered only at response_due; squash cancels pending response; RMW can retry/rehold',
            'controller_added_CPU_bit':'ED/ECC recovery_active 1 bit, in addition to E2 8-bit refill/32-bit epoch',
            'explicit_exclusions':['in-flight saved epoch and fallback metadata','pending decoded instruction/response and simulator timing tags','common existing CPU queues/checkpoints, BTB/RAS/architecture','shared combinational SET'],
            'physical_RTL_latency':'NOT_MEASURED; declared software protocol assumption','full_CPU_checkpoint_serialization':'NOT_IMPLEMENTED; repeat warmup per run'}
    (ROOT/'sources/gem5_e3_source.lock.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS prepared separate pinned worktree; upstream TAGE files unchanged; source is not yet CPU verified')
if __name__=='__main__':main()
