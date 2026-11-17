#include "tage/history/lease.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <iostream>
using namespace bp;
void check(bool x,const char *why) {if(!x) throw std::runtime_error(why);}
int main() {
    try {
        TageState core; auto before=core.save();
        Word raw;raw.flip(0);raw.flip(64);core.write_history_word(21,raw);
        Word bad;bad.flip(3);core.write_history_word(0,bad);
        auto dirty=core.save();
        QuiescentLease lease(8,3);
        lease.append(8);
        unsigned callbacks=0;
        auto publish=[&] {++callbacks;publish_own_folds(core);};
        check(!lease.service(0,false,publish),"must wait for actual restore owners");
        check(!lease.service(1,true,publish),"service latency is not free");
        check(!lease.service(3,true,publish),"not ready early");
        check(core.save().folded==dirty.folded,"no early fold mutation");
        check(lease.service(4,true,publish),"charged publication");
        auto after=core.save();
        check(callbacks==1 && lease.publications==1,"exactly one publish");
        check(after.global==dirty.global && after.pred==dirty.pred && after.hyst==dirty.hyst
              && after.alt==dirty.alt && after.aging==dirty.aging,"source and learning untouched");
        check(core.read_history_word(0).bit(0),"canonical fold includes actual faulty own raw");
        check(after.global!=before.global,"no golden source repair");
        auto stable=core.bits();
        check(lease.service(5,false,publish) && core.bits()==stable,"no gratuitous service");
        lease.xor_age(3);check(lease.due(),"age is exposed metadata, no detector oracle");
        check(!lease.service(6,true,publish),"age upset can trigger early charged service");
        bool rejected=false;
        try {lease.append(1);} catch(const std::logic_error &) {rejected=true;}
        check(rejected,"no append under quiescent worker");
        rejected=false;
        try {lease.service(7,false,publish);} catch(const std::logic_error &) {rejected=true;}
        check(rejected,"no stale owner reentry");
        check(lease.service(9,true,publish),"normal service after integrity probe");
        QuiescentLease disabled(0,0);disabled.append(1000);
        check(disabled.service(0,false,publish) && !disabled.due(),"feature-off contract");
        QuiescentLease overflow(1,3);overflow.append(1);rejected=false;
        try {overflow.service(UINT64_MAX-1,true,publish);} catch(const std::overflow_error &) {rejected=true;}
        check(rejected,"completion counter wrap cannot become free immediate service");
        std::cout<<"PASS lease drain/service publication, own faulty source, no learning/gold repair, age upset, forbidden stale-owner/append\n";
        return 0;
    } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
