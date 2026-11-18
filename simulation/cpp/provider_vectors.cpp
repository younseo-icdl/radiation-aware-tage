// Build provider boundary vectors using the pinned native C++ predictor.
#include "tage/predictor/tage_adapter.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>

namespace {
struct Tags {
    uint64_t low=0;
    unsigned high=0;
    void add(unsigned tag, unsigned offset) {
        low |= uint64_t(tag)<<offset; // All fields start below bit 64.
        if(offset>52) high |= tag>>(64-offset);
    }
};

std::ostream &operator<<(std::ostream &out, const Tags &tags) {
    return out<<std::setw(2)<<std::setfill('0')<<tags.high<<std::setw(16)<<tags.low;
}

class ProviderReference : public bp::TageState {
  public:
    void emit(std::ostream &out, std::mt19937_64 &rng, unsigned trial) {
        const unsigned pc=rng();
        auto *info=makeBranchInfo(pc,true);
        tagePredict(0,pc,true,info);
        const unsigned enabled=trial%2 ? 127 : rng()&127;
        const bool bimodal=rng()&1, prefer_longest=rng()&1;
        btablePrediction[info->bimodalIndex]=bimodal;
        useAltPredForNewlyAllocated[0]=prefer_longest ? -1 : 0;
        Tags query,rows;
        unsigned offset=0,counters=0;
        for(unsigned b=1;b<=7;++b) {
            noSkip[b]=enabled>>(b-1)&1;
            const auto tag=unsigned(info->tableTags[b]);
            const auto row=tag^unsigned(rng()&1);
            const auto counter=unsigned(rng()&7);
            gtable[b][info->tableIndices[b]].tag=row;
            gtable[b][info->tableIndices[b]].ctr=int(counter)-(counter>=4?8:0);
            query.add(tag,offset);rows.add(row,offset);
            offset+=tagTableTagWidths[b];
            counters|=counter<<(3*(b-1));
        }
        bool pred=tagePredict(0,pc,true,info);
        out<<query<<' '<<rows<<' '<<counters<<' '<<enabled<<' '<<bimodal<<' '<<prefer_longest<<' '
           <<pred<<' '<<info->hitBank<<' '<<info->altBank<<' '<<info->provider<<'\n';
        delete info;
    }
};
}

int main(int argc,char **argv) {
    try {
        if(argc!=2 || std::filesystem::exists(argv[1]))
            throw std::invalid_argument("usage: tage-provider-vectors FRESH_OUTPUT");
        std::ofstream out(argv[1]);
        if(!out) throw std::runtime_error("cannot create provider vectors");
        ProviderReference reference;
        std::mt19937_64 rng(548);
        out<<std::hex;
        for(unsigned trial=0;trial<20000;++trial) reference.emit(out,rng,trial);
        out.close();
        if(!out) throw std::runtime_error("provider vector write failed");
        return 0;
    } catch(const std::exception &error) {std::cerr<<error.what()<<'\n';return 1;}
}
