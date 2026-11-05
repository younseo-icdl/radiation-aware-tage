#include "continuation/role_adapter.hpp"
#include "replay/e1_trace.hpp"
#include "fault/event_stream.hpp"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <sys/resource.h>
using namespace bp;
int main(int argc,char**argv){try{
    if(argc!=10)throw std::invalid_argument("usage: scheduled TRACE ANCHOR HORIZON SCHEME EVENTS_TSV MODEL OUTPUT_PREFIX K ROLE_POLICY");
    auto trace=read_e1_trace(argv[1]);unsigned anchor=std::stoul(argv[2]),horizon=std::stoul(argv[3]);
    if(!horizon||horizon>100000)throw std::invalid_argument("schedule horizon");
    auto scheme=scheme_from(argv[4]);unsigned k=std::stoul(argv[8]);auto window=e1_window(trace,anchor,horizon);
    std::ifstream input(argv[5]);if(!input)throw std::runtime_error("external schedule missing");
    std::vector<TimedFault> events;std::string line;double previous=-1;
    while(std::getline(input,line)){if(line.empty()||line[0]=='#')continue;std::istringstream row(line);double coordinate;std::string encoded,extra;
        if(!(row>>coordinate>>encoded)||(row>>extra)||!std::isfinite(coordinate)||coordinate<0||coordinate>=horizon||coordinate<previous)throw std::runtime_error("invalid external coordinate/order");
        previous=coordinate;std::vector<size_t> ids;std::stringstream parser(encoded);std::string token;
        while(std::getline(parser,token,';')){size_t end=0;auto id=std::stoull(token,&end);if(end!=token.size())throw std::runtime_error("invalid external logical id");ids.push_back(id);}
        if(ids.empty())throw std::runtime_error("empty external event");events.push_back({coordinate,std::move(ids),6});
        if(events.size()>20000)throw std::runtime_error("external event safety limit");}
    auto clock=std::chrono::steady_clock::now();TageAdapter clean;
    for(size_t i=0;i<window.begin;++i)clean.step(trace.controls[i].branch);auto warm=clean.snapshot();std::vector<bool> gold;
    for(size_t i=window.begin;i<window.end;++i)gold.push_back(clean.step(trace.controls[i].branch));
    RolePolicy policy=std::string(argv[9])=="N1"?RolePolicy::N1:std::string(argv[9])=="H1"?RolePolicy::H1:std::string(argv[9])=="REV"?RolePolicy::REV:RolePolicy::LEGACY;RoleAdapter faulty(scheme,policy,k);faulty.warm(warm);
    for(const auto& event:events){std::set<size_t> unique;
        for(auto id:event.sites)if(id>=faulty.protection.exposed_bits()||!unique.insert(id).second)throw std::runtime_error("invalid/duplicate external site");}
    std::ofstream out(std::string(argv[7])+".csv"),log(std::string(argv[7])+".events.csv");if(!out||!log)throw std::runtime_error("external output");
    log<<"event_id,coordinate,applied_before_conditional,site_ids,multiplicity,status\n"<<std::setprecision(17);
    size_t cursor=0;unsigned ordinal=0,harm=0,help=0,cm=0,fm=0,flips=0,multibins=0;int first=-1,last=-1,first_detected=-1;int injected_control=-1,detected_control=-1;
    for(size_t i=window.begin;i<window.end;++i){auto b=trace.controls[i].branch;
        if(b.conditional){auto n=apply_before_branch(events,cursor,ordinal,[&](const TimedFault& e){faulty.protection.corrupt(e.sites);if(injected_control<0)injected_control=int(i-window.begin);flips+=e.sites.size();
            log<<cursor<<','<<e.time<<','<<ordinal<<',';for(unsigned j=0;j<e.sites.size();++j){if(j)log<<';';log<<e.sites[j];}log<<','<<e.sites.size()<<",PASS\n";});multibins+=n>1;}
        auto detected_before=faulty.protection.stats.detected;bool p=faulty.step(b),g=gold[i-window.begin];
        if(faulty.protection.stats.detected>detected_before&&first_detected<0){first_detected=ordinal;detected_control=int(i-window.begin);}if(b.conditional){bool ff=p!=b.taken,gg=g!=b.taken;fm+=ff;cm+=gg;harm+=ff&&!gg;help+=!ff&&gg;
            if(p!=g){if(first<0)first=ordinal;last=ordinal;}++ordinal;}}
    if(cursor!=events.size()||ordinal!=horizon||int(fm)-int(cm)!=int(harm)-int(help)||faulty.predictor_rng!=clean.predictor_rng)throw std::runtime_error("external events/horizon/RNG/accounting");
    auto a=faulty.core.bits(),z=clean.core.bits();unsigned residual=0;for(unsigned i=0;i<a.size();++i)residual+=a[i]!=z[i];
    if(events.empty()&&(harm||help||residual||faulty.core.bits()!=clean.core.bits()))throw std::runtime_error("external zero full-state mismatch");
    auto s=faulty.protection.stats;struct rusage usage;getrusage(RUSAGE_SELF,&usage);
    out<<"model,scheme,event_count,flip_count,multi_event_bins,clean_misses,faulty_misses,harm,help,net,instructions,post_branches,delta_MPKI,first_divergence,last_divergence,end_differing_base_bits,detected,corrected,DUE,reset_refill,refill_updates,fallback_predictions,wall_seconds,peak_RSS_KiB,status,inspection_interval,inspections,checks,history_writes,fold_delta_xor_inputs,source_decodes,rebuild_steps,first_detector_conditional,detector_delay_control_updates\n"<<std::setprecision(17);
    out<<argv[6]<<','<<scheme_name(scheme)<<','<<events.size()<<','<<flips<<','<<multibins<<','<<cm<<','<<fm<<','<<harm<<','<<help<<','<<int(harm)-int(help)<<','<<window.instructions<<','<<ordinal<<','<<1000.0*(int(harm)-int(help))/window.instructions<<','<<first<<','<<last<<','<<residual<<','<<s.detected<<','<<s.corrected<<','<<s.due<<','<<s.reset_refill<<','<<s.refill_updates<<','<<s.fallback_predictions<<','<<std::chrono::duration<double>(std::chrono::steady_clock::now()-clock).count()<<','<<usage.ru_maxrss<<",PASS,"<<k<<','<<faulty.protection.inspections<<','<<s.checks<<','<<faulty.protection.history_writes<<','<<faulty.protection.fold_delta_xor_inputs<<','<<faulty.protection.source_decodes<<','<<faulty.protection.rebuild_steps<<','<<first_detected<<','<<(detected_control<0?-1:detected_control-injected_control)<<'\n';
    if(!out||!log)throw std::runtime_error("external write failure");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL_EXECUTION "<<e.what()<<'\n';return 1;}}
