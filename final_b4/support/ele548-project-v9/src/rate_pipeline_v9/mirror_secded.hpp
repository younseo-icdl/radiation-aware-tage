#pragma once
#include "../protection/word.hpp"
#include <stdexcept>

namespace bp::v9 {
struct MirrorUncorrectable:std::runtime_error {
    unsigned due_copies;
    explicit MirrorUncorrectable(const char* why,unsigned due=0)
        :std::runtime_error(why),due_copies(due){}
};
struct MirrorCell {Word data{};uint16_t check=0;};
// Two actual systematic SECDED copies. No saved/expected payload participates
// in decoding. At most two physical flips total are corrected losslessly.
class MirrorSecded {
    WordSecded code_;
 public:
    struct Result {Word data;bool repaired=false;unsigned corrected_copies=0,due_copies=0;};
    explicit MirrorSecded(unsigned width):code_(width){}
    unsigned data_bits()const{return code_.k;}
    unsigned check_bits()const{return code_.r+1;}
    void store(MirrorCell& primary,MirrorCell& mirror,const Word& data)const {
        const auto check=code_.encode(data);primary={data,check};mirror={data,check};
    }
    Result decode(MirrorCell& primary,MirrorCell& mirror)const {
        const auto a=code_.decode(primary.data,primary.check);
        const auto b=code_.decode(mirror.data,mirror.check);
        if(a.due&&b.due)throw MirrorUncorrectable("both SECDED copies DUE",2);
        if(!a.due&&!b.due&&a.payload!=b.payload)
            throw MirrorUncorrectable("valid SECDED copies disagree");
        const Word chosen=a.due?b.payload:a.payload;
        const auto check=code_.encode(chosen);
        Result r{chosen,primary.data!=chosen||mirror.data!=chosen||
                        primary.check!=check||mirror.check!=check,
                        unsigned(a.corrected)+unsigned(b.corrected),unsigned(a.due)+unsigned(b.due)};
        if(r.repaired)store(primary,mirror,chosen);
        return r;
    }
};
} // namespace bp::v9
