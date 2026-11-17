// Cheap committed-query locality screen; no CPU or hardware timing is inferred.
#include <array>
#include <charconv>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <list>
#include <map>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>
#include <zlib.h>

using Key = std::array<uint64_t, 3>;
struct Hash {
    size_t operator()(const Key &k) const {
        uint64_t h=14695981039346656037ULL;
        for (auto x:k) h=(h^x)*1099511628211ULL;
        return h;
    }
};
struct Cache {
    unsigned capacity;
    std::list<Key> lru;
    std::unordered_map<Key,std::list<Key>::iterator,Hash> entries;
    uint64_t hits=0, accesses=0;
    explicit Cache(unsigned n):capacity(n) {}
    void read(const Key &key) {
        ++accesses;
        auto i=entries.find(key);
        if (i!=entries.end()) {++hits;lru.splice(lru.begin(),lru,i->second);return;}
        if (entries.size()==capacity) {entries.erase(lru.back());lru.pop_back();}
        lru.push_front(key);entries.emplace(key,lru.begin());
    }
};
uint64_t number(std::string_view s) {
    uint64_t value=0;
    auto out=std::from_chars(s.data(),s.data()+s.size(),value);
    if(out.ec!=std::errc() || out.ptr!=s.data()+s.size()) throw std::invalid_argument("numeric trace field");
    return value;
}
std::vector<std::string_view> split(const std::string &line) {
    std::vector<std::string_view> fields;
    size_t first=0;
    for(size_t i=0;i<=line.size();++i) if(i==line.size() || line[i]==',') {
        fields.emplace_back(line.data()+first,i-first);first=i+1;
    }
    return fields;
}
Key window(Key raw,unsigned bits) {
    for(unsigned limb=0;limb<3;++limb) {
        if(bits>=64) bits-=64;
        else {raw[limb]&=bits ? (uint64_t(1)<<bits)-1 : 0;bits=0;}
    }
    return raw;
}
int main(int argc,char **argv) {
    try {
        if(argc!=3) throw std::invalid_argument("usage: tage-trace-screen COMMITTED.csv.gz FRESH_OUTPUT_DIR");
        std::filesystem::path output=argv[2];
        if(std::filesystem::exists(output)) throw std::invalid_argument("output exists");
        gzFile input=gzopen(argv[1],"rb");
        if(!input) throw std::runtime_error("cannot open trace");
        char buffer[65536];
        auto line=[&](std::string &s) {
            if(!gzgets(input,buffer,sizeof(buffer))) return false;
            s=buffer;
            if(!s.empty() && s.back()=='\n') s.pop_back();
            else if(!gzeof(input)) throw std::runtime_error("oversized trace row");
            if(!s.empty() && s.back()=='\r') s.pop_back();
            return true;
        };
        std::string text;
        if(!line(text)) throw std::runtime_error("empty trace");
        std::map<std::string,unsigned> columns;
        auto header=split(text);
        for(unsigned i=0;i<header.size();++i) columns.emplace(std::string(header[i]),i);
        for(auto name:{"branch_id","conditional","pc","raw_limb0","raw_limb1","raw_limb2","provider_type","hit_bank","alternate_bank"})
            if(!columns.count(name)) throw std::runtime_error("missing trace column");
        const std::array<unsigned,7> lengths{5,9,15,25,44,76,130};
        std::vector<Cache> caches;
        for(unsigned b=0;b<7;++b) {caches.emplace_back(16);caches.emplace_back(64);}
        std::array<uint64_t,8> selected{};
        std::map<uint64_t,uint64_t> pcs;
        uint64_t branches=0,conditional=0;
        while(line(text)) {
            auto f=split(text);
            if(f.size()!=header.size()) throw std::runtime_error("malformed trace row");
            ++branches;
            if(number(f[columns.at("branch_id")])!=branches)
                throw std::runtime_error("nonconsecutive committed branch identity");
            if(number(f[columns.at("conditional")])==0) continue;
            ++conditional;
            ++pcs[number(f[columns.at("pc")])];
            Key raw{number(f[columns.at("raw_limb0")]),number(f[columns.at("raw_limb1")]),number(f[columns.at("raw_limb2")])};
            for(unsigned b=0;b<7;++b) {
                Key key=window(raw,lengths[b]);caches[2*b].read(key);caches[2*b+1].read(key);
            }
            unsigned p=number(f[columns.at("provider_type")]);
            unsigned bank=p==1 ? number(f[columns.at("hit_bank")]) :
                          p==3 ? number(f[columns.at("alternate_bank")]) : 0;
            if(bank>7) throw std::runtime_error("provider bank outside geometry");
            ++selected[bank];
        }
        int error=0;gzerror(input,&error);
        if(error!=Z_OK && error!=Z_STREAM_END) throw std::runtime_error("gzip read error");
        if(gzclose(input)!=Z_OK) throw std::runtime_error("gzip close error");
        std::filesystem::create_directories(output);
        std::ofstream cache(output/"FOLD_CACHE_LOCALITY.csv");
        cache<<"bank,history_length,entries,accesses,hits,misses,hit_fraction,key_payload_valid_bits_excluding_replacement\n";
        const unsigned tag_widths[]={9,9,10,10,11,11,12};
        for(unsigned b=0;b<7;++b) for(unsigned c=0;c<2;++c) {
            auto &x=caches[2*b+c];
            cache<<b+1<<','<<lengths[b]<<','<<x.capacity<<','<<x.accesses<<','<<x.hits<<','<<x.accesses-x.hits<<','
                 <<(x.accesses ? double(x.hits)/x.accesses : 0)<<','
                 <<x.capacity*(lengths[b]+9+2*tag_widths[b]-1+1)<<'\n';
        }
        std::ofstream providers(output/"PROVIDER_COUNTS.csv");
        providers<<"selected_bank,committed_conditional_queries\n";
        for(unsigned b=0;b<8;++b) providers<<b<<','<<selected[b]<<'\n';
        std::ofstream pc(output/"PC_COUNTS.csv");pc<<"pc,committed_conditional_queries\n";
        for(auto [address,count]:pcs) pc<<address<<','<<count<<'\n';
        std::ofstream summary(output/"SUMMARY.json");
        summary<<"{\"committed_branches\":"<<branches<<",\"conditional_queries\":"<<conditional
            <<",\"unique_conditional_pcs\":"<<pcs.size()<<",\"cache_contract\":\"exact raw-window content, independent per-bank fully associative LRU, 16/64 entries, fold payload only; no PC key\","
              "\"sampling\":\"all recorded committed-query source snapshots; wrong-path lookups not exported\","
              "\"physical_cost\":\"UNKNOWN; source read, tag compare, replacement, valid/integrity, ports and clock not free\","
              "\"CPU_speedup\":\"NOT_MEASURED\",\"generation_cache_and_ahead_operand_timing\":\"NOT_OBSERVED\"}\n";
        std::cout<<"PASS_COMMITTED_TRACE_SCREEN_NOT_CPU_OR_PPA conditional="<<conditional<<'\n';
        return 0;
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
