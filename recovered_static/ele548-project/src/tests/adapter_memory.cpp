#include "predictor/tage_adapter.hpp"
#include <iostream>
int main(){
 bp::TageAdapter a;
 for(unsigned i=0;i<5000;++i)a.step({0x4000+(i%100)*4,0x9000,bool(i%3),bool(i%13)});
 auto s=a.snapshot();bp::TageAdapter b;b.restore(s);
 auto sites=b.core.sites();std::vector<size_t> ids;
 for(unsigned k=0;k<6;++k)ids.push_back(std::find_if(sites.begin(),sites.end(),[=](const bp::Site& t){return t.kind==k;})->id);
 b.core.corrupt(ids);
 for(unsigned i=0;i<2000;++i)b.step({0x5000+(i%50)*4,0xa000,bool(i%5),true});
 b.restore(s);if(!b.core.equal(a.core))return 2;
 std::cout<<"PASS adapter allocation, history transitions, six-field injection and snapshot lifecycle\n";
}
