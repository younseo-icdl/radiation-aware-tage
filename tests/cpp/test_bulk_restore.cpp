#include "tage/history/bulk_restore.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <array>
#include <iostream>
#include <random>

// Expose only the original pinned kernel to use as an independent reference.
struct Reference : bp::TageState {using Fold = FoldedHistory;};
void check(bool value,const char *why) {if(!value) throw std::runtime_error(why);}
int main() {
    try {
        std::mt19937_64 rng(548);
        constexpr std::array<unsigned,7> lengths{5,9,15,25,44,76,130};
        constexpr std::array<unsigned,7> tags{9,9,10,10,11,11,12};
        unsigned comparisons=0, dirty_preserved=0;
        for(unsigned trial=0;trial<3000;++trial) {
            std::array<uint8_t,1024> ring{};
            for(auto &bit:ring) bit=rng()&1;
            const unsigned head=rng()%ring.size();
            const unsigned n=trial<513?trial:rng()%513;
            auto read=[&](unsigned age) {return ring[(head+age)%ring.size()];};
            // A raw window of 642 bits includes the largest old/new endpoint.
            std::array<uint8_t,642> linear{};
            for(unsigned i=0;i<linear.size();++i) linear[i]=read(i);
            for(unsigned bank=0;bank<7;++bank)
                for(unsigned width:{9u,tags[bank],tags[bank]-1}) {
                    Reference::Fold reference;reference.init(lengths[bank],width);
                    reference.comp=rng()&((1u<<width)-1); // Arbitrarily dirty F.
                    const auto stored=reference.comp;
                    for(unsigned k=0;k<n;++k) reference.restore(linear.data()+k);
                    const auto bulk=bp::bulk_restore_fold(stored,lengths[bank],width,n,read);
                    check(bulk==reference.comp,"bulk != pinned sequential inverse");
                    unsigned canonical=0;
                    for(unsigned age=0;age<lengths[bank];++age)
                        canonical^=unsigned(read(n+age))<<(age%width);
                    dirty_preserved+=bulk!=canonical;
                    if(!n) check(bulk==stored,"zero undo must not repair inconsistent F");
                    ++comparisons;
                }
        }
        check(dirty_preserved>60000,"test must exercise persistent inconsistent folds");
        for(unsigned invalid=0;invalid<4;++invalid) {
            bool rejected=false;
            try {bp::bulk_restore_fold(invalid==3?1024:0,invalid==0?131:130,
                                      invalid==1?32:9,invalid==2?513:0,
                                      [](unsigned){throw std::runtime_error("unexpected read");return false;});}
            catch(const std::invalid_argument &) {rejected=true;}
            check(rejected,"invalid geometry must fail before source access");
        }
        std::cout<<"PASS "<<comparisons<<" pinned bulk-undo comparisons, n=0..512, circular wrap, arbitrary live raw/F; no canonical repair\n";
        return 0;
    } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
