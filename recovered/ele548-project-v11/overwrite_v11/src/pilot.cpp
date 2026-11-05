#include "model.hpp"
#include "replay/e1_trace.hpp"
#include <fstream>
#include <optional>
#include <memory>
#include <iomanip>
#include <iostream>

using bp::v11::BaselineAdapter;using bp::v11::OverwriteAdapter;
static void need(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
struct Saved {
  bp::RoundState::Snapshot state;std::mt19937_64 rng;
  std::optional<bp::RoundHistory::Snapshot> protection;
  std::optional<bp::v5::State::SourceSnapshot> direct;
};
class Model {
 public:
  unsigned kind;
  std::unique_ptr<BaselineAdapter> base;
  std::unique_ptr<OverwriteAdapter> overwrite;
  std::unique_ptr<bp::v5::Adapter> direct;
  explicit Model(unsigned k):kind(k) {
    if(k==5)direct=std::make_unique<bp::v5::Adapter>("direct");
    else if(k==6)overwrite=std::make_unique<OverwriteAdapter>();
    else {
      const bp::Scheme scheme[]={bp::Scheme::P0,bp::Scheme::ED,bp::Scheme::ED,bp::Scheme::ECC,bp::Scheme::TMR};
      base=std::make_unique<BaselineAdapter>(scheme[k],k==2?bp::RoundPolicy::N1:bp::RoundPolicy::LEGACY,k==2?64:0);
    }
  }
  bool step(const bp::Branch& b) {return direct?direct->step(b):overwrite?overwrite->step(b):base->step(b);}
  Saved save()const {
    if(direct)return {direct->core.save(),direct->rng,{},direct->core.source_save()};
    if(overwrite)return {overwrite->core.save(),overwrite->rng,overwrite->protection.snapshot(),{}};
    return {base->core.save(),base->rng,base->protection.snapshot(),{}};
  }
  void load(const Saved& s) {
    if(direct) {direct->core.load(s.state);direct->core.source_restore(*s.direct);direct->rng=s.rng;}
    else if(overwrite) {overwrite->core.load(s.state);overwrite->protection.restore(*s.protection);overwrite->rng=s.rng;overwrite->core.activity={};}
    else {base->core.load(s.state);base->protection.restore(*s.protection);base->rng=s.rng;}
  }
  bool bit(const bp::Site& s)const {
    if(direct) {
      if(s.kind==4&&!s.bank)return direct->core.ring_bit(s.row);
      return (direct->core.payload(s)>>s.bit)&1u;
    }
    auto& c=overwrite?static_cast<bp::RoundState&>(overwrite->core):base->core;
    return (c.payload(s)>>s.bit)&1u;
  }
  void inject(const bp::Site& s) {
    bool before=bit(s);
    if(direct)direct->core.corrupt({s.id});
    else if(overwrite)overwrite->protection.corrupt({s.id});
    else base->protection.corrupt({s.id});
    need(before!=bit(s),"logical SBU did not XOR");
  }
};
struct WindowResult {uint64_t misses=0,conditionals=0,pred_hash=14695981039346656037ULL;};
static WindowResult replay(Model& m,const bp::E1Trace&t,size_t begin,size_t end) {
  WindowResult r;
  for(size_t i=begin;i<end;++i) {
    auto& b=t.controls[i].branch;bool p=m.step(b);
    if(b.conditional){++r.conditionals;r.misses+=p!=b.taken;r.pred_hash^=p;r.pred_hash*=1099511628211ULL;}
  }
  return r;
}
int main(int argc,char**argv) {try {
  need(argc==4,"usage pilot TRACE1 TRACE2 OUTPUT_CSV");
  std::ofstream out(argv[3]);need(bool(out),"output CSV unavailable");out<<std::setprecision(17);
  out<<"trace,field,owner,logical_id,bank,row,bit,mode,status,event_control_index,horizon_controls,conditional_branches,instruction_records,clean_misses,fault_misses,delta_misses,delta_MPKI,clean_prediction_hash,fault_prediction_hash,overwrite_forward_calls,overwrite_tap_terms,overwrite_source_bits,overwrite_fold_bit_writes\n";
  const char* names[]={"P0","P_ED_FREQUENT","P_ED_PERIODIC64","P_ECC","P_TMR","DIRECT","OVERWRITE"};
  const unsigned raw_positions[]={0,16,64,129},fold_positions[]={0,49,99,199},offsets[]={0,127,511,999};
  constexpr size_t warm=20000,H=10000;
  uint64_t actual=0,removed=0,normal_windows=0;
  for(unsigned wi=0;wi<2;++wi) {
    auto t=bp::read_e1_trace(argv[wi+1]);need(t.controls.size()>warm+1000+H,"real trace too short");
    std::vector<std::unique_ptr<Model>> models;std::vector<Saved> snapshots;
    for(unsigned k=0;k<7;++k) {
      models.push_back(std::make_unique<Model>(k));replay(*models.back(),t,0,warm);snapshots.push_back(models.back()->save());
    }
    need(snapshots[0].rng==snapshots[6].rng,"normal predictor RNG differs");
    auto all=models[0]->base->core.sites();std::vector<bp::Site> raw,fold;
    for(auto s:all) {if(s.kind==4&&!s.bank)raw.push_back(s);if(s.kind==5)fold.push_back(s);}
    need(raw.size()==130&&fold.size()==200,"logical geometry changed");
    for(unsigned field=0;field<2;++field)for(unsigned owner=0;owner<4;++owner) {
      size_t begin=warm+offsets[owner],end=begin+H;
      const auto& s=field?fold.at(fold_positions[owner]):raw.at(raw_positions[owner]);
      const uint64_t instructions=t.controls[end-1].instruction-t.controls[begin].instruction+1;
      std::optional<WindowResult> normal_reference;
      for(unsigned k=0;k<7;++k) {
        auto& m=*models[k];m.load(snapshots[k]);replay(m,t,warm,begin);
        auto before=m.save();auto clean=replay(m,t,begin,end);++normal_windows;
        if(!normal_reference)normal_reference=clean;
        need(clean.misses==normal_reference->misses&&clean.pred_hash==normal_reference->pred_hash,"seven-way clean prediction mismatch");
        m.load(before);
        const bool not_exposed=k==5&&field==1;
        out<<wi<<','<<(field?"FOLD":"RAW")<<','<<owner<<','<<s.id<<','<<s.bank<<','<<s.row<<','<<s.bit<<','<<names[k]<<',';
        if(not_exposed) {
          ++removed;out<<"STRUCTURALLY_REMOVED_NOT_EXPOSED,"<<begin<<','<<H<<','<<clean.conditionals<<','<<instructions<<','<<clean.misses<<",,,,"<<clean.pred_hash<<",,,,,\n";
          continue;
        }
        m.inject(s);auto faulty=replay(m,t,begin,end);++actual;
        const int64_t delta=int64_t(faulty.misses)-int64_t(clean.misses);
        out<<"PASS_REAL_TRACE_CPP_NOT_CPU_CYCLES,"<<begin<<','<<H<<','<<clean.conditionals<<','<<instructions<<','<<clean.misses<<','<<faulty.misses<<','<<delta<<','<<1000.0*delta/instructions<<','<<clean.pred_hash<<','<<faulty.pred_hash;
        if(k==6) {const auto&a=m.overwrite->core.activity;out<<','<<a.forward_calls<<','<<a.fold_tap_terms<<','<<a.source_bits_sampled<<','<<a.fold_bit_writes;}
        else out<<",,,,";
        out<<'\n';
      }
    }
  }
  out.close();need(bool(out),"CSV write failed");
  std::cout<<"{\"status\":\"PASS_REAL_TRACE_DEVELOPMENT_CPP_PILOT_NOT_CPU_PERFORMANCE\",\"owner_cases\":16,\"planned_rows\":112,\"actual_fault_replays\":"<<actual<<",\"structurally_removed_rows\":"<<removed<<",\"normal_windows\":"<<normal_windows<<",\"warmup_controls\":"<<warm<<",\"post_event_controls\":"<<H<<",\"event_distribution\":\"predeclared_fixed_sites_offsets_not_random_population\",\"cpu_simulations\":0}\n";
  return 0;
} catch(const std::exception&e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
