#include "source_protection.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
using namespace bp::v18b3;
int main(){try{unsigned jobs=0;for(unsigned policy=0;policy<6;++policy){bp::RoundState ref;auto words=ref.history_words();std::vector<Geometry>g;for(unsigned i=0;i<21;++i)g.push_back({ref.fold_length(i),words[i].width});auto mode=policy==5?Mode::Direct:Mode::Recurrent;Service s(mode,g);s.attach_guard(std::make_unique<FiniteProtection>(s.selected_widths(),policy==5?Protect::P0:Protect(policy),mode==Mode::Direct));unsigned accepts=0;
for(unsigned n=0;n<600;++n){if(s.can_retire(1))s.retire(1);if(n<300){if(s.accept(Kind::Append,1,n&1,n&1))++accepts;if(s.accept(Kind::Read))++accepts;}s.tick();s.take();s.take();if(!s.conserved())throw IntegrityError("mixed conservation");}
for(unsigned n=0;n<2000&&!s.drained();++n){s.tick();s.take();s.take();}if(!s.drained()||!s.conserved()||accepts<50)throw IntegrityError("mixed did not drain");jobs+=accepts;}
std::cout<<"{\"status\":\"PASS_MIXED_READ_RMW_EDGE_TRANSACTION\",\"transactions\":"<<jobs<<",\"CPU_trials\":0}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
