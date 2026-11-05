// TEST ONLY. Extracted from the actual R2 pinned source; not a predictor model.
// Full source SHA bindings are in history_state_sources.json.
#pragma once
#include <cstdint>
#include <array>
namespace history_state_pinned {
struct FoldedHistory
{
        unsigned comp;
        int compLength;
        int origLength;
        int outpoint;
        int bufferSize;

        FoldedHistory()
        {
            comp = 0;
        }

        void init(int original_length, int compressed_length)
        {
            origLength = original_length;
            compLength = compressed_length;
            outpoint = original_length % compressed_length;
        }

        void update(uint8_t * h)
        {
            comp = (comp << 1) | h[0];
            comp ^= h[origLength] << outpoint;
            comp ^= (comp >> compLength);
            comp &= (1ULL << compLength) - 1;
        }

        void restore(uint8_t * h)
        {
            comp ^= h[origLength] << outpoint;
            auto tmp = (comp & 1) ^ h[0];
            comp = (tmp << (compLength-1)) | (comp >> 1);
        }
    };
struct Mixer {
 const std::array<int,8> logTagTableSizes = {13,9,9,9,9,9,9,9};
int F(int A, int size, int bank) const
{
    int A1, A2;

    A = A & ((1ULL << size) - 1);
    A1 = (A & ((1ULL << logTagTableSizes[bank]) - 1));
    A2 = (A >> logTagTableSizes[bank]);
    A2 = ((A2 << bank) & ((1ULL << logTagTableSizes[bank]) - 1))
       + (A2 >> (logTagTableSizes[bank] - bank));
    A = A1 ^ A2;
    A = ((A << bank) & ((1ULL << logTagTableSizes[bank]) - 1))
      + (A >> (logTagTableSizes[bank] - bank));
    return (A);
}
};
}
