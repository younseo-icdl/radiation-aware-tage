#include "replay/e1_trace.hpp"
#include "fault/multiplicity.hpp"
#include "fault/seed_namespace.hpp"
#include <array>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sys/resource.h>
using namespace bp;
struct PlannedTrial {unsigned field,trial,inject,k;uint64_t seed;std::vector<size_t> ids;};
struct GoldState {std::vector<uint8_t> bits;std::vector<int8_t> alt;int64_t aging;std::mt19937_64 rng;};
int main(int argc,char**argv){try{
    if(argc!=14)throw std::invalid_argument("usage: e1_campaign TRACE WORKLOAD INDEX ANCHOR WARMUP PREFIX HORIZON TRIALS K1 K2 MODEL SEED_BASE OUTPUT_CSV");
    unsigned windex=std::stoul(argv[3]),anchor=std::stoul(argv[4]),warmup=std::stoul(argv[5]);
    unsigned prefix=std::stoul(argv[6]),horizon=std::stoul(argv[7]),trials=std::stoul(argv[8]);
    if(anchor<warmup||!prefix||horizon!=100000||!trials||trials>100)throw std::invalid_argument("invalid E1 bounds");
    MultiplicityProfile profile(std::stoull(argv[9]),std::stoull(argv[10]));
    std::string model=argv[11];uint64_t seed_base=std::stoull(argv[12]);
    const bool zero=model=="ZERO";
    auto trace=read_e1_trace(argv[1]);
    if(size_t(anchor)+prefix+horizon>trace.conditionals.size())throw std::runtime_error("incomplete real E1 window");
    TageAdapter clean;auto sites=clean.core.sites();std::array<std::vector<size_t>,6> fields;
    for(auto& s:sites)fields[s.kind].push_back(s.id);
    std::vector<PlannedTrial> plan;std::set<size_t> endpoints;
    const std::array<unsigned,5> checkpoints{130,1000,10000,50000,100000};
    for(unsigned field=0;field<6;++field)for(unsigned trial=0;trial<trials;++trial){
        uint64_t seed=seed_base+windex*1000000+field*10000+trial;
        std::mt19937_64 time_rng(fault_seed(seed,FaultStream::Time)),k_rng(fault_seed(seed,FaultStream::Multiplicity)),location_rng(fault_seed(seed,FaultStream::Location));
        unsigned inject=std::uniform_int_distribution<unsigned>(0,prefix-1)(time_rng);
        unsigned k=profile.draw(k_rng);auto ids=logical_adjacent_event(fields[field],k,location_rng);
        plan.push_back({field,trial,inject,k,seed,std::move(ids)});
        for(auto h:checkpoints)endpoints.insert(trace.conditionals[anchor+inject+h-1]);
    }
    size_t begin=trace.conditionals[anchor];
    for(size_t i=(anchor==warmup?0:trace.conditionals[anchor-warmup]);i<begin;++i)clean.step(trace.controls[i].branch);
    std::map<unsigned,TageAdapter::Snapshot> starts;
    std::map<size_t,GoldState> gold_state;
    std::vector<bool> gold;unsigned ordinal=0;
    size_t final=trace.conditionals[anchor+prefix+horizon-1]+1;
    for(size_t i=begin;i<final;++i){const auto& b=trace.controls[i].branch;
        if(b.conditional&&ordinal<prefix&&ordinal%1000==0)starts.emplace(ordinal,clean.snapshot());
        gold.push_back(clean.step(b));ordinal+=b.conditional;
        if(endpoints.count(i)){
            // Only control metadata copied from full snapshot; SW slack is not
            // exposed physical state and is never used as a recovery criterion.
            auto s=clean.core.save();
            gold_state.emplace(i,GoldState{compact_bits(clean.core,sites),s.alt,s.aging,clean.predictor_rng});
        }
    }
    std::ofstream out(argv[13]);if(!out)throw std::runtime_error("output unavailable");
    out<<"workload,model,field,subfield,trial,trial_master_seed,time_seed,k_seed,location_seed,inject_offset,original_conditional_ordinal,original_instruction_record,multiplicity,event_site_ids,bank,row,bit,width,conditional_anchor_probability,harm,help,net,clean_misses,faulty_misses,post_branches,instructions,delta_MPKI,first_divergence,last_divergence,queried_address_visits,first_queried_address";
    for(auto h:checkpoints)out<<",harm_"<<h<<",help_"<<h<<",net_"<<h<<",instructions_"<<h<<",delta_MPKI_"<<h<<",all_residual_"<<h<<",field_residual_"<<h<<",controls_equal_"<<h<<",observed_semantic_equal_"<<h;
    out<<",wall_seconds,peak_rss_kib,status\n"<<std::setprecision(17);
    for(const auto& trial:plan){auto start=std::chrono::steady_clock::now();TageAdapter faulty;
        unsigned checkpoint=trial.inject/1000*1000;
        faulty.restore(starts.at(checkpoint));
        size_t event=trace.conditionals[anchor+trial.inject];
        for(size_t i=trace.conditionals[anchor+checkpoint];i<event;++i)faulty.step(trace.controls[i].branch);
        if(!zero)faulty.core.corrupt(trial.ids);
        std::string subfield=subfield_name(sites[trial.ids[0]]);
        for(auto id:trial.ids)if(subfield!=subfield_name(sites[id]))subfield="cross_subfield";
        auto window=e1_window(trace,anchor+trial.inject,horizon);
        unsigned harm=0,help=0,clean_misses=0,faulty_misses=0,o=0,visits=0;
        int first=-1,last=-1,first_visit=-1;
        std::array<unsigned,5> harms{},helps{},residuals{},field_residuals{},control_equal{},semantic_equal{};
        std::array<uint64_t,5> instructions{};unsigned cindex=0;
        for(size_t i=window.begin;i<window.end;++i){const auto& b=trace.controls[i].branch;
            bool p=faulty.step_observed(b,[&](const Base::BranchInfo& bi){
                if(!b.conditional||trial.field>=4)return;
                bool queried=false;
                for(auto id:trial.ids){const auto& s=sites[id];
                    queried|=s.kind==0 ? (s.bank?unsigned(bi.bimodalIndex>>2):unsigned(bi.bimodalIndex))==s.row
                                       : unsigned(bi.tableIndices[s.bank])==s.row;}
                if(queried){++visits;if(first_visit<0)first_visit=o;}
            });
            bool g=gold[i-begin];
            if(b.conditional){bool fm=p!=b.taken,gm=g!=b.taken;
                harm+=fm&&!gm;help+=!fm&&gm;clean_misses+=gm;faulty_misses+=fm;
                if(p!=g){if(first<0)first=o;last=o;}++o;
                if(cindex<checkpoints.size()&&o==checkpoints[cindex]){
                    auto bits=compact_bits(faulty.core,sites);const auto& gs=gold_state.at(i);
                    for(size_t id=0;id<bits.size();++id){bool different=bits[id]!=gs.bits[id];residuals[cindex]+=different;field_residuals[cindex]+=different&&sites[id].kind==trial.field;}
                    auto s=faulty.core.save();
                    control_equal[cindex]=s.alt==gs.alt&&s.aging==gs.aging&&faulty.predictor_rng==gs.rng;
                    semantic_equal[cindex]=residuals[cindex]==0&&control_equal[cindex];
                    if(faulty.predictor_rng!=gs.rng)throw std::runtime_error("predictor RNG changed by event schedule");
                    if(zero&&!semantic_equal[cindex])throw std::runtime_error("zero-event canonical state mismatch");
                    harms[cindex]=harm;helps[cindex]=help;
                    instructions[cindex]=trace.controls[i].instruction-trace.controls[event].instruction+1;
                    ++cindex;
                }
            }
        }
        if(o!=horizon||cindex!=5||int(faulty_misses)-int(clean_misses)!=int(harm)-int(help))throw std::runtime_error("bad equal followup/accounting");
        double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        struct rusage use;getrusage(RUSAGE_SELF,&use);auto s=sites[trial.ids[0]];
        out<<argv[2]<<','<<model<<','<<field_name(trial.field)<<','<<subfield<<','<<trial.trial<<','<<trial.seed<<','<<fault_seed(trial.seed,FaultStream::Time)<<','<<fault_seed(trial.seed,FaultStream::Multiplicity)<<','<<fault_seed(trial.seed,FaultStream::Location)<<','<<trial.inject<<','<<anchor+trial.inject<<','<<trace.controls[event].instruction<<','<<(zero?0:trial.k)<<',';
        for(size_t j=0;j<trial.ids.size();++j){if(j)out<<';';out<<trial.ids[j];}
        out<<','<<s.bank<<','<<s.row<<','<<s.bit<<','<<s.width<<','<<1.0/(fields[trial.field].size()-trial.k+1)/prefix<<','<<harm<<','<<help<<','<<int(harm)-int(help)<<','<<clean_misses<<','<<faulty_misses<<','<<o<<','<<window.instructions<<','<<1000.0*(int(harm)-int(help))/window.instructions<<','<<first<<','<<last<<','<<(trial.field<4?int(visits):-1)<<','<<first_visit;
        for(unsigned j=0;j<5;++j)out<<','<<harms[j]<<','<<helps[j]<<','<<int(harms[j])-int(helps[j])<<','<<instructions[j]<<','<<1000.0*(int(harms[j])-int(helps[j]))/instructions[j]<<','<<residuals[j]<<','<<field_residuals[j]<<','<<control_equal[j]<<','<<semantic_equal[j];
        out<<','<<seconds<<','<<use.ru_maxrss<<",PASS\n";
        out.flush();if(!out)throw std::runtime_error("output failure");
        if(trial.trial+1==trials)std::cerr<<argv[2]<<' '<<model<<' '<<field_name(trial.field)<<" completed="<<trials<<'\n';
    }
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL_EXECUTION "<<e.what()<<'\n';return 1;}}
