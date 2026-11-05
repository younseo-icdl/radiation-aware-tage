# Radiation-aware TAGE

ELE548 research on the performance impact of SEUs in TAGE state and the cost of recovery. The required comparisons retain the same selected state under P0, parity/exclude/relearn, SECDED and TMR. Periodic parity and exact direct folding are additional comparisons.

## Recovery status — 2026-11-05

The original experiment workspace was deleted. This repository preserves **partial source recovery from surviving attachments and historical text-edit records**. Recovered files are candidates, not a rebuilt or revalidated copy of the original producer. No prior experiments have been rerun during recovery.

- `final_b4/`: curated latest B4 source candidates and their original-path map; start here.
- `recovered_static/`: historical source candidates assembled from exact patch context, literal file writes and virtual text/copy transformations.
- `recovered/`: the independent first-pass recovery from patch requests.
- `recovery/`: file hashes, provenance, unresolved-state summaries and upstream source pin.
- `results/summaries/b4_eval_logged_summary.csv`: 42 non-P0 aggregate rows recovered from historical output. These are not the missing per-owner raw records.
- `scripts/`: recovery and backup tools. Recovery scripts do not execute historical build or simulation commands.

The deleted final ZIP, ELF, complete source lock and all original trial logs have **not** been recovered. Available tool-output hashes are compared in `recovery/HISTORICAL_HASH_COMPARISON.csv`; absence of a hash match is not verification. Absolute include paths and dependencies may need restoration before a future build.

The original attachments, papers, course/reference files and private recovery evidence are kept in a separate local download bundle. This public repository contains research-code candidates and authored summaries, rather than the private input bundle.

## Historical experiment interpretation

The October records reported completion of B4 clean36, development-fault102 and independent-fault408 program runs, with CPU cap4199. This is a historical recorded result, not a new verification after deletion. SOURCE and WHOLE exposure differ; n=8 owner-level evaluation and shared A/C must not be counted as additional independent samples. Benefits measured against common finite P0 do not establish native-relative superiority. C−A=0 in a common stage-fit model does not mean physical protection costs are zero.

No recovery claim establishes RTL/PPA, mission FIT or full CPU safety. See [recovery notes](docs/RECOVERY.ko.md) and [backup workflow](docs/BACKUP_POLICY.ko.md).
