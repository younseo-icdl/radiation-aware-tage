#include "vector_protection.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
using namespace bp::v18b3;
static void need(bool x,const char*s){if(!x)throw std::runtime_error(s);}
static auto widths(){bp::RoundState s;std::array<unsigned,23>w{};auto h=s.history_words();for(unsigned i=0;i<23;++i)w[i]=h[i].width;return w;}
static size_t start(VectorProtection&u,const std::string&s){for(auto&r:u.manifest())if(r.name==s)return r.start;throw std::runtime_error("missing manifest region");}
static VectorProtection::Words fixture(){VectorProtection::Words a{};auto w=widths();for(unsigned i=0;i<23;++i)for(unsigned j=0;j<w[i];++j)a[i].set(j,(i*17+j*7)%3==0);return a;}
static void prime(VectorProtection&u,const VectorProtection::Words&a){need(u.publish(100,0,a),"encode admission");need(u.phase()==3,"encoder not registered");u.advance();need(u.ready(),"encoder not complete after edge");}
static VectorProtection::Result finish(VectorProtection&u,unsigned token=1,unsigned version=0){for(unsigned n=0;n<12;++n){auto out=u.take(token,version);if(out)return *out;u.advance();}throw std::runtime_error("finite decode did not complete");}
int main(){try{
 const auto w=widths();auto good=fixture();unsigned normal=0,sbu=0,meta=0,latch=0,due=0,stale=0,wrap=0,even=0,three=0,correlated=0;
 for(auto p:{Protect::P0,Protect::Parity,Protect::Periodic,Protect::Ecc,Protect::Tmr}){
  VectorProtection seed(w,p);prime(seed,good);
  need(seed.sample(1,0,true,good),"normal admission");need(!seed.take(1,0),"result visible before real stage");seed.advance();auto a=seed.take(1,0);need(a&&a->words==good&&!a->reset,"normal codec mismatch");++normal;
  for(unsigned word=0;word<23;++word)for(unsigned bit=0;bit<w[word];++bit){
   VectorProtection u(w,p);prime(u,good);auto bad=good;bad[word].flip(bit);need(u.sample(1,0,true,bad),"SBU sample");auto out=finish(u);
   if(p==Protect::Parity)need(out.reset&&u.fallback(),"parity SBU not reset/excluded");
   else if(p==Protect::Ecc||p==Protect::Tmr)need(!out.reset&&out.words==good&&u.stats.corrected==1,"SBU not actual correction");
   else need(out.words==bad&&!out.reset,"P0/periodic immediate inspection changed");++sbu;
  }
  VectorProtection in(w,p);prime(in,good);need(in.sample(1,0,true,good),"latch fixture");
  // Every component bit receives precise XOR independently. Only metadata and
  // pre-decode protected payload have a guarantee; other sites remain exposed.
  for(size_t bit=0;bit<in.bits();++bit){auto u=in;bool before=u.logical_bit(bit);u.corrupt({bit});need(u.logical_bit(bit)!=before,"component XOR not precise");need(in.logical_bit(bit)==before,"component snapshot aliases");
   if(bit<start(u,"protect_stage_payload")-1){auto out=finish(u);need(out.words==good&&!out.reset,"metadata SBU changed returned data");++meta;}
   else if(bit>=start(u,"protect_stage_payload")&&bit<start(u,"protect_stage_payload")+346){auto out=finish(u);if(p==Protect::Ecc||p==Protect::Tmr)need(out.words==good,"coded input latch SBU not corrected");else if(p==Protect::Parity)need(out.reset,"parity input latch SBU missed");++latch;}
  }
  auto stale_unit=in;stale_unit.advance();need(!stale_unit.take(1,1)&&stale_unit.ready()&&stale_unit.stats.stale==1,"stale source version accepted");++stale;
  auto cancelled=in;cancelled.cancel(1);cancelled.advance();need(cancelled.ready()&&!cancelled.take(1,0),"cancelled stage escaped");
 }
 // Check-cell SBU is corrected using only actual data+sidecar.
 {VectorProtection u(w,Protect::Ecc);prime(u,good);need(u.check_bits()==121,"frozen ECC sidecar width");u.corrupt({start(u,"protect_sidecars")});need(u.sample(1,0,true,good),"check SBU");auto out=finish(u);need(out.words==good&&u.stats.corrected==1,"ECC check-cell correction");}
 // Same-word double data error: actual SECDED DUE causes reset/fallback.
 {VectorProtection u(w,Protect::Ecc);prime(u,good);auto bad=good;bad[0].flip(0);bad[0].flip(1);u.sample(1,0,true,bad);auto out=finish(u);need(out.reset&&u.stats.due==1,"SECDED double not DUE");++due;}
 {VectorProtection u(w,Protect::Parity);prime(u,good);auto bad=good;bad[0].flip(0);bad[0].flip(1);u.sample(1,0,true,bad);auto out=finish(u);need(!out.reset&&out.words==bad,"even parity error was oracle-corrected");++even;}
 {VectorProtection u(w,Protect::Ecc);prime(u,good);auto bad=good;bad[0].flip(0);bad[0].flip(1);bad[0].flip(2);u.sample(1,0,true,bad);auto out=finish(u);need(out.reset||out.words!=good,"three-bit fixture unexpectedly correct; choose documented bad tuple");++three;}
 {VectorProtection u(w,Protect::Tmr);prime(u,good);auto bad=good;bad[0].flip(0);u.corrupt({start(u,"protect_replica1")});u.sample(1,0,true,bad);auto out=finish(u);need(out.words!=good&&!out.reset,"correlated TMR was oracle-corrected");++correlated;}
 // Periodic delta keeps the old residual, never launders a source upset.
 {VectorProtection u(w,Protect::Periodic);prime(u,good);auto bad=good;bad[0].flip(0);for(unsigned n=0;n<63;++n){u.sample(1,0,false,bad);auto out=finish(u);need(!out.reset&&out.residual==1,"periodic residual lost before due");need(u.publish(100+n,0,bad,out.residual),"delta publication");u.advance();}u.sample(1,0,true,bad);auto out=finish(u);need(out.reset,"periodic64 never detected retained residual");}
 // Tiny protected epoch must stop at wrap and requires explicit drained ACK.
 {VectorProtection u(w,Protect::Parity,false,2);VectorProtection::Words zero{},bad{};bad[0].set(0,true);for(unsigned n=0;n<4;++n){u.sample(1,0,true,bad);auto out=finish(u);need(out.reset,"tiny epoch reset");if(n<3){need(u.publish(99,0,zero),"reset encode");u.advance();}}need(u.wrap_waiting()&&!u.ready(),"epoch wrapped without barrier");u.acknowledge_epoch_drained();need(u.epoch()==0&&!u.wrap_waiting(),"wrap ACK");wrap=u.stats.wraps;}
 // Logical atomic duplicate reject does not partially modify a cell.
 {VectorProtection u(w,Protect::P0);bool x=u.logical_bit(0);bool rejected=false;try{u.corrupt({0,0});}catch(const std::invalid_argument&){rejected=true;}need(rejected&&u.logical_bit(0)==x,"partial invalid atomic event");}
 std::cout<<"{\"status\":\"PASS_VECTOR_STAGE_COMPONENT_NOT_CPU_OR_FULL_SOURCE_RECOVERY\",\"normal_policies\":"<<normal<<",\"source_payload_SBU\":"<<sbu<<",\"metadata_SBU\":"<<meta<<",\"predecode_latch_SBU\":"<<latch<<",\"DUE\":"<<due<<",\"stale_rejected\":"<<stale<<",\"wrap_barriers\":"<<wrap<<",\"even_parity_undetected_observed\":"<<even<<",\"SECDED3plus_outside_guarantee_observed\":"<<three<<",\"correlated_TMR_failure_observed\":"<<correlated<<",\"CPU_trials\":0}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
