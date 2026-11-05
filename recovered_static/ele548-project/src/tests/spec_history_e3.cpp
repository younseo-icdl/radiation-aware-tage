#include "predictor/tage_adapter.hpp"
#include "protection/spec_history.hpp"
#include <iostream>
using namespace bp;
static void require(bool v,const char* why){if(!v)throw std::runtime_error(why);}
int main(){try{
    gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;params.histBufferSize=4096;
    // Unit-test variant exercises original periodic aging frequently; CPU
    // experiments retain the locked release's logUResetPeriod=18.
    params.logUResetPeriod=6;params.initialTCounterValue=32;
    std::mt19937_64 input(548991);
    for(auto scheme:{Scheme::P0,Scheme::ED,Scheme::ECC,Scheme::TMR}){
        TageState ref(params),state(params);HistoryController ctl(state,scheme,true);SpecHistoryProtocol cpu(state,ctl);
        std::mt19937_64 a(548),z(548);
        for(unsigned group=0;group<10000;++group){
            std::array<Base::BranchInfo*,3> rb{},sb{};std::array<EpochRecord,3> epochs{};std::array<Branch,3> branches{};
            for(unsigned i=0;i<3;++i){auto& b=branches[i];b={0x1000+(input()%128)*2+(input()%2),0x2000,bool(input()&1),i!=2||group%5!=0};
                rb[i]=ref.makeBranchInfo(b.pc,b.conditional);sb[i]=state.makeBranchInfo(b.pc,b.conditional);epochs[i]=cpu.capture();
                bool rp=ref.tagePredict(0,b.pc,b.conditional,rb[i]);bool sp=state.tagePredict(0,b.pc,b.conditional,sb[i]);require(rp==sp,"speculative clean prediction");
                ref.updateHistories(0,b.pc,true,rp,b.target,{},rb[i]);cpu.speculative(0,b.pc,sp,b.target,{},sb[i],epochs[i]);}
            ref.restoreHistState(0,rb[2]);cpu.discard(0,sb[2],epochs[2]);delete rb[2];delete sb[2];
            ref.squash(0,branches[1].taken,branches[1].target,{},rb[1]);cpu.corrected(0,branches[1].taken,branches[1].target,{},sb[1],epochs[1]);
            for(unsigned i=0;i<2;++i){auto b=branches[i];bool actual=i?b.taken:rb[i]->tagePred;
                int arand=int(a()%std::numeric_limits<int>::max())&3,zrand=int(z()%std::numeric_limits<int>::max())&3;
                if(b.conditional){ref.updateStats(actual,rb[i]);ref.condBranchUpdate(0,b.pc,actual,rb[i],arand,b.target,rb[i]->tagePred);}
                ref.updateHistories(0,b.pc,false,actual,b.target,{},rb[i]);cpu.commit(0,b.pc,actual,b.target,{},sb[i],epochs[i],zrand);delete rb[i];delete sb[i];}
            require(ref.equal(state)&&a==z,"speculative clean full-state/RNG/rollback equality");
        }
        require(!ctl.stats.detected,"spurious speculative detector");
    }
    for(auto scheme:{Scheme::ED,Scheme::ECC}){
        TageState state(params);HistoryController ctl(state,scheme,true);SpecHistoryProtocol cpu(state,ctl);
        Branch b{0x1234,0x2000,true,true};auto e=cpu.capture();auto* old=state.makeBranchInfo(b.pc,true);state.tagePredict(0,b.pc,true,old);cpu.speculative(0,b.pc,true,b.target,{},old,e);
        auto w=state.history_words();ctl.corrupt(scheme==Scheme::ED?std::vector<size_t>{w[0].sites[0]}:std::vector<size_t>{w[0].sites[0],w[0].sites[1]});ctl.check();
        require(ctl.refill==130&&ctl.recovery_active&&ctl.epoch==1,"CPU history reset");
        auto before=state.bits();cpu.discard(0,old,e);require(state.bits()==before&&cpu.stale_restores_suppressed==1,"stale generation restored corrupt checkpoint");
        cpu.corrected(0,false,b.target,{},old,e);require(state.bits()==before,"old corrected branch inserted speculative history");
        cpu.commit(0,b.pc,true,b.target,{},old,e,0);delete old;require(ctl.refill==129,"old branch did not refill on real commit");
        for(unsigned i=0;i<129;++i){auto q=cpu.capture();auto* bi=state.makeBranchInfo(b.pc,true);state.tagePredict(0,b.pc,true,bi);before=state.bits();
            cpu.speculative(0,b.pc,true,b.target,{},bi,q);require(state.bits()==before,"refill inserted speculative directions");
            cpu.commit(0,b.pc,bool(i&1),b.target,{},bi,q,0);delete bi;}
        require(ctl.refill==0&&ctl.fallback()&&ctl.recovery_active,"tagged mode resumed before CPU drain");
        require(cpu.frontend_blocked(false),"did not hold frontend for drain");require(!cpu.frontend_blocked(true)&&!ctl.fallback(),"drain did not reenable tagged providers");
        auto extra=ctl.additional_sites();require(extra.back().structure=="recovery_active","CPU recovery flag omitted from manifest");ctl.corrupt({extra.back().id});require(ctl.logical_bit(extra.back().id),"CPU recovery flag not exposed");
        require(!cpu.frontend_blocked(true)&&!ctl.recovery_active,"spurious flag drain contract");
    }
    std::cout<<"PASS four schemes: 30k speculative predictions each, 10k young-discard/older-correct rollbacks and 20k commit state/RNG comparisons; 4096-byte rollover; ED/ECC stale generation suppression; actual 130-commit refill; queue-empty drain; added recovery flag injection\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
