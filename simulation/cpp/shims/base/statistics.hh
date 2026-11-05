#pragma once
#include <vector>
// Standalone counters expose the subset used by TAGEBase. gem5 builds use its
// real statistics library; this header is only on the C++ replay include path.
namespace gem5 {
namespace statistics {
struct Group {
    explicit Group(Group * = nullptr) {}
};
namespace units {
struct Count {
    static int get() { return 0; }
};
} // namespace units
struct Scalar {
    unsigned long long value = 0;
    Scalar(Group * = nullptr, const char * = "", int = 0, const char * = "") {}
    Scalar &operator++(int) {
        ++value;
        return *this;
    }
};
struct Vector {
    std::vector<Scalar> values;
    Vector(Group * = nullptr, const char * = "", int = 0, const char * = "") {}
    void init(unsigned n) { values.resize(n); }
    Scalar &operator[](unsigned n) { return values.at(n); }
};
} // namespace statistics
} // namespace gem5
#define ADD_STAT(name, unit, description) name(this, #name, unit, description)
