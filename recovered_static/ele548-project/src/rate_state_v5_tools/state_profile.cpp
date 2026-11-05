#include "rate_state_v5_r5/representation.hpp"
#include <iostream>
#include <bitset>
using namespace bp;using namespace bp::v5;
struct Profile:State{
 using State::State;
 void print(const char*name){
  std::set<unsigned> unique;unsigned contributions=0,offset=0;
  std::vector<std::bitset<256>> columns(maxHist);
  std::cout<<"{\"mode\":\""<<name<<"\",\"hist_lengths\":[";
  for(unsigned b=1;b<=nHistoryTables;++b){if(b>1)std::cout<<',';std::cout<<histLengths[b];for(auto a:selected[b])unique.insert(a);contributions+=selected[b].size();
   for(unsigned domain=0;domain<3;++domain){unsigned w=domain?tagTableTagWidths[b]-(domain==2):logTagTableSizes[b];
    for(auto age:selected[b]){unsigned lane=age%w;if(rep!=Representation::Direct&&rep!=Representation::Recurrent&&domain)lane=(age*(domain==1?3:5)+(age/w)*(domain==1?1:3)+domain)%w;columns[age].flip(offset+lane);}offset+=w;}
  }
  std::bitset<256> pivots[256];unsigned rank=0;
  for(auto col:columns){for(int bit=255;bit>=0;--bit)if(col[bit]){if(pivots[bit].any())col^=pivots[bit];else{pivots[bit]=col;++rank;break;}}}
  std::cout<<"],\"distinct_source_ages_per_lookup\":"<<unique.size()<<",\"raw_bit_contributions_all21_folds\":"<<3*contributions<<",\"direction_hash_output_bits\":"<<offset<<",\"GF2_direction_map_rank\":"<<rank<<",\"max_hist\":"<<maxHist<<"}";
 }
};
int main(){std::cout<<"[";bool comma=false;for(auto name:{"recurrent","direct","geometric","stratum","short32"}){if(comma)std::cout<<',';comma=true;Profile p(name,16);p.print(name);}std::cout<<"]\n";}
