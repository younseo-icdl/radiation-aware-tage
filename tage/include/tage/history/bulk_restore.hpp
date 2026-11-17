#pragma once
#include <cstdint>
#include <stdexcept>

namespace bp {
// Algebraic equivalent of repeated pinned FoldedHistory::restore calls. Read
// both windows from the CURRENT live circular history, including any upsets.
// This is a correctness kernel, not a free/modeled hardware restore port.
template<class ReadAge>
uint32_t bulk_restore_fold(uint32_t stored, unsigned length, unsigned width,
                           unsigned count, ReadAge read_age) {
    if(!length || length>130 || !width || width>31 || count>512)
        throw std::invalid_argument("bulk restore geometry/count");
    const uint32_t mask=(uint32_t(1)<<width)-1;
    if(stored & ~mask) throw std::invalid_argument("bulk restore stored width");
    uint32_t before=0, after=0;
    for(unsigned age=0;age<length;++age) {
        before^=uint32_t(bool(read_age(age)))<<(age%width);
        after^=uint32_t(bool(read_age(age+count)))<<(age%width);
    }
    uint32_t residual=stored^before;
    const unsigned shift=count%width;
    if(shift) residual=((residual>>shift)|(residual<<(width-shift)))&mask;
    return after^residual;
}
} // namespace bp
