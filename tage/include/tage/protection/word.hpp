#pragma once
#include <array>
#include <cstdint>
#include <stdexcept>

namespace bp {
// Explicit bits, up to 192. No sizeof/object-representation fault injection.
struct Word {
    std::array<uint64_t, 3> limb{};
    bool bit(unsigned i) const {
        if (i >= 192)
            throw std::out_of_range("word bit");
        return (limb[i / 64] >> (i % 64)) & 1;
    }
    void set(unsigned i, bool v) {
        if (i >= 192)
            throw std::out_of_range("word bit");
        uint64_t m = uint64_t(1) << (i % 64);
        if (v)
            limb[i / 64] |= m;
        else
            limb[i / 64] &= ~m;
    }
    void flip(unsigned i) {
        if (i >= 192)
            throw std::out_of_range("word bit");
        limb[i / 64] ^= uint64_t(1) << (i % 64);
    }
    bool operator==(const Word &b) const { return limb == b.limb; }
    bool operator!=(const Word &b) const { return !(*this == b); }
    bool fits(unsigned width) const {
        if (width > 192)
            return false;
        unsigned whole = width / 64, tail = width % 64;
        if (tail && (limb[whole] >> tail))
            return false;
        for (unsigned j = whole + (tail != 0); j < 3; ++j)
            if (limb[j])
                return false;
        return true;
    }
    bool parity() const {
        return (__builtin_parityll(limb[0]) ^ __builtin_parityll(limb[1]) ^
                __builtin_parityll(limb[2]));
    }
    bool parity_mask(const Word &b) const {
        return (__builtin_parityll(limb[0] & b.limb[0]) ^ __builtin_parityll(limb[1] & b.limb[1]) ^
                __builtin_parityll(limb[2] & b.limb[2]));
    }
};
inline Word majority(const Word &a, const Word &b, const Word &c) {
    Word r;
    for (unsigned i = 0; i < 3; ++i)
        r.limb[i] = (a.limb[i] & b.limb[i]) | (a.limb[i] & c.limb[i]) | (b.limb[i] & c.limb[i]);
    return r;
}

// Systematic shortened extended Hamming: payload remains in the original
// logical cells; r Hamming check cells and one overall parity are sidecars.
class WordSecded {
    std::array<Word, 8> masks{};
    std::array<int, 256> position_to_payload{};

  public:
    unsigned k, r = 0, n;
    explicit WordSecded(unsigned width) : k(width) {
        if (k < 1 || k > 180)
            throw std::invalid_argument("SECDED payload width");
        while ((1u << r) < k + r + 1)
            ++r;
        if (r > 8)
            throw std::invalid_argument("SECDED syndrome width");
        n = k + r + 1;
        position_to_payload.fill(-1);
        unsigned d = 0;
        for (unsigned p = 1; p < n; ++p)
            if (p & (p - 1)) {
                position_to_payload[p] = d;
                for (unsigned j = 0; j < r; ++j)
                    if (p & (1u << j))
                        masks[j].set(d, true);
                ++d;
            }
        if (d != k)
            throw std::logic_error("SECDED geometry");
    }
    uint16_t encode(const Word &data) const {
        if (!data.fits(k))
            throw std::invalid_argument("nonlogical ECC payload bits");
        uint16_t check = 0;
        for (unsigned j = 0; j < r; ++j)
            if (data.parity_mask(masks[j]))
                check |= 1u << j;
        if (data.parity() ^ bool(__builtin_parity(check)))
            check |= 1u << r;
        return check;
    }
    struct Result {
        Word payload;
        uint16_t check;
        bool corrected = false, due = false;
        unsigned syndrome = 0;
    };
    Result decode(const Word &data, uint16_t check) const {
        if (!data.fits(k))
            throw std::invalid_argument("nonlogical ECC payload bits");
        if (check >> (r + 1))
            throw std::invalid_argument("nonlogical ECC check bits");
        unsigned syndrome = check & ((1u << r) - 1);
        for (unsigned j = 0; j < r; ++j)
            if (data.parity_mask(masks[j]))
                syndrome ^= 1u << j;
        bool odd = data.parity() ^ bool(__builtin_parity(check));
        Result result{data, check, false, false, syndrome};
        if (odd) {
            if (syndrome == 0) {
                result.check ^= 1u << r;
                result.corrected = true;
            } else if (syndrome < n) {
                if (position_to_payload[syndrome] >= 0)
                    result.payload.flip(position_to_payload[syndrome]);
                else
                    result.check ^= 1u << __builtin_ctz(syndrome);
                result.corrected = true;
            } else
                result.due = true;
        } else if (syndrome)
            result.due = true;
        // Real decoder law; no oracle K or golden payload here. >=3 errors may
        // be missed or miscorrected, including invalid shortened syndromes.
        return result;
    }
};
} // namespace bp
