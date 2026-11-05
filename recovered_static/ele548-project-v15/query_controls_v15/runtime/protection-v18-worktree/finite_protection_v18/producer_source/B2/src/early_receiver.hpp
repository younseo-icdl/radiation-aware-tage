#pragma once
#include "controller.hpp"
namespace bp::v18 {
// Four real token/PC bindings. Simulator BI addresses are host associations to
// already CPU-owned branch records; no pointer bits are injected or used as
// recovery operands. Each association's hardware token/PC/valid is exposed.
class EarlyReceiver {
 struct Binding {bool valid=false;Token token{};uint64_t pc=0;};
 std::array<Cell,4> owners_{{Cell{97},Cell{97},Cell{97},Cell{97}}};
 Cell control_{1};Controller& controller_;uint64_t hold_until_=0;
 void hold(){++metadata_repairs;hold_until_=std::max(hold_until_,controller_.port.source.cycle()+1);}
 static Word pack(Binding b){Word w;w.set(0,b.valid);put(w,1,32,b.token.packed());put(w,33,32,uint32_t(b.pc));put(w,65,32,uint32_t(b.pc>>32));return w;}
 Binding load(unsigned i){bool repaired=false;auto w=owners_[i].load(repaired);if(repaired)hold();return {w.bit(0),Token::unpack(get(w,1,32)),uint64_t(get(w,33,32))|(uint64_t(get(w,65,32))<<32)};}
 bool cancelled(){bool repaired=false;auto w=control_.load(repaired);if(repaired)hold();return w.bit(0);}
 void set_cancel(bool v){Word w;w.set(0,v);control_.store(w);}
 bool poll(){try{
  cancelled();std::set<uint32_t> ids;
  for(unsigned i=0;i<4;++i){auto b=load(i);if(b.valid&&(!b.token.packed()||!ids.insert(b.token.packed()).second))throw IntegrityError("early binding token encoding");}
  return controller_.port.source.cycle()>=hold_until_;
 }catch(const v9::MirrorUncorrectable&e){throw IntegrityError(e.what());}}
 int owner(Token token){for(unsigned i=0;i<4;++i){auto b=load(i);if(b.valid&&b.token==token)return int(i);}return -1;}
 public:
 uint64_t claims=0,delivered=0,metadata_repairs=0,max_pending=0,deferred_cancels=0,discarded_unclaimed=0;
 explicit EarlyReceiver(Controller&c):controller_(c){for(auto&cell:owners_)cell.store({});control_.store({});}
 EarlyReceiver(const EarlyReceiver&)=delete;
 EarlyReceiver(const EarlyReceiver&o,Controller&c):owners_(o.owners_),control_(o.control_),controller_(c),hold_until_(o.hold_until_),claims(o.claims),delivered(o.delivered),metadata_repairs(o.metadata_repairs),max_pending(o.max_pending),deferred_cancels(o.deferred_cancels),discarded_unclaimed(o.discarded_unclaimed){}
 bool ready(){return poll()&&!cancelled();}
 unsigned pending(){if(!poll())return 4;unsigned n=0;for(unsigned i=0;i<4;++i)n+=load(i).valid;return n;}
 bool quiescent(){return ready()&&pending()==0;}
 bool claimable(Token t,uint64_t pc){
  if(!ready()||owner(t)>=0)return false;
  for(const auto&d:controller_.port.descriptors())if(d.token==t)return !d.conditional&&d.pc==pc;
  return false;
 }
 std::optional<unsigned> claim(uint64_t pc){
  if(!ready())return {};
  for(const auto&d:controller_.port.descriptors()){
   if(owner(d.token)>=0)continue;
   if(d.conditional||d.pc!=pc)throw IntegrityError("early claim PC/type/order mismatch");
   for(unsigned i=0;i<4;++i)if(!load(i).valid){owners_[i].store(pack({true,d.token,d.pc}));++claims;max_pending=std::max(max_pending,uint64_t(pending()));return i;}
   return {};
  }return {};
 }
 void cancel(){(void)poll();set_cancel(true);++deferred_cancels;}
 template<class Deliver>void advance(Deliver deliver){
  if(!poll())return;
  auto head=controller_.checkpoint_head();
  if(head){const int slot=owner(head->token);
   if(slot>=0){auto b=load(unsigned(slot));if(b.pc!=head->pc||head->conditional)throw IntegrityError("late checkpoint PC/type ownership");
    auto response=controller_.take_checkpoint(head->token);if(!response)throw IntegrityError("late checkpoint lost within consume");
    deliver(unsigned(slot),response->path);owners_[slot].store({});++delivered;
   }else if(cancelled()){
    if(!controller_.discard_checkpoint(head->token))throw IntegrityError("cancelled checkpoint discard failed");++discarded_unclaimed;
   }
  }
  if(cancelled()&&pending()==0){controller_.cancel();set_cancel(false);}
 }
 bool conserved(){return poll()&&claims==delivered+pending()&&controller_.conserved();}
 std::vector<Service::Region> manifest()const{
  std::vector<Service::Region> r;size_t at=0;
  for(unsigned i=0;i<4;++i){r.push_back({"early_checkpoint_owner_"+std::to_string(i),at,owners_[i].bits()});at+=owners_[i].bits();}
  r.push_back({"early_deferred_cancel",at,control_.bits()});return r;
 }
 size_t bits()const{auto r=manifest();return r.back().start+r.back().bits;}
 bool logical_bit(size_t n)const{if(n>=bits())throw std::out_of_range("early receiver bit");for(auto&c:owners_){if(n<c.bits())return c.bit(n);n-=c.bits();}return control_.bit(n);}
 void corrupt(const std::vector<size_t>&ids){std::set<size_t> unique;for(auto n:ids)if(n>=bits()||!unique.insert(n).second)throw std::invalid_argument("early atomic sites");for(auto n:ids){bool done=false;for(auto&c:owners_){if(n<c.bits()){c.flip(n);done=true;break;}n-=c.bits();}if(!done)control_.flip(n);}}
};
}
