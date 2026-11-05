#include "predictor/protected_adapter.hpp"
#include <iostream>
using namespace bp;
int main(){try{
    std::cout<<"scheme,site_id,structure,word_id,bit,width,replica,selected_payload\n";
    for(auto scheme:{Scheme::P0,Scheme::ED,Scheme::ECC,Scheme::TMR}){
        ProtectedAdapter p(scheme);auto sites=p.predictor.core.sites();
        for(const auto& s:sites){std::string word;
            if(s.kind==4)word="raw_path:"+std::to_string(s.bank);
            else word=std::string(field_name(s.kind))+":"+std::to_string(s.bank)+":"+std::to_string(s.row);
            std::cout<<scheme_name(scheme)<<','<<s.id<<','<<field_name(s.kind)<<','<<word<<','<<s.bit<<','<<s.width<<",0,"<<(s.kind>=4)<<'\n';
        }
        for(const auto& s:p.protection.additional_sites()){
            std::string word=s.structure=="refill_remaining"||s.structure=="history_epoch"?s.structure:p.protection.specs()[s.word].id;
            std::cout<<scheme_name(scheme)<<','<<s.id<<','<<s.structure<<','<<word<<','<<s.bit<<','<<s.width<<','<<s.replica<<",0\n";
        }
    }
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
