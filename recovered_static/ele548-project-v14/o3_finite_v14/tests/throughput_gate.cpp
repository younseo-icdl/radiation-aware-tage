#include "source_access.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <deque>
#include <iostream>
using namespace bp::v14;
struct Model : SourceAccess<bp::RoundState> {
    Model(const gem5::TAGEBaseParams& p, Mode mode, unsigned L) : SourceAccess(p) { configure(mode,L,L); }
};
static void need(bool v, const char* message) { if (!v) throw std::runtime_error(message); }
int main() { try {
    std::cout << "{\"status\":\"PASS_CURRENT_MEASURED_SOURCE_INDEPENDENT_II1_NOT_CPU_NEXT_PC\",\"CPU_trials\":0,\"cases\":[";
    bool first=true;
    for (auto mode : {Mode::Recurrent,Mode::Direct,Mode::Overwrite})
      for (unsigned L : {1u,2u}) for (bool single : {false,true}) {
        gem5::TAGEBaseParams p; p.speculativeHistUpdate=true; p.instShiftAmt=0;
        Model model(p,mode,L); bp::RoundState reference(p);
        std::deque<std::pair<Token,uint64_t>> live;
        unsigned issued=0,completed=0,maximum=0;
        auto issue=[&] {
            if (issued==128 || single&&!live.empty()) return;
            // Independent control input only: these PCs are known to this
            // component producer. This is not an actual next-PC branch stream.
            uint64_t pc=0x4000+issued*4;
            auto token=model.engine->request(pc,true);
            if (token) { live.push_back({*token,pc}); ++issued; maximum=std::max(maximum,unsigned(live.size())); }
        };
        issue();
        while (completed<128 && model.engine->port.source.cycle()<1000) {
            model.advance();
            if (!live.empty() && model.engine->peek(live.front().first)) {
                auto* actual=model.consume(live.front().first);
                auto* expected=reference.makeBranchInfo(live.front().second,true);
                bool prediction=reference.tagePredict(0,live.front().second,true,expected);
                bp::v9::Payload a,b; a.capture_response(*actual);a.put(25,actual->tagePred);
                b.capture_response(*expected);b.put(25,prediction);
                need(a.data==b.data,"current source/provider normal response mismatch");
                delete actual;delete expected;live.pop_front();++completed;
            }
            issue();
        }
        auto cycles=model.engine->port.source.cycle();
        need(completed==128 && model.engine->conserved(),"current source throughput conservation");
        need(cycles==(single?128*(L+1):128+L),"current real source/provider stage timing");
        need(maximum==(single?1:L+1),"finite multiple request storage did not fill");
        if (!first) std::cout<<',';first=false;
        std::cout<<"{\"mode\":"<<unsigned(mode)<<",\"source_L\":"<<L<<",\"provider_extra_L\":1,\"II\":1,\"single_pending\":"<<(single?"true":"false")<<",\"component_cycles\":"<<cycles<<",\"max_outstanding\":"<<maximum<<",\"completed\":"<<completed<<'}';
      }
    std::cout<<"]}\n";
} catch(const std::exception& e) { std::cerr<<"FAIL "<<e.what()<<'\n';return 1; } }
