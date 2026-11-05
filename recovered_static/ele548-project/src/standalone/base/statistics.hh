#pragma once
#include <vector>
namespace gem5 { namespace statistics {
struct Group { explicit Group(Group* = nullptr) {} };
struct Scalar { unsigned long long value=0; Scalar& operator++(int){++value;return *this;} };
struct Vector { std::vector<Scalar> values; void init(unsigned n){values.resize(n);} Scalar& operator[](unsigned n){return values.at(n);} };
}}
