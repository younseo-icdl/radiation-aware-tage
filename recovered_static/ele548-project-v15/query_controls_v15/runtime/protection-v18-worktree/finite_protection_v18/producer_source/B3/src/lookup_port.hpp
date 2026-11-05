#pragma once
#include "service.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_pipeline_v9/payload.hpp"
namespace bp::v18b3 {
// Clocked source-fold -> table/provider boundary, NOT an O3 integration.
// Source sampling/reduction is Service's real L1/2. One additional actual
// table/provider edge consumes the stored reply, with four physical contexts.
// Callback receives only the ACTUAL PC/type/fold/path operands. It must execute
// the pinned index/tag/provider logic and must not update speculative history.
class LookupPort {
 struct Context {Cell meta{132};std::array<unsigned,21> fold{};unsigned path=0;v9::Payload result;};
 struct Meta {unsigned phase=0;Token token{};uint64_t pc=0;bool conditional=false;uint32_t protection_epoch=0;};
 std::array<Context,4> contexts_;
 Cell control_{1};uint64_t hold_until_=0;
 static Word pack(Meta m){Word w;put(w,0,2,m.phase);put(w,2,32,m.token.packed());put(w,34,32,uint32_t(m.pc));put(w,66,32,uint32_t(m.pc>>32));w.set(98,m.conditional);put(w,100,32,m.protection_epoch);return w;}
 // Bit99 is an explicitly allocated zero-reserved physical metadata bit;
 // a valid nonzero reserved bit after decoding fails closed.
 Meta load(Context&c){bool repair=false;auto w=c.meta.load(repair);if(repair)hold();if(w.bit(99))throw IntegrityError("lookup reserved metadata encoding");return {get(w,0,2),Token::unpack(get(w,2,32)),uint64_t(get(w,34,32))|(uint64_t(get(w,66,32))<<32),w.bit(98),get(w,100,32)};}
 static void store(Context&c,Meta m){c.meta.store(pack(m));}
 Word ctl(){bool repair=false;auto w=control_.load(repair);if(repair)hold();return w;}
 void hold(){++metadata_repairs;hold_until_=std::max(hold_until_,source.cycle()+1);}
 bool poll(){try{ctl();for(auto&c:contexts_)load(c);return source.cycle()>=hold_until_;}catch(const v9::MirrorUncorrectable&e){++integrity_failures;throw IntegrityError(e.what());}}
 unsigned fold_bit(const Context&c,unsigned n)const{for(unsigned w=0;w<21;++w){if(n<geometry_[w].width)return (c.fold[w]>>n)&1;n-=geometry_[w].width;}throw std::out_of_range("context fold bit");}
 void flip_fold(Context&c,unsigned n){for(unsigned w=0;w<21;++w){if(n<geometry_[w].width){c.fold[w]^=1u<<n;return;}n-=geometry_[w].width;}throw std::out_of_range("context fold bit");}
 std::vector<Geometry> geometry_;
 public:
 Service source;
 uint64_t accepted=0,produced=0,consumed=0,cancelled=0,acks=0,full_stalls=0,metadata_repairs=0,integrity_failures=0;
 uint64_t stale_protection_responses=0;
 uint32_t protection_epoch(){return source.guard()?source.guard()->epoch():0;}
 LookupPort(Mode mode,std::vector<Geometry> g,unsigned UL=1,unsigned QL=1,unsigned id_bits=16,unsigned epoch_bits=16):geometry_(g),source(mode,g,UL,QL,1,id_bits,epoch_bits){control_.store({});for(auto&c:contexts_)store(c,{});}
 std::optional<Token> request(uint64_t pc,bool conditional){
  if(!poll())return {};Context* free=nullptr;for(auto&c:contexts_)if(!load(c).phase){free=&c;break;}
  if(!free){++full_stalls;return {};}
  auto t=source.accept(Kind::Read);if(!t)return {};
  store(*free,{1,*t,pc,conditional});++accepted;return t;
 }
 struct NoAck {void operator()(const Reply&)const{}};
 template<class Provider,class Ack=NoAck> void advance(Provider provider,Ack ack={}){
  source.tick();if(!poll())return;control_.store({});
  Context* next=nullptr;Meta chosen;
  for(auto&c:contexts_){auto m=load(c);if(m.phase==3&&m.protection_epoch!=protection_epoch()){m.phase=2;store(c,m);++stale_protection_responses;}if(m.phase==2&&(!next||m.token.packed()<chosen.token.packed())){next=&c;chosen=m;}}
  // One actual provider port; no provider invocation at request admission.
  if(next){next->result=provider(chosen.pc,chosen.conditional,next->fold,next->path);chosen.phase=3;chosen.protection_epoch=protection_epoch();store(*next,chosen);++produced;}
  // At most one read and one independent source ACK can leave the component
  // on this edge. A newly latched fold reply cannot use the provider above.
  for(unsigned port=0;port<2;++port){auto r=source.take();if(!r)break;if(r->kind!=Kind::Read){++acks;ack(*r);continue;}
   Context* target=nullptr;Meta m;
   for(auto&c:contexts_){auto x=load(c);if(x.phase==1&&x.token==r->token){target=&c;m=x;break;}}
   if(!target){++integrity_failures;throw IntegrityError("orphan fold reply at provider boundary");}
   target->fold=r->folds;target->path=r->path;m.phase=2;store(*target,m);
  }
 }
 struct Output {Token token;uint64_t pc;bool conditional;v9::Payload payload;unsigned path;};
 struct Descriptor {Token token;uint64_t pc;bool conditional;};
 std::vector<Descriptor> descriptors(){
  std::vector<Descriptor> out;if(!poll())return out;
  for(auto&c:contexts_){auto m=load(c);if(m.phase)out.push_back({m.token,m.pc,m.conditional});}
  std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.token.packed()<b.token.packed();});return out;
 }
 std::optional<Output> take(Token token,bool consume=true){
  if(!poll()||ctl().bit(0))return {};
  for(auto&c:contexts_){auto m=load(c);if(m.phase!=3||m.token!=token||m.protection_epoch!=protection_epoch())continue;
   if(!c.result.legal_response(m.conditional)){++integrity_failures;throw IntegrityError("invalid provider response encoding");}
   Output out{m.token,m.pc,m.conditional,c.result,c.path};if(!consume)return out;store(c,{});Word w;w.set(0,true);control_.store(w);++consumed;return out;
  }return {};
 }
 std::optional<Output> head(){if(!poll()||ctl().bit(0))return {};Context* first=nullptr;Meta best;for(auto&c:contexts_){auto m=load(c);if(m.phase&&(!first||m.token.packed()<best.token.packed())){first=&c;best=m;}}if(!first||best.phase!=3)return {};return take(best.token,false);}
 bool discard_ready(Token token){
  if(!poll()||ctl().bit(0))return false;
  for(auto&c:contexts_){auto m=load(c);if(m.phase==3&&m.token==token){store(c,{});Word w;w.set(0,true);control_.store(w);++cancelled;return true;}}
  return false;
 }
 void cancel(){
  // Actual receiver squash invalidates all unconsumed contexts. Source writes
  // and their ACKs remain in Service, and its repair-held cancel is latched.
  (void)poll();source.cancel_reads();for(auto&c:contexts_){if(load(c).phase)++cancelled;store(c,{});}
 }
 bool receiver_drained(){if(!poll())return false;for(auto&c:contexts_)if(load(c).phase)return false;return true;}
 bool acknowledge_wrap(){return receiver_drained()&&source.acknowledge_receiver_drained();}
 uint64_t pending()const{uint64_t n=0;for(auto&c:contexts_)n+=get(c.meta.a.data,0,2)!=0;return n;}
 bool conserved()const{return accepted==consumed+cancelled+pending()&&source.conserved();}
 std::vector<Service::Region> manifest()const{
  auto r=source.manifest();size_t at=source.bits();auto add=[&](std::string s,size_t bits){r.push_back({s,at,bits});at+=bits;};
  add("provider_control_mirrored_SECDED",control_.bits());
  for(unsigned i=0;i<4;++i){add("provider_context_metadata_"+std::to_string(i),contexts_[i].meta.bits());add("provider_fold_path_latch_"+std::to_string(i),216);add("provider_result_latch_"+std::to_string(i),contexts_[i].result.bits());}return r;
 }
 size_t bits()const{auto r=manifest();return r.back().start+r.back().bits;}
 bool logical_bit(size_t n)const{
  if(n>=bits())throw std::out_of_range("lookup port bit");if(n<source.bits())return source.logical_bit(n);n-=source.bits();
  if(n<control_.bits())return control_.bit(n);n-=control_.bits();
  for(auto&c:contexts_){if(n<c.meta.bits())return c.meta.bit(n);n-=c.meta.bits();if(n<216)return n<200?fold_bit(c,n):(c.path>>(n-200))&1;n-=216;if(n<c.result.bits())return c.result.bit(n);n-=c.result.bits();}throw std::logic_error("lookup manifest traversal");
 }
 void corrupt(const std::vector<size_t>&ids){
  std::set<size_t> distinct;for(auto n:ids)if(n>=bits()||!distinct.insert(n).second)throw std::invalid_argument("lookup atomic fault sites");
  for(auto n:ids){if(n<source.bits()){source.corrupt({n});continue;}n-=source.bits();if(n<control_.bits()){control_.flip(n);continue;}n-=control_.bits();
   for(auto&c:contexts_){if(n<c.meta.bits()){c.meta.flip(n);break;}n-=c.meta.bits();if(n<216){if(n<200)flip_fold(c,n);else c.path^=1u<<(n-200);break;}n-=216;if(n<c.result.bits()){c.result.flip(n);break;}n-=c.result.bits();}
  }
 }
};
}
