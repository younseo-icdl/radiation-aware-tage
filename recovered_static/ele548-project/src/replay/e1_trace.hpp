#pragma once
#include "predictor/tage_adapter.hpp"
#include <cstring>
#include <fstream>

namespace bp {
struct IndexedControl { Branch branch; uint64_t instruction; };
struct E1Trace {
    std::vector<IndexedControl> controls;
    std::vector<size_t> conditionals;
};
inline uint64_t little(const char* data, unsigned width) {
    uint64_t value=0;
    for(unsigned i=0;i<width;++i) value|=uint64_t(static_cast<unsigned char>(data[i]))<<(8*i);
    return value;
}
inline E1Trace read_e1_trace(const std::string& path) {
    std::ifstream f(path,std::ios::binary);
    if(!f) throw std::runtime_error("missing E1 input");
    char header[8];
    if(!f.read(header,8)||std::memcmp(header,"E1CBP001",8)) throw std::runtime_error("bad E1 magic");
    E1Trace trace;char raw[18];uint64_t previous=0;
    while(f.read(raw,18)) {
        uint64_t instruction=little(raw+8,8);
        auto taken=little(raw+16,1),conditional=little(raw+17,1);
        if(instruction<=previous||taken>1||conditional>1) throw std::runtime_error("invalid indexed control");
        previous=instruction;
        if(conditional) trace.conditionals.push_back(trace.controls.size());
        trace.controls.push_back({{little(raw,4),little(raw+4,4),bool(taken),bool(conditional)},instruction});
    }
    if(f.gcount()!=0||!f.eof()||trace.conditionals.empty()) throw std::runtime_error("truncated/empty E1 trace");
    return trace;
}
struct E1Window {size_t begin,end;uint64_t instructions;};
inline E1Window e1_window(const E1Trace& trace,unsigned start,unsigned horizon) {
    if(!horizon||size_t(start)+horizon>trace.conditionals.size()) throw std::invalid_argument("short post-event window");
    size_t begin=trace.conditionals[start],end=trace.conditionals[start+horizon-1]+1;
    return {begin,end,trace.controls[end-1].instruction-trace.controls[begin].instruction+1};
}
inline const char* subfield_name(const Site& s) {
    if(s.kind==4) return s.bank?"path":"raw_direction";
    if(s.kind==5) return s.row==0?"index_fold":(s.row==1?"tag_fold_0":"tag_fold_1");
    return field_name(s.kind);
}
inline std::vector<uint8_t> compact_bits(const TageState& state,const std::vector<Site>& sites) {
    std::vector<uint8_t> bits;bits.reserve(sites.size());
    for(const auto& s:sites) bits.push_back((state.payload(s)>>s.bit)&1u);
    return bits;
}
} // namespace bp
