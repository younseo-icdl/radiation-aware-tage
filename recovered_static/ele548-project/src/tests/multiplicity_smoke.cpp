#include "fault/multiplicity.hpp"
#include <cassert>
#include <set>
#include <iostream>
int main(){std::mt19937_64 rng(548);bp::MultiplicityProfile one(1,0),two(0,1);
 for(int i=0;i<100;++i){assert(one.draw(rng)==1);assert(two.draw(rng)==2);auto ids=bp::logical_adjacent_event({10,11,12,13},2,rng);assert(ids.size()==2&&ids[1]==ids[0]+1&&ids[0]>=10&&ids[1]<=13);}
 for(auto weights:{std::pair<unsigned,unsigned>{205,9},{142,5}}){bp::MultiplicityProfile p(weights.first,weights.second);unsigned pairs=0;for(int i=0;i<10000;++i)pairs+=p.draw(rng)==2;assert(pairs>0&&pairs<10000);}
 bool bad=false;try{bp::logical_adjacent_event({10},2,rng);}catch(const std::invalid_argument&){bad=true;}assert(bad);
 bad=false;try{bp::MultiplicityProfile p(0,0);}catch(const std::invalid_argument&){bad=true;}assert(bad);
 std::cout<<"PASS exact K support, valid unique adjacent sites, boundary rejection and source-profile draws\n";
}
