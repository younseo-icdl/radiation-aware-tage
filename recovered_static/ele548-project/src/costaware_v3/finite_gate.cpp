#include "finite_fifo.hpp"
#include <iostream>
using namespace bp;
int main(){try{unsigned cases=0;
 for(unsigned L:{1u,2u})for(unsigned II:{1u,2u}){
  FiniteRmwQueue q(50,4,L,II);Word a;a.limb[0]=17;Word b;b.limb[0]=23;q.push(a);q.push(b);if(!q.start())throw std::runtime_error("start");int state=0;
  for(unsigned tick=1;tick<=8;++tick){auto value=q.tick();if(value){state+=value->limb[0];++cases;}if(tick<L&&state)throw std::runtime_error("early functional publication");q.start();}
  if(state!=40||!q.conserved())throw std::runtime_error("work lost/order");++cases;
 }
 FiniteRmwQueue base(50,4,2,1);for(unsigned j=0;j<4;++j){Word w;w.limb[0]=19+j;base.push(w);}base.start();auto snapshot=base.save();
 for(size_t bit=0;bit<base.bits();++bit){FiniteRmwQueue q(50,4,2,1);q.restore(snapshot);q.flip(bit);unsigned sum=0;
  for(unsigned cycle=0;cycle<16;++cycle){auto value=q.tick();if(value)sum+=value->limb[0];q.start();}
  if(sum!=82||!q.conserved())throw std::runtime_error("single-cell queue corruption not corrected");++cases;}
 FiniteRmwQueue due(50,4,1,1);due.restore(snapshot);due.flip(0);due.flip(1);bool caught=false;try{due.tick();}catch(const QueueIntegrityError&){caught=true;}if(!caught)throw std::runtime_error("control DUE missed");due.clear();if(!due.conserved())throw std::runtime_error("cancel accounting");++cases;
 auto copy=base;copy.flip(0);if(copy.bit(0)==base.bit(0))throw std::runtime_error("shallow queue copy");++cases;
 std::cout<<"PASS "<<cases<<" delayed-publication/L-vs-II/FIFO/every-cell SBU/control-DUE/deep-copy cases\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
