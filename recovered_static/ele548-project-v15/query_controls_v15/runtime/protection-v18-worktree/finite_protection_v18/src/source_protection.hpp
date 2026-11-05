#pragma once
#include "vector_protection.hpp"
namespace bp::v18 {
// Finite source integration. Fault-triggered recovery keeps stale CPU BIs in
// fallback until committed refill AND an actual full receiver/CPU drain ACK.
// It does not need to trust stale rollback operands during this interval.
class FiniteProtection:public SourceGuard {
 struct Action {bool pending=false,authorized=false;uint32_t token=0,residual=0,authorized_token=0;};
 Cell action_{89};bool hold_=false;Words sampled_{};bool direct_;
 static Word pack(Action a){Word w;w.set(0,a.pending);put(w,1,32,a.token);put(w,33,23,a.residual);w.set(56,a.authorized);put(w,57,32,a.authorized_token);return w;}
 Action load(){bool fixed=false;auto w=action_.load(fixed);if(fixed){hold_=true;++metadata_repairs;}return {w.bit(0),w.bit(56),get(w,1,32),get(w,33,23),get(w,57,32)};}
 void store(Action a){action_.store(pack(a));}
 unsigned payload_bits()const{return direct_?146:346;}
 bool payload_bit(unsigned n)const{auto widths=unit_widths_;for(unsigned w=0;w<23;++w)if(!direct_||w>=21){if(n<widths[w])return sampled_[w].bit(n);n-=widths[w];}throw std::out_of_range("authorized source payload");}
 void payload_flip(unsigned n){for(unsigned w=0;w<23;++w)if(!direct_||w>=21){if(n<unit_widths_[w]){sampled_[w].flip(n);return;}n-=unit_widths_[w];}throw std::out_of_range("authorized source payload");}
 std::array<unsigned,23>unit_widths_;
 public:
 VectorProtection unit;
 uint64_t source_checks=0,source_repair_publications=0,suppressed_stale_source_ops=0,committed_refill_publications=0,publication_waits=0,metadata_repairs=0;
 FiniteProtection(std::array<unsigned,23>w,Protect p,bool direct=false,unsigned epoch_bits=32):direct_(direct),unit_widths_(w),unit(w,p,direct,epoch_bits){store({});}
 std::unique_ptr<SourceGuard> clone()const override{return std::make_unique<FiniteProtection>(*this);}
 bool authorize(Service&s,uint32_t token,bool lookup,unsigned kind,uint32_t version,const Words&actual)override{
  auto a=load();if(hold_)return false;
  if(a.authorized){if(a.authorized_token!=token||!unit.ready())return false;a.authorized=false;store(a);return true;}
  if(a.pending)return false;
  if(auto out=unit.take(token,version)){
   sampled_=out->words;++source_checks;
   for(unsigned w=0;w<23;++w)if((out->reset||((out->repair_mask>>w)&1))&&(!direct_||w>=21)){s.write_selected_word(w,out->words[w]);++source_repair_publications;}
   if(lookup&&out->reset){if(!unit.publish(token,version,sampled_,0,false))throw IntegrityError("reset encode without owned check slot");a.authorized=true;a.authorized_token=token;store(a);return false;}
   if(!lookup){a.pending=true;a.token=token;a.residual=out->residual;store(a);if(unit.fallback()&&(kind==unsigned(Kind::Append)||kind==unsigned(Kind::Undo)))++suppressed_stale_source_ops;}
   return true;
  }
  if(unit.ready())unit.sample(token,version,lookup,actual);return false;
 }
 const Words&sampled()const override{return sampled_;}
 void prefetch(uint32_t token,bool lookup,uint32_t version,const Words&actual)override{auto a=load();if(!hold_&&!a.pending&&!a.authorized&&unit.ready())unit.sample(token,version,lookup,actual);}
 bool can_publish(uint32_t token)override{auto a=load();const bool result=!hold_&&a.pending&&a.token==token&&unit.ready();if(!result)++publication_waits;return result;}
 void published(uint32_t token,unsigned kind,uint32_t version,const Words&actual)override{
  auto a=load();const bool history_update=kind==unsigned(Kind::CommittedHistory)||!unit.fallback()&&(kind==unsigned(Kind::Append)||kind==unsigned(Kind::Undo));if(hold_||!a.pending||a.token!=token||!unit.publish(token,version,actual,a.residual,history_update))throw IntegrityError("source publication did not own finite encoder");
  a.pending=false;store(a);if(kind==unsigned(Kind::CommittedHistory)){unit.committed_refill();++committed_refill_publications;}
 }
 void advance()override{if(hold_){hold_=false;return;}unit.advance();}
 void cancel_reads()override{unit.cancel_lookup();auto a=load();a.authorized=false;store(a);}
 bool fallback()override{return unit.fallback();}
 uint32_t epoch()override{return unit.epoch();}
 bool drained()override{auto a=load();return !hold_&&!a.pending&&!a.authorized&&unit.drained();}
 void acknowledge_refill_and_epoch_drained(){if(!drained())throw IntegrityError("protection ACK before source drain");if(unit.wrap_waiting())unit.acknowledge_epoch_drained();unit.acknowledge_refill_drained();}
 std::vector<Region> manifest()const override{
  std::vector<Region> out;size_t at=0;for(auto&r:unit.manifest()){out.push_back({r.name,at,r.bits});at+=r.bits;}
  out.push_back({"protect_source_action_mirrored_SECDED",at,action_.bits()});at+=action_.bits();out.push_back({"protect_source_action_hold",at++,1});out.push_back({"protect_authorized_source_payload",at,payload_bits()});return out;
 }
 size_t bits()const override{auto m=manifest();return m.back().start+m.back().bits;}
 bool logical_bit(size_t n)const override{if(n>=bits())throw std::out_of_range("finite source protection bit");if(n<unit.bits())return unit.logical_bit(n);n-=unit.bits();if(n<action_.bits())return action_.bit(n);n-=action_.bits();if(!n)return hold_;return payload_bit(n-1);}
 void corrupt(const std::vector<size_t>&ids)override{
  std::set<size_t> unique;for(auto n:ids)if(n>=bits()||!unique.insert(n).second)throw std::invalid_argument("finite source protection atomic sites");
  for(auto n:ids){if(n<unit.bits()){unit.corrupt({n});continue;}n-=unit.bits();if(n<action_.bits()){action_.flip(n);continue;}n-=action_.bits();if(!n)hold_=!hold_;else payload_flip(n-1);}
 }
};
}
