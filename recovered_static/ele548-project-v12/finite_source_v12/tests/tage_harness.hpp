#pragma once
#include "service.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <random>

namespace bp::v12::test {
// Verification harness, NOT a gem5 timing backend. Host-only raw/fold helper
// arrays are kept for the original upstream API/snapshot/getGHR. The actual
// authoritative source is Service. Addresses are computed only from a real
// staged read reply; no injector/golden data enters production service.
class Core:public bp::RoundState {
 unsigned pcbit_=0;Mode mode_;
 static gem5::TAGEBaseParams parameters(bool spec){gem5::TAGEBaseParams p;p.speculativeHistUpdate=spec;p.histBufferSize=4096;return p;}
 static std::vector<Geometry> geometry(const bp::RoundState&s){auto words=s.history_words();std::vector<Geometry> out;for(unsigned w=0;w<21;++w)out.push_back({s.fold_length(w),words[w].width});return out;}
 void sync_observer_helpers(){
  const auto image=service.observe_source();auto&h=this->threadHistory[0];h.ptGhist=0;h.pathHist=image.path;
  for(unsigned i=0;i<130;++i)h.globalHist[i]=image.raw[i];
  if(mode_!=Mode::Direct)install_folds(image.folds);
 }
 void install_folds(const std::array<unsigned,21>&v){for(unsigned w=0;w<21;++w){bp::Word x;x.limb[0]=v[w];this->write_history_word(w,x);}}
 public:
 Service service;
 explicit Core(Mode mode,unsigned L,bool spec=false):bp::RoundState(parameters(spec)),mode_(mode),service(mode,geometry(*this),L,L){}
 Reply operation(Kind kind,unsigned n=0,unsigned bits=0,unsigned arg=0){
  std::optional<Token> t;
  for(unsigned i=0;i<10000&&!t;++i){t=service.accept(kind,n,bits,arg);if(!t){if(service.drained()&&service.wrap_waiting())service.acknowledge_receiver_drained();service.tick();}}
  if(!t)throw std::runtime_error("TAGE harness command admission timeout");
  for(unsigned i=0;i<10000;++i){if(auto r=service.take(t)){if(!service.conserved())throw std::runtime_error("TAGE harness lost source work");return *r;}service.tick();}
  throw std::runtime_error("TAGE harness source response timeout");
 }
 void calculateIndicesAndTags(gem5::ThreadID tid,gem5::Addr pc,bp::Base::BranchInfo*bi)override{
  auto r=operation(Kind::Read);sync_observer_helpers();install_folds(r.folds);this->threadHistory[tid].pathHist=r.path;
  bp::RoundState::calculateIndicesAndTags(tid,pc,bi);
 }
 void updateGHist(gem5::ThreadID tid,uint64_t bits,uint8_t n)override{
  if(!n)return;if(tid||n>2)throw std::invalid_argument("plain TAGE harness scope");
  operation(Kind::Append,n,unsigned(bits&3),pcbit_);sync_observer_helpers();
 }
 void recordHistState(gem5::ThreadID tid,bp::Base::BranchInfo*bi)override{sync_observer_helpers();bp::RoundState::recordHistState(tid,bi);}
 void restoreHistState(gem5::ThreadID tid,bp::Base::BranchInfo*bi)override{
  if(!this->speculativeHistUpdate||!bi->modified)return;
  const auto n=bi->nGhist;operation(Kind::Undo,n,0,bi->pathHist);sync_observer_helpers();
  if(n){bi->nGhist=0;bi->modified=false;}
 }
 void updatePathAndGlobalHistory(gem5::ThreadID tid,int brtype,bool taken,gem5::Addr pc,gem5::Addr target,bp::Base::BranchInfo*bi)override{
  pcbit_=(pc>>this->instShiftAmt)&1;
  bp::RoundState::updatePathAndGlobalHistory(tid,brtype,taken,pc,target,bi);
 }
 void commit_record(bp::Base::BranchInfo*bi){for(unsigned i=0;i<10000;++i){if(service.retire(bi->nGhist))return;service.tick();}throw std::runtime_error("retire control timeout");}
 void refresh_for_comparison(){auto r=operation(Kind::Read);sync_observer_helpers();install_folds(r.folds);}
 struct Snapshot {bp::RoundState::Snapshot helper;Service source;unsigned pcbit;};
 Snapshot snapshot()const{return {save(),service,pcbit_};}
 void restore(const Snapshot&s){if(s.source.bits()!=service.bits())throw std::invalid_argument("harness snapshot geometry");load(s.helper);service=s.source;pcbit_=s.pcbit;}
 void inject(const std::vector<size_t>&ids){
  auto all=sites();std::set<size_t> unique;std::vector<size_t> table,history;
  auto region=[&](const std::string&name){for(auto&r:service.manifest())if(r.name==name)return r.start;throw std::invalid_argument("inactive history field");};
  size_t fold_offset=0;for(auto id:ids){if(id>=all.size()||!unique.insert(id).second)throw std::invalid_argument("bad atomic predictor event");const auto&s=all[id];
   if(s.kind<4)table.push_back(id);
   else if(s.kind==4)history.push_back(s.bank?region("path")+s.bit:service.active_raw_site(s.row));
   else {
    if(mode_==Mode::Direct)throw std::invalid_argument("direct fold has no physical site");
    fold_offset=0;for(auto&v:all){if(v.id==id)break;if(v.kind==5)++fold_offset;}history.push_back(region("fold")+fold_offset);
   }
  }
  // All IDs/aliases validated before either storage domain is changed.
  bp::RoundState::corrupt(table);service.corrupt(history);sync_observer_helpers();
 }
};
inline void compare(Core&dut,const bp::RoundState&ref){
 dut.refresh_for_comparison();auto a=dut.save(),b=ref.save();auto image=dut.service.observe_source();
 if(a.pred!=b.pred||a.hyst!=b.hyst||a.path!=b.path||a.non_spec!=b.non_spec||a.aging!=b.aging||a.alt!=b.alt||a.folded!=b.folded)throw std::runtime_error("finite TAGE logical state mismatch");
 for(unsigned age=0;age<130;++age)if(image.raw[age]!=ref.raw_bit(age))throw std::runtime_error("finite TAGE source mismatch");
 if(dut.getGHR(0)!=ref.getGHR(0))throw std::runtime_error("finite GHR mismatch");
 for(unsigned bank=1;bank<a.tables.size();++bank)for(unsigned row=0;row<a.tables[bank].size();++row){auto x=a.tables[bank][row],y=b.tables[bank][row];if(x.ctr!=y.ctr||x.tag!=y.tag||x.u!=y.u)throw std::runtime_error("finite TAGE training mismatch");}
}
inline void compare_prediction(const bp::Base::BranchInfo&a,const bp::Base::BranchInfo&b,bool conditional){
 if(!conditional)return;
 if(a.tagePred!=b.tagePred||a.provider!=b.provider||a.hitBank!=b.hitBank||a.altBank!=b.altBank)throw std::runtime_error("finite TAGE prediction/provider mismatch");
 for(unsigned bank=1;bank<=7;++bank)if(a.tableIndices[bank]!=b.tableIndices[bank]||a.tableTags[bank]!=b.tableTags[bank])throw std::runtime_error("finite TAGE address mismatch");
}
}
