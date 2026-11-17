// Generate private vectors from the pinned C++ TAGE hash implementation.
#include "tage/history/direct_access.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>

std::string hex(const std::vector<bool> &bits) {
    std::string result;
    for(unsigned nibble=0;nibble<(bits.size()+3)/4;++nibble) {
        unsigned value=0;
        for(unsigned b=0;b<4;++b) if(nibble*4+b<bits.size() && bits[nibble*4+b]) value|=1u<<b;
        result.push_back("0123456789abcdef"[value]);
    }
    std::reverse(result.begin(),result.end()); return result;
}
void append(std::vector<bool> &bits,uint64_t value,unsigned width) {
    for(unsigned b=0;b<width;++b) bits.push_back((value>>b)&1);
}
int main(int argc,char **argv) {
    try {
        if(argc!=3) throw std::invalid_argument("usage: tage-rtl-vectors FRESH_OUTPUT COUNT");
        if(std::filesystem::exists(argv[1])) throw std::invalid_argument("output exists");
        unsigned count=std::stoul(argv[2]);
        if(!count || count>1000000) throw std::invalid_argument("count must be 1..1000000");
        bp::TageState stored;
        bp::DirectAccess<bp::TageState> direct;
        direct.direct_queries=true;
        auto words=stored.history_words();
        std::mt19937_64 rng(548);
        std::ofstream out(argv[1]);
        for(unsigned trial=0;trial<count;++trial) {
            uint32_t pc=rng(); uint16_t path=rng(); bp::Word raw;
            raw.limb[0]=rng();raw.limb[1]=rng();raw.limb[2]=rng()&3;
            bp::Word p; p.limb[0]=path;
            stored.write_history_word(21,raw);direct.write_history_word(21,raw);
            stored.write_history_word(22,p);direct.write_history_word(22,p);
            std::vector<bool> folds,rawbits;
            for(unsigned w=0;w<21;++w) {
                bp::Word v;v.limb[0]=rng();stored.write_history_word(w,v);
                append(folds,stored.read_history_word(w).limb[0],words[w].width);
            }
            for(unsigned b=0;b<130;++b) rawbits.push_back(raw.bit(b));
            auto *a=stored.makeBranchInfo(pc,true), *b=direct.makeBranchInfo(pc,true);
            stored.tagePredict(0,pc,true,a);direct.tagePredict(0,pc,true,b);
            out<<std::hex<<pc<<' '<<path<<' '<<hex(rawbits)<<' '<<hex(folds);
            for(unsigned mask:{0u,127u,64u}) {
                std::vector<bool> indices,tags;
                for(unsigned bank=1;bank<=7;++bank) {
                    auto *bi=(mask>>(bank-1))&1 ? b : a;
                    append(indices,bi->tableIndices[bank],9);
                    append(tags,bi->tableTags[bank],words[(bank-1)*3+1].width);
                }
                out<<' '<<hex(indices)<<' '<<hex(tags);
            }
            out<<'\n';delete a;delete b;
        }
        std::cout<<"PASS_CXX_HASH_VECTORS "<<std::dec<<count<<" (not RTL simulation or CPU timing)\n";
        return 0;
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
