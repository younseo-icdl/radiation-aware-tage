#include "replay/e1_trace.hpp"
#include <iomanip>
#include <iostream>
using namespace bp;
int main(int argc,char**argv){try{
    if(argc!=6)throw std::invalid_argument("usage: e1_warmup TRACE WORKLOAD ANCHOR HORIZON OUTPUT_CSV");
    auto trace=read_e1_trace(argv[1]);unsigned anchor=std::stoul(argv[3]),horizon=std::stoul(argv[4]);
    auto window=e1_window(trace,anchor,horizon);std::ofstream out(argv[5]);
    if(!out)throw std::runtime_error("output unavailable");
    out<<"workload,warmup_branches,observation_branches,instructions,misses,MPKI,prediction_disagreement_vs_500k,status\n";
    std::vector<std::vector<bool>> predictions;std::vector<unsigned> misses;
    for(unsigned warmup:{20000u,100000u,200000u,400000u,500000u}){
        if(anchor<warmup)throw std::invalid_argument("warmup before input start");
        TageAdapter adapter;
        for(size_t i=(anchor==warmup?0:trace.conditionals[anchor-warmup]);i<window.begin;++i)adapter.step(trace.controls[i].branch);
        std::vector<bool> prediction;unsigned miss=0;
        for(size_t i=window.begin;i<window.end;++i){const auto& b=trace.controls[i].branch;bool p=adapter.step(b);
            if(b.conditional){prediction.push_back(p);miss+=p!=b.taken;}}
        if(prediction.size()!=horizon)throw std::runtime_error("warmup horizon mismatch");
        predictions.push_back(std::move(prediction));misses.push_back(miss);
    }
    for(unsigned i=0;i<5;++i){unsigned disagreement=0;for(unsigned b=0;b<horizon;++b)disagreement+=predictions[i][b]!=predictions[4][b];
        out<<std::setprecision(17)<<argv[2]<<','<<std::vector<unsigned>{20000,100000,200000,400000,500000}[i]<<','<<horizon<<','<<window.instructions<<','<<misses[i]<<','<<1000.0*misses[i]/window.instructions<<','<<disagreement<<",PASS\n";}
    out.flush();if(!out)throw std::runtime_error("output failure");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL_EXECUTION "<<e.what()<<'\n';return 1;}}
