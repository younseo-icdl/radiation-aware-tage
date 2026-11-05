# Radiation models and source semantics

The model has four independent choices: **arrival process**, **multiplicity**, **logical placement**, and **exposure coordinate**. Source measurements constrain some of these choices; they do not automatically determine a target CPU's physical fault rate.

## CHARM-informed marks

The selected 6T SRAM experiment in CHARM Table II reports 205 single-bit events and 9 double-bit events. The corresponding profile is

- P(K=1)=205/214.
- P(K=2)=9/214.
- E[K]=223/214, approximately 1.04206 flips per event.

This profile uses that table and experiment. It does not assert that K is naturally bounded by two; other reported conditions include larger clusters. The measured SRAM technology is not assumed to be the predictor's physical implementation.

The `charm` raw-history profile places all K bits atomically in a contiguous logical-age run within raw130. Logical neighbors are not claimed to be physical neighboring cells. `single` uses K=1. Uniform S*=346 single-event sensitivity samples one selected bit without deriving a radiation rate.

## Arrival process and units

For a declared homogeneous Poisson process, N(t) has mean lambda*t and interarrival times are exponential with mean 1/lambda. `--rate` is **events per declared exposure unit**. Expected bit flips per unit are lambda*E[K]; an event rate is not divided by E[K].

The cycle-based SOURCE stress reference is 2,000 events/s at a modeled 2GHz CPU clock, or 1e-6 events/cycle. This is an assumed stress rate, not a calibrated target-process measurement. A branch-based rate is a separate experiment parameter: cycles, executed control branches, conditional branches, and wall-clock seconds are not interchangeable exposure units.

`python -m radiation` generates continuous Poisson arrivals and rounds each arrival up to its integer exposure position. Separate events landing in the same position remain separate atomic events. A single-event experiment instead samples an integer position uniformly within the declared horizon and accepts no rate parameter. C++ injection occurs before the one-based control-branch ordinal. The gem5 schedule stores absolute ticks, at 500 ticks per cycle for the pinned 2GHz model.

The generator uses NumPy PCG64 and namespace-v2 SeedSequence entropy. Time, K/catalog selection, location/geometry, and dispersed controls use declared independent roles. Predictor allocation RNG is separate. Preserve a generated schedule across a matched comparison; do not regenerate it from candidate-dependent run length.

## CERN cluster data

The [public cluster collection](https://doi.org/10.5281/zenodo.8314389) provides coordinate records. `radiation/cern.py` validates an entire file: bounding boxes, anchors, coordinate counts, uniqueness, indexed records, and optional clock labels. Suspected origin sentinel records are flagged and retained.

```bash
.venv/bin/python -m radiation.data fetch-cern --destination data/cern
.venv/bin/python -m radiation.data cern data/cern/clust_p29MeV.txt
.venv/bin/python -m radiation --seed 548 --horizon 10000 --rate 0.001 \
  --scope sstar --multiplicity cern --catalog data/cern/clust_p29MeV.txt \
  --mapping interleaved --time-unit branches --output work/cern/events.txt
```

Acquisition uses fixed provider URLs and checks provider MD5 before accepting a file. A mismatch preserves an existing file and fails. No API availability is required.

Conditional footprint stress samples published K>=2 records uniformly, then translates each complete shape onto an **assumed 16x22 logical tile** with 346 valid cells. Contiguous-word, interleaved-word, and dispersed-same-K mappings are controls. Unmappable shapes fail; clusters are never silently clipped. This does not identify P(MCU), true particle identity, source live exposure, or target physical cell placement. The source clustering methods include [2014](https://doi.org/10.1109/TNS.2014.2313742), [2015](https://doi.org/10.1109/TNS.2015.2496874), and [2020 characterization](https://doi.org/10.1109/REDW51883.2020.9325822). Clock labels are not a calibrated arrival stream for this CPU.

## Flying Laptop detection timestamps

The supplied [DaRUS dataset](https://doi.org/10.18419/DARUS-443) contains **2,129 raw rows**, **2,055 distinct complete records/timestamps**, and **74 duplicate extra rows**. Duplicate records are not evidence of multiple-cell upsets.

```bash
.venv/bin/python -m radiation.data flying data/flying/DetectedSEUTimeTags_with_TLE_Data.csv
.venv/bin/python -m radiation.data flying data/flying/DetectedSEUTimeTags_with_TLE_Data.csv \
  --schedule work/flying/events.txt --horizon 100000 --time-unit branches \
  --duplicates collapse --timing observed --multiplicity single --seed 548
```

`radiation/empirical.py` supports retained-record versus collapsed-timestamp sensitivity, original detection ordering, permuted gaps, and fixed-count Poisson timing (sorted uniform positions conditional on N). Mapping the source span into a simulation horizon is explicit time compression. SBU or independent CHARM marks are separate assumptions. Stable source-group/occurrence namespaces match marks across timing and duplicate controls.

Detector live intervals, sensitive target bit count, bit addresses, and source-to-target scaling are not established by these timestamps. Counts divided by the observed time span are descriptive densities, not target per-bit SEU rates.

## Scope-specific rates and limitations

SOURCE targets raw130. SSTAR346 is a selected-state conditional experiment. WHOLE must include the actual candidate's table state and added logical storage from its generated manifest. For a per-bit Poisson K=1 law, candidate total rate is the per-bit rate times exposed bit count. Matching raw total event counts across candidates with different storage changes the per-bit law.

The WHOLE accelerated reference used in prior experiment definitions is `(1.05e-14 * 20 / 3600) * 1e15` events per bit per second. The acceleration and the source cross-section/flux assumptions must accompany any use of this reference. The provided CLI creates SOURCE and SSTAR schedules; it does not infer a WHOLE semantic coupling or generate a physical FIT estimate. Supply an explicitly declared manifest-based schedule for whole-state studies.

No profile here establishes mission FIT, dose effects, a PDK-specific cross section, or physical MCU adjacency. TCAD is not used.
