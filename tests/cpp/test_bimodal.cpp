#include "tage/predictor/bimodal.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <iostream>
using namespace bp;
struct Reference : TageState {
    bool prediction(uint64_t pc) const { return btablePrediction[bindex(pc)]; }
    void train(uint64_t pc, bool taken) {
        auto *bi = makeBranchInfo(pc, true);
        tagePredict(0, pc, true, bi);
        baseUpdate(pc, taken, bi); delete bi;
    }
};
int main() {
    try {
        Bimodal base; Reference reference; std::mt19937_64 rng(548);
        for (unsigned i = 0; i < 100000; ++i) {
            uint64_t pc = rng()%65536; bool taken = rng()&1;
            if (base.predict(pc) != reference.prediction(pc))
                throw std::runtime_error("bimodal prediction");
            base.update(pc, taken); reference.train(pc, taken);
            if (i%1024 == 0) {
                auto snapshot = reference.save();
                if (base.prediction != snapshot.pred || base.hysteresis != snapshot.hyst)
                    throw std::runtime_error("bimodal shared hysteresis training");
            }
        }
        auto p = base.prediction, h = base.hysteresis;
        base.flip(17); base.flip(8192+3);
        if (base.prediction[17] == p[17] || base.hysteresis[3] == h[3] || base.bits()!=10240)
            throw std::runtime_error("base exposure");
        bool rejected = false;
        try { base.flip(10240); } catch (const std::out_of_range &) { rejected = true; }
        if (!rejected) throw std::runtime_error("base site bounds");
        std::cout << "PASS minimal bimodal matches TAGE base/shared-hysteresis updates over 100k branches; prediction/hysteresis bit exposure\n";
        return 0;
    } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 1; }
}
