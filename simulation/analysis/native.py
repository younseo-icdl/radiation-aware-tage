"""Stream paired native CPU traces without substituting miss penalties for time."""
import argparse
import csv
import gzip
from itertools import zip_longest
import json
from pathlib import Path
from .recovery import RecoverySeries, timing_windows


def trace(directory):
    with gzip.open(Path(directory)/'committed.csv.gz', 'rt') as stream:
        for row in csv.DictReader(stream):
            if None in row or None in row.values():
                raise ValueError('malformed committed trace')
            yield row


def summarize(clean, fault):
    clean, fault = Path(clean), Path(fault)
    u0 = json.loads((clean/'native.json').read_text())
    uf = json.loads((fault/'native.json').read_text())
    if any(s['missing_lookup_mapping'] or s['missing_retirement_mapping'] for s in (u0, uf)):
        raise ValueError('missing lookup/retirement joins')
    with (fault/'events.csv').open() as stream:
        events = list(csv.DictReader(stream))
    if len(events) != 1 or int(events[0]['multiplicity']) != 1:
        raise ValueError('single-event single-bit recovery reader required')
    event_tick = int(events[0]['applied_tick'])
    metrics = {name: RecoverySeries() for name in
               ('own_fold_invariant', 'fold_reference_given_equal_source',
                'index_mismatch', 'query_tag_mismatch', 'provider_metadata_mismatch',
                'prediction_difference', 'harmful', 'helpful')}
    counts = {'paired_branches': 0, 'paired_conditionals': 0, 'post_event_conditionals': 0,
              'fold_reference_alignment_gaps': 0, 'harmful': 0, 'helpful': 0}
    coordinates = {}
    identity = ('branch_id', 'pc', 'target', 'taken', 'conditional')
    source = ('raw_limb0', 'raw_limb1', 'raw_limb2', 'path', 'nonspec_path')

    def checkpoints():
        conditional_id = 0
        for left, right in zip_longest(trace(clean), trace(fault)):
            if left is None or right is None or any(left[k] != right[k] for k in identity):
                raise ValueError('NA_ALIGNMENT: committed architectural branch sequence differs')
            counts['paired_branches'] += 1
            if int(left['branch_id']) != counts['paired_branches']:
                raise ValueError('nonconsecutive branch identity')
            if left['conditional'] != '1':
                continue
            conditional_id += 1
            counts['paired_conditionals'] += 1
            post = int(right['lookup_tick']) >= event_tick
            lp, rp, taken = (int(x) for x in
                            (left['tage_prediction'], right['tage_prediction'], right['taken']))
            harmful, helpful = int(lp == taken and rp != taken), int(lp != taken and rp == taken)
            if post:
                counts['post_event_conditionals'] += 1
                same_source = all(left[k] == right[k] for k in source)
                counts['fold_reference_alignment_gaps'] += not same_source
                counts['harmful'] += harmful
                counts['helpful'] += helpful
                values = {
                    'own_fold_invariant': int(right['fold_invariant_distance']),
                    'fold_reference_given_equal_source':
                        sum((int(a)^int(b)).bit_count() for a, b in
                            zip(left['folds'].split(';'), right['folds'].split(';')))
                        if same_source else None,
                    'index_mismatch': int(left['indices'] != right['indices']),
                    'query_tag_mismatch': int(left['query_tags'] != right['query_tags']),
                    'provider_metadata_mismatch': int(any(left[k] != right[k] for k in
                        ('provider_type', 'hit_bank', 'alternate_bank'))),
                    'prediction_difference': int(lp != rp), 'harmful': harmful, 'helpful': helpful}
                for key, value in values.items():
                    metrics[key].observe(conditional_id, value)
                # Keep only milestone coordinates; full trace remains the primary source.
                if any(value for value in values.values() if value is not None):
                    coordinates['last_nonzero'] = {'conditional_id': conditional_id,
                        'branch_id': int(right['branch_id']), 'fault_retire_tick': int(right['retire_tick'])}
            if int(right['retire_tick']) >= event_tick and int(left['retire_tick']) >= event_tick:
                yield {'branch_id': conditional_id, 'fault_time': int(right['retire_tick']),
                       'clean_time': int(left['retire_tick']), 'harmful': harmful,
                       'helpful': helpful, 'prediction_differences': int(lp != rp)}

    windows = timing_windows(checkpoints())
    origins = {name: RecoverySeries() for name in ('active_raw_origin', 'live_raw_origin')}
    with (fault/'raw_origins.csv').open() as stream:
        for row in csv.DictReader(stream):
            if int(row['tick']) < event_tick:
                continue
            active, live = int(row['active_origin_bits']), int(row['restorable_origin_bits'])
            origins['active_raw_origin'].observe(int(row['callback_ordinal']), active)
            origins['live_raw_origin'].observe(int(row['callback_ordinal']), active+live)
    same_output = (clean/'program.stdout').read_bytes() == (fault/'program.stdout').read_bytes()
    same_retirement = all(u0[key] == uf[key] for key in
                          ('retired_ops', 'retired_instructions', 'retired_pc_identity'))
    valid = same_output and same_retirement
    return {'status': 'COMPARABLE' if valid else 'NONCOMPARABLE',
            'comparison': 'UF/U0; no protected candidate measured',
            'fault_tick': event_tick, 'program_exit_tick_clean': u0['tick'],
            'program_exit_tick_fault': uf['tick'], 'tick_difference': uf['tick']-u0['tick'],
            'runtime_overhead_percent': 100*(uf['tick']/u0['tick']-1) if valid else None,
            'stdout_equal': same_output, 'retirement_identity_equal': same_retirement,
            'counts': counts, 'last_observed_difference_coordinate': coordinates,
            'state_recovery': {k: v.summary() for k, v in metrics.items()},
            'origin_recovery': {k: v.summary() for k, v in origins.items()},
            'origin_scope': 'raw provenance, including observed live restorable heads; not semantic shadow distance',
            'physical_cell_overwrite_time': None, 'path_origin_recovery': 'NOT_OBSERVED',
            'learning_full_state_recovery': 'NOT_OBSERVED_IN_CPU_TRACE',
            'prediction_scope': 'TAGE conditional direction; final BPU direction/target overrides are not exported',
            'final_BPU_prediction_recovery': 'NOT_OBSERVED',
            'timing_rule_scope': 'exact CPU retirement times with conservative TAGE-direction-difference exclusion; not a complete final-BPU recovery certificate',
            'fold_reference_scope': 'only equal raw/path/nonspec snapshots at matched architectural queries; other samples NA_ALIGNMENT',
            'timing': windows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--clean', type=Path, required=True)
    p.add_argument('--fault', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('output exists; choose a fresh analysis directory')
    result = summarize(args.clean, args.fault)
    args.output.mkdir(parents=True)
    windows = result['timing'].pop('windows')
    (args.output/'SUMMARY.json').write_text(json.dumps(result, indent=2)+'\n')
    if windows:
        with (args.output/'RECOVERY_WINDOWS.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(windows[0]))
            writer.writeheader()
            writer.writerows(windows)
    print(json.dumps({k: v for k, v in result.items() if k not in
                     ('state_recovery', 'origin_recovery', 'counts', 'timing')}))


if __name__ == '__main__':
    main()
