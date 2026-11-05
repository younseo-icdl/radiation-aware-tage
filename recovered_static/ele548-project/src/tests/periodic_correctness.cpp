#include "predictor/periodic_adapter.hpp"
#include "predictor/protected_adapter.hpp"
#include "protection/periodic_spec_history.hpp"
#include <iostream>
using namespace bp;
static void require(bool v,const char* why){if(!v)throw std::runtime_error(why);}
int main(){try{
    std::mt19937_64 inputs(548202610);
    for(auto s:{Scheme::P0,Scheme::ED,Scheme::ECC,Scheme::TMR}){
        ProtectedAdapter legacy(s);PeriodicAdapter extension(s);
        for(unsigned i=0;i<2500;++i){Branch b{0x1000+(inputs()%128)*2,0x2000,bool(inputs()&1),i%7!=0};
            require(legacy.step(b)==extension.step(b),"disabled policy prediction drift");}
        require(legacy.predictor.core.equal(extension.predictor.core),"disabled policy state drift");
        require(legacy.predictor.predictor_rng==extension.predictor.predictor_rng,"disabled policy RNG drift");
        require(legacy.protection.stats.checks==extension.protection.stats.checks&&
                legacy.protection.stats.word_writes==extension.protection.stats.word_writes,"disabled policy activity drift");
    }
    for(unsigned k:{1u,8u,32u,64u}){
        PeriodicAdapter policy(Scheme::ED,k);TageAdapter clean;
        for(unsigned i=0;i<12000;++i){Branch b{0x1000+(inputs()%128)*2,0x2000,bool(inputs()&1),i%7!=0};
            require(policy.step(b)==clean.step(b),"periodic clean prediction");}
        require(clean.core.equal(policy.predictor.core)&&clean.predictor_rng==policy.predictor.predictor_rng,"periodic clean state/RNG");
        require(!policy.protection.stats.detected,"periodic false alarm");
        require(policy.protection.inspections==(12000-1)/k,"periodic cadence");
    }
    unsigned singles=0;Branch b{0x1234,0x2000,true,true};
    PeriodicAdapter p(Scheme::ED,8);
    for(unsigned i=0;i<64;++i)p.step(b);
    auto warm=p.snapshot();std::vector<size_t> ids;
    for(const auto& w:p.protection.specs())ids.insert(ids.end(),w.sites.begin(),w.sites.end());
    for(const auto& s:p.protection.additional_sites())if(s.structure=="parity")ids.push_back(s.id);
    for(auto id:ids){p.restore(warm);p.protection.check(true);p.protection.corrupt({id});
        auto d=p.protection.stats.detected;
        for(unsigned n=0;n<8;++n){p.step(b);require(p.protection.stats.detected==d,"inspection earlier than k writes");}
        p.step(b);require(p.protection.stats.detected>d&&p.protection.epoch==warm.protection.base.epoch+1,"odd residual lost during writes");++singles;
    }
    // Even parity errors and repeated XOR cancellation are not magically detected.
    p.restore(warm);p.protection.check(true);auto w=p.protection.specs()[0];auto d=p.protection.stats.detected;
    p.protection.corrupt({w.sites[0],w.sites[1]});for(unsigned i=0;i<9;++i)p.step(b);
    require(p.protection.stats.detected==d,"oracle even-error detection");
    p.restore(warm);p.protection.check(true);p.protection.corrupt({w.sites[0]});p.protection.corrupt({w.sites[0]});
    for(unsigned i=0;i<9;++i)p.step(b);require(p.protection.stats.detected==warm.protection.base.stats.detected,"same-tick XOR cancellation");
    // Whole-event rejection is atomic, including the policy counter.
    auto bits=p.predictor.core.bits();auto old_progress=p.protection.progress;
    try{p.protection.corrupt({w.sites[0],p.protection.exposed_bits()});require(false,"invalid event accepted");}catch(const std::invalid_argument&){}
    require(bits==p.predictor.core.bits()&&p.protection.progress==old_progress,"partial invalid event");
    // Real progress cells can change the cadence; saturation avoids wraparound.
    for(unsigned bit=0;bit<8;++bit){p.restore(warm);p.protection.check(true);
        auto id=p.protection.exposed_bits()-8+bit;p.protection.corrupt({id});require(p.protection.logical_bit(id),"progress bit not exposed");
        for(unsigned i=0;i<10;++i)p.step(b);require(p.protection.inspections>warm.protection.inspections,"progress fault disabled inspection");}
    p.restore(warm);auto restored_bits=p.predictor.core.bits();auto snap=p.snapshot();p.step(b);p.protection.corrupt({w.sites[0]});p.restore(snap);
    require(p.protection.progress==snap.protection.progress,"snapshot progress not restored");
    require(p.predictor.core.bits()==restored_bits,"snapshot state");
    gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;params.histBufferSize=4096;
    params.logUResetPeriod=6;params.initialTCounterValue=32;
    for(unsigned k:{1u,8u,32u}){
        TageState clean(params),state(params);PeriodicHistoryController ctl(state,Scheme::ED,true,k);
        PeriodicSpecHistoryProtocol protocol(state,ctl);std::mt19937_64 a(548),z(548);
        for(unsigned group=0;group<2500;++group){
            std::array<Base::BranchInfo*,3> rb{},sb{};std::array<EpochRecord,3> records{};std::array<Branch,3> branches{};
            for(unsigned j=0;j<3;++j){auto& q=branches[j];q={0x1000+(inputs()%128)*2,0x2000,bool(inputs()&1),j!=2||group%5!=0};
                rb[j]=clean.makeBranchInfo(q.pc,q.conditional);sb[j]=state.makeBranchInfo(q.pc,q.conditional);records[j]=protocol.capture();
                auto cp=clean.tagePredict(0,q.pc,q.conditional,rb[j]),fp=state.tagePredict(0,q.pc,q.conditional,sb[j]);require(cp==fp,"speculative prediction");
                clean.updateHistories(0,q.pc,true,cp,q.target,{},rb[j]);protocol.speculative(0,q.pc,fp,q.target,{},sb[j],records[j]);}
            clean.restoreHistState(0,rb[2]);protocol.discard(0,sb[2],records[2]);delete rb[2];delete sb[2];
            clean.squash(0,branches[1].taken,branches[1].target,{},rb[1]);protocol.corrected(0,branches[1].taken,branches[1].target,{},sb[1],records[1]);
            for(unsigned j=0;j<2;++j){auto q=branches[j];auto actual=j?q.taken:rb[j]->tagePred;
                int ar=int(a()%std::numeric_limits<int>::max())&3,zr=int(z()%std::numeric_limits<int>::max())&3;
                if(q.conditional){clean.updateStats(actual,rb[j]);clean.condBranchUpdate(0,q.pc,actual,rb[j],ar,q.target,rb[j]->tagePred);}
                clean.updateHistories(0,q.pc,false,actual,q.target,{},rb[j]);protocol.commit(0,q.pc,actual,q.target,{},sb[j],records[j],zr);delete rb[j];delete sb[j];}
            require(clean.equal(state)&&a==z,"speculative state/RNG/rollback/rollover drift");
        }
        require(!ctl.stats.detected,"speculative false detection");
        auto record=protocol.capture();auto* old=state.makeBranchInfo(b.pc,true);state.tagePredict(0,b.pc,true,old);
        protocol.speculative(0,b.pc,true,b.target,{},old,record);ctl.corrupt({ctl.specs()[0].sites[0]});ctl.progress=k;
        protocol.capture();require(ctl.epoch==1&&ctl.refill==130,"periodic reset/refill");
        auto before=state.bits();protocol.discard(0,old,record);require(before==state.bits(),"stale checkpoint restored");
        protocol.corrected(0,false,b.target,{},old,record);require(before==state.bits(),"stale correction restored");
        protocol.commit(0,b.pc,true,b.target,{},old,record,0);delete old;require(ctl.refill==129,"actual refill missing");
    }
    std::cout<<"PASS disabled four-baseline equivalence; periodic1/8/32/64 clean; "<<singles
             <<" odd payload/sidecar cases retained across RMW; even/cancel/atomic/counter/snapshot; speculative rollback/4096 rollover/aging/stale-generation/refill\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
