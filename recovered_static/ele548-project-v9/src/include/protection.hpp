#pragma once
// Research starting primitives. NOT a complete TAGE/recovery-controller implementation.
#include <cstdint>
#include <stdexcept>
#include <vector>
namespace bpseu {
inline uint64_t mask(unsigned w) {
    if(w==0 || w>64) throw std::invalid_argument("width outside 1..64");
    return w==64 ? ~uint64_t(0) : (uint64_t(1)<<w)-1;
}
inline bool parity(uint64_t x) { // even parity check: XOR of all bits
    bool p=false; while(x){p=!p;x&=x-1;} return p;
}
inline uint64_t flip_atomic(uint64_t word,unsigned width,const std::vector<unsigned>& bits) {
    if(word & ~mask(width))throw std::invalid_argument("nonlogical upper bits set");
    uint64_t flips=0;
    for(auto b:bits){
        if(b>=width)throw std::out_of_range("fault bit outside logical width");
        if(flips & (uint64_t(1)<<b))throw std::invalid_argument("duplicate bit in single event");
        flips|=uint64_t(1)<<b;
    }
    return word ^ flips; // no intermediate detector/repair calls
}
inline int64_t decode_signed(uint64_t word,unsigned width) {
    if(width<1 || width>32)throw std::invalid_argument("signed helper width 1..32");
    word &= mask(width);
    return (word & (uint64_t(1)<<(width-1))) ? int64_t(word)-int64_t(uint64_t(1)<<width) : int64_t(word);
}
inline uint64_t encode_signed(int64_t word,unsigned width) {
    if(width<1 || width>32)throw std::invalid_argument("signed helper width 1..32");
    int64_t bound=int64_t(1)<<(width-1);
    if(word < -bound || word >= bound)throw std::out_of_range("signed overflow");
    return uint64_t(word)&mask(width);
}
inline uint64_t parity_encode(uint64_t payload,unsigned k) {
    if(k<1 || k>63 || (payload & ~mask(k)))throw std::invalid_argument("invalid parity payload");
    return payload | (uint64_t(parity(payload))<<k);
}
inline bool parity_valid(uint64_t code,unsigned k) {
    if(k<1 || k>63 || (code & ~mask(k+1)))throw std::invalid_argument("invalid parity code");
    return !parity(code);
}
inline uint64_t majority(uint64_t a,uint64_t b,uint64_t c,unsigned k) {
    return ((a&b)|(a&c)|(b&c))&mask(k);
}
struct SecdedResult { uint64_t payload, repaired_code; bool corrected, uncorrectable; };
class Secded {
public:
    const unsigned k;
    unsigned r=0,n=0;
    explicit Secded(unsigned data_bits):k(data_bits) {
        if(k<1 || k>32)throw std::invalid_argument("starter SECDED supports payload 1..32 bits");
        while((uint64_t(1)<<r)<k+r+1)++r;
        n=k+r+1; // shortened Hamming code plus overall parity
    }
    static bool is_check(unsigned p){return (p&(p-1))==0;}
    uint64_t encode(uint64_t d)const {
        if(d & ~mask(k))throw std::invalid_argument("ECC payload too wide");
        uint64_t c=0;unsigned di=0;
        for(unsigned p=1;p<n;++p)if(!is_check(p)){c|=((d>>di)&1)<<(p-1);++di;}
        for(unsigned i=0;i<r;++i){
            const unsigned check=1u<<i;bool x=false;
            for(unsigned p=1;p<n;++p)if(p&check)x^=bool((c>>(p-1))&1);
            if(x)c|=uint64_t(1)<<(check-1);
        }
        if(parity(c))c|=uint64_t(1)<<(n-1);
        return c;
    }
    SecdedResult decode(uint64_t code)const {
        if(code & ~mask(n))throw std::invalid_argument("ECC code too wide");
        unsigned syndrome=0;
        for(unsigned p=1;p<n;++p)if((code>>(p-1))&1)syndrome^=p;
        const bool odd=parity(code);bool corrected=false,uncorrectable=false;
        uint64_t repaired=code;
        if(odd){
            if(syndrome==0){repaired^=uint64_t(1)<<(n-1);corrected=true;}
            else if(syndrome<n){repaired^=uint64_t(1)<<(syndrome-1);corrected=true;}
            else uncorrectable=true; // invalid shortened-code syndrome
        } else if(syndrome)uncorrectable=true;
        uint64_t d=0;unsigned di=0;
        for(unsigned p=1;p<n;++p)if(!is_check(p)){d|=((repaired>>(p-1))&1)<<di;++di;}
        return {d,repaired,corrected,uncorrectable};
        // For >=3 flipped bits this decoder can miscorrect or miss corruption.
        // Never use oracle error count to override its returned status.
    }
};
}
