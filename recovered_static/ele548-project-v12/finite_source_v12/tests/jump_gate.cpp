#include "inverse_jump.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include "/home/youns/workspace/ele548-project-v10/cost_v10/tests/history_state_pinned_reference.hpp"
#include <iostream>
#include <random>
using namespace bp::v12;
static void need(bool v,const char*w){if(!v)throw std::runtime_error(w);}
int main(){try{
 bp::RoundState geometry;auto words=geometry.history_words();std::mt19937_64 rng(0x12a10);uint64_t comparisons=0,dirty=0;
 std::array<uint8_t,1130> ring;for(auto&x:ring)x=rng()&1;
 auto window=[&](unsigned head){std::array<uint8_t,130> r{};for(unsigned age=0;age<130;++age)r[age]=ring[(head+age)%1130];return r;};
 for(unsigned pattern=0;pattern<3;++pattern){
  if(pattern==1){ring[45]^=1;ring[46]^=1;ring[47]^=1;}
  if(pattern==2)for(auto&x:ring)x=rng()&1;
  constexpr unsigned head=37;auto before=window(head);
  for(unsigned w=0;w<21;++w){const auto length=geometry.fold_length(w),width=words[w].width;const unsigned value=rng()&((1u<<width)-1);
   history_state_pinned::FoldedHistory pinned;pinned.init(length,width);pinned.comp=value;uint8_t raw[131]={};
   for(unsigned n=0;n<=1000;++n){auto after=window(head+n);need(inverse_jump(value,before,after,length,width,n)==pinned.comp,"jump differs from pinned inverse on arbitrary corrupted state");++comparisons;
    if(n<1000){raw[0]=ring[(head+n)%1130];raw[length]=ring[(head+n+length)%1130];pinned.restore(raw);}}
  }
 }
 // Every folded SBU remains a rotated discrepancy at every retained undo span.
 const unsigned head=79;auto before=window(head);
 for(unsigned w=0;w<21;++w){auto length=geometry.fold_length(w),width=words[w].width;
  for(unsigned bit=0;bit<width;++bit){auto value=phi(before,length,width)^(1u<<bit);history_state_pinned::FoldedHistory pinned;pinned.init(length,width);pinned.comp=value;uint8_t raw[131]={};
   for(unsigned n=0;n<=1000;++n){auto after=window(head+n);auto result=inverse_jump(value,before,after,length,width,n);
    need(result==pinned.comp&&result!=phi(after,length,width),"jump silently became overwrite recovery");++dirty;
    if(n<1000){raw[0]=ring[(head+n)%1130];raw[length]=ring[(head+n+length)%1130];pinned.restore(raw);}}
  }
 }
 std::cout<<"{\"status\":\"PASS_EXACT_INVERSE_JUMP_LEMMA_NOT_STAGED_CONTROLLER\",\"arbitrary_state_comparisons\":"<<comparisons<<",\"dirty_fold_span_checks\":"<<dirty<<",\"max_undo\":1000,\"static_raw_assumption\":true,\"controller_implemented\":false}\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
