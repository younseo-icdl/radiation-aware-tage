#pragma once
#include "../protection/word.hpp"

namespace bp::v7 {
// Systematic SECDED sidecars. Decoding uses only actual payload/check cells,
// never an expected value, saved host metadata, event list or fault count.
class MetadataSecded {
    WordSecded code_;
 public:
    explicit MetadataSecded(unsigned width):code_(width){}
    unsigned data_bits()const{return code_.k;}
    unsigned check_bits()const{return code_.r+1;}
    uint16_t encode(const Word& data)const{return code_.encode(data);}
    WordSecded::Result decode(const Word& data,uint16_t check)const {
        return code_.decode(data,check);
    }
};
}
