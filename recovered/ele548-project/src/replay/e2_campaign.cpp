#include "predictor/protected_adapter.hpp"
#include "replay/e1_trace.hpp"
#include "fault/event_stream.hpp"
#include "fault/seed_namespace.hpp"
#include <array>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <map>
#include <sys/resource.h>
using namespace bp;
struct Plan {unsigned trial,offset;uint64_t seed;};
struct Gold {std::vector<uint8_t> bits;std::vector<int8_t> alt;int64_t aging;std::mt19937_64 rng;};
static std::vector<TimedFault> selected_events(const std::vector<double>& times,const std::vector<TageAccess::HistoryWord>& words,
        const MultiplicityProfile& profile,uint64_t kseed,uint64_t location,unsigned field){
    std::vector<const TageAccess::HistoryWord*> eligible;size_t total=0;
    for(auto& w:words)if(field==6||w.kind==field){eligible.push_back(&w);total+=w.width;}
    std::mt19937_64 krng(kseed),wrng(location),arng(location^0x9e3779b97f4a7c15ULL);
    std::vector<TimedFault> result;
    for(auto time:times){auto ticket=std::uniform_int_distribution<size_t>(0,total-1)(wrng);unsigned wi=0;
        while(ticket>=eligible[wi]->width)ticket-=eligible[wi++]->width;
        auto k=profile.draw(krng);auto ids=logical_adjacent_event(eligible[wi]->sites,k,arng);
        result.push_back({time,std::move(ids),eligible[wi]->kind});}
    return result;
}
static std::vector<TimedFault> storage_events(const std::vector<double>& times,const std::array<std::vector<size_t>,6>& fields,
        const std::vector<StoredSite>& extra,const MultiplicityProfile& profile,uint64_t kseed,uint64_t location){
    // Core field pools, then natural added check/control/replica words. No
    // cross-replica geometry is inferred from these logical anchors.
    std::vector<std::vector<size_t>> pools(fields.begin(),fields.end());
    std::string previous;
    for(auto& s:extra){auto key=s.structure+":"+std::to_string(s.replica)+":"+std::to_string(s.word);
        if(key!=previous){pools.emplace_back();previous=key;}pools.back().push_back(s.id);}
    size_t total=0;for(auto& p:pools)total+=p.size();
    std::mt19937_64 krng(kseed),prng(location),arng(location^0x9e3779b97f4a7c15ULL);
    std::vector<TimedFault> result;
    for(auto time:times){auto ticket=std::uniform_int_distribution<size_t>(0,total-1)(prng);unsigned pool=0;
        while(ticket>=pools[pool].size())ticket-=pools[pool++].size();
        unsigned k=profile.draw(krng);
        // A one-bit parity word has no within-word K=2 location. Do not clip K:
        // in that case choose the second unique bit uniformly from the entire
        // exposed population (explicit dispersed logical MCU sensitivity).
        std::vector<size_t> ids;
        if(k<=pools[pool].size())ids=logical_adjacent_event(pools[pool],k,arng);
        else {ids.push_back(pools[pool][0]);auto pick=std::uniform_int_distribution<size_t>(0,total-2)(arng);
            size_t second=pick>=ids[0]?pick+1:pick;ids.push_back(second);}
        result.push_back({time,std::move(ids),pool<6?pool:6});}
    return result;
}
int main(int argc,char** argv){try{
    if(argc!=17)throw std::invalid_argument("usage: e2_campaign TRACE WORKLOAD INDEX ANCHOR PREFIX HORIZON N K1 K2 MODEL MODE POP FIELD BASE_RATE SEED OUTPUT_PREFIX");
    unsigned wi=std::stoul(argv[3]),anchor=std::stoul(argv[4]),prefix=std::stoul(argv[5]),horizon=std::stoul(argv[6]),n=std::stoul(argv[7]);
    MultiplicityProfile kprofile(std::stoull(argv[8]),std::stoull(argv[9]));
    std::string model=argv[10],mode=argv[11],population=argv[12];unsigned field=std::stoul(argv[13]);
    double base_rate=std::stod(argv[14]);uint64_t seed_base=std::stoull(argv[15]);bool zero=model=="ZERO";
    if(!n||n>100||!horizon||horizon>100000||!prefix||prefix>20000||!std::isfinite(base_rate)||base_rate<0||
       (mode!="single"&&mode!="repeat")||(population!="selected_payload"&&population!="paired_base_full"&&population!="storage_scaled_full")||
       (field!=4&&field!=5&&field!=6))throw std::invalid_argument("E2 bounds/config");
    auto trace=read_e1_trace(argv[1]);if(size_t(anchor)+prefix+horizon>trace.conditionals.size())throw std::runtime_error("incomplete E2 window");
    TageAdapter clean;auto sites=clean.core.sites();auto words=clean.core.history_words();std::array<std::vector<size_t>,6> fields;
    for(auto& s:sites)fields[s.kind].push_back(s.id);
    std::vector<Plan> plans;std::set<size_t> ends;
    for(unsigned trial=0;trial<n;++trial){auto seed=seed_base+wi*1000000+field*10000+trial;
        std::mt19937_64 rng(fault_seed(seed,FaultStream::Time));unsigned offset=mode=="single"?std::uniform_int_distribution<unsigned>(0,prefix-1)(rng):0;
        plans.push_back({trial,offset,seed});ends.insert(trace.conditionals[anchor+offset+horizon-1]);}
    size_t begin=trace.conditionals[anchor];for(size_t i=0;i<begin;++i)clean.step(trace.controls[i].branch);
    std::map<unsigned,TageAdapter::Snapshot> starts;std::map<size_t,Gold> gold_state;std::vector<bool> gold;unsigned ordinal=0;
    for(size_t i=begin;i<=*ends.rbegin();++i){auto b=trace.controls[i].branch;
        if(b.conditional&&ordinal<prefix&&ordinal%1000==0)starts.emplace(ordinal,clean.snapshot());
        gold.push_back(clean.step(b));ordinal+=b.conditional;
        if(ends.count(i)){auto s=clean.core.save();gold_state.emplace(i,Gold{compact_bits(clean.core,sites),s.alt,s.aging,clean.predictor_rng});}}
    std::ofstream out(std::string(argv[16])+".csv"),event_out(std::string(argv[16])+".events.csv");
    if(!out||!event_out)throw std::runtime_error("E2 output");out<<std::setprecision(17);event_out<<std::setprecision(17);
    out<<"workload,model,mode,population,field,scheme,trial,trial_master_seed,time_seed,k_seed,location_seed,inject_offset,original_instruction,event_rate_per_conditional,expected_flip_rate_per_conditional,exposed_bits,event_count,flip_count,selected_payload_flips,extra_storage_flips,multi_event_bins,harm,help,net,clean_misses,faulty_misses,post_branches,instructions,delta_MPKI,first_divergence,last_divergence,end_differing_base_bits,end_controls_equal,refill_remaining,history_epoch,checks,word_reads,word_writes,sidecar_reads,sidecar_writes,encode_words,voted_words,detected,corrected,due,reset_refill,repair_words,replica_repairs,refill_updates,fallback_predictions,wall_seconds,peak_rss_kib,status\n";
    event_out<<"workload,model,mode,population,field,scheme,trial,event_id,arrival_conditional_coordinate,applied_before_conditional,event_site_ids,multiplicity,status\n";
    for(auto scheme:{Scheme::P0,Scheme::ED,Scheme::ECC,Scheme::TMR}){
        ProtectedAdapter faulty(scheme);
        for(auto& trial:plans){auto clock=std::chrono::steady_clock::now();unsigned checkpoint=trial.offset/1000*1000;
            faulty.load_clean_warmup(starts.at(checkpoint));size_t event=trace.conditionals[anchor+trial.offset];
            for(size_t i=trace.conditionals[anchor+checkpoint];i<event;++i)faulty.step(trace.controls[i].branch);
            faulty.protection.stats={};
            size_t exposed=population=="selected_payload"?(field==4?146:field==5?200:346):population=="paired_base_full"?sites.size():faulty.protection.exposed_bits();
            double rate=base_rate*(population=="storage_scaled_full"?double(exposed)/sites.size():1);
            std::vector<double> times=zero?std::vector<double>{}:mode=="single"?std::vector<double>{0}:poisson_times(rate,horizon,fault_seed(trial.seed,FaultStream::Time));
            std::vector<TimedFault> events;
            if(population=="selected_payload")events=selected_events(times,words,kprofile,fault_seed(trial.seed,FaultStream::Multiplicity),fault_seed(trial.seed,FaultStream::Location),field);
            else if(population=="paired_base_full")events=mark_events(times,fields,kprofile,fault_seed(trial.seed,FaultStream::Multiplicity),fault_seed(trial.seed,FaultStream::Location));
            else events=storage_events(times,fields,faulty.protection.additional_sites(),kprofile,fault_seed(trial.seed,FaultStream::Multiplicity),fault_seed(trial.seed,FaultStream::Location));
            auto window=e1_window(trace,anchor+trial.offset,horizon);unsigned harm=0,help=0,gm=0,fm=0,o=0,flips=0,selected=0,extra=0,multibins=0;size_t cursor=0;int first=-1,last=-1;
            for(size_t i=window.begin;i<window.end;++i){auto b=trace.controls[i].branch;
                if(b.conditional){auto count=apply_before_branch(events,cursor,o,[&](const TimedFault& e){faulty.protection.corrupt(e.sites);flips+=e.sites.size();
                    event_out<<argv[2]<<','<<model<<','<<mode<<','<<population<<','<<field<<','<<scheme_name(scheme)<<','<<trial.trial<<','<<cursor<<','<<e.time<<','<<o<<',';
                    for(unsigned j=0;j<e.sites.size();++j){auto id=e.sites[j];selected+=id<sites.size()&&sites[id].kind>=4;extra+=id>=sites.size();if(j)event_out<<';';event_out<<id;}
                    event_out<<','<<e.sites.size()<<",PASS\n";});multibins+=count>1;}
                bool p=faulty.step(b),g=gold[i-begin];
                if(b.conditional){bool ff=p!=b.taken,gg=g!=b.taken;fm+=ff;gm+=gg;harm+=ff&&!gg;help+=!ff&&gg;if(p!=g){if(first<0)first=o;last=o;}++o;}}
            if(cursor!=events.size()||o!=horizon||int(fm)-int(gm)!=int(harm)-int(help))throw std::runtime_error("E2 events/horizon/accounting");
            auto bits=compact_bits(faulty.predictor.core,sites);const auto& z=gold_state.at(window.end-1);unsigned residual=0;
            for(unsigned id=0;id<bits.size();++id)residual+=bits[id]!=z.bits[id];auto state=faulty.predictor.core.save();
            bool controls=state.alt==z.alt&&state.aging==z.aging&&faulty.predictor.predictor_rng==z.rng;
            if(faulty.predictor.predictor_rng!=z.rng)throw std::runtime_error("fault RNG changed predictor RNG");
            if(events.empty()&&(harm||help||residual||!controls||faulty.protection.stats.detected))throw std::runtime_error("zero fault equivalence failure");
            auto& s=faulty.protection.stats;struct rusage use;getrusage(RUSAGE_SELF,&use);
            double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-clock).count();
            out<<argv[2]<<','<<model<<','<<mode<<','<<population<<','<<field<<','<<scheme_name(scheme)<<','<<trial.trial<<','<<trial.seed<<','<<fault_seed(trial.seed,FaultStream::Time)<<','<<fault_seed(trial.seed,FaultStream::Multiplicity)<<','<<fault_seed(trial.seed,FaultStream::Location)<<','<<trial.offset<<','<<trace.controls[event].instruction<<','<<(mode=="single"?-1:rate)<<','<<(mode=="single"?-1:rate*double(kprofile.k1+2*kprofile.k2)/(kprofile.k1+kprofile.k2))<<','<<exposed<<','<<events.size()<<','<<flips<<','<<selected<<','<<extra<<','<<multibins<<','<<harm<<','<<help<<','<<int(harm)-int(help)<<','<<gm<<','<<fm<<','<<o<<','<<window.instructions<<','<<1000.0*(int(harm)-int(help))/window.instructions<<','<<first<<','<<last<<','<<residual<<','<<controls<<','<<unsigned(faulty.protection.refill)<<','<<faulty.protection.epoch<<','<<s.checks<<','<<s.word_reads<<','<<s.word_writes<<','<<s.sidecar_reads<<','<<s.sidecar_writes<<','<<s.encode_words<<','<<s.voted_words<<','<<s.detected<<','<<s.corrected<<','<<s.due<<','<<s.reset_refill<<','<<s.repair_words<<','<<s.replica_repairs<<','<<s.refill_updates<<','<<s.fallback_predictions<<','<<seconds<<','<<use.ru_maxrss<<",PASS\n";out.flush();
            if(!out||!event_out)throw std::runtime_error("E2 output failure");
        }
    }
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL_EXECUTION "<<e.what()<<'\n';return 1;}}
