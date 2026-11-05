#include "replay/e1_trace.hpp"
#include <iostream>
using namespace bp;
void check(bool good,const char* message){if(!good)throw std::runtime_error(message);}
int main(){try{
    // Gapped original record indices include non-control instructions in MPKI.
    E1Trace trace{{{{0x100,0x200,true,true},10},{{0x200,0x300,true,false},12},
                  {{0x300,0x400,false,true},20},{{0x400,0x500,true,true},35}}, {0,2,3}};
    auto first=e1_window(trace,0,2),late=e1_window(trace,1,2);
    check(first.begin==0&&first.end==3&&first.instructions==11,"instruction denominator first window");
    check(late.begin==2&&late.end==4&&late.instructions==16,"equal followup late window");
    bool rejected=false;try{e1_window(trace,2,2);}catch(const std::invalid_argument&){rejected=true;}
    check(rejected,"incomplete followup accepted");
    TageAdapter normal,observed;unsigned callbacks=0;std::mt19937_64 input(5401);
    for(unsigned i=0;i<10000;++i){Branch b{0x4000+(input()%128)*4,0x5000,bool(input()&1),bool(i%11)};
        auto a=normal.step(b),z=observed.step_observed(b,[&](const Base::BranchInfo&){++callbacks;});
        check(a==z,"observer changed prediction");}
    check(callbacks==10000&&normal.core.equal(observed.core)&&normal.predictor_rng==observed.predictor_rng,
          "observer changed state/RNG");
    auto sites=normal.core.sites();auto bits=compact_bits(normal.core,sites);auto original=normal.core.bits();
    check(bits.size()==65370&&std::equal(bits.begin(),bits.end(),original.begin()),"compact gold state mismatch");
    std::cout<<"PASS exact inclusive instruction denominator, equal post-event horizon, incomplete-window rejection, read-only observer full-state/RNG equivalence\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
