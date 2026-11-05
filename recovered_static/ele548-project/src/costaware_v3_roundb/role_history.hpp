#pragma once
#include "history_access.hpp"
#include "../protection/history_controller.hpp"
#include <array>
#include <functional>
namespace bp {
enum class RoundPolicy { LEGACY,N1,H1,REV,STAGED };
enum class RoundTransition { Forward,Undo,Correct };
class RoundHistory {
 RoundAccess& core;
 std::vector<TageAccess::HistoryWord> words;
 std::vector<WordSecded> codecs;
 std::vector<uint16_t> checks;
 std::vector<Word> a,b;
 std::vector<Scheme> mode;
 std::vector<Site> sites;
 std::vector<StoredSite> extra;
 std::array<bool,23> delta{};
 bool writing=false;
 std::array<bool,23> full_before{};
 void reset_refill(){if(external_shadow){Word g;g.limb[0]=shadow_generation;auto d=generation_codec.decode(g,generation_check);shadow_generation=d.due?0:uint32_t(d.payload.limb[0]+1);g.limb[0]=shadow_generation;generation_check=generation_codec.encode(g);}if(policy==RoundPolicy::STAGED){stage_state={};stage_state.set(15,true);stage_check=stage_codec.encode(stage_state);}core.reset_selected_history();refill=130;++epoch;++stats.reset_refill;recovery_active=cpu_protocol;phase=scan=publish=retries=0;synchronize();if(policy==RoundPolicy::H1){shadow={};for(unsigned j=0;j<2;++j)shadow_check[j]=codecs[j+21].encode(shadow[j]);}if(on_reset)on_reset();}
 void start_rebuild(){++epoch;recovery_active=true;refill=0;phase=1;scan=publish=retries=0;++rebuild_requests;core.tagged_enabled(false);}
 void encode_word(unsigned w){auto d=core.read_history_word(w);if(mode[w]==Scheme::ED)checks[w]=d.parity();else if(mode[w]==Scheme::ECC)checks[w]=codecs[w].encode(d);else if(mode[w]==Scheme::TMR)a[w]=b[w]=d;}
 bool validate_shadow(){bool corrected=false;for(unsigned j=0;j<2;++j){++shadow_decodes;auto r=codecs[j+21].decode(shadow[j],shadow_check[j]);if(r.due){++stats.due;++stats.detected;reset_refill();return false;}if(r.corrected){++stats.corrected;++stats.detected;shadow[j]=r.payload;shadow_check[j]=r.check;corrected=true;}}if(corrected)++shadow_corrections;return true;}
 void clear_scan(){for(unsigned w=0;w<21;++w){acc[w]={};acc_parity[w]=false;}scan=publish=0;phase=2;}
 public:
 const Scheme scheme;const RoundPolicy policy;const bool cpu_protocol;const unsigned interval;const bool full_delta,reset_recovery,external_shadow;
 uint64_t full_reduction_bits=0;
 uint8_t refill=0,progress=0,phase=0,scan=0,publish=0,retries=0;uint32_t epoch=0;bool recovery_active=false;
 ProtectionStats stats;
 std::function<void()> on_reset;
 uint64_t skipped_calls=0;
 uint64_t history_writes=0,inspections=0,fold_delta_xor_inputs=0,raw_delta_xor_inputs=0,path_delta_xor_inputs=0;
 uint64_t source_decodes=0,source_encode_bits=0,shadow_decodes=0,shadow_corrections=0,shadow_encode_bits=0;
 uint64_t rebuild_requests=0,rebuild_steps=0,rebuild_source_bits=0,rebuild_xor_inputs=0,rebuild_writes=0,rebuild_restarts=0;
 Word stage_state{};uint16_t stage_check=0;WordSecded stage_codec{16};
 uint32_t shadow_generation=0;uint16_t generation_check=0;WordSecded generation_codec{32};
 std::array<Word,2> shadow{};std::array<uint16_t,2> shadow_check{};
 std::array<Word,21> acc{};std::array<bool,21> acc_parity{};
 explicit RoundHistory(RoundAccess& c,Scheme s,bool cpu=false,RoundPolicy p=RoundPolicy::LEGACY,unsigned k=0,bool full=false,bool reset=false,bool separate=false):core(c),words(c.history_words()),scheme(s),policy(p),cpu_protocol(cpu),interval(k),full_delta(full),reset_recovery(reset),external_shadow(separate){
  if((p==RoundPolicy::N1||p==RoundPolicy::H1||p==RoundPolicy::STAGED)&&(!k||k>64))throw std::invalid_argument("bounded interval1..64");
  for(auto& w:words)codecs.emplace_back(w.width);checks.resize(23);a.resize(23);b.resize(23);mode.assign(23,s);
  if((p==RoundPolicy::N1||p==RoundPolicy::STAGED))mode.assign(23,Scheme::ED);
  if(p==RoundPolicy::H1){mode.assign(23,Scheme::ED);mode[21]=mode[22]=Scheme::ECC;}
  if(p==RoundPolicy::REV){mode.assign(23,Scheme::ECC);mode[21]=mode[22]=Scheme::ED;}
  sites=core.sites();synchronize();size_t id=sites.size();
  for(unsigned w=0;w<23;++w){if(mode[w]==Scheme::ED||mode[w]==Scheme::ECC){unsigned width=mode[w]==Scheme::ED?1:codecs[w].r+1;for(unsigned bit=0;bit<width;++bit)extra.push_back({id++,mode[w]==Scheme::ED?"parity":"secded_check",w,bit,width,0});}}
  for(unsigned rep=1;rep<=2;++rep)for(unsigned w=0;w<23;++w)if(mode[w]==Scheme::TMR)for(unsigned bit=0;bit<words[w].width;++bit)extra.push_back({id++,"replica",w,bit,words[w].width,rep});
  if(s==Scheme::ED||s==Scheme::ECC||p!=RoundPolicy::LEGACY){for(unsigned bit=0;bit<8;++bit)extra.push_back({id++,"refill_remaining",0,bit,8,0});for(unsigned bit=0;bit<32;++bit)extra.push_back({id++,"history_epoch",0,bit,32,0});if(cpu)extra.push_back({id++,"recovery_active",0,0,1,0});}
  if(p==RoundPolicy::N1||p==RoundPolicy::H1||p==RoundPolicy::STAGED)for(unsigned bit=0;bit<8;++bit)extra.push_back({id++,"inspection_progress",0,bit,8,0});
  if(p==RoundPolicy::H1){
   for(unsigned j=0;j<2;++j){for(unsigned bit=0;bit<words[j+21].width;++bit)extra.push_back({id++,"committed_source",j,bit,words[j+21].width,0});for(unsigned bit=0;bit<codecs[j+21].r+1;++bit)extra.push_back({id++,"committed_source_check",j,bit,codecs[j+21].r+1,0});}
   for(unsigned w=0;w<21;++w){for(unsigned bit=0;bit<words[w].width;++bit)extra.push_back({id++,"rebuild_accumulator",w,bit,words[w].width,0});extra.push_back({id++,"rebuild_accumulator_parity",w,0,1,0});}
   for(auto name:{"rebuild_phase","rebuild_scan","rebuild_publish","rebuild_retries"})for(unsigned bit=0;bit<8;++bit)extra.push_back({id++,name,0,bit,8,0});
  }
  if(policy==RoundPolicy::STAGED){set_stage(0,127,false);for(unsigned bit=0;bit<16;++bit)extra.push_back({id++,"staged_control",0,bit,16,0});for(unsigned bit=0;bit<stage_codec.r+1;++bit)extra.push_back({id++,"staged_control_check",0,bit,stage_codec.r+1,0});}
  if(external_shadow){Word g;g.limb[0]=shadow_generation;generation_check=generation_codec.encode(g);for(unsigned bit=0;bit<32;++bit)extra.push_back({id++,"shadow_generation",0,bit,32,0});for(unsigned bit=0;bit<generation_codec.r+1;++bit)extra.push_back({id++,"shadow_generation_check",0,bit,generation_codec.r+1,0});}

 }
 struct Snapshot {Word stage_state;uint16_t stage_check;uint32_t shadow_generation;uint16_t generation_check;std::vector<uint16_t> checks;std::vector<Word>a,b;uint8_t refill,progress,phase,scan,publish,retries;uint32_t epoch;bool active;ProtectionStats stats;std::array<Word,2> shadow;std::array<uint16_t,2> shadow_check;std::array<Word,21> acc;std::array<bool,21> acc_parity;std::array<uint64_t,18> activity;};
 Snapshot snapshot()const{if(writing)throw std::logic_error("snapshot in atomic transition");return {stage_state,stage_check,shadow_generation,generation_check,checks,a,b,refill,progress,phase,scan,publish,retries,epoch,recovery_active,stats,shadow,shadow_check,acc,acc_parity,{history_writes,inspections,fold_delta_xor_inputs,raw_delta_xor_inputs,path_delta_xor_inputs,source_decodes,source_encode_bits,shadow_decodes,shadow_corrections,shadow_encode_bits,rebuild_requests,rebuild_steps,rebuild_source_bits,rebuild_xor_inputs,rebuild_writes,rebuild_restarts,skipped_calls,full_reduction_bits}};}
 void restore(const Snapshot& s){if(s.checks.size()!=23||s.a.size()!=23||s.b.size()!=23)throw std::invalid_argument("role snapshot");stage_state=s.stage_state;stage_check=s.stage_check;shadow_generation=s.shadow_generation;generation_check=s.generation_check;checks=s.checks;a=s.a;b=s.b;refill=s.refill;progress=s.progress;phase=s.phase;scan=s.scan;publish=s.publish;retries=s.retries;epoch=s.epoch;recovery_active=s.active;stats=s.stats;shadow=s.shadow;shadow_check=s.shadow_check;acc=s.acc;acc_parity=s.acc_parity;history_writes=s.activity[0];inspections=s.activity[1];fold_delta_xor_inputs=s.activity[2];raw_delta_xor_inputs=s.activity[3];path_delta_xor_inputs=s.activity[4];source_decodes=s.activity[5];source_encode_bits=s.activity[6];shadow_decodes=s.activity[7];shadow_corrections=s.activity[8];shadow_encode_bits=s.activity[9];rebuild_requests=s.activity[10];rebuild_steps=s.activity[11];rebuild_source_bits=s.activity[12];rebuild_xor_inputs=s.activity[13];rebuild_writes=s.activity[14];rebuild_restarts=s.activity[15];skipped_calls=s.activity[16];full_reduction_bits=s.activity[17];writing=false;apply_admission();}
 bool fallback()const{if(policy==RoundPolicy::STAGED)return (stage_active()&&!ready_mask())||(cpu_protocol&&recovery_active);return refill||(cpu_protocol&&recovery_active)||phase;}

 unsigned stage_count()const{return unsigned(stage_state.limb[0]&255);}
 unsigned ready_mask()const{return unsigned((stage_state.limb[0]>>8)&127);}
 bool stage_active()const{return stage_state.bit(15);}
 unsigned eligible_mask()const{auto n=stage_count();return n>=130?127:n>=44?31:n>=16?7:0;}
 bool stage_drain_due()const{return policy==RoundPolicy::STAGED&&stage_active()&&ready_mask()!=eligible_mask();}
 void set_stage(unsigned count,unsigned mask,bool active){stage_state={};stage_state.limb[0]=count|(mask<<8)|(unsigned(active)<<15);stage_check=stage_codec.encode(stage_state);}
 bool validate_stage(){auto d=stage_codec.decode(stage_state,stage_check);if(d.due){++stats.detected;++stats.due;reset_refill();return false;}if(d.corrected){stage_state=d.payload;stage_check=d.check;++stats.detected;++stats.corrected;}
  if(stage_count()>130||(stage_active()&&ready_mask()>eligible_mask())){++stats.detected;reset_refill();return false;}return true;}
 void stage_commit(){if(!validate_stage()||!stage_active())return;auto n=std::min(130u,stage_count()+1);set_stage(n,ready_mask(),true);refill=130-n;++stats.refill_updates;apply_admission();}
 void apply_admission(){if(policy==RoundPolicy::STAGED)core.admitted(stage_active()?ready_mask():127);else core.tagged_enabled(!fallback());}
 void force_refill(){reset_refill();apply_admission();}
 uint32_t shadow_gen(){Word g;g.limb[0]=shadow_generation;auto d=generation_codec.decode(g,generation_check);if(d.due){++stats.detected;++stats.due;shadow_generation=0;generation_check=0;reset_refill();return shadow_generation;}if(d.corrected){shadow_generation=d.payload.limb[0];generation_check=d.check;++stats.corrected;}return shadow_generation;}
 bool inspection_due()const{return policy==RoundPolicy::LEGACY||policy==RoundPolicy::REV||progress>=interval;}
 const std::vector<TageAccess::HistoryWord>& specs()const{return words;}
 const std::vector<StoredSite>& additional_sites()const{return extra;}
 size_t exposed_bits()const{return sites.size()+extra.size();}
 void synchronize(){for(unsigned w=0;w<23;++w)encode_word(w);if(policy==RoundPolicy::H1&&!phase){for(unsigned j=0;j<2;++j){shadow[j]=core.read_history_word(j+21);shadow_check[j]=codecs[j+21].encode(shadow[j]);}}}
 void load_clean_shadow(){for(unsigned j=0;j<2;++j){shadow[j]=core.read_history_word(j+21);shadow_check[j]=codecs[j+21].encode(shadow[j]);}}
 bool check(bool boundary=false){
  if(policy==RoundPolicy::STAGED&&!validate_stage())return true;
  if(policy==RoundPolicy::LEGACY&&scheme==Scheme::P0)return false;
  bool due=(policy==RoundPolicy::LEGACY||policy==RoundPolicy::REV||(boundary&&inspection_due()));
  if(!due&&policy!=RoundPolicy::H1){++skipped_calls;apply_admission();return false;}
  if(due){progress=0;++inspections;++stats.checks;}bool bad=false,source_corrected=false,fold_bad=false;
  for(unsigned w=0;w<23;++w){if(!due&&w<21)continue;auto data=core.read_history_word(w);stats.word_reads+=mode[w]==Scheme::TMR?3:1;
   if(mode[w]==Scheme::ED||mode[w]==Scheme::ECC)++stats.sidecar_reads;
   if(mode[w]==Scheme::ED){if(data.parity()!=bool(checks[w])){++stats.detected;if(policy==RoundPolicy::H1&&w<21)fold_bad=true;else bad=true;}}
   else if(mode[w]==Scheme::ECC){if(w>=21)++source_decodes;auto r=codecs[w].decode(data,checks[w]);if(r.due){++stats.detected;++stats.due;bad=true;}else if(r.corrected){++stats.detected;++stats.corrected;++stats.repair_words;core.write_history_word(w,r.payload);checks[w]=r.check;++stats.word_writes;++stats.sidecar_writes;source_corrected|=w>=21;}}
   else if(mode[w]==Scheme::TMR){auto v=majority(data,a[w],b[w]);++stats.voted_words;if(data!=a[w]||data!=b[w]){++stats.detected;++stats.corrected;++stats.repair_words;stats.replica_repairs+=(data!=v)+(a[w]!=v)+(b[w]!=v);core.write_history_word(w,v);a[w]=b[w]=v;stats.word_writes+=3;}}
  }
  if(bad){reset_refill();stats.word_writes+=23;stats.sidecar_writes+=23;stats.encode_words+=23;}
  else if(policy==RoundPolicy::H1&&(fold_bad||source_corrected)&&!fallback()){if(reset_recovery){auto saved=shadow;auto saved_check=shadow_check;reset_refill();shadow=saved;shadow_check=saved_check;core.tagged_enabled(false);return true;}start_rebuild();if(!cpu_protocol){complete_cpu_drain();while(phase)advance_rebuild_step();}}
  apply_admission();return bad||fold_bad||source_corrected;
 }
 void begin(RoundTransition type,uint64_t pc,bool taken,Base::BranchInfo* bi){
  if(writing)throw std::logic_error("nested transition");writing=true;delta.fill(false);
  if(policy!=RoundPolicy::N1&&policy!=RoundPolicy::H1&&policy!=RoundPolicy::STAGED)return;
  if(full_delta){for(unsigned w=0;w<23;++w)if(mode[w]==Scheme::ED){full_before[w]=core.read_history_word(w).parity();full_reduction_bits+=words[w].width;}return;}
  bool undo=type==RoundTransition::Undo||(type==RoundTransition::Correct&&bi&&bi->modified);
  bool forward=type!=RoundTransition::Undo;
  for(unsigned w=0;w<21;++w){unsigned L=core.fold_length(w);bool v=false;
   if(undo)v^=core.raw_bit(0)^core.raw_bit(L);
   if(forward)v^=taken^core.raw_bit(undo?L:L-1);
   delta[w]=v;fold_delta_xor_inputs+=2*(unsigned(undo)+unsigned(forward));
  }
  bool raw=false;if(undo)raw^=core.raw_bit(0)^core.raw_bit(130);if(forward)raw^=taken^core.raw_bit(undo?130:129);delta[21]=raw;raw_delta_xor_inputs+=2*(unsigned(undo)+unsigned(forward));
  auto path=core.read_history_word(22).limb[0];uint64_t next=path;
  if(undo){if(!bi)throw std::invalid_argument("undo needs branch metadata");next=bi->pathHist;}
  if(forward)next=((next<<1)|(pc&1))&65535;
  if(undo){delta[22]=__builtin_parityll(path^next);path_delta_xor_inputs+=32;}else{delta[22]=((path>>15)&1)^(pc&1);path_delta_xor_inputs+=2;}
 }
 void finish(bool committed){
  if(!writing)throw std::logic_error("finish without transition");writing=false;
  if(full_delta&&(policy==RoundPolicy::N1||policy==RoundPolicy::H1||policy==RoundPolicy::STAGED))for(unsigned w=0;w<23;++w)if(mode[w]==Scheme::ED){delta[w]=full_before[w]^core.read_history_word(w).parity();full_reduction_bits+=words[w].width;}
  for(unsigned w=0;w<23;++w){if((policy==RoundPolicy::N1||policy==RoundPolicy::H1||policy==RoundPolicy::STAGED)&&mode[w]==Scheme::ED)checks[w]^=delta[w];else encode_word(w);if(w>=21&&mode[w]==Scheme::ECC)source_encode_bits+=words[w].width;}
  stats.word_writes+=23*(scheme==Scheme::TMR?3:1);if(scheme==Scheme::ED||scheme==Scheme::ECC||policy!=RoundPolicy::LEGACY){stats.sidecar_writes+=23;stats.encode_words+=((policy==RoundPolicy::N1||policy==RoundPolicy::STAGED)?0:policy==RoundPolicy::H1?2:23);}
  ++history_writes;if(interval&&progress<interval)++progress;
  if(committed&&refill&&policy!=RoundPolicy::STAGED){--refill;++stats.refill_updates;apply_admission();}
 }
 void commit_source(uint64_t pc,bool taken){if(policy==RoundPolicy::STAGED){stage_commit();return;}if(policy!=RoundPolicy::H1||external_shadow)return;commit_shadow_complete(pc,taken);}
 void commit_shadow_complete(uint64_t pc,bool taken){validate_shadow();
  Word h;h.set(0,taken);for(unsigned i=1;i<130;++i)h.set(i,shadow[0].bit(i-1));shadow[0]=h;shadow[1].limb[0]=((shadow[1].limb[0]<<1)|(pc&1))&65535;
  for(unsigned j=0;j<2;++j){shadow_check[j]=codecs[j+21].encode(shadow[j]);shadow_encode_bits+=words[j+21].width;}
 }
 void complete_cpu_drain(){if(policy==RoundPolicy::STAGED){if(!validate_stage())return;set_stage(stage_count(),eligible_mask(),eligible_mask()!=127);recovery_active=false;apply_admission();return;}if(refill)throw std::logic_error("premature drain");if(policy==RoundPolicy::H1&&phase){if(!validate_shadow())return;clear_scan();}else{recovery_active=false;apply_admission();}}
 bool advance_rebuild_step(){
  if(!phase)return false;++rebuild_steps;
  if(phase>4||scan>130||publish>21||retries>3){++stats.detected;stats.word_writes+=23;stats.sidecar_writes+=23;reset_refill();return true;}
  if(phase==1)return true; // Wait for the actual CPU history queue to drain.
  auto restart=[&]{++rebuild_restarts;if(++retries>2)reset_refill();else clear_scan();};
  if(phase==2){unsigned end=std::min(130u,unsigned(scan)+16);
   for(unsigned i=scan;i<end;++i){bool bit=shadow[0].bit(i);++rebuild_source_bits;for(unsigned w=0;w<21;++w)if(i<core.fold_length(w)){if(bit)acc[w].flip(i%words[w].width);acc_parity[w]^=bit;++rebuild_xor_inputs;}}
   scan=end;if(scan==130)phase=3;return true;
  }
  if(phase==3){auto corrections=shadow_corrections;if(!validate_shadow())return true;if(shadow_corrections!=corrections){restart();return true;}
   for(unsigned w=0;w<21;++w)if(acc[w].parity()!=acc_parity[w]){++stats.detected;restart();return true;}phase=4;publish=0;return true;
  }
  if(publish<21){core.write_history_word(publish,acc[publish]);checks[publish]=acc_parity[publish];++publish;++rebuild_writes;return true;}
  auto corrections=shadow_corrections;if(!validate_shadow())return true;if(shadow_corrections!=corrections){restart();return true;}
  for(unsigned j=0;j<2;++j){core.write_history_word(j+21,shadow[j]);checks[j+21]=shadow_check[j];}
  phase=0;recovery_active=false;progress=0;apply_admission();return false;
 }
 void prediction(){if(fallback())++stats.fallback_predictions;}
 uint16_t stored_check(unsigned w)const{return checks.at(w);}
 bool logical_bit(size_t id)const{
  if(id>=exposed_bits())throw std::out_of_range("role logical bit");if(id<sites.size()){auto& s=sites[id];return (core.payload(s)>>s.bit)&1;}
  auto& s=extra[id-sites.size()];auto& n=s.structure;
  if(n=="parity"||n=="secded_check")return (checks[s.word]>>s.bit)&1;
  if(n=="replica")return (s.replica==1?a[s.word]:b[s.word]).bit(s.bit);
  if(n=="committed_source")return shadow[s.word].bit(s.bit);
  if(n=="committed_source_check")return (shadow_check[s.word]>>s.bit)&1;
  if(n=="rebuild_accumulator")return acc[s.word].bit(s.bit);
  if(n=="rebuild_accumulator_parity")return acc_parity[s.word];
  if(n=="staged_control")return stage_state.bit(s.bit);
  if(n=="staged_control_check")return (stage_check>>s.bit)&1;
  if(n=="shadow_generation")return (shadow_generation>>s.bit)&1;
  if(n=="shadow_generation_check")return (generation_check>>s.bit)&1;
  if(n=="recovery_active")return recovery_active;
  uint32_t v=n=="refill_remaining"?refill:n=="history_epoch"?epoch:n=="inspection_progress"?progress:n=="rebuild_phase"?phase:n=="rebuild_scan"?scan:n=="rebuild_publish"?publish:retries;return (v>>s.bit)&1;
 }
 void corrupt(const std::vector<size_t>& ids){std::set<size_t> unique;for(auto id:ids)if(id>=exposed_bits()||!unique.insert(id).second)throw std::invalid_argument("invalid/duplicate role event");
  for(auto id:ids){if(id<sites.size()){auto&s=sites[id];core.write_payload(s,core.payload(s)^(1u<<s.bit));continue;}auto&s=extra[id-sites.size()];auto&n=s.structure;
   if(n=="parity"||n=="secded_check")checks[s.word]^=uint16_t(1)<<s.bit;
   else if(n=="replica")(s.replica==1?a[s.word]:b[s.word]).flip(s.bit);
   else if(n=="committed_source")shadow[s.word].flip(s.bit);
   else if(n=="committed_source_check")shadow_check[s.word]^=uint16_t(1)<<s.bit;
   else if(n=="rebuild_accumulator")acc[s.word].flip(s.bit);
   else if(n=="rebuild_accumulator_parity")acc_parity[s.word]=!acc_parity[s.word];
   else if(n=="staged_control")stage_state.flip(s.bit);
   else if(n=="staged_control_check")stage_check^=uint16_t(1)<<s.bit;
   else if(n=="shadow_generation")shadow_generation^=uint32_t(1)<<s.bit;
   else if(n=="shadow_generation_check")generation_check^=uint16_t(1)<<s.bit;
   else if(n=="refill_remaining")refill^=uint8_t(1)<<s.bit;
   else if(n=="history_epoch")epoch^=uint32_t(1)<<s.bit;
   else if(n=="recovery_active")recovery_active=!recovery_active;
   else if(n=="inspection_progress")progress^=uint8_t(1)<<s.bit;
   else if(n=="rebuild_phase")phase^=uint8_t(1)<<s.bit;
   else if(n=="rebuild_scan")scan^=uint8_t(1)<<s.bit;
   else if(n=="rebuild_publish")publish^=uint8_t(1)<<s.bit;
   else retries^=uint8_t(1)<<s.bit;
  }
 }
};
}
