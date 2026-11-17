// Protocol vectors from the pinned speculative TAGE state and hash operations.
#include "tage/history/direct_access.hpp"
#include "tage/history/lease.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>

std::string packed(const std::vector<bool> &bits) {
    std::string s;
    for(unsigned n=0;n<(bits.size()+3)/4;++n) {
        unsigned v=0;for(unsigned b=0;b<4;++b) if(n*4+b<bits.size() && bits[n*4+b]) v|=1u<<b;
        s.push_back("0123456789abcdef"[v]);
    }
    std::reverse(s.begin(),s.end());return s;
}
void add(std::vector<bool> &bits,uint64_t value,unsigned width) {
    for(unsigned b=0;b<width;++b) bits.push_back((value>>b)&1);
}
int main(int argc,char **argv) {
    try {
        if(argc!=3 || std::filesystem::exists(argv[1]))
            throw std::invalid_argument("usage: tage-state-vectors FRESH_OUTPUT COUNT");
        unsigned count=std::stoul(argv[2]);
        if(count<1000 || count>1000000) throw std::invalid_argument("count must be 1000..1000000");
        gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;params.histBufferSize=4096;
        bp::DirectAccess<bp::TageState> core(params);
        auto geometry=core.history_words();
        struct Owner {unsigned id; bp::Base::BranchInfo *bi;};
        std::vector<Owner> live;
        std::set<unsigned> free;
        for(unsigned i=0;i<512;++i) free.insert(i);
        std::mt19937_64 rng(548);unsigned head=0;
        unsigned total_append=0,total_undo=0,publications=0,max_live=0,raw_faults=0,fold_faults=0;
        std::ofstream out(argv[1]);if(!out) throw std::runtime_error("cannot create vectors");
        for(unsigned trial=0;trial<count;++trial) {
            unsigned kind=trial%17==7?1:(trial%19==9?2:0),address=0;
            if(kind==1) {
                address=rng()%130;auto raw=core.read_history_word(21);raw.flip(address);
                core.write_history_word(21,raw);++raw_faults;
            } else if(kind==2) {
                address=rng()%200;unsigned bit=address,w=0;
                while(bit>=geometry[w].width) bit-=geometry[w++].width;
                auto value=core.read_history_word(w);value.flip(bit);core.write_history_word(w,value);++fold_faults;
            }
            // First fill every owner, then undo all 512 in one operation.
            unsigned undo=trial==171?512:0;
            if(trial>700 && !live.empty() && trial%7==0) undo=1+rng()%live.size();
            unsigned restore=undo?live[live.size()-undo].id:0;
            for(unsigned k=0;k<undo;++k) {
                auto owner=live.back();live.pop_back();core.restoreHistState(0,owner.bi);
                delete owner.bi;free.insert(owner.id);
            }
            head=(head+undo)&1023;total_undo+=undo;
            // Committed owners relinquish slots without restoring raw/path.
            if(trial>=172 && trial<=700) {
                for(auto owner:live) {delete owner.bi;free.insert(owner.id);}
                live.clear();
            } else if(trial>700 && live.size()>400) {
                for(unsigned k=0;k<100;++k) {delete live[k].bi;free.insert(live[k].id);}
                live.erase(live.begin(),live.begin()+100);
            }
            unsigned app=trial<171?std::min(3u,512u-unsigned(live.size())):
                         (trial>=172 && trial<700?3:rng()%4);
            app=std::min(app,unsigned(free.size()));
            bool publish=live.empty() && !undo && (trial==700 || (trial>700 && trial%11==0));
            if(publish) app=0;
            unsigned bits=rng()&7,pathbits=rng()&7,owners=0;
            std::array<unsigned,3> ids{};
            for(unsigned a=0;a<app;++a) {ids[a]=*free.begin();free.erase(free.begin());owners|=ids[a]<<(a*9);}
            unsigned prefix[2]={unsigned(rng()%(app+1)),unsigned(rng()%(app+1))};
            uint32_t pcs[2]={uint32_t(rng()),uint32_t(rng())};
            std::array<std::vector<bool>,4> hashes;
            // Save expected endpoints independently at each query's prefix.
            std::array<std::vector<bool>,2> si,st,di,dt;
            for(unsigned a=0;a<=app;++a) {
                for(unsigned q=0;q<2;++q) if(prefix[q]==a) {
                    auto *bi=core.makeBranchInfo(pcs[q],true);
                    for(unsigned direct=0;direct<2;++direct) {
                        core.direct_queries=direct;core.tagePredict(0,pcs[q],true,bi);
                        for(unsigned b=1;b<=7;++b) {
                            add(direct?di[q]:si[q],bi->tableIndices[b],9);
                            add(direct?dt[q]:st[q],bi->tableTags[b],geometry[(b-1)*3+1].width);
                        }
                    }
                    core.direct_queries=false;delete bi;
                }
                if(a<app) {
                    unsigned pc=(rng()&~1u)|((pathbits>>a)&1);
                    auto *bi=core.makeBranchInfo(pc,true);
                    core.tagePredict(0,pc,true,bi);
                    core.updateHistories(0,pc,true,(bits>>a)&1,pc+4,{},bi);
                    live.push_back({ids[a],bi});head=(head-1)&1023;++total_append;
                }
            }
            if(publish) {bp::publish_own_folds(core,geometry);++publications;}
            for(unsigned q=0;q<2;++q) {
                hashes[0].insert(hashes[0].end(),si[q].begin(),si[q].end());
                hashes[1].insert(hashes[1].end(),st[q].begin(),st[q].end());
                hashes[2].insert(hashes[2].end(),di[q].begin(),di[q].end());
                hashes[3].insert(hashes[3].end(),dt[q].begin(),dt[q].end());
            }
            std::vector<bool> raw,folds;
            auto value=core.read_history_word(21);for(unsigned b=0;b<130;++b) raw.push_back(value.bit(b));
            for(unsigned w=0;w<21;++w) add(folds,core.read_history_word(w).limb[0],geometry[w].width);
            out<<std::hex<<kind<<' '<<address<<' '<<undo<<' '<<restore<<' '<<app<<' '<<bits<<' '<<pathbits<<' '<<owners<<' '<<publish<<' '
               <<((uint64_t(pcs[1])<<32)|pcs[0])<<' '<<(prefix[0]|(prefix[1]<<2));
            for(auto &hash:hashes) out<<' '<<packed(hash);
            out<<' '<<packed(raw)<<' '<<packed(folds)<<' '<<core.read_history_word(22).limb[0]<<' '<<head<<'\n';
            max_live=std::max(max_live,unsigned(live.size()));
        }
        for(auto owner:live) delete owner.bi;
        out.close();if(!out) throw std::runtime_error("vector write failed");
        if(max_live!=512 || !publications || !raw_faults || !fold_faults || total_undo<512)
            throw std::runtime_error("insufficient protocol coverage");
        std::cout<<"PASS_CXX_STATE_VECTORS count="<<count<<" appends="<<total_append<<" undos="<<total_undo
                 <<" max_live="<<max_live<<" publications="<<publications<<" raw_faults="<<raw_faults<<" fold_faults="<<fold_faults<<'\n';
        return 0;
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
