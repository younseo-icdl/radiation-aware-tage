#pragma once
#include "base/statistics.hh"
namespace gem5 { struct SimObject: statistics::Group {template<class P> explicit SimObject(const P&) {} virtual ~SimObject()=default; virtual void init(){} }; }
