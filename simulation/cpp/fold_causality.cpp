// Deterministic production-kernel experiment, not CPU performance or radiation MC.
#include "tage/predictor/tage_adapter.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>

struct Production : bp::TageState {using Fold = FoldedHistory;};
struct Arm {
    std::array<uint8_t,131> h{};
    Production::Fold f;
    int first_ref=-1,first_inv=-1,last_ref=-1,last_inv=-1;
    void update(bool incoming) {
        std::move_backward(h.begin(),h.end()-1,h.end());h[0]=incoming;
        f.update(h.data()); // Pinned production function, post-append h[L].
    }
    unsigned phi() const {
        unsigned value=0;
        for(int age=0;age<f.origLength;++age) value^=unsigned(h[age])<<(age%f.compLength);
        return value;
    }
};
void require(bool test,const char *why) {if(!test) throw std::runtime_error(why);}
bool input(unsigned pattern,unsigned step) {
    if(pattern==0) return false;
    if(pattern==1) return true;
    if(pattern==2) return step&1;
    // Stateless deterministic input independent of fault-arm access order.
    uint64_t v=step+0x9e3779b97f4a7c15ULL;
    v=(v^(v>>30))*0xbf58476d1ce4e5b9ULL;
    v=(v^(v>>27))*0x94d049bb133111ebULL;
    return (v^(v>>31))&1;
}
int main(int argc,char **argv) {
    try {
        if(argc!=2 || std::filesystem::exists(argv[1]))
            throw std::invalid_argument("usage: tage-fold-causality FRESH_OUTPUT_DIRECTORY");
        std::filesystem::create_directories(argv[1]);
        std::ofstream summary(std::filesystem::path(argv[1])/"SUMMARY.csv");
        std::ofstream trace(std::filesystem::path(argv[1])/"HAND_TRACE.csv");
        require(bool(summary)&&bool(trace),"cannot create output");
        summary<<"pattern,bank,kind,L,width,age,arm,expected_first_tap,first_d_ref,first_d_inv,last_d_ref,last_d_inv,horizon_updates\n";
        trace<<"pattern,bank,kind,L,width,age,arm,update,incoming,next_outgoing,stored,phi,reference,d_ref,d_inv,active_window_raw_diff,active_raw130_diff\n";
        const unsigned lengths[]{5,9,15,25,44,76,130}, tags[]{9,9,10,10,11,11,12};
        const char *names[]{"CLEAN","RAW_ONLY","COHERENT_INCOMING","FOLD_ONLY","RAW_REPAIRED_BEFORE_TAP","RAW_REPAIRED_AFTER_TAP","REBASE_OWN_AT0"};
        uint64_t cases=0,checks=0;
        for(unsigned pattern=0;pattern<4;++pattern)
          for(unsigned bank=0;bank<7;++bank)
           for(unsigned kind=0;kind<3;++kind)
            for(unsigned age=0;age<130;++age) {
                const unsigned L=lengths[bank],width=kind==0?9:tags[bank]-(kind-1);
                const int tap=age<L?int(L-age):-1;
                std::array<Arm,7> arm;
                for(auto &a:arm) a.f.init(L,width);
                for(unsigned step=0;step<300;++step) {
                    arm[0].update(input(pattern,step));
                    arm[2].update(input(pattern,step)^(step==299-age));
                }
                for(unsigned a:{1u,3u,4u,5u,6u}) arm[a]=arm[0];
                for(unsigned a:{1u,4u,5u,6u}) arm[a].h[age]^=1;
                arm[3].f.comp^=1;
                arm[6].f.comp=arm[6].phi();
                for(unsigned step=0;step<=260;++step) {
                    if(tap>0 && step==unsigned(tap-1)) arm[4].h=arm[0].h;
                    if(tap>0 && step==unsigned(tap)) arm[5].h=arm[0].h;
                    for(unsigned a=0;a<arm.size();++a) {
                        auto &v=arm[a];
                        unsigned ref=v.f.comp^arm[0].f.comp,inv=v.f.comp^v.phi();
                        if(ref) {if(v.first_ref<0)v.first_ref=step;v.last_ref=step;}
                        if(inv) {if(v.first_inv<0)v.first_inv=step;v.last_inv=step;}
                        require((arm[0].f.comp^arm[0].phi())==0,"clean recurrence != independent oracle");
                        require(arm[2].f.comp==arm[2].phi(),"coherent incoming lost consistency");
                        require(arm[6].f.comp==arm[2].f.comp && arm[6].h==arm[2].h,
                                "own-H rebase != coherent wrong-input state");
                        if(a==1) {
                            require(bool(ref)==(tap>0 && step>=unsigned(tap)),"raw first fold difference violates tap theorem");
                            if(ref) require(__builtin_popcount(ref)==1,"raw residual is rotation, not bit amplification");
                        }
                        if(a==2) require(bool(ref)==(tap>0 && step<unsigned(tap)),"coherent input did not expire at outgoing tap");
                        if(a==3) require(__builtin_popcount(ref)==1,"fold-only residual not conserved under common inputs");
                        if(a==4) require(ref==0,"repair before tap failed to prevent residual");
                        if(a==5) require(bool(ref)==(tap>0 && step>=unsigned(tap)),"raw repair after tap silently healed fold");
                        if(pattern==0 && bank==2 && kind==1 && (age==3 || age==15) && step<=32) {
                            unsigned raw_diff=0,window_diff=0;
                            for(unsigned i=0;i<130;++i) {
                                raw_diff+=v.h[i]!=arm[0].h[i];
                                if(i<L) window_diff+=v.h[i]!=arm[0].h[i];
                            }
                            trace<<pattern<<','<<bank+1<<','<<kind<<','<<L<<','<<width<<','<<age<<','<<names[a]<<','<<step<<','
                                 <<input(pattern,300+step)<<','<<unsigned(v.h[L-1])<<','<<v.f.comp<<','<<v.phi()<<','<<arm[0].f.comp<<','
                                 <<__builtin_popcount(ref)<<','<<__builtin_popcount(inv)<<','<<window_diff<<','<<raw_diff<<'\n';
                        }
                        ++checks;
                    }
                    if(step<260) for(auto &a:arm) a.update(input(pattern,300+step));
                }
                for(unsigned a=0;a<arm.size();++a) {
                    const auto &v=arm[a];
                    summary<<pattern<<','<<bank+1<<','<<kind<<','<<L<<','<<width<<','<<age<<','<<names[a]<<','<<tap<<','
                           <<v.first_ref<<','<<v.first_inv<<','<<v.last_ref<<','<<v.last_inv<<",260\n";
                }
                ++cases;
            }
        summary.close();trace.close();require(bool(summary)&&bool(trace),"output write failed");
        std::cout<<"PASS_PRODUCTION_FOLD_CAUSALITY cases="<<cases<<" arm_observations="<<checks
                 <<" raw_ages=130 patterns=4 horizon=260; no CPU or speculative-recovery claim\n";
        return 0;
    } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
