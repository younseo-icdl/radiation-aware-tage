#pragma once
#include <cstdint>
#include <stdexcept>
namespace bp {
enum class FaultStream : uint8_t {Time=1, Multiplicity=2, Location=3};
// Injective for all permitted master/role pairs. Adjacent trials cannot reuse
// another role's seed. Shared master across matched conditions is intentional.
inline uint64_t fault_seed(uint64_t master,FaultStream role){
    if(master>=(uint64_t(1)<<56))throw std::invalid_argument("fault master seed exceeds namespace");
    return (master<<8)|uint8_t(role);
}
}
