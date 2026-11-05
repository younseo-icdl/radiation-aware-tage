#pragma once
#include <cstdint>
#include <memory>
namespace gem5 {
using Addr = uint64_t;
using ThreadID = unsigned;
struct StaticInst {};
using StaticInstPtr = std::shared_ptr<StaticInst>;
} // namespace gem5
