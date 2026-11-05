#include "source_access.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
using namespace bp::v18b4;
static void need(bool x,const char*s){if(!x)throw std::runtime_error(s);}
struct Model:SourceAccess<bp::RoundState>{Model(const gem5::TAGEBaseParams&p):SourceAccess(p){configure(Mode::Recurrent,1,1);enable_protection(Protect::Ecc,Mode::Recurrent);}};
static void drain(Model&m){for(unsigned i=0;i<600&&!m.drained();++i)m.advance();need(m.drained(),"finite drain timeout");}
static bp::Base::BranchInfo* lookup(Model&m){auto t=m.request(0x1000,true);need(bool(t),"test lookup rejected");for(unsigned i=0;i<600;++i){m.advance();if(m.engine->peek(*t))return m.consume(*t);}throw std::runtime_error("finite lookup timeout");}
static void reset(Model&m){auto&s=m.engine->port.source;s.corrupt({s.selected_site(21,76),s.selected_site(21,77)});auto*bi=lookup(m);delete bi;drain(m);need(m.fallback(),"actual ECC DUE/reset not observed");}
int main(){try{
 gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;p.instShiftAmt=0;p.histBufferSize=4096;
 Model a(p);auto*old=lookup(a);const bool actual=old->tagePred;a.updateHistories(0,0x1000,true,actual,0x2000,{},old);drain(a);need(a.retire_with_outcome(old->nGhist,actual,0x1000),"pre-reset retirement");
 reset(a);auto before=a.engine->enqueued;a.updateHistories(0,0x1000,false,actual,0x2000,{},old);delete old;need(a.engine->enqueued==before&&a.fallback_commits==0,"pre-reset committed branch re-entered later refill");
 Model b(p);reset(b);need(b.prepare_recovery(),"recovery reservation");need(!b.can_retire(0)&&!b.retire_with_outcome(0,true,0x1000),"retirement bypassed prepared squash reservation");b.engine->begin();b.engine->end();need(b.retire_with_outcome(0,true,0x1000),"post-reservation actual retirement");need(!b.can_retire(0),"same-cycle second commit admitted");
 auto regions=b.engine->manifest();auto region=std::find_if(regions.begin(),regions.end(),[](const auto&r){return r.name=="ingress_control_mirrored_SECDED";});need(region!=regions.end(),"control manifest missing");unsigned cases=0;
 for(size_t bit=0;bit<region->bits;++bit){auto c=*b.engine;c.corrupt({region->start+bit});need(!c.committed_ready()&&!c.committed_ready(),"SBU opened same-cycle write port");c.advance([](uint64_t,bool,const std::array<unsigned,21>&,unsigned){return bp::v9::Payload{};});need(c.committed_ready()&&c.conserved(),"next-cycle protected ingress did not recover");++cases;}
 std::cout<<"{\"status\":\"PASS_PRE_RESET_DELAYED_TRAINING_RESERVED_SQUASH_AND_USED_PORT_SBU\",\"pre_reset_no_duplicate\":1,\"squash_reservation_backpressure\":1,\"used_port_metadata_SBU_cases\":"<<cases<<",\"CPU_trials\":0}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
