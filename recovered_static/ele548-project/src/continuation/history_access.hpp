#pragma once
#include "predictor/tage_adapter.hpp"
namespace bp {
class ContinuationAccess : public TageAccess {
 public:
 explicit ContinuationAccess(const gem5::TAGEBaseParams& p):TageAccess(p){}
 bool raw_bit(unsigned age)const {if(age>maxHist)throw std::out_of_range("raw transition age");return threadHistory[0].globalHist.at(threadHistory[0].ptGhist+age)&1;}
 unsigned fold_length(unsigned word)const {if(word>=21)throw std::out_of_range("fold word");return histLengths[word/3+1];}
 Word phi(unsigned word)const {Word v;auto specs=history_words();auto width=specs.at(word).width;for(unsigned age=0;age<fold_length(word);++age)if(raw_bit(age))v.flip(age%width);return v;}
};
