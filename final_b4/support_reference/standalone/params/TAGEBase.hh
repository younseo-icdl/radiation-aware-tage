#pragma once
#include <vector>
#include <cstdint>
namespace gem5 {
// Explicit plain TAGE geometry from pinned BranchPredictor.py. Offline replay
// uses non-speculative direction history and a finite implementation buffer.
struct TAGEBaseParams {
 unsigned logRatioBiModalHystEntries=2,nHistoryTables=7,tagTableCounterBits=3,tagTableUBits=2;
 unsigned histBufferSize=2097152,minHist=5,maxHist=130,pathHistBits=16;
 std::vector<unsigned> tagTableTagWidths{0,9,9,10,10,11,11,12};
 std::vector<int> logTagTableSizes{13,9,9,9,9,9,9,9};
 unsigned numThreads=1; uint64_t logUResetPeriod=18; int64_t initialTCounterValue=1<<17;
 unsigned numUseAltOnNa=1,useAltOnNaBits=4,maxNumAlloc=1,instShiftAmt=0;
 bool takenOnlyHistory=false; std::vector<bool> noSkip{}; bool speculativeHistUpdate=false;
};
}
