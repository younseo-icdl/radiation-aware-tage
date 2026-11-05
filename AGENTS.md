# Project conventions

- Keep documentation and maintained code comments in English.
- Put reusable fault models in `radiation/`, predictor/protection implementations in `tage/`, and simulation integration or analysis in `simulation/`.
- Prefer reusable command-line tools and tests. Do not commit one-off report generators, campaign-specific coordinators, copied source snapshots, generated manifests, or build products.
- Preserve TAGE geometry, hashes, allocation policy, training order, and speculative behavior unless the experiment explicitly changes them. Distinguish functional replay from modeled CPU performance.
- Keep P0, P_ED, P_ECC, and P_TMR as matched baselines on S*=346 bits. Treat direct folding and periodic inspection as additional comparisons.
- Keep radiation event rate, multiplicity, time coordinate, logical placement, and physical interpretation explicit. Never treat duplicate timestamp records as MCUs.
- Verify meaningful changes with `make test`. Use `make gem5-test` for the bounded checksum regression when a compatible build is available. A C++ PASS does not establish O3 correctness or hardware cost.
- Use fresh build/output directories for independent producers. Do not overwrite files used by running experiments.
- Keep private benchmark distributions, course materials, papers, credentials, raw session logs, license files, and PDK/library data outside this public repository.
- Commit and push completed code/document changes to the configured remote. Preserve shared history; never force-push.
- Current implementation scope is C++ and gem5. RTL, Cadence, SPICE, and TCAD are outside this stage.
