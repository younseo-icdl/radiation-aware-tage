CXX ?= g++
CPPFLAGS += -Itage/include -Itage/backend -Isimulation/cpp/shims
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare -Wno-misleading-indentation
BUILD := build
BACKEND := $(BUILD)/tage_base.o
TEST_SOURCES := $(wildcard tests/cpp/test_*.cpp)
TESTS := $(patsubst tests/cpp/%.cpp,$(BUILD)/tests/%,$(TEST_SOURCES))
HEADERS := $(shell find tage simulation/cpp/shims -name '*.hpp' -o -name '*.hh')
.PHONY: all test cpp-test python-test smoke clean
all: $(BUILD)/tage-sim
$(BUILD) $(BUILD)/tests:
	mkdir -p $@
$(BACKEND): tage/backend/cpu/pred/tage_base.cc $(HEADERS) | $(BUILD)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
$(BUILD)/tage-sim: simulation/cpp/main.cpp $(BACKEND) $(HEADERS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< $(BACKEND) -o $@
$(BUILD)/tests/%: tests/cpp/%.cpp $(BACKEND) $(HEADERS) | $(BUILD)/tests
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< $(BACKEND) -o $@
cpp-test: $(TESTS)
	@set -e; for t in $(TESTS); do echo "Running $$t"; "$$t"; done
PYTHON ?= python3
python-test: $(BUILD)/tage-sim
	$(PYTHON) -m unittest discover -s tests/python -v
test: cpp-test python-test
smoke: all
	$(BUILD)/tage-sim --demo 2000 --scheme P0
clean:
	rm -rf $(BUILD)/tests $(BUILD)/tage-sim $(BACKEND)

CC ?= gcc
$(BUILD)/checksum: simulation/workloads/checksum.c | $(BUILD)
	$(CC) -O2 -std=c11 -ffreestanding -fno-stack-protector -mstackrealign -nostdlib -static -no-pie -fno-pie -Wl,-e,_start $< -o $@
.PHONY: checksum
checksum: $(BUILD)/checksum
	$(BUILD)/checksum

GEM5_TREE ?= build/gem5
GEM5_OUTPUT ?= work/gem5-checksum
GEM5_JOBS ?= 4
.PHONY: gem5-test
gem5-test: $(BUILD)/checksum
	$(PYTHON) tests/gem5/checksum.py --tree $(GEM5_TREE) --output $(GEM5_OUTPUT) --jobs $(GEM5_JOBS)
