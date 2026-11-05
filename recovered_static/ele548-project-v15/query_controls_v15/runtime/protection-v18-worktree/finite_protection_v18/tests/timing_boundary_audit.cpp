#include "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/protection-v18-worktree/finite_protection_v18/producer_source/B2/src/source_protection.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
using namespace bp::v18;
static void need(bool x,const char*s){if(!x)throw IntegrityError(s);}
static auto geometry(){bp::RoundState r;auto w=r.history_words();std::vector<Geometry>g;for(unsigned i=0;i<21;++i)g.push_back({r.fold_length(i),w[i].width});return g;}
static Service make(Protect p){Service s(Mode::Recurrent,geometry());s.attach_guard(std::make_unique<FiniteProtection>(s.selected_widths(),p));return s;}
static FiniteProtection& guard(Service&s){return *dynamic_cast<FiniteProtection*>(s.guard());}
static size_t frame(Service&s){for(auto&r:s.manifest())if(r.name=="protect_stage_payload")return r.start;throw IntegrityError("frame absent");}
static void drain(Service&s){for(unsigned n=0;n<100;++n){if(s.drained())return;s.tick();s.take();s.take();}throw IntegrityError("audit drain");}
static Reply read(Service&s){auto t=s.accept(Kind::Read);need(bool(t),"audit read admission");for(unsigned n=0;n<100;++n){s.tick();if(auto r=s.take(*t))return *r;}throw IntegrityError("audit read timeout");}
int main(){try{
 unsigned sampling=0,encoder=0;
 for(auto policy:{Protect::P0,Protect::Ecc})for(unsigned when=0;when<3;++when){auto s=make(policy);if(when==0)s.corrupt({s.selected_site(21,49)});need(bool(s.accept(Kind::Append,1,1,1)),"sampling append");s.tick();need(guard(s).unit.phase()==1,"actual decoder operand not registered");if(when==1)s.corrupt({s.selected_site(21,49)});if(when==2)s.corrupt({frame(s)+200+49});drain(s);bool actual=s.source_bit(50);bool expected=policy==Protect::P0&&when!=1;need(actual==expected,"sampling boundary changed");need(s.conserved(),"sampling conservation");++sampling;}
 // Physical S* is healthy, but a single uncoded ENCODER operand upset can
 // generate incorrect check bits or fan out to BOTH TMR replicas. A later
 // decoder action labelled 'corrected' is not proof of golden correctness.
 for(auto policy:{Protect::P0,Protect::Parity,Protect::Ecc,Protect::Tmr}){auto s=make(policy);need(bool(s.accept(Kind::Append,1,1,1)),"encoder append");s.tick();s.tick();s.tick();need(guard(s).unit.phase()==3,"not actual encoder input phase");need(s.selected_words()[0].limb[0]==1,"healthy source before encoder upset");s.corrupt({frame(s)+1});drain(s);auto r=read(s);drain(s);
 if(policy==Protect::P0)need(r.folds[0]==1,"P0 no-op encode mutated source");
 else if(policy==Protect::Parity)need(guard(s).fallback()&&guard(s).unit.stats.resets==1,"encoder parity upset not detected");
 else need(r.folds[0]==3&&s.selected_words()[0].limb[0]==3&&guard(s).unit.stats.corrected==1,"encoder common operand boundary not observed");need(s.conserved(),"encoder conservation");++encoder;}
 std::cout<<"{\"status\":\"OBSERVED_SAMPLING_AND_UNCODED_ENCODER_BOUNDARIES_NOT_FULL_BIT_CORRECTION\",\"sampling_phase_cases\":"<<sampling<<",\"encoder_phase_cases\":"<<encoder<<",\"late_primary_RMW_upset_overwritten_without_detection\":true,\"ECC_encoder_latch_SEU_can_miscorrect_healthy_source\":true,\"TMR_encoder_latch_SEU_can_fan_out_to_two_replicas\":true,\"new_gem5_CPU\":0,\"real_workload_results\":0}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
