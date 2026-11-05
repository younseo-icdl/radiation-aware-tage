#pragma once
#include "service.hpp"
namespace bp::v18 {
enum class Protect {P0,Parity,Periodic,Ecc,Tmr};
// One real vector decode/encode stage. Source ports, version validation and
// source writeback belong to the caller; this component cannot inspect events.
class VectorProtection {
 public:
 using Words=std::array<Word,23>;
 struct Result {Words words;uint32_t token,version,epoch,residual,repair_mask;bool reset;};
 struct Counters {uint64_t sampled=0,decoded=0,inspected=0,encoded=0,detected=0,corrected=0,due=0,repairs=0,stale=0,cancelled=0,unit_busy=0,sidecar_reads=0,sidecar_writes=0,word_reads=0,word_writes=0,metadata_repairs=0,resets=0,wraps=0; } stats;
 private:
 struct Meta {unsigned phase=0;uint32_t token=0,version=0,epoch=0,residual=0,mask=0;bool lookup=false,bad=false;};
 struct Control {uint32_t epoch=0;unsigned progress=0,refill=0;bool active=false,wrap=false;};
 Cell meta_{146},control_{49};bool hold_=false;
 Words frame_{},rep1_{},rep2_{},frame_rep1_{},frame_rep2_{};
 std::array<uint16_t,23> check_{},frame_check_{};
 std::array<unsigned,23> widths_;std::vector<WordSecded> codes_;
 Protect policy_;bool direct_;unsigned epoch_mask_;
 static Word pack(Meta m){Word w;put(w,0,2,m.phase);put(w,2,32,m.token);put(w,34,32,m.version);put(w,66,32,m.epoch);put(w,98,23,m.residual);put(w,121,23,m.mask);w.set(144,m.lookup);w.set(145,m.bad);return w;}
 static Meta unpack(Word w){return {get(w,0,2),get(w,2,32),get(w,34,32),get(w,66,32),get(w,98,23),get(w,121,23),w.bit(144),w.bit(145)};}
 Word read(Cell&c){bool repaired=false;auto w=c.load(repaired);if(repaired){hold_=true;++stats.metadata_repairs;}return w;}
 Meta meta(){return unpack(read(meta_));}
 Control control(){auto w=read(control_);Control c{get(w,0,32),get(w,32,7),get(w,39,8),w.bit(47),w.bit(48)};if(c.progress>64||c.refill>130||c.epoch>epoch_mask_)throw IntegrityError("protection control encoding");return c;}
 void store(Meta m){meta_.store(pack(m));}
 void store(Control c){Word w;put(w,0,32,c.epoch);put(w,32,7,c.progress);put(w,39,8,c.refill);w.set(47,c.active);w.set(48,c.wrap);control_.store(w);}
 bool selected(unsigned w)const{return !direct_||w>=21;}
 unsigned check_width(unsigned w)const{return policy_==Protect::Ecc?codes_[w].r+1:(policy_==Protect::Parity||policy_==Protect::Periodic?1:0);}
 bool payload_bit(const Words&a,unsigned n)const{for(unsigned w=0;w<23;++w)if(selected(w)){if(n<widths_[w])return a[w].bit(n);n-=widths_[w];}throw std::out_of_range("protection vector payload bit");}
 void payload_flip(Words&a,unsigned n){for(unsigned w=0;w<23;++w)if(selected(w)){if(n<widths_[w]){a[w].flip(n);return;}n-=widths_[w];}throw std::out_of_range("protection vector flip");}
 bool check_bit(const std::array<uint16_t,23>&a,unsigned n)const{for(unsigned w=0;w<23;++w)if(selected(w)){auto width=check_width(w);if(n<width)return(a[w]>>n)&1;n-=width;}throw std::out_of_range("protection sidecar bit");}
 void check_flip(std::array<uint16_t,23>&a,unsigned n){for(unsigned w=0;w<23;++w)if(selected(w)){auto width=check_width(w);if(n<width){a[w]^=uint16_t(1u<<n);return;}n-=width;}throw std::out_of_range("protection sidecar flip");}
 public:
 VectorProtection(std::array<unsigned,23> widths,Protect policy,bool direct=false,unsigned epoch_bits=32):widths_(widths),policy_(policy),direct_(direct),epoch_mask_(epoch_bits==32?~0u:(1u<<epoch_bits)-1){
  if(epoch_bits<2||epoch_bits>32||direct&&policy!=Protect::P0)throw std::invalid_argument("protection configuration");
  unsigned sum=0;for(auto width:widths_){codes_.emplace_back(width);sum+=width;}if(sum!=346||widths_[21]!=130||widths_[22]!=16)throw std::invalid_argument("protection S* geometry");store(Meta{});store(Control{});
 }
 unsigned payload_bits()const{return direct_?146:346;}
 unsigned check_bits()const{unsigned n=0;for(unsigned w=0;w<23;++w)if(selected(w))n+=check_width(w);return n;}
 bool ready(){auto m=meta();auto c=control();return !hold_&&!m.phase&&!c.wrap;}
 bool sample(uint32_t token,uint32_t version,bool lookup,const Words&actual){
  if(!ready()){++stats.unit_busy;return false;}for(unsigned w=0;w<23;++w)if(!actual[w].fits(widths_[w]))throw IntegrityError("sample outside logical vector width");
  frame_=actual;frame_check_=check_;if(policy_==Protect::Tmr){frame_rep1_=rep1_;frame_rep2_=rep2_;}
  auto c=control();store(Meta{1,token,version,c.epoch,0,0,lookup,false});++stats.sampled;stats.word_reads+=direct_?2:23;return true;
 }
 // Explicit edge: neither sample() nor take() performs decode or encode.
 void advance(){
  if(hold_){hold_=false;return;}auto m=meta();auto c=control();if(hold_)return;
  if(m.phase==1){
   const bool inspect=policy_!=Protect::Periodic||m.lookup&&c.progress>=64;
   if(inspect&&policy_!=Protect::P0)++stats.inspected;
   if(policy_==Protect::Periodic&&inspect)c.progress=0;
   for(unsigned w=0;w<23;++w)if(selected(w)){
    if(policy_==Protect::Parity||policy_==Protect::Periodic){
     if(policy_==Protect::Periodic&&m.lookup&&!inspect)continue;
     const bool bad=frame_[w].parity()^bool(frame_check_[w]);m.residual|=uint32_t(bad)<<w;++stats.sidecar_reads;
     if(inspect&&bad){++stats.detected;m.bad=true;}
    }else if(policy_==Protect::Ecc){auto d=codes_[w].decode(frame_[w],frame_check_[w]);++stats.sidecar_reads;
     if(d.due){++stats.due;++stats.detected;m.bad=true;}
     else if(d.corrected){++stats.detected;++stats.corrected;m.mask|=1u<<w;frame_[w]=d.payload;frame_check_[w]=d.check;}
    }else if(policy_==Protect::Tmr){auto vote=majority(frame_[w],frame_rep1_[w],frame_rep2_[w]);
     if(frame_[w]!=frame_rep1_[w]||frame_[w]!=frame_rep2_[w]){++stats.detected;++stats.corrected;m.mask|=1u<<w;frame_[w]=frame_rep1_[w]=frame_rep2_[w]=vote;}}
   }
   if(m.bad){c.active=true;c.refill=130;if(c.epoch==epoch_mask_)c.wrap=true;else ++c.epoch;frame_={};m.epoch=c.epoch;m.residual=0;m.mask=0;++stats.resets;}
   ++stats.decoded;m.phase=2;store(m);store(c);
  }else if(m.phase==3){
   for(unsigned w=0;w<23;++w)if(selected(w)){
    if(policy_==Protect::Parity||policy_==Protect::Periodic){check_[w]=frame_[w].parity()^bool((m.residual>>w)&1);++stats.sidecar_writes;}
    else if(policy_==Protect::Ecc){check_[w]=codes_[w].encode(frame_[w]);++stats.sidecar_writes;}
    else if(policy_==Protect::Tmr){rep1_[w]=rep2_[w]=frame_[w];stats.word_writes+=2;}
   }
   if(policy_==Protect::Periodic&&!m.bad&&c.progress<64)++c.progress;++stats.encoded;store(Meta{});store(c);
  }
 }
 std::optional<Result> take(uint32_t token,uint32_t current_version){
  auto m=meta();auto c=control();if(hold_||m.phase!=2||m.token!=token)return {};
  if(m.version!=current_version||m.epoch!=c.epoch&&!m.bad){++stats.stale;store(Meta{});return {};}
  Result result{frame_,m.token,m.version,m.epoch,m.residual,m.mask,m.bad};
  // The caller must own the real publication port before this operation.
  for(unsigned w=0;w<23;++w)if((m.mask>>w)&1){if(policy_==Protect::Ecc)check_[w]=frame_check_[w];else if(policy_==Protect::Tmr)rep1_[w]=rep2_[w]=frame_[w];++stats.repairs;}
  store(Meta{});return result;
 }
 bool publish(uint32_t token,uint32_t version,const Words&actual,uint32_t residual=0,bool count_history_update=true){
  if(!ready())return false;frame_=actual;auto c=control();store(Meta{3,token,version,c.epoch,residual,0,false,!count_history_update});return true;
 }
 void cancel(uint32_t token){auto m=meta();if(m.phase&&m.token==token){store(Meta{});++stats.cancelled;}}
 void cancel_lookup(){auto m=meta();if(m.phase&&m.lookup){store(Meta{});++stats.cancelled;}}
 uint32_t epoch(){return control().epoch;}
 unsigned refill_remaining(){return control().refill;}
 bool fallback(){auto c=control();return c.active||c.refill||c.wrap;}
 bool wrap_waiting(){return control().wrap;}
 void acknowledge_epoch_drained(){auto c=control();if(!c.wrap||meta().phase)throw IntegrityError("protection epoch ACK without full component drain");c.wrap=false;c.epoch=0;store(c);++stats.wraps;}
 void committed_refill(){auto c=control();if(c.refill)--c.refill;store(c);}
 void acknowledge_refill_drained(){auto c=control();if(c.refill||meta().phase)throw IntegrityError("premature refill ACK");c.active=false;store(c);}
 unsigned phase(){return meta().phase;}
 bool drained(){auto m=meta();(void)control();return !hold_&&!m.phase;}
 struct Region {std::string name;size_t start,bits;};
 std::vector<Region> manifest()const{
  std::vector<Region> out;size_t n=0;auto add=[&](std::string name,size_t bits){if(bits){out.push_back({name,n,bits});n+=bits;}};
  add("protect_stage_metadata_mirrored_SECDED",meta_.bits());add("protect_control_mirrored_SECDED",control_.bits());add("protect_metadata_hold",1);
  add("protect_stage_payload",payload_bits());add("protect_sidecars",check_bits());add("protect_stage_sidecars",check_bits());
  if(policy_==Protect::Tmr){add("protect_replica1",payload_bits());add("protect_replica2",payload_bits());add("protect_stage_replica1",payload_bits());add("protect_stage_replica2",payload_bits());}return out;
 }
 size_t bits()const{auto m=manifest();return m.back().start+m.back().bits;}
 bool logical_bit(size_t n)const{
  if(n>=bits())throw std::out_of_range("protection logical bit");if(n<meta_.bits())return meta_.bit(n);n-=meta_.bits();if(n<control_.bits())return control_.bit(n);n-=control_.bits();if(!n)return hold_;--n;
  if(n<payload_bits())return payload_bit(frame_,n);n-=payload_bits();
  if(n<check_bits())return check_bit(check_,n);n-=check_bits();if(n<check_bits())return check_bit(frame_check_,n);n-=check_bits();
  for(const Words*a:{&rep1_,&rep2_,&frame_rep1_,&frame_rep2_}){if(n<payload_bits())return payload_bit(*a,n);n-=payload_bits();}throw std::logic_error("protection manifest traversal");
 }
 void corrupt(const std::vector<size_t>&ids){
  std::set<size_t> unique;for(auto n:ids)if(n>=bits()||!unique.insert(n).second)throw std::invalid_argument("protection atomic logical sites");
  for(auto n:ids){if(n<meta_.bits()){meta_.flip(n);continue;}n-=meta_.bits();if(n<control_.bits()){control_.flip(n);continue;}n-=control_.bits();if(!n){hold_=!hold_;continue;}--n;
   if(n<payload_bits()){payload_flip(frame_,n);continue;}n-=payload_bits();if(n<check_bits()){check_flip(check_,n);continue;}n-=check_bits();if(n<check_bits()){check_flip(frame_check_,n);continue;}n-=check_bits();
   for(Words*a:{&rep1_,&rep2_,&frame_rep1_,&frame_rep2_}){if(n<payload_bits()){payload_flip(*a,n);break;}n-=payload_bits();}
  }
 }
};
}
