#pragma once
#include <array>
#include <cstdint>
#include <stdexcept>
namespace bp::v6 {
// Canonical pinned configuration, checked against actual SimObject geometry.
// Seven 9-bit indices; tags 9,9,10,10,11,11,12; provider result fields.
struct Payload {
 static constexpr std::array<unsigned,26> widths{{9,9,9,9,9,9,9,9,9,10,10,11,11,12,3,3,9,9,13,1,1,1,1,1,3,1}};
 static constexpr unsigned width_sum(){unsigned n=0;for(auto w:widths)n+=w;return n;}
 std::array<uint64_t,4> data{};
 size_t bits()const{return width_sum();}
 bool bit(size_t n)const{if(n>=bits())throw std::out_of_range("pipeline payload bit");return (data[n/64]>>(n%64))&1;}
 void flip(size_t n){if(n>=bits())throw std::out_of_range("pipeline payload bit");data[n/64]^=uint64_t(1)<<(n%64);}
 unsigned get(unsigned field)const{unsigned start=0;for(unsigned i=0;i<field;++i)start+=widths.at(i);unsigned v=0;for(unsigned b=0;b<widths.at(field);++b)v|=unsigned(bit(start+b))<<b;return v;}
 void put(unsigned field,unsigned v){unsigned start=0;for(unsigned i=0;i<field;++i)start+=widths.at(i);for(unsigned b=0;b<widths.at(field);++b){auto n=start+b;bool x=(v>>b)&1;if(bit(n)!=x)flip(n);}}
 template<class BI> void capture_addresses(const BI& b){for(unsigned i=1;i<=7;++i){put(i-1,b.tableIndices[i]);put(6+i,b.tableTags[i]);}}
 template<class BI> void restore_addresses(BI& b)const{for(unsigned i=1;i<=7;++i){b.tableIndices[i]=get(i-1);b.tableTags[i]=get(6+i);}}
 template<class BI> void capture_response(const BI& b){if(b.condBranch)capture_addresses(b);put(14,b.hitBank);put(15,b.altBank);put(16,b.hitBankIndex);put(17,b.altBankIndex);put(18,b.bimodalIndex);put(19,b.tagePred);put(20,b.altTaken);put(21,b.longestMatchPred);put(22,b.pseudoNewAlloc);put(23,b.valid);put(24,b.provider<=3?b.provider:4);}
 template<class BI> void restore_response(BI& b)const{restore_addresses(b);b.hitBank=get(14);b.altBank=get(15);b.hitBankIndex=get(16);b.altBankIndex=get(17);b.bimodalIndex=get(18);b.tagePred=get(19);b.altTaken=get(20);b.longestMatchPred=get(21);b.pseudoNewAlloc=get(22);b.valid=get(23);auto p=get(24);if(p>4)throw std::runtime_error("FAIL_PIPELINE invalid provider encoding");b.provider=p==4?unsigned(-1):p;}
};
}
