#pragma once
#include <array>
#include <cstdint>
#include <stdexcept>
namespace bp::pipeline {
inline unsigned phi(const std::array<uint8_t, 130> &raw, unsigned length, unsigned width) {
    unsigned value = 0;
    for (unsigned age = 0; age < length; ++age)
        if (raw[age] & 1)
            value ^= 1u << (age % width);
    return value;
}
// NEW DERIVATION: exact inverse recurrence over a fold-opaque atomic undo.
// Both windows and the folded word are ACTUAL operands, including corruption.
// This retains the recurrent discrepancy; it is not overwrite recovery.
// Source windows must come from the same retained, unchanged raw buffer. No
// equivalence is claimed to a multi-cycle undo with interleaved source faults.
inline unsigned inverse_jump(unsigned stored_fold, const std::array<uint8_t, 130> &before,
                             const std::array<uint8_t, 130> &after, unsigned length, unsigned width,
                             unsigned undo) {
    if (!length || length > 130 || !width || width > 16 || undo > 1000 ||
        stored_fold >= (1u << width))
        throw std::invalid_argument("inverse jump geometry");
    const auto discrepancy = stored_fold ^ phi(before, length, width);
    const auto rotate = undo % width;
    const auto moved =
        rotate ? ((discrepancy >> rotate) | (discrepancy << (width - rotate))) & ((1u << width) - 1)
               : discrepancy;
    return moved ^ phi(after, length, width);
}
} // namespace bp::pipeline
