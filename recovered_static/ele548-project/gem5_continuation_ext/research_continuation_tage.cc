#include "cpu/pred/research_continuation_tage.hh"
#include "base/logging.hh"
#include <iomanip>
#include <sstream>
namespace bp {
CpuContinuationTAGEBase::CpuContinuationTAGEBase(const gem5::ContinuationTAGEBaseParams& p):ContinuationAccess(p),period(p.cycle_ticks),
    check_cycles(p.check_cycles),repair_cycles(p.repair_cycles),inspection_interval(p.inspection_interval),maintenance_cycles(p.maintenance_cycles),
    role_policy(p.role_policy=="N1"?RolePolicy::N1:p.role_policy=="H1"?RolePolicy::H1:p.role_policy=="REV"?RolePolicy::REV:RolePolicy::LEGACY),selected(scheme_from(p.scheme)),
    schedule_path(p.schedule_file),event_path(p.event_log),summary_path(p.summary_file),manifest_path(p.manifest_file),read_path(p.read_log),read_limit(p.read_log_limit),
    injection([this]{inject_next();},name()+".logical_SEU",false,gem5::Event::CPU_Tick_Pri-1){
    fatal_if(p.numThreads!=1||!p.speculativeHistUpdate||p.takenOnlyHistory,"Research CPU protocol requires single-thread speculative direction history");
    fatal_if(!period||check_cycles>64||repair_cycles>64,"Invalid assumed response latency");
    fatal_if(selected==Scheme::P0&&(check_cycles||repair_cycles),"P0 reference has no protection response latency");
}
void CpuContinuationTAGEBase::init(){
    Base::init();protection=std::make_unique<RoleHistoryController>(*this,selected,true,role_policy,inspection_interval);
    fatal_if(sites().size()!=65370||history_words().size()!=23,"CPU logical geometry differs from frozen scope");
    protocol=std::make_unique<RoleSpecHistoryProtocol>(*this,*protection);write_manifest();
    if(!schedule_path.empty()){
        std::ifstream input(schedule_path);fatal_if(!input,"Missing frozen CPU injection schedule");
        std::string line;gem5::Tick previous=0;bool first=true;
        while(std::getline(input,line)){
            if(line.empty()||line[0]=='#')continue;
            std::istringstream stream(line);EventSpec e;std::string encoded,extra;
            fatal_if(!(stream>>e.tick>>encoded)||(stream>>extra),"Malformed tick/logical-ID event");
            fatal_if(!first&&e.tick<previous,"Non-monotone event ticks");previous=e.tick;first=false;
            std::stringstream ids(encoded);std::string id;std::set<size_t> unique;
            while(std::getline(ids,id,';')){size_t end=0;auto value=std::stoull(id,&end);fatal_if(end!=id.size()||value>=exposed_bits()||!unique.insert(value).second,"Invalid/duplicate CPU logical ID");e.ids.push_back(value);}
            fatal_if(e.ids.empty(),"Empty atomic event");events.push_back(std::move(e));
        }
    }
    if(!event_path.empty()){event_output.open(event_path);fatal_if(!event_output,"Cannot open event log");
        event_output<<"event_id,tick,site_ids,before_bits,after_bits,XOR_verified,epoch,refill_remaining,recovery_active\n";
        repair_output.open(event_path+".repairs.csv");fatal_if(!repair_output,"Cannot open repair log");
        repair_output<<"tick,origin,detected_words,repair_busy_until,assumed_repair_cycles\n";
        rebuild_output.open(event_path+".rebuild.csv");
        rebuild_output<<"tick,phase_before,phase_after,scan_before,scan_after,publish_before,publish_after,source_bits_delta,fold_xor_delta,rebuild_writes_delta\n";}
    if(!read_path.empty()){read_output.open(read_path);fatal_if(!read_output,"Cannot open read log");
        read_output<<"read_id,tick,pc,conditional,events_applied_before_read,detected_before_read,epoch,fallback\n";}
}
void CpuContinuationTAGEBase::account_repairs(uint64_t before,unsigned origin){
    account_update_work();
    auto delta=protection->stats.detected-before;if(!delta)return;
    fatal_if(origin>=repairs_by_origin.size(),"Unknown repair origin");
    ++repair_batches;++repairs_by_origin[origin];
    // One parallel word-repair batch holds the response port for R cycles.
    // Storage writes begin now, and the independent backend update lane may
    // continue. Batches arriving while busy serialize; event clock continues.
    repair_busy_until=std::max(gem5::curTick(),repair_busy_until)+period*repair_cycles;
    static const char* names[]={"read","consume","speculative","commit","corrected","discard","rebuild"};
    if(repair_output){repair_output<<gem5::curTick()<<','<<names[origin]<<','<<delta<<','<<repair_busy_until<<','<<repair_cycles<<'\n';repair_output.flush();}
}
void CpuContinuationTAGEBase::note_prediction_read(gem5::Addr pc,bool conditional){
    ++prediction_reads;if(gem5::curTick()==last_fault_tick)++lookups_at_fault_tick;
    if(read_output&&prediction_reads<=read_limit){read_output<<prediction_reads<<','<<gem5::curTick()<<','<<pc<<','<<conditional<<','<<applied_events<<','<<protection->stats.detected<<','<<protection->epoch<<','<<protection->fallback()<<'\n';read_output.flush();}
}
void CpuContinuationTAGEBase::account_update_work(){
    auto count=protection->history_writes-last_write_count;
    if(role_policy==RolePolicy::H1){auto extra=protection->shadow_encode_bits-last_shadow_encode;if(extra)++count;last_shadow_encode=protection->shadow_encode_bits;}
    last_write_count=protection->history_writes;
    if(selected==Scheme::P0||!maintenance_cycles)return;
    try{maintenance.reserve(count*maintenance_cycles,gem5::curTick()/period);}
    catch(const std::overflow_error&){fatal("FAIL_PROTOCOL_RESOURCE bounded maintenance debt4095 overflow");}
    update_jobs+=count;max_update_queue=std::max(max_update_queue,uint64_t(maintenance.remaining!=0));
}
void CpuContinuationTAGEBase::advance_rebuild_clock(){
    if(protection->phase>=2&&last_rebuild_advance!=gem5::curTick()){
        last_rebuild_advance=gem5::curTick();
        auto phase=protection->phase,scan=protection->scan,publish=protection->publish;
        auto bits=protection->rebuild_source_bits,xors=protection->rebuild_xor_inputs,writes=protection->rebuild_writes;
        auto before_detected=protection->stats.detected;protection->advance_rebuild_step();account_repairs(before_detected,6);
        if(rebuild_output){rebuild_output<<gem5::curTick()<<','<<unsigned(phase)<<','<<unsigned(protection->phase)<<','<<unsigned(scan)<<','<<unsigned(protection->scan)<<','<<unsigned(publish)<<','<<unsigned(protection->publish)<<','<<protection->rebuild_source_bits-bits<<','<<protection->rebuild_xor_inputs-xors<<','<<protection->rebuild_writes-writes<<'\n';rebuild_output.flush();}
    }
}
void CpuContinuationTAGEBase::startup(){if(!events.empty())schedule(injection,events[0].tick);}
void CpuContinuationTAGEBase::corrupt(const std::vector<size_t>& ids){
    std::set<size_t> unique;std::vector<size_t> ordinary;
    for(auto id:ids)fatal_if(id>=exposed_bits()||!unique.insert(id).second,"Invalid combined controller event");
    for(auto id:ids)if(id<protection->exposed_bits())ordinary.push_back(id);
    protection->corrupt(ordinary);
    for(auto id:ids)if(id>=protection->exposed_bits())maintenance.flip(id-protection->exposed_bits());
}
void CpuContinuationTAGEBase::inject_next(){
    maintenance.advance(gem5::curTick()/period);
    // All same-tick events apply in file order at priority 49, before CPU 50.
    while(cursor<events.size()&&events[cursor].tick==gem5::curTick()){
        const auto& e=events[cursor];std::vector<bool> before;
        for(auto id:e.ids)before.push_back(logical_bit(id));
        corrupt(e.ids);
        for(unsigned i=0;i<e.ids.size();++i)fatal_if(logical_bit(e.ids[i])==before[i],"Logical XOR did not toggle exactly once");
        if(event_output){event_output<<cursor<<','<<gem5::curTick()<<',';
            for(unsigned i=0;i<e.ids.size();++i){if(i)event_output<<';';event_output<<e.ids[i];}event_output<<',';
            for(auto v:before)event_output<<v;event_output<<',';
            for(auto id:e.ids)event_output<<logical_bit(id);
            event_output<<",1,"<<protection->epoch<<','<<unsigned(protection->refill)<<','<<protection->recovery_active<<'\n';event_output.flush();}
        ++cursor;++applied_events;applied_flips+=e.ids.size();last_fault_tick=gem5::curTick();
    }
    if(cursor<events.size())schedule(injection,events[cursor].tick);
}
void CpuContinuationTAGEBase::write_manifest(){
    if(manifest_path.empty())return;std::ofstream out(manifest_path);fatal_if(!out,"Manifest output");
    out<<"{\"scheme\":\""<<scheme_name(selected)<<"\",\"scope_id\":\"E1_SSTAR_V1\",\"base_bits\":65370,\"total_bits\":"<<exposed_bits()<<",\"additional_sites\":[";
    bool first=true;for(const auto& s:protection->additional_sites()){if(!first)out<<',';first=false;
        out<<"{\"id\":"<<s.id<<",\"structure\":\""<<s.structure<<"\",\"word\":"<<s.word<<",\"bit\":"<<s.bit<<",\"width\":"<<s.width<<",\"replica\":"<<s.replica<<'}';}
    if(maintenance_cycles)for(unsigned bit=0;bit<BurstWorkCounter::width;++bit){if(!first)out<<',';first=false;out<<"{\"id\":"<<protection->exposed_bits()+bit<<",\"structure\":\"maintenance_work_remaining\",\"word\":0,\"bit\":"<<bit<<",\"width\":"<<BurstWorkCounter::width<<",\"replica\":0}";}
    out<<"],\"inspection_interval\":"<<inspection_interval<<",\"atomic_update_scratch\":\"23 transition parity deltas combinational; stored H1 rebuild accumulators exposed in additional_sites\",\"excluded\":[\"existing in-flight BranchInfo/CPU queues/BTB/RAS/architectural state\",\"in-flight epoch copies and fallback-at-lookup metadata\",\"pending decoded instruction/response record and absolute simulator timing tags\",\"allocator/aging metadata, statistics, RNG, software pointer/slack\",\"shared combinational SET\"]}\n";
}
void CpuContinuationTAGEBase::dumpSeu(){
    if(summary_path.empty())return;std::ofstream out(summary_path);fatal_if(!out,"Summary output");auto& s=protection->stats;
    uint64_t logical_hash=14695981039346656037ULL;
    for(const auto& site:sites()){logical_hash^=(payload(site)>>site.bit)&1;logical_hash*=1099511628211ULL;}
    unsigned phi_mismatch=0;for(unsigned w=0;w<21;++w)phi_mismatch+=(phi(w)!=read_history_word(w));
    auto mix=[&](uint64_t value){for(unsigned byte=0;byte<8;++byte){logical_hash^=(value>>(8*byte))&255;logical_hash*=1099511628211ULL;}};
    mix(tCounter);mix(threadHistory[0].nonSpecPathHist);for(auto value:useAltPredForNewlyAllocated)mix(uint8_t(value));
    out<<"{\"scheme\":\""<<scheme_name(selected)<<"\",\"scheduled_events\":"<<events.size()<<",\"applied_events\":"<<applied_events<<",\"applied_flips\":"<<applied_flips
       <<",\"unapplied_future_events\":"<<events.size()-cursor<<",\"prediction_reads\":"<<prediction_reads<<",\"lookups_at_fault_tick\":"<<lookups_at_fault_tick
       <<",\"response_hold_cycles\":"<<response_hold_cycles<<",\"drain_hold_cycles\":"<<drain_hold_cycles<<",\"cancelled_responses\":"<<cancelled_responses<<",\"retried_responses\":"<<retried_responses
       <<",\"stale_restores_suppressed\":"<<protocol->stale_restores_suppressed<<",\"stale_training_suppressed\":"<<protocol->stale_training_suppressed
       <<",\"speculative_writes\":"<<protocol->speculative_writes<<",\"committed_refill_writes\":"<<protocol->committed_refill_writes<<",\"drains_completed\":"<<protocol->drains_completed
       <<",\"refill_remaining\":"<<unsigned(protection->refill)<<",\"history_epoch\":"<<protection->epoch<<",\"recovery_active\":"<<protection->recovery_active
       <<",\"checks\":"<<s.checks<<",\"detected\":"<<s.detected<<",\"corrected\":"<<s.corrected<<",\"DUE\":"<<s.due<<",\"reset_refill\":"<<s.reset_refill
       <<",\"repair_words\":"<<s.repair_words<<",\"replica_repairs\":"<<s.replica_repairs<<",\"refill_updates\":"<<s.refill_updates<<",\"fallback_predictions\":"<<s.fallback_predictions
       <<",\"word_reads\":"<<s.word_reads<<",\"word_writes\":"<<s.word_writes<<",\"sidecar_reads\":"<<s.sidecar_reads<<",\"sidecar_writes\":"<<s.sidecar_writes
       <<",\"encode_words\":"<<s.encode_words<<",\"voted_words\":"<<s.voted_words<<",\"injection_priority\":49,\"cpu_tick_priority\":50,\"cycle_ticks\":"<<period
       <<",\"assumed_check_cycles\":"<<check_cycles<<",\"assumed_repair_cycles\":"<<repair_cycles<<",\"end_tick\":"<<gem5::curTick()
       <<",\"fold_phi_mismatch_words\":"<<phi_mismatch<<",\"canonical_base_state_hash\":"<<logical_hash<<",\"predictor_rng_draws\":"<<predictor_rng_draws<<",\"predictor_rng_hash\":"<<predictor_rng_hash
       <<",\"inspection_interval\":"<<inspection_interval<<",\"inspection_progress\":"<<unsigned(protection->progress)<<",\"continuation_inspections\":"<<protection->inspections<<",\"skipped_check_calls\":"<<protection->skipped_calls
       <<",\"delta_word_reads\":"<<0<<",\"delta_sidecar_reads\":"<<0<<",\"delta_parity_operations\":"<<0
       <<",\"repair_busy_until\":"<<repair_busy_until<<",\"repair_batches\":"<<repair_batches<<",\"repairs_by_origin\":[";
    for(unsigned i=0;i<repairs_by_origin.size();++i){if(i)out<<',';out<<repairs_by_origin[i];}out<<"],\"maintenance_cycles\":"<<maintenance_cycles<<",\"max_update_queue\":"<<max_update_queue<<",\"max_maintenance_backlog_cycles\":"<<maintenance.max_debt<<",\"maintenance_remaining\":"<<maintenance.remaining<<",\"maintenance_serviced_cycles\":"<<maintenance.serviced<<",\"update_jobs\":"<<update_jobs<<",\"maintenance_hold_cycles\":"<<maintenance_hold_cycles
       <<",\"fold_delta_xor_inputs\":"<<protection->fold_delta_xor_inputs<<",\"raw_delta_xor_inputs\":"<<protection->raw_delta_xor_inputs<<",\"path_delta_xor_inputs\":"<<protection->path_delta_xor_inputs
       <<",\"source_decodes\":"<<protection->source_decodes<<",\"source_encode_bits\":"<<protection->source_encode_bits<<",\"shadow_decodes\":"<<protection->shadow_decodes<<",\"shadow_encode_bits\":"<<protection->shadow_encode_bits
       <<",\"rebuild_requests\":"<<protection->rebuild_requests<<",\"rebuild_steps\":"<<protection->rebuild_steps<<",\"rebuild_source_bits\":"<<protection->rebuild_source_bits<<",\"rebuild_xor_inputs\":"<<protection->rebuild_xor_inputs<<",\"rebuild_writes\":"<<protection->rebuild_writes<<",\"rebuild_restarts\":"<<protection->rebuild_restarts<<",\"rebuild_phase\":"<<unsigned(protection->phase)<<"}\n";
}
CpuContinuationTAGE::CpuContinuationTAGE(const gem5::ContinuationTAGEParams& p):TAGE(p),core(*dynamic_cast<CpuContinuationTAGEBase*>(p.tage)){}
CpuContinuationTAGE::~CpuContinuationTAGE(){delete pending.info;}
void CpuContinuationTAGE::seuCancelPending(gem5::ThreadID tid){
    fatal_if(tid,"Only one thread supported");if(pending.active)++core.cancelled_responses;
    if(pending.info)assert(!pending.info->tageBranchInfo->modified);delete pending.info;pending=Pending{};
}
bool CpuContinuationTAGE::seuFrontendBlocked(gem5::ThreadID tid,bool history_empty){
    if(core.protection->phase>=2){core.advance_rebuild_clock();if(core.protection->phase){++core.drain_hold_cycles;return true;}}
    core.maintenance.advance(gem5::curTick()/core.period);
    if(core.maintenance_cycles&&core.maintenance.remaining){++core.maintenance_hold_cycles;return true;}
    auto before=core.protocol->drains_completed;bool blocked=core.protocol->frontend_blocked(history_empty);
    if(core.protocol->drains_completed!=before)seuCancelPending(tid);
    if(blocked)++core.drain_hold_cycles;return blocked;
}
bool CpuContinuationTAGE::read_pending(gem5::ThreadID tid){
    auto detected=core.protection->stats.detected;auto r=core.protocol->capture();
    pending.info=new CpuInfo(core,pending.pc,pending.conditional,r);
    pending.prediction=core.tagePredict(tid,pending.pc,pending.conditional,pending.info->tageBranchInfo);
    core.note_prediction_read(pending.pc,pending.conditional);pending.read=true;
    core.account_repairs(detected,0);pending.response_due=std::max(gem5::curTick(),core.repair_busy_until);
    return gem5::curTick()>=pending.response_due;
}
bool CpuContinuationTAGE::seuPredictionReady(gem5::ThreadID tid,gem5::Addr pc,bool conditional){
    fatal_if(tid,"Only one thread supported");
    if(!pending.active){pending.active=true;pending.pc=pc;pending.conditional=conditional;pending.check_due=gem5::curTick()+core.period*(core.protection->inspection_due()?core.check_cycles:0);}
    fatal_if(pending.pc!=pc||pending.conditional!=conditional,"Pending response PC/type changed without cancellation");
    if(gem5::curTick()<core.repair_busy_until){
        if(!pending.read)pending.check_due=std::max(pending.check_due,core.repair_busy_until+core.period*(core.protection->inspection_due()?core.check_cycles:0));
        ++core.response_hold_cycles;return false;
    }
    if(gem5::curTick()<pending.check_due){++core.response_hold_cycles;return false;}
    if(!pending.read)read_pending(tid);
    if(gem5::curTick()<pending.response_due){++core.response_hold_cycles;return false;}
    // The second integrity check is the history RMW check at consumption.
    // A detected generation/mode change invalidates the pending direction.
    auto detected=core.protection->stats.detected;core.protection->check();core.account_repairs(detected,1);
    if(!core.protocol->current(pending.info->record)||pending.info->record.fallback!=core.protection->fallback()){
        ++core.retried_responses;delete pending.info;pending.info=nullptr;pending.read=false;
        pending.check_due=std::max(gem5::curTick(),core.repair_busy_until)+core.period*(core.protection->inspection_due()?core.check_cycles:0);
        if(pending.check_due>gem5::curTick()){++core.response_hold_cycles;return false;}read_pending(tid);
    }else pending.response_due=std::max(pending.response_due,core.repair_busy_until);
    if(gem5::curTick()<pending.response_due){++core.response_hold_cycles;return false;}return true;
}
bool CpuContinuationTAGE::predict(gem5::ThreadID tid,gem5::Addr pc,bool conditional,void*& history){
    fatal_if(!pending.active||!pending.read||pending.pc!=pc||pending.conditional!=conditional||gem5::curTick()<pending.response_due,"Prediction consumed before ready");
    history=pending.info;pending.info=nullptr;auto value=pending.prediction;pending=Pending{};return value;
}
void CpuContinuationTAGE::updateHistories(gem5::ThreadID tid,gem5::Addr pc,bool uncond,bool taken,gem5::Addr target,const gem5::StaticInstPtr& inst,void*& history){
    if(!history){assert(uncond);predict(tid,pc,false,history);}auto* info=static_cast<CpuInfo*>(history);
    auto detected=core.protection->stats.detected;
    core.protocol->speculative(tid,pc,taken,target,inst,info->tageBranchInfo,info->record);
    core.account_repairs(detected,2);
}
void CpuContinuationTAGE::update(gem5::ThreadID tid,gem5::Addr pc,bool taken,void*& history,bool squashed,const gem5::StaticInstPtr& inst,gem5::Addr target){
    assert(history);auto* info=static_cast<CpuInfo*>(history);
    auto detected=core.protection->stats.detected;
    if(squashed){core.protocol->corrected(tid,taken,target,inst,info->tageBranchInfo,info->record);core.account_repairs(detected,4);return;}
    int nrand=rng->random<int>()&3;++core.predictor_rng_draws;core.predictor_rng_hash^=uint64_t(nrand);core.predictor_rng_hash*=1099511628211ULL;
    core.protocol->commit(tid,pc,taken,target,inst,info->tageBranchInfo,info->record,nrand);core.account_repairs(detected,3);delete info;history=nullptr;
}
void CpuContinuationTAGE::squash(gem5::ThreadID tid,void*& history){
    assert(history);auto* info=static_cast<CpuInfo*>(history);auto detected=core.protection->stats.detected;
    core.protocol->discard(tid,info->tageBranchInfo,info->record);core.account_repairs(detected,5);delete info;history=nullptr;
}
void CpuContinuationTAGE::branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void*&){fatal("Decoupled frontend unsupported in fixed CPU research scope");}
}
