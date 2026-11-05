#pragma once
#include <cstdint>
#include <random>
#include <stdexcept>
#include <vector>
namespace bp {
struct MultiplicityProfile {
 uint64_t k1,k2;
 MultiplicityProfile(uint64_t a,uint64_t b):k1(a),k2(b){if(a+b==0||a>1000000||b>1000000)throw std::invalid_argument("invalid K=1/2 weights");}
 unsigned draw(std::mt19937_64& rng)const {return std::uniform_int_distribution<uint64_t>(0,k1+k2-1)(rng)<k1?1:2;}
};
// Source informs K only. This flattening is an explicit logical mapping assumption.
// Sample valid anchors; never clip K, wrap at boundaries, or XOR one bit twice.
inline std::vector<size_t> logical_adjacent_event(const std::vector<size_t>& field,unsigned k,std::mt19937_64& rng){
 if(k==0||k>field.size())throw std::invalid_argument("event larger than field");
 size_t first=std::uniform_int_distribution<size_t>(0,field.size()-k)(rng);
 return std::vector<size_t>(field.begin()+first,field.begin()+first+k);
}
}
