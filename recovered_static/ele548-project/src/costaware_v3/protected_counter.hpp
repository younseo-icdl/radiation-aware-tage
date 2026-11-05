#pragma once
#include "finite_fifo.hpp"
namespace bp {
class ProtectedCounter32 {
 uint32_t data=0;uint16_t check=0;unsigned width;WordSecded code;
 public:
 explicit ProtectedCounter32(unsigned w=32):width(w),code(w){if(w>32)throw std::invalid_argument("scalar width");}
 uint64_t corrected=0;
 uint32_t value(){Word w;w.limb[0]=data;auto d=code.decode(w,check);if(d.due)throw QueueIntegrityError("sequence counter DUE");if(d.corrected){data=d.payload.limb[0];check=d.check;++corrected;}return data;}
 void set(uint32_t v){data=v;Word w;w.limb[0]=v;check=code.encode(w);}
 uint32_t increment(){auto v=value()+1;set(v);return v;}
 size_t bits()const{return width+code.r+1;}
 bool bit(size_t id)const{if(id>=bits())throw std::out_of_range("counter bit");return id<width?((data>>id)&1):((check>>(id-width))&1);}
 void flip(size_t id){if(id>=bits())throw std::out_of_range("counter bit");if(id<width)data^=uint32_t(1)<<id;else check^=uint16_t(1)<<(id-width);}
};
}
